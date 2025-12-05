#!/usr/bin/env python3
"""Full pipeline rebuild with signal protection and progress logging."""
import signal
import sys
import time
import json
from pathlib import Path

# Ignore signals that might kill the process
signal.signal(signal.SIGINT, signal.SIG_IGN)
signal.signal(signal.SIGTERM, signal.SIG_IGN)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingestion.csv_loader import load_csv_records, write_staging_jsonl

SOURCE = Path("data/source")
STAGING = Path("data/staging")
DATABASE = Path("data/database")

def log(msg: str):
    """Print with timestamp and flush."""
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def step1_ingest():
    """Ingest CSVs to staging JSONL."""
    STAGING.mkdir(exist_ok=True)
    
    csvs = sorted(SOURCE.glob("*.csv"))
    total = len(csvs)
    
    # Find already done
    done = {p.stem for p in STAGING.glob("*.jsonl")}
    todo = [c for c in csvs if c.stem not in done]
    
    log(f"📥 STEP 1: INGEST - {len(todo)} remaining of {total} CSVs")
    
    start = time.time()
    success = errors = 0
    
    for i, csv in enumerate(todo, 1):
        try:
            out = STAGING / (csv.stem + ".jsonl")
            records = list(load_csv_records(csv))
            write_staging_jsonl(records, out)
            success += 1
        except Exception as e:
            errors += 1
            log(f"  ❌ {csv.name}: {e}")
        
        if i % 100 == 0 or i == len(todo):
            elapsed = time.time() - start
            rate = i / elapsed if elapsed > 0 else 1
            eta = (len(todo) - i) / rate if rate > 0 else 0
            log(f"  [{i:4d}/{len(todo)}] {success} ok, {errors} err | {elapsed:.0f}s, ~{eta:.0f}s left")
    
    log(f"✅ INGEST COMPLETE: {success} new files")
    return success

def step2_transform():
    """Transform staging JSONL to database JSON by running the transform script."""
    DATABASE.mkdir(exist_ok=True)
    
    log("🔄 STEP 2: TRANSFORM - Running transform_to_database.py...")
    
    import subprocess
    start = time.time()
    
    result = subprocess.run(
        [sys.executable, "scripts/pipeline/transform_to_database.py"],
        cwd=str(Path(__file__).parent.parent.parent),
        capture_output=True,
        text=True
    )
    
    elapsed = time.time() - start
    
    # Count results
    db_count = len(list(DATABASE.glob("*.json")))
    
    if result.returncode != 0:
        log(f"  ⚠️ Transform had issues: {result.stderr[:200] if result.stderr else 'unknown'}")
    
    log(f"✅ TRANSFORM COMPLETE: {db_count} database files in {elapsed:.1f}s")
    return db_count

def step3_build_duckdb():
    """Build DuckDB from database JSON files."""
    import duckdb
    
    DB_FILE = Path("data/keymark.duckdb")
    SCHEMA_FILE = Path("backend/db/schema.sql")
    
    log("🗄️ STEP 3: BUILD DUCKDB")
    
    files = sorted(DATABASE.glob("*.json"))
    log(f"  Found {len(files)} database files")
    
    # Collect all data first
    log("  Collecting data...")
    start = time.time()
    
    manufacturers = {}  # name -> id
    models = {}  # (mfr_id, name) -> id
    variants_set = set()
    
    variants = []
    measurements = []
    
    for fi, p in enumerate(files, 1):
        try:
            data = json.loads(p.read_text())
            meta = data.get("file_metadata", {})
            mfr = (meta.get("Manufacturer") or "Unknown").strip() or "Unknown"
            model = (meta.get("Modelname") or "Unknown").strip() or "Unknown"
            
            # Track manufacturer
            if mfr not in manufacturers:
                manufacturers[mfr] = len(manufacturers) + 1
            mfr_id = manufacturers[mfr]
            
            # Track model
            if (mfr_id, model) not in models:
                models[(mfr_id, model)] = len(models) + 1
            
            # Process heat pumps
            for hi, hp in enumerate(data.get("heat_pumps", []), 1):
                vname = (hp.get("variant") or hp.get("title") or "").strip() or f"variant_{hi:03d}"
                base, sfx = vname, 2
                while (mfr, model, vname) in variants_set:
                    vname = f"{base}_{sfx}"; sfx += 1
                variants_set.add((mfr, model, vname))
                
                props = {k: v for k, v in hp.items() if k not in ("measurements", "variant", "title")}
                variants.append((mfr, model, vname, json.dumps(props) if props else None))
                
                for m in hp.get("measurements", []):
                    measurements.append((mfr, model, vname,
                        m.get("climate"), m.get("application"), m.get("design_temp"),
                        m.get("capacity"), m.get("power_input"), m.get("cop"),
                        m.get("outlet_temp"), m.get("scop"), json.dumps(m) if m else None))
        except Exception as e:
            pass
        
        if fi % 500 == 0:
            log(f"    Processed {fi}/{len(files)} files...")
    
    log(f"  Collected: {len(manufacturers)} mfrs, {len(models)} models, {len(variants)} variants, {len(measurements)} measurements")
    
    # Write to DuckDB
    log("  Writing to DuckDB...")
    
    if DB_FILE.exists():
        DB_FILE.unlink()
    
    conn = duckdb.connect(str(DB_FILE))
    conn.execute(SCHEMA_FILE.read_text())
    
    # Insert manufacturers
    conn.execute("BEGIN")
    conn.executemany("INSERT OR IGNORE INTO manufacturers (name) VALUES (?)", 
                     [(m,) for m in manufacturers.keys()])
    conn.execute("COMMIT")
    log(f"    Inserted {len(manufacturers)} manufacturers")
    
    # Insert models
    conn.execute("BEGIN")
    conn.executemany("INSERT OR IGNORE INTO models (manufacturer_name, model_name) VALUES (?, ?)",
                     [(mfr, model) for (mfr_id, model), _ in models.items() 
                      for mfr in [next(m for m, i in manufacturers.items() if i == mfr_id)]])
    conn.execute("COMMIT")
    log(f"    Inserted {len(models)} models")
    
    # Insert variants in batches
    BATCH = 10000
    conn.execute("BEGIN")
    for i in range(0, len(variants), BATCH):
        batch = variants[i:i+BATCH]
        conn.executemany("INSERT OR IGNORE INTO variants (manufacturer_name, model_name, variant_name, properties) VALUES (?, ?, ?, ?)", batch)
        if (i + BATCH) % 50000 == 0:
            log(f"    Variants: {min(i+BATCH, len(variants))}/{len(variants)}")
    conn.execute("COMMIT")
    log(f"    Inserted {len(variants)} variants")
    
    # Insert measurements in batches
    conn.execute("BEGIN")
    for i in range(0, len(measurements), BATCH):
        batch = measurements[i:i+BATCH]
        conn.executemany("""INSERT OR IGNORE INTO measurements 
            (manufacturer_name, model_name, variant_name, climate, application, design_temp,
             capacity, power_input, cop, outlet_temp, scop, raw_data) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", batch)
        if (i + BATCH) % 100000 == 0:
            log(f"    Measurements: {min(i+BATCH, len(measurements))}/{len(measurements)}")
    conn.execute("COMMIT")
    log(f"    Inserted {len(measurements)} measurements")
    
    conn.close()
    elapsed = time.time() - start
    log(f"✅ DUCKDB COMPLETE in {elapsed:.1f}s")

def main():
    log("=" * 60)
    log("FULL PIPELINE REBUILD")
    log("=" * 60)
    
    overall_start = time.time()
    
    step1_ingest()
    step2_transform()
    step3_build_duckdb()
    
    elapsed = time.time() - overall_start
    log("=" * 60)
    log(f"🎉 PIPELINE COMPLETE in {elapsed/60:.1f} minutes")
    log("=" * 60)
    
    # Final stats
    log(f"  Source CSVs: {len(list(SOURCE.glob('*.csv')))}")
    log(f"  Staging files: {len(list(STAGING.glob('*.jsonl')))}")
    log(f"  Database files: {len(list(DATABASE.glob('*.json')))}")

if __name__ == "__main__":
    main()

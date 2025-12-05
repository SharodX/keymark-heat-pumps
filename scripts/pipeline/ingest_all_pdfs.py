"""Ingest all PDF files from source directory and extract tables to JSONL."""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add the repository root to sys.path so imports like `ingestion.*` work when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ingestion.pdf_extractor import extract_pdf_tables, PDFExtractionError
from ingestion import IngestionMetrics

root = Path("/workspaces/keymark-heat-pumps/data/source")
out_root = Path("/workspaces/keymark-heat-pumps/data/staging")
out_root.mkdir(parents=True, exist_ok=True)

# Create logs directory
logs_dir = Path("/workspaces/keymark-heat-pumps/data/logs")
logs_dir.mkdir(parents=True, exist_ok=True)

# Initialize metrics and logging
metrics = IngestionMetrics()
pdf_files = sorted(root.rglob("*.pdf"))
total_pdfs = len(pdf_files)

print(f"Found {total_pdfs} PDF files to process")
print("=" * 80)

processed = 0
successful = 0
failed = 0
errors_log = []

for pdf_path in pdf_files:
    processed += 1
    model_id = pdf_path.stem
    
    try:
        # Extract records from PDF
        records = extract_pdf_tables(pdf_path, metrics=metrics, model_id=model_id)
        
        # Write to JSONL
        out_path = out_root / (model_id + ".jsonl")
        with open(out_path, 'w') as f:
            for record in records:
                f.write(json.dumps(record) + '\n')
        
        successful += 1
        # Only print every 50 files or on failure to reduce output noise
        if processed % 50 == 0 or processed <= 5:
            print(f"[{processed:4d}/{total_pdfs}] ✓ {len(records)} records from {model_id[:50]}...")
        
    except PDFExtractionError as e:
        failed += 1
        error_msg = str(e)
        errors_log.append({
            'file': model_id,
            'error': error_msg,
            'timestamp': datetime.now().isoformat()
        })
        print(f"[{processed:4d}/{total_pdfs}] ✗ {model_id}: {error_msg}")
    except Exception as e:
        failed += 1
        error_msg = f"Unexpected error: {str(e)}"
        errors_log.append({
            'file': model_id,
            'error': error_msg,
            'timestamp': datetime.now().isoformat()
        })
        print(f"[{processed:4d}/{total_pdfs}] ✗ {model_id}: {error_msg}")

print("=" * 80)
print(f"\nResults:")
print(f"  Total PDFs: {total_pdfs}")
print(f"  Successful: {successful} ({100*successful/total_pdfs:.1f}%)")
print(f"  Failed: {failed} ({100*failed/total_pdfs:.1f}%)")

if errors_log:
    error_log_path = logs_dir / "pdf_ingestion_errors.json"
    with open(error_log_path, 'w') as f:
        json.dump(errors_log, f, indent=2)
    print(f"\nError details saved to: {error_log_path}")

print(f"\nFiles written to: {out_root}")

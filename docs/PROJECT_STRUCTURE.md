# Keymark Heat Pumps - Project Structure

## Overview

This project aggregates European Keymark heat pump certification data, normalizes it into a DuckDB database, and provides analysis tools + web interface for SCOP verification according to EN14825:2018.

## Data Model

The database uses a **Manufacturer → Subtype → Model** hierarchy:

| Level | Description | Example |
|-------|-------------|---------|
| **Manufacturer** | Company producing the heat pump | "Daikin Europe N.V." |
| **Subtype** | Product line or series | "EHBH08D6V" |
| **Model** | Specific variant/configuration | "ERGA04DV + EHBH08D6V" |

---

## Directory Structure

```
keymark-heat-pumps/
├── docs/                          # 📚 Documentation
│   ├── PROJECT_STRUCTURE.md       # This file
│   ├── EN_CODES_REFERENCE.md      # EN14825/14511/12102 code mapping
│   ├── SCOP_CALCULATIONS.md       # SCOP formula implementation
│   └── ALTERNATE_FORMAT_FILES.md  # Files with metadata-only format
│
├── data/                          # 📦 All data files (mostly .gitignored)
│   ├── source/                    # Raw input files (CSV + PDF from Keymark)
│   ├── staging/                   # Intermediate JSONL files (from ingestion)
│   ├── database/                  # Structured JSON (ready for DuckDB load)
│   ├── pdf_extractions/           # Extracted PDF table data
│   ├── logs/                      # Sync and transform logs
│   ├── keymark.duckdb             # Full database
│   └── keymark_unique.duckdb      # Deduplicated database
│
├── ingestion/                     # 🔄 Data ingestion modules
│   ├── csv_loader.py              # CSV → JSONL normalization
│   └── pdf_extractor.py           # PDF → JSON extraction
│
├── scripts/                       # 🔧 Pipeline & analysis scripts
│   ├── pipeline/                  # Core pipeline scripts
│   │   ├── ingest_all_csvs.py     # Parse CSVs → staging JSONL
│   │   ├── ingest_all_pdfs.py     # Extract PDFs → staging JSONL
│   │   ├── transform_to_database.py # JSONL → database JSON
│   │   ├── build_duckdb.py        # JSON → keymark.duckdb (main builder)
│   │   ├── build_unique_duckdb.py   # Deduplicate → keymark_unique.duckdb
│   │   ├── full_rebuild.py        # Complete pipeline from scratch
│   │   └── incremental_update.py  # Sync new files only
│   ├── analysis/                  # Analysis & verification
│   │   ├── calculate_scop_en14825.py
│   │   ├── run_scop_batch.py
│   │   └── analyze_dataset.py
│   ├── scraping/                  # Keymark sync scripts
│   │   └── sync_keymark.py        # Download CSVs + PDFs from Keymark
│   └── archive/                   # Unused/experimental scripts
│
├── backend/                       # 🖥️ FastAPI backend
│   ├── api/
│   │   ├── app.py                 # Main FastAPI application
│   │   └── routes/                # API endpoints
│   │       ├── heat_pumps.py      # /heat-pumps endpoint
│   │       ├── measurements.py    # /measurements endpoint
│   │       ├── en14825.py         # /en14825/* endpoints
│   │       └── heat_pump_detail.py # /heat-pump/detail endpoint
│   ├── models/                    # Pydantic models
│   │   ├── heat_pump.py
│   │   └── measurement.py
│   └── db/
│       ├── schema.sql             # DuckDB schema
│       └── deps.py                # Database dependencies
│
├── frontend/                      # 🎨 Streamlit dashboard
│   ├── streamlit_app.py           # Main dashboard
│   └── pages/                     # Additional pages
│       ├── en14825_analytics.py   # EN14825 data explorer
│       ├── heat_pump_detail.py    # Individual heat pump viewer
│       └── scop_verification.py   # SCOP calculation verifier
│
├── tests/                         # ✅ Unit tests
│   ├── test_csv_loader.py
│   └── test_scop_calculator.py
│
├── outputs/                       # 📊 Analysis outputs
│   └── *.csv, *.json              # Generated reports
│
└── archive/                       # 🗄️ Old/working documents
    ├── mapping_experiments/       # CSV↔PDF mapping attempts
    └── working_docs/              # Draft documentation
```

---

## Data Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA PIPELINE                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  [External]              [Ingestion]           [Transform]           │
│  Keymark CSVs  ────────► staging/*.jsonl ────► data/database/*.json  │
│  Keymark PDFs  ────────► staging/*.jsonl       (structured JSON)     │
│                          pdf_extractions/                            │
│                                                                      │
│  [Database Build]                              [Serve]               │
│  data/database/*.json ─► keymark.duckdb ─────► FastAPI + Streamlit   │
│                       └─► keymark_unique.duckdb                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Pipeline Scripts (in order)

| Script | Input | Output | Description |
|--------|-------|--------|-------------|
| `sync_keymark.py` | Keymark website | `data/source/` | Download CSVs + PDFs |
| `ingest_all_csvs.py` | `data/source/*.csv` | `data/staging/*.jsonl` | Parse CSV files |
| `ingest_all_pdfs.py` | `data/source/*.pdf` | `data/staging/*.jsonl` | Extract PDF tables |
| `transform_to_database.py` | `data/staging/*.jsonl` | `data/database/*.json` | Normalize to JSON |
| `build_duckdb.py` | `data/database/*.json` | `data/keymark.duckdb` | Build DuckDB |
| `build_unique_duckdb.py` | `data/keymark.duckdb` | `data/keymark_unique.duckdb` | Deduplicate |

**Convenience scripts:**
- `full_rebuild.py` - Complete pipeline from source to DuckDB
- `incremental_update.py` - Sync and process only new files

---

## Key Files

### Documentation
| File | Purpose |
|------|---------|
| `docs/EN_CODES_REFERENCE.md` | Complete EN14825/14511/12102 code mapping |
| `docs/SCOP_CALCULATIONS.md` | EN14825 SCOP formulas & implementation |
| `docs/ALTERNATE_FORMAT_FILES.md` | 404 files with metadata-only format |
| `data/DIMENSION_CODE_MAPPING.md` | Dimension encoding (X_Y_Z_W format) |

### Configuration
| File | Purpose |
|------|---------|
| `data/manifest.yaml` | Data source definitions |
| `backend/db/schema.sql` | DuckDB table schema |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Excludes data files from git |

---

## Databases

### Main Database (`keymark.duckdb`)

| Table | Count | Description |
|-------|-------|-------------|
| `manufacturers` | 181 | Unique manufacturer names |
| `subtypes` | 2,446 | Product lines (with metadata JSON) |
| `models` | 8,334 | Specific configurations (with properties JSON) |
| `measurements` | 1,130,175 | EN test measurements |

### Unique Database (`keymark_unique.duckdb`)

| Table | Count | Description |
|-------|-------|-------------|
| `model_signatures` | 3,762 | Unique measurement fingerprints |
| `unique_models` | 3,762 | Representative model for each signature |
| `unique_measurements` | 472,214 | Deduplicated measurements |
| `model_lookup` | 8,234 | Maps all models to their signature |

### Schema

```sql
-- Main tables
CREATE TABLE manufacturers (manufacturer_name VARCHAR PRIMARY KEY);

CREATE TABLE subtypes (
    manufacturer_name VARCHAR,
    subtype_name VARCHAR,
    metadata JSON,
    PRIMARY KEY (manufacturer_name, subtype_name)
);

CREATE TABLE models (
    manufacturer_name VARCHAR,
    subtype_name VARCHAR,
    model_name VARCHAR,
    properties JSON,
    PRIMARY KEY (manufacturer_name, subtype_name, model_name)
);

CREATE TABLE measurements (
    manufacturer_name VARCHAR,
    subtype_name VARCHAR,
    model_name VARCHAR,
    en_code VARCHAR,
    dimension VARCHAR,
    value DOUBLE
);
```

---

## Running the Project

### Using VS Code Tasks (Recommended)
- **Start All**: `Ctrl+Shift+B`
- **Stop All**: Run Task → "🛑 Stop All Services"

### Manual Commands

```bash
# API Server
uvicorn backend.api.app:app --reload --host 0.0.0.0 --port 8000

# Streamlit Dashboard
streamlit run frontend/streamlit_app.py --server.port 8501

# Rebuild Database
python scripts/pipeline/build_duckdb.py
python scripts/pipeline/build_unique_duckdb.py

# Full Pipeline Rebuild
python scripts/pipeline/full_rebuild.py

# Run Tests
pytest tests/
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/heat-pumps/` | GET | List heat pumps with search/filter |
| `/measurements/` | GET | Paginated measurements |
| `/en14825/metadata` | GET | Filter options (manufacturers, refrigerants, etc.) |
| `/en14825/data` | GET | EN14825 data with comprehensive filtering |
| `/heat-pump/detail` | GET | Detailed test points for specific model |

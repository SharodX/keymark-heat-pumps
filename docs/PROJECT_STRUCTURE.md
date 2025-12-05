# Keymark Heat Pumps - Project Structure

## Overview

This project aggregates European Keymark heat pump certification data, normalizes it into a DuckDB database, and provides analysis tools + web interface for SCOP verification according to EN14825:2018.

---

## Directory Structure

```
keymark-heat-pumps/
├── docs/                          # 📚 Documentation (NEW - consolidated)
│   ├── PROJECT_STRUCTURE.md       # This file
│   ├── PIPELINE.md                # Data pipeline documentation
│   ├── EN_CODES_REFERENCE.md      # Final EN code mapping reference
│   └── SCOP_CALCULATIONS.md       # SCOP formula implementation
│
├── data/                          # 📦 All data files
│   ├── source/                    # Raw input files (CSV + PDF from Keymark)
│   ├── staging/                   # Intermediate JSONL files (from ingestion)
│   ├── database/                  # Structured JSON (ready for DuckDB load)
│   ├── pdf_extractions/           # Extracted PDF table data
│   ├── keymark.duckdb             # Full database
│   └── keymark_unique.duckdb      # Deduplicated database
│
├── ingestion/                     # 🔄 Data ingestion modules
│   ├── csv_loader.py              # CSV → JSONL normalization
│   └── pdf_extractor.py           # PDF → JSON extraction
│
├── scripts/                       # 🔧 Pipeline & analysis scripts
│   ├── pipeline/                  # Core pipeline scripts
│   │   ├── ingest_all_csvs.py
│   │   ├── ingest_all_pdfs.py
│   │   ├── transform_to_database.py
│   │   ├── build_duckdb.py
│   │   └── build_unique_duckdb.py
│   ├── analysis/                  # Analysis & verification
│   │   ├── calculate_scop_en14825.py
│   │   ├── run_scop_batch.py
│   │   ├── analyze_dataset.py
│   │   └── analyze_multi_climate_scop.py
│   └── archive/                   # Unused/experimental scripts
│
├── backend/                       # 🖥️ FastAPI backend
│   ├── api/
│   │   ├── app.py                 # Main FastAPI application
│   │   └── routes/                # API endpoints
│   └── db/
│       ├── schema.sql             # DuckDB schema
│       └── deps.py                # Database dependencies
│
├── frontend/                      # 🎨 Streamlit dashboard
│   ├── streamlit_app.py           # Main dashboard
│   └── pages/                     # Additional pages
│       ├── heat_pump_detail.py
│       └── scop_verification.py
│
├── tests/                         # ✅ Unit tests
│   ├── test_csv_loader.py
│   └── test_scop_calculator.py
│
├── outputs/                       # 📊 Analysis outputs
│   └── *.csv, *.json              # Generated reports
│
└── archive/                       # 🗄️ Old/working documents (NEW)
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

1. **`scripts/pipeline/ingest_all_csvs.py`** - Parse CSVs → `staging/*.jsonl`
2. **`scripts/pipeline/ingest_all_pdfs.py`** - Extract PDFs → `staging/*.jsonl` + `pdf_extractions/*.json`
3. **`scripts/pipeline/transform_to_database.py`** - JSONL → `data/database/*.json`
4. **`scripts/pipeline/build_duckdb.py`** - JSON → `data/keymark.duckdb`
5. **`scripts/pipeline/build_unique_duckdb.py`** - Deduplicate → `data/keymark_unique.duckdb`

---

## Key Files

### Documentation (Final Versions)
| File | Purpose |
|------|---------|
| `docs/EN_CODES_REFERENCE.md` | Complete EN14825/14511/12102 code mapping |
| `docs/SCOP_CALCULATIONS.md` | EN14825 SCOP formulas & implementation |
| `data/DIMENSION_CODE_MAPPING.md` | Dimension encoding (X_Y_Z_W format) |

### Configuration
| File | Purpose |
|------|---------|
| `data/manifest.yaml` | Data source definitions |
| `backend/db/schema.sql` | DuckDB table schema |
| `requirements.txt` | Python dependencies |

### Mapping Files
| File | Purpose | Status |
|------|---------|--------|
| `data/complete_mapping.json` | Analysis output - EN code statistics | Reference only |
| `data/universal_mapping.json` | Generalized mapping rules | Reference only |
| `data/header_climate_mapping.json` | PDF header → climate zone | Used by extraction |

---

## Databases

| Database | Rows | Purpose |
|----------|------|---------|
| `keymark.duckdb` | 309K measurements | Full database with duplicates |
| `keymark_unique.duckdb` | 309K measurements | Cross-manufacturer deduplication |

### Tables
- `manufacturers` (95) - Unique manufacturer names
- `models` (1,187) - Heat pump models
- `variants` (2,484) - Model variants/configurations
- `measurements` (309,009) - EN test measurements
- `unique_variants` - Deduplicated variants
- `unique_measurements` - Canonical measurements
- `variant_lookup` - Maps variants to signatures
- `variant_signatures` - Fingerprints for deduplication

---

## Running the Project

### API Server
```bash
uvicorn backend.api.app:app --reload
```

### Streamlit Dashboard
```bash
streamlit run frontend/streamlit_app.py
```

### Rebuild Database
```bash
python scripts/pipeline/build_duckdb.py
python scripts/pipeline/build_unique_duckdb.py
```

### Run Tests
```bash
pytest tests/
```

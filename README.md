# Keymark Heat Pumps

Analyze and verify heat pump performance data from the European Keymark certification database.

## Overview

This project:
1. **Ingests** raw CSV and PDF data from Keymark certifications
2. **Normalizes** data into a structured DuckDB database
3. **Analyzes** heat pump performance (SCOP calculations per EN14825:2018)
4. **Serves** data via FastAPI + Streamlit dashboard

## Quick Start

### VS Code / Codespaces (Recommended)

Use the built-in tasks:

| Action | Shortcut |
|--------|----------|
| **🚀 Start All Services** | `Ctrl+Shift+B` (or `Cmd+Shift+B` on Mac) |
| **🛑 Stop All Services** | `Ctrl+Shift+P` → "Run Task" → "🛑 Stop All Services" |
| **🔄 Restart All Services** | `Ctrl+Shift+P` → "Run Task" → "🔄 Restart All Services" |

Or use the **Run and Debug** panel (`Ctrl+Shift+D`) for debugging:
- "🚀 Start All (Debug)" - starts both with debugger attached

### Manual Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start API server
uvicorn backend.api.app:app --reload

# Start Streamlit dashboard  
streamlit run frontend/streamlit_app.py
```

## Project Structure

See [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md) for detailed documentation.

```
keymark-heat-pumps/
├── docs/                    # Documentation
├── data/                    # Data files (source, staging, database)
├── ingestion/               # Data ingestion modules
├── scripts/
│   ├── pipeline/            # Core pipeline scripts
│   └── analysis/            # SCOP calculation & analysis
├── backend/                 # FastAPI backend
├── frontend/                # Streamlit dashboard
├── tests/                   # Unit tests
├── outputs/                 # Analysis outputs
└── archive/                 # Old/experimental files
```

## Data Pipeline

```
CSV/PDF sources → staging/JSONL → database/JSON → DuckDB → API → Dashboard
```

**Pipeline scripts** (in order):
1. `scripts/pipeline/ingest_all_csvs.py`
2. `scripts/pipeline/ingest_all_pdfs.py`
3. `scripts/pipeline/transform_to_database.py`
4. `scripts/pipeline/build_duckdb.py`
5. `scripts/pipeline/build_unique_duckdb.py`

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md) | Full project structure |
| [`docs/EN_CODES_REFERENCE.md`](docs/EN_CODES_REFERENCE.md) | EN14825/14511/12102 code mapping |
| [`docs/SCOP_CALCULATIONS.md`](docs/SCOP_CALCULATIONS.md) | SCOP formula implementation |
| [`data/DIMENSION_CODE_MAPPING.md`](data/DIMENSION_CODE_MAPPING.md) | Dimension encoding (X_Y_Z_W) |

## Database

| Database | Description |
|----------|-------------|
| `data/keymark.duckdb` | Full database (309K measurements) |
| `data/keymark_unique.duckdb` | Deduplicated version |

## API Endpoints

- `GET /measurements` – Paginated measurements with filters
- `GET /heat-pumps` – Heat pump list with search
- `GET /en14825` – EN14825-specific data
- `GET /health` – Health check

## Testing

```bash
pytest tests/
```

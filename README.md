# keymark-heat-pumps
Analyze heat pumps found in keymark database

## Ingestion utilities

- Define CSV/PDF sources in `data/manifest.yaml` with model identifiers.
- Use `ingestion/csv_loader.py` to normalize CSV headers and emit staging JSONL files under `data/staging/`.
- Use `ingestion/pdf_extractor.py` to pull tables and labeled values from PDFs, capturing `model_id` and `submodel_id` metadata where available.
- Shared logging and metrics helpers live in `ingestion/__init__.py`.

## API server

The FastAPI application in `backend/api/app.py` exposes DuckDB data with paginated responses tailored for Streamlit or any HTTP client.

### Endpoints

- `GET /measurements` – Paginated measurement rows with exact-match filters plus optional `climates=warmer|average|colder` repeatable params.
- `GET /heat-pumps` – Paginated list of manufacturer/model/variant combinations with total measurement counts and `has_cold_climate` flag; supports `search=` and `has_cold_climate=true` filters for dropdowns.

1. Build the DuckDB file if necessary: `scripts/build_duckdb.py`.
2. Install dependencies once: `pip install -r requirements.txt`.
3. Launch the server with Uvicorn:

```bash
/workspaces/keymark-heat-pumps/.venv/bin/uvicorn backend.api.app:app --reload
```

### Pagination contract

- Endpoints accept `limit` (1-1000) and `offset` query params; defaults are `limit=100`, `offset=0`.
- Responses follow the `Page[T]` structure with a `meta` block: `{total, limit, offset, has_more}` for quick UI paging.
- Filter parameters (manufacturer/model/variant/en_code/dimension/climates) map directly to DuckDB filters so Streamlit can request only the subset it needs.

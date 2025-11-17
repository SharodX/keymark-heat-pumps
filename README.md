# keymark-heat-pumps
Analyze heat pumps found in keymark database

## Ingestion utilities

- Define CSV/PDF sources in `data/manifest.yaml` with model identifiers.
- Use `ingestion/csv_loader.py` to normalize CSV headers and emit staging JSONL files under `data/staging/`.
- Use `ingestion/pdf_extractor.py` to pull tables and labeled values from PDFs, capturing `model_id` and `submodel_id` metadata where available.
- Shared logging and metrics helpers live in `ingestion/__init__.py`.

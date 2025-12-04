import sys
from pathlib import Path

# Add the repository root to sys.path so imports like `ingestion.*` work when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingestion.csv_loader import load_csv_records, write_staging_jsonl

root = Path("/workspaces/keymark-heat-pumps/data/source")
out_root = Path("/workspaces/keymark-heat-pumps/staging")
out_root.mkdir(parents=True, exist_ok=True)

for csv_path in root.rglob("*.csv"):
    records, _ = load_csv_records(csv_path, model_id=csv_path.stem)
    out_path = out_root / (csv_path.stem + ".jsonl")
    write_staging_jsonl(records, out_path)
    print("Wrote", len(records), "rows ->", out_path)
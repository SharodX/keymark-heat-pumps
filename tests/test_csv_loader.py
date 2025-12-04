from pathlib import Path
import json

import pytest

from ingestion.csv_loader import load_csv_records, normalize_header, write_staging_jsonl


class DummyMetrics:
    def __init__(self):
        self.rows = 0

    def add_rows(self, n: int) -> None:
        self.rows += n


def test_normalize_header_basic():
    assert normalize_header("Foo Bar") == "foo_bar"
    assert normalize_header("  Mixed-CASE Value ") == "mixed-case_value"


def test_load_csv_records_basic(tmp_path):
    csv_path = tmp_path / "sample.csv"
    # headers with spaces + different casing, include variant/sub model combos
    csv_content = "Model Name,Variant,Sub Model,Value\n" "ModelA,VAR1,SubA,100\n"
    csv_path.write_text(csv_content, encoding="utf-8")

    metrics = DummyMetrics()
    records, field_map = load_csv_records(csv_path, metrics=metrics, model_id="m-1")

    assert isinstance(records, list)
    assert len(records) == 1
    r = records[0]
    # model_id given is applied to all records
    assert r["model_id"] == "m-1"
    # the variant value should be copied into submodel_id by the loader
    assert r.get("submodel_id") == "VAR1"
    # field_map maps normalized->original header
    assert field_map["model_name"] == "Model Name"


def test_write_staging_jsonl(tmp_path):
    sample = [{"a": 1}, {"b": 2}]
    out = tmp_path / "staging" / "out.jsonl"
    write_staging_jsonl(sample, out)
    assert out.exists()
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == sample[0]


def test_integration_load_first_repo_csv():
    csv_root = Path("/workspaces/keymark-heat-pumps/data/source")
    csvs = list(csv_root.glob("**/*.csv"))
    if not csvs:
        pytest.skip("No CSV files found in data/source to run integration test.")
    first = csvs[0]
    metrics = DummyMetrics()
    records, field_map = load_csv_records(first, metrics=metrics, model_id=first.stem)
    # ensure metrics matched the record count
    assert metrics.rows == len(records)
    # every record should include the model_id we passed
    for r in records:
        assert r.get("model_id") == first.stem
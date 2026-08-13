#!/usr/bin/env python3
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "nyc311_2025-01-01_to_2025-01-02.csv"
MANIFEST = ROOT / "data" / "raw" / "source_manifest.json"
START = datetime.fromisoformat("2025-01-01T00:00:00.000")
END = datetime.fromisoformat("2025-01-03T00:00:00.000")
REQUIRED = {"unique_key", "created_date", "agency", "complaint_type", "status", "borough"}


def validate():
    manifest = json.loads(MANIFEST.read_text())
    digest = hashlib.sha256(RAW.read_bytes()).hexdigest()
    failures = []
    if digest != manifest["sha256"]:
        failures.append("raw snapshot hash differs from manifest")
    with RAW.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if not REQUIRED.issubset(reader.fieldnames or []):
            failures.append("required columns missing")
        rows = list(reader)
    if len(rows) != manifest["rows"]:
        failures.append("row count differs from manifest")
    ids = [row["unique_key"] for row in rows]
    if len(ids) != len(set(ids)):
        failures.append("duplicate unique_key values")
    outside = [row["unique_key"] for row in rows if not START <= datetime.fromisoformat(row["created_date"]) < END]
    if outside:
        failures.append(f"{len(outside)} rows outside declared window")
    if failures:
        raise SystemExit("validation failed: " + "; ".join(failures))
    print(f"validated hash, schema, {len(rows)} rows, unique IDs, and time window")


if __name__ == "__main__":
    validate()

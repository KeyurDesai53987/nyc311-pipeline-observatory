#!/usr/bin/env python3
"""Checkpointed ingestion of a fixed NYC 311 snapshot from the Socrata API."""
import argparse
import csv
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
ENDPOINT = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
START = "2025-01-01T00:00:00.000"
END = "2025-01-03T00:00:00.000"
FIELDS = ["unique_key", "created_date", "closed_date", "agency", "complaint_type",
          "descriptor", "status", "borough", "incident_zip", "latitude", "longitude",
          "due_date", "resolution_description", "resolution_action_updated_date"]


def atomic_json_write(path, payload):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n")
    os.replace(temporary, path)


def prepare_partial(partial, checkpoint, fields):
    """Return the durable row offset, rolling back an uncommitted appended page."""
    if not checkpoint.exists():
        with partial.open("w", newline="") as handle:
            csv.DictWriter(handle, fieldnames=fields).writeheader()
        return 0
    state = json.loads(checkpoint.read_text())
    expected = state["offset"]
    if not partial.exists():
        raise RuntimeError("checkpoint exists but partial data file is missing")
    with partial.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) < expected:
        raise RuntimeError(f"partial file has {len(rows)} rows but checkpoint requires {expected}")
    if len(rows) > expected:
        with partial.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows[:expected])
    return expected


def fetch_page(offset, limit, retries=4):
    params = {
        "$select": ",".join(FIELDS),
        "$where": f'created_date >= "{START}" and created_date < "{END}"',
        "$order": "created_date,unique_key",
        "$limit": str(limit),
        "$offset": str(offset),
    }
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "nyc311-pipeline-observatory/1.0"})
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response), url
        except Exception:
            if attempt + 1 == retries:
                raise
            time.sleep(2 ** attempt)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--page-size", type=int, default=5000)
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    output = RAW / "nyc311_2025-01-01_to_2025-01-02.csv"
    partial = RAW / "nyc311_2025-01-01_to_2025-01-02.partial.csv"
    checkpoint = RAW / "checkpoint.json"
    offset = prepare_partial(partial, checkpoint, FIELDS)
    while True:
        page, _ = fetch_page(offset, args.page_size)
        if not page:
            break
        with partial.open("a", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
            writer.writerows(page)
            handle.flush()
            os.fsync(handle.fileno())
        offset += len(page)
        atomic_json_write(checkpoint, {"offset": offset})
        if len(page) < args.page_size:
            break
    os.replace(partial, output)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    manifest = {
        "dataset": "311 Service Requests from 2020 to Present",
        "dataset_id": "erm2-nwe9",
        "publisher": "NYC OpenData / NYC 311",
        "documentation": "https://dev.socrata.com/foundry/data.cityofnewyork.us/erm2-nwe9",
        "endpoint": ENDPOINT,
        "window_start_inclusive": START,
        "window_end_exclusive": END,
        "ordering": "created_date,unique_key",
        "rows": offset,
        "sha256": digest,
        "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "note": "URLs contain only public query parameters; raw records are unmodified API responses projected to listed fields.",
    }
    atomic_json_write(RAW / "source_manifest.json", manifest)
    checkpoint.unlink(missing_ok=True)
    print(f"wrote {offset} factual records; sha256={digest}")


if __name__ == "__main__":
    main()

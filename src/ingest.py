#!/usr/bin/env python3
"""Checkpointed ingestion of a fixed NYC 311 snapshot from the Socrata API."""
import argparse
import csv
import hashlib
import json
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
    checkpoint = RAW / "checkpoint.json"
    offset = 0
    rows = []
    source_urls = []
    if checkpoint.exists():
        state = json.loads(checkpoint.read_text())
        offset = state["offset"]
        if output.exists():
            with output.open(newline="") as handle:
                rows = list(csv.DictReader(handle))
    while True:
        page, url = fetch_page(offset, args.page_size)
        source_urls.append(url)
        if not page:
            break
        rows.extend(page)
        offset += len(page)
        with output.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        checkpoint.write_text(json.dumps({"offset": offset, "rows": len(rows)}, indent=2) + "\n")
        if len(page) < args.page_size:
            break
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
        "rows": len(rows),
        "sha256": digest,
        "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "note": "URLs contain only public query parameters; raw records are unmodified API responses projected to listed fields.",
    }
    (RAW / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    checkpoint.unlink(missing_ok=True)
    print(f"wrote {len(rows)} factual records; sha256={digest}")


if __name__ == "__main__":
    main()

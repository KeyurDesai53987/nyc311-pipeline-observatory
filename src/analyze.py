#!/usr/bin/env python3
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "nyc311_2025-01-01_to_2025-01-02.csv"
RESULTS = ROOT / "results"
PROCESSED = ROOT / "data" / "processed"


def dt(value):
    return datetime.fromisoformat(value) if value else None


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] if lower == upper else ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def main():
    with RAW.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    ids = [row["unique_key"] for row in rows]
    duplicate_ids = len(ids) - len(set(ids))
    invalid_created = 0
    closed_before_created = 0
    closure_hours = []
    by_agency = defaultdict(lambda: {"requests": 0, "closed": 0, "closure_hours": []})
    by_borough = Counter()
    by_complaint = Counter()
    missing = Counter()
    for row in rows:
        for field in ("agency", "complaint_type", "borough", "incident_zip", "latitude", "longitude"):
            if not row[field]:
                missing[field] += 1
        try:
            created = dt(row["created_date"])
        except ValueError:
            invalid_created += 1
            continue
        closed = dt(row["closed_date"])
        agency = row["agency"] or "UNKNOWN"
        by_agency[agency]["requests"] += 1
        by_borough[row["borough"] or "Unspecified"] += 1
        by_complaint[row["complaint_type"] or "Unspecified"] += 1
        if closed:
            hours = (closed - created).total_seconds() / 3600
            if hours < 0:
                closed_before_created += 1
            else:
                closure_hours.append(hours)
                by_agency[agency]["closed"] += 1
                by_agency[agency]["closure_hours"].append(hours)
    agency_rows = []
    for agency, values in by_agency.items():
        agency_rows.append({
            "agency": agency,
            "requests": values["requests"],
            "closed_with_valid_duration": values["closed"],
            "closure_rate": values["closed"] / values["requests"],
            "median_closure_hours": statistics.median(values["closure_hours"]) if values["closure_hours"] else "",
            "p90_closure_hours": percentile(values["closure_hours"], .9) if values["closure_hours"] else "",
        })
    agency_rows.sort(key=lambda item: item["requests"], reverse=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    with (PROCESSED / "agency_performance.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=agency_rows[0].keys())
        writer.writeheader(); writer.writerows(agency_rows)
    summary = {
        "records": len(rows),
        "unique_request_ids": len(set(ids)),
        "duplicate_request_ids": duplicate_ids,
        "invalid_created_timestamps": invalid_created,
        "closed_before_created": closed_before_created,
        "valid_closed_records": len(closure_hours),
        "overall_median_closure_hours": statistics.median(closure_hours),
        "overall_p90_closure_hours": percentile(closure_hours, .9),
        "missing_field_counts": dict(missing),
        "top_complaint_types": by_complaint.most_common(10),
        "borough_counts": by_borough.most_common(),
        "top_agencies": agency_rows[:10],
    }
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

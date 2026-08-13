# Design and decision record

## Source selection

NYC 311 was selected because the publisher documents the dataset, updates it daily, exposes stable request identifiers, and supplies timestamps, status, category, agency, and geography. The fixed interval `[2025-01-01, 2025-01-03)` makes the snapshot reproducible in scope even if the source later updates closure fields.

## Failure controls

| Risk | Implemented control |
|---|---|
| API interruption | bounded exponential retry |
| partial download | page-level checkpoint |
| unstable page order | explicit `created_date,unique_key` order |
| duplicate ingestion | unique-key measurement |
| upstream mutation | checked-in snapshot plus SHA-256 manifest |
| timestamp corruption | parsing and negative-duration checks |
| silent nulls | field-level missingness counts |
| misleading latency | median and p90, with semantic caveats |

Offset pagination is adequate for this immutable historical window. For a live, mutating interval, keyset pagination on `(created_date, unique_key)` plus a high-water mark would be safer because inserts can shift offsets.

## Observed issue

The first command-line query lost the Socrata `$where` parameter because the shell interpreted `$where` as a variable. The API rejected the remaining text as an unknown argument. Quoting the complete parameter preserved the literal field name. The production ingestion avoids shell interpolation entirely by encoding parameters in Python.

## Interpretation rules

This repository reports observations, not causal claims. Borough request volume does not measure population-adjusted need. Agency closure differences do not establish agency effectiveness. The selected dates include New Year's Day and must not be described as a typical period.

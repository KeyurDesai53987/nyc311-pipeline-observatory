import unittest
import csv
import json
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analyze import percentile
from ingest import prepare_partial


class AnalysisTests(unittest.TestCase):
    def test_percentile_interpolates_observed_numeric_values(self):
        self.assertEqual(percentile([1, 2, 3, 4], .5), 2.5)

    def test_empty_percentile_is_none(self):
        self.assertIsNone(percentile([], .9))

    def test_restart_rolls_back_page_not_committed_to_checkpoint(self):
        source = Path(__file__).resolve().parents[1] / "data" / "raw" / "nyc311_2025-01-01_to_2025-01-02.csv"
        with source.open(newline="") as handle:
            reader = csv.DictReader(handle)
            factual_rows = [next(reader), next(reader)]
            fields = reader.fieldnames
        with tempfile.TemporaryDirectory() as directory:
            partial = Path(directory) / "snapshot.partial.csv"
            checkpoint = Path(directory) / "checkpoint.json"
            with partial.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader(); writer.writerows(factual_rows)
            checkpoint.write_text(json.dumps({"offset": 1}))
            self.assertEqual(prepare_partial(partial, checkpoint, fields), 1)
            with partial.open(newline="") as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), 1)


if __name__ == "__main__":
    unittest.main()

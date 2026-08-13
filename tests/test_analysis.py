import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analyze import percentile


class AnalysisTests(unittest.TestCase):
    def test_percentile_interpolates_observed_numeric_values(self):
        self.assertEqual(percentile([1, 2, 3, 4], .5), 2.5)

    def test_empty_percentile_is_none(self):
        self.assertIsNone(percentile([], .9))


if __name__ == "__main__":
    unittest.main()

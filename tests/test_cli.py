import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def run_trace(self, content, *extra):
        with tempfile.TemporaryDirectory() as folder:
            trace = Path(folder) / "input.trace"
            trace.write_text(content, encoding="utf-8")
            return subprocess.run(
                [sys.executable, "-m", "cachelab", str(trace), "--size", "64",
                 "--line-size", "16", "--ways", "1", *extra],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )

    def test_json_output_matches_known_conflict_trace(self):
        result = self.run_trace("0\n64\n0\n64\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual((report["accesses"], report["hits"], report["evictions"]), (4, 0, 3))
        self.assertEqual(report["config"]["sets"], 4)

    def test_empty_file_is_valid(self):
        result = self.run_trace("# no references\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["hit_rate"], 0.0)

    def test_invalid_trace_has_line_number_and_no_partial_json(self):
        result = self.run_trace("0\n# blank\nbroken\n")
        self.assertEqual(result.returncode, 2)
        self.assertIn("line 3:", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_invalid_geometry_exits_nonzero(self):
        result = self.run_trace("0\n", "--ways", "8")
        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot exceed", result.stderr)

    def test_missing_file_is_reported_without_traceback(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run(
                [sys.executable, "-m", "cachelab", str(Path(folder) / "missing.trace")],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_comparison_contains_manually_derived_results(self):
        result = subprocess.run([sys.executable, "-m", "experiments.compare"],
                                cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = list(csv.DictReader(io.StringIO(result.stdout)))
        self.assertEqual([(r["scenario"], int(r["hits"]), int(r["misses"])) for r in rows],
                         [("conflict-direct", 0, 8), ("conflict-2way", 6, 2),
                          ("locality-direct", 14, 2), ("replacement-lru", 2, 3),
                          ("replacement-fifo", 1, 4)])
        expected = (ROOT / "examples" / "results.csv").read_text(encoding="utf-8")
        self.assertEqual(result.stdout, expected)


if __name__ == "__main__":
    unittest.main()

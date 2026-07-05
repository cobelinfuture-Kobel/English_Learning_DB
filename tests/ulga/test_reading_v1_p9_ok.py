from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ulga.builders.p9_make import make_ok, make_synthetic_ok
from ulga.validators.p9_ok import check_ok


class ReadingV1P9OkTests(unittest.TestCase):
    def test_synthetic_ok_passes_checker(self) -> None:
        report = check_ok(make_synthetic_ok())
        self.assertEqual(report["status"], "PASS", report)

    def test_ok_row_has_alignment_and_guards(self) -> None:
        row = make_synthetic_ok()
        self.assertEqual(row["q"], 3)
        self.assertEqual(row["k"], 3)
        self.assertTrue(row["aligned"])
        self.assertTrue(row["local_only"])
        self.assertFalse(row["public_ready"])

    def test_checker_blocks_empty_q(self) -> None:
        row = make_ok("qa", {"page_id": "p", "items": [], "keys": []})
        report = check_ok(row)
        self.assertIn("q", report["errors"])

    def test_checker_blocks_unaligned_keys(self) -> None:
        row = make_ok("qa", {"page_id": "p", "items": ["q1"], "keys": []})
        report = check_ok(row)
        self.assertIn("align", report["errors"])

    def test_checker_blocks_public_ready(self) -> None:
        row = make_synthetic_ok()
        row["public_ready"] = True
        report = check_ok(row)
        self.assertIn("public", report["errors"])


if __name__ == "__main__":
    unittest.main()

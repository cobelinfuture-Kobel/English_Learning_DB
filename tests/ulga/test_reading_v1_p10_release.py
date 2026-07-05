from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ulga.builders.p10_make import make_release, make_synthetic_release
from ulga.validators.p10_ok import check_ok


class ReadingV1P10ReleaseTests(unittest.TestCase):
    def test_synthetic_release_passes_checker(self) -> None:
        report = check_ok(make_synthetic_release())
        self.assertEqual(report["status"], "PASS", report)

    def test_release_has_required_guards(self) -> None:
        row = make_synthetic_release()
        self.assertTrue(row["local_user"])
        self.assertFalse(row["public_ready"])
        self.assertEqual(row["sample"], "p8_page_001")

    def test_checker_blocks_missing_guide(self) -> None:
        row = make_release("r", "", "p8_page_001")
        report = check_ok(row)
        self.assertIn("guide", report["errors"])

    def test_checker_blocks_missing_sample(self) -> None:
        row = make_release("r", "guide", "")
        report = check_ok(row)
        self.assertIn("sample", report["errors"])

    def test_checker_blocks_public_ready(self) -> None:
        row = make_synthetic_release()
        row["public_ready"] = True
        report = check_ok(row)
        self.assertIn("public", report["errors"])


if __name__ == "__main__":
    unittest.main()

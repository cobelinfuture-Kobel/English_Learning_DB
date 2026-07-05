from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ulga.builders.make_reading_v1_p6_source_units import make_source_unit, make_synthetic_source_units
from ulga.builders.p6_pack import pack
from ulga.validators.check_reading_v1_p6_source_unit import check_source_unit


class ReadingV1P6SourceUnitTests(unittest.TestCase):
    def test_synthetic_units_pass_checker(self) -> None:
        units = make_synthetic_source_units()
        reports = [check_source_unit(unit) for unit in units]
        self.assertEqual(len(units), 3)
        self.assertTrue(all(report["validator_status"] == "PASS" for report in reports), reports)

    def test_source_unit_has_required_guards(self) -> None:
        unit = make_source_unit("u1", "sentence", "The dog runs.", "A1", "animals", "literal_detail")
        self.assertTrue(unit["reviewed"])
        self.assertTrue(unit["local_only"])
        self.assertFalse(unit["public_ready"])

    def test_checker_blocks_invalid_source_type(self) -> None:
        unit = make_source_unit("u1", "poem", "The dog runs.", "A1", "animals", "literal_detail")
        report = check_source_unit(unit)
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("RV1_P6_SRC_ERR_TYPE", codes)

    def test_checker_blocks_public_ready(self) -> None:
        unit = make_source_unit("u1", "sentence", "The dog runs.", "A1", "animals", "literal_detail")
        unit["public_ready"] = True
        report = check_source_unit(unit)
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("RV1_P6_SRC_ERR_PUBLIC", codes)

    def test_pack_lists_source_unit_ids(self) -> None:
        units = make_synthetic_source_units()
        result = pack(units)
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["items"], ["p6_sentence_001", "p6_dialogue_001", "p6_passage_001"])


if __name__ == "__main__":
    unittest.main()

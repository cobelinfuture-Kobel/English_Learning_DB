from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ulga.builders.make_reading_v1_p7_question_items import make_question_item, make_synthetic_question_items
from ulga.builders.p7_pack import pack
from ulga.validators.check_reading_v1_p7_question_item import check_question_item


class ReadingV1P7QuestionItemTests(unittest.TestCase):
    def test_synthetic_items_pass_checker(self) -> None:
        items = make_synthetic_question_items()
        reports = [check_question_item(item) for item in items]
        self.assertEqual(len(items), 3)
        self.assertTrue(all(report["validator_status"] == "PASS" for report in reports), reports)

    def test_question_item_has_required_guards(self) -> None:
        item = make_question_item("q1", "u1", "literal_detail", "Where is it?", "on the desk")
        self.assertTrue(item["print_eligible"])
        self.assertTrue(item["local_only"])
        self.assertFalse(item["public_ready"])

    def test_checker_blocks_invalid_question_type(self) -> None:
        item = make_question_item("q1", "u1", "free_write", "Where is it?", "on the desk")
        report = check_question_item(item)
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("RV1_P7_Q_ERR_TYPE", codes)

    def test_checker_blocks_missing_answer(self) -> None:
        item = make_question_item("q1", "u1", "literal_detail", "Where is it?", "")
        report = check_question_item(item)
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("RV1_P7_Q_ERR_ANSWER", codes)

    def test_pack_lists_question_ids(self) -> None:
        items = make_synthetic_question_items()
        result = pack(items)
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["items"], ["p7_q_001", "p7_q_002", "p7_q_003"])
        self.assertTrue(result["print_ready"])


if __name__ == "__main__":
    unittest.main()

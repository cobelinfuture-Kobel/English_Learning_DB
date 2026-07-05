from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ulga.builders.make_reading_v1_p3_records import make_record, make_records, make_synthetic_record
from ulga.builders.make_reading_v1_p3_summary import make_summary
from ulga.validators.check_reading_v1_p3_record import check_record


def source_tag() -> dict:
    return {
        "item_id": "p2_item_001",
        "review_tag": "literal_detail_miss",
        "question_type": "literal_who",
        "pattern_family": "literal_comprehension",
    }


class ReadingV1P3LocalRecordTests(unittest.TestCase):
    def test_synthetic_record_passes_checker(self) -> None:
        report = check_record(make_synthetic_record())
        self.assertEqual(report["validator_status"], "PASS", report)
        self.assertEqual(report["summary"]["error_count"], 0)

    def test_builder_maps_source_tag_to_group(self) -> None:
        record = make_record(source_tag(), "p2_package_001")
        self.assertEqual(record["group_key"], "review_literal_detail")
        self.assertEqual(record["package_id"], "p2_package_001")

    def test_unknown_source_tag_uses_operator_group(self) -> None:
        source = source_tag()
        source["review_tag"] = "custom_local_tag"
        record = make_record(source, "p2_package_001")
        self.assertEqual(record["group_key"], "review_operator_needed")

    def test_checker_blocks_invalid_group(self) -> None:
        record = make_synthetic_record()
        record["group_key"] = "review_future_gap"
        report = check_record(record)
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("RV1_P3_REC_ERR_GROUP", codes)

    def test_builder_deep_copies_source(self) -> None:
        source = source_tag()
        record = make_record(source, "p2_package_001")
        source["question_type"] = "changed_after_build"
        self.assertEqual(record["source_copy"]["question_type"], "literal_who")

    def test_summary_counts_records(self) -> None:
        first = make_record(source_tag(), "p2_package_001")
        second_source = deepcopy(source_tag())
        second_source["item_id"] = "p2_item_002"
        second_source["review_tag"] = "unanswered"
        second = make_record(second_source, "p2_package_001")
        summary = make_summary("p2_package_001", [first, second], "local review")
        self.assertEqual(summary["item_count"], 2)
        self.assertEqual(summary["group_counts"]["review_literal_detail"], 1)
        self.assertEqual(summary["group_counts"]["review_unanswered"], 1)
        self.assertFalse(summary["public_ready"])
        self.assertFalse(summary["learner_state_write"])


if __name__ == "__main__":
    unittest.main()

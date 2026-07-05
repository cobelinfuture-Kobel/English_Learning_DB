from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ulga.builders.p8_make import make_card, make_synthetic_card
from ulga.builders.p8_pack import pack
from ulga.validators.p8_card import check_card


class ReadingV1P8CardTests(unittest.TestCase):
    def test_synthetic_card_passes_checker(self) -> None:
        report = check_card(make_synthetic_card())
        self.assertEqual(report["validator_status"], "PASS", report)

    def test_card_has_items_keys_and_guards(self) -> None:
        card = make_synthetic_card()
        self.assertEqual(len(card["items"]), 3)
        self.assertEqual(len(card["keys"]), 3)
        self.assertTrue(card["local_only"])
        self.assertFalse(card["public_ready"])

    def test_checker_blocks_empty_items(self) -> None:
        card = make_card("p", "title", [])
        report = check_card(card)
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("P8_ERR_ITEMS", codes)

    def test_checker_blocks_public_ready(self) -> None:
        card = make_synthetic_card()
        card["public_ready"] = True
        report = check_card(card)
        codes = {error["code"] for error in report["errors"]}
        self.assertIn("P8_ERR_PUBLIC", codes)

    def test_pack_lists_page_ids(self) -> None:
        result = pack([make_synthetic_card()])
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["items"], ["p8_page_001"])
        self.assertTrue(result["local_only"])


if __name__ == "__main__":
    unittest.main()

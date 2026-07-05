from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site" / "rv1"


class ReadingV1StaticSiteTests(unittest.TestCase):
    def test_static_files_exist(self) -> None:
        self.assertTrue((SITE / "index.html").is_file())
        self.assertTrue((SITE / "app.js").is_file())
        self.assertTrue((SITE / "style.css").is_file())
        self.assertTrue((SITE / "d.json").is_file())

    def test_index_has_buttons_and_targets(self) -> None:
        html = (SITE / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="loadBtn"', html)
        self.assertIn('id="toggleBtn"', html)
        self.assertIn('id="printBtn"', html)
        self.assertIn('id="sheet"', html)

    def test_app_prefers_local_api_and_falls_back_to_static_data(self) -> None:
        js = (SITE / "app.js").read_text(encoding="utf-8")
        self.assertIn("http://127.0.0.1:8781/api/pack?limit=10", js)
        self.assertIn("fetchJson('d.json')", js)
        self.assertIn("local-api", js)
        self.assertIn("window.print()", js)
        self.assertIn("showAnswers", js)

    def test_data_has_three_items(self) -> None:
        data = json.loads((SITE / "d.json").read_text(encoding="utf-8"))
        self.assertEqual(len(data["items"]), 3)
        self.assertTrue(all(item.get("q") and item.get("a") for item in data["items"]))

    def test_print_css_exists(self) -> None:
        css = (SITE / "style.css").read_text(encoding="utf-8")
        self.assertIn("@media print", css)
        self.assertIn(".actions { display: none; }", css)


if __name__ == "__main__":
    unittest.main()

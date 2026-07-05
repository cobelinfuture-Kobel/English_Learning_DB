from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.r2_http import HOST, run
from tools.r2_local import extract_text, levels, linked_texts, pack, probe, root, rows


class R2LocalTests(unittest.TestCase):
    def make_tree(self):
        tmp = tempfile.TemporaryDirectory()
        base = Path(tmp.name)
        level = base / "derived" / "Level_A"
        level.mkdir(parents=True)
        (level / "one.json").write_text(json.dumps({"source_text": "A cat sits."}), encoding="utf-8")
        return tmp, base

    def make_linked_tree(self):
        tmp = tempfile.TemporaryDirectory()
        base = Path(tmp.name)
        level = base / "Level_A"
        bridge = base / "bridge" / "reading_authority" / "Level_A"
        level.mkdir(parents=True)
        bridge.mkdir(parents=True)
        (level / "raz_A_1_audio_timeline_extract.json").write_text(
            json.dumps({"items": [{"sentence": "The fox jumps."}]}), encoding="utf-8"
        )
        (bridge / "candidate.json").write_text(
            json.dumps({"records": [{"source_traceability": {"path": "Level_A/raz_A_1_audio_timeline_extract.json"}}]}),
            encoding="utf-8",
        )
        return tmp, base

    def test_root_uses_value(self):
        tmp, base = self.make_tree()
        self.addCleanup(tmp.cleanup)
        self.assertEqual(root(str(base)), base.resolve())

    def test_levels_find_level_dirs(self):
        tmp, base = self.make_tree()
        self.addCleanup(tmp.cleanup)
        self.assertEqual(levels(base), ["Level_A"])

    def test_rows_read_json_only(self):
        tmp, base = self.make_tree()
        self.addCleanup(tmp.cleanup)
        result = rows(base)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["data"]["source_text"], "A cat sits.")

    def test_extract_text_reads_nested_lists(self):
        data = {"items": [{"book_title": "Book One"}, {"sentence": "The dog runs."}]}
        self.assertEqual(extract_text(data), ["Book One", "The dog runs."])

    def test_extract_text_uses_generic_natural_strings(self):
        data = {"items": [{"unknown_key": "A bird is in the tree."}, {"path": "a/b/c.json"}]}
        self.assertEqual(extract_text(data), ["A bird is in the tree."])

    def test_linked_texts_resolve_json_refs(self):
        tmp, base = self.make_linked_tree()
        self.addCleanup(tmp.cleanup)
        candidate = json.loads((base / "bridge" / "reading_authority" / "Level_A" / "candidate.json").read_text())
        self.assertEqual(linked_texts(base, candidate), ["The fox jumps."])

    def test_probe_reports_shape_and_texts(self):
        tmp, base = self.make_tree()
        self.addCleanup(tmp.cleanup)
        result = probe(base)
        self.assertEqual(result[0]["texts"], ["A cat sits."])
        self.assertIn("source_text", result[0]["shape"]["keys"])

    def test_pack_uses_linked_text_when_candidate_has_only_refs(self):
        tmp, base = self.make_linked_tree()
        self.addCleanup(tmp.cleanup)
        result = pack(base)
        qs = [item["q"] for item in result["items"]]
        self.assertIn("The fox jumps.", qs)

    def test_pack_is_local_and_read_only(self):
        tmp, base = self.make_tree()
        self.addCleanup(tmp.cleanup)
        result = pack(base)
        self.assertTrue(result["local_only"])
        self.assertTrue(result["read_only"])
        self.assertEqual(result["levels"], ["Level_A"])
        self.assertEqual(result["items"][0]["q"], "A cat sits.")
        self.assertIn("source", result["items"][0])

    def test_http_run_requires_localhost(self):
        self.assertEqual(HOST, "127.0.0.1")
        with self.assertRaises(ValueError):
            run(host="0.0.0.0", port=8782)


if __name__ == "__main__":
    unittest.main()

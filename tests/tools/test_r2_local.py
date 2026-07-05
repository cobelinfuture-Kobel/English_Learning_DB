from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.r2_http import HOST, run
from tools.r2_local import levels, pack, root, rows


class R2LocalTests(unittest.TestCase):
    def make_tree(self):
        tmp = tempfile.TemporaryDirectory()
        base = Path(tmp.name)
        level = base / "derived" / "Level_A"
        level.mkdir(parents=True)
        (level / "one.json").write_text(json.dumps({"source_text": "A cat sits."}), encoding="utf-8")
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

    def test_pack_is_local_and_read_only(self):
        tmp, base = self.make_tree()
        self.addCleanup(tmp.cleanup)
        result = pack(base)
        self.assertTrue(result["local_only"])
        self.assertTrue(result["read_only"])
        self.assertEqual(result["levels"], ["Level_A"])
        self.assertEqual(result["items"][0]["q"], "A cat sits.")

    def test_http_run_requires_localhost(self):
        self.assertEqual(HOST, "127.0.0.1")
        with self.assertRaises(ValueError):
            run(host="0.0.0.0", port=8782)


if __name__ == "__main__":
    unittest.main()

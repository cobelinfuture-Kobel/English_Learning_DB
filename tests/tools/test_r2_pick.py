from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.r2_pick import ok_text, pack, probe, texts


class R2PickTests(unittest.TestCase):
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
            json.dumps({
                "schema_version": "raz_reading_authority_bridge_contract.v1",
                "records": [{"source_traceability": {"path": "Level_A/raz_A_1_audio_timeline_extract.json"}}],
            }),
            encoding="utf-8",
        )
        return tmp, base

    def test_ok_text_blocks_schema_version(self):
        self.assertFalse(ok_text("raz_reading_authority_bridge_contract.v1"))
        self.assertTrue(ok_text("The fox jumps."))

    def test_texts_use_natural_strings_only(self):
        data = {"schema_version": "raz_reading_authority_bridge_contract.v1", "items": [{"sentence": "The fox jumps."}]}
        self.assertEqual(texts(data), ["The fox jumps."])

    def test_pack_prefers_linked_text_for_bridge_candidate(self):
        tmp, base = self.make_linked_tree()
        self.addCleanup(tmp.cleanup)
        result = pack(base)
        self.assertEqual(result["items"][0]["q"], "The fox jumps.")

    def test_probe_reports_linked_texts(self):
        tmp, base = self.make_linked_tree()
        self.addCleanup(tmp.cleanup)
        result = probe(base)
        self.assertEqual(result[0]["linked_texts"], ["The fox jumps."])


if __name__ == "__main__":
    unittest.main()

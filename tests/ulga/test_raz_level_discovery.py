from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ulga.builders import build_raz_level_discovery as discovery  # noqa: E402


class RazLevelDiscoveryTests(unittest.TestCase):
    def write_json(self, path: Path, data: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def write_jsonl(self, path: Path, rows: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
        path.write_text(payload + ("\n" if rows else ""), encoding="utf-8")

    def write_policy(self, path: Path, approved_levels: list[str]) -> None:
        self.write_json(
            path,
            {
                "approved_levels": approved_levels,
                "authority_status": "candidate_only",
                "promotion_allowed": False,
            },
        )

    def make_raw_payload(
        self,
        *,
        level: str,
        book_id: str = "1001",
        sentence_count: int = 2,
        page_count: int = 1,
        reuse_count: int = 1,
        include_clean_summary: bool = True,
    ) -> dict:
        sentence_candidates = [
            {
                "candidate_id": f"RAZ_{level}_{book_id}_CAND_{index:06d}",
                "page_unit_id": f"RAZ_{level}_{book_id}_P001",
                "cleaned_candidate": f"Sentence {index}.",
                "page_number": 1,
            }
            for index in range(1, sentence_count + 1)
        ]
        page_units = [
            {
                "page_unit_id": f"RAZ_{level}_{book_id}_P{index:03d}",
                "book_id": book_id,
                "level": level,
                "title": f"Book {level}",
                "page_number": index,
                "sentence_candidate_ids": [item["candidate_id"] for item in sentence_candidates],
                "sentence_count": sentence_count,
                "clean_text": " ".join(item["cleaned_candidate"] for item in sentence_candidates),
            }
            for index in range(1, page_count + 1)
        ]
        reuse_units = [
            {
                "reuse_unit_id": f"RAZ_{level}_{book_id}_REUSE_{index:06d}",
                "source_page_unit_id": page_units[0]["page_unit_id"] if page_units else None,
                "source_sentence_candidate_ids": [item["candidate_id"] for item in sentence_candidates],
                "book_id": book_id,
                "level": level,
                "title": f"Book {level}",
                "page_number": 1,
                "clean_text": " ".join(item["cleaned_candidate"] for item in sentence_candidates),
                "sentence_count": sentence_count,
            }
            for index in range(1, reuse_count + 1)
        ]
        payload = {
            "book_metadata": {
                "book_id": book_id,
                "level": level,
                "title": f"Book {level}",
                "story_page_start": 1,
                "story_page_end": max(1, page_count),
                "story_page_count": max(1, page_count),
                "min_story_page_number": 1,
                "allowed_text_types": ["story"],
            },
            "source_type": "raz_audio_timeline",
            "extraction_method": "bookAudioContent",
            "extractor_version": "test",
            "sentence_candidates": sentence_candidates,
            "page_units": page_units,
            "reuse_unit_candidates": reuse_units,
            "excluded_items": [],
            "legacy_story_sentences": [],
        }
        if include_clean_summary:
            payload["clean_summary"] = {"summary": f"Summary {level}"}
        return payload

    def make_enriched_sentence(self, level: str, authority_status: str = "candidate_only") -> dict:
        return {
            "candidate_id": f"RAZ_{level}_1001_CAND_000001",
            "source_page_unit_id": f"RAZ_{level}_1001_P001",
            "text": "I see a cat.",
            "source_tags": {"raz_level": level, "book_id": "1001", "page_unit_id": f"RAZ_{level}_1001_P001"},
            "content_unit_tags": {"content_unit_type": "sentence", "sentence_count": 1},
            "theme_tags": {"mapped_theme": "Animals"},
            "linguistic_tags": {"grammar_tags": []},
            "pedagogical_tags": {"skill_area": ["reading"], "question_type_candidates": ["reading_comprehension"]},
            "reuse_tags": {"reusability_tags": ["exercise_seed"]},
            "qa_tags": {"authority_status": authority_status, "final_eligible": False, "warnings": []},
        }

    def make_tree(self, base: Path) -> tuple[Path, Path]:
        raw_root = base / "raz_output_jsons"
        derived_root = raw_root / "derived"
        return raw_root, derived_root

    def test_discovery_with_multiple_ready_levels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw_root, derived_root = self.make_tree(Path(tmp))
            for level in ["A", "B"]:
                self.write_json(
                    raw_root / f"Level_{level}" / f"raz_{level}_1001_audio_timeline_extract.json",
                    self.make_raw_payload(level=level, sentence_count=3, page_count=2, reuse_count=1),
                )
            records = discovery.discover_raz_levels(raw_root=raw_root, derived_root=derived_root)
            statuses = {record["normalized_level"]: record["status"] for record in records}
            self.assertEqual(statuses["A"], discovery.READY_FOR_REUSE_UNIT_PIPELINE)
            self.assertEqual(statuses["B"], discovery.READY_FOR_REUSE_UNIT_PIPELINE)

    def test_discovery_with_partial_level(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw_root, derived_root = self.make_tree(Path(tmp))
            self.write_json(
                raw_root / "Level_C" / "raz_C_1001_audio_timeline_extract.json",
                self.make_raw_payload(level="C", sentence_count=0, page_count=0, reuse_count=0, include_clean_summary=False),
            )
            record = discovery.discover_raz_levels(raw_root=raw_root, derived_root=derived_root)[0]
            self.assertEqual(record["status"], discovery.PARTIAL_SOURCE_ONLY)
            self.assertIn("sentence_candidates", record["missing_artifacts"])

    def test_discovery_with_malformed_or_missing_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw_root, derived_root = self.make_tree(Path(tmp))
            malformed = raw_root / "Level_D" / "raz_D_1001_audio_timeline_extract.json"
            malformed.parent.mkdir(parents=True, exist_ok=True)
            malformed.write_text("{bad json", encoding="utf-8")
            record = discovery.discover_raz_levels(raw_root=raw_root, derived_root=derived_root)[0]
            self.assertEqual(record["status"], discovery.INVALID_FORMAT)
            self.assertTrue(record["skip_reasons"])

    def test_summary_count_consistency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw_root, derived_root = self.make_tree(Path(tmp))
            self.write_json(
                raw_root / "Level_A" / "raz_A_1001_audio_timeline_extract.json",
                self.make_raw_payload(level="A", sentence_count=2, page_count=1, reuse_count=1),
            )
            self.write_json(
                raw_root / "Level_B" / "raz_B_1001_audio_timeline_extract.json",
                self.make_raw_payload(level="B", sentence_count=0, page_count=0, reuse_count=0, include_clean_summary=False),
            )
            records = discovery.discover_raz_levels(raw_root=raw_root, derived_root=derived_root)
            summary = discovery.build_summary(records)
            counted_total = (
                summary["ready_level_count"]
                + summary["skipped_level_count"]
                + summary["partial_level_count"]
                + summary["invalid_level_count"]
                + summary["missing_required_input_count"]
            )
            self.assertEqual(counted_total, summary["total_detected_levels"])

    def test_candidate_only_and_promotion_invariants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw_root, derived_root = self.make_tree(Path(tmp))
            self.write_json(
                raw_root / "Level_E" / "raz_E_1001_audio_timeline_extract.json",
                self.make_raw_payload(level="E", sentence_count=1, page_count=1, reuse_count=1),
            )
            self.write_jsonl(
                derived_root / "Level_E" / "enriched" / "raz_E_sentence_enriched.jsonl",
                [self.make_enriched_sentence("E", authority_status="promoted")],
            )
            record = discovery.discover_raz_levels(raw_root=raw_root, derived_root=derived_root)[0]
            self.assertEqual(record["authority_status"], "candidate_only")
            self.assertFalse(record["promotion_allowed"])

    def test_no_crash_when_no_levels_are_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw_root, derived_root = self.make_tree(Path(tmp))
            records = discovery.discover_raz_levels(raw_root=raw_root, derived_root=derived_root)
            summary = discovery.build_summary(records)
            self.assertEqual(records, [])
            self.assertEqual(summary["total_detected_levels"], 0)
            self.assertEqual(summary["ready_level_count"], 0)

    def test_existing_known_levels_cdef_are_discoverable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw_root, derived_root = self.make_tree(Path(tmp))
            for level in ["C", "D", "E", "F"]:
                self.write_json(
                    raw_root / f"Level_{level}" / f"raz_{level}_1001_audio_timeline_extract.json",
                    self.make_raw_payload(level=level, sentence_count=1, page_count=1, reuse_count=0),
                )
            records = discovery.discover_raz_levels(raw_root=raw_root, derived_root=derived_root)
            discovered_levels = {record["normalized_level"] for record in records}
            self.assertTrue({"C", "D", "E", "F"} <= discovered_levels)

    def test_queryable_levels_respect_policy_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw_root, derived_root = self.make_tree(Path(tmp))
            for level in ["A", "G"]:
                self.write_json(
                    raw_root / f"Level_{level}" / f"raz_{level}_1001_audio_timeline_extract.json",
                    self.make_raw_payload(level=level, sentence_count=1, page_count=1, reuse_count=1),
                )
                self.write_jsonl(
                    derived_root / f"Level_{level}" / "enriched" / f"raz_{level}_sentence_enriched.jsonl",
                    [self.make_enriched_sentence(level)],
                )
                self.write_json(
                    derived_root / f"Level_{level}" / "enriched" / f"raz_{level}_page_unit_enriched.json",
                    [],
                )
                self.write_json(
                    derived_root / f"Level_{level}" / "enriched" / f"raz_{level}_reuse_unit_enriched.json",
                    [],
                )

            policy_path = Path(tmp) / "query_policy.json"
            self.write_policy(policy_path, ["A"])

            policy_levels = discovery.load_query_layer_policy_levels(policy_path)
            records = [
                discovery.inspect_level(
                    level,
                    raw_root=raw_root,
                    derived_root=derived_root,
                    query_layer_policy_levels=policy_levels,
                )
                for level in ["A", "G"]
            ]
            self.assertTrue(records[0]["query_layer_ready"])
            self.assertFalse(records[1]["query_layer_ready"])
            self.assertEqual(discovery.discover_queryable_levels(records=records), ["A"])


if __name__ == "__main__":
    unittest.main()

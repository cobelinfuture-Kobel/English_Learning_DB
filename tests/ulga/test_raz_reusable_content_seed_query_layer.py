from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ulga.query import raz_reusable_content_seed_query_layer as query_layer  # noqa: E402


class RazReusableContentSeedQueryLayerTests(unittest.TestCase):
    def write_json(self, path: Path, data: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def write_jsonl(self, path: Path, rows: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")

    def write_policy(self, base: Path, approved_levels: list[str]) -> None:
        path = base / "ulga" / "policies" / "raz_seed_query_layer_policy.json"
        self.write_json(
            path,
            {
                "approved_levels": approved_levels,
                "authority_status": "candidate_only",
                "promotion_allowed": False,
            },
        )

    def make_sentence(self, level: str = "A", theme: str = "Animals", warnings: list[str] | None = None) -> dict:
        return {
            "candidate_id": f"RAZ_{level}_1_CAND_000001",
            "source_page_unit_id": f"RAZ_{level}_1_P003",
            "text": "I see a cat.",
            "source_tags": {
                "source": "RAZ",
                "source_type": "raz_audio_timeline",
                "extraction_method": "bookAudioContent",
                "extractor_version": "raz_audio_timeline_to_content_authority_v3_story_filter",
                "raz_level": level,
                "book_id": "1",
                "book_title": "Cat Book",
                "page_number": 3,
                "page_unit_id": f"RAZ_{level}_1_P003",
                "candidate_id": f"RAZ_{level}_1_CAND_000001",
                "raw_file_path": f"raz_output_jsons/Level_{level}/raz_{level}_1_audio_timeline_extract.json",
            },
            "content_unit_tags": {
                "content_unit_type": "sentence",
                "sentence_authority_eligible": True,
                "is_story_sentence": True,
                "is_heading": False,
                "is_direct_speech": False,
                "is_question": False,
                "is_imperative": False,
                "sentence_count": 1,
            },
            "theme_tags": {
                "primary_theme": theme,
                "mapped_theme": theme,
                "subthemes": ["cat"],
                "theme_confidence": 0.9 if theme != "Unknown" else 0.25,
                "theme_source": "test",
            },
            "linguistic_tags": {
                "cefr_estimate": None,
                "raz_level": level,
                "grammar_tags": ["pronoun_subject", "present_simple"],
                "sentence_pattern_tags": ["simple_sentence_candidate"],
                "vocabulary_tags": [
                    {"word": "I", "normalized_word": "i", "pos": "pronoun", "lookup_status": "not_linked_in_s4"},
                    {"word": "cat", "normalized_word": "cat", "pos": "unknown", "lookup_status": "not_linked_in_s4"},
                ],
                "chunk_tags": [],
            },
            "pedagogical_tags": {
                "skill_area": ["reading", "vocabulary", "grammar", "listening"],
                "question_type_candidates": ["reading_comprehension", "fill_blank", "word_ordering", "dictation"],
                "exercise_seed": True,
                "assessment_seed": True,
            },
            "reuse_tags": {
                "is_reusable_unit": True,
                "reusability_tags": ["exercise_seed", "picture_prompt_seed", "vocabulary_exposure_seed"],
                "derivation_potential": {
                    "short_reading": "none",
                    "writing_model": "none",
                    "dialogue_rewrite": "none",
                    "exercise_generation": "possible",
                    "listening_audio": "possible",
                },
            },
            "qa_tags": {
                "authority_status": "candidate_only",
                "promotion_status": "not_promoted",
                "review_status": "pending",
                "tagging_status": "auto_tagged",
                "needs_human_review": False,
                "final_eligible": False,
                "warnings": warnings or [],
                "confidence": {"theme": 0.9},
            },
        }

    def make_page_unit(self, level: str = "F", heading: bool = False) -> dict:
        warnings = ["section_heading_detected"] if heading else []
        return {
            "page_unit_id": f"RAZ_{level}_1098_P003" if not heading else f"RAZ_{level}_836_P004",
            "book_id": "1098" if not heading else "836",
            "level": level,
            "title": "Does It Sink or Float?" if not heading else "Community Workers",
            "page_number": 3 if not heading else 4,
            "sentence_candidate_ids": [f"RAZ_{level}_1098_CAND_000001", f"RAZ_{level}_1098_CAND_000002"],
            "sentence_count": 4 if not heading else 2,
            "text": "Some things sink in water.\nSome things float in water." if not heading else "Introduction\nCommunity workers help people.",
            "source_tags": {
                "source": "RAZ",
                "source_type": "raz_audio_timeline",
                "extraction_method": "bookAudioContent",
                "extractor_version": "raz_audio_timeline_to_content_authority_v3_story_filter",
                "raz_level": level,
                "book_id": "1098" if not heading else "836",
                "book_title": "Does It Sink or Float?" if not heading else "Community Workers",
                "page_number": 3 if not heading else 4,
                "page_unit_id": f"RAZ_{level}_1098_P003" if not heading else f"RAZ_{level}_836_P004",
                "raw_file_path": f"raz_output_jsons/Level_{level}/raz_{level}_1098_audio_timeline_extract.json",
            },
            "authority_status": "candidate_only",
            "promotion_status": "not_promoted",
            "review_status": "pending",
            "content_unit_tags": {
                "content_unit_type": "multi_sentence_unit",
                "sentence_count": 4 if not heading else 2,
                "has_multi_sentence_unit": True,
                "has_direct_speech": False,
                "has_sequence": False,
                "has_heading": heading,
            },
            "theme_tags": {
                "primary_theme": "Science" if not heading else "Community",
                "mapped_theme": "Science" if not heading else "Community",
                "subthemes": ["physical_science"] if not heading else ["community"],
                "theme_confidence": 0.92,
                "theme_source": "test",
            },
            "pedagogical_tags": {
                "skill_area": ["reading", "vocabulary", "grammar", "comprehension", "retelling"],
                "question_type_candidates": ["reading_comprehension", "sentence_ordering", "retelling_prompt", "short_answer"],
                "exercise_seed": True,
                "assessment_seed": True,
            },
            "reuse_tags": {
                "is_reusable_unit": True,
                "reusability_tags": ["short_reading_seed", "sequencing_seed", "retelling_seed", "comprehension_question_seed", "exercise_seed"],
                "derivation_potential": {
                    "short_reading": "high",
                    "writing_model": "medium",
                    "dialogue_rewrite": "none",
                    "exercise_generation": "high",
                    "listening_audio": "unknown",
                },
            },
            "qa_tags": {
                "authority_status": "candidate_only",
                "promotion_status": "not_promoted",
                "review_status": "pending",
                "tagging_status": "auto_tagged",
                "needs_human_review": heading,
                "final_eligible": False,
                "warnings": warnings,
                "confidence": {"theme": 0.92},
            },
        }

    def make_reuse_unit(self) -> dict:
        page = self.make_page_unit(level="F", heading=False)
        page["reuse_unit_id"] = "RAZ_F_1098_REUSE_000001"
        page["source_page_unit_id"] = page.pop("page_unit_id")
        page["source_sentence_candidate_ids"] = page.pop("sentence_candidate_ids")
        page["reuse_tags"]["reusability_tags"].append("dialogue_rewrite_seed")
        page["reuse_tags"]["derivation_potential"]["dialogue_rewrite"] = "possible"
        page["content_unit_tags"]["has_direct_speech"] = True
        return page

    def make_derived_root(self, base: Path) -> Path:
        root = base / "raz_output_jsons" / "derived"
        for level in "ABCDEF":
            enriched = root / f"Level_{level}" / "enriched"
            enriched.mkdir(parents=True, exist_ok=True)
            sentences = [self.make_sentence(level=level, theme="Animals")]
            if level == "A":
                sentences.append(self.make_sentence(level=level, theme="Unknown", warnings=["unknown_theme"]))
            self.write_jsonl(enriched / f"raz_{level}_sentence_enriched.jsonl", sentences)
            pages = [self.make_page_unit(level=level, heading=False)]
            if level == "F":
                pages.append(self.make_page_unit(level=level, heading=True))
            self.write_json(enriched / f"raz_{level}_page_unit_enriched.json", pages)
            reuse_units = [self.make_reuse_unit()] if level == "F" else []
            self.write_json(enriched / f"raz_{level}_reuse_unit_enriched.json", reuse_units)
        return root

    def test_load_seed_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.write_policy(Path(tmp), list("ABCDEF"))
            root = self.make_derived_root(Path(tmp))
            cards = query_layer.load_seed_cards(root)
            self.assertGreaterEqual(len(cards), 12)
            self.assertTrue(query_layer.REQUIRED_SEED_CARD_FIELDS <= set(cards[0]))
            self.assertEqual(cards[0]["qa"]["authority_status"], "candidate_only")
            self.assertFalse(cards[0]["qa"]["final_eligible"])

    def test_short_reading_query_excludes_unknown_and_heading_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.write_policy(Path(tmp), list("ABCDEF"))
            root = self.make_derived_root(Path(tmp))
            response = query_layer.find_short_reading_seeds(limit=20, derived_root=root)
            self.assertNotIn("error", response)
            self.assertGreater(response["result_count"], 0)
            for card in response["results"]:
                self.assertNotEqual(card["theme"]["mapped_theme"], "Unknown")
                self.assertFalse(card["content_unit"].get("has_heading"))
                self.assertFalse(card["qa"].get("needs_human_review"))
                self.assertGreaterEqual(card["content_unit"].get("sentence_count"), 2)

    def test_exercise_seed_query_with_question_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.write_policy(Path(tmp), list("ABCDEF"))
            root = self.make_derived_root(Path(tmp))
            response = query_layer.find_exercise_seeds(
                {"question_type_candidates": ["word_ordering"], "levels": ["A"]},
                limit=10,
                derived_root=root,
            )
            self.assertNotIn("error", response)
            self.assertGreater(response["result_count"], 0)
            for card in response["results"]:
                self.assertEqual(card["source"]["raz_level"], "A")
                self.assertIn("word_ordering", card["pedagogy"]["question_type_candidates"])

    def test_theme_query_and_explain_seed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.write_policy(Path(tmp), list("ABCDEF"))
            root = self.make_derived_root(Path(tmp))
            response = query_layer.find_theme_seeds("Science", {"record_types": ["page_unit", "reuse_unit"]}, limit=5, derived_root=root)
            self.assertNotIn("error", response)
            self.assertGreater(response["result_count"], 0)
            seed_id = response["results"][0]["seed_id"]
            explained = query_layer.explain_seed(seed_id, derived_root=root)
            self.assertEqual(explained["result_count"], 1)
            self.assertEqual(explained["results"][0]["seed_id"], seed_id)
            self.assertIn("seed_score", explained["results"][0]["ranking"])

    def test_guardrails_reject_adaptive_and_generation_requests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.write_policy(Path(tmp), list("ABCDEF"))
            root = self.make_derived_root(Path(tmp))
            static_response = query_layer.query_reusable_content_seeds(
                {"query_type": "find_reusable_seeds", "static_only": False},
                derived_root=root,
            )
            self.assertEqual(static_response["error"]["code"], "STATIC_ONLY_REQUIRED")

            adaptive_response = query_layer.query_reusable_content_seeds(
                {"query_type": "find_reusable_seeds", "filters": {"learner_id": "james"}, "static_only": True},
                derived_root=root,
            )
            self.assertEqual(adaptive_response["error"]["code"], "ADAPTIVE_FIELD_REJECTED")

            generation_response = query_layer.query_reusable_content_seeds(
                {"query_type": "find_reusable_seeds", "filters": {"generate_exercise": True}, "static_only": True},
                derived_root=root,
            )
            self.assertEqual(generation_response["error"]["code"], "ADAPTIVE_FIELD_REJECTED")

    def test_include_unknown_theme_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.write_policy(Path(tmp), list("ABCDEF"))
            root = self.make_derived_root(Path(tmp))
            default_response = query_layer.find_reusable_seeds({"levels": ["A"]}, limit=50, derived_root=root)
            self.assertTrue(all(card["theme"]["mapped_theme"] != "Unknown" for card in default_response["results"]))

            include_response = query_layer.find_reusable_seeds({"levels": ["A"], "include_unknown_theme": True}, limit=50, derived_root=root)
            self.assertTrue(any(card["theme"]["mapped_theme"] == "Unknown" for card in include_response["results"]))
            self.assertIn("UNKNOWN_THEME_INCLUDED_BY_REQUEST", include_response["query_metadata"]["warnings"])

    def test_load_seed_cards_respects_query_layer_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.write_policy(base, list("ABCDEF"))
            root = base / "raz_output_jsons" / "derived"
            for level in ["A", "G"]:
                enriched = root / f"Level_{level}" / "enriched"
                enriched.mkdir(parents=True, exist_ok=True)
                self.write_jsonl(enriched / f"raz_{level}_sentence_enriched.jsonl", [self.make_sentence(level=level)])
                self.write_json(enriched / f"raz_{level}_page_unit_enriched.json", [])
                self.write_json(enriched / f"raz_{level}_reuse_unit_enriched.json", [])

            cards = query_layer.load_seed_cards(root)
            self.assertEqual({card["source"]["raz_level"] for card in cards}, {"A"})


if __name__ == "__main__":
    unittest.main()

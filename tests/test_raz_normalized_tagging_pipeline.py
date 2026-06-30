from __future__ import annotations

import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.raz_normalized_tagging_pipeline import (  # noqa: E402
    detect_heading,
    infer_content_unit_tags_for_sentence,
    infer_grammar_tags,
    infer_sentence_patterns,
    has_forbidden_audio_keys,
    is_narrow_imperative_sentence,
    infer_theme,
    run_pipeline,
)


class RazNormalizedTaggingPipelineTests(unittest.TestCase):
    def make_sample_raw(self) -> dict:
        return {
            "source_type": "raz_audio_timeline",
            "extraction_method": "bookAudioContent",
            "extractor_version": "raz_audio_timeline_to_content_authority_v3_story_filter",
            "book_metadata": {
                "level": "F",
                "book_id": "836",
                "title": "Community Workers",
                "story_page_start": 4,
                "story_page_end": 5,
                "story_page_count": 2,
                "allowed_text_types": ["text"],
                "min_story_page_number": 3,
            },
            "sentence_candidates": [
                {
                    "candidate_id": "RAZ_F_836_CAND_000001",
                    "page_unit_id": "RAZ_F_836_P004",
                    "level": "F",
                    "book_id": "836",
                    "title": "Community Workers",
                    "page_number": 4,
                    "candidate_order": 1,
                    "text_type": "text",
                    "cleaned_candidate": "Introduction",
                    "word_count": 1,
                    "source_traceability": {
                        "source_type": "raz_audio_timeline",
                        "generated_content": False,
                        "raw_audio_fields_preserved": True,
                    },
                    "authority_status": "candidate_only",
                    "promotion_status": "not_promoted",
                    "review_status": "pending",
                    "section_audio": "https://example.invalid/audio.mp3",
                    "audio_trace": {
                        "cue_start_ms": 100,
                        "cue_end_ms": 1040,
                    },
                    "word_trace": [
                        {
                            "word": "Introduction",
                            "cue_start_ms": 100,
                            "cue_end_ms": 1040,
                            "audio_url": "https://example.invalid/word.mp3",
                        }
                    ],
                },
                {
                    "candidate_id": "RAZ_F_836_CAND_000002",
                    "page_unit_id": "RAZ_F_836_P004",
                    "level": "F",
                    "book_id": "836",
                    "title": "Community Workers",
                    "page_number": 4,
                    "candidate_order": 2,
                    "text_type": "text",
                    "cleaned_candidate": "Community workers are people who work in a community.",
                    "word_count": 9,
                    "source_traceability": {
                        "source_type": "raz_audio_timeline",
                        "generated_content": False,
                        "raw_audio_fields_preserved": True,
                    },
                    "authority_status": "candidate_only",
                    "promotion_status": "not_promoted",
                    "review_status": "pending",
                    "section_audio": "https://example.invalid/audio.mp3",
                    "audio_trace": {
                        "cue_start_ms": 1820,
                        "cue_end_ms": 5260,
                    },
                    "word_trace": [
                        {
                            "word": "Community",
                            "cue_start_ms": 1820,
                            "cue_end_ms": 2370,
                            "audio_url": "https://example.invalid/community.mp3",
                        }
                    ],
                },
            ],
            "page_units": [
                {
                    "page_unit_id": "RAZ_F_836_P004",
                    "level": "F",
                    "book_id": "836",
                    "title": "Community Workers",
                    "page_number": 4,
                    "sentence_candidate_ids": [
                        "RAZ_F_836_CAND_000001",
                        "RAZ_F_836_CAND_000002",
                    ],
                    "sentence_count": 2,
                    "clean_text": "Introduction\nCommunity workers are people who work in a community.",
                }
            ],
            "reuse_unit_candidates": [
                {
                    "reuse_unit_id": "RAZ_F_836_REUSE_000001",
                    "source_page_unit_id": "RAZ_F_836_P004",
                    "level": "F",
                    "book_id": "836",
                    "title": "Community Workers",
                    "page_number": 4,
                    "source_sentence_candidate_ids": [
                        "RAZ_F_836_CAND_000001",
                        "RAZ_F_836_CAND_000002",
                    ],
                    "sentence_count": 2,
                    "clean_text": "Introduction\nCommunity workers are people who work in a community.",
                }
            ],
            "clean_summary": {},
            "excluded_items": [],
        }

    def test_heading_detection(self) -> None:
        self.assertTrue(detect_heading("Introduction"))
        self.assertTrue(detect_heading("Keeping People Healthy"))
        self.assertFalse(detect_heading("Lou is sick."))
        self.assertFalse(detect_heading("Who is this community worker?"))

    def test_theme_inference(self) -> None:
        theme = infer_theme("Lou is sick. He has the flu.", "Lou's Flu")
        self.assertEqual(theme["mapped_theme"], "Health")
        self.assertGreaterEqual(theme["theme_confidence"], 0.7)

    def test_theme_title_overrides(self) -> None:
        cases = [
            ("A Pet for Jupe", "Pets"),
            ("Spending Dimes One at a Time", "Money"),
            ("Double It!", "Math"),
            ("Changing Seasons", "Weather"),
            ("Trucking", "Transportation"),
            ("A Look at Fossils", "Science"),
            ("Taste This", "Body"),
            ("Getting Ready for School", "DailyRoutine"),
        ]
        for title, expected_theme in cases:
            with self.subTest(title=title):
                theme = infer_theme("", title)
                self.assertEqual(theme["mapped_theme"], expected_theme)
                self.assertEqual(theme["theme_source"], "title_override_map_v2")
                self.assertGreaterEqual(theme["theme_confidence"], 0.9)

    def test_s6p_p0_theme_title_mappings(self) -> None:
        cases = [
            ("Amazing Mummies", "Science"),
            ("Our Five Senses", "Body"),
            ("American Symbols", "Community"),
            ("Abigail Adams", "Community"),
            ("Miles the Nile Crocodile", "Animals"),
            ("Elephants: Giant Mammals", "Animals"),
            ("Rapunzel", "StoryFable"),
            ("The Empty Pot", "StoryFable"),
        ]
        for title, expected_theme in cases:
            with self.subTest(title=title):
                theme = infer_theme("", title)
                self.assertEqual(theme["mapped_theme"], expected_theme)
                self.assertEqual(theme["theme_source"], "title_override_map_v2")

    def test_s6p_p0_theme_does_not_misclassify_sports_as_civics(self) -> None:
        theme = infer_theme("", "American Football")
        self.assertNotEqual(theme["mapped_theme"], "Community")

    def test_s6s_p1_theme_updates_authorized_social_story_titles(self) -> None:
        theme = infer_theme("Billy is a puppy.", "Billy Gets Lost")
        self.assertEqual(theme["mapped_theme"], "Feelings")
        self.assertEqual(theme["theme_source"], "title_override_map_v2")

    def test_s6s_p1_theme_title_mappings(self) -> None:
        cases = [
            ("Rude Robot", "Feelings"),
            ("Cool as a Cuke", "Feelings"),
            ("Mystery Valentine", "Holidays"),
            ("Welcome to Turkey", "Travel"),
            ("Club Monster", "StoryFable"),
            ("Pip, the Monster Princess", "StoryFable"),
        ]
        for title, expected_theme in cases:
            with self.subTest(title=title):
                theme = infer_theme("", title)
                self.assertEqual(theme["mapped_theme"], expected_theme)
                self.assertEqual(theme["theme_source"], "title_override_map_v2")

    def test_s6p_p0_pattern_accepts_simple_svo(self) -> None:
        text = "He lives in a big house with a blue roof."
        patterns = infer_sentence_patterns(text, infer_content_unit_tags_for_sentence(text))
        self.assertIn("simple_declarative_svo", patterns)

    def test_s6p_p0_pattern_accepts_simple_svc(self) -> None:
        text = "Pizza was a big hit in the United States."
        patterns = infer_sentence_patterns(text, infer_content_unit_tags_for_sentence(text))
        self.assertIn("simple_declarative_svc", patterns)

    def test_s6p_p0_pattern_accepts_declarative_with_pp_expansion(self) -> None:
        text = "The great gray kangaroo has a pouch."
        patterns = infer_sentence_patterns(text, infer_content_unit_tags_for_sentence(text))
        self.assertIn("simple_declarative_svo", patterns)

    def test_s6p_p0_pattern_excludes_headings_dialogue_poetry_and_inversion(self) -> None:
        cases = [
            ("Introduction", None),
            ('"Do you know the way to my house?" Billy asks.', None),
            ("She had a ring at the end of her nose, her nose, her nose.", None),
            ("And there in the wood a piggy-wig stood.", None),
        ]
        for text, _expected in cases:
            with self.subTest(text=text):
                patterns = infer_sentence_patterns(text, infer_content_unit_tags_for_sentence(text))
                self.assertNotIn("simple_declarative_svo", patterns)
                self.assertNotIn("simple_declarative_svc", patterns)

    def test_s6s_p1_imperative_detection_is_narrow(self) -> None:
        self.assertTrue(is_narrow_imperative_sentence("Fill a small pot with soil."))
        self.assertTrue(is_narrow_imperative_sentence("Look around."))
        self.assertFalse(is_narrow_imperative_sentence("Run"))
        self.assertFalse(is_narrow_imperative_sentence("Look Out for the Spout", is_heading=True))

    def test_s6s_p1_imperative_adds_grammar_tag_without_heading_spillover(self) -> None:
        self.assertIn("imperative_procedural", infer_grammar_tags("Fill a small pot with soil."))
        self.assertIn("imperative_procedural", infer_grammar_tags("Don't forget to brush your teeth!"))
        self.assertNotIn("imperative_procedural", infer_grammar_tags("Step 3: See the Seedling"))
        self.assertNotIn("imperative_procedural", infer_grammar_tags("Run"))

    def test_pipeline_writes_derived_outputs_without_audio_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            raw_dir = tmp_path / "raz_output_jsons" / "Level_F"
            raw_dir.mkdir(parents=True)
            raw_file = raw_dir / "raz_F_836_audio_timeline_extract.json"
            raw_file.write_text(json.dumps(self.make_sample_raw(), ensure_ascii=False, indent=2), encoding="utf-8")

            output_root = tmp_path / "raz_output_jsons" / "derived"
            result, summary, validation = run_pipeline(
                input_root=tmp_path / "raz_output_jsons",
                output_root=output_root,
                levels=["F"],
                dry_run=False,
            )

            self.assertEqual(validation["status"], "PASS")
            self.assertEqual(summary["totals"]["sentence_enriched_count"], 2)
            self.assertEqual(summary["by_level"]["F"]["section_heading_candidate_count"], 1)
            self.assertTrue((output_root / "Level_F" / "enriched" / "raz_F_sentence_enriched.jsonl").exists())
            self.assertTrue((output_root / "reports" / "raz_tagging_summary.json").exists())

            enriched_records = [
                json.loads(line)
                for line in (output_root / "Level_F" / "enriched" / "raz_F_sentence_enriched.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertFalse(has_forbidden_audio_keys(enriched_records))
            heading = enriched_records[0]
            self.assertEqual(heading["content_unit_tags"]["content_unit_type"], "section_heading")
            self.assertFalse(heading["content_unit_tags"]["sentence_authority_eligible"])
            self.assertEqual(heading["qa_tags"]["authority_status"], "candidate_only")
            self.assertTrue(heading["qa_tags"]["needs_human_review"])
            self.assertGreaterEqual(len(result.warnings), 1)

            warning_report = json.loads((output_root / "reports" / "raz_tagging_warnings.json").read_text(encoding="utf-8"))
            warning_counter = Counter((row["record_id"], row["warning_type"]) for row in warning_report)
            warning_types = Counter(row["warning_type"] for row in warning_report)

            self.assertEqual(warning_types["section_heading_detected"], 1)
            self.assertEqual(warning_types["unknown_grammar"], 1)
            self.assertEqual(warning_types["unknown_pattern"], 0)
            self.assertEqual(warning_types["human_review_required"], 1)
            self.assertEqual(warning_types["unknown_theme"], 0)
            self.assertTrue(all(count == 1 for count in warning_counter.values()))

    def test_dry_run_does_not_write_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            raw_dir = tmp_path / "raz_output_jsons" / "Level_F"
            raw_dir.mkdir(parents=True)
            raw_file = raw_dir / "raz_F_836_audio_timeline_extract.json"
            raw_file.write_text(json.dumps(self.make_sample_raw(), ensure_ascii=False, indent=2), encoding="utf-8")

            output_root = tmp_path / "raz_output_jsons" / "derived"
            _result, summary, validation = run_pipeline(
                input_root=tmp_path / "raz_output_jsons",
                output_root=output_root,
                levels=["F"],
                dry_run=True,
            )

            self.assertEqual(validation["status"], "PASS")
            self.assertTrue(summary["dry_run"])
            self.assertFalse(output_root.exists())

    def test_default_level_discovery_respects_inventory_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            raw_root = tmp_path / "raz_output_jsons"
            output_root = raw_root / "derived"

            valid_dir = raw_root / "Level_F"
            valid_dir.mkdir(parents=True)
            (valid_dir / "raz_F_836_audio_timeline_extract.json").write_text(
                json.dumps(self.make_sample_raw(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            invalid_dir = raw_root / "Level_BAD"
            invalid_dir.mkdir(parents=True)
            (invalid_dir / "raz_BAD_1001_audio_timeline_extract.json").write_text(
                json.dumps(self.make_sample_raw(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            result, summary, validation = run_pipeline(
                input_root=raw_root,
                output_root=output_root,
                levels=None,
                dry_run=True,
            )

            self.assertEqual(validation["status"], "PASS")
            self.assertEqual(result.raw_files_seen, 1)
            self.assertEqual(list(summary["by_level"].keys()), ["F"])


if __name__ == "__main__":
    unittest.main()

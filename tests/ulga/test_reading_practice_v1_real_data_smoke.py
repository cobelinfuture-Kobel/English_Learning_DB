import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.audits import audit_reading_practice_v1_real_data_smoke as smoke
from ulga.builders import build_reading_candidate_items as item_builder

AUDIT_PATH = BASE_DIR / "ulga" / "audits" / "audit_reading_practice_v1_real_data_smoke.py"


def source_item(intake_id, text, source_type="sentence_candidate", sentence_count=1):
    return {
        "intake_id": intake_id,
        "source_type": source_type,
        "level": "A",
        "book_id": "RAZ_A_TEST_BOOK",
        "page_number": 1,
        "sentence_count": sentence_count,
        "clean_text": text,
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
        "generated_content": False,
        "source_traceability": {
            "source_type": source_type,
            "source_path": "tests/fixtures/raz_a_test.json",
            "source_record_id": f"{intake_id}_SRC",
            "generated_content": False,
        },
        "query_tags": {
            "theme_hints": ["Test"],
            "grammar_tags": [],
            "pattern_tags": [],
            "vocabulary_tags": [],
            "reusability_tags": ["exercise_seed"],
        },
    }


def smoke_index_payload():
    items = [
        source_item("SRC_WHO", "The boy runs."),
        source_item("SRC_WHAT", "The girl has a kite."),
        source_item("SRC_WHERE", "The cat is on the bed."),
        source_item("SRC_CLOZE", "I eat rice."),
        source_item("SRC_ORDER", "I get up.\nI eat breakfast.\nI go to school.", "page_unit", 3),
    ]
    summary = {
        "schema_version": "RAZ_READING_AUTHORITY_INTAKE_QUERY_INDEX_SUMMARY_V1",
        "status": "PASS",
        "total_items": len(items),
    }
    return {
        "schema_version": "RAZ_READING_AUTHORITY_INTAKE_QUERY_INDEX_V1",
        "items": items,
        "summary": summary,
    }


def test_real_data_smoke_reports_blocked_when_s11_inputs_absent(tmp_path):
    result = smoke.run_smoke(
        index_path=tmp_path / "missing_index.json",
        index_summary_path=tmp_path / "missing_summary.json",
        limit_per_question_type=1,
    )
    assert result["status"] == "BLOCKED_INPUT_ABSENT"
    assert result["decision"] == "REAL_DATA_SMOKE_NOT_RUN"
    assert result["generated_items"] == 0


def test_real_data_smoke_passes_against_s11_shaped_fixture(tmp_path):
    payload = smoke_index_payload()
    index_path = tmp_path / "raz_reading_authority_intake_query_index.json"
    summary_path = tmp_path / "raz_reading_authority_intake_query_index_summary.json"
    index_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    summary_path.write_text(json.dumps(payload["summary"], ensure_ascii=False), encoding="utf-8")

    result = smoke.run_smoke(index_path=index_path, index_summary_path=summary_path, limit_per_question_type=1)
    assert result["status"] == "PASS"
    assert result["decision"] == "REAL_DATA_SMOKE_PASS"
    assert result["generated_items"] == 6
    assert result["package_items"] == 6
    assert result["promoted_count"] == 0
    assert result["learner_facing_count"] == 0
    assert set(result["by_question_type"]) == set(item_builder.QUESTION_TYPES)


def test_real_data_smoke_fails_when_real_index_generates_no_items(tmp_path):
    payload = {
        "schema_version": "RAZ_READING_AUTHORITY_INTAKE_QUERY_INDEX_V1",
        "items": [source_item("SRC_NO_FEATURE", "Blue.")],
        "summary": {"schema_version": "RAZ_READING_AUTHORITY_INTAKE_QUERY_INDEX_SUMMARY_V1", "total_items": 1},
    }
    index_path = tmp_path / "index.json"
    summary_path = tmp_path / "summary.json"
    index_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    summary_path.write_text(json.dumps(payload["summary"], ensure_ascii=False), encoding="utf-8")

    result = smoke.run_smoke(index_path=index_path, index_summary_path=summary_path, limit_per_question_type=1)
    assert result["status"] == "FAIL"
    assert "real_data_generated_items_zero" in result["errors"]


def test_real_data_smoke_direct_cli_missing_input_is_non_failure(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(AUDIT_PATH),
            "--index",
            str(tmp_path / "missing_index.json"),
            "--index-summary",
            str(tmp_path / "missing_summary.json"),
        ],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Reading System V1 real-data smoke: BLOCKED_INPUT_ABSENT" in result.stdout
    assert "Decision: REAL_DATA_SMOKE_NOT_RUN" in result.stdout

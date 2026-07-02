import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


from ulga.audits.audit_raz_reading_authority_intake_query_index_readback import (
    SOURCE_CANDIDATE_PATH,
    analyze_index_payload,
    analyze_source_candidate_payload,
    build_findings,
    classify_warning_groups,
)


def test_classify_warning_groups_splits_bridge_and_derived():
    warnings = [
        "no_candidate_records_found:raz_output_jsons/bridge/reading_authority/Level_A/file.json",
        "no_candidate_records_found:raz_output_jsons/derived/Level_A/file.json",
        "source_parse_skipped:other.json",
    ]
    assert classify_warning_groups(warnings) == {
        "bridge_candidate_artifact": 1,
        "derived_artifact": 1,
        "other": 1,
    }


def test_analyze_source_candidate_payload_reads_levels_and_ids():
    payload = {
        "records": [
            {"source_level": "A", "reading_intake_id": "id-1"},
            {"normalized_level": "B", "reading_intake_id": "id-2"},
            {"source_level": "C"},
        ]
    }
    analysis = analyze_source_candidate_payload(payload)
    assert analysis["record_count"] == 3
    assert analysis["source_levels"] == {"A": 1, "B": 1, "C": 1}
    assert analysis["missing_source_level_count"] == 0
    assert analysis["missing_reading_intake_id_count"] == 1


def test_build_findings_detects_s10a_unknown_level_drop_and_bad_tags():
    index_payload = {
        "items": [
            {
                "level": "UNKNOWN",
                "authority_status": "candidate_only",
                "promotion_status": "not_promoted",
                "generated_content": False,
                "source_traceability": {
                    "source_path": "ulga/graph/raz_reading_authority_intake_candidates.json",
                    "source_record_id": None,
                },
                "query_tags": {"reusability_tags": ["{'bad': 'tag'}"]},
            },
            {
                "level": "UNKNOWN",
                "authority_status": "candidate_only",
                "promotion_status": "not_promoted",
                "generated_content": False,
                "source_traceability": {
                    "source_path": "ulga/graph/raz_reading_authority_intake_candidates.json",
                    "source_record_id": None,
                },
                "query_tags": {"reusability_tags": []},
            },
        ]
    }
    index_analysis = analyze_index_payload(index_payload)
    source_analysis = analyze_source_candidate_payload(
        {
            "records": [
                {"source_level": "A", "reading_intake_id": "rid-1"},
                {"source_level": "B", "reading_intake_id": "rid-2"},
            ]
        }
    )
    findings = build_findings(
        index_analysis=index_analysis,
        summary_payload={
            "total_items": 2,
            "warnings": [
                "no_candidate_records_found:raz_output_jsons/derived/Level_A/file.json",
            ],
        },
        source_analysis=source_analysis,
    )
    codes = {finding["code"] for finding in findings}
    assert "S10A_SOURCE_LEVELS_DROPPED" in codes
    assert "MALFORMED_REUSABILITY_TAGS" in codes
    assert "SOURCE_RECORD_ID_NOT_PROPAGATED" in codes
    assert "WARNING_SCOPE_NOT_BRIDGE_ONLY" in codes


def test_analyze_index_payload_counts_candidate_only_and_unknown_items():
    analysis = analyze_index_payload(
        {
            "items": [
                {
                    "level": "A",
                    "authority_status": "candidate_only",
                    "promotion_status": "not_promoted",
                    "generated_content": False,
                    "source_traceability": {"source_path": "a.json", "source_record_id": "1"},
                    "query_tags": {"reusability_tags": []},
                },
                {
                    "level": "UNKNOWN",
                    "authority_status": "candidate_only",
                    "promotion_status": "not_promoted",
                    "generated_content": False,
                    "source_traceability": {"source_path": "b.json", "source_record_id": None},
                    "query_tags": {"reusability_tags": []},
                },
            ]
        }
    )
    assert analysis["total_items"] == 2
    assert analysis["candidate_only_count"] == 2
    assert analysis["promoted_count"] == 0
    assert analysis["generated_content_count"] == 0
    assert analysis["unknown_items"] == 1
    assert analysis["unknown_ratio"] == 0.5

import json
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_DIR = os.path.join(BASE_DIR, "chunk_profile", "json")
REPORT_DIR = os.path.join(BASE_DIR, "chunk_profile", "reports")

CHUNKS_PATH = os.path.join(JSON_DIR, "chunks.json")
CHUNKS_WITH_EVIDENCE_PATH = os.path.join(JSON_DIR, "chunks_with_evidence.json")
RECLASSIFIED_GROUPS_PATH = os.path.join(JSON_DIR, "chunk_duplicate_groups_reclassified.json")
REVIEW_CANDIDATES_PATH = os.path.join(JSON_DIR, "chunk_exact_duplicate_review_candidates.json")
SENSE_INDEX_PATH = os.path.join(JSON_DIR, "chunk_sense_signature_index.json")
POLICY_PATH = os.path.join(JSON_DIR, "chunk_evidence_policy.json")
REPORT_PATH = os.path.join(REPORT_DIR, "chunk_duplicate_evidence_recovery_report.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_evidence_outputs_exist_and_are_valid_json():
    for path in [
        CHUNKS_WITH_EVIDENCE_PATH,
        RECLASSIFIED_GROUPS_PATH,
        REVIEW_CANDIDATES_PATH,
        SENSE_INDEX_PATH,
        POLICY_PATH,
        REPORT_PATH,
    ]:
        assert os.path.exists(path), f"Missing output: {path}"
        load_json(path)


def test_chunks_with_evidence_preserves_chunk_count_and_ids():
    chunks = load_json(CHUNKS_PATH)
    enriched = load_json(CHUNKS_WITH_EVIDENCE_PATH)
    assert len(enriched) == len(chunks)
    assert [item["id"] for item in enriched] == [item["id"] for item in chunks]


def test_every_chunk_has_source_evidence_fields():
    enriched = load_json(CHUNKS_WITH_EVIDENCE_PATH)
    required = {
        "evidence_status",
        "source_row_index",
        "matched_row_candidates",
        "raw_base_word",
        "raw_guideword",
        "raw_level",
        "raw_part_of_speech",
        "raw_topic",
        "raw_details",
        "raw_row_fields",
        "row_signature",
        "sense_signature",
    }
    for item in enriched:
        evidence = item.get("source_evidence")
        assert evidence, f"{item['id']} missing source_evidence"
        assert required.issubset(evidence.keys())
        assert evidence["evidence_status"] in {"matched", "ambiguous_match", "unmatched"}


def test_matched_chunks_have_row_index_and_signatures():
    enriched = load_json(CHUNKS_WITH_EVIDENCE_PATH)
    for item in enriched:
        evidence = item["source_evidence"]
        if evidence["evidence_status"] != "unmatched":
            assert isinstance(evidence["source_row_index"], int)
            assert evidence["row_signature"]
            assert evidence["sense_signature"]
            assert evidence["source_row_index"] in evidence["matched_row_candidates"]


def test_reclassified_groups_preserve_group_count():
    original = load_json(os.path.join(JSON_DIR, "chunk_duplicate_groups.json"))
    reclassified = load_json(RECLASSIFIED_GROUPS_PATH)
    assert len(reclassified) == len(original)


def test_reclassified_groups_have_recovery_fields():
    groups = load_json(RECLASSIFIED_GROUPS_PATH)
    for group in groups:
        assert "recovered_classification" in group
        assert "evidence_risk" in group
        assert "source_row_indexes" in group
        assert "sense_signature_count" in group


def test_review_candidates_are_review_risk_groups():
    candidates = load_json(REVIEW_CANDIDATES_PATH)
    for group in candidates:
        assert group["evidence_risk"] == "review"
        assert group["recovered_classification"] in {
            "confirmed_exact_duplicate",
            "evidence_incomplete_review",
        }


def test_sense_signature_index_ids_exist():
    chunks = load_json(CHUNKS_WITH_EVIDENCE_PATH)
    valid_ids = {chunk["id"] for chunk in chunks}
    index = load_json(SENSE_INDEX_PATH)
    assert index
    for ids in index.values():
        assert set(ids).issubset(valid_ids)


def test_evidence_policy_is_additive_and_non_destructive():
    policy = load_json(POLICY_PATH)
    assert policy["rules"]["do_not_delete_duplicates"] is True
    assert policy["rules"]["do_not_modify_cefr"] is True
    assert policy["rules"]["source_evidence_is_additive"] is True


def test_report_verdict_is_not_fail():
    report = load_json(REPORT_PATH)
    assert report["verdict"] in {"PASS", "WARNING"}
    assert report["unmatched_total"] == 0

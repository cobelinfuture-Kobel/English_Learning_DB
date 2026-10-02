from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "ulga" / "contracts" / "a1fs_v1_u06_q02_vocabulary_carrier_authority.json"
Q01 = ROOT / "ulga" / "contracts" / "a1fs_v1_u06_q01_canonical_target_gap_projection.json"
U05_Q02 = ROOT / "ulga" / "contracts" / "a1fs_v1_u05_q02_vocabulary_carrier_authority.json"
CP02 = ROOT / "ulga" / "reports" / "a1fs_v1_cp02_per_unit_authority_bindings.json"
VOCAB_NODES = ROOT / "ulga" / "graph" / "vocabulary_nodes.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _bucket(status: str) -> str:
    if status.startswith("BLOCKED_"):
        return "BLOCKED"
    if status.startswith("REVIEW_REQUIRED"):
        return "REVIEW_REQUIRED"
    return "ADMITTED"


def _find_u06(node):
    if isinstance(node, dict):
        if node.get("grammar_unit_id") == "GRAMMAR_CAN_STATEMENT" and "authority_bindings" in node:
            return node
        for value in node.values():
            found = _find_u06(value)
            if found:
                return found
    elif isinstance(node, list):
        for value in node:
            found = _find_u06(value)
            if found:
                return found
    return None


def test_u06_q02_vocabulary_carrier_authority() -> None:
    data = _load(ARTIFACT)
    q01 = _load(Q01)
    u05 = _load(U05_Q02)
    cp02 = _load(CP02)
    vocab_nodes = _load(VOCAB_NODES)

    assert data["status"] == "PASS_A1FS_V1_U06Q02_VOCABULARY_AUTHORITY_AND_REUSABLE_CARRIER_ADMISSION"
    assert data["unit_number"] == 6
    assert data["unit_id"] == "GRAMMAR_CAN_STATEMENT"
    assert q01["teaching_activation"]["direct_teaching_target_row_count"] == 2
    assert q01["routing_amendment"]["outstanding_teaching_obligation_count"] == 10

    u06 = _find_u06(cp02)
    assert u06 is not None
    seed_refs = u06["authority_bindings"]["vocabulary"]["selected_refs"]
    assert len(seed_refs) == 12
    assert u06["authority_bindings"]["vocabulary"]["allowed_pool_count"] == 784

    admitted_u05 = [
        row for row in u05["matrix"]
        if _bucket(row["unit05_admission_status"]) == "ADMITTED"
    ]
    assert len(admitted_u05) == 106

    reusable_map = {
        "NOUN": "OBJECT",
        "PERSON": "SUBJECT_OR_PERSON",
        "ROLE": "SUBJECT_OR_PERSON",
        "ACTION_SUPPORT": "ACTION_VERB",
        "PLACE": "PLACE",
    }
    reusable_u05 = [row for row in admitted_u05 if row["carrier_class"] in reusable_map]
    excluded_u05 = [row for row in admitted_u05 if row["carrier_class"] not in reusable_map]
    assert len(reusable_u05) == 83
    assert len(excluded_u05) == 23
    assert {row["carrier_class"] for row in excluded_u05} == {"ADJECTIVE", "AGE_STATE"}

    vocab_by_source_id = {
        row["metadata"]["source_vocabulary_id"]: row
        for row in vocab_nodes
        if row.get("metadata", {}).get("source_vocabulary_id")
    }
    seed_ids = {ref.rsplit(":", 1)[1] for ref in seed_refs}
    reusable_ids = {row["canonical_vocab_id"] for row in reusable_u05}
    assert len(seed_ids & reusable_ids) == 4
    assert len(seed_ids - reusable_ids) == 8
    assert all(seed_id in vocab_by_source_id for seed_id in seed_ids)

    rows = data["matrix"]
    assert len(rows) == 91
    assert len({row["canonical_vocab_id"] for row in rows}) == 91
    assert {row["canonical_vocab_id"] for row in rows} == reusable_ids | seed_ids

    by_class = data["summary"]["by_carrier_class"]
    assert by_class["SUBJECT_OR_PERSON"]["admitted_identity_count"] == 21
    assert by_class["ACTION_VERB"]["admitted_identity_count"] == 15
    assert by_class["OBJECT"]["admitted_identity_count"] == 25
    assert by_class["ACTIVITY_COMPLEMENT"]["admitted_identity_count"] == 0
    assert by_class["PLACE"]["admitted_identity_count"] == 29
    assert by_class["MANNER_OR_SUPPORT"]["admitted_identity_count"] == 1

    expected_seed_surfaces = {
        "I", "she", "they", "we", "make", "book",
        "run", "read", "fast", "sister", "ride", "swim",
    }
    actual_seed_surfaces = {row["surface"] for row in rows if row["unit06_seed_ref"]}
    assert actual_seed_surfaces == expected_seed_surfaces

    for row in rows:
        canonical = vocab_by_source_id[row["canonical_vocab_id"]]
        assert row["vocabulary_ref"] == canonical["id"]
        assert row["surface"] == canonical["label"]
        assert row["canonical_cefr_level"] == canonical["cefr_level"]
        assert row["canonical_part_of_speech"] == canonical["metadata"]["part_of_speech"]
        assert row["actual_unit06_learner_usage_claimed"] is False

    a2_rows = [row for row in rows if row["canonical_cefr_level"] == "A2"]
    assert len(a2_rows) == 5
    assert {row["surface"] for row in a2_rows} == {
        "bus stop", "library", "market", "playground", "sports centre"
    }
    assert all("U05_Q02_EXACT_ADMITTED_REUSE" in row["source_roles"] for row in a2_rows)

    summary = data["summary"]
    assert summary["predecessor_u05_admitted_identity_count"] == 106
    assert summary["predecessor_u05_reusable_identity_count"] == 83
    assert summary["predecessor_u05_not_reused_identity_count"] == 23
    assert summary["unit06_authority_seed_identity_count"] == 12
    assert summary["seed_overlap_with_u05_reusable_count"] == 4
    assert summary["seed_only_existing_global_identity_count"] == 8
    assert summary["admitted_identity_count"] == 91
    assert summary["new_global_vocabulary_identity_count"] == 0
    assert summary["new_to_predecessor_carrier_pool_identity_count"] == 8
    assert summary["a2_prior_authority_override_reuse_count"] == 5
    assert summary["new_a2_identity_admission_count"] == 0
    assert summary["actual_unit06_learner_usage_rate"] is None

    boundaries = data["claim_boundaries"]
    assert boundaries["all_91_are_existing_global_vocabulary_identities"] is True
    assert boundaries["zero_new_global_vocabulary_identities"] is True
    assert boundaries["no_new_a2_a2plus_admission"] is True
    assert boundaries["q02_carrier_admission_does_not_claim_q06_sentence_usage"] is True
    assert boundaries["q02_does_not_activate_any_of_q01_future_owner_rows"] is True
    assert boundaries["allowed_pool_784_is_not_unit06_admitted_pool"] is True
    assert boundaries["activity_complement_zero_at_lexical_identity_level_is_intentional"] is True

    scope = data["scope"]
    assert scope["future_owner_routed_rows_excluded_from_q02"] == 10
    assert scope["learner_facing_sentence_generation"] is False
    assert scope["q03_form_meaning_materialized"] is False
    assert scope["q04_chunk_materialized"] is False
    assert scope["q05_frame_materialized"] is False
    assert scope["q06_sentence_assets_materialized"] is False
    assert scope["a2_a2plus_unlocked"] is False

    assert data["next_short_step"] == "A1FS-V1-U06Q03_Unit06CanFormMeaningBoundaryAuthority"

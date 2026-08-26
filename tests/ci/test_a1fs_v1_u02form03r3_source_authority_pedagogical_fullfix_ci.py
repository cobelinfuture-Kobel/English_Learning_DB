from collections import Counter
from functools import lru_cache

from ulga.builders import _a1fs_v1_u02form03r3_global_distinct_base as r3_base
from ulga.builders import (
    build_a1fs_v1_u02form01_unit02_existing_learner_renderer_reuse_and_16x40_deterministic_form_materialization
    as form01,
)
from ulga.builders import (
    build_a1fs_v1_u02form03r3_source_authority_pedagogical_fullfix_and_global_distinct_runtime
    as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u02form03r3_source_authority_pedagogical_fullfix
    as validator,
)


@lru_cache(maxsize=1)
def _payload():
    return builder.build_export_payload()


@lru_cache(maxsize=1)
def _baseline():
    return r3_base.build_export_payload()


def _identity(rows):
    return [{
        "slot_id": row["slot_id"],
        "runtime_occurrence_id": row["runtime_occurrence_id"],
        "selected_item_id": row["selected_item_id"],
        "candidate_ids": list(row["candidate_ids"]),
        "learner_support_note": row["learner_support_note"],
        "visible_signature": row["visible_signature"],
        "effective_signature": row["effective_signature"],
        "runtime_semantic_signature": row["runtime_semantic_signature"],
    } for row in rows if int(row["form_number"]) <= 12]


def test_r4r1_preserves_q01_q08_and_forms01_12_runtime_identity_exactly():
    baseline = _baseline()
    payload = _payload()
    for key in builder._Q1_Q8_KEYS:
        assert payload[key] == baseline[key]
    assert payload["q01_q08_preservation"]["preserved"] is True

    before = baseline["q10_questionbank_capacity_runtime"]["runtime_occurrences"]
    after = payload["q10_questionbank_capacity_runtime"]["runtime_occurrences"]
    assert _identity(before) == _identity(after)
    proof = payload["forms01_12_runtime_identity_preservation"]
    assert proof["preserved"] is True
    assert proof["runtime_occurrence_count"] == 480
    assert proof["baseline_sha256"] == proof["r4r1_sha256"]


def test_r4r1_adds_exact_160_transfer_items_and_cuts_over_only_forms13_16():
    q10 = _payload()["q10_questionbank_capacity_runtime"]
    assert q10["inventory_summary"]["unit02_approved_item_count"] == builder.EXPECTED_UNIT02_APPROVED_ITEMS
    assert q10["inventory_summary"]["r4r1_transfer_stage_policy_bound_items"] == builder.R4R1_TRANSFER_ITEM_COUNT == 160

    r4_items = [row for row in q10["unit02_approved_items"] if row["item_id"].startswith("U02FORM03R4R1-")]
    assert len(r4_items) == 160
    assert Counter(row["task_family"] for row in r4_items) == Counter({family: 16 for family in builder.TASK_FAMILIES})
    assert len({row["semantic_signature"] for row in r4_items}) == 160
    assert all(row["r4r1_transfer_demand"] == "NEW_CONTEXT_APPLICATION" for row in r4_items)
    assert all(row["support_level"] == "TRANSFER_NEW_CONTEXT_NO_RULE_HINT" for row in r4_items)

    runtime = q10["runtime_occurrences"]
    non_transfer = [row for row in runtime if row["form_number"] <= 12]
    transfer = [row for row in runtime if row["form_number"] >= 13]
    assert len(non_transfer) == 480
    assert len(transfer) == 160
    assert not any(row["selected_item_id"].startswith("U02FORM03R4R1-") for row in non_transfer)
    assert all(row["selected_item_id"].startswith("U02FORM03R4R1-") for row in transfer)
    assert Counter(row["task_family"] for row in transfer) == Counter({family: 16 for family in builder.TASK_FAMILIES})


def test_r4r1_transfer_instructions_are_task_specific_and_stale_generic_note_is_gone():
    runtime = _payload()["q10_questionbank_capacity_runtime"]["runtime_occurrences"]
    transfer = [row for row in runtime if row["form_number"] >= 13]
    assert len({row["learner_support_note"] for row in transfer}) == 10
    for family in builder.TASK_FAMILIES:
        notes = {row["learner_support_note"] for row in transfer if row["task_family"] == family}
        assert notes == {builder.TRANSFER_NOTE_BY_FAMILY[family]}
    assert not any(row["learner_support_note"] == "Apply the plural rule in a new sentence without a hint." for row in transfer)


def test_r4r1_changes_actual_transfer_task_demand_for_all_160_runtime_slots():
    baseline = _baseline()["q10_questionbank_capacity_runtime"]
    current = _payload()["q10_questionbank_capacity_runtime"]
    old_items = {row["item_id"]: row for row in baseline["unit02_approved_items"]}
    new_items = {row["item_id"]: row for row in current["unit02_approved_items"]}
    old_by_slot = {row["slot_id"]: row for row in baseline["runtime_occurrences"]}

    changed = 0
    for row in current["runtime_occurrences"]:
        if row["form_number"] < 13:
            continue
        old_row = old_by_slot[row["slot_id"]]
        old_item = old_items[old_row["selected_item_id"]]
        new_item = new_items[row["selected_item_id"]]
        assert "New situation" in str(new_item["stimulus"])
        assert new_item["r4r1_transfer_demand"] == "NEW_CONTEXT_APPLICATION"
        if (
            old_item["prompt"] != new_item["prompt"]
            or old_item["stimulus"] != new_item["stimulus"]
            or old_item["options"] != new_item["options"]
            or old_item["question_type"] != new_item["question_type"]
        ):
            changed += 1
    assert changed == 160

    progression = current["progression_support_contract"]
    assert progression["transfer_demand_proven"] is True
    assert progression["independent_transfer_topology_distinct"] is True
    assert progression["transfer_stage_topology_change_count"] == 160
    assert progression["transfer_stage_task_specific_note_count"] == 10


def test_r4r1_retains_global_640_distinctness_zero_answer_leak_and_q6_binding():
    q10 = _payload()["q10_questionbank_capacity_runtime"]
    runtime = q10["runtime_occurrences"]
    proof = q10["global_distinctness_proof"]

    assert len(runtime) == 640
    assert len({row["selected_item_id"] for row in runtime}) == 640
    assert len({row["visible_signature"] for row in runtime}) == 640
    assert len({row["effective_signature"] for row in runtime}) == 640
    assert len({row["runtime_semantic_signature"] for row in runtime}) == 640
    assert proof["exact_duplicate_groups"] == 0
    assert proof["semantic_duplicate_groups"] == 0
    assert proof["prior_activity_direct_answer_leaks"] == 0
    assert proof["global_640_distinct_runtime_question_proof"] is True

    bound = [row for row in runtime if row["sentence_asset_binding"]["status"] == "BOUND_CANONICAL_Q6_SENTENCE_ASSET"]
    assert len(bound) == 128
    assert Counter(row["task_family"] for row in bound) == Counter({"PRODUCTIVE_RESPONSE": 64, "TRANSFER": 64})


def test_r4r1_learner_materialization_keeps_16x40_and_exposes_task_specific_transfer_prompts():
    materialized = form01.build_materialization()
    forms = materialized["student_forms"]
    assert len(forms) == 16
    assert all(form["learner_visible_activity_count"] == 40 for form in forms)
    assert all(form["skill_counts"] == {"READING": 16, "WRITING": 24} for form in forms)

    transfer_forms = [form for form in forms if form["form_ordinal"] >= 13]
    transfer_activities = [activity for form in transfer_forms for activity in form["activities"]]
    assert len(transfer_activities) == 160
    prompt_texts = [activity["prompt"] for activity in transfer_activities]
    assert not any("Apply the plural rule in a new sentence without a hint." in prompt for prompt in prompt_texts)
    for note in builder.TRANSFER_NOTE_BY_FAMILY.values():
        assert sum(note in prompt for prompt in prompt_texts) == 16


def test_r4r1_policy_bound_candidate_and_validator_pass():
    candidate = builder.build_candidate()
    receipt = validator.validate_candidate(candidate)
    approved = builder.admit_candidate(candidate)
    report = validator.validate_approved(candidate, approved)
    assert receipt["status"] == "PASS"
    assert report["validation_status"] == "PASS"
    assert report["forms01_12_runtime_identity_preserved"] is True
    assert report["r4r1_transfer_items"] == 160
    assert report["transfer_runtime_occurrences"] == 160
    assert report["transfer_topology_change_count"] == 160
    assert report["global_640_distinct_runtime_question_proof"] is True

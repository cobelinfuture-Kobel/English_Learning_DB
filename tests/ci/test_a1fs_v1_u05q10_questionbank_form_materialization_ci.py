from collections import Counter

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u05q10_questionbank_form_materialization as builder
from ulga.validators import validate_a1fs_v1_u05q10_questionbank_form_materialization as validator


def payload():
    return builder.build_export_payload()


def test_u05_q10_materializes_exact_twenty_by_forty_questionbank_and_forms():
    p = payload()
    report = validator.validate_payload(p)
    assert report["status"] == "PASS"
    assert len(p["questionbank_items"]) == 800
    assert len(p["forms"]) == 20
    assert len(p["runtime_bindings"]) == 800
    assert p["materialization_contract"]["section_counts_per_form"] == {"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}
    for form in p["forms"]:
        assert form["question_count"] == 40
        assert form["section_counts"] == {"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}


def test_u05_q10_covers_all_q09_task_families_q08_functions_frames_and_subjects():
    p = payload()
    items = p["questionbank_items"]
    src = builder._sources()
    families = builder._families(src)
    q08_functions = {row["function_id"] for row in src["q08"]["communicative_functions"]}
    q08_frames = set(src["q08"]["frame_function_compatibility"])
    q06_subjects = set(src["q06"]["coverage"]["subject_class_counts"])

    assert {row["task_family_id"] for row in items} == set(families)
    assert {row["communicative_function_id"] for row in items} == q08_functions
    assert {row["frame_id"] for row in items} == q08_frames
    assert {row["subject_class"] for row in items} == q06_subjects
    assert {row["polarity"] for row in items} == {"AFFIRMATIVE", "NEGATIVE"}
    assert {builder._frame_base(row["frame_id"]) for row in items} == {"NP", "ADJ", "PLACE"}

    assert p["coverage"]["task_family_coverage"] == "10/10"
    assert p["coverage"]["communicative_function_coverage"] == "7/7"
    assert p["coverage"]["frame_coverage"] == "6/6"
    assert p["coverage"]["subject_class_coverage"] == "9/9"
    assert p["coverage"]["polarity_coverage"] == "2/2"
    assert p["coverage"]["complement_class_coverage"] == "3/3"


def test_u05_q10_uses_800_distinct_q06_sources_and_preserves_surface_semantics_boundary():
    p = payload()
    items = p["questionbank_items"]
    assert len({row["q06_identity"] for row in items}) == 800
    assert len({row["item_id"] for row in items}) == 800
    assert len({row["item_semantic_signature"] for row in items}) == 800
    assert all(row["surface_variant_is_new_semantics"] is False for row in items)

    variants = Counter(row["surface_variant"] for row in items)
    assert variants["FULL"] > 0
    assert variants["CONTRACTED"] + variants["CONTRACTED_ALT"] > 0
    assert p["coverage"]["surface_variant_coverage"]["surface_variant_is_new_semantics"] is False


def test_u05_q10_context_required_items_resolve_q07_and_standalone_items_stay_scene_free():
    p = payload()
    items = p["questionbank_items"]
    src = builder._sources()
    bindings = builder._binding_map(src)
    scenes = builder._scene_map(src)

    for row in items:
        if row["requires_context_binding"]:
            assert row["q06_identity"] in bindings
            scene_ref = bindings[row["q06_identity"]]["scene_ref_id"]
            assert row["scene_ref_id"] == scene_ref
            assert scene_ref in scenes
            if row["polarity"] == "NEGATIVE":
                truth = scenes[scene_ref]["truth_evidence_spec"]
                assert truth["explicit_positive_alternative_required_for_negative"] is True
                assert truth["negation_proof_by_absence_allowed"] is False
            if row["subject_class"] in {"he", "she", "it", "they"}:
                assert scenes[scene_ref]["referent_binding_spec"]["required"] is True
        else:
            assert row["scene_ref_id"] is None

    assert p["coverage"]["context_required_unbound_item_count"] == 0
    assert p["coverage"]["standalone_item_forced_scene_count"] == 0


def test_u05_q10_selected_response_contract_has_one_exact_scored_answer():
    p = payload()
    for row in p["questionbank_items"]:
        options = row["options"]
        if not options:
            continue
        assert len(options) == len(set(options))
        assert row["correct_answer"] in options
        assert row["single_answer_unique_cue_required"] is True
        assert row["response_contract"]["single_answer_required"] is True


def test_u05_q10_cf05_information_request_does_not_unlock_unit05_interrogative_mastery():
    p = payload()
    cf05 = [row for row in p["questionbank_items"] if row["communicative_function_id"] == "U05-CF05_REQUEST_BASIC_BE_INFORMATION"]
    assert cf05
    assert {row["task_family_id"] for row in cf05}.issubset({
        "U05-TF09_PRODUCTIVE_RESPONSE",
        "U05-TF10_TRANSFER",
    })
    for row in cf05:
        assert row["stimulus"]["exact_question_form_materialized_by_unit05"] is False
        assert row["be_interrogative_mastery_activated"] is False
        assert row["response_contract"]["scoring_mode"] == "HUMAN_REVIEW"


def test_u05_q10_runtime_has_three_same_family_candidates_per_slot():
    p = payload()
    by_id = {row["item_id"]: row for row in p["questionbank_items"]}
    assert len(p["runtime_bindings"]) == 800
    assert len({row["slot_id"] for row in p["runtime_bindings"]}) == 800
    for row in p["runtime_bindings"]:
        assert len(row["candidate_ids"]) == 3
        assert len(set(row["candidate_ids"])) == 3
        assert row["selected_item_id"] == row["candidate_ids"][0]
        assert all(candidate in by_id for candidate in row["candidate_ids"])
        assert all(by_id[candidate]["task_family_id"] == row["task_family_id"] for candidate in row["candidate_ids"])


def test_u05_q10_progression_sections_policy_bound_admission_and_scope_boundaries():
    p = payload()
    assert Counter(form["progression_role"] for form in p["forms"]) == Counter({
        "GUIDED": 4,
        "REDUCED_SUPPORT": 4,
        "INDEPENDENT": 4,
        "TRANSFER": 4,
        "RETENTION": 4,
    })

    candidate = builder.build_candidate()
    assert candidate["artifact_role"] == policy_artifact.CANDIDATE_ROLE
    receipt = validator.validate_candidate(candidate)
    assert receipt["status"] == "PASS"
    approved = builder.admit_candidate(candidate)
    assert approved["artifact_role"] == policy_artifact.APPROVED_ROLE
    assert approved["admission"]["status"] == "APPROVED"

    assert all(value is False for value in p["boundaries"].values())
    assert p["next_short_step"] == builder.NEXT_SHORT_STEP

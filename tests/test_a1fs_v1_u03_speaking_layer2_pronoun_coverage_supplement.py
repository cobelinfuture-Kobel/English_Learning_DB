from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.builders import build_a1fs_v1_u03_speaking_layer2_pronoun_coverage_supplement as builder
from ulga.validators import validate_a1fs_v1_u03_speaking_layer2_pronoun_coverage_supplement as validator


def _contract() -> dict:
    return {
        "append_only": {"supplement_id_prefix": "U03-CONN-SUP-"},
        "additional_minimums": {"you": 48, "we": 48, "it": 42},
        "combined_minimums": {"you": 48, "we": 48, "it": 52},
    }


def _fixtures() -> tuple[list[dict], list[dict], dict]:
    base = [{"connected_id": "BASE", "utterances": ["I speak.", "He speaks.", "She speaks.", "They speak.", *(["It is here."] * 10)]}]
    atomics: list[dict] = []
    supplement: list[dict] = []
    for pronoun in ("you", "we"):
        for i in range(48):
            aid = f"A-{pronoun}-{i}"
            text = f"{pronoun.capitalize()} practise sentence {i}."
            atomics.append({"atomic_id": aid, "text": text, "subject_pronoun": pronoun, "semantic_admission_class": "APPROVE", "reference_mode": "DIRECT"})
            supplement.append({"connected_id": f"U03-CONN-SUP-{pronoun.upper()}-{i:03d}", "target_subject_pronoun": pronoun, "atomic_source_ids": [aid], "utterances": [text]})
    for i in range(14):
        identity_id = f"IT-ID-{i}"
        identity = f"It is a book{i}."
        atomics.append({"atomic_id": identity_id, "text": identity, "subject_pronoun": "it", "semantic_admission_class": "CONTEXT_BOUND_APPROVE", "reference_mode": "REFERENCE_BOUND"})
        attr_ids = []
        attrs = []
        for j, text in enumerate(("It is small.", "It is red.", "It is old.")):
            aid = f"IT-{i}-{j}"
            atomics.append({"atomic_id": aid, "text": text, "subject_pronoun": "it", "semantic_admission_class": "CONTEXT_BOUND_APPROVE", "reference_mode": "REFERENCE_BOUND"})
            attr_ids.append(aid)
            attrs.append(text)
        antecedent = f"This is a book{i}."
        supplement.append({
            "connected_id": f"U03-CONN-SUP-IT-{i:03d}",
            "target_subject_pronoun": "it",
            "atomic_source_ids": [identity_id, *attr_ids],
            "antecedent": {"utterance_index": 0, "text": antecedent, "referent_type": "SINGULAR_NONHUMAN", "source_atomic_id": identity_id},
            "utterances": [antecedent, *attrs],
        })
    return base, atomics, {"supplement_records": supplement}


def test_validator_accepts_exact_append_only_coverage() -> None:
    base, atomics, payload = _fixtures()
    report = validator.validate_payload(payload, base_rows=base, atomic_rows=atomics, contract=_contract())
    assert report["validation_status"] == validator.PASS_STATUS
    assert report["additional_sentence_initial_pronoun_counts"] == {"you": 48, "we": 48, "it": 42}
    assert report["combined_sentence_initial_pronoun_counts"]["it"] == 52
    assert report["append_only_base_ids_unchanged"] is True


def test_validator_rejects_it_without_prior_bound_antecedent() -> None:
    base, atomics, payload = _fixtures()
    drifted = deepcopy(payload)
    it_row = next(row for row in drifted["supplement_records"] if row["target_subject_pronoun"] == "it")
    it_row["utterances"][0] = "It is a book0."
    with pytest.raises(validator.SupplementValidationError):
        validator.validate_payload(drifted, base_rows=base, atomic_rows=atomics, contract=_contract())


def test_it_builder_cycles_safe_referents_without_requiring_14_unique_noun_heads() -> None:
    anchors = []
    for i, noun in enumerate(("book", "pen", "player", "apple", "bag", "box", "room")):
        article = "an" if noun == "apple" else "a"
        anchors.append({"atomic_id": f"ID-{i}", "source_sentence_id": f"S-{i}", "text": f"It is {article} {noun}.", "_article": article, "_noun_phrase": noun, "_noun": noun})
    attrs = {text: {"atomic_id": f"ATTR-{i}", "text": text, "source_sentence_id": f"AS-{i}"} for i, text in enumerate(builder.IT_ATTRIBUTE_TEXTS)}
    donors = [{"scene_family": "SCHOOL_CLASSROOM_LEARNING", "scene_location": "in the classroom", "q10_source_item_id": "Q10-1"}]
    cards = builder._make_it_cards(anchors, attrs, donors)
    assert len(cards) == 14
    assert sum(1 for row in cards for text in row["utterances"] if text.startswith("It ")) == 42
    assert all(not row["utterances"][0].startswith("It ") for row in cards)


def test_builder_declares_policy_bound_and_does_not_mutate_base_contract() -> None:
    assert builder.A1FS_CONTENT_POLICY_MODE == "POLICY_BOUND"
    assert "build_a1fs_v1_policy_bound_content_artifact" in builder.policy_artifact.__name__

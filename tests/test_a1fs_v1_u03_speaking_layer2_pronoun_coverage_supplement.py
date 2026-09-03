from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json

import pytest

from ulga.builders import build_a1fs_v1_u03_speaking_layer2_pronoun_coverage_supplement as builder
from ulga.validators import validate_a1fs_v1_u03_speaking_layer2_pronoun_coverage_supplement as validator


CONTRACT_PATH = Path(__file__).resolve().parents[1] / "ulga/contracts/a1fs_v1_u03_speaking_layer2_pronoun_coverage_supplement_contract.json"


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _atomic(aid: str, text: str, pronoun: str, *, reference: bool = False) -> dict:
    return {
        "atomic_id": aid,
        "source_sentence_id": f"S-{aid}",
        "text": text,
        "subject_pronoun": pronoun,
        "semantic_admission_class": "CONTEXT_BOUND_APPROVE" if reference else "APPROVE",
        "reference_mode": "REFERENCE_BOUND" if reference else "DIRECT",
    }


def _fixture() -> tuple[list[dict], list[dict], dict]:
    base = [
        {
            "connected_id": "BASE-C",
            "family": builder.FAMILY_C,
            "title": "Sentence Chain 01",
            "scene_family": "SCHOOL_CLASSROOM_LEARNING",
            "scene_location": "in the classroom",
            "q10_source_item_id": "Q10-C",
            "utterances": ["I speak.", "He speaks.", "She speaks.", "They speak."],
        },
        {
            "connected_id": "BASE-E",
            "family": builder.FAMILY_E,
            "title": "Show and Tell · Object 01",
            "scene_family": "SCHOOL_CLASSROOM_LEARNING",
            "scene_location": "in the classroom",
            "q10_source_item_id": "Q10-E",
            "utterances": [
                "This is a book.",
                "It is red.",
                "I have a book.",
                "I like books.",
                "I can see books.",
                "It is in the classroom.",
            ],
        },
        {
            "connected_id": "BASE-H",
            "family": builder.FAMILY_H,
            "title": "Reference Check 01",
            "scene_family": "SCHOOL_CLASSROOM_LEARNING",
            "scene_location": "in the classroom",
            "q10_source_item_id": "Q10-H",
            "utterances": [
                "I can see Mia.",
                "She has a book.",
                "I can see Ben.",
                "He has a pen.",
                "Mia and Ben are together.",
                "They are in the classroom.",
                "I have a question.",
                "They have answers.",
            ],
        },
        {
            "connected_id": "BASE-IT",
            "family": builder.FAMILY_C,
            "title": "Baseline It Coverage",
            "scene_family": "SCHOOL_CLASSROOM_LEARNING",
            "scene_location": "in the classroom",
            "q10_source_item_id": "Q10-IT",
            "utterances": ["It is here."] * 8,
        },
    ]

    atomics: list[dict] = []
    for i in range(48):
        body = f"practise pattern {i}."
        atomics.extend([
            _atomic(f"I-{i}", f"I {body}", "i"),
            _atomic(f"YOU-{i}", f"You {body}", "you"),
            _atomic(f"WE-{i}", f"We {body}", "we"),
        ])
    atomics.append(_atomic("IT-ID", "It is a book.", "it", reference=True))
    for idx, text in enumerate(builder.IT_ATTRIBUTE_TEXTS):
        atomics.append(_atomic(f"IT-ATTR-{idx}", text, "it", reference=True))

    shared = builder._shared_i_you_we_rows(
        atomics,
        base_surfaces={x for row in base for x in row["utterances"]},
        needed=48,
    )
    supplement = [
        *builder._make_we_c_cards(shared["we"], [base[0], base[3]]),
        *builder._make_it_e_cards(atomics, [base[1]]),
        *builder._make_you_h_cards(shared["you"], shared["i"], [base[2]]),
    ]
    return base, atomics, {"supplement_records": supplement}


def test_formal_ci_supplement_accepts_exact_coverage_and_counts() -> None:
    base, atomics, payload = _fixture()
    report = validator.validate_payload(payload, base_rows=base, atomic_rows=atomics, contract=_contract())
    assert report["validation_status"] == validator.PASS_STATUS
    assert report["supplement_set_count"] == 34
    assert report["supplement_utterance_count"] == 228
    assert report["supplement_family_counts"] == {
        builder.FAMILY_C: 8,
        builder.FAMILY_E: 14,
        builder.FAMILY_H: 12,
    }
    assert report["additional_sentence_initial_pronoun_counts"] == {"you": 48, "we": 48, "it": 42}
    assert report["combined_sentence_initial_pronoun_counts"]["it"] == 52
    assert report["formal_c_i_family_contract_pass"] is True
    assert report["expected_supplement_logical_pages"] == 12


def test_rejects_you_as_part_f_personal_speaking() -> None:
    base, atomics, payload = _fixture()
    drifted = deepcopy(payload)
    row = next(x for x in drifted["supplement_records"] if x["target_subject_pronoun"] == "you")
    row["family"] = "F_PERSONAL_SPEAKING"
    with pytest.raises(validator.SupplementValidationError, match="target_family_mismatch"):
        validator.validate_payload(drifted, base_rows=base, atomic_rows=atomics, contract=_contract())


def test_rejects_part_h_non_alternating_or_unmatched_you_i_pair() -> None:
    base, atomics, payload = _fixture()
    drifted = deepcopy(payload)
    row = next(x for x in drifted["supplement_records"] if x["target_subject_pronoun"] == "you")
    row["turns"][1]["speaker"] = "A"
    with pytest.raises(validator.SupplementValidationError, match="part_h_ab_alternation_required"):
        validator.validate_payload(drifted, base_rows=base, atomic_rows=atomics, contract=_contract())

    drifted = deepcopy(payload)
    row = next(x for x in drifted["supplement_records"] if x["target_subject_pronoun"] == "you")
    row["turns"][1]["text"] = row["utterances"][3]
    row["utterances"][1] = row["utterances"][3]
    with pytest.raises(validator.SupplementValidationError, match="part_h_you_i_body_mismatch"):
        validator.validate_payload(drifted, base_rows=base, atomic_rows=atomics, contract=_contract())


def test_rejects_it_without_prior_bound_antecedent_or_with_donor_support_drift() -> None:
    base, atomics, payload = _fixture()
    drifted = deepcopy(payload)
    row = next(x for x in drifted["supplement_records"] if x["target_subject_pronoun"] == "it")
    row["utterances"][0] = "It is a book."
    with pytest.raises(validator.SupplementValidationError):
        validator.validate_payload(drifted, base_rows=base, atomic_rows=atomics, contract=_contract())

    drifted = deepcopy(payload)
    row = next(x for x in drifted["supplement_records"] if x["target_subject_pronoun"] == "it")
    row["source_layer2_support_utterances"][0] = "I have a pen."
    row["utterances"][4] = "I have a pen."
    with pytest.raises(validator.SupplementValidationError, match="part_e_support_not_from_donor"):
        validator.validate_payload(drifted, base_rows=base, atomic_rows=atomics, contract=_contract())


def test_it_builder_uses_formal_six_row_part_e_and_exact_42_it_lines() -> None:
    base, atomics, _ = _fixture()
    cards = builder._make_it_e_cards(atomics, [base[1]])
    assert len(cards) == 14
    assert all(card["family"] == builder.FAMILY_E for card in cards)
    assert all(len(card["utterances"]) == 6 for card in cards)
    assert sum(
        1 for card in cards for text in card["utterances"]
        if text.startswith("It ")
    ) == 42
    assert all(card["utterances"][0].startswith("This is ") for card in cards)
    assert all(len(card["source_layer2_support_utterances"]) == 2 for card in cards)


def test_html_matches_formal_ci_part_and_page_contract() -> None:
    _, _, payload = _fixture()
    rendered = builder.render_html(payload["supplement_records"])
    assert rendered.count("<section class='page'>") == 12
    assert "Part C · Sentence Chaining" in rendered
    assert "Part E · Show and Tell" in rendered
    assert "Part H · Interaction / Role-play" in rendered
    assert "Part A" not in rendered
    assert "Part B" not in rendered
    assert "R Read · S Shadow · M Memory" in rendered
    assert "<span class='speaker'>A:</span>" in rendered
    assert "Layer 2 · High chunk repetition + high lexical variation" in rendered


def test_builder_declares_policy_bound() -> None:
    assert builder.A1FS_CONTENT_POLICY_MODE == "POLICY_BOUND"
    assert "build_a1fs_v1_policy_bound_content_artifact" in builder.policy_artifact.__name__

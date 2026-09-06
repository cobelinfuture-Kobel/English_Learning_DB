#!/usr/bin/env python3
"""Focused regression for Unit04 Q10R1 TF07 learner-projection repair."""
from __future__ import annotations

from product.a1fs_v1_2_1 import (
    u04q10r1_unit04_learner_facing_pedagogical_acceptance as acceptance,
)


def test_u04q10r1_tf07_restores_complement_and_section_purpose_without_duplicates():
    payload = acceptance.source.build_export_payload()
    acceptance._source_contract(payload)
    forms = acceptance._project_forms(payload)
    items = {str(row["item_id"]): row for row in payload["questionbank_items"]}
    source_forms = list(payload["forms"])
    tf07_count = 0

    for form_number, form in enumerate(forms, start=1):
        source_ids = [str(value) for value in source_forms[form_number - 1]["item_ids"]]
        exact = []
        normalized = []
        for activity, item_id in zip(form["activities"], source_ids):
            item = items[item_id]
            exact.append(
                acceptance._canonical(
                    acceptance._visible_payload(activity, normalized=False)
                )
            )
            normalized.append(
                acceptance._canonical(
                    acceptance._visible_payload(activity, normalized=True)
                )
            )
            if str(item["task_family_id"]) != "U04-TF07_CONTEXT_GAP":
                continue

            tf07_count += 1
            complement = acceptance._complement(item)
            assert f"Place or object: {complement}" in str(activity["stimulus"])
            section = str(item["section"])
            if section == "C":
                assert "Build the missing place phrase from the evidence." in str(
                    activity["prompt"]
                )
            elif section == "D":
                assert "Use the context to complete the missing place phrase." in str(
                    activity["prompt"]
                )
            else:
                raise AssertionError(f"TF07_UNEXPECTED_SECTION:{item_id}:{section}")

        assert acceptance._duplicate_excess(exact) == 0, f"EXACT:F{form_number:02d}"
        assert acceptance._duplicate_excess(normalized) == 0, (
            f"NORMALIZED:F{form_number:02d}"
        )

    assert tf07_count > 0


def test_u04q10r1_tf07_repair_keeps_locked_source_identity_and_acceptance_green():
    report = acceptance.build_acceptance_report()
    acceptance_report = report["acceptance"]
    assert acceptance_report["within_form_exact_duplicate_count"] == 0
    assert acceptance_report["within_form_normalized_duplicate_count"] == 0
    assert acceptance_report["selected_relation_answer_leak_count"] == 0
    assert report["claim_boundaries"]["source_800_runtime_rows_mutated"] is False
    assert report["claim_boundaries"]["source_selected_item_identities_mutated"] is False
    assert report["claim_boundaries"]["source_candidate_identities_mutated"] is False
    assert report["claim_boundaries"]["q10_redone"] is False

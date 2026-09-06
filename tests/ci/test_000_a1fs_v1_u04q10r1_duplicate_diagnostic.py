#!/usr/bin/env python3
"""Temporary exact diagnostic for Unit04 Q10R1 within-form TF07 duplicates."""
from __future__ import annotations

from collections import defaultdict
import json

import pytest

from product.a1fs_v1_2_1 import (
    u04q10r1_unit04_learner_facing_pedagogical_acceptance as acceptance,
)


def test_000_u04q10r1_emit_tf07_exact_source_differences_and_stop_suite():
    payload = acceptance.source.build_export_payload()
    acceptance._source_contract(payload)
    forms = acceptance._project_forms(payload)
    items = {str(row["item_id"]): row for row in payload["questionbank_items"]}
    source_forms = list(payload["forms"])
    exact_groups = []

    for form_number, form in enumerate(forms, start=1):
        source_ids = [str(value) for value in source_forms[form_number - 1]["item_ids"]]
        buckets = defaultdict(list)
        for question_number, (activity, item_id) in enumerate(
            zip(form["activities"], source_ids), start=1
        ):
            signature = acceptance._canonical(
                acceptance._visible_payload(activity, normalized=False)
            )
            buckets[signature].append((question_number, item_id))
        for pairs in buckets.values():
            if len(pairs) <= 1:
                continue
            rows = []
            for question_number, item_id in pairs:
                item = items[item_id]
                rows.append({
                    "form": f"F{form_number:02d}",
                    "question": f"Q{question_number:02d}",
                    "item_id": item_id,
                    "item_keys": sorted(str(key) for key in item.keys()),
                    "task_family": str(item.get("task_family_id") or ""),
                    "relation": str(item.get("relation_surface") or ""),
                    "communicative_function": str(item.get("communicative_function_id") or ""),
                    "source_sentence_text": str(item.get("source_sentence_text") or ""),
                    "place_phrase": str(item.get("place_phrase") or ""),
                    "reference_landmarks": list(item.get("reference_landmarks") or []),
                    "stimulus": item.get("stimulus"),
                    "scene_ref_id": item.get("scene_ref_id"),
                    "source_scene_ref": item.get("source_scene_ref"),
                    "answerability_basis": item.get("answerability_basis"),
                    "evidence_mode": item.get("evidence_mode"),
                    "evidence_role": item.get("evidence_role"),
                    "response_contract": item.get("response_contract"),
                    "semantic_signature": item.get("semantic_signature"),
                })
            exact_groups.append(rows)

    pytest.exit(
        "U04Q10R1_TF07_SOURCE_DIAGNOSTIC="
        + json.dumps({"exact_groups": exact_groups}, ensure_ascii=False),
        returncode=1,
    )

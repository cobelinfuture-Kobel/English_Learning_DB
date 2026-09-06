#!/usr/bin/env python3
"""Temporary exact diagnostic for Unit04 Q10R1 within-form learner-visible duplicates."""
from __future__ import annotations

from collections import defaultdict
import json

import pytest

from product.a1fs_v1_2_1 import (
    u04q10r1_unit04_learner_facing_pedagogical_acceptance as acceptance,
)


def _groups(signatures):
    buckets = defaultdict(list)
    for row in signatures:
        buckets[row["signature"]].append(row)
    return [rows for rows in buckets.values() if len(rows) > 1]


def test_000_u04q10r1_emit_exact_duplicate_groups_and_stop_suite():
    payload = acceptance.source.build_export_payload()
    acceptance._source_contract(payload)
    forms = acceptance._project_forms(payload)
    items = {str(row["item_id"]): row for row in payload["questionbank_items"]}
    source_forms = list(payload["forms"])

    exact_groups = []
    normalized_groups = []
    for form_number, form in enumerate(forms, start=1):
        source_ids = [str(value) for value in source_forms[form_number - 1]["item_ids"]]
        exact_rows = []
        normalized_rows = []
        for question_number, (activity, item_id) in enumerate(
            zip(form["activities"], source_ids), start=1
        ):
            item = items[item_id]
            detail = {
                "form": f"F{form_number:02d}",
                "question": f"Q{question_number:02d}",
                "item_id": item_id,
                "task_family": str(item["task_family_id"]),
                "relation": str(item["relation_surface"]),
                "communicative_function": str(item["communicative_function_id"]),
                "source_sentence_text": str(item.get("source_sentence_text") or ""),
                "place_phrase": str(item.get("place_phrase") or ""),
                "prompt": str(activity.get("prompt") or ""),
                "stimulus": str(activity.get("stimulus") or ""),
                "options": [str(value) for value in activity.get("options") or []],
            }
            exact_rows.append({
                "signature": acceptance._canonical(
                    acceptance._visible_payload(activity, normalized=False)
                ),
                **detail,
            })
            normalized_rows.append({
                "signature": acceptance._canonical(
                    acceptance._visible_payload(activity, normalized=True)
                ),
                **detail,
            })
        for rows in _groups(exact_rows):
            exact_groups.append(rows)
        for rows in _groups(normalized_rows):
            normalized_groups.append(rows)

    report = {
        "exact_duplicate_excess": sum(len(rows) - 1 for rows in exact_groups),
        "normalized_duplicate_excess": sum(len(rows) - 1 for rows in normalized_groups),
        "exact_groups": exact_groups,
        "normalized_groups": normalized_groups,
    }
    print("U04Q10R1_DUPLICATE_DIAGNOSTIC=" + json.dumps(report, ensure_ascii=False))
    pytest.exit("U04Q10R1_DUPLICATE_DIAGNOSTIC_COMPLETE", returncode=1)

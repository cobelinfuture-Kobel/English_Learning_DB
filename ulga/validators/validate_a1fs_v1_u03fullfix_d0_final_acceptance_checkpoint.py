#!/usr/bin/env python3
"""Fail-closed Unit03 FullFix D0 acceptance checkpoint and semantic regressions.

This validator records the SHA-bound D0 learner package accepted on 2026-09-01
and the two semantic presentation regressions discovered during full PDF review:
1) stale location frames inside one learner item; 2) lower-cased proper names
introduced by temporal-context de-duplication.

It creates no learner content and does not mutate Q1-Q10/Q6/PDF artifacts.
"""
from __future__ import annotations

import json
import re
from typing import Any, Iterable, Mapping

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only Unit03 FullFix D0 acceptance checkpoint and semantic regression "
    "guard. It creates or mutates no grammar, vocabulary, chunk, SentenceAsset, "
    "QuestionBank, scene, runtime/state/scoring, PDF, Unit04, Q11, or A2 authority."
)

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U03FULLFIX-D0_Unit03FinalAcceptanceCheckpoint"
PASS_STATUS = "PASS_A1FS_V1_U03FULLFIX_D0_FINAL_ACCEPTANCE_CHECKPOINT"

EXPECTED_D0_STATUS = "PASS_A1FS_V1_U03FULLFIX_D0_FINAL_ACCEPTANCE"
EXPECTED_D1_STATUS = "PASS_A1FS_V1_U03FULLFIX_D1R1_PDF_ACCEPTANCE"
EXPECTED_ITEM_COUNT = 800
EXPECTED_FORM_COUNT = 20
EXPECTED_STORY_COUNT = 20
EXPECTED_SECTION_COUNTS = {"A": 120, "B": 200, "C": 200, "D": 160, "E": 120}
CONTENT_REPEAT_THRESHOLD = 0.03

ACCEPTED_SOURCE_IDENTITY = {
    "inventory_sha256": "676d5a056e51ed4de3daa54a67e3d00d12097d78deb85802b8a5471746d69950",
    "runtime_sha256": "e94df622c899e9bfa8405eb22c63fdb4fc21b70ef7fd88e7ae4a5ffa9c931b64",
    "questionbook_sha256": "8930658c3ca9684bcf768aafbe09161e561429b3c0f6751ced89e3a5e8689a37",
    "answerkey_sha256": "11ceb58093a71e82d3b9a9fe6c018e5107356624fd3d72082e15d5eec23c07c9",
    "d2_semantic_qa_sha256": "adeba46bede26d539f48c6a570f4760e04c14817e4b3483eab21fd355ded8242",
    "d3_content_qa_sha256": "8513f2500c53519a9d7ab37f08802d5d2af5a16ce31f5b73a6d701a17620f9f0",
}

KNOWN_SETTINGS = sorted(
    {
        "in the bathroom", "by a mirror", "in a bedroom", "at a writing table",
        "at home with family", "at a picnic table", "at home", "in the kitchen",
        "near a computer desk", "in the music room", "in a garden", "at a farm",
        "in the classroom", "in a small shop", "at the playground", "in town",
        "near the station", "in the living room", "at the zoo", "at the train station",
        "near the town library", "in house pictures", "on a town map", "in a home picture",
    },
    key=len,
    reverse=True,
)
_SETTING_RE = re.compile("|".join(re.escape(value) for value in KNOWN_SETTINGS), re.I)
PROPER_NAMES = {
    "Mia", "Emma", "Lucy", "Ava", "Ruby", "Ella", "Sofia", "Lily", "Zoe", "Anna",
    "Ben", "Jack", "Tom", "Ryan", "Sam", "Leo", "Owen", "Max", "Noah", "Alex",
}


class U03FullFixD0AcceptanceError(ValueError):
    pass


def _casefold(value: Any) -> str:
    return str(value or "").casefold()


def location_hits(text: Any) -> list[str]:
    return [match.group(0) for match in _SETTING_RE.finditer(str(text or ""))]


def stale_location_frames(text: Any, target_setting: Any) -> list[str]:
    """Return location frames that conflict with the row's bound setting.

    A shorter phrase contained inside the target is not stale, e.g. ``at home``
    inside ``at home with family``.
    """
    target = _casefold(target_setting)
    failures: list[str] = []
    for hit in location_hits(text):
        folded = hit.casefold()
        if folded == target or folded in target:
            continue
        failures.append(hit)
    return failures


def lowercase_proper_names(text: Any) -> list[str]:
    raw = str(text or "")
    failures: list[str] = []
    for name in sorted(PROPER_NAMES):
        if re.search(r"(?<![A-Za-z])" + re.escape(name.lower()) + r"(?![A-Za-z])", raw):
            failures.append(name)
    return failures


def semantic_regression_failures(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("section") or "") == "E":
            continue
        item_id = str(row.get("item_id") or "")
        stale = stale_location_frames(row.get("stimulus"), row.get("micro_scene_setting"))
        if stale:
            failures.append({"item_id": item_id, "code": "STALE_LOCATION_FRAME", "detail": stale})
        for field in ("micro_scene_context", "stimulus"):
            bad_names = lowercase_proper_names(row.get(field))
            if bad_names:
                failures.append(
                    {"item_id": item_id, "code": "LOWERCASE_PROPER_NAME", "field": field, "detail": bad_names}
                )
    return failures


def validate_d0_manifest(manifest: Mapping[str, Any]) -> None:
    if manifest.get("status") != EXPECTED_D0_STATUS or manifest.get("final_acceptance") != "PASS":
        raise U03FullFixD0AcceptanceError("D0_STATUS_INVALID")
    if manifest.get("q1_q10_scope") != "FINAL_ACCEPTED":
        raise U03FullFixD0AcceptanceError("Q1_Q10_SCOPE_NOT_FINAL_ACCEPTED")

    d3 = manifest.get("d3_data_content_acceptance", {})
    if d3.get("status") != "PASS" or int(d3.get("items", -1)) != EXPECTED_ITEM_COUNT:
        raise U03FullFixD0AcceptanceError("D3_DENOMINATOR_INVALID")
    if int(d3.get("forms", -1)) != EXPECTED_FORM_COUNT:
        raise U03FullFixD0AcceptanceError("D3_FORM_COUNT_INVALID")
    if any(d3.get("section_acceptance", {}).get(section) != "PASS" for section in "ABCDE"):
        raise U03FullFixD0AcceptanceError("D3_SECTION_ACCEPTANCE_INVALID")
    if float(d3.get("content_exact_repeat_rate", 1.0)) >= CONTENT_REPEAT_THRESHOLD:
        raise U03FullFixD0AcceptanceError("CONTENT_REPEAT_THRESHOLD_FAILED")
    if int(d3.get("scene_family_count", -1)) != 17:
        raise U03FullFixD0AcceptanceError("SCENE_FAMILY_COUNT_INVALID")
    if int(d3.get("micro_scene_duplicate_context_count", -1)) != 0:
        raise U03FullFixD0AcceptanceError("MICRO_SCENE_DUPLICATE_CONTEXT")

    d2 = manifest.get("d2_semantic_acceptance", {})
    if d2.get("status") != "PASS" or int(d2.get("reviewed_items", -1)) != EXPECTED_ITEM_COUNT:
        raise U03FullFixD0AcceptanceError("D2_DENOMINATOR_INVALID")
    if int(d2.get("passed_items", -1)) != EXPECTED_ITEM_COUNT or int(d2.get("failed_items", -1)) != 0:
        raise U03FullFixD0AcceptanceError("D2_SEMANTIC_ACCEPTANCE_INVALID")
    if (int(d2.get("stories_reviewed", -1)), int(d2.get("stories_passed", -1)), int(d2.get("stories_failed", -1))) != (20, 20, 0):
        raise U03FullFixD0AcceptanceError("D2_STORY_ACCEPTANCE_INVALID")

    d1 = manifest.get("d1_pdf_acceptance", {})
    if d1.get("status") != EXPECTED_D1_STATUS:
        raise U03FullFixD0AcceptanceError("D1_STATUS_INVALID")
    expected_pdf = {
        "questionbook_pages": 80,
        "answerkey_pages": 20,
        "prompt_alignment": 800,
        "answer_alignment": 800,
        "blank_pages": 0,
        "clipped_or_edge_violations": 0,
        "answer_label_leakage": 0,
    }
    for key, value in expected_pdf.items():
        if int(d1.get(key, -1)) != value:
            raise U03FullFixD0AcceptanceError(f"D1_PDF_ACCEPTANCE_INVALID:{key}")
    if d1.get("full_page_visual_review") != "PASS":
        raise U03FullFixD0AcceptanceError("D1_FULL_PAGE_VISUAL_REVIEW_NOT_PASS")

    identity = manifest.get("source_identity", {})
    if identity != ACCEPTED_SOURCE_IDENTITY:
        raise U03FullFixD0AcceptanceError("D0_SOURCE_IDENTITY_DRIFT")

    boundaries = manifest.get("claim_boundaries", {})
    forbidden_true = ("q6_regenerated", "q11_created", "unit04_started", "generic_contract_started", "pdf_renderer_modified_source_content")
    if any(boundaries.get(key) is not False for key in forbidden_true):
        raise U03FullFixD0AcceptanceError("D0_CLAIM_BOUNDARY_DRIFT")


def build_checkpoint(manifest: Mapping[str, Any]) -> dict[str, Any]:
    validate_d0_manifest(manifest)
    return {
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "accepted_source_identity": dict(ACCEPTED_SOURCE_IDENTITY),
        "semantic_regressions_guarded": ["STALE_LOCATION_FRAME", "LOWERCASE_PROPER_NAME"],
        "unit03_final_acceptance": "PASS",
        "q6_regenerated": False,
        "q11_created": False,
        "unit04_started": False,
        "a2_unlocked": False,
    }


def main() -> int:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    print(json.dumps(build_checkpoint(payload), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

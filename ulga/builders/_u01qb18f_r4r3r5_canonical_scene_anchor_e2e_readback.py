"""Executable readback for the bounded R4R3R5 canonical scene-anchor FullFix."""
from __future__ import annotations

from ulga.builders import _u01qb18f_r2_canonical_micro_scene_authority_fullfix as authority
from ulga.builders import _u01qb18f_r4r3r5_canonical_scene_anchor_reconciliation_fullfix as r4r3r5
from ulga.builders import (
    build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration
    as u13,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only executable acceptance readback over the existing R4R3R5 canonical "
    "scene-anchor authority; no content, QuestionBank, learner state, runtime, planner, "
    "scoring, Unit02-24, audio, Speaking score, or A2 state is changed."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18F-R4R3R5_CanonicalSceneAnchorE2EReadback"
PASS_STATUS = "PASS_A1FS_V1_U01QB18F_R4R3R5_CANONICAL_SCENE_ANCHOR_E2E_READBACK"


def run() -> dict[str, object]:
    if not r4r3r5.installed():
        raise RuntimeError("R4R3R5_NOT_INSTALLED")
    report = authority.require_authority_pass()
    package = authority.canonical_scene_package(r4r3r5.SHOP04_REF)
    index = u13._scene_semantic_index()
    anchors = list(package.get("anchors") or [])
    u13_anchors = list(index[r4r3r5.SHOP04_REF].get("anchors") or [])
    if anchors != list(r4r3r5.EXPECTED_SHOP04_ANCHORS):
        raise RuntimeError("SHOP04_CANONICAL_ANCHORS_INVALID")
    if u13_anchors != anchors:
        raise RuntimeError("SHOP04_U13_ANCHOR_PARITY_INVALID")
    return {
        "status": PASS_STATUS,
        "shop04_anchors": anchors,
        "canonical_scene_count": report["canonical_scene_count"],
        "unit01_runtime_bindable_scene_count": report[
            "unit01_runtime_bindable_scene_count"
        ],
        "deferred_scene_refs": report["deferred_scene_refs"],
        "questionbank_modified": False,
        "new_scene_authored": False,
        "bound_evidence_modified": False,
    }


if __name__ == "__main__":
    result = run()
    for key, value in result.items():
        print(f"{key.upper()}={value}")

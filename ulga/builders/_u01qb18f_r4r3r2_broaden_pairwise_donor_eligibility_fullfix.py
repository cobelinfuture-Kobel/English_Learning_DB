"""Broaden R4R3R1 pairwise donor eligibility to legal reused scenes.

Actual R4 production diagnostics proved that U01-MA-SHOP-04 in Form08 has no
single-exposure future SHOPPING donor, but two already-reused donor slots are
fully legal after moving their later exposure to Form08:

- F11 U01-C4-TOY-SHOP -> effective exposures F04/F08, repeat gap 4
- F12 U01-MA-SHOP-01 -> effective exposures F05/F08, repeat gap 3

R4R3R1 rejected both only because it required donor exposure_count == 1.
This adapter keeps the original pairwise solver first, then broadens the donor
domain only to exposure_count == 2 scenes whose moved exposure preserves the
frozen max-two-exposure and minimum-repeat-gap contracts and whose resulting
current and donor Forms both pass the complete Reading/Writing/Speaking runtime
capacity solver.

It authors no content, adds no QuestionBank item or scene, changes no scoring,
runtime/planner/database authority, and never touches bound Forms or learner
evidence.  It patches only R4R3R1's private candidate admission function; U16C
remains the public assembler owner and R4R3R1 remains the scene-swap writer.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import _u01qb18f_r4r3r1_donor_rejection_diagnostic as diagnostic
from ulga.builders import _u01qb18f_r4r3r1_support_stage_scene_swap_fullfix as r4r3r1
from ulga.builders import build_a1fs_v1_u01qb14r1_runtime_task_aware_allocation_patch as runtime_allocation

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Learner-state-safe admission broadening for the existing R4R3R1 pairwise scene "
    "swap solver. It reuses already-approved scenes and the existing 474-item runtime; "
    "it authors no content and changes no QuestionBank, bound learner evidence, scoring/"
    "runtime/planner/database authority, Unit02-24, audio, Speaking scoring, or A2 state."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18F-R4R3R2_BroadenPairwiseDonorEligibilityToLegalReusedSceneFullFix"
PASS_STATUS = "PASS_A1FS_V1_U01QB18F_R4R3R2_BROADEN_PAIRWISE_DONOR_ELIGIBILITY_TO_LEGAL_REUSED_SCENE_FULLFIX"
NEXT_SHORT_STEP = r4r3r1.NEXT_SHORT_STEP

_ORIGINAL_CANDIDATE_SWAP = r4r3r1._candidate_swap
_INSTALLED = False


class BroadenedPairwiseDonorEligibilityError(ValueError):
    """Fail-closed R4R3R2 installation/admission error."""


def _broadened_candidate_swap(
    database: Path,
    *,
    current_form: int,
    failing_ref: str,
    all_rows: Sequence[Mapping[str, Any]],
    frozen_forms: set[int],
):
    """Preserve legacy candidates, then admit legal exposure-count-two donors."""
    legacy = _ORIGINAL_CANDIDATE_SWAP(
        Path(database),
        current_form=current_form,
        failing_ref=failing_ref,
        all_rows=all_rows,
        frozen_forms=frozen_forms,
    )
    if legacy is not None:
        return legacy

    usage = r4r3r1.r4r3._scene_usage(all_rows)
    failing_usage = usage.get(str(failing_ref))
    if failing_usage is None:
        raise BroadenedPairwiseDonorEligibilityError(
            f"FAILING_SCENE_USAGE_MISSING:{failing_ref}"
        )
    # R4R3R2 only broadens the single-exposure failure case already owned by R4R3R1.
    if int(failing_usage["exposure_count"]) != 1:
        return None

    family = str(failing_usage["situation_family"])
    current_refs = {
        str(row["scene_ref_id"])
        for row in all_rows
        if int(row["form_ordinal"]) == int(current_form)
    }
    catalog = runtime_allocation._catalog(Path(database))
    ranked: list[tuple[tuple[Any, ...], Any]] = []
    seen: set[tuple[int, str]] = set()

    for row in all_rows:
        donor_form = int(row["form_ordinal"])
        donor_ref = str(row["scene_ref_id"])
        key = (donor_form, donor_ref)
        if key in seen:
            continue
        seen.add(key)

        if donor_form <= int(current_form) or donor_form in frozen_forms:
            continue
        if donor_ref == str(failing_ref) or donor_ref in current_refs:
            continue

        donor_usage = usage.get(donor_ref)
        if donor_usage is None or int(donor_usage["exposure_count"]) != 2:
            continue
        if str(donor_usage["situation_family"]) != family:
            continue

        donor_form_refs = {
            str(value["scene_ref_id"])
            for value in all_rows
            if int(value["form_ordinal"]) == donor_form
        }
        if str(failing_ref) in donor_form_refs:
            continue

        repeat_ok, _repeat_detail = diagnostic._post_swap_repeat_gap(
            donor_usage=donor_usage,
            donor_form=donor_form,
            current_form=current_form,
        )
        if not repeat_ok:
            continue

        simulated = r4r3r1._swap_scene_packages_in_memory(
            all_rows,
            current_form=current_form,
            failing_ref=failing_ref,
            donor_form=donor_form,
            donor_ref=donor_ref,
        )
        try:
            current_choices = {
                skill: r4r3r1._form_skill_choices(
                    all_rows=simulated,
                    form_ordinal=current_form,
                    skill=skill,
                    catalog=catalog,
                )
                for skill in ("READING", "WRITING", "SPEAKING")
            }
            donor_choices = {
                skill: r4r3r1._form_skill_choices(
                    all_rows=simulated,
                    form_ordinal=donor_form,
                    skill=skill,
                    catalog=catalog,
                )
                for skill in ("READING", "WRITING", "SPEAKING")
            }
        except runtime_allocation.RuntimeTaskAwareAllocationError:
            continue

        # Preserve the legacy deterministic policy: nearest future Form, then scene ref.
        rank = (donor_form - int(current_form), donor_ref)
        ranked.append(
            (
                rank,
                (
                    donor_form,
                    donor_ref,
                    simulated,
                    current_choices["SPEAKING"],
                    donor_choices["SPEAKING"],
                ),
            )
        )

    if not ranked:
        return None
    ranked.sort(key=lambda value: value[0])
    return ranked[0][1]


def install() -> None:
    global _INSTALLED
    if installed():
        _INSTALLED = True
        return
    if r4r3r1._candidate_swap is not _ORIGINAL_CANDIDATE_SWAP:
        raise BroadenedPairwiseDonorEligibilityError(
            "R4R3R1_PRIVATE_CANDIDATE_OWNER_DRIFT"
        )
    r4r3r1._candidate_swap = _broadened_candidate_swap
    _INSTALLED = True


def installed() -> bool:
    return _INSTALLED and r4r3r1._candidate_swap is _broadened_candidate_swap

#!/usr/bin/env python3
"""Unit04 Q10R1 bounded TF07 learner-projection repair.

Reuses the locked Q10R1 implementation unchanged and repairs only TF07 learner
presentation: restore the source-backed place/object complement after the place
phrase is masked, and preserve the existing Section C versus Section D learner
task purpose. No QuestionBank/runtime/candidate/sentence/scene identity changes.
"""
from __future__ import annotations

from typing import Any, Mapping

from product.a1fs_v1_2_1 import (
    u04q10r1_unit04_learner_facing_pedagogical_acceptance_impl as _impl,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Bounded learner-presentation adapter over the approved Unit04 Q10R1 "
    "implementation. Restores only already-selected TF07 complement evidence "
    "and existing Section C/D task purpose; creates no QuestionBank item, "
    "sentence, scene, selector, runtime, scoring, PDF, Unit05, or A2 authority."
)

# Preserve the complete public/private module contract used by existing focused CI.
for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)

# Keep the wrapper's explicit content-policy declaration after re-export.
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Bounded learner-presentation adapter over the approved Unit04 Q10R1 "
    "implementation. Restores only already-selected TF07 complement evidence "
    "and existing Section C/D task purpose; creates no QuestionBank item, "
    "sentence, scene, selector, runtime, scoring, PDF, Unit05, or A2 authority."
)

_ORIGINAL_PROMPT = _impl._prompt
_ORIGINAL_STIMULUS = _impl._stimulus


def _prompt(item: Mapping[str, Any]) -> str:
    """Project TF07 with the already-authorized Section C/D learner purpose."""
    family = str(item["task_family_id"])
    if family != "U04-TF07_CONTEXT_GAP":
        return _ORIGINAL_PROMPT(item)

    stage = str(item["progression_role"])
    if stage not in STAGE_PREFIX:
        raise Unit04LearnerFacingAcceptanceError(
            f"STAGE_PROMPT_SUPPORT_MISSING:{stage}"
        )

    section = str(item.get("section") or "")
    if section == "C":
        core = "Build the missing place phrase from the evidence."
    elif section == "D":
        core = "Use the context to complete the missing place phrase."
    else:
        raise Unit04LearnerFacingAcceptanceError(
            f"TF07_SECTION_INVALID:{item.get('item_id')}:{section}"
        )
    return f"{STAGE_PREFIX[stage]}{core}".strip()


def _stimulus(item: Mapping[str, Any]) -> str:
    """Keep TF07 answerable after masking without exposing the target relation."""
    family = str(item["task_family_id"])
    if family != "U04-TF07_CONTEXT_GAP":
        return _ORIGINAL_STIMULUS(item)

    context = _impl._mask_place_phrase_sentence(item)
    complement = _impl._complement(item)
    support = _impl._support_text(item)
    return f"Context: {context} | Place or object: {complement} | {support}"


# Functions defined in the implementation resolve globals in that implementation
# module. Patch only these two learner-projection hooks; source payload stays read-only.
_impl._prompt = _prompt
_impl._stimulus = _stimulus
globals()["_prompt"] = _prompt
globals()["_stimulus"] = _stimulus


if __name__ == "__main__":
    print(json.dumps(build_acceptance_report(), ensure_ascii=False, indent=2))

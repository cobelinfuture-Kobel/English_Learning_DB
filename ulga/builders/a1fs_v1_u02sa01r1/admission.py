from __future__ import annotations
import hashlib
from copy import deepcopy
from typing import Any, Mapping, Sequence
from .constants import *
from .common import *
def semantic_decision(candidate: Mapping[str, Any]) -> tuple[str, list[str]]:
    noun = normalize_surface(candidate["singular"])
    pattern_id = str(candidate["pattern_id"])
    if noun in CHILD_CONTEXT_RESTRICTED:
        return "REJECT", ["CHILD_CONTEXT_RESTRICTED_LEXEME"]
    if candidate.get("generation_role") != "MORPHOLOGY_TARGET" and candidate.get("review_required"):
        return "DEFER", ["CANONICAL_VOCABULARY_REVIEW_REQUIRED"]
    if candidate.get("generation_role") != "MORPHOLOGY_TARGET" and noun in COUNTABILITY_OR_SENSE_REVIEW:
        return "DEFER", ["COUNTABILITY_OR_SENSE_REVIEW_REQUIRED"]
    if candidate.get("generation_role") != "MORPHOLOGY_TARGET" and noun in PROPER_OR_TIME_NAME_REVIEW:
        return "DEFER", ["PROPER_OR_TIME_NAME_PLURAL_REVIEW_REQUIRED"]
    if pattern_id == "SP_000003" and noun in NON_POSSESSABLE_FOR_CHILD_I_HAVE:
        return "REJECT", ["I_HAVE_CHILD_CONTEXT_POSSESSION_IMPLAUSIBLE"]
    if pattern_id in {"SP_000004", "SP_000005"} and candidate.get("numeric_determiner"):
        return "REJECT", ["PREFERENCE_NUMERIC_PLURAL_CONTEXT_INCOMPLETE"]
    if pattern_id == "SP_000013":
        if not candidate.get("numeric_determiner"):
            return "REJECT", ["REQUEST_PLURAL_NP_REQUIRES_QUANTITY"]
        if noun in NON_REQUESTABLE_FOR_CAN_I_HAVE:
            return "REJECT", ["REQUEST_OBJECT_PEDAGOGICALLY_IMPLAUSIBLE"]
    return "APPROVE", ["STRUCTURALLY_VALID_AND_A1_PEDAGOGICALLY_USABLE"]


def admit_candidates(candidates: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    admitted=[]; rejected=[]; deferred=[]
    for candidate in candidates:
        decision, reasons = semantic_decision(candidate)
        if decision == "APPROVE":
            sid = "U02-SENT-" + hashlib.sha256(candidate["normalized_sentence"].encode("utf-8")).hexdigest()[:16].upper()
            admitted.append({"sentence_id": sid, "unit_id": UNIT_ID, "text": candidate["sentence"], "normalized_text": candidate["normalized_sentence"], "canonical_admission_status": "ADMITTED", "pattern_id": candidate["pattern_id"], "np_surface": candidate["np_surface"], "np_variant": candidate["np_variant"], "singular": candidate["singular"], "plural": candidate["plural"], "vocabulary_ids": list(candidate["vocabulary_ids"]), "generation_role": candidate["generation_role"], "direct_unit02_morphology_assessment_allowed": candidate["generation_role"] == "MORPHOLOGY_TARGET", "yle_bands": list(candidate["yle_bands"]), "canonical_levels": list(candidate["canonical_levels"]), "semantic_pedagogical_decision": decision, "decision_reasons": reasons, "source_refs": deepcopy(candidate["source_refs"]), "unit01_deferred_i_have_reuse": bool(candidate.get("unit01_deferred_i_have_reuse")), "legacy_unnormalized": False})
        else:
            memory={"candidate_id": candidate["candidate_id"], "sentence_sha256": hashlib.sha256(candidate["sentence"].encode("utf-8")).hexdigest(), "pattern_id": candidate["pattern_id"], "singular": candidate["singular"], "decision": decision, "reason_codes": reasons}
            (rejected if decision == "REJECT" else deferred).append(memory)
    if len({x["sentence_id"] for x in admitted}) != len(admitted) or len({x["normalized_text"] for x in admitted}) != len(admitted):
        raise U02SA01R1BuildError("ADMITTED_SENTENCE_IDENTITY_NOT_DISTINCT")
    return {"admitted": admitted, "rejected": rejected, "deferred": deferred}



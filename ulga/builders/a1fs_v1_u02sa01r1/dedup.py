from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping, Sequence
from .constants import *
from .common import *
def apply_private_cumulative_dedup(manifest: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    receipt = deepcopy(dict(manifest.get("private_cumulative_dedup_receipt") or {}))
    if receipt.get("full_private_replay_performed") is not True:
        raise U02SA01R1BuildError("PRIVATE_REPLAY_REQUIRED")
    if receipt.get("unit01_sentence_pool_count") != EXPECTED_UNIT01_SENTENCE_ASSETS:
        raise U02SA01R1BuildError("PRIVATE_REPLAY_POOL_COUNT_DRIFT")
    if receipt.get("unit01_exact_identity_count") != EXPECTED_UNIT01_EXACT_TEXT_IDENTITIES or receipt.get("unit01_normalized_identity_count") != EXPECTED_UNIT01_NORMALIZED_TEXT_IDENTITIES:
        raise U02SA01R1BuildError("PRIVATE_REPLAY_IDENTITY_COUNT_DRIFT")
    if receipt.get("unit01_direct_u02_plain_s_plural_sentence_asset_count") != 0 or receipt.get("unit01_direct_u02_new_pattern_sentence_asset_count") != 0:
        raise U02SA01R1BuildError("PRIVATE_REPLAY_STRUCTURAL_OVERLAP_NONZERO")
    if receipt.get("exact_overlap_count") != 0 or receipt.get("normalized_overlap_count") != 0:
        raise U02SA01R1BuildError("PRIVATE_REPLAY_OVERLAP_NONZERO")
    if receipt.get("private_sentence_bodies_committed") is not False or receipt.get("private_sentence_fingerprints_committed") is not False:
        raise U02SA01R1BuildError("PRIVATE_EVIDENCE_LEAK")
    allowed = set(PATTERN_TEMPLATES)
    for row in candidates:
        if row.get("pattern_id") not in allowed or row.get("np_is_plural") is not True:
            raise U02SA01R1BuildError("CANDIDATE_OUTSIDE_ZERO_OVERLAP_STRUCTURAL_DOMAIN")
    receipt["evaluated_candidate_count"] = len(candidates)
    receipt["new_after_cumulative_dedup_count"] = len(candidates)
    receipt["structural_domain_candidate_digest"] = digest([{"pattern_id": r["pattern_id"], "normalized_sentence": r["normalized_sentence"]} for r in candidates])
    return [dict(row, cumulative_dedup_state="NEW_CANDIDATE") for row in candidates], receipt



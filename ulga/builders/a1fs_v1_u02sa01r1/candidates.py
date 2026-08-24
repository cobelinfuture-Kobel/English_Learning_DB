from __future__ import annotations
import hashlib
from copy import deepcopy
from typing import Any, Mapping, Sequence
from .constants import *
from .common import *
from .np_inventory import _deferred_i_have_surfaces
def build_candidates(manifest: Mapping[str, Any], np_inventory: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    deferred_surfaces = _deferred_i_have_surfaces(manifest)
    rows = []
    for np in np_inventory:
        for pattern_id, template in PATTERN_TEMPLATES.items():
            sentence = template.format(np=np["np_surface"])
            normalized = normalize_sentence(sentence)
            rows.append({"candidate_id": "U02-CAND-" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20].upper(), "sentence": sentence, "normalized_sentence": normalized, "pattern_id": pattern_id, "np_surface": np["np_surface"], "np_variant": np["np_variant"], "singular": np["singular"], "plural": np["plural"], "vocabulary_ids": list(np["vocabulary_ids"]), "generation_role": np["generation_role"], "yle_bands": list(np["yle_bands"]), "review_required": np["review_required"], "canonical_levels": list(np["canonical_levels"]), "numeric_determiner": bool(np["numeric_determiner"]), "np_is_plural": bool(np["np_is_plural"]), "source_refs": deepcopy(np["source_refs"]), "unit01_deferred_i_have_reuse": pattern_id == "SP_000003" and (normalize_surface(np["singular"]) in deferred_surfaces or normalize_surface(np["np_surface"]) in deferred_surfaces)})
    ids = [row["candidate_id"] for row in rows]
    texts = [row["normalized_sentence"] for row in rows]
    if len(ids) != len(set(ids)) or len(texts) != len(set(texts)):
        raise U02SA01R1BuildError("GENERATED_CANDIDATE_IDENTITY_NOT_DISTINCT")
    return rows



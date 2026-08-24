from __future__ import annotations
from typing import Any, Mapping, Sequence
from ulga.builders import build_a1fs_v1_u02ch01_unit02_native_chunk_assets as u02ch01
from .constants import *
from .common import *
def build_np_inventory(manifest: Mapping[str, Any], universe: Mapping[str, Any]) -> list[dict[str, Any]]:
    nps: dict[str, dict[str, Any]] = {}
    def add(np_surface: str, variant: str, noun: Mapping[str, Any], source_ref: Mapping[str, Any], numeric: bool = False, modifiers: Sequence[str] = ()):
        key = normalize_surface(np_surface)
        value = nps.get(key)
        if value is None:
            nps[key] = {"np_surface": np_surface, "normalized_np": key, "np_variant": variant, "singular": noun["surface"], "plural": noun["plural"], "vocabulary_ids": list(noun["vocabulary_ids"]), "generation_role": noun["role"], "yle_bands": list(noun.get("yle_bands", [])), "review_required": bool(noun.get("review_required")), "canonical_levels": list(noun.get("canonical_levels", [])), "numeric_determiner": numeric, "modifiers": list(modifiers), "source_refs": [dict(source_ref)], "np_is_plural": True}
        else:
            value["source_refs"].append(dict(source_ref))
            value["vocabulary_ids"] = sorted(set(value["vocabulary_ids"]) | set(noun["vocabulary_ids"]))
            if noun["role"] == "MORPHOLOGY_TARGET":
                value["generation_role"] = "MORPHOLOGY_TARGET"
    for noun in universe["all_valid"]:
        add(noun["plural"], "BARE_PLURAL", noun, {"source_type": "DYNAMIC_GENERATION_UNIVERSE"})
        add(f"two {noun['plural']}", "NUM_PLURAL", noun, {"source_type": "DYNAMIC_GENERATION_UNIVERSE"}, numeric=True)

    # Reuse Unit01 adjective/very structure without exposing private sentence bodies or sentence IDs.
    for seed in manifest.get("unit01_i_can_see_structural_seeds", []):
        key = normalize_surface(seed.get("canonical_surface") or "")
        noun = universe["by_surface"].get(key)
        if noun is None:
            continue
        modifiers = [str(x) for x in seed.get("modifiers", []) if str(x).strip()]
        if seed.get("very") and modifiers and normalize_surface(modifiers[0]) != "very":
            modifiers = ["very", *modifiers]
        if not modifiers:
            continue
        surface = " ".join([*modifiers, noun["plural"]])
        add(surface, "UNIT01_MODIFIER_REUSE_PLURAL", noun, {"source_type": "UNIT01_I_CAN_SEE_STRUCTURAL_REUSE", "authority_sha256": UNIT01_SENTENCE_POOL_SHA256}, modifiers=modifiers)

    chunks = u02ch01.build_assets()
    if len(chunks) != EXPECTED_U02_NATIVE_CHUNKS:
        raise U02SA01R1BuildError(f"U02_NATIVE_CHUNK_COUNT_DRIFT:{len(chunks)}")
    for asset in chunks:
        slots = dict(asset.get("lexical_slots") or {})
        singular = normalize_surface(slots.get("singular_noun") or "")
        noun = universe["by_surface"].get(singular)
        surface = str(asset.get("surface") or "").strip()
        if noun is None or not surface:
            continue
        add(surface, "U02_NATIVE_CHUNK", noun, {"source_type": "U02CH01_NATIVE_CHUNK", "asset_id": asset.get("asset_id")}, numeric=normalize_surface(slots.get("determiner") or "") == "two", modifiers=[str(slots.get("adjective"))] if slots.get("adjective") else [])
    return [nps[key] for key in sorted(nps)]


def _deferred_i_have_surfaces(manifest: Mapping[str, Any]) -> set[str]:
    return {normalize_surface(x) for x in manifest.get("unit01_deferred_i_have_np_surfaces", [])}



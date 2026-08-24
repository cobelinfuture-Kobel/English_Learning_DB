from __future__ import annotations
from typing import Any
from ulga.builders import build_a1fs_v1_u02sp02_unit01_unit02_exact_sentence_frame_coverage_recheck as u02sp02
from .constants import *
from .common import *
from .universe import build_generation_universe
from .np_inventory import build_np_inventory
from .candidates import build_candidates
from .dedup import apply_private_cumulative_dedup
from .admission import admit_candidates

def build_production() -> dict[str, Any]:
    manifest = load_manifest(); vocabulary = load_vocabulary()
    # Q5 authority check: the four new families must remain canonical; no grammar widening.
    q5 = u02sp02.build_report()
    new_ids = sorted(u02sp02.UNIT02_NEW_CANONICAL_PATTERNS)
    if new_ids != sorted(EXPECTED_NEW_PATTERN_IDS):
        raise U02SA01R1BuildError(f"Q5_PATTERN_AUTHORITY_DRIFT:{new_ids}")
    universe = build_generation_universe(manifest, vocabulary)
    np_inventory = build_np_inventory(manifest, universe)
    generated = build_candidates(manifest, np_inventory)
    after_dedup, dedup_receipt = apply_private_cumulative_dedup(manifest, generated)
    decisions = admit_candidates(after_dedup)
    return {"manifest": manifest, "universe": universe, "np_inventory": np_inventory, "generated": generated, "dedup_receipt": dedup_receipt, "q5": q5, **decisions}

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from builders.build_ket_data_s6_image_language_derivation import (
    EXPECTED_RECORD_COUNT,
    EXPECTED_SCENE_COUNT,
    OUTPUT_SCHEMA,
    TASK_ID,
    materialize,
)

STATUS = "PASS_KET_DATA_S6_CORE_BRIDGE"
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class S6Error(ValueError):
    pass


def _root(root=None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1])


def validate(root=None) -> dict:
    root = _root(root)
    out = materialize(root)
    errors = []
    records = out.get("language_assets") or []
    if out.get("schema") != OUTPUT_SCHEMA or out.get("task_id") != TASK_ID:
        errors.append("TOP_CONTRACT")
    if out.get("source_stage") != "KET_DATA_S5" or out.get("output_stage") != "KET_DATA_S6":
        errors.append("STAGE_CHAIN")
    if out.get("contract_source") != "KET_S6_1.txt":
        errors.append("CONTRACT_SOURCE")
    if len(records) != EXPECTED_RECORD_COUNT:
        errors.append("RECORD_COUNT")
    expected_ids = [f"KET_S6_LANG_{i:06d}" for i in range(1, EXPECTED_RECORD_COUNT + 1)]
    if [x.get("language_asset_id") for x in records] != expected_ids:
        errors.append("LANGUAGE_ASSET_ID_SEQUENCE")

    seen = set()
    levels = Counter()
    a1_scene_ids = set()
    for row in records:
        rid = row.get("language_asset_id", "?")
        key = (row.get("image_asset_id"), row.get("derivation_target_level"), row.get("sentence"))
        if key in seen:
            errors.append(f"DUPLICATE_LANGUAGE_ASSET:{rid}")
        seen.add(key)
        levels[row.get("derivation_target_level")] += 1
        if row.get("derivation_target_level") == "A1":
            a1_scene_ids.add(row.get("image_asset_id"))
        if row.get("source_exam_context") != "KET_A2":
            errors.append(f"SOURCE_CONTEXT:{rid}")
        if row.get("semantic_engine") != "GPT-5.6 Sol" or row.get("prompt_contract_version") != "KET_S6_V1":
            errors.append(f"ENGINE:{rid}")
        if row.get("candidate_source") != "GPT-5.6_SOL_FROZEN_CANDIDATE":
            errors.append(f"CANDIDATE_SOURCE:{rid}")
        if row.get("semantic_review_status") != "APPROVED_FOR_DETERMINISTIC_ADMISSION_CHECK":
            errors.append(f"SEMANTIC_REVIEW:{rid}")
        if row.get("derivation_status") != "ADMITTED" or row.get("validation_status") != "PASS":
            errors.append(f"ADMISSION:{rid}")
        if row.get("learner_facing") is not False:
            errors.append(f"LEARNER_FACING:{rid}")
        if not DIGEST_RE.fullmatch(row.get("input_semantic_digest") or "") or not DIGEST_RE.fullmatch(row.get("candidate_digest") or ""):
            errors.append(f"DIGEST:{rid}")
        fact_refs = row.get("fact_refs") or []
        if not fact_refs or any("[" in x or "]" in x for x in fact_refs):
            errors.append(f"FACT_REF:{rid}")
        if not all(x.startswith(row.get("image_asset_id", "") + "#") for x in fact_refs):
            errors.append(f"FACT_REF_IMAGE:{rid}")
        if not row.get("pattern_refs") or not all(x.startswith("pattern:") for x in row["pattern_refs"]):
            errors.append(f"PATTERN_REFS:{rid}")
        if not row.get("grammar_refs") or not all(x.startswith("grammar:") for x in row["grammar_refs"]):
            errors.append(f"GRAMMAR_REFS:{rid}")
        if not row.get("egp_source_refs") or len(row["egp_source_refs"]) != len(row["grammar_refs"]):
            errors.append(f"EGP_REFS:{rid}")
        if not row.get("vocabulary_refs") or not all(re.fullmatch(r"v_\d+", x or "") for x in row["vocabulary_refs"]):
            errors.append(f"VOCAB_REFS:{rid}")
        for binding in row.get("vocabulary_bindings") or []:
            if binding.get("binding_precision") != "LEMMA_POS_LEVEL_CANONICAL_SET":
                errors.append(f"VOCAB_PRECISION:{rid}")
            if not binding.get("source_fact_ref", "").startswith(row.get("image_asset_id", "") + "#"):
                errors.append(f"VOCAB_FACT_REF:{rid}")

    summary = out.get("summary") or {}
    if summary.get("scene_source_count") != EXPECTED_SCENE_COUNT:
        errors.append("SCENE_SOURCE_COUNT")
    if summary.get("scene_images_with_a1_asset") != EXPECTED_SCENE_COUNT or len(a1_scene_ids) != EXPECTED_SCENE_COUNT:
        errors.append("A1_SCENE_COVERAGE")
    if summary.get("language_asset_count") != EXPECTED_RECORD_COUNT:
        errors.append("SUMMARY_RECORD_COUNT")
    if summary.get("target_level_counts") != {"A1": 15, "A1_plus": 1} or dict(levels) != {"A1": 15, "A1_plus": 1}:
        errors.append("TARGET_LEVEL_COUNTS")
    if summary.get("non_scene_language_asset_count") != 0:
        errors.append("NON_SCENE_LANGUAGE_ASSET")
    if summary.get("new_image_identity_count") != 0:
        errors.append("NEW_IMAGE_IDENTITY")
    if summary.get("live_model_call_count") != 0:
        errors.append("LIVE_MODEL_CALL")

    engine = out.get("semantic_engine_contract") or {}
    if engine.get("live_model_call_in_ci") is not False or engine.get("frozen_candidate_required") is not True:
        errors.append("MODEL_REPRODUCIBILITY_CONTRACT")
    policy = out.get("language_asset_policy") or {}
    if policy.get("learner_facing") is not False or policy.get("question_generation_allowed") is not False:
        errors.append("LEARNER_BOUNDARY")
    if policy.get("index_based_fact_refs_allowed") is not False:
        errors.append("INDEX_FACT_REF_POLICY")

    if errors:
        raise S6Error("\n".join(errors[:100]))
    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "scene_source_count": summary["scene_source_count"],
        "scene_images_with_a1_asset": summary["scene_images_with_a1_asset"],
        "language_asset_count": summary["language_asset_count"],
        "a1_asset_count": levels["A1"],
        "a1_plus_asset_count": levels["A1_plus"],
        "s5_fact_lineage": True,
        "grammar_dual_identity_bridge": True,
        "vocabulary_authority_binding": True,
        "live_model_call_count": 0,
        "new_image_identity_count": 0,
        "learner_facing": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2))
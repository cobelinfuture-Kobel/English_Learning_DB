from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from builders.build_ket_data_s7_image_multiple_task_family_projection import (
    EXPECTED_IMAGE_ASSET_COUNT,
    EXPECTED_LANGUAGE_ASSET_COUNT,
    EXPECTED_SHELLS_PER_LANGUAGE_ASSET,
    EXPECTED_TASK_SHELL_COUNT,
    OUTPUT_SCHEMA,
    TASK_ID,
    materialize,
)

STATUS = "PASS_KET_DATA_S7_IMAGE_MULTIPLE_TASK_FAMILY_PROJECTION"
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class S7Error(ValueError):
    pass


def _root(root=None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1])


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(root=None) -> dict:
    root = _root(root)
    out = materialize(root)
    errors = []
    rows = out.get("task_shells") or []
    if out.get("schema") != OUTPUT_SCHEMA or out.get("task_id") != TASK_ID:
        errors.append("TOP_CONTRACT")
    if out.get("source_stage") != "KET_DATA_S6" or out.get("output_stage") != "KET_DATA_S7":
        errors.append("STAGE_CHAIN")
    if out.get("contract_source") != "KET_S7.txt":
        errors.append("CONTRACT_SOURCE")
    if len(rows) != EXPECTED_TASK_SHELL_COUNT:
        errors.append("TASK_SHELL_COUNT")

    taxonomy = _json(root / "data" / "ket" / "ket_s3_unified_assessment_taxonomy.json")
    layers = taxonomy.get("layers") or {}
    response_modes = set((layers.get("response_mode") or {}).get("values") or [])
    task_families = set((layers.get("task_family") or {}).get("values") or [])
    modalities = set((layers.get("stimulus_modality") or {}).get("values") or [])
    capabilities = set((layers.get("assessment_capability") or {}).get("values") or [])
    response_formats = set((layers.get("response_format") or {}).get("values") or [])

    ids = [x.get("task_shell_id") for x in rows]
    expected_ids = [f"KET_S7_TASK_{i:06d}" for i in range(1, EXPECTED_TASK_SHELL_COUNT + 1)]
    if ids != expected_ids:
        errors.append("TASK_SHELL_ID_SEQUENCE")

    by_language = defaultdict(list)
    by_image = defaultdict(list)
    levels_by_image = defaultdict(set)
    modes = Counter()
    levels = Counter()
    families = Counter()
    for row in rows:
        rid = row.get("task_shell_id", "?")
        by_language[row.get("source_language_asset_id")].append(row)
        by_image[row.get("source_image_asset_id")].append(row)
        levels_by_image[row.get("source_image_asset_id")].add(row.get("derivation_target_level"))
        modes[(row.get("s3_classification") or {}).get("response_mode")] += 1
        levels[row.get("derivation_target_level")] += 1
        families[row.get("derived_task_family")] += 1

        if row.get("source_stage") != "KET_DATA_S6":
            errors.append(f"SOURCE_STAGE:{rid}")
        if row.get("source_exam_context") != "KET_A2":
            errors.append(f"SOURCE_CONTEXT:{rid}")
        if row.get("authority_scope") != "DERIVED_PRACTICE_NOT_CURRENT_KET_CANONICAL":
            errors.append(f"AUTHORITY_SCOPE:{rid}")
        if row.get("materialization_status") != "TASK_SHELL_ONLY" or row.get("validation_status") != "PASS":
            errors.append(f"MATERIALIZATION_STATUS:{rid}")
        if row.get("learner_facing") is not False:
            errors.append(f"LEARNER_FACING:{rid}")
        if row.get("question_bank_item") is not False:
            errors.append(f"QUESTION_BANK_ITEM:{rid}")
        if row.get("current_ket_canonical_mechanic") is not False:
            errors.append(f"CANONICAL_PROMOTION:{rid}")
        if not DIGEST_RE.fullmatch(row.get("task_shell_digest") or ""):
            errors.append(f"DIGEST:{rid}")

        c = row.get("s3_classification") or {}
        if c.get("response_mode") not in response_modes:
            errors.append(f"RESPONSE_MODE:{rid}")
        if c.get("stimulus_modality") not in modalities:
            errors.append(f"STIMULUS_MODALITY:{rid}")
        if c.get("response_format") not in response_formats:
            errors.append(f"RESPONSE_FORMAT:{rid}")
        caps = c.get("assessment_capabilities") or []
        if not caps or any(x not in capabilities for x in caps):
            errors.append(f"ASSESSMENT_CAPABILITY:{rid}")
        task_ref = c.get("task_family_ref")
        if task_ref is not None and task_ref not in task_families:
            errors.append(f"TASK_FAMILY_REF:{rid}")
        if task_ref is not None:
            errors.append(f"CANONICAL_TASK_FAMILY_PROMOTION:{rid}")
        if c.get("task_family_binding_status") != "UNBOUND_DERIVED_PRACTICE":
            errors.append(f"TASK_FAMILY_BINDING_STATUS:{rid}")

        lineage = row.get("authority_lineage") or {}
        if lineage.get("image_asset_id") != row.get("source_image_asset_id"):
            errors.append(f"IMAGE_LINEAGE:{rid}")
        if lineage.get("language_asset_id") != row.get("source_language_asset_id"):
            errors.append(f"LANGUAGE_LINEAGE:{rid}")
        fact_refs = lineage.get("fact_refs") or []
        if not fact_refs or not all(
            isinstance(x, str) and x.startswith(row.get("source_image_asset_id", "") + "#")
            for x in fact_refs
        ):
            errors.append(f"FACT_LINEAGE:{rid}")
        if not lineage.get("pattern_refs") or not lineage.get("grammar_refs") or not lineage.get("egp_source_refs"):
            errors.append(f"GRAMMAR_LINEAGE:{rid}")
        if not lineage.get("vocabulary_refs"):
            errors.append(f"VOCABULARY_LINEAGE:{rid}")

    if len(by_language) != EXPECTED_LANGUAGE_ASSET_COUNT:
        errors.append("SOURCE_LANGUAGE_ASSET_COVERAGE")
    if len(by_image) != EXPECTED_IMAGE_ASSET_COUNT:
        errors.append("SOURCE_IMAGE_ASSET_COVERAGE")
    if any(len(v) != EXPECTED_SHELLS_PER_LANGUAGE_ASSET for v in by_language.values()):
        errors.append("SHELLS_PER_LANGUAGE_ASSET")
    expected_modes = {"MATCH", "SELECT", "SPEAK", "STRUCTURED_ENTRY", "TEXT_ENTRY"}
    if set(modes) != expected_modes or any(modes[x] != EXPECTED_LANGUAGE_ASSET_COUNT for x in expected_modes):
        errors.append("RESPONSE_MODE_COVERAGE")
    if set(families.values()) != {EXPECTED_LANGUAGE_ASSET_COUNT} or len(families) != EXPECTED_SHELLS_PER_LANGUAGE_ASSET:
        errors.append("DERIVED_TASK_FAMILY_COVERAGE")

    summary = out.get("summary") or {}
    if summary.get("source_language_asset_count") != EXPECTED_LANGUAGE_ASSET_COUNT:
        errors.append("SUMMARY_LANGUAGE_COUNT")
    if summary.get("source_image_asset_count") != EXPECTED_IMAGE_ASSET_COUNT:
        errors.append("SUMMARY_IMAGE_COUNT")
    if summary.get("task_shell_count") != EXPECTED_TASK_SHELL_COUNT:
        errors.append("SUMMARY_SHELL_COUNT")
    if summary.get("target_level_shell_counts") != {"A1": 75, "A1_plus": 5} or dict(levels) != {"A1": 75, "A1_plus": 5}:
        errors.append("TARGET_LEVEL_COUNTS")
    if summary.get("response_mode_counts") != {
        "MATCH": 16,
        "SELECT": 16,
        "SPEAK": 16,
        "STRUCTURED_ENTRY": 16,
        "TEXT_ENTRY": 16,
    }:
        errors.append("SUMMARY_RESPONSE_MODES")
    if summary.get("image_with_multiple_shell_count") != EXPECTED_IMAGE_ASSET_COUNT:
        errors.append("MULTI_SHELL_IMAGE_COUNT")
    if summary.get("image_with_multiple_level_count") != sum(1 for x in levels_by_image.values() if len(x) > 1) or summary.get("image_with_multiple_level_count") != 1:
        errors.append("MULTI_LEVEL_IMAGE_COUNT")
    for key in (
        "canonical_task_family_promotion_count",
        "learner_facing_task_count",
        "question_bank_item_count",
        "new_image_identity_count",
        "new_language_identity_count",
        "live_model_call_count",
    ):
        if summary.get(key) != 0:
            errors.append(f"ZERO_BOUNDARY:{key}")

    handshake = out.get("s3_handshake") or {}
    if handshake.get("response_mode_redefinition_allowed") is not False:
        errors.append("HANDSHAKE_RESPONSE_MODE")
    if handshake.get("canonical_task_family_promotion_allowed") is not False:
        errors.append("HANDSHAKE_CANONICAL_PROMOTION")
    if handshake.get("derived_practice_family_separate_from_canonical_task_family") is not True:
        errors.append("HANDSHAKE_DERIVED_SEPARATION")

    policy = out.get("projection_policy") or {}
    if policy.get("learner_facing") is not False or policy.get("question_bank_generation_allowed") is not False:
        errors.append("PROJECTION_BOUNDARY")
    if policy.get("task_shell_not_final_question") is not True:
        errors.append("FINAL_QUESTION_BOUNDARY")
    if policy.get("current_ket_canonical_promotion_allowed") is not False:
        errors.append("CURRENT_KET_PROMOTION_BOUNDARY")

    if errors:
        raise S7Error("\n".join(errors[:100]))
    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "source_language_asset_count": summary["source_language_asset_count"],
        "source_image_asset_count": summary["source_image_asset_count"],
        "task_shell_count": summary["task_shell_count"],
        "a1_task_shell_count": levels["A1"],
        "a1_plus_task_shell_count": levels["A1_plus"],
        "response_mode_count": len(modes),
        "derived_task_family_count": len(families),
        "s3_five_layer_handshake": True,
        "s6_authority_lineage_preserved": True,
        "canonical_task_family_promotion_count": 0,
        "learner_facing_task_count": 0,
        "question_bank_item_count": 0,
        "new_image_identity_count": 0,
        "new_language_identity_count": 0,
        "live_model_call_count": 0,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2))

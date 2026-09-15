from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from builders.build_ket_data_s8_task_origin_governance import (
    EXPECTED_A1FS_DERIVED_COUNT,
    EXPECTED_GOVERNED_RECORD_COUNT,
    EXPECTED_SOURCE_EXACT_COUNT,
    EXPECTED_SUPPLEMENTARY_EXCLUDED_COUNT,
    OUTPUT_SCHEMA,
    TASK_ID,
    materialize,
)

STATUS = "PASS_KET_DATA_S8_ORIGINAL_VS_DERIVED_TASK_GOVERNANCE"
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class S8Error(ValueError):
    pass


def _root(root=None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1])


def validate(root=None) -> dict:
    root = _root(root)
    out = materialize(root)
    errors = []
    rows = list(out.get("origin_records") or [])
    summary = out.get("summary") or {}

    if out.get("schema") != OUTPUT_SCHEMA or out.get("task_id") != TASK_ID:
        errors.append("TOP_CONTRACT")
    if out.get("output_stage") != "KET_DATA_S8" or out.get("contract_source") != "KET_S8.txt":
        errors.append("STAGE_CONTRACT")
    if len(rows) != EXPECTED_GOVERNED_RECORD_COUNT:
        errors.append("GOVERNED_RECORD_COUNT")

    expected_ids = [f"KET_S8_ORIGIN_{i:06d}" for i in range(1, EXPECTED_GOVERNED_RECORD_COUNT + 1)]
    if [x.get("origin_record_id") for x in rows] != expected_ids:
        errors.append("ORIGIN_RECORD_ID_SEQUENCE")
    if len({x.get("origin_digest") for x in rows}) != len(rows):
        errors.append("ORIGIN_DIGEST_UNIQUENESS")

    origins = Counter()
    levels = Counter()
    source_exact_ids = set()
    s7_shell_ids = set()
    derived_image_ids = set()

    for row in rows:
        rid = row.get("origin_record_id", "?")
        origin = row.get("task_origin")
        origins[origin] += 1
        if origin not in {"SOURCE_EXACT", "A1FS_DERIVED"}:
            errors.append(f"TASK_ORIGIN:{rid}")
        if not DIGEST_RE.fullmatch(row.get("origin_digest") or ""):
            errors.append(f"DIGEST:{rid}")
        if row.get("learner_facing") is not False:
            errors.append(f"LEARNER_FACING:{rid}")
        if row.get("question_bank_item") is not False:
            errors.append(f"QUESTION_BANK_ITEM:{rid}")
        if row.get("source_task_copied") is not False:
            errors.append(f"SOURCE_TASK_COPY:{rid}")
        if row.get("source_wording_copied") is not False:
            errors.append(f"SOURCE_WORDING_COPY:{rid}")
        if row.get("authority_validation_status") != "PASS":
            errors.append(f"AUTHORITY_VALIDATION_STATUS:{rid}")

        if origin == "SOURCE_EXACT":
            item_id = row.get("source_item_id")
            if not item_id or item_id in source_exact_ids:
                errors.append(f"SOURCE_EXACT_ID:{rid}")
            source_exact_ids.add(item_id)
            if row.get("derived_from") != []:
                errors.append(f"SOURCE_EXACT_DERIVED_FROM:{rid}")
            if row.get("source_task_reference_only") is not True:
                errors.append(f"SOURCE_EXACT_REFERENCE_ONLY:{rid}")
            if row.get("generation_model") is not None or row.get("generation_method") is not None:
                errors.append(f"SOURCE_EXACT_GENERATION:{rid}")
            if row.get("target_level") is not None:
                errors.append(f"SOURCE_EXACT_TARGET_LEVEL:{rid}")
            if row.get("authority_validation") != "SOURCE_AUTHORITY_ALREADY_VALIDATED":
                errors.append(f"SOURCE_EXACT_AUTHORITY:{rid}")
            if row.get("authority_scope") != "CURRENT_KET_CANONICAL_MECHANIC":
                errors.append(f"SOURCE_EXACT_SCOPE:{rid}")
            if row.get("current_ket_canonical_mechanic") is not True:
                errors.append(f"SOURCE_EXACT_CANONICAL:{rid}")
        elif origin == "A1FS_DERIVED":
            shell_id = row.get("s7_task_shell_id")
            if not shell_id or shell_id in s7_shell_ids:
                errors.append(f"S7_SHELL_ID:{rid}")
            s7_shell_ids.add(shell_id)
            derived_from = row.get("derived_from") or []
            if len(derived_from) != 1 or not str(derived_from[0]).startswith("KET_IMG_"):
                errors.append(f"DERIVED_FROM_IMAGE:{rid}")
            else:
                derived_image_ids.add(derived_from[0])
            if row.get("source_item_id") is not None:
                errors.append(f"DERIVED_SOURCE_ITEM:{rid}")
            if row.get("source_task_reference_only") is not False:
                errors.append(f"DERIVED_REFERENCE_ONLY:{rid}")
            if row.get("generation_model") is not None:
                errors.append(f"FALSE_MODEL_PROVENANCE:{rid}")
            if row.get("generation_method") != "DETERMINISTIC_S7_PROJECTION":
                errors.append(f"DERIVED_GENERATION_METHOD:{rid}")
            level = row.get("target_level")
            levels[level] += 1
            if level not in {"A1", "A1_plus"}:
                errors.append(f"DERIVED_TARGET_LEVEL:{rid}")
            if row.get("authority_validation") != "REQUIRED":
                errors.append(f"DERIVED_AUTHORITY_REQUIREMENT:{rid}")
            if row.get("authority_scope") != "A1FS_DERIVED_FROM_KET_IMAGE_EVIDENCE":
                errors.append(f"DERIVED_AUTHORITY_SCOPE:{rid}")
            if row.get("current_ket_canonical_mechanic") is not False:
                errors.append(f"DERIVED_CANONICAL_PROMOTION:{rid}")
            lineage = row.get("authority_lineage") or {}
            if lineage.get("image_asset_id") != derived_from[0]:
                errors.append(f"DERIVED_IMAGE_LINEAGE:{rid}")
            if lineage.get("language_asset_id") != row.get("source_language_asset_id"):
                errors.append(f"DERIVED_LANGUAGE_LINEAGE:{rid}")
            if not lineage.get("fact_refs") or not lineage.get("grammar_refs") or not lineage.get("vocabulary_refs"):
                errors.append(f"DERIVED_AUTHORITY_LINEAGE:{rid}")

    if origins != Counter({"SOURCE_EXACT": EXPECTED_SOURCE_EXACT_COUNT, "A1FS_DERIVED": EXPECTED_A1FS_DERIVED_COUNT}):
        errors.append("TASK_ORIGIN_COUNTS")
    if levels != Counter({"A1": 75, "A1_plus": 5}):
        errors.append("DERIVED_LEVEL_COUNTS")
    if len(source_exact_ids) != EXPECTED_SOURCE_EXACT_COUNT:
        errors.append("SOURCE_EXACT_UNIQUE_COUNT")
    if len(s7_shell_ids) != EXPECTED_A1FS_DERIVED_COUNT:
        errors.append("S7_SHELL_UNIQUE_COUNT")
    if len(derived_image_ids) != 15:
        errors.append("DERIVED_IMAGE_COVERAGE")

    excluded = out.get("excluded_supplementary_practice_item_ids") or []
    if len(excluded) != EXPECTED_SUPPLEMENTARY_EXCLUDED_COUNT or len(set(excluded)) != len(excluded):
        errors.append("SUPPLEMENTARY_EXCLUSION_COUNT")
    if source_exact_ids.intersection(excluded):
        errors.append("SOURCE_EXACT_SUPPLEMENTARY_OVERLAP")

    expected_summary = {
        "governed_record_count": 1440,
        "source_exact_count": 1360,
        "a1fs_derived_count": 80,
        "derived_a1_count": 75,
        "derived_a1_plus_count": 5,
        "supplementary_practice_excluded_count": 92,
        "derived_source_task_copy_count": 0,
        "derived_source_wording_copy_count": 0,
        "derived_current_ket_canonical_promotion_count": 0,
        "learner_facing_count": 0,
        "question_bank_item_count": 0,
        "new_image_identity_count": 0,
        "new_language_identity_count": 0,
        "live_model_call_count": 0,
    }
    if summary != expected_summary:
        errors.append("SUMMARY")

    policy = out.get("origin_policy") or {}
    if policy.get("allowed_task_origins") != ["SOURCE_EXACT", "A1FS_DERIVED"]:
        errors.append("ORIGIN_POLICY")
    if policy.get("derived_source_task_copy_allowed") is not False:
        errors.append("DERIVED_COPY_POLICY")
    if policy.get("derived_source_wording_copy_allowed") is not False:
        errors.append("DERIVED_WORDING_POLICY")
    if policy.get("derived_current_ket_canonical_promotion_allowed") is not False:
        errors.append("DERIVED_PROMOTION_POLICY")
    if policy.get("derived_requires_authority_validation") is not True:
        errors.append("DERIVED_VALIDATION_POLICY")
    if policy.get("supplementary_practice_in_binary_registry") is not False:
        errors.append("SUPPLEMENTARY_BINARY_POLICY")

    if errors:
        raise S8Error("\n".join(errors[:100]))
    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "governed_record_count": summary["governed_record_count"],
        "source_exact_count": summary["source_exact_count"],
        "a1fs_derived_count": summary["a1fs_derived_count"],
        "derived_a1_count": summary["derived_a1_count"],
        "derived_a1_plus_count": summary["derived_a1_plus_count"],
        "supplementary_practice_excluded_count": summary["supplementary_practice_excluded_count"],
        "derived_image_asset_count": len(derived_image_ids),
        "derived_source_task_copy_count": 0,
        "derived_source_wording_copy_count": 0,
        "derived_current_ket_canonical_promotion_count": 0,
        "learner_facing_count": 0,
        "question_bank_item_count": 0,
        "new_image_identity_count": 0,
        "new_language_identity_count": 0,
        "live_model_call_count": 0,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2))

from __future__ import annotations

import json
import re
from pathlib import Path

from builders.build_ket_data_s9_level_adaptation_contract import (
    EXPECTED_CANONICAL_PROFILE_COUNT,
    EXPECTED_SOURCE_EXACT_ITEM_COUNT,
    OUTPUT_SCHEMA,
    TASK_ID,
    materialize,
)

STATUS = "PASS_KET_DATA_S9_LEVEL_ADAPTATION_CONTRACT"
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class S9Error(ValueError):
    pass


def _root(root=None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1])


def validate(root=None) -> dict:
    root = _root(root)
    out = materialize(root)
    errors = []
    rows = list(out.get("adaptation_records") or [])
    summary = out.get("summary") or {}

    if out.get("schema") != OUTPUT_SCHEMA or out.get("task_id") != TASK_ID:
        errors.append("TOP_CONTRACT")
    if out.get("output_stage") != "KET_DATA_S9" or out.get("contract_source") != "KET_S9.txt":
        errors.append("STAGE_CONTRACT")
    if len(rows) != EXPECTED_CANONICAL_PROFILE_COUNT:
        errors.append("PROFILE_COUNT")

    expected_ids = [f"KET_S9_ADAPT_{i:03d}" for i in range(1, EXPECTED_CANONICAL_PROFILE_COUNT + 1)]
    if [x.get("adaptation_record_id") for x in rows] != expected_ids:
        errors.append("RECORD_ID_SEQUENCE")
    if len({x.get("semantic_profile_id") for x in rows}) != len(rows):
        errors.append("PROFILE_ID_UNIQUENESS")
    if len({x.get("adaptation_digest") for x in rows}) != len(rows):
        errors.append("DIGEST_UNIQUENESS")

    guided_rows = []
    for row in rows:
        rid = row.get("adaptation_record_id", "?")
        if not DIGEST_RE.fullmatch(row.get("adaptation_digest") or ""):
            errors.append(f"DIGEST:{rid}")
        if row.get("authority_scope") != "CURRENT_KET_CANONICAL_MECHANIC":
            errors.append(f"AUTHORITY_SCOPE:{rid}")
        if row.get("NATIVE_LEVEL") != "A2_KET":
            errors.append(f"NATIVE_LEVEL:{rid}")
        if row.get("ADAPTABLE_DOWN") is not True:
            errors.append(f"ADAPTABLE_DOWN:{rid}")
        if row.get("MIN_ADAPTED_LEVEL") != "A1":
            errors.append(f"MIN_ADAPTED_LEVEL:{rid}")
        if row.get("ADAPTATION_RULE") != "PRESERVE_S3_MECHANIC_REDUCE_RESPONSE_DEMAND":
            errors.append(f"ADAPTATION_RULE:{rid}")
        if row.get("adapted_output_origin") != "A1FS_DERIVED":
            errors.append(f"ADAPTED_ORIGIN:{rid}")
        if row.get("current_ket_canonical_promotion_allowed") is not False:
            errors.append(f"CANONICAL_PROMOTION:{rid}")
        if row.get("learner_facing_task_materialized") is not False:
            errors.append(f"LEARNER_FACING:{rid}")
        if row.get("question_bank_item_materialized") is not False:
            errors.append(f"QUESTION_BANK:{rid}")
        if not row.get("response_mode") or not row.get("task_family") or not row.get("stimulus_modality"):
            errors.append(f"S3_MECHANIC_IDENTITY:{rid}")
        if not row.get("assessment_capabilities"):
            errors.append(f"S3_CAPABILITY:{rid}")
        if int(row.get("source_exact_item_count") or 0) <= 0:
            errors.append(f"SOURCE_EXACT_COVERAGE:{rid}")
        if row.get("concrete_level_projection") is not None:
            guided_rows.append(row)

    if sum(x.get("source_exact_item_count", 0) for x in rows) != EXPECTED_SOURCE_EXACT_ITEM_COUNT:
        errors.append("SOURCE_EXACT_TOTAL")
    if len(guided_rows) != 1:
        errors.append("CONCRETE_SOURCE_EXAMPLE_COUNT")
    else:
        guided = guided_rows[0]
        if guided.get("semantic_profile_id") != "KET_S2_TASK_006":
            errors.append("GUIDED_PROFILE")
        if guided.get("task_family") != "GUIDED_MESSAGE":
            errors.append("GUIDED_TASK_FAMILY")
        if guided.get("response_mode") != "TEXT_ENTRY":
            errors.append("GUIDED_RESPONSE_MODE")
        if guided.get("native_response_format") != "25_PLUS_WORD_MESSAGE":
            errors.append("GUIDED_NATIVE_FORMAT")
        if "WRITE_TO_MULTIPLE_CONTENT_POINTS" not in guided.get("assessment_capabilities", []):
            errors.append("GUIDED_CAPABILITY")
        projection = guided.get("concrete_level_projection") or {}
        if list(projection) != ["A1", "A1_plus", "A2_KET"]:
            errors.append("GUIDED_LEVEL_SEQUENCE")
        if projection.get("A1", {}).get("response_expectation") != "2_SENTENCES":
            errors.append("GUIDED_A1")
        if projection.get("A1_plus", {}).get("response_expectation") != "3_SENTENCES":
            errors.append("GUIDED_A1_PLUS")
        if projection.get("A2_KET", {}).get("response_expectation") != "25_PLUS_WORD_MESSAGE":
            errors.append("GUIDED_A2_KET")

    expected_summary = {
        "canonical_mechanic_profile_count": 14,
        "source_exact_item_count_covered": 1360,
        "adaptable_down_profile_count": 14,
        "min_adapted_level_a1_profile_count": 14,
        "concrete_source_example_profile_count": 1,
        "supplementary_practice_profile_count_admitted": 0,
        "learner_facing_task_count": 0,
        "question_bank_item_count": 0,
        "new_a2_content_count": 0,
        "live_model_call_count": 0,
    }
    if summary != expected_summary:
        errors.append("SUMMARY")

    policy = out.get("level_adaptation_policy") or {}
    if policy.get("level_sequence") != ["A1", "A1_plus", "A2_KET"]:
        errors.append("LEVEL_SEQUENCE")
    if policy.get("preserve_s3_response_mode") is not True:
        errors.append("PRESERVE_RESPONSE_MODE")
    if policy.get("preserve_s3_task_family") is not True:
        errors.append("PRESERVE_TASK_FAMILY")
    if policy.get("preserve_s3_stimulus_modality") is not True:
        errors.append("PRESERVE_STIMULUS_MODALITY")
    if policy.get("preserve_s3_assessment_capabilities") is not True:
        errors.append("PRESERVE_CAPABILITY")
    if policy.get("response_format_may_adapt") is not True:
        errors.append("RESPONSE_FORMAT_ADAPTATION")
    if policy.get("source_exact_origin_must_remain_source_exact") is not True:
        errors.append("SOURCE_EXACT_ORIGIN")
    if policy.get("adapted_output_origin_must_be_a1fs_derived") is not True:
        errors.append("DERIVED_ORIGIN")
    if policy.get("supplementary_practice_profiles_admitted") is not False:
        errors.append("SUPPLEMENTARY_SCOPE")
    if policy.get("learner_facing_generation_allowed") is not False:
        errors.append("LEARNER_FACING_POLICY")
    if policy.get("question_bank_generation_allowed") is not False:
        errors.append("QUESTION_BANK_POLICY")
    if policy.get("live_model_call_in_ci") is not False:
        errors.append("LIVE_MODEL_POLICY")

    if errors:
        raise S9Error("\n".join(errors[:100]))
    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "canonical_mechanic_profile_count": summary["canonical_mechanic_profile_count"],
        "source_exact_item_count_covered": summary["source_exact_item_count_covered"],
        "adaptable_down_profile_count": summary["adaptable_down_profile_count"],
        "min_adapted_level": "A1",
        "native_level": "A2_KET",
        "concrete_source_example_profile_count": summary["concrete_source_example_profile_count"],
        "learner_facing_task_count": 0,
        "question_bank_item_count": 0,
        "new_a2_content_count": 0,
        "live_model_call_count": 0,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2))

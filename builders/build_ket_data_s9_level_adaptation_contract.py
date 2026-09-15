from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

TASK_ID = "KET_Data_S9_LevelAdaptationContract"
CONTRACT_SCHEMA = "ket.data.s9.level_adaptation_contract.v1"
OUTPUT_SCHEMA = "ket.data.s9.level_adaptation_registry.v1"
EXPECTED_CANONICAL_PROFILE_COUNT = 14
EXPECTED_SOURCE_EXACT_ITEM_COUNT = 1360


class S9BuildError(ValueError):
    pass


def _root(root=None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1])


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _sha256_json(value) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def materialize(root=None, *, output_path=None) -> dict:
    root = _root(root)
    contract = _json(root / "data" / "ket" / "ket_s9_level_adaptation_contract.json")
    if (
        contract.get("schema"),
        contract.get("task_id"),
        contract.get("output_stage"),
        contract.get("contract_source"),
    ) != (
        CONTRACT_SCHEMA,
        TASK_ID,
        "KET_DATA_S9",
        "KET_S9.txt",
    ):
        raise S9BuildError("CONTRACT")

    pred = contract.get("predecessors") or {}
    s3_path = root / pred["s3_taxonomy_path"]
    s8_contract_path = root / pred["s8_contract_path"]
    if _git_blob_sha(s8_contract_path.read_bytes()) != pred.get("s8_contract_git_blob_sha"):
        raise S9BuildError("S8_CONTRACT_BLOB_DRIFT")

    s3 = _json(s3_path)
    if s3.get("task_id") != "KET_Data_S3_UnifiedFiveLayerAssessmentTaxonomy":
        raise S9BuildError("S3_TASK_ID")
    if s3.get("layer_order") != [
        "response_mode",
        "task_family",
        "stimulus_modality",
        "assessment_capability",
        "response_format",
    ]:
        raise S9BuildError("S3_LAYER_ORDER")

    policy = contract.get("level_adaptation_policy") or {}
    if policy.get("level_sequence") != ["A1", "A1_plus", "A2_KET"]:
        raise S9BuildError("LEVEL_SEQUENCE")
    if policy.get("native_level") != "A2_KET":
        raise S9BuildError("NATIVE_LEVEL")
    if policy.get("adaptable_down") is not True:
        raise S9BuildError("ADAPTABLE_DOWN")
    if policy.get("min_adapted_level") != "A1":
        raise S9BuildError("MIN_ADAPTED_LEVEL")
    if policy.get("adaptation_rule") != "PRESERVE_S3_MECHANIC_REDUCE_RESPONSE_DEMAND":
        raise S9BuildError("ADAPTATION_RULE")
    for key in (
        "preserve_s3_response_mode",
        "preserve_s3_task_family",
        "preserve_s3_stimulus_modality",
        "preserve_s3_assessment_capabilities",
        "response_format_may_adapt",
        "language_load_may_reduce",
        "content_point_load_may_reduce",
        "scaffolding_may_increase",
        "source_exact_origin_must_remain_source_exact",
        "adapted_output_origin_must_be_a1fs_derived",
        "adapted_output_must_not_be_promoted_to_current_ket_canonical",
    ):
        if policy.get(key) is not True:
            raise S9BuildError(f"POLICY_TRUE_REQUIRED:{key}")
    for key in (
        "supplementary_practice_profiles_admitted",
        "learner_facing_generation_allowed",
        "question_bank_generation_allowed",
        "live_model_call_in_ci",
    ):
        if policy.get(key) is not False:
            raise S9BuildError(f"POLICY_FALSE_REQUIRED:{key}")
    if policy.get("current_materialization_scope") != "CONTRACT_AND_COVERAGE_ONLY":
        raise S9BuildError("MATERIALIZATION_SCOPE")

    from builders.build_ket_data_s8_task_origin_governance import materialize as materialize_s8

    s8 = materialize_s8(root)
    source_exact = [
        x for x in (s8.get("origin_records") or [])
        if x.get("task_origin") == "SOURCE_EXACT"
    ]
    if len(source_exact) != EXPECTED_SOURCE_EXACT_ITEM_COUNT:
        raise S9BuildError("SOURCE_EXACT_COUNT")
    if len(source_exact) != pred.get("expected_source_exact_item_count"):
        raise S9BuildError("SOURCE_EXACT_CONTRACT_COUNT")

    profiles = [
        x for x in (s3.get("profile_normalizations") or [])
        if x.get("authority_scope") == "CURRENT_KET_CANONICAL_MECHANIC"
        and str(x.get("semantic_profile_id") or "").startswith("KET_S2_TASK_")
    ]
    profiles = sorted(profiles, key=lambda x: x["semantic_profile_id"])
    if len(profiles) != EXPECTED_CANONICAL_PROFILE_COUNT:
        raise S9BuildError("CANONICAL_PROFILE_COUNT")
    if len(profiles) != pred.get("expected_current_ket_canonical_profile_count"):
        raise S9BuildError("CANONICAL_PROFILE_CONTRACT_COUNT")

    item_counts = Counter(x.get("semantic_profile_id") for x in source_exact)
    profile_ids = {x["semantic_profile_id"] for x in profiles}
    if set(item_counts) != profile_ids:
        raise S9BuildError("SOURCE_EXACT_PROFILE_COVERAGE")
    if sum(item_counts.values()) != EXPECTED_SOURCE_EXACT_ITEM_COUNT:
        raise S9BuildError("SOURCE_EXACT_PROFILE_TOTAL")

    guided = contract.get("guided_message_source_example") or {}
    if guided.get("source_capability_label") != "WRITE_GUIDED_MESSAGE":
        raise S9BuildError("GUIDED_SOURCE_LABEL")
    if guided.get("s3_semantic_profile_id") != "KET_S2_TASK_006":
        raise S9BuildError("GUIDED_PROFILE")
    expected_guided = {
        "A1": {
            "instruction": "Tell Ben where these things are. Write 2 sentences.",
            "response_expectation": "2_SENTENCES",
        },
        "A1_plus": {
            "instruction": "Write 3 sentences to Ben. Tell him where his bag, book and shoes are.",
            "response_expectation": "3_SENTENCES",
        },
        "A2_KET": {
            "instruction": "Write the complete message according to the official-style content-point requirements.",
            "response_expectation": "25_PLUS_WORD_MESSAGE",
        },
    }
    if guided.get("adaptations") != expected_guided:
        raise S9BuildError("GUIDED_ADAPTATION_SOURCE_DRIFT")

    records = []
    for index, profile in enumerate(profiles, start=1):
        normalized = profile.get("normalized_values") or {}
        profile_id = profile["semantic_profile_id"]
        record = {
            "adaptation_record_id": f"KET_S9_ADAPT_{index:03d}",
            "semantic_profile_id": profile_id,
            "authority_scope": profile["authority_scope"],
            "response_mode": normalized.get("response_mode"),
            "task_family": normalized.get("task_family"),
            "stimulus_modality": normalized.get("stimulus_modality"),
            "assessment_capabilities": list(normalized.get("assessment_capabilities") or []),
            "native_response_format": normalized.get("response_format"),
            "source_exact_item_count": item_counts[profile_id],
            "NATIVE_LEVEL": policy["native_level"],
            "ADAPTABLE_DOWN": policy["adaptable_down"],
            "MIN_ADAPTED_LEVEL": policy["min_adapted_level"],
            "ADAPTATION_RULE": policy["adaptation_rule"],
            "adapted_output_origin": "A1FS_DERIVED",
            "current_ket_canonical_promotion_allowed": False,
            "learner_facing_task_materialized": False,
            "question_bank_item_materialized": False,
            "concrete_level_projection": None,
        }
        if profile_id == guided["s3_semantic_profile_id"]:
            if normalized.get("task_family") != guided.get("s3_task_family"):
                raise S9BuildError("GUIDED_TASK_FAMILY")
            if normalized.get("response_mode") != guided.get("s3_response_mode"):
                raise S9BuildError("GUIDED_RESPONSE_MODE")
            if normalized.get("stimulus_modality") != guided.get("s3_stimulus_modality"):
                raise S9BuildError("GUIDED_STIMULUS")
            if guided.get("s3_assessment_capability") not in record["assessment_capabilities"]:
                raise S9BuildError("GUIDED_CAPABILITY")
            if normalized.get("response_format") != guided.get("native_response_format"):
                raise S9BuildError("GUIDED_RESPONSE_FORMAT")
            record["source_capability_label"] = guided["source_capability_label"]
            record["concrete_level_projection"] = guided["adaptations"]
        record["adaptation_digest"] = _sha256_json(record)
        records.append(record)

    summary = {
        "canonical_mechanic_profile_count": len(records),
        "source_exact_item_count_covered": sum(x["source_exact_item_count"] for x in records),
        "adaptable_down_profile_count": sum(1 for x in records if x["ADAPTABLE_DOWN"] is True),
        "min_adapted_level_a1_profile_count": sum(1 for x in records if x["MIN_ADAPTED_LEVEL"] == "A1"),
        "concrete_source_example_profile_count": sum(1 for x in records if x["concrete_level_projection"] is not None),
        "supplementary_practice_profile_count_admitted": 0,
        "learner_facing_task_count": 0,
        "question_bank_item_count": 0,
        "new_a2_content_count": 0,
        "live_model_call_count": 0,
    }
    if summary != contract.get("expected_summary"):
        raise S9BuildError(f"SUMMARY_DRIFT:{summary!r}")

    out = {
        "schema": OUTPUT_SCHEMA,
        "task_id": TASK_ID,
        "source_stage": ["KET_DATA_S3", "KET_DATA_S8"],
        "output_stage": "KET_DATA_S9",
        "contract_source": "KET_S9.txt",
        "status": "MATERIALIZED",
        "level_adaptation_policy": policy,
        "adaptation_records": records,
        "summary": summary,
    }
    if output_path:
        Path(output_path).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    print(json.dumps(materialize(), ensure_ascii=False, indent=2))

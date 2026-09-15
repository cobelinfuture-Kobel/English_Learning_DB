from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

TASK_ID = "KET_Data_S8_OriginalVsDerivedTaskGovernance"
CONTRACT_SCHEMA = "ket.data.s8.task_origin_governance.contract.v1"
OUTPUT_SCHEMA = "ket.data.s8.task_origin_governance.v1"
EXPECTED_SOURCE_EXACT_COUNT = 1360
EXPECTED_SUPPLEMENTARY_EXCLUDED_COUNT = 92
EXPECTED_A1FS_DERIVED_COUNT = 80
EXPECTED_GOVERNED_RECORD_COUNT = 1440


class S8BuildError(ValueError):
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
    contract_path = root / "data" / "ket" / "ket_s8_task_origin_governance.json"
    contract = _json(contract_path)
    if (
        contract.get("schema"),
        contract.get("task_id"),
        contract.get("output_stage"),
        contract.get("contract_source"),
    ) != (
        CONTRACT_SCHEMA,
        TASK_ID,
        "KET_DATA_S8",
        "KET_S8.txt",
    ):
        raise S8BuildError("CONTRACT")

    pred = contract.get("predecessors") or {}
    s2b_contract_path = root / pred["s2b_contract_path"]
    s7_contract_path = root / pred["s7_contract_path"]
    if _git_blob_sha(s2b_contract_path.read_bytes()) != pred.get("s2b_contract_git_blob_sha"):
        raise S8BuildError("S2B_CONTRACT_BLOB_DRIFT")
    if _git_blob_sha(s7_contract_path.read_bytes()) != pred.get("s7_contract_git_blob_sha"):
        raise S8BuildError("S7_CONTRACT_BLOB_DRIFT")

    policy = contract.get("origin_policy") or {}
    if policy.get("allowed_task_origins") != ["SOURCE_EXACT", "A1FS_DERIVED"]:
        raise S8BuildError("TASK_ORIGIN_ENUM")
    if policy.get("source_exact_scope") != "CURRENT_KET_CANONICAL_MECHANIC":
        raise S8BuildError("SOURCE_EXACT_SCOPE")
    for key in (
        "supplementary_practice_in_binary_registry",
        "derived_source_task_copy_allowed",
        "derived_source_wording_copy_allowed",
        "derived_current_ket_canonical_promotion_allowed",
        "registry_copies_source_wording",
        "learner_facing",
        "question_bank_generation_allowed",
        "new_image_identity_allocation_allowed",
        "new_language_identity_allocation_allowed",
        "live_model_call_in_ci",
    ):
        if policy.get(key) is not False:
            raise S8BuildError(f"POLICY_FALSE_REQUIRED:{key}")
    if policy.get("derived_requires_authority_validation") is not True:
        raise S8BuildError("AUTHORITY_VALIDATION_POLICY")
    if policy.get("derived_must_preserve_image_evidence_lineage") is not True:
        raise S8BuildError("IMAGE_EVIDENCE_LINEAGE_POLICY")

    generation = contract.get("derived_generation_policy") or {}
    if generation.get("current_materialization_method") != "DETERMINISTIC_S7_PROJECTION":
        raise S8BuildError("GENERATION_METHOD")
    if generation.get("current_generation_model") is not None:
        raise S8BuildError("GENERATION_MODEL_FALSE_CLAIM")
    if generation.get("future_model_authored_records_must_record_generation_model") is not True:
        raise S8BuildError("FUTURE_MODEL_PROVENANCE_POLICY")
    if generation.get("target_levels") != ["A1", "A1_plus"]:
        raise S8BuildError("TARGET_LEVEL_POLICY")
    if generation.get("authority_validation_requirement") != "REQUIRED":
        raise S8BuildError("AUTHORITY_VALIDATION_REQUIREMENT")

    from builders.build_ket_data_s2b_item_semantic_projection import materialize as materialize_s2b
    from builders.build_ket_data_s7_image_multiple_task_family_projection import materialize as materialize_s7

    s2b = materialize_s2b(root)
    s7 = materialize_s7(root)
    projected_items = list(s2b.get("projected_items") or [])
    source_exact_items = [
        x for x in projected_items
        if x.get("semantic_authority_scope") == "CURRENT_KET_CANONICAL_MECHANIC"
        and x.get("is_current_ket_exam_mechanic") is True
    ]
    supplementary_items = [x for x in projected_items if x.get("practice_profile_id")]
    task_shells = list(s7.get("task_shells") or [])

    if len(source_exact_items) != pred.get("expected_source_exact_count") or len(source_exact_items) != EXPECTED_SOURCE_EXACT_COUNT:
        raise S8BuildError("SOURCE_EXACT_COUNT")
    if len(supplementary_items) != pred.get("expected_supplementary_practice_excluded_count") or len(supplementary_items) != EXPECTED_SUPPLEMENTARY_EXCLUDED_COUNT:
        raise S8BuildError("SUPPLEMENTARY_EXCLUDED_COUNT")
    if len(task_shells) != pred.get("expected_a1fs_derived_count") or len(task_shells) != EXPECTED_A1FS_DERIVED_COUNT:
        raise S8BuildError("A1FS_DERIVED_COUNT")

    records = []
    for item in sorted(source_exact_items, key=lambda x: x["item_id"]):
        record = {
            "origin_record_id": f"KET_S8_ORIGIN_{len(records) + 1:06d}",
            "task_origin": "SOURCE_EXACT",
            "source_item_id": item["item_id"],
            "source_id": item["source_id"],
            "source_page_ids": list(item.get("page_ids") or []),
            "source_image_ids": list(item.get("image_ids") or []),
            "semantic_profile_id": item.get("semantic_profile_id"),
            "derived_from": [],
            "source_task_reference_only": True,
            "source_task_copied": False,
            "source_wording_copied": False,
            "generation_model": None,
            "generation_method": None,
            "target_level": None,
            "authority_validation": "SOURCE_AUTHORITY_ALREADY_VALIDATED",
            "authority_validation_status": "PASS",
            "authority_scope": "CURRENT_KET_CANONICAL_MECHANIC",
            "current_ket_canonical_mechanic": True,
            "learner_facing": False,
            "question_bank_item": False,
        }
        record["origin_digest"] = _sha256_json(record)
        records.append(record)

    for shell in task_shells:
        lineage = shell.get("authority_lineage") or {}
        image_id = shell.get("source_image_asset_id")
        if not image_id or lineage.get("image_asset_id") != image_id:
            raise S8BuildError(f"S7_IMAGE_LINEAGE:{shell.get('task_shell_id')}")
        if shell.get("current_ket_canonical_mechanic") is not False:
            raise S8BuildError(f"S7_CANONICAL_PROMOTION:{shell.get('task_shell_id')}")
        record = {
            "origin_record_id": f"KET_S8_ORIGIN_{len(records) + 1:06d}",
            "task_origin": "A1FS_DERIVED",
            "source_item_id": None,
            "source_id": None,
            "source_page_ids": [],
            "source_image_ids": [image_id],
            "semantic_profile_id": None,
            "derived_from": [image_id],
            "s7_task_shell_id": shell["task_shell_id"],
            "source_language_asset_id": shell["source_language_asset_id"],
            "derived_task_family": shell["derived_task_family"],
            "s3_classification": shell["s3_classification"],
            "authority_lineage": lineage,
            "source_task_reference_only": False,
            "source_task_copied": False,
            "source_wording_copied": False,
            "generation_model": generation.get("current_generation_model"),
            "generation_method": generation["current_materialization_method"],
            "target_level": shell["derivation_target_level"],
            "authority_validation": generation["authority_validation_requirement"],
            "authority_validation_status": "PASS",
            "authority_scope": "A1FS_DERIVED_FROM_KET_IMAGE_EVIDENCE",
            "current_ket_canonical_mechanic": False,
            "learner_facing": False,
            "question_bank_item": False,
        }
        record["origin_digest"] = _sha256_json(record)
        records.append(record)

    if len(records) != EXPECTED_GOVERNED_RECORD_COUNT:
        raise S8BuildError("GOVERNED_RECORD_COUNT")

    origin_counts = Counter(x["task_origin"] for x in records)
    derived = [x for x in records if x["task_origin"] == "A1FS_DERIVED"]
    level_counts = Counter(x["target_level"] for x in derived)
    summary = {
        "governed_record_count": len(records),
        "source_exact_count": origin_counts["SOURCE_EXACT"],
        "a1fs_derived_count": origin_counts["A1FS_DERIVED"],
        "derived_a1_count": level_counts["A1"],
        "derived_a1_plus_count": level_counts["A1_plus"],
        "supplementary_practice_excluded_count": len(supplementary_items),
        "derived_source_task_copy_count": sum(1 for x in derived if x.get("source_task_copied") is True),
        "derived_source_wording_copy_count": sum(1 for x in derived if x.get("source_wording_copied") is True),
        "derived_current_ket_canonical_promotion_count": sum(
            1 for x in derived if x.get("current_ket_canonical_mechanic") is True
        ),
        "learner_facing_count": sum(1 for x in records if x.get("learner_facing") is True),
        "question_bank_item_count": sum(1 for x in records if x.get("question_bank_item") is True),
        "new_image_identity_count": 0,
        "new_language_identity_count": 0,
        "live_model_call_count": 0,
    }
    if summary != contract.get("expected_summary"):
        raise S8BuildError(f"SUMMARY_DRIFT:{summary!r}")

    out = {
        "schema": OUTPUT_SCHEMA,
        "task_id": TASK_ID,
        "source_stage": ["KET_DATA_S2B", "KET_DATA_S7"],
        "output_stage": "KET_DATA_S8",
        "contract_source": "KET_S8.txt",
        "status": "MATERIALIZED",
        "origin_policy": policy,
        "derived_generation_policy": generation,
        "origin_records": records,
        "excluded_supplementary_practice_item_ids": sorted(x["item_id"] for x in supplementary_items),
        "summary": summary,
    }
    if output_path:
        Path(output_path).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    print(json.dumps(materialize(), ensure_ascii=False, indent=2))

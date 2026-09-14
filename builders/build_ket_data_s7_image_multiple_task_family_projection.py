from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

TASK_ID = "KET_Data_S7_ImageMultipleTaskFamilyProjection"
CONTRACT_SCHEMA = "ket.data.s7.image_multiple_task_family_projection.contract.v1"
OUTPUT_SCHEMA = "ket.data.s7.image_multiple_task_family_projection.v1"
EXPECTED_LANGUAGE_ASSET_COUNT = 16
EXPECTED_IMAGE_ASSET_COUNT = 15
EXPECTED_SHELLS_PER_LANGUAGE_ASSET = 5
EXPECTED_TASK_SHELL_COUNT = 80


class S7BuildError(ValueError):
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


def _enum(taxonomy: dict, layer: str) -> set[str]:
    values = (((taxonomy.get("layers") or {}).get(layer) or {}).get("values") or [])
    return set(values)


def materialize(root=None, *, output_path=None) -> dict:
    root = _root(root)
    contract_path = root / "data" / "ket" / "ket_s7_image_multiple_task_family_projection.json"
    contract = _json(contract_path)
    if (
        contract.get("schema"),
        contract.get("task_id"),
        contract.get("source_stage"),
        contract.get("output_stage"),
        contract.get("contract_source"),
    ) != (
        CONTRACT_SCHEMA,
        TASK_ID,
        "KET_DATA_S6",
        "KET_DATA_S7",
        "KET_S7.txt",
    ):
        raise S7BuildError("CONTRACT")

    pred = contract.get("s6_predecessor") or {}
    s6_contract_path = root / pred["contract_path"]
    s6_bytes = s6_contract_path.read_bytes()
    if _git_blob_sha(s6_bytes) != pred.get("contract_git_blob_sha"):
        raise S7BuildError("S6_CONTRACT_BLOB_DRIFT")
    if pred.get("new_language_identity_allocation_allowed") is not False:
        raise S7BuildError("NEW_LANGUAGE_IDENTITY_POLICY")
    if pred.get("new_image_identity_allocation_allowed") is not False:
        raise S7BuildError("NEW_IMAGE_IDENTITY_POLICY")

    from builders.build_ket_data_s6_image_language_derivation import materialize as materialize_s6
    s6 = materialize_s6(root)
    language_assets = list(s6.get("language_assets") or [])
    if len(language_assets) != pred.get("expected_language_asset_count") or len(language_assets) != EXPECTED_LANGUAGE_ASSET_COUNT:
        raise S7BuildError("S6_LANGUAGE_ASSET_COUNT")
    image_ids = {x.get("image_asset_id") for x in language_assets}
    if len(image_ids) != pred.get("expected_image_asset_count") or len(image_ids) != EXPECTED_IMAGE_ASSET_COUNT:
        raise S7BuildError("S6_IMAGE_ASSET_COUNT")

    handshake = contract.get("s3_handshake") or {}
    taxonomy_path = root / handshake["taxonomy_path"]
    taxonomy_bytes = taxonomy_path.read_bytes()
    if _git_blob_sha(taxonomy_bytes) != handshake.get("taxonomy_git_blob_sha"):
        raise S7BuildError("S3_TAXONOMY_BLOB_DRIFT")
    taxonomy = _json(taxonomy_path)
    if taxonomy.get("layer_order") != handshake.get("required_layer_order"):
        raise S7BuildError("S3_LAYER_ORDER")
    if handshake.get("response_mode_redefinition_allowed") is not False:
        raise S7BuildError("S3_RESPONSE_MODE_REDEFINITION_POLICY")
    if handshake.get("canonical_task_family_promotion_allowed") is not False:
        raise S7BuildError("S3_CANONICAL_TASK_FAMILY_PROMOTION_POLICY")
    if handshake.get("derived_practice_family_separate_from_canonical_task_family") is not True:
        raise S7BuildError("S3_DERIVED_FAMILY_SEPARATION_POLICY")

    response_modes = _enum(taxonomy, "response_mode")
    task_families = _enum(taxonomy, "task_family")
    modalities = _enum(taxonomy, "stimulus_modality")
    capabilities = _enum(taxonomy, "assessment_capability")
    response_formats = _enum(taxonomy, "response_format")

    policy = contract.get("projection_policy") or {}
    if policy.get("learner_facing") is not False:
        raise S7BuildError("LEARNER_FACING_POLICY")
    if policy.get("question_bank_generation_allowed") is not False:
        raise S7BuildError("QUESTION_BANK_POLICY")
    if policy.get("final_distractor_generation_allowed") is not False:
        raise S7BuildError("DISTRACTOR_POLICY")
    if policy.get("current_ket_canonical_promotion_allowed") is not False:
        raise S7BuildError("CANONICAL_PROMOTION_POLICY")
    if policy.get("live_model_call_in_ci") is not False:
        raise S7BuildError("NONDETERMINISTIC_MODEL_POLICY")
    if policy.get("task_shell_not_final_question") is not True:
        raise S7BuildError("TASK_SHELL_BOUNDARY")
    if policy.get("shells_per_language_asset") != EXPECTED_SHELLS_PER_LANGUAGE_ASSET:
        raise S7BuildError("SHELL_COUNT_POLICY")

    specs = list(contract.get("task_shell_specs") or [])
    if len(specs) != EXPECTED_SHELLS_PER_LANGUAGE_ASSET:
        raise S7BuildError("TASK_SHELL_SPEC_COUNT")
    spec_families = set()
    for spec in specs:
        family = spec.get("derived_task_family")
        if not family or family in spec_families:
            raise S7BuildError("DERIVED_TASK_FAMILY_ID")
        spec_families.add(family)
        if spec.get("response_mode") not in response_modes:
            raise S7BuildError(f"S3_RESPONSE_MODE:{family}")
        if spec.get("stimulus_modality") not in modalities:
            raise S7BuildError(f"S3_STIMULUS_MODALITY:{family}")
        if spec.get("response_format") not in response_formats:
            raise S7BuildError(f"S3_RESPONSE_FORMAT:{family}")
        caps = spec.get("assessment_capabilities") or []
        if not caps or any(x not in capabilities for x in caps):
            raise S7BuildError(f"S3_ASSESSMENT_CAPABILITY:{family}")
        canonical_ref = spec.get("s3_canonical_task_family_ref")
        if canonical_ref is not None and canonical_ref not in task_families:
            raise S7BuildError(f"S3_TASK_FAMILY_REF:{family}")
        if canonical_ref is not None:
            raise S7BuildError(f"CANONICAL_TASK_FAMILY_PROMOTION_NOT_ALLOWED:{family}")

    task_shells = []
    for language_asset in language_assets:
        level = language_asset.get("derivation_target_level")
        if level not in policy.get("target_levels", []):
            raise S7BuildError(f"TARGET_LEVEL:{language_asset.get('language_asset_id')}:{level}")
        if language_asset.get("learner_facing") is not False:
            raise S7BuildError(f"S6_LEARNER_BOUNDARY:{language_asset.get('language_asset_id')}")
        for spec in specs:
            n = len(task_shells) + 1
            classification = {
                "response_mode": spec["response_mode"],
                "task_family_ref": spec.get("s3_canonical_task_family_ref"),
                "stimulus_modality": spec["stimulus_modality"],
                "assessment_capabilities": list(spec["assessment_capabilities"]),
                "response_format": spec["response_format"],
                "task_family_binding_status": "UNBOUND_DERIVED_PRACTICE",
            }
            lineage = {
                "image_asset_id": language_asset["image_asset_id"],
                "language_asset_id": language_asset["language_asset_id"],
                "fact_refs": list(language_asset.get("fact_refs") or []),
                "pattern_refs": list(language_asset.get("pattern_refs") or []),
                "grammar_refs": list(language_asset.get("grammar_refs") or []),
                "egp_source_refs": list(language_asset.get("egp_source_refs") or []),
                "vocabulary_refs": list(language_asset.get("vocabulary_refs") or []),
            }
            task_shells.append(
                {
                    "task_shell_id": f"KET_S7_TASK_{n:06d}",
                    "source_stage": "KET_DATA_S6",
                    "source_exam_context": policy["source_exam_context"],
                    "source_image_asset_id": language_asset["image_asset_id"],
                    "source_language_asset_id": language_asset["language_asset_id"],
                    "derivation_target_level": level,
                    "derived_task_family": spec["derived_task_family"],
                    "s3_classification": classification,
                    "prompt_template": spec["prompt_template"],
                    "answer_source": spec["answer_source"],
                    "materialization_boundary": spec["materialization_boundary"],
                    "source_sentence": language_asset["sentence"],
                    "authority_lineage": lineage,
                    "authority_scope": "DERIVED_PRACTICE_NOT_CURRENT_KET_CANONICAL",
                    "task_shell_digest": _sha256_json(
                        {
                            "source_language_asset_id": language_asset["language_asset_id"],
                            "source_image_asset_id": language_asset["image_asset_id"],
                            "derivation_target_level": level,
                            "derived_task_family": spec["derived_task_family"],
                            "s3_classification": classification,
                            "prompt_template": spec["prompt_template"],
                            "answer_source": spec["answer_source"],
                            "authority_lineage": lineage,
                        }
                    ),
                    "learner_facing": False,
                    "question_bank_item": False,
                    "current_ket_canonical_mechanic": False,
                    "materialization_status": "TASK_SHELL_ONLY",
                    "validation_status": "PASS",
                }
            )

    if len(task_shells) != EXPECTED_TASK_SHELL_COUNT:
        raise S7BuildError("TASK_SHELL_COUNT")

    level_counts = Counter(x["derivation_target_level"] for x in task_shells)
    mode_counts = Counter(x["s3_classification"]["response_mode"] for x in task_shells)
    shells_by_image = defaultdict(list)
    levels_by_image = defaultdict(set)
    for row in task_shells:
        shells_by_image[row["source_image_asset_id"]].append(row)
        levels_by_image[row["source_image_asset_id"]].add(row["derivation_target_level"])
    summary = {
        "source_language_asset_count": len(language_assets),
        "source_image_asset_count": len(image_ids),
        "task_shell_count": len(task_shells),
        "target_level_shell_counts": dict(sorted(level_counts.items())),
        "response_mode_counts": dict(sorted(mode_counts.items())),
        "image_with_multiple_shell_count": sum(1 for rows in shells_by_image.values() if len(rows) > 1),
        "image_with_multiple_level_count": sum(1 for levels in levels_by_image.values() if len(levels) > 1),
        "canonical_task_family_promotion_count": sum(
            1 for row in task_shells if row["s3_classification"].get("task_family_ref") is not None
        ),
        "learner_facing_task_count": sum(1 for row in task_shells if row.get("learner_facing") is True),
        "question_bank_item_count": sum(1 for row in task_shells if row.get("question_bank_item") is True),
        "new_image_identity_count": 0,
        "new_language_identity_count": 0,
        "live_model_call_count": 0,
    }
    if summary != contract.get("expected_summary"):
        raise S7BuildError(f"SUMMARY_DRIFT:{summary!r}")

    out = {
        "schema": OUTPUT_SCHEMA,
        "task_id": TASK_ID,
        "source_stage": "KET_DATA_S6",
        "output_stage": "KET_DATA_S7",
        "contract_source": "KET_S7.txt",
        "status": "MATERIALIZED",
        "s3_handshake": handshake,
        "projection_policy": policy,
        "task_shells": task_shells,
        "summary": summary,
    }
    if output_path:
        Path(output_path).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    print(json.dumps(materialize(), ensure_ascii=False, indent=2))

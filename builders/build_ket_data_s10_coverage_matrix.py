from __future__ import annotations

import hashlib
import importlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

TASK_ID = "KET_Data_S10_A1FSCurrentVsKETReferenceCoverageMatrix"
CONTRACT_SCHEMA = "ket.data.s10.coverage_matrix.contract.v1"
OUTPUT_SCHEMA = "ket.data.s10.coverage_matrix.v1"
PASS_STATUS = "PASS_KET_DATA_S10_A1FS_CURRENT_VS_KET_REFERENCE_COVERAGE_MATRIX"

EXPECTED_ROW_IDS = [f"KET_S10_COV_{index:03d}" for index in range(1, 8)]
EXPECTED_STATUS_COUNTS = {"missing": 1, "weak": 2, "partial": 3, "strong": 1}


class S10BuildError(ValueError):
    pass


def _root(root=None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1])


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _sha256_json(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _load_module(path: str):
    try:
        return importlib.import_module(path)
    except Exception as exc:
        raise S10BuildError(f"U04_EVIDENCE_IMPORT:{path}:{type(exc).__name__}") from exc


def _task_variant_set(fsv2) -> set[str]:
    variants: set[str] = set()
    for values in getattr(fsv2, "TASK_VARIANTS", {}).values():
        variants.update(str(value) for value in values)
    return variants


def _ms02c_family_set(ms02c) -> set[str]:
    return {
        str(shape.get("task_family"))
        for shape in getattr(ms02c, "TASK_SHAPES", {}).values()
        if isinstance(shape, dict) and shape.get("task_family")
    }


def _validate_u04_evidence(contract: dict[str, Any]) -> dict[str, Any]:
    evidence = contract.get("u04_current_evidence") or {}
    fsv2 = _load_module(str(evidence.get("fsv2_module") or ""))
    spv2 = _load_module(str(evidence.get("spv2_module") or ""))
    ms02c = _load_module(str(evidence.get("ms02c_module") or ""))
    vav2 = _load_module(str(evidence.get("vav2_module") or ""))

    if getattr(fsv2, "TASK_ID", None) != "A1FS-V1-U04FSV2_Current360ContextualForm01To20ActiveRuntimeMaterialization":
        raise S10BuildError("FSV2_TASK_ID")
    if getattr(spv2, "TASK_ID", None) != "A1FS-V1-U04SPV2_SpeakingLayer1BridgeLayer2Cutover":
        raise S10BuildError("SPV2_TASK_ID")
    if getattr(ms02c, "TASK_ID", None) != "A1FS-V1-U04MS02C_KETFourSkillTaskAssessmentProjection":
        raise S10BuildError("MS02C_TASK_ID")
    if getattr(vav2, "TASK_ID", None) != "A1FS-V1-U04VAV2_Current360LearnerFacingVisualPedagogicalAcceptance":
        raise S10BuildError("VAV2_TASK_ID")

    if getattr(fsv2, "FORM_COUNT", None) != evidence.get("expected_form_count"):
        raise S10BuildError("U04_FORM_COUNT")
    if getattr(fsv2, "TOTAL_ACTIVITIES", None) != evidence.get("expected_activity_count"):
        raise S10BuildError("U04_ACTIVITY_COUNT")
    if getattr(vav2, "SPEAKING_TASK_COUNT", None) != evidence.get("expected_speaking_task_count"):
        raise S10BuildError("U04_SPEAKING_TASK_COUNT")

    variants = _task_variant_set(fsv2)
    speaking_modes = set(str(value) for value in getattr(spv2, "LAYER2_MODES", ()))
    ms02c_families = _ms02c_family_set(ms02c)

    required = {
        "READING_SPECIFIC_INFORMATION",
        "READING_CONNECTED_QA",
        "CONTEXT_GAP_RELATION_WRITE",
        "PASSAGE_FOCUS_SENTENCE_RESTORE",
        "WRITING_ONE_LOCATION_FACT",
        "WRITING_TWO_LOCATION_FACTS",
        "SPEAKING_LOCATION_QA",
        "SPEAKING_SCENE_DESCRIPTION",
    }
    missing_variants = sorted(required - variants)
    if missing_variants:
        raise S10BuildError("U04_VARIANT_SIGNAL_MISSING:" + ",".join(missing_variants))

    required_speaking = {
        "LOCATION_QA",
        "SCENE_DESCRIPTION",
        "DIALOGUE_FOLLOW_UP",
        "TRANSFER_CHANGED_LOCATION",
    }
    missing_speaking = sorted(required_speaking - speaking_modes)
    if missing_speaking:
        raise S10BuildError("U04_SPEAKING_SIGNAL_MISSING:" + ",".join(missing_speaking))

    required_families = {
        "SHORT_READING_LOCATION_EXTRACTION",
        "LISTENING_LOCATION_EXTRACTION",
        "SPEAKING_LOCATION_QA_AND_TRANSFER",
        "SHORT_WRITING_LOCATION_DESCRIPTION",
    }
    missing_families = sorted(required_families - ms02c_families)
    if missing_families:
        raise S10BuildError("U04_MS02C_SIGNAL_MISSING:" + ",".join(missing_families))

    return {
        "module_task_ids": {
            "fsv2": fsv2.TASK_ID,
            "spv2": spv2.TASK_ID,
            "ms02c": ms02c.TASK_ID,
            "vav2": vav2.TASK_ID,
        },
        "form_count": fsv2.FORM_COUNT,
        "activity_count": fsv2.TOTAL_ACTIVITIES,
        "speaking_task_count": vav2.SPEAKING_TASK_COUNT,
        "task_variants": sorted(variants),
        "speaking_modes": sorted(speaking_modes),
        "ms02c_task_families": sorted(ms02c_families),
        "exact_short_message_meaning_present": (
            "SHORT_MESSAGE_MEANING" in variants
            or "SHORT_MESSAGE_MEANING" in ms02c_families
        ),
        "exact_multi_text_matching_present": (
            "MULTI_TEXT_MATCHING" in variants
            or "MULTI_TEXT_MATCHING" in ms02c_families
        ),
        "exact_open_cloze_present": (
            "OPEN_CLOZE" in variants or "OPEN_CLOZE" in ms02c_families
        ),
        "exact_guided_message_present": (
            "GUIDED_MESSAGE" in variants or "GUIDED_MESSAGE" in ms02c_families
        ),
        "exact_visual_discussion_present": (
            "SPEAK_VISUAL_DISCUSSION" in variants
            or "SPEAK_VISUAL_DISCUSSION" in ms02c_families
        ),
    }


def _evidence_for_row(row: dict[str, Any], u04: dict[str, Any]) -> dict[str, Any]:
    row_id = row["coverage_id"]
    variants = set(u04["task_variants"])
    speaking = set(u04["speaking_modes"])
    families = set(u04["ms02c_task_families"])

    if row_id == "KET_S10_COV_001":
        if u04["exact_short_message_meaning_present"]:
            raise S10BuildError("SOURCE_STATUS_DRIFT:COV001")
        return {
            "supports_status": "missing",
            "positive_signals": [],
            "absent_exact_signals": ["SHORT_MESSAGE_MEANING"],
        }

    if row_id == "KET_S10_COV_002":
        required = {"READING_SPECIFIC_INFORMATION", "READING_CONNECTED_QA"}
        if not required.issubset(variants) or u04["exact_multi_text_matching_present"]:
            raise S10BuildError("SOURCE_STATUS_DRIFT:COV002")
        return {
            "supports_status": "partial",
            "positive_signals": sorted(required),
            "absent_exact_signals": ["MULTI_TEXT_MATCHING"],
        }

    if row_id == "KET_S10_COV_003":
        required_variants = {"READING_SPECIFIC_INFORMATION", "SPEAKING_LOCATION_QA"}
        required_families = {
            "SHORT_READING_LOCATION_EXTRACTION",
            "LISTENING_LOCATION_EXTRACTION",
        }
        required_speaking = {"LOCATION_QA"}
        if (
            not required_variants.issubset(variants)
            or not required_families.issubset(families)
            or not required_speaking.issubset(speaking)
        ):
            raise S10BuildError("SOURCE_STATUS_DRIFT:COV003")
        return {
            "supports_status": "strong",
            "positive_signals": sorted(
                required_variants | required_families | required_speaking
            ),
            "absent_exact_signals": [],
        }

    if row_id == "KET_S10_COV_004":
        required = {"CONTEXT_GAP_RELATION_WRITE", "PASSAGE_FOCUS_SENTENCE_RESTORE"}
        if not required.issubset(variants) or u04["exact_open_cloze_present"]:
            raise S10BuildError("SOURCE_STATUS_DRIFT:COV004")
        return {
            "supports_status": "partial",
            "positive_signals": sorted(required),
            "absent_exact_signals": ["OPEN_CLOZE"],
        }

    if row_id == "KET_S10_COV_005":
        required = {"WRITING_ONE_LOCATION_FACT", "WRITING_TWO_LOCATION_FACTS"}
        if not required.issubset(variants) or u04["exact_guided_message_present"]:
            raise S10BuildError("SOURCE_STATUS_DRIFT:COV005")
        return {
            "supports_status": "weak",
            "positive_signals": sorted(required),
            "absent_exact_signals": ["GUIDED_MESSAGE"],
        }

    if row_id == "KET_S10_COV_006":
        required = {"SCENE_DESCRIPTION"}
        if not required.issubset(speaking):
            raise S10BuildError("SOURCE_STATUS_DRIFT:COV006")
        return {
            "supports_status": "partial",
            "positive_signals": sorted(required),
            "absent_exact_signals": ["IMAGE_STIMULUS_BOUND_DESCRIPTION"],
        }

    if row_id == "KET_S10_COV_007":
        required = {"SCENE_DESCRIPTION", "DIALOGUE_FOLLOW_UP", "TRANSFER_CHANGED_LOCATION"}
        if not required.issubset(speaking) or u04["exact_visual_discussion_present"]:
            raise S10BuildError("SOURCE_STATUS_DRIFT:COV007")
        return {
            "supports_status": "weak",
            "positive_signals": sorted(required),
            "absent_exact_signals": ["SPEAK_VISUAL_DISCUSSION"],
        }

    raise S10BuildError(f"UNKNOWN_COVERAGE_ROW:{row_id}")


def materialize(root=None, *, output_path=None) -> dict[str, Any]:
    root = _root(root)
    contract_path = root / "data" / "ket" / "ket_s10_coverage_matrix.json"
    contract = _json(contract_path)

    if (
        contract.get("schema"),
        contract.get("task_id"),
        contract.get("output_stage"),
        contract.get("contract_source"),
    ) != (
        CONTRACT_SCHEMA,
        TASK_ID,
        "KET_DATA_S10",
        "KET_S10.txt",
    ):
        raise S10BuildError("CONTRACT")

    scope = contract.get("scope") or {}
    if scope.get("comparison") != "A1FS_CURRENT_VS_KET_REFERENCE":
        raise S10BuildError("COMPARISON")
    if scope.get("current_unit") != 4 or scope.get("future_design_unit_range") != [4, 24]:
        raise S10BuildError("UNIT_SCOPE")
    if scope.get("coverage_matrix_only") is not True:
        raise S10BuildError("MATRIX_ONLY")
    if scope.get("unit_content_mutation_allowed") is not False:
        raise S10BuildError("UNIT_CONTENT_MUTATION")
    if scope.get("unit05_plus_materialization_allowed") is not False:
        raise S10BuildError("UNIT05_PLUS_MATERIALIZATION")

    pred = contract.get("predecessors") or {}
    s9_contract_path = root / str(pred.get("s9_contract_path") or "")
    if _git_blob_sha(s9_contract_path.read_bytes()) != pred.get("s9_contract_git_blob_sha"):
        raise S10BuildError("S9_CONTRACT_BLOB_DRIFT")

    from builders.build_ket_data_s9_level_adaptation_contract import materialize as materialize_s9

    s9 = materialize_s9(root)
    s9_summary = s9.get("summary") or {}
    if s9_summary.get("canonical_mechanic_profile_count") != pred.get(
        "expected_s9_canonical_profile_count"
    ):
        raise S10BuildError("S9_PROFILE_COUNT")
    if s9_summary.get("source_exact_item_count_covered") != pred.get(
        "expected_s9_source_exact_item_count"
    ):
        raise S10BuildError("S9_SOURCE_EXACT_COUNT")

    s9_by_profile = {
        str(record["semantic_profile_id"]): record
        for record in (s9.get("adaptation_records") or [])
    }
    if len(s9_by_profile) != pred.get("expected_s9_canonical_profile_count"):
        raise S10BuildError("S9_PROFILE_INDEX")

    u04 = _validate_u04_evidence(contract)
    source_rows = contract.get("coverage_rows") or []
    if [row.get("coverage_id") for row in source_rows] != EXPECTED_ROW_IDS:
        raise S10BuildError("ROW_ID_SEQUENCE")

    rows: list[dict[str, Any]] = []
    referenced_profiles: set[str] = set()
    for source in source_rows:
        profile_ids = [str(value) for value in source.get("s3_profile_ids") or []]
        if not profile_ids:
            raise S10BuildError(f"PROFILE_REF_EMPTY:{source.get('coverage_id')}")
        records = []
        for profile_id in profile_ids:
            record = s9_by_profile.get(profile_id)
            if record is None:
                raise S10BuildError(f"S9_PROFILE_UNRESOLVED:{profile_id}")
            records.append(record)
            referenced_profiles.add(profile_id)

        axis = source.get("reference_axis")
        expected_value = source.get("s3_reference_value")
        if axis == "TASK_FAMILY":
            if not any(record.get("task_family") == expected_value for record in records):
                raise S10BuildError(f"TASK_FAMILY_REF_MISMATCH:{source['coverage_id']}")
        elif axis == "ASSESSMENT_CAPABILITY":
            if not all(
                expected_value in (record.get("assessment_capabilities") or [])
                for record in records
            ):
                raise S10BuildError(f"CAPABILITY_REF_MISMATCH:{source['coverage_id']}")
        else:
            raise S10BuildError(f"REFERENCE_AXIS:{axis}")

        evidence = _evidence_for_row(source, u04)
        if evidence["supports_status"] != source.get("U04_current"):
            raise S10BuildError(f"U04_STATUS_EVIDENCE_MISMATCH:{source['coverage_id']}")

        row = {
            **source,
            "ket_reference": [
                {
                    "semantic_profile_id": record["semantic_profile_id"],
                    "task_family": record["task_family"],
                    "response_mode": record["response_mode"],
                    "stimulus_modality": record["stimulus_modality"],
                    "assessment_capabilities": record["assessment_capabilities"],
                    "native_response_format": record["native_response_format"],
                    "NATIVE_LEVEL": record["NATIVE_LEVEL"],
                    "ADAPTABLE_DOWN": record["ADAPTABLE_DOWN"],
                    "MIN_ADAPTED_LEVEL": record["MIN_ADAPTED_LEVEL"],
                    "ADAPTATION_RULE": record["ADAPTATION_RULE"],
                }
                for record in records
            ],
            "u04_evidence": evidence,
        }
        row["coverage_digest"] = _sha256_json(row)
        rows.append(row)

    governance = contract.get("governance") or {}
    for key in (
        "source_rows_are_authoritative_s10_matrix_seed",
        "coverage_status_must_be_bound_to_current_u04_evidence",
        "s9_level_adaptation_identity_must_be_preserved",
        "s8_origin_governance_must_not_be_bypassed",
    ):
        if governance.get(key) is not True:
            raise S10BuildError(f"GOVERNANCE_TRUE_REQUIRED:{key}")
    for key in (
        "learner_facing_generation_allowed",
        "question_bank_generation_allowed",
        "new_image_generation_allowed",
        "new_language_asset_generation_allowed",
        "a2_or_a2_plus_unlock_allowed",
        "live_model_call_in_ci",
        "new_summary_document_allowed",
    ):
        if governance.get(key) is not False:
            raise S10BuildError(f"GOVERNANCE_FALSE_REQUIRED:{key}")

    status_counts = Counter(str(row["U04_current"]) for row in rows)
    summary = {
        "coverage_row_count": len(rows),
        "status_counts": {
            key: status_counts.get(key, 0)
            for key in ("missing", "weak", "partial", "strong")
        },
        "unique_ket_reference_profile_count": len(referenced_profiles),
        "u04_evidence_module_count": len(u04["module_task_ids"]),
        "learner_facing_task_count": 0,
        "question_bank_item_count": 0,
        "new_content_count": 0,
        "a2_or_a2_plus_unlock_count": 0,
        "live_model_call_count": 0,
    }
    if summary["status_counts"] != EXPECTED_STATUS_COUNTS:
        raise S10BuildError(f"STATUS_COUNT_DRIFT:{summary['status_counts']}")
    if summary != contract.get("expected_summary"):
        raise S10BuildError(f"SUMMARY_DRIFT:{summary!r}")

    out = {
        "schema": OUTPUT_SCHEMA,
        "task_id": TASK_ID,
        "source_stage": ["KET_DATA_S9", "A1FS_V1_UNIT04_CURRENT"],
        "output_stage": "KET_DATA_S10",
        "contract_source": "KET_S10.txt",
        "status": "MATERIALIZED",
        "scope": scope,
        "coverage_rows": rows,
        "u04_current_evidence": {
            "module_task_ids": u04["module_task_ids"],
            "form_count": u04["form_count"],
            "activity_count": u04["activity_count"],
            "speaking_task_count": u04["speaking_task_count"],
        },
        "summary": summary,
        "governance": governance,
    }
    out["matrix_digest"] = _sha256_json(out["coverage_rows"])

    if output_path:
        Path(output_path).write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return out


if __name__ == "__main__":
    print(json.dumps(materialize(), ensure_ascii=False, indent=2))

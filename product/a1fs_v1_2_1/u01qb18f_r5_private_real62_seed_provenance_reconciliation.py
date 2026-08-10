#!/usr/bin/env python3
"""Reconcile Unit01 model-authored micro-scenes with their exact approved seeds.

This operator-local runner replays the original U01QB06 -> U01QB07 deterministic
seed-resolution path against the exact approved private Real62 artifact. It does
not author scenes, rewrite the 474-item QuestionBank, or promote private source
text. The output is a private provenance overlay/readback containing only source
identities, hashes and semantic summaries required to prove the original seed
lineage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from product.a1fs_v1_2_1 import u01qb18f_r4_full_semantic_language_pedagogical_replay as r4
from ulga.builders import _u01qb18f_r2_canonical_micro_scene_authority_fullfix as r2
from ulga.builders import build_a1fs_online_v1_2_u01e_s01_unit01_five_context_authority_admission as s01
from ulga.builders import build_a1fs_v1_razq01e_unit01_approved_content_existing_qb_learner_stimulus_runtime as razq01e
from ulga.builders import build_a1fs_v1_u01qb06_unit01_micro_scene_pool_inventory as u06
from ulga.builders import build_a1fs_v1_u01qb07_unit01_micro_scene_seed_enrichment as u07
from ulga.builders import build_a1fs_v1_u01qb15_actual_real62_fresh474_r2_private_acceptance_runner as real62_contract

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Private read-only provenance reconciliation over the already-approved Real62 "
    "artifact and existing U01QB06/U01QB07/U01QB18F-R2 authorities. No learner "
    "content, source text, scene identity, QuestionBank, selector, planner, runtime, "
    "database, scoring, Unit02-24, audio/Speaking-score, or A2 authority is created."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB18F-R5_Unit01PrivateReal62SeedProvenanceReconciliationFullFix"
PASS_STATUS = "PASS_A1FS_V1_U01QB18F_R5_PRIVATE_REAL62_SEED_PROVENANCE_RECONCILIATION"
FAIL_STATUS = "FAIL_A1FS_V1_U01QB18F_R5_PRIVATE_REAL62_SEED_PROVENANCE_RECONCILIATION"
NEXT_SHORT_STEP = "A1FS-V1-U01QB18G_Unit01TwelveFormLearnerFacingPedagogicalReviewAndCloseout"
EXPECTED_MODEL_SCENES = 27
EXPECTED_CONTENT_ASSETS = 62
EXPECTED_RUNTIME_ITEMS = 474
EXPECTED_REAL62_EXTENSION_ITEMS = 186
EXPECTED_REAL62_ARTIFACT_SHA256 = real62_contract.EXPECTED_REAL62_ARTIFACT_SHA256
RECONCILED_DETAIL_STATUS = "RECONCILED_FROM_EXACT_APPROVED_PRIVATE_ARTIFACT"
DEFAULT_OUTPUT = Path(
    ".local/a1fs_v1/review/unit01_micro_scene_real62_seed_provenance.private.json"
)


class PrivateReal62ProvenanceError(ValueError):
    pass


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PrivateReal62ProvenanceError(f"UNREADABLE_JSON:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise PrivateReal62ProvenanceError(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def _real62_identity(path: Path) -> tuple[dict[str, Any], str, str]:
    """Use the existing U01QB15 canonical artifact identity contract unchanged."""
    try:
        return real62_contract._real62_identity(Path(path))
    except Exception as exc:
        raise PrivateReal62ProvenanceError(f"REAL62_CANONICAL_IDENTITY_INVALID:{exc}") from exc


def _write_private(path: Path, value: Mapping[str, Any]) -> None:
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _validate_r4_report(report: Mapping[str, Any], *, real62_artifact_sha256: str) -> None:
    if report.get("task_id") != r4.TASK_ID or report.get("validation_status") != r4.PASS_STATUS:
        raise PrivateReal62ProvenanceError("R4_FULL_SEMANTIC_REPLAY_NOT_PASS")
    proof = report.get("runtime_proof") or {}
    if int(proof.get("runtime_item_count", 0)) != EXPECTED_RUNTIME_ITEMS:
        raise PrivateReal62ProvenanceError("R4_RUNTIME_ITEM_COUNT_INVALID")
    if int(proof.get("real62_extension_item_count", 0)) != EXPECTED_REAL62_EXTENSION_ITEMS:
        raise PrivateReal62ProvenanceError("R4_REAL62_EXTENSION_COUNT_INVALID")
    if str(proof.get("real62_artifact_sha256") or "") != real62_artifact_sha256:
        raise PrivateReal62ProvenanceError("R4_REAL62_ARTIFACT_IDENTITY_MISMATCH")
    if proof.get("source_production_database_modified") is not False:
        raise PrivateReal62ProvenanceError("R4_SOURCE_PRODUCTION_DATABASE_MODIFIED")


def _private_inventory(
    approved_content: Mapping[str, Any], *, real62_artifact_sha256: str
) -> dict[str, Any]:
    # Reuse the canonical RAZQ01E admission check before any provenance replay.
    assets = razq01e._approved_content_assets(approved_content)
    if len(assets) != EXPECTED_CONTENT_ASSETS:
        raise PrivateReal62ProvenanceError(
            f"APPROVED_CONTENT_ASSET_COUNT_INVALID:{len(assets)}:{EXPECTED_CONTENT_ASSETS}"
        )
    return u06.build_inventory(
        approved_content,
        s01.CONTEXTS,
        approved_content_sha256=real62_artifact_sha256,
        canonical_context_sha256=u06.digest(s01.CONTEXTS),
    )


def _seed_evidence(anchor: Mapping[str, Any]) -> dict[str, Any]:
    core = anchor.get("semantic_scene_core") or {}
    return {
        "seed_scene_ref_id": str(anchor.get("scene_ref_id") or ""),
        "scene_origin": str(anchor.get("scene_origin") or ""),
        "lineage_mode": str(anchor.get("lineage_mode") or ""),
        "source_authority": str(anchor.get("source_authority") or ""),
        "content_kind": str(anchor.get("content_kind") or ""),
        "semantic_scene_signature_v2": str(anchor.get("semantic_scene_signature_v2") or ""),
        "setting": str(core.get("setting") or ""),
        "objects": list(core.get("objects") or []),
    }


def _reconcile_inventory(inventory: Mapping[str, Any]) -> dict[str, Any]:
    rows = u07.inventory_rows(inventory)
    anchors = u07.eligible_anchor_rows(rows)
    anchor_by_ref = {str(row.get("scene_ref_id") or ""): row for row in anchors}
    if not anchor_by_ref:
        raise PrivateReal62ProvenanceError("ELIGIBLE_APPROVED_SEED_ANCHORS_MISSING")

    spec = u07.read_json(u07.DEFAULT_SPEC)
    candidates = u07.candidates(spec)
    if len(candidates) != EXPECTED_MODEL_SCENES:
        raise PrivateReal62ProvenanceError(
            f"MODEL_SCENE_COUNT_INVALID:{len(candidates)}:{EXPECTED_MODEL_SCENES}"
        )

    authority_report = r2.require_authority_pass()
    reconciled: list[dict[str, Any]] = []
    unique_real62_refs: set[str] = set()
    unique_context_refs: set[str] = set()
    real62_scene_count = 0
    context_scene_count = 0
    mixed_scene_count = 0

    for candidate in candidates:
        # Original U01QB07 resolver: model_scene_row() calls resolve_anchor_refs().
        replayed = u07.model_scene_row(candidate, anchors)
        scene_ref = str(replayed["scene_ref_id"])
        current = r2.canonical_scene_package(scene_ref)
        if str(current.get("semantic_scene_signature_v2") or "") != str(
            replayed.get("semantic_scene_signature_v2") or ""
        ):
            raise PrivateReal62ProvenanceError(f"MODEL_SCENE_SEMANTIC_DRIFT:{scene_ref}")
        current_lineage = current.get("source_lineage") or {}
        provenance = replayed.get("provenance") or {}
        if (
            str(current_lineage.get("lineage_mode") or "")
            != "MODEL_AUTHORED_FROM_APPROVED_SEEDS"
            or str(provenance.get("source_claim") or "")
            != "SEED_ANCHORED_MODEL_AUTHORED_NOT_SOURCE_EQUIVALENT"
            or provenance.get("source_equivalence_claimed") is not False
        ):
            raise PrivateReal62ProvenanceError(f"MODEL_SCENE_PROVENANCE_DRIFT:{scene_ref}")

        refs = [str(value) for value in provenance.get("resolved_seed_scene_ref_ids") or []]
        if not refs or len(refs) != len(set(refs)):
            raise PrivateReal62ProvenanceError(f"RESOLVED_SEED_REFS_INVALID:{scene_ref}")
        evidence: list[dict[str, Any]] = []
        real62_refs: list[str] = []
        context_refs: list[str] = []
        for ref in refs:
            anchor = anchor_by_ref.get(ref)
            if anchor is None:
                raise PrivateReal62ProvenanceError(
                    f"RESOLVED_SEED_REF_NOT_ELIGIBLE:{scene_ref}:{ref}"
                )
            if (
                anchor.get("scene_origin") == "REAL62_CONTENT_ASSET"
                and anchor.get("lineage_mode") == "PROJECT_AUTHORED_CONTRACT_COMPLETION"
            ):
                raise PrivateReal62ProvenanceError(
                    f"PROJECT_AUTHORED_COMPLETION_USED_AS_SEED:{scene_ref}:{ref}"
                )
            origin = str(anchor.get("scene_origin") or "")
            if origin == "REAL62_CONTENT_ASSET":
                real62_refs.append(ref)
                unique_real62_refs.add(ref)
            elif origin == "CANONICAL_UNIT01_CONTEXT":
                context_refs.append(ref)
                unique_context_refs.add(ref)
            else:
                raise PrivateReal62ProvenanceError(
                    f"UNEXPECTED_SEED_ORIGIN:{scene_ref}:{ref}:{origin}"
                )
            evidence.append(_seed_evidence(anchor))

        if real62_refs:
            real62_scene_count += 1
        if context_refs:
            context_scene_count += 1
        if real62_refs and context_refs:
            mixed_scene_count += 1
        reconciled.append(
            {
                "scene_ref_id": scene_ref,
                "semantic_scene_signature_v2": str(replayed["semantic_scene_signature_v2"]),
                "source_class": "MODEL_AUTHORED_FROM_APPROVED_SEEDS",
                "source_claim": str(provenance["source_claim"]),
                "resolved_seed_scene_ref_ids": refs,
                "real62_seed_scene_ref_ids": real62_refs,
                "canonical_context_seed_scene_ref_ids": context_refs,
                "seed_evidence": evidence,
                "resolved_seed_scene_ref_detail_status": RECONCILED_DETAIL_STATUS,
            }
        )

    if len(reconciled) != EXPECTED_MODEL_SCENES:
        raise PrivateReal62ProvenanceError("RECONCILED_MODEL_SCENE_COUNT_INVALID")
    return {
        "authority_report": authority_report,
        "reconciled_model_scenes": reconciled,
        "model_scene_count": len(reconciled),
        "model_scenes_with_real62_seed": real62_scene_count,
        "model_scenes_with_canonical_context_seed": context_scene_count,
        "model_scenes_with_mixed_seed_types": mixed_scene_count,
        "unique_real62_seed_ref_count": len(unique_real62_refs),
        "unique_canonical_context_seed_ref_count": len(unique_context_refs),
        "unique_real62_seed_refs": sorted(unique_real62_refs),
        "unique_canonical_context_seed_refs": sorted(unique_context_refs),
    }


def materialize_reconciliation(
    *,
    real62_path: Path,
    r4_report_path: Path,
    output: Path,
    expected_real62_artifact_sha256: str = EXPECTED_REAL62_ARTIFACT_SHA256,
) -> dict[str, Any]:
    real62_path = Path(real62_path).resolve(strict=True)
    r4_report_path = Path(r4_report_path).resolve(strict=True)
    approved_content, artifact_sha, raw_file_sha = _real62_identity(real62_path)
    if artifact_sha != expected_real62_artifact_sha256:
        raise PrivateReal62ProvenanceError(
            "REAL62_ARTIFACT_SHA256_INVALID:"
            f"{artifact_sha}:{expected_real62_artifact_sha256}"
        )
    r4_report = _load_json(r4_report_path)
    _validate_r4_report(r4_report, real62_artifact_sha256=artifact_sha)
    inventory = _private_inventory(
        approved_content,
        real62_artifact_sha256=artifact_sha,
    )
    reconciliation = _reconcile_inventory(inventory)

    result = {
        "schema_version": "a1fs.v1.u01qb18f.r5.private_real62_seed_provenance.v1",
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "real62_artifact_sha256": artifact_sha,
        "real62_file_sha256": raw_file_sha,
        "r4_report_sha256": _file_sha256(r4_report_path),
        "r4_validation_status": r4_report["validation_status"],
        "canonical_scene_count": int(
            reconciliation["authority_report"]["canonical_scene_count"]
        ),
        "unit01_runtime_bindable_scene_count": int(
            reconciliation["authority_report"]["unit01_runtime_bindable_scene_count"]
        ),
        "deferred_scene_refs": list(reconciliation["authority_report"]["deferred_scene_refs"]),
        "model_scene_count": reconciliation["model_scene_count"],
        "reconciled_model_scene_count": reconciliation["model_scene_count"],
        "unresolved_model_scene_count": 0,
        "model_scenes_with_real62_seed": reconciliation["model_scenes_with_real62_seed"],
        "model_scenes_with_canonical_context_seed": reconciliation[
            "model_scenes_with_canonical_context_seed"
        ],
        "model_scenes_with_mixed_seed_types": reconciliation[
            "model_scenes_with_mixed_seed_types"
        ],
        "unique_real62_seed_ref_count": reconciliation["unique_real62_seed_ref_count"],
        "unique_canonical_context_seed_ref_count": reconciliation[
            "unique_canonical_context_seed_ref_count"
        ],
        "unique_real62_seed_refs": reconciliation["unique_real62_seed_refs"],
        "unique_canonical_context_seed_refs": reconciliation[
            "unique_canonical_context_seed_refs"
        ],
        "reconciled_model_scenes": reconciliation["reconciled_model_scenes"],
        "provenance_overlay": {
            row["scene_ref_id"]: {
                "resolved_seed_scene_ref_ids": row["resolved_seed_scene_ref_ids"],
                "real62_seed_scene_ref_ids": row["real62_seed_scene_ref_ids"],
                "canonical_context_seed_scene_ref_ids": row[
                    "canonical_context_seed_scene_ref_ids"
                ],
                "resolved_seed_scene_ref_detail_status": RECONCILED_DETAIL_STATUS,
                "real62_artifact_sha256": artifact_sha,
                "u07_resolution_algorithm": "ORIGINAL_U01QB07_RESOLVE_ANCHOR_REFS",
            }
            for row in reconciliation["reconciled_model_scenes"]
        },
        "source_text_exported": False,
        "questionbank_modified": False,
        "scene_semantics_modified": False,
        "new_scene_authored": False,
        "next_short_step": NEXT_SHORT_STEP,
    }
    _write_private(output, result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real62", type=Path, required=True)
    parser.add_argument("--r4-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        value = materialize_reconciliation(
            real62_path=args.real62,
            r4_report_path=args.r4_report,
            output=args.output,
        )
    except (
        PrivateReal62ProvenanceError,
        r2.CanonicalMicroSceneAuthorityError,
        u06.InventoryBuildError,
        u07.SceneEnrichmentError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"STATUS={FAIL_STATUS}")
        print(f"ERROR={exc}")
        return 1

    print(f"STATUS={value['validation_status']}")
    print(f"REAL62_ARTIFACT_SHA256={value['real62_artifact_sha256']}")
    print(f"REAL62_FILE_SHA256={value['real62_file_sha256']}")
    print(f"CANONICAL_SCENES={value['canonical_scene_count']}")
    print(f"UNIT01_BINDABLE_SCENES={value['unit01_runtime_bindable_scene_count']}")
    print("DEFERRED_SCENE_REFS=" + ",".join(value["deferred_scene_refs"]))
    print(f"MODEL_SCENES={value['model_scene_count']}")
    print(f"RECONCILED_MODEL_SCENES={value['reconciled_model_scene_count']}")
    print(f"UNRESOLVED_MODEL_SCENES={value['unresolved_model_scene_count']}")
    print(f"MODEL_SCENES_WITH_REAL62_SEED={value['model_scenes_with_real62_seed']}")
    print(
        "MODEL_SCENES_WITH_CANONICAL_CONTEXT_SEED="
        f"{value['model_scenes_with_canonical_context_seed']}"
    )
    print(f"UNIQUE_REAL62_SEED_REFS={value['unique_real62_seed_ref_count']}")
    print(
        "UNIQUE_CANONICAL_CONTEXT_SEED_REFS="
        f"{value['unique_canonical_context_seed_ref_count']}"
    )
    print(f"SOURCE_TEXT_EXPORTED={value['source_text_exported']}")
    print(f"OUTPUT={Path(args.output).resolve()}")
    print(f"NEXT_SHORT_STEP={value['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

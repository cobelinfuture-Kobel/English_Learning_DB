from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from product.a1fs_v1_2_1 import u01qb18f_r4_full_semantic_language_pedagogical_replay as r4
from product.a1fs_v1_2_1 import u01qb18f_r5_private_real62_seed_provenance_reconciliation as runner
from ulga.builders import _u01qb18f_r2_canonical_micro_scene_authority_fullfix as r2
from ulga.builders import build_a1fs_v1_u01qb06_unit01_micro_scene_pool_inventory as u06
from ulga.builders import build_a1fs_v1_u01qb07_unit01_micro_scene_seed_enrichment as u07


def _fake_r4(real62_artifact_sha: str) -> dict:
    return {
        "task_id": r4.TASK_ID,
        "validation_status": r4.PASS_STATUS,
        "runtime_proof": {
            "runtime_item_count": 474,
            "real62_extension_item_count": 186,
            "real62_artifact_sha256": real62_artifact_sha,
            "source_production_database_modified": False,
        },
    }


def _synthetic_real62_inventory(*, project_authored: bool = False) -> dict:
    candidates = u07.candidates(u07.read_json(u07.DEFAULT_SPEC))
    objects = sorted({str(obj) for row in candidates for obj in row["objects"]})
    rows = []
    for obj in objects:
        core = u06.semantic_scene_core(
            setting="SYNTHETIC_PRIVATE_SEED",
            participants=["LEARNER"],
            objects=[obj],
            descriptors=[],
            actions=[],
            relations=[],
            information_structure=["FIRST_MENTION"],
            communicative_functions=["IDENTIFY"],
        )
        rows.append(
            {
                "scene_origin": "REAL62_CONTENT_ASSET",
                "scene_ref_id": f"REAL62-SEED-{obj}",
                "semantic_scene_signature_v2": u06.digest(core),
                "semantic_scene_core": core,
                "lineage_mode": (
                    "PROJECT_AUTHORED_CONTRACT_COMPLETION"
                    if project_authored
                    else "SEMANTIC_ANCHOR_A1_IMITATION"
                ),
                "source_authority": "RAZ_READING_AUTHORITY",
                "content_kind": "MICRO_SCENE",
            }
        )
    return {"scene_rows": rows}


def _install_synthetic_private_identity(
    monkeypatch: pytest.MonkeyPatch,
    path: Path,
    *,
    artifact_sha: str,
) -> str:
    raw_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(
        runner,
        "_real62_identity",
        lambda actual_path: ({"private": "fixture"}, artifact_sha, raw_sha),
    )
    return raw_sha


def test_r5_replays_original_u07_seed_resolution_without_source_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    private_real62 = tmp_path / "real62.approved.private.json"
    private_real62.write_text('{"private":"fixture"}\n', encoding="utf-8")
    artifact_sha = "a" * 64
    raw_sha = _install_synthetic_private_identity(
        monkeypatch,
        private_real62,
        artifact_sha=artifact_sha,
    )
    r4_report = tmp_path / "r4.json"
    r4_report.write_text(json.dumps(_fake_r4(artifact_sha)), encoding="utf-8")
    output = tmp_path / "r5.private.json"

    monkeypatch.setattr(
        runner,
        "_private_inventory",
        lambda approved_content, *, real62_artifact_sha256: _synthetic_real62_inventory(),
    )
    result = runner.materialize_reconciliation(
        real62_path=private_real62,
        r4_report_path=r4_report,
        output=output,
        expected_real62_artifact_sha256=artifact_sha,
    )

    assert r4.NEXT_SHORT_STEP == runner.TASK_ID
    assert result["validation_status"] == runner.PASS_STATUS
    assert result["real62_artifact_sha256"] == artifact_sha
    assert result["real62_file_sha256"] == raw_sha
    assert result["canonical_scene_count"] == 32
    assert result["unit01_runtime_bindable_scene_count"] == 31
    assert result["deferred_scene_refs"] == ["U01-MA-FOOD-04"]
    assert result["model_scene_count"] == 27
    assert result["reconciled_model_scene_count"] == 27
    assert result["unresolved_model_scene_count"] == 0
    assert result["model_scenes_with_real62_seed"] == 27
    assert result["model_scenes_with_canonical_context_seed"] == 0
    assert result["unique_real62_seed_ref_count"] > 0
    assert result["source_text_exported"] is False
    assert result["questionbank_modified"] is False
    assert result["scene_semantics_modified"] is False
    assert result["new_scene_authored"] is False
    assert len(result["provenance_overlay"]) == 27
    persisted = output.read_text(encoding="utf-8")
    assert "text_excerpt" not in persisted
    assert '"sentences"' not in persisted
    assert "MODEL_AUTHORED_FROM_APPROVED_SEEDS" in persisted
    assert "ORIGINAL_U01QB07_RESOLVE_ANCHOR_REFS" in persisted


def test_r5_rejects_r4_and_private_real62_artifact_identity_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    private_real62 = tmp_path / "real62.approved.private.json"
    private_real62.write_text("{}\n", encoding="utf-8")
    artifact_sha = "a" * 64
    _install_synthetic_private_identity(
        monkeypatch,
        private_real62,
        artifact_sha=artifact_sha,
    )
    r4_report = tmp_path / "r4.json"
    r4_report.write_text(json.dumps(_fake_r4("0" * 64)), encoding="utf-8")
    monkeypatch.setattr(
        runner,
        "_private_inventory",
        lambda approved_content, *, real62_artifact_sha256: _synthetic_real62_inventory(),
    )
    with pytest.raises(
        runner.PrivateReal62ProvenanceError,
        match="R4_REAL62_ARTIFACT_IDENTITY_MISMATCH",
    ):
        runner.materialize_reconciliation(
            real62_path=private_real62,
            r4_report_path=r4_report,
            output=tmp_path / "out.json",
            expected_real62_artifact_sha256=artifact_sha,
        )


def test_r5_forbids_project_authored_completion_as_seed() -> None:
    with pytest.raises(
        runner.PrivateReal62ProvenanceError,
        match="ELIGIBLE_APPROVED_SEED_ANCHORS_MISSING",
    ):
        runner._reconcile_inventory(_synthetic_real62_inventory(project_authored=True))


def test_r5_fails_if_current_canonical_scene_semantics_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = r2.canonical_scene_package

    def drifted(ref: str):
        value = original(ref)
        if ref == "U01-MA-SCH-01":
            value = deepcopy(value)
            value["semantic_scene_signature_v2"] = "0" * 64
        return value

    monkeypatch.setattr(r2, "canonical_scene_package", drifted)
    with pytest.raises(
        runner.PrivateReal62ProvenanceError,
        match="MODEL_SCENE_SEMANTIC_DRIFT:U01-MA-SCH-01",
    ):
        runner._reconcile_inventory(_synthetic_real62_inventory())


def test_r5_content_policy_boundary() -> None:
    assert runner.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert runner.A1FS_CONTENT_POLICY_EXEMPTION
    assert runner.EXPECTED_MODEL_SCENES == 27
    assert runner.EXPECTED_REAL62_ARTIFACT_SHA256 == (
        "5b8564788cb645d8d3dd784316be5b05f950260da173a2bee7cfcbe1a7d9ab46"
    )
    assert runner.NEXT_SHORT_STEP.startswith("A1FS-V1-U01QB18G_")

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ulga.builders import (
    build_a1fs_v1_u01qb15_production_release_state_acceptance_and_closeout as closeout,
)


def test_unit01_u01qb15_production_release_closeout_accepts_exact_operator_edge_evidence() -> None:
    result = closeout.validate_release_state()
    assert result["status"] == closeout.PASS_STATUS
    assert result["product_status"] == closeout.PRODUCT_STATUS
    assert result["unit01_closeout_complete"] is True
    assert result["release_authority"] == {
        "product_version": "1.2.1",
        "serve_module": "product.a1fs_v1_2_1.u01qb15_runtime_server_e2e",
        "unit_count": 24,
        "lesson_count": 72,
        "static_asset_count": 277,
        "unit01_questionbank_revision": "U01QB15-R1",
        "unit01_runtime_item_count": 474,
        "unit01_extension_item_count": 186,
        "unit01_form_count": 12,
        "unit01_blueprint_activity_count": 240,
    }
    assert result["learner_vertical_acceptance"]["reading_form_1_to_2"] is True
    assert result["learner_vertical_acceptance"]["writing_form_1_scoring_outcome"] == "AUTO_PASS"
    assert result["learner_vertical_acceptance"]["speaking_form_1_to_2"] is True
    assert result["learner_vertical_acceptance"]["legacy_unit02_to_unit24_route_preserved"] is True
    assert result["learner_vertical_acceptance"]["canonical_source_state_unchanged"] is True
    assert result["claim_boundaries"]["a2_unlocked"] is False
    assert result["claim_boundaries"]["listening_enabled"] is False
    assert result["claim_boundaries"]["speaking_scoring_enabled"] is False


def test_closeout_fails_closed_if_operator_edge_evidence_is_tampered(tmp_path: Path) -> None:
    evidence = json.loads(closeout.EVIDENCE_PATH.read_text(encoding="utf-8"))
    evidence["console_observed"]["canonical_source_state_unchanged"] = False
    evidence["pass_contract_assertions"]["legacy_non_unit01_route_smoke_passed"] = False
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(evidence), encoding="utf-8")
    with pytest.raises(closeout.ProductionReleaseCloseoutError) as caught:
        closeout.validate_release_state(evidence_path=path)
    message = str(caught.value)
    assert "EDGE_CANONICAL_SOURCE_STATE_UNCHANGED_INVALID" in message
    assert "EDGE_CONTRACT_LEGACY_NON_UNIT01_ROUTE_SMOKE_PASSED_INVALID" in message


def test_closeout_fails_closed_on_release_manifest_denominator_drift(tmp_path: Path) -> None:
    manifest = json.loads(closeout.MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["unit01_questionbank_runtime_item_count"] = 473
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(
        closeout.ProductionReleaseCloseoutError,
        match="MANIFEST_UNIT01_QUESTIONBANK_RUNTIME_ITEM_COUNT_INVALID",
    ):
        closeout.validate_release_state(manifest_path=path)

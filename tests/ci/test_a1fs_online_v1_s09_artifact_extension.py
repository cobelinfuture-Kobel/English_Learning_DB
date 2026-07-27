from __future__ import annotations

from ulga.artifacts.a1fs_artifact_authority import DEFAULT_MANIFEST
from ulga.runners import materialize_a1fs_online_v1 as runner


def test_default_authority_loads_s09_through_s15_without_overwriting_prior_nodes() -> None:
    manifest = runner._load_effective_manifest(DEFAULT_MANIFEST)
    assert manifest["default_through"] == "S15_SAFE"
    for artifact_id in (
        "S08_SAFE",
        "S09_SAFE",
        "S10_SAFE",
        "S11_SAFE",
        "S12_SAFE",
        "S13_SAFE",
        "S14_SAFE",
        "S15_SAFE",
    ):
        assert artifact_id in manifest["artifacts"]

    s09_entry = manifest["artifacts"]["S09_SAFE"]
    assert s09_entry["dependencies"] == ["CP01", "CP04", "M03", "S08_SAFE"]
    assert s09_entry["expected"]["population_summary.populated_unit_count"] == 24
    assert s09_entry["expected"]["runtime_summary.populated_asset_count"] == 264

    s10_entry = manifest["artifacts"]["S10_SAFE"]
    assert s10_entry["dependencies"] == ["S09_SAFE"]
    assert s10_entry["expected"]["release_candidate_summary.unit_count"] == 24
    assert s10_entry["expected"]["release_candidate_summary.restart_resume_pass"] is True

    s11_entry = manifest["artifacts"]["S11_SAFE"]
    assert s11_entry["dependencies"] == ["S10_SAFE"]
    assert s11_entry["expected"]["security_acceptance_summary.authentication_required"] is True
    assert s11_entry["expected"]["security_acceptance_summary.csrf_required_for_state_change"] is True
    assert s11_entry["expected"]["deployment_boundary.public_release_completed"] is False

    s12_entry = manifest["artifacts"]["S12_SAFE"]
    assert s12_entry["dependencies"] == ["S11_SAFE"]
    assert s12_entry["expected"]["remote_acceptance_summary.acceptance_mode"] == "SIMULATED_EXTERNAL_HTTPS_EDGE"
    assert s12_entry["expected"]["remote_acceptance_summary.direct_origin_bypass_blocked"] is True
    assert s12_entry["expected"]["remote_acceptance_summary.secure_host_cookie_observed"] is True
    assert s12_entry["expected"]["deployment_boundary.live_remote_deployment_completed"] is False
    assert s12_entry["expected"]["deployment_boundary.public_release_completed"] is False

    s13_entry = manifest["artifacts"]["S13_SAFE"]
    assert s13_entry["dependencies"] == ["S12_SAFE"]
    assert s13_entry["expected"]["localhost_acceptance_summary.unit_count"] == 24
    assert s13_entry["expected"]["localhost_acceptance_summary.logout_revocation_survived_process_restart"] is True
    assert s13_entry["expected"]["deployment_boundary.formal_localhost_launch_ready"] is True
    assert s13_entry["expected"]["deployment_boundary.cloudflare_enabled"] is False
    assert s13_entry["expected"]["deployment_boundary.public_release_completed"] is False

    s14_entry = manifest["artifacts"]["S14_SAFE"]
    assert s14_entry["dependencies"] == ["S13_SAFE"]
    assert s14_entry["expected"]["learner_semantics_summary.unit_count"] == 24
    assert s14_entry["expected"]["learner_semantics_summary.bilingual_unit_label_count"] == 24
    assert s14_entry["expected"]["learner_semantics_summary.learner_primary_internal_id_count"] == 0
    assert s14_entry["expected"]["learner_semantics_summary.session_unit_mastery_semantics_separated"] is True
    assert s14_entry["expected"]["learner_semantics_summary.raw_progress_default_visible"] is False
    assert s14_entry["expected"]["capability_contract.cloudflare_enabled"] is False
    assert s14_entry["expected"]["capability_contract.audio_enabled"] is False

    s15_entry = manifest["artifacts"]["S15_SAFE"]
    assert s15_entry["dependencies"] == ["S14_SAFE"]
    assert s15_entry["expected"]["scored_journey_summary.unit_count"] == 24
    assert s15_entry["expected"]["scored_journey_summary.reading_scored_journey_pass"] is True
    assert s15_entry["expected"]["scored_journey_summary.writing_scored_or_human_reviewed_journey_pass"] is True
    assert s15_entry["expected"]["scored_journey_summary.retry_attempt_history_connected"] is True
    assert s15_entry["expected"]["scored_journey_summary.pending_human_review_blocked"] is True
    assert s15_entry["expected"]["capability_contract.parallel_scoring_engine_created"] is False
    assert s15_entry["expected"]["capability_contract.mastery_write_enabled"] is False
    assert s15_entry["expected"]["capability_contract.audio_enabled"] is False
    assert s15_entry["expected"]["capability_contract.cloudflare_enabled"] is False


def test_explicit_manifest_does_not_load_default_online_extensions(tmp_path) -> None:
    explicit = tmp_path / "manifest.json"
    explicit.write_text(
        """{
  "schema_version": "a1fs.artifact.authority.v1",
  "task_id": "A1FS-ARTIFACT-AUTHORITY-V1-S00_SharedArtifactRootManifestAndChainRunner",
  "artifact_root_env": "ENGLISH_DB_ARTIFACT_ROOT",
  "default_through": "ONLY",
  "artifacts": {
    "ONLY": {
      "authority": "repository",
      "path": "example.json",
      "dependencies": [],
      "expected": {}
    }
  }
}
""",
        encoding="utf-8",
    )
    manifest = runner._load_effective_manifest(explicit)
    assert manifest["default_through"] == "ONLY"
    assert set(manifest["artifacts"]) == {"ONLY"}

from __future__ import annotations

from ulga.artifacts.a1fs_artifact_authority import DEFAULT_MANIFEST
from ulga.runners import materialize_a1fs_online_v1 as runner


def test_default_authority_loads_s09_s10_extension_without_overwriting_prior_nodes() -> None:
    manifest = runner._load_effective_manifest(DEFAULT_MANIFEST)
    assert manifest["default_through"] == "S10_SAFE"
    assert "S08_SAFE" in manifest["artifacts"]
    assert "S09_SAFE" in manifest["artifacts"]
    assert "S10_SAFE" in manifest["artifacts"]

    s09_entry = manifest["artifacts"]["S09_SAFE"]
    assert s09_entry["dependencies"] == ["CP01", "CP04", "M03", "S08_SAFE"]
    assert s09_entry["expected"]["population_summary.populated_unit_count"] == 24
    assert s09_entry["expected"]["runtime_summary.populated_asset_count"] == 264

    s10_entry = manifest["artifacts"]["S10_SAFE"]
    assert s10_entry["dependencies"] == ["S09_SAFE"]
    assert s10_entry["expected"]["release_candidate_summary.unit_count"] == 24
    assert s10_entry["expected"]["release_candidate_summary.asset_count"] == 264
    assert s10_entry["expected"]["release_candidate_summary.restart_resume_pass"] is True
    assert s10_entry["expected"]["production_safety.production_database_unchanged"] is True


def test_explicit_manifest_does_not_load_default_s09_s10_extension(tmp_path) -> None:
    explicit = tmp_path / "manifest.json"
    explicit.write_text(
        """{
  \"schema_version\": \"a1fs.artifact.authority.v1\",
  \"task_id\": \"A1FS-ARTIFACT-AUTHORITY-V1-S00_SharedArtifactRootManifestAndChainRunner\",
  \"artifact_root_env\": \"ENGLISH_DB_ARTIFACT_ROOT\",
  \"default_through\": \"ONLY\",
  \"artifacts\": {
    \"ONLY\": {
      \"authority\": \"repository\",
      \"path\": \"example.json\",
      \"dependencies\": [],
      \"expected\": {}
    }
  }
}
""",
        encoding="utf-8",
    )
    manifest = runner._load_effective_manifest(explicit)
    assert manifest["default_through"] == "ONLY"
    assert set(manifest["artifacts"]) == {"ONLY"}

from __future__ import annotations

from ulga.artifacts.a1fs_artifact_authority import DEFAULT_MANIFEST
from ulga.runners import materialize_a1fs_online_v1 as runner


def test_default_authority_loads_s09_extension_without_overwriting_prior_nodes() -> None:
    manifest = runner._load_effective_manifest(DEFAULT_MANIFEST)
    assert manifest["default_through"] == "S09_SAFE"
    assert "S08_SAFE" in manifest["artifacts"]
    assert "S09_SAFE" in manifest["artifacts"]
    entry = manifest["artifacts"]["S09_SAFE"]
    assert entry["dependencies"] == ["CP01", "CP04", "M03", "S08_SAFE"]
    assert entry["expected"]["population_summary.populated_unit_count"] == 24
    assert entry["expected"]["runtime_summary.populated_asset_count"] == 264


def test_explicit_manifest_does_not_load_default_s09_extension(tmp_path) -> None:
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

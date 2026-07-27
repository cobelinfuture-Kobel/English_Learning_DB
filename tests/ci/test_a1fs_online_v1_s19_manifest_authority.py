from __future__ import annotations

from ulga.artifacts.a1fs_artifact_authority import DEFAULT_MANIFEST
from ulga.runners import materialize_a1fs_online_v1 as runner


def test_s19_is_the_default_authority_tail_and_s20_is_not_admitted() -> None:
    manifest = runner._load_effective_manifest(DEFAULT_MANIFEST)
    assert manifest["default_through"] == "S19_SAFE"
    s18 = manifest["artifacts"]["S18_SAFE"]
    assert s18["dependencies"] == ["S17_SAFE"]
    s19 = manifest["artifacts"]["S19_SAFE"]
    assert s19["dependencies"] == ["S18_SAFE"]
    assert s19["path"] == "a1fs_v1/online_v1/s19/localhost_nonaudio_release_candidate.private.json"
    assert s19["report_path"] == "a1fs_v1/online_v1/s19/localhost_nonaudio_release_candidate.safe.json"
    assert s19["expected"]["release_candidate_id"] == "A1FS-ONLINE-V1-D0-RC1"
    assert s19["expected"]["release_candidate_summary.release_candidate_created"] is True
    assert s19["expected"]["release_candidate_summary.release_candidate_externally_deployed"] is False
    assert s19["expected"]["capability_contract.new_product_capability_created"] is False
    assert s19["expected"]["capability_contract.cloudflare_enabled"] is False
    assert "S20_SAFE" not in manifest["artifacts"]

from __future__ import annotations

from ulga.artifacts.a1fs_artifact_authority import DEFAULT_MANIFEST
from ulga.runners import materialize_a1fs_online_v1 as runner


def test_s18_remains_direct_predecessor_of_s19_authority_tail() -> None:
    manifest = runner._load_effective_manifest(DEFAULT_MANIFEST)
    assert manifest["default_through"] == "S19_SAFE"
    s17 = manifest["artifacts"]["S17_SAFE"]
    assert s17["dependencies"] == ["S16_SAFE"]
    assert s17["path"] == "a1fs_v1/online_v1/s17/dashboard_human_review.private.json"
    s18 = manifest["artifacts"]["S18_SAFE"]
    assert s18["dependencies"] == ["S17_SAFE"]
    assert s18["path"] == "a1fs_v1/online_v1/s18/nonaudio_e2e_release_acceptance_recovery.private.json"
    assert s18["report_path"] == "a1fs_v1/online_v1/s18/nonaudio_e2e_release_acceptance_recovery.safe.json"
    s19 = manifest["artifacts"]["S19_SAFE"]
    assert s19["dependencies"] == ["S18_SAFE"]
    assert "S20_SAFE" not in manifest["artifacts"]

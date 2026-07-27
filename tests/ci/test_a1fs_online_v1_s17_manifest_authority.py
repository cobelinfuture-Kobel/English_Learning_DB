from __future__ import annotations

from ulga.artifacts.a1fs_artifact_authority import DEFAULT_MANIFEST
from ulga.runners import materialize_a1fs_online_v1 as runner


def test_s17_and_s18_remain_direct_predecessors_of_s19_authority_tail() -> None:
    manifest = runner._load_effective_manifest(DEFAULT_MANIFEST)
    assert manifest["default_through"] == "S19_SAFE"
    s16 = manifest["artifacts"]["S16_SAFE"]
    assert s16["dependencies"] == ["CP01", "S15_SAFE"]
    assert s16["path"] == "a1fs_v1/online_v1/s16/canonical_mastery_remediation_review.private.json"
    s17 = manifest["artifacts"]["S17_SAFE"]
    assert s17["dependencies"] == ["S16_SAFE"]
    assert s17["path"] == "a1fs_v1/online_v1/s17/dashboard_human_review.private.json"
    assert s17["report_path"] == "a1fs_v1/online_v1/s17/dashboard_human_review.safe.json"
    s18 = manifest["artifacts"]["S18_SAFE"]
    assert s18["dependencies"] == ["S17_SAFE"]
    s19 = manifest["artifacts"]["S19_SAFE"]
    assert s19["dependencies"] == ["S18_SAFE"]
    assert "S20_SAFE" not in manifest["artifacts"]

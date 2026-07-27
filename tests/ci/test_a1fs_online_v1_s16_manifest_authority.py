from __future__ import annotations

from ulga.artifacts.a1fs_artifact_authority import DEFAULT_MANIFEST
from ulga.runners import materialize_a1fs_online_v1 as runner


def test_s16_remains_the_direct_predecessor_of_s17_authority_tail() -> None:
    manifest = runner._load_effective_manifest(DEFAULT_MANIFEST)
    assert manifest["default_through"] == "S17_SAFE"
    s15 = manifest["artifacts"]["S15_SAFE"]
    assert s15["dependencies"] == ["S14_SAFE"]
    assert s15["path"] == "a1fs_v1/online_v1/s15/reading_writing_scored_journey.private.json"
    s16 = manifest["artifacts"]["S16_SAFE"]
    assert s16["dependencies"] == ["CP01", "S15_SAFE"]
    assert s16["path"] == "a1fs_v1/online_v1/s16/canonical_mastery_remediation_review.private.json"
    assert s16["report_path"] == "a1fs_v1/online_v1/s16/canonical_mastery_remediation_review.safe.json"
    s17 = manifest["artifacts"]["S17_SAFE"]
    assert s17["dependencies"] == ["S16_SAFE"]

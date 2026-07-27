from __future__ import annotations

from ulga.artifacts.a1fs_artifact_authority import DEFAULT_MANIFEST
from ulga.runners import materialize_a1fs_online_v1 as runner


def test_s14_through_s17_remain_ordered_predecessors_of_s18() -> None:
    manifest = runner._load_effective_manifest(DEFAULT_MANIFEST)
    assert manifest["default_through"] == "S18_SAFE"
    s14 = manifest["artifacts"]["S14_SAFE"]
    assert s14["dependencies"] == ["S13_SAFE"]
    assert s14["path"] == "a1fs_v1/online_v1/s14/learner_facing_semantics.private.json"
    assert s14["report_path"] == "a1fs_v1/online_v1/s14/learner_facing_semantics.safe.json"
    s15 = manifest["artifacts"]["S15_SAFE"]
    assert s15["dependencies"] == ["S14_SAFE"]
    assert s15["path"] == "a1fs_v1/online_v1/s15/reading_writing_scored_journey.private.json"
    assert s15["report_path"] == "a1fs_v1/online_v1/s15/reading_writing_scored_journey.safe.json"
    s16 = manifest["artifacts"]["S16_SAFE"]
    assert s16["dependencies"] == ["CP01", "S15_SAFE"]
    s17 = manifest["artifacts"]["S17_SAFE"]
    assert s17["dependencies"] == ["S16_SAFE"]
    s18 = manifest["artifacts"]["S18_SAFE"]
    assert s18["dependencies"] == ["S17_SAFE"]

from __future__ import annotations

from ulga.artifacts.a1fs_artifact_authority import DEFAULT_MANIFEST
from ulga.runners import materialize_a1fs_online_v1 as runner


def test_s14_is_the_only_new_default_authority_tail() -> None:
    manifest = runner._load_effective_manifest(DEFAULT_MANIFEST)
    assert manifest["default_through"] == "S14_SAFE"
    entry = manifest["artifacts"]["S14_SAFE"]
    assert entry["dependencies"] == ["S13_SAFE"]
    assert entry["path"] == "a1fs_v1/online_v1/s14/learner_facing_semantics.private.json"
    assert entry["report_path"] == "a1fs_v1/online_v1/s14/learner_facing_semantics.safe.json"
    assert "S15_SAFE" not in manifest["artifacts"]

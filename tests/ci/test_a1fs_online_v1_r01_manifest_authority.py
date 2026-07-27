from __future__ import annotations

from ulga.runners import materialize_a1fs_online_v1_r01 as r01_runner


def test_r01_shared_authority_extends_s19_without_replacing_it() -> None:
    manifest = r01_runner.load_r01_manifest()
    assert manifest["default_through"] == "R01_SAFE"
    assert manifest["artifacts"]["R01_SAFE"]["dependencies"] == ["S19_SAFE"]
    command = manifest["artifacts"]["R01_SAFE"]["command"]
    assert command[1:3] == [
        "-m",
        "ulga.builders.build_a1fs_online_v1_r01_self_contained_product_root_update_channel",
    ]
    assert manifest["artifacts"]["S19_SAFE"]["dependencies"] == ["S18_SAFE"]


def test_r01_runner_declares_non_content_producer_governance() -> None:
    assert r01_runner.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert r01_runner.A1FS_CONTENT_POLICY_EXEMPTION

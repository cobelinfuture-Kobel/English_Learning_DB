from __future__ import annotations

from pathlib import Path

from ulga.runners import materialize_a1fs_online_v1_r01 as r01_runner
from ulga.runners import run_a1fs_r01_with_product_root_authority as product_root_runner


def test_r01_shared_authority_extends_s19_without_replacing_it() -> None:
    manifest = r01_runner.load_r01_manifest()
    assert manifest["default_through"] == "R01_SAFE"
    assert manifest["artifacts"]["R01_SAFE"]["dependencies"] == ["S19_SAFE"]
    command = manifest["artifacts"]["R01_SAFE"]["command"]
    assert command[1:3] == [
        "-m",
        "ulga.runners.run_a1fs_r01_with_product_root_authority",
    ]
    assert "ulga/runners/run_a1fs_r01_with_product_root_authority.py" in (
        manifest["artifacts"]["R01_SAFE"]["repository_inputs"]
    )
    assert manifest["artifacts"]["S19_SAFE"]["dependencies"] == ["S18_SAFE"]


def test_product_root_authority_prefers_explicit_then_environment(
    tmp_path: Path, monkeypatch,
) -> None:
    output = tmp_path / "authority" / "r01.private.json"
    configured = tmp_path / "configured" / "A1FS_V1"
    explicit = tmp_path / "explicit" / "A1FS_V1"
    monkeypatch.setenv(product_root_runner.PRODUCT_ROOT_ENV, str(configured))
    assert product_root_runner.resolve_product_root(
        explicit=None, output_path=output,
    ) == configured.resolve()
    assert product_root_runner.resolve_product_root(
        explicit=explicit, output_path=output,
    ) == explicit.resolve()
    monkeypatch.delenv(product_root_runner.PRODUCT_ROOT_ENV)
    assert product_root_runner.resolve_product_root(
        explicit=None, output_path=output,
    ) == (output.parent / "A1FS_V1").resolve()


def test_r01_runner_declares_non_content_producer_governance() -> None:
    assert r01_runner.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert r01_runner.A1FS_CONTENT_POLICY_EXEMPTION
    assert product_root_runner.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert product_root_runner.A1FS_CONTENT_POLICY_EXEMPTION

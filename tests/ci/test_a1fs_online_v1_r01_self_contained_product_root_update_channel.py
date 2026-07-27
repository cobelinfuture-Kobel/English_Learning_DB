from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_online_v1_r01_self_contained_product_root_update_channel as r01
from ulga.validators.validate_a1fs_online_v1_r01_self_contained_product_root_update_channel import validate_outputs


def _sqlite(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS marker(value TEXT)")
        connection.execute("INSERT INTO marker(value) VALUES('preserved')")


def _source(tmp_path: Path):
    database = tmp_path / "source/runtime.sqlite3"
    auth = tmp_path / "source/auth.sqlite3"
    _sqlite(database)
    _sqlite(auth)
    state = tmp_path / "source/state"
    state.mkdir(parents=True)
    (state / "snapshot.json").write_text('{"state":"ok"}\n', encoding="utf-8")
    static = tmp_path / "source/static"
    static.mkdir()
    (static / "index.html").write_text("<html>ok</html>", encoding="utf-8")
    graph = tmp_path / "source/graph.json"
    graph.write_text('{"nodes":[]}\n', encoding="utf-8")
    bundles = {f"LESSON_{i:03d}": {"lesson_id": f"LESSON_{i:03d}"} for i in range(72)}
    sequence = {f"UNIT_{i:02d}": i for i in range(1, 25)}
    return database, auth, bundles, sequence, graph, state, static


def test_materializes_single_v1_root_with_relative_release_and_shared_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    database, auth, bundles, sequence, graph, state, static = _source(tmp_path)
    source_receipt = {"task_id": r01.s19.TASK_ID}
    monkeypatch.setattr(
        r01, "_source_from_s19",
        lambda _: (source_receipt, database, auth, bundles, sequence, graph, state, static),
    )
    code_root = tmp_path / "code"
    module = code_root / "ulga/builders"
    module.mkdir(parents=True)
    (code_root / "ulga/__init__.py").write_text("", encoding="utf-8")
    (module / "__init__.py").write_text("", encoding="utf-8")
    (module / "build_a1fs_online_v1_r01_self_contained_product_root_update_channel.py").write_text(
        "A1FS_CONTENT_POLICY_MODE='NOT_CONTENT_PRODUCER'\n", encoding="utf-8"
    )
    output = tmp_path / "authority/r01.private.json"
    report = tmp_path / "authority/r01.safe.json"
    root = output.parent / "A1FS_V1"
    receipt, safe = r01.materialize(
        s19_path=tmp_path / "s19.json", output_path=output, report_path=report,
        product_root=root, code_root=code_root,
    )
    assert (root / "releases/1.0.0").is_dir()
    assert (root / "shared/database/learner_runtime.sqlite3").is_file()
    assert (root / "shared/auth/auth_state.sqlite3").is_file()
    assert (root / "shared/learner_state/canonical_learning_state").is_dir()
    assert (root / "current_version.txt").read_text(encoding="ascii").strip() == "1.0.0"
    manifest = r01.validate_release(root / "releases/1.0.0")
    for key in (
        "app_root", "secure_static_root", "graph_path", "bundle_registry_path",
        "sequence_path", "shared_database_path", "shared_auth_state_path",
        "shared_learner_state_root",
    ):
        assert not Path(manifest[key]).is_absolute()
        assert ":" not in manifest[key]
    validation = validate_outputs(
        receipt=receipt, safe_report=safe, output_root=output.parent,
        s19_path=tmp_path / "s19.json",
    )
    assert validation["error_count"] == 0, validation["errors"]


def _candidate(path: Path, version: str) -> Path:
    path.mkdir(parents=True)
    (path / "app").mkdir()
    (path / "app/marker.txt").write_text(version, encoding="utf-8")
    r01.write_json(path / "release_manifest.json", r01._release_manifest(version))
    r01.write_json(path / "VERSION.json", {
        "product_id": r01.PRODUCT_ID, "product_version": version, "immutable_release": True,
    })
    r01._write_checksums(path)
    return path


def test_atomic_update_and_rollback_preserve_shared_state(tmp_path: Path) -> None:
    root = tmp_path / "A1FS_V1"
    _candidate(root / "releases/1.0.0", "1.0.0")
    _sqlite(root / "shared/database/learner_runtime.sqlite3")
    _sqlite(root / "shared/auth/auth_state.sqlite3")
    state = root / "shared/learner_state/canonical_learning_state"
    state.mkdir(parents=True)
    (state / "progress.json").write_text('{"attempts":7}\n', encoding="utf-8")
    r01._atomic_text(root / "current_version.txt", "1.0.0\n")
    candidate = _candidate(tmp_path / "candidate-1.0.1", "1.0.1")
    before = r01.directory_digest(root / "shared")
    result = r01.install_candidate(product_root=root, candidate=candidate, version="1.0.1")
    assert result["status"] == "PASS_ATOMIC_UPDATE_ACTIVATED"
    assert r01._current_version(root) == "1.0.1"
    assert r01.directory_digest(root / "shared") == before
    assert (root / "backups/before_1.0.1/database/learner_runtime.sqlite3").is_file()
    rolled = r01.rollback(product_root=root)
    assert rolled["status"] == "PASS_ATOMIC_ROLLBACK_ACTIVATED"
    assert r01._current_version(root) == "1.0.0"
    assert r01.directory_digest(root / "shared") == before


def test_operator_bat_files_are_ascii_crlf_and_bom_free(tmp_path: Path) -> None:
    outputs = r01._write_operator_bundle(tmp_path)
    assert set(outputs) == {
        "OPEN_A1FS_V1.bat", "STOP_A1FS_V1.bat", "STATUS_A1FS_V1.bat",
        "UPDATE_A1FS_V1.bat", "ROLLBACK_A1FS_V1.bat",
    }
    for path in map(Path, outputs.values()):
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf")
        assert b"\r\n" in data
        assert all(byte < 128 for byte in data)


@pytest.mark.parametrize("value", ["/absolute/path", "../escape", "C:/windows/path", ""])
def test_relative_product_paths_fail_closed(value: str) -> None:
    with pytest.raises(r01.ProductRootError, match="not_relative"):
        r01._relative(value)


def test_r01_declares_non_content_producer_governance() -> None:
    assert r01.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert r01.A1FS_CONTENT_POLICY_EXEMPTION

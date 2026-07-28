from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

from ulga.builders import _a1fs_v1_1_m02_exact_sequence_static_adapter as sequence_adapter
from ulga.builders import _a1fs_v1_1_m02_release_core as core
from ulga.builders import build_a1fs_online_v1_r01_self_contained_product_root_update_channel as r01
from ulga.builders import build_a1fs_v1_1_m01_unit01_cross_skill_vertical_slice as m01
from ulga.builders import build_a1fs_v1_1_m02_unit01_local_product_acceptance_release as builder
from ulga.builders import build_a1fs_v1_1_m02f_exact_sequence_learner_submission_fullfix as fullfix
from ulga.validators import validate_a1fs_v1_1_m02_unit01_local_product_acceptance_release as validator
from ulga.validators import validate_a1fs_v1_1_m02f_exact_sequence_learner_submission_fullfix as fullfix_validator


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def bundles_and_sequence() -> tuple[dict, dict[str, int], list[dict]]:
    bundles: dict = {}
    sequence: dict[str, int] = {}
    contracts: list[dict] = []
    grammar_ids = [m01.UNIT_ID] + [f"GRAMMAR_FIXTURE_{index:02d}" for index in range(2, 25)]
    reading_answers = ["a cat", "the book", "an apple", "a cat"]
    writing_answers = ["a bag", "an apple", "the book", "the apple"]
    for unit_index, grammar_id in enumerate(grammar_ids, start=1):
        sequence[grammar_id] = unit_index
        for skill, count in (("READING", 4), ("WRITING", 4), ("SPEAKING", 3)):
            lesson_id = f"A1FS_ONLINE_V1:{grammar_id}:{skill}"
            assets = []
            for asset_index in range(1, count + 1):
                asset_key = f"ASSET:{grammar_id}:{skill}:{asset_index}"
                role = "CHK" if asset_index == count and skill != "SPEAKING" else "PRD"
                assets.append({
                    "asset_key": asset_key,
                    "role": role,
                    "learner_payload": {
                        "prompt": f"Original {skill} {asset_index}",
                        "response_capture_enabled": skill != "SPEAKING",
                    },
                })
                if grammar_id == m01.UNIT_ID:
                    if skill == "READING":
                        answer = reading_answers[asset_index - 1]
                        contract = {
                            "scoring_mode": "NORMALIZED_TEXT",
                            "response_type": "string",
                            "accepted_texts": [answer],
                            "accepted_sequence": [],
                            "human_review_fallback": False,
                        }
                    elif skill == "WRITING":
                        answer = writing_answers[asset_index - 1]
                        if asset_index == 2:
                            contract = {
                                "scoring_mode": "EXACT_SEQUENCE",
                                "response_type": "sequence",
                                "accepted_texts": [],
                                "accepted_sequence": ["an", "apple"],
                                "human_review_fallback": False,
                            }
                        else:
                            contract = {
                                "scoring_mode": "NORMALIZED_TEXT",
                                "response_type": "string",
                                "accepted_texts": [answer],
                                "accepted_sequence": [],
                                "human_review_fallback": False,
                            }
                    else:
                        contract = {
                            "scoring_mode": "FEATURE_RUBRIC",
                            "response_type": "string",
                            "accepted_texts": [],
                            "accepted_sequence": [],
                            "human_review_fallback": True,
                            "rubric": {"practice_only": True},
                        }
                    contracts.append({
                        "lesson_id": lesson_id,
                        "asset_key": asset_key,
                        "role": role,
                        "capture_enabled": 0 if skill == "SPEAKING" else 1,
                        "contract": contract,
                    })
            bundles[lesson_id] = {
                "lesson": {"lesson_id": lesson_id, "skill": skill, "level": "A1"},
                "assets": assets,
            }
    return bundles, sequence, contracts


def sqlite_file(path: Path, marker: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE marker(value TEXT NOT NULL)")
        connection.execute("INSERT INTO marker(value) VALUES(?)", (marker,))
        connection.commit()


def product_database(path: Path, contracts: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """CREATE TABLE response_contracts(
                asset_key TEXT PRIMARY KEY,
                lesson_id TEXT NOT NULL,
                skill TEXT NOT NULL,
                role TEXT NOT NULL,
                capture_enabled INTEGER NOT NULL,
                contract_json TEXT NOT NULL,
                contract_digest TEXT NOT NULL
            )"""
        )
        for row in contracts:
            skill = row["lesson_id"].rsplit(":", 1)[-1]
            rendered = json.dumps(row["contract"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            connection.execute(
                "INSERT INTO response_contracts VALUES(?,?,?,?,?,?,?)",
                (
                    row["asset_key"], row["lesson_id"], skill, row["role"],
                    row["capture_enabled"], rendered, r01.digest(row["contract"]),
                ),
            )
        connection.commit()


def product_root(tmp_path: Path) -> tuple[Path, dict, dict[str, int]]:
    bundles, sequence, contracts = bundles_and_sequence()
    root = tmp_path / "A1FS_V1"
    release = root / "releases" / core.SOURCE_VERSION
    (release / "app/ulga").mkdir(parents=True)
    (release / "app/ulga/__init__.py").write_text("\n", encoding="utf-8")
    static = release / "runtime/secure_static"
    static.mkdir(parents=True)
    (static / "index.html").write_text("<html></html>\n", encoding="utf-8")
    (static / "app.js").write_text(
        "'use strict';"
        + sequence_adapter.SOURCE_RESPONSE_FOR
        + "card.append(prompt);const options=asset.learner_payload.options||[];\n",
        encoding="utf-8",
    )
    (static / "styles.css").write_text("body{}\n", encoding="utf-8")
    write_json(release / "runtime/graph.json", {"nodes": []})
    write_json(release / "runtime/bundles.json", bundles)
    write_json(release / "runtime/sequence.json", sequence)
    write_json(release / "VERSION.json", {
        "product_id": r01.PRODUCT_ID,
        "product_version": core.SOURCE_VERSION,
        "immutable_release": True,
    })
    write_json(release / "release_manifest.json", r01._release_manifest(core.SOURCE_VERSION))
    r01._write_checksums(release)
    r01.validate_release(release)
    product_database(root / "shared/database/learner_runtime.sqlite3", contracts)
    sqlite_file(root / "shared/auth/auth_state.sqlite3", "auth")
    state = root / "shared/learner_state/canonical_learning_state"
    state.mkdir(parents=True)
    write_json(state / "state.json", {"state": "preserved"})
    (root / "shared/logs").mkdir(parents=True)
    (root / "shared/config").mkdir(parents=True)
    (root / "current_version.txt").write_text(core.SOURCE_VERSION + "\n", encoding="ascii")
    write_json(root / "product.json", {"product_id": r01.PRODUCT_ID})
    return root, bundles, sequence


def fake_acceptance(*, product_root: Path) -> dict:
    current = (Path(product_root) / "current_version.txt").read_text(encoding="ascii").strip()
    assert current == core.TARGET_VERSION
    reading = {
        "lesson_id": m01.LESSON_IDS["READING"],
        "contract_count": 4,
        "outcomes": ["AUTO_PASS"] * 4,
        "pending_human_review_count": 0,
        "completion_allowed": True,
        "session_completed": True,
    }
    writing = dict(reading)
    writing["lesson_id"] = m01.LESSON_IDS["WRITING"]
    return {
        "installed_version": core.TARGET_VERSION,
        "authenticated_http_login_pass": True,
        "authenticated_bootstrap_pass": True,
        "authenticated_progress_pass": True,
        "authenticated_dashboard_pass": True,
        "unit_count": 24,
        "lesson_count": 72,
        "asset_count": 264,
        "unit01_real_reading_visible": True,
        "unit01_contextual_writing_visible": True,
        "unit01_speaking_practice_visible": True,
        "reading": reading,
        "writing": writing,
        "speaking_practice_card_count": 3,
        "speaking_capture_enabled": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "a2_unlocked": False,
    }


def test_m02_builds_v11_candidate_and_preserves_production_state(tmp_path: Path) -> None:
    root, source_bundles, _ = product_root(tmp_path)
    code_root = tmp_path / "code"
    (code_root / "ulga").mkdir(parents=True)
    (code_root / "ulga/__init__.py").write_text("\n", encoding="utf-8")
    output = tmp_path / "out/m02.private.json"
    report = tmp_path / "out/m02.safe.json"
    before = core.shared_identity(root)

    receipt, safe = builder.materialize(
        product_root=root,
        code_root=code_root,
        output_path=output,
        report_path=report,
        acceptance_runner=fake_acceptance,
    )

    assert core.shared_identity(root) == before
    assert (root / "current_version.txt").read_text(encoding="ascii").strip() == core.SOURCE_VERSION
    assert receipt["release_summary"]["target_product_version"] == core.TARGET_VERSION
    assert receipt["release_summary"]["preserved_lesson_count"] == 69
    candidate = Path(receipt["runtime_outputs"]["candidate_root"])
    manifest = r01.validate_release(candidate)
    assert manifest["release_id"] == core.RELEASE_ID
    assert manifest["modified_unit_ids"] == [m01.UNIT_ID]
    assert manifest["learner_state_migration_required"] is False
    candidate_bundles = json.loads((candidate / "runtime/bundles.json").read_text(encoding="utf-8"))
    overlay = core.validate_overlay(source_bundles=source_bundles, target_bundles=candidate_bundles)
    assert overlay["changed_lesson_ids"] == sorted(m01.LESSON_IDS.values())
    installer = Path(receipt["runtime_outputs"]["installer_path"])
    raw = installer.read_bytes()
    assert raw.startswith(b"param(")
    assert b"\r\n" in raw and not raw.startswith(b"\xef\xbb\xbf")
    validation = validator.validate_outputs(
        receipt=receipt,
        safe_report=safe,
        output_root=output.parent,
        product_root=root,
    )
    assert validation["error_count"] == 0, validation


def test_overlay_rejects_non_unit01_bundle_drift(tmp_path: Path) -> None:
    root, source_bundles, _ = product_root(tmp_path)
    source = core.source_product(root)
    overlay = core.build_m01_overlay(source, tmp_path / "overlay")
    target = deepcopy(overlay["bundles"])
    lesson = next(value for value in target if value not in m01.LESSON_IDS.values())
    target[lesson]["assets"][0]["learner_payload"]["prompt"] = "forbidden drift"
    with pytest.raises(core.ReleaseCoreError, match="release_changed_lesson_set_invalid"):
        core.validate_overlay(source_bundles=source_bundles, target_bundles=target)


def test_source_version_must_be_v100(tmp_path: Path) -> None:
    root, _, _ = product_root(tmp_path)
    (root / "current_version.txt").write_text("1.0.1\n", encoding="ascii")
    with pytest.raises(core.ReleaseCoreError, match="source_product_version_invalid"):
        core.source_product(root)


def installed_v110_root(tmp_path: Path) -> Path:
    root, _, _ = product_root(tmp_path)
    code_root = tmp_path / "v110-code"
    (code_root / "ulga").mkdir(parents=True)
    (code_root / "ulga/__init__.py").write_text("\n", encoding="utf-8")
    output = tmp_path / "v110-out/m02.private.json"
    report = tmp_path / "v110-out/m02.safe.json"
    receipt, _ = builder.materialize(
        product_root=root,
        code_root=code_root,
        output_path=output,
        report_path=report,
        acceptance_runner=fake_acceptance,
    )
    r01.install_candidate(
        product_root=root,
        candidate=Path(receipt["runtime_outputs"]["candidate_root"]),
        version=core.TARGET_VERSION,
    )
    assert r01._current_version(root) == fullfix.SOURCE_VERSION
    return root


def test_m02f_builds_v111_and_preserves_v110_production_state(tmp_path: Path) -> None:
    root = installed_v110_root(tmp_path)
    before = core.shared_identity(root)
    output = tmp_path / "m02f-out/m02f.private.json"
    report = tmp_path / "m02f-out/m02f.safe.json"

    receipt, safe = fullfix.materialize(
        product_root=root,
        output_path=output,
        report_path=report,
    )

    assert r01._current_version(root) == fullfix.SOURCE_VERSION
    assert core.shared_identity(root) == before
    candidate = Path(receipt["runtime_outputs"]["candidate_root"])
    manifest = r01.validate_release(candidate)
    assert manifest["product_version"] == fullfix.TARGET_VERSION
    assert manifest["learner_submission_adapter"] == "CONTROLLED_SEQUENCE_TEXT_TO_TOKEN_LIST"
    assert manifest["answer_contract_changed"] is False
    sequence_adapter.validate_app_js(candidate / "runtime/secure_static/app.js")
    acceptance_root = Path(receipt["runtime_outputs"]["acceptance_product_root"])
    assert r01._current_version(acceptance_root) == fullfix.TARGET_VERSION
    assert receipt["acceptance_summary"]["shared_state_preserved"] is True
    validation = fullfix_validator.validate_outputs(
        receipt=receipt,
        safe_report=safe,
        product_root=root,
        output_root=output.parent,
    )
    assert validation["error_count"] == 0, validation


def test_exact_sequence_serializer_executes_actual_javascript(tmp_path: Path) -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("node runtime unavailable")
    script = (
        sequence_adapter.SERIALIZER
        + "const seq=serializeTextResponse({learner_payload:{writing_stage:'CONTROLLED_SEQUENCE'}},'  an   apple  ');"
        + "const text=serializeTextResponse({learner_payload:{writing_stage:'GUIDED_CONTEXTUAL_SENTENCE'}},' There is an apple. ');"
        + "if(JSON.stringify(seq)!=='[\"an\",\"apple\"]')process.exit(11);"
        + "if(text!==' There is an apple. ')process.exit(12);"
    )
    result = subprocess.run([node, "-e", script], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_m02f_requires_installed_v110_source(tmp_path: Path) -> None:
    root, _, _ = product_root(tmp_path)
    with pytest.raises(fullfix.M02FFullFixError, match="source_product_version_invalid"):
        fullfix.source_product(root)

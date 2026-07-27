from __future__ import annotations

from pathlib import Path

from ulga.builders import build_a1fs_online_v1_s19_localhost_nonaudio_learner_product_release_candidate as s19
from ulga.validators import validate_a1fs_online_v1_s19_localhost_nonaudio_learner_product_release_candidate as validator


def test_s19_directory_digest_is_deterministic_and_content_bound(tmp_path: Path) -> None:
    root = tmp_path / "tree"
    (root / "nested").mkdir(parents=True)
    (root / "a.txt").write_text("alpha", encoding="utf-8")
    (root / "nested" / "b.txt").write_text("beta", encoding="utf-8")

    first = s19.directory_digest(root)
    assert first == s19.directory_digest(root)

    (root / "nested" / "b.txt").write_text("changed", encoding="utf-8")
    assert s19.directory_digest(root) != first


def test_s19_operator_bundle_is_versioned_loopback_only_and_secret_free(tmp_path: Path) -> None:
    outputs = s19._write_operator_bundle(
        target_root=tmp_path / "operator",
        receipt_path=tmp_path / "s19.private.json",
        auth_state=tmp_path / "auth.sqlite3",
    )
    checks = s19._operator_checks(outputs)
    assert checks == {
        "start_script_contract_pass": True,
        "stop_script_contract_pass": True,
        "status_script_contract_pass": True,
        "readback_script_contract_pass": True,
        "release_contract_boundary_pass": True,
    }
    start = Path(outputs["start_script_path"]).read_text(encoding="utf-8")
    assert s19.RELEASE_CANDIDATE_ID in start
    assert s19.s18.s17.s16.s15.CANARY_PASSWORD not in start
    assert s19.s18.s17.s16.s15.CANARY_SESSION_SECRET not in start
    contract = s19.read_json(Path(outputs["release_contract_path"]), "contract")
    assert contract["host"] == "127.0.0.1"
    assert contract["external_network_binding_allowed"] is False
    assert contract["public_delivery_enabled"] is False
    assert contract["cloudflare_enabled"] is False
    assert contract["audio_enabled"] is False
    assert contract["a2_session_enabled"] is False


def test_s19_checksum_manifest_detects_release_file_drift(tmp_path: Path) -> None:
    release = tmp_path / "release"
    release.mkdir()
    (release / "asset.txt").write_text("accepted", encoding="utf-8")
    checksum_path, rows = s19._write_checksums(release)
    assert rows == {"asset.txt": s19.file_digest(release / "asset.txt")}
    s19._validate_checksums(release, checksum_path)

    (release / "asset.txt").write_text("drift", encoding="utf-8")
    try:
        s19._validate_checksums(release, checksum_path)
    except s19.ReleaseCandidateError as exc:
        assert str(exc) == "s19_checksum_mismatch"
    else:
        raise AssertionError("checksum drift must fail closed")


def test_s19_safe_validator_uses_exact_private_key_identity() -> None:
    safe = {
        "release_candidate_summary": {
            "authenticated_candidate_review_queue_pass": True,
            "production_database_unchanged": True,
        },
        "capability_contract": {
            "versioned_localhost_release_candidate_created": True,
        },
    }
    assert validator._find_exact_private_keys(safe) == set()
    s19.safe_scan(safe)

    private = {
        "nested": [
            {"attempt_id": "private"},
            {"session_id": "private"},
            {"asset_key": "private"},
            {"response_json": {}},
            {"review_queue": []},
            {"database_path": "private"},
            {"auth_state_path": "private"},
            {"state_root": "private"},
        ]
    }
    assert validator._find_exact_private_keys(private) == {
        "attempt_id", "session_id", "asset_key", "response_json", "review_queue",
        "database_path", "auth_state_path", "state_root",
    }


def test_s19_is_local_release_candidate_and_hands_off_to_unapproved_s20() -> None:
    assert s19.RELEASE_CANDIDATE_ID == "A1FS-ONLINE-V1-D0-RC1"
    assert s19.PRODUCT_STATUS == "LOCALHOST_NONAUDIO_LEARNER_PRODUCT_RELEASE_CANDIDATE_READY_NOT_EXTERNAL"
    assert s19.NEXT_SHORT_STEP == "A1FS-ONLINE-V1-S20_CloudflareDeploymentAndExternalAcceptance_NoAudio"

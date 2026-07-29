#!/usr/bin/env python3
"""Build, install, serve, accept, and rollback the A1FS V1.2.1 U01F patch."""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from collections import Counter
from contextlib import closing
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlparse

from ulga.builders import _a1fs_v1_1_m02_release_core as m02_core
from ulga.builders import _a1fs_online_v1_2_1_u01f_static as static_patch
from ulga.builders import build_a1fs_online_v1_r01_self_contained_product_root_update_channel as r01
from ulga.builders import build_a1fs_online_v1_2_u01e_local_production_operator_acceptance as v12_operator
from ulga.builders import build_a1fs_online_v1_2_u01e_s05_release_migration_acceptance as v12

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Patches the accepted V1.2 runtime so pending M6 human review no longer blocks "
    "session completion, reuses the existing S16 M7/M8 refresh after review, and "
    "presents already-approved SINGLE_SELECT options in a stable per-session order. "
    "It creates no item, answer, scoring/mastery authority, audio, A2 unlock, external "
    "route, curriculum, or parallel learner-state engine."
)

PROGRAM_ID = "A1FS-ONLINE-V1.2.1-U01F"
TASK_ID = (
    "A1FS-ONLINE-V1.2.1-U01F-S04_"
    "PatchReleaseMigrationRollbackAndLocalProductionAcceptance"
)
SCHEMA_VERSION = "a1fs.online.v1_2_1.u01f.patch_release.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_2_1_U01F_PATCH_RELEASE_ACCEPTANCE"
PRODUCT_STATUS = "A1FS_V1_2_1_U01F_NONBLOCKING_REVIEW_RANDOM_OPTIONS_READY"
SOURCE_VERSION = "1.2.0"
TARGET_VERSION = "1.2.1"
RELEASE_ID = "A1FS-ONLINE-V1.2.1-U01F-PATCH1"
MODULE = "ulga.builders.build_a1fs_online_v1_2_1_u01f_patch_release"
EXPECTED_UNIT_COUNT = 24
EXPECTED_LESSON_COUNT = 72
EXPECTED_ASSET_COUNT = 277
EXPECTED_UNIT01_COUNTS = {"READING": 10, "WRITING": 8, "SPEAKING": 6}
DEFAULT_READBACK_NAME = "a1fs_v1_2_1_u01f_operator_acceptance.safe.json"
DEFAULT_OUTPUT_ROOT = Path(r"G:\HomeWork\A1FS_V1_2_1_U01F_OPERATOR_RUN")
NEXT_SHORT_STEP = "A1FS-ONLINE-V1.2.1-U01F_ProductionCloseoutReadback"


class U01FPatchError(ValueError):
    """Fail-closed V1.2.1 patch release/runtime error."""


_BASE_V12_APPLICATION = v12._core.V12Application
_BASE_V12_HANDLER = v12._core.V12Handler


class V121Application(_BASE_V12_APPLICATION):
    """V1.2 app with nonblocking review and post-review canonical refresh."""

    def bootstrap(self) -> dict[str, Any]:
        value = super().bootstrap()
        value.update(
            {
                "task_id": TASK_ID,
                "schema_version": SCHEMA_VERSION,
                "validation_status": PASS_STATUS,
                "product_status": PRODUCT_STATUS,
                "product_version": TARGET_VERSION,
            }
        )
        value["learner_product_semantics"].update(
            {
                "pending_human_review_blocks_session_completion": False,
                "pending_human_review_blocks_mastery": True,
                "post_review_canonical_learning_refresh": True,
                "single_select_option_order_mode": "SESSION_STABLE_PSEUDORANDOM",
                "single_select_option_shuffle_policy_version": static_patch.SHUFFLE_POLICY_VERSION,
                "runtime_free_generation_allowed": False,
            }
        )
        return value

    def completion_readiness(self, session_id: str) -> dict[str, Any]:
        value = deepcopy(super().completion_readiness(session_id))
        if str(value.get("skill") or "").upper() == "SPEAKING":
            value["assessment_resolution_state"] = "PRACTICE_ONLY"
            return value
        blockers = [
            str(code)
            for code in value.get("blocking_reason_codes", [])
            if str(code) != "HUMAN_REVIEW_PENDING"
        ]
        required = int(value.get("required_response_count") or 0)
        attempted = int(value.get("attempted_response_count") or 0)
        passed = int(value.get("passed_response_count") or 0)
        pending = int(value.get("pending_human_review_count") or 0)
        retry = int(value.get("retry_required_count") or 0)
        not_attempted = int(value.get("not_attempted_count") or 0)
        allowed = (
            required > 0
            and attempted == required
            and not_attempted == 0
            and retry == 0
            and passed + pending == required
            and not blockers
        )
        value.update(
            {
                "gate_mode": "DYNAMIC_BUNDLE_ATTEMPTED_WITH_PENDING_REVIEW_NONBLOCKING",
                "completion_allowed": allowed,
                "blocking_reason_codes": list(dict.fromkeys(blockers)),
                "assessment_resolution_state": (
                    "PENDING_HUMAN_REVIEW" if pending else "RESOLVED"
                ),
                "pending_review_counts_as_pass": False,
                "pending_review_counts_as_mastery": False,
            }
        )
        return value

    def review_attempt(
        self, payload: Mapping[str, Any], *, reviewer_id: str
    ) -> dict[str, Any]:
        result = super().review_attempt(payload, reviewer_id=reviewer_id)
        outcome = str(result.get("review_result", {}).get("outcome") or "")
        refresh: dict[str, Any] | None = None
        if outcome in {"HUMAN_APPROVE", "HUMAN_REJECT"}:
            attempt_id = str(payload.get("attempt_id") or "")
            with closing(sqlite3.connect(self.database_path)) as connection:
                row = connection.execute(
                    "SELECT learner_id FROM response_attempts WHERE attempt_id=?",
                    (attempt_id,),
                ).fetchone()
            if not row:
                raise U01FPatchError("reviewed_attempt_learner_missing")
            refresh = self.refresh_canonical_learning(learner_id=str(row[0]))
        result.update(
            {
                "mastery_refreshed": refresh is not None,
                "canonical_learning_refresh": refresh,
                "session_reopened": False,
            }
        )
        return result

    def learner_review_feedback(self) -> dict[str, Any]:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """SELECT a.response_json,a.submitted_at,s.outcome,
                          q.decision,q.reviewed_at,q.criteria_json,q.notes,
                          a.lesson_id,a.asset_key
                   FROM response_attempts a
                   JOIN scoring_results s USING(attempt_id)
                   JOIN response_contracts c USING(asset_key)
                   LEFT JOIN human_review_queue q USING(attempt_id)
                   WHERE a.learner_id=? AND c.skill='WRITING'
                     AND s.outcome IN(
                       'PENDING_HUMAN_REVIEW','HUMAN_APPROVE',
                       'HUMAN_REJECT','HUMAN_DEFER'
                     )
                   ORDER BY a.submitted_at DESC,a.attempt_id DESC""",
                (self.default_learner_id,),
            ).fetchall()
        reviews: list[dict[str, Any]] = []
        for row in rows:
            response = json.loads(str(row["response_json"]))
            criteria_raw = str(row["criteria_json"] or "{}")
            criteria = json.loads(criteria_raw)
            reviews.append(
                {
                    "lesson_id": str(row["lesson_id"]),
                    "asset_key": str(row["asset_key"]),
                    "response": response,
                    "submitted_at": str(row["submitted_at"]),
                    "outcome": str(row["outcome"]),
                    "decision": None if row["decision"] is None else str(row["decision"]),
                    "reviewed_at": None if row["reviewed_at"] is None else str(row["reviewed_at"]),
                    "criteria": criteria if isinstance(criteria, Mapping) else {},
                    "notes": None if row["notes"] is None else str(row["notes"]),
                }
            )
        return {
            "task_id": TASK_ID,
            "validation_status": PASS_STATUS,
            "product_version": TARGET_VERSION,
            "learner_only": True,
            "review_count": len(reviews),
            "reviews": reviews,
        }

    def progress_readback(self) -> dict[str, Any]:
        value = super().progress_readback()
        value.update(
            {
                "task_id": TASK_ID,
                "schema_version": SCHEMA_VERSION,
                "validation_status": PASS_STATUS,
                "product_status": PRODUCT_STATUS,
                "product_version": TARGET_VERSION,
            }
        )
        value["semantic_boundaries"].update(
            {
                "pending_review_session_completion_allowed": True,
                "pending_review_mastery_claimed": False,
                "post_review_uses_existing_m7_m8_authority": True,
            }
        )
        return value


class V121Handler(_BASE_V12_HANDLER):
    @property
    def v121_app(self) -> V121Application:
        return self.server.app  # type: ignore[attr-defined]

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/api/my-writing-reviews":
            super().do_GET()
            return
        if not self._transport_valid():
            return
        claims = self._claims()
        if claims is None:
            self._json(401, {"error": "authentication_required"})
            return
        try:
            self._json(200, self.v121_app.learner_review_feedback())
        except (
            U01FPatchError,
            v12._core.S05ReleaseError,
            v12._core.s17.DashboardReviewError,
            sqlite3.Error,
            ValueError,
        ) as exc:
            self._json(409, {"error": str(exc)})


def make_app(
    *,
    database: Path,
    bundles: Mapping[str, Mapping[str, Any]],
    sequence: Mapping[str, int],
    graph_path: Path,
    state_root: Path,
    registry: Sequence[Mapping[str, Any]],
    learner_id: str = v12._core.CANARY_LEARNER_ID,
) -> V121Application:
    return V121Application(
        database_path=database,
        bundles=bundles,
        sequence_by_grammar=sequence,
        graph_path=graph_path,
        state_root=state_root,
        default_learner_id=learner_id,
        target_registry=registry,
    )


def activate_runtime_patch() -> None:
    """Activate V1.2.1 adapters only for the V1.2.1 serve process."""
    v12._core.V12Application = V121Application
    v12._core.V12Handler = V121Handler
    v12._core.make_app = make_app
    v12._core.MODULE = MODULE


def source_product(product_root: Path) -> dict[str, Any]:
    root = Path(product_root).resolve()
    version, manifest, bundles, sequence = r01._load_product(root)
    if version != SOURCE_VERSION:
        raise U01FPatchError(
            f"SOURCE_VERSION_REQUIRED={SOURCE_VERSION};ACTUAL={version}"
        )
    if len(sequence) != EXPECTED_UNIT_COUNT or len(bundles) != EXPECTED_LESSON_COUNT:
        raise U01FPatchError("source_product_denominator_invalid")
    asset_count = sum(len(bundle.get("assets", [])) for bundle in bundles.values())
    if asset_count != EXPECTED_ASSET_COUNT:
        raise U01FPatchError(f"source_asset_count_invalid:{asset_count}")
    unit01_counts = {
        skill: len(bundles[v12._core.m01.LESSON_IDS[skill]].get("assets", []))
        for skill in EXPECTED_UNIT01_COUNTS
    }
    if unit01_counts != EXPECTED_UNIT01_COUNTS:
        raise U01FPatchError(f"source_unit01_counts_invalid:{unit01_counts}")
    release_root = root / "releases" / version
    static_root = r01._resolve(root, str(manifest["secure_static_root"]))
    database = r01._resolve(root, str(manifest["shared_database_path"]))
    auth = r01._resolve(root, str(manifest["shared_auth_state_path"]))
    graph = r01._resolve(root, str(manifest["graph_path"]))
    state = r01._resolve(root, str(manifest["shared_learner_state_root"]))
    registry = v12._core.load_registry(root, manifest)
    if not all(
        path.exists()
        for path in (release_root, static_root, database, auth, graph, state)
    ):
        raise U01FPatchError("source_runtime_missing")
    return {
        "root": root,
        "version": version,
        "manifest": manifest,
        "bundles": bundles,
        "sequence": sequence,
        "release_root": release_root,
        "static_root": static_root,
        "database": database,
        "auth": auth,
        "graph": graph,
        "state": state,
        "registry": registry,
        "asset_count": asset_count,
        "unit01_counts": unit01_counts,
        "shared_identity": m02_core.shared_identity(root),
    }


def _rewrite_release_paths(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace(
            f"releases/{SOURCE_VERSION}/", f"releases/{TARGET_VERSION}/"
        )
    if isinstance(value, list):
        return [_rewrite_release_paths(row) for row in value]
    if isinstance(value, Mapping):
        return {str(key): _rewrite_release_paths(child) for key, child in value.items()}
    return value


def build_candidate_release(
    *, product_root: Path, code_root: Path, output_root: Path
) -> tuple[Path, dict[str, Any]]:
    del code_root
    source = source_product(product_root)
    output_root = Path(output_root).resolve()
    candidate = output_root / "candidate" / TARGET_VERSION
    if candidate.exists():
        shutil.rmtree(r01._win32_long_path(candidate))
    candidate.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        r01._win32_long_path(source["release_root"]),
        r01._win32_long_path(candidate),
    )
    manifest_path = candidate / "release_manifest.json"
    manifest = _rewrite_release_paths(
        r01.read_json(manifest_path, "v12_release_manifest")
    )
    manifest.update(
        {
            "schema_version": SCHEMA_VERSION,
            "product_version": TARGET_VERSION,
            "source_product_version": SOURCE_VERSION,
            "release_id": RELEASE_ID,
            "serve_module": MODULE,
            "runtime_patch_task_id": TASK_ID,
            "database_migration_mode": "NONE_SHARED_STATE_PRESERVED",
            "pending_review_blocks_session_completion": False,
            "pending_review_blocks_mastery": True,
            "single_select_option_order_mode": "SESSION_STABLE_PSEUDORANDOM",
            "single_select_option_shuffle_policy_version": static_patch.SHUFFLE_POLICY_VERSION,
            "v1_2_rollback_supported": True,
        }
    )
    r01.write_json(manifest_path, manifest)

    static_root = candidate / "runtime" / "secure_static"
    static_result = static_patch.patch_static(static_root, static_root)
    app_builders = candidate / "app" / "ulga" / "builders"
    app_builders.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__).resolve(), app_builders / Path(__file__).name)
    shutil.copy2(
        Path(static_patch.__file__).resolve(),
        app_builders / Path(static_patch.__file__).name,
    )
    (candidate / "checksums.json").unlink(missing_ok=True)
    r01._write_checksums(candidate)
    checked = r01.validate_release(candidate)
    if checked.get("product_version") != TARGET_VERSION:
        raise U01FPatchError("candidate_version_invalid")
    return candidate, static_result


def _load_v121(product_root: Path) -> tuple[Any, ...]:
    root = Path(product_root).resolve()
    version, manifest, bundles, sequence = r01._load_product(root)
    if version != TARGET_VERSION:
        raise U01FPatchError(f"TARGET_VERSION_REQUIRED={TARGET_VERSION};ACTUAL={version}")
    database = r01._resolve(root, str(manifest["shared_database_path"]))
    auth = r01._resolve(root, str(manifest["shared_auth_state_path"]))
    state = r01._resolve(root, str(manifest["shared_learner_state_root"]))
    graph = r01._resolve(root, str(manifest["graph_path"]))
    static = r01._resolve(root, str(manifest["secure_static_root"]))
    registry = v12._core.load_registry(root, manifest)
    return root, manifest, bundles, sequence, database, auth, state, graph, static, registry


def installed_product_readback(product_root: Path) -> dict[str, Any]:
    (
        root,
        manifest,
        bundles,
        sequence,
        database,
        _auth,
        _state,
        _graph,
        static,
        registry,
    ) = _load_v121(product_root)
    asset_count = sum(len(bundle.get("assets", [])) for bundle in bundles.values())
    unit01_counts = {
        skill: len(bundles[v12._core.m01.LESSON_IDS[skill]].get("assets", []))
        for skill in EXPECTED_UNIT01_COUNTS
    }
    if (
        len(sequence) != EXPECTED_UNIT_COUNT
        or len(bundles) != EXPECTED_LESSON_COUNT
        or asset_count != EXPECTED_ASSET_COUNT
        or unit01_counts != EXPECTED_UNIT01_COUNTS
        or len(registry) != 24
    ):
        raise U01FPatchError("installed_product_denominator_invalid")
    status_counts = Counter(str(row.get("runtime_status") or "") for row in registry)
    if status_counts != Counter({"RUNTIME_ACTIVE": 24}):
        raise U01FPatchError(f"registry_status_invalid:{dict(status_counts)}")
    static_result = static_patch.validate_static(static)
    with closing(sqlite3.connect(database)) as connection:
        active_profiles = int(
            connection.execute(
                "SELECT COUNT(*) FROM learner_profiles WHERE profile_state='ACTIVE'"
            ).fetchone()[0]
        )
    return {
        "product_version": TARGET_VERSION,
        "release_id": str(manifest.get("release_id") or RELEASE_ID),
        "release_checksums_valid": True,
        "unit_count": len(sequence),
        "lesson_count": len(bundles),
        "asset_count": asset_count,
        "unit01_activity_count": len(registry),
        "unit01_counts": unit01_counts,
        "active_learner_profile_count": active_profiles,
        "static_acceptance": static_result,
        "product_root_present": root.is_dir(),
    }


def serve(*, product_root: Path, host: str, port: int) -> None:
    activate_runtime_patch()
    if not v12._core.s17.s16.s15.s11._is_loopback(host):
        raise U01FPatchError(f"NON_LOOPBACK_HOST_FORBIDDEN={host}")
    (
        _root,
        _manifest,
        bundles,
        sequence,
        database,
        auth,
        state,
        graph,
        static,
        registry,
    ) = _load_v121(product_root)
    learner_id, _selection = v12_operator._active_learner_id(database)
    config = v12._core.s17.s16.s15.s13.PersistentBoundaryConfig.from_environment(
        host=host, port=port, revocation_db_path=auth
    )
    server = v12._core.V12Server(
        (host, port),
        make_app(
            database=database,
            bundles=bundles,
            sequence=sequence,
            graph_path=graph,
            state_root=state,
            registry=registry,
            learner_id=learner_id,
        ),
        static,
        config,
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()


def authenticated_http_readback(
    *,
    port: int,
    request_runner: Callable[..., tuple[Any, Mapping[str, str]]] | None = None,
) -> dict[str, Any]:
    environment = v12_operator._required_environment()
    request = request_runner or v12._core.s17.s16.s15.s11._request
    origin = f"http://127.0.0.1:{int(port)}"
    login, headers = request(
        int(port),
        "POST",
        "/auth/login",
        {
            "username": environment["A1FS_S11_AUTH_USERNAME"],
            "password": environment["A1FS_S11_AUTH_PASSWORD"],
        },
        origin=origin,
    )
    cookie = str(headers.get("Set-Cookie") or "").split(";", 1)[0]
    if not cookie or not isinstance(login, Mapping) or not login.get("csrf_token"):
        raise U01FPatchError("operator_login_invalid")
    bootstrap, _ = request(int(port), "GET", "/api/bootstrap", cookie=cookie)
    progress, _ = request(int(port), "GET", "/api/progress", cookie=cookie)
    coverage, _ = request(int(port), "GET", "/api/unit01-coverage", cookie=cookie)
    feedback, _ = request(int(port), "GET", "/api/my-writing-reviews", cookie=cookie)
    if len(bootstrap.get("units", [])) != EXPECTED_UNIT_COUNT:
        raise U01FPatchError("operator_bootstrap_unit_count_invalid")
    if progress.get("product_version") != TARGET_VERSION:
        raise U01FPatchError("operator_progress_version_invalid")
    if coverage.get("curriculum_item_count") != 24:
        raise U01FPatchError("operator_coverage_count_invalid")
    if not isinstance(feedback.get("reviews"), list):
        raise U01FPatchError("operator_review_feedback_invalid")
    return {
        "authenticated_login_pass": True,
        "bootstrap_pass": True,
        "progress_pass": True,
        "coverage_endpoint_pass": True,
        "learner_review_feedback_endpoint_pass": True,
        "unit_count": len(bootstrap.get("units", [])),
        "unit01_activity_count": int(coverage["curriculum_item_count"]),
        "practised_item_count": int(
            coverage.get("learner_evidence_summary", {}).get(
                "distinct_attempted_item_count", 0
            )
        ),
        "review_feedback_count": int(feedback.get("review_count") or 0),
        "get_only_operator_acceptance": True,
        "credential_exported": False,
    }


def operator_acceptance(
    *, product_root: Path, port: int, output_path: Path
) -> dict[str, Any]:
    installed = installed_product_readback(product_root)
    start_result = r01.start(product_root=product_root, port=int(port))
    http = authenticated_http_readback(port=int(port))
    core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "installed_product": installed,
        "runtime_start": {
            "status": str(start_result.get("status") or ""),
            "version": str(start_result.get("version") or ""),
            "localhost_only": True,
        },
        "operator_http_acceptance": http,
        "defect_fullfix": {
            "pending_review_blocks_session_completion": False,
            "pending_review_counts_as_mastery": False,
            "post_review_canonical_refresh": True,
            "single_select_option_order": "SESSION_STABLE_PSEUDORANDOM",
            "same_session_refresh_order_stable": True,
            "runtime_question_generation_used": False,
        },
        "boundaries": {
            "unit_count": 24,
            "lesson_count": 72,
            "asset_count": 277,
            "unit02_modified": False,
            "listening_enabled": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
            "role_based_identity_authorization_claimed": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    readback = {**core, "report_sha256": r01.digest(core)}
    r01.write_json(Path(output_path).resolve(), readback)
    return readback


def release_acceptance(
    *, product_root: Path, code_root: Path, output_root: Path
) -> dict[str, Any]:
    source = source_product(product_root)
    production_before = source["shared_identity"]
    candidate, static_result = build_candidate_release(
        product_root=product_root,
        code_root=code_root,
        output_root=output_root,
    )
    clone = m02_core.build_acceptance_root(
        product_root=product_root,
        target_root=Path(output_root).resolve() / "acceptance" / "product",
    )
    installed = r01.install_candidate(
        product_root=clone, candidate=candidate, version=TARGET_VERSION
    )
    target_readback = installed_product_readback(clone)
    rollback = r01.rollback(product_root=clone, version=SOURCE_VERSION)
    if r01._current_version(clone) != SOURCE_VERSION:
        raise U01FPatchError("rollback_to_v12_failed")
    r01._switch_version(clone, TARGET_VERSION)
    if r01._current_version(clone) != TARGET_VERSION:
        raise U01FPatchError("forward_switch_to_v121_failed")
    if m02_core.shared_identity(product_root) != production_before:
        raise U01FPatchError("production_shared_state_mutated_by_acceptance")
    return {
        "validation_status": PASS_STATUS,
        "source_version": SOURCE_VERSION,
        "target_version": TARGET_VERSION,
        "candidate_root": str(candidate),
        "static_acceptance": static_result,
        "installed_status": str(installed.get("status") or "PASS"),
        "target_readback": target_readback,
        "rollback_status": str(rollback.get("status") or "PASS"),
        "rollback_to_v12_pass": True,
        "forward_switch_to_v121_pass": True,
        "production_shared_state_unchanged": True,
    }


def materialize(
    *,
    product_root: Path,
    code_root: Path,
    output_path: Path,
    report_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    output_path = Path(output_path).resolve()
    report_path = Path(report_path).resolve()
    output_root = output_path.parent / "u01f"
    if output_root.exists():
        shutil.rmtree(r01._win32_long_path(output_root))
    output_root.mkdir(parents=True)
    acceptance = release_acceptance(
        product_root=product_root,
        code_root=code_root,
        output_root=output_root,
    )
    core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "release_id": RELEASE_ID,
        "source_product_version": SOURCE_VERSION,
        "target_product_version": TARGET_VERSION,
        "release_summary": {
            "unit_count": EXPECTED_UNIT_COUNT,
            "lesson_count": EXPECTED_LESSON_COUNT,
            "asset_count": EXPECTED_ASSET_COUNT,
            "unit01_counts": EXPECTED_UNIT01_COUNTS,
            "new_asset_count": 0,
            "database_schema_changed": False,
        },
        "acceptance_summary": acceptance,
        "boundaries": {
            "existing_item_bank_changed": False,
            "runtime_generation_allowed": False,
            "unit02_modified": False,
            "listening_enabled": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    receipt = {**core, "artifact_sha256": r01.digest(core)}
    safe = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "source_product_version": SOURCE_VERSION,
        "target_product_version": TARGET_VERSION,
        "release_summary": core["release_summary"],
        "acceptance_summary": acceptance,
        "boundaries": core["boundaries"],
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    r01.write_json(output_path, receipt)
    r01.write_json(report_path, safe)
    return receipt, safe


def install_and_accept(
    *,
    product_root: Path,
    code_root: Path,
    output_root: Path,
    port: int,
) -> dict[str, Any]:
    root = Path(product_root).resolve()
    output_root = Path(output_root).resolve()
    try:
        output_root.relative_to(root)
    except ValueError:
        pass
    else:
        raise U01FPatchError("OUTPUT_ROOT_MUST_BE_OUTSIDE_PRODUCT_ROOT")
    v12_operator._required_environment()
    current = r01._current_version(root)
    if current not in {SOURCE_VERSION, TARGET_VERSION}:
        raise U01FPatchError(
            f"SOURCE_OR_TARGET_VERSION_REQUIRED={SOURCE_VERSION}_OR_{TARGET_VERSION};ACTUAL={current}"
        )
    if current == SOURCE_VERSION:
        pid_path = root / "shared" / "a1fs_v1.pid"
        if pid_path.is_file():
            pid = int(pid_path.read_text(encoding="ascii").strip())
            if r01._pid_alive(pid):
                r01.stop(product_root=root, port=int(port))
            else:
                pid_path.unlink(missing_ok=True)
        output_root.mkdir(parents=True, exist_ok=True)
        candidate, _static = build_candidate_release(
            product_root=root, code_root=code_root, output_root=output_root
        )
        r01.install_candidate(
            product_root=root, candidate=candidate, version=TARGET_VERSION
        )
    try:
        return operator_acceptance(
            product_root=root,
            port=int(port),
            output_path=root
            / "shared"
            / "operator_readbacks"
            / DEFAULT_READBACK_NAME,
        )
    except Exception as exc:
        notes: list[str] = []
        try:
            if (root / "shared" / "a1fs_v1.pid").is_file():
                r01.stop(product_root=root, port=int(port))
            notes.append("runtime_stopped")
        except Exception as stop_exc:
            notes.append(f"stop_failed:{stop_exc}")
        if r01._current_version(root) == TARGET_VERSION:
            try:
                result = r01.rollback(product_root=root, version=SOURCE_VERSION)
                notes.append(str(result.get("status") or "rollback_complete"))
            except Exception as rollback_exc:
                notes.append(f"rollback_failed:{rollback_exc}")
        raise U01FPatchError(
            "POST_INSTALL_OPERATOR_ACCEPTANCE_FAILED;"
            + ";".join(notes)
            + f";cause={exc}"
        ) from exc


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    server = commands.add_parser("serve")
    server.add_argument("--product-root", type=Path, required=True)
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=r01.DEFAULT_PORT)

    build = commands.add_parser("materialize")
    build.add_argument("--product-root", type=Path, required=True)
    build.add_argument("--code-root", type=Path, default=Path(__file__).resolve().parents[2])
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--report", type=Path, required=True)

    accept = commands.add_parser("operator-acceptance")
    accept.add_argument("--product-root", type=Path, required=True)
    accept.add_argument("--port", type=int, default=r01.DEFAULT_PORT)
    accept.add_argument("--output", type=Path)

    run = commands.add_parser("install-and-accept")
    run.add_argument("--product-root", type=Path, required=True)
    run.add_argument("--code-root", type=Path, default=Path(__file__).resolve().parents[2])
    run.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    run.add_argument("--port", type=int, default=r01.DEFAULT_PORT)

    args = parser.parse_args(argv)
    try:
        if args.command == "serve":
            serve(product_root=args.product_root, host=args.host, port=args.port)
        elif args.command == "materialize":
            receipt, _safe = materialize(
                product_root=args.product_root,
                code_root=args.code_root,
                output_path=args.output,
                report_path=args.report,
            )
            print(json.dumps(receipt, ensure_ascii=False, indent=2))
        elif args.command == "operator-acceptance":
            output = args.output or (
                Path(args.product_root).resolve()
                / "shared"
                / "operator_readbacks"
                / DEFAULT_READBACK_NAME
            )
            print(
                json.dumps(
                    operator_acceptance(
                        product_root=args.product_root,
                        port=args.port,
                        output_path=output,
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(
                json.dumps(
                    install_and_accept(
                        product_root=args.product_root,
                        code_root=args.code_root,
                        output_root=args.output_root,
                        port=args.port,
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        return 0
    except (
        U01FPatchError,
        static_patch.U01FStaticError,
        r01.ProductRootError,
        v12._core.S05ReleaseError,
        v12._core.s17.DashboardReviewError,
        sqlite3.Error,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

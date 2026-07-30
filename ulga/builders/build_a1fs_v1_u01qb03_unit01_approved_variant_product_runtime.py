#!/usr/bin/env python3
"""Final product runtime adapter for U01QB03.

This layer preserves the existing V1.2.1 authenticated API routes. It appends a
small client-side override to the existing product app.js so start/resume render
the dynamic ten-item assets returned by the existing endpoints, and it makes a
repeat exposure for the same session/item idempotent so the existing retry UI
can submit a new M6 attempt without duplicating exposure evidence.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from copy import deepcopy
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from ulga.builders import (
    build_a1fs_v1_u01qb03_unit01_approved_variant_product_surface as surface,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Extends the existing authenticated V1.2.1 product handler only to serve the existing app.js plus a Unit01 dynamic-session client override, and makes repeated exposure idempotent for retry. It creates no new API route, content, UI authority, planner, learner database, scoring engine, mastery, audio, A2 content, or Unit02-Unit24 content."
PROGRAM_ID = surface.PROGRAM_ID
TASK_ID = surface.TASK_ID
SCHEMA_VERSION = surface.SCHEMA_VERSION
PASS_STATUS = surface.PASS_STATUS
NEXT_SHORT_STEP = surface.NEXT_SHORT_STEP

CLIENT_PATCH = r"""
/* U01QB03 dynamic approved-variant session adapter. */
begin=async function(lane){
  if(locked())throw new Error('請先繼續或放棄目前的本次學習');
  active=await api('/api/session/start',{lesson_id:lane.lesson_id});
  pendingResume=null;updateActivePanel();complete.hidden=false;complete.disabled=true;
  const sessionLane=active.dynamic_item_session?{...lane,assets:active.assets,asset_count:active.item_count}:lane;
  currentLane=sessionLane;renderLane(sessionLane);
  text(status,`本次學習開始：${currentUnit.learner_label}／${lane.learner_label}`);
  await loadProgress();
};
restore=function(snapshot){
  const match=findLane(snapshot.session.lesson_id);if(!match)throw new Error('active_session_bundle_missing');
  pendingResume=null;active=snapshot.session;currentUnit=match.unit;
  const sessionLane=snapshot.dynamic_item_session?{...match.lane,assets:snapshot.assets,asset_count:snapshot.item_count}:match.lane;
  currentLane=sessionLane;updateActivePanel();complete.hidden=false;complete.disabled=true;renderLane(sessionLane);
  text(status,`繼續本次學習：${match.unit.learner_label}／${match.lane.learner_label}`);
};
""".strip()


class Unit01VariantProductApplication(surface.Unit01VariantProductApplication):
    """Product surface with idempotent retry exposure."""

    def record_exposure(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        asset_key = str(payload.get("asset_key") or "")
        session_id = str(payload.get("session_id") or "")
        expected_version = int(payload["expected_session_version"])
        with closing(surface._connect(self.database_path)) as connection:
            item = connection.execute(
                "SELECT item_id FROM u01qb02_item_catalog WHERE asset_key=?",
                (asset_key,),
            ).fetchone()
            existing = None
            if item:
                existing = connection.execute(
                    """SELECT exposure_id,selection_reason FROM u01qb02_item_exposures
                    WHERE session_id=? AND item_id=?""",
                    (session_id, str(item["item_id"])),
                ).fetchone()
                session = connection.execute(
                    """SELECT learner_id,lesson_id,skill,level,session_state,session_version,
                    exposure_count,attempt_count,started_at,updated_at,outcome
                    FROM learning_sessions WHERE session_id=?""",
                    (session_id,),
                ).fetchone()
            else:
                session = None
        if not item or not existing:
            return super().record_exposure(payload)
        if session is None or session["session_state"] != "ACTIVE":
            raise surface.ProductSurfaceError("session_not_active")
        if int(session["session_version"]) != expected_version:
            raise surface.ProductSurfaceError(
                f"session_version_conflict:{session['session_version']}"
            )
        return {
            "validation_status": PASS_STATUS,
            "session_id": session_id,
            "item_id": str(item["item_id"]),
            "asset_key": asset_key,
            "selection_reason": str(existing["selection_reason"]),
            "exposure_id": str(existing["exposure_id"]),
            "session_version": int(session["session_version"]),
            "m3_exposure_recorded": True,
            "exposure_already_recorded": True,
            "dynamic_item_session": True,
            "mastery_claimed": False,
            "u01qb03_task_id": TASK_ID,
        }


def client_javascript(static_root: Path) -> bytes:
    base = (Path(static_root) / "app.js").read_text(encoding="utf-8")
    if "U01QB03 dynamic approved-variant session adapter" in base:
        raise surface.ProductSurfaceError("client_patch_already_present")
    return (base.rstrip() + "\n\n" + CLIENT_PATCH + "\n").encode("utf-8")


class Unit01VariantProductHandler(surface.product_core.V12Handler):
    @property
    def unit01_app(self) -> Unit01VariantProductApplication:
        return self.server.app  # type: ignore[attr-defined]

    def do_GET(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/app.js":
            super().do_GET()
            return
        if not self._transport_valid():
            return
        claims = self._claims()
        if claims is None:
            self._json(401, {"error": "authentication_required"})
            return
        raw = client_javascript(self.server.secure_static_root)  # type: ignore[attr-defined]
        self.send_response(200)
        self._send_headers(
            content_type="application/javascript; charset=utf-8",
            content_length=len(raw),
        )
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)


class Unit01VariantProductServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], app: Unit01VariantProductApplication, static_root: Path, config: Any):
        if not surface.product_core.s17.s16.s15.s11._is_loopback(address[0]):
            raise surface.ProductSurfaceError(f"non_loopback_host_forbidden:{address[0]}")
        self.app = app
        self.static_root = Path(static_root)
        self.secure_static_root = Path(static_root)
        self.config = config
        super().__init__(address, Unit01VariantProductHandler)
        self.config.bind_local_port(int(self.server_address[1]))


def make_app(
    *,
    database: Path,
    bundles: Mapping[str, Mapping[str, Any]],
    sequence: Mapping[str, int],
    graph_path: Path,
    state_root: Path,
    registry: Sequence[Mapping[str, Any]],
    learner_id: str,
) -> Unit01VariantProductApplication:
    return Unit01VariantProductApplication(
        database_path=database,
        bundles=bundles,
        sequence_by_grammar=sequence,
        graph_path=graph_path,
        state_root=state_root,
        default_learner_id=learner_id,
        target_registry=registry,
    )

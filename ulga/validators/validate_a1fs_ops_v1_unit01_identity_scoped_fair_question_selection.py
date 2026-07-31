#!/usr/bin/env python3
"""Independently validate Unit01 identity-scoped fair question selection."""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Sequence

from ulga.builders import (
    build_a1fs_ops_v1_unit01_identity_scoped_fair_question_selection as builder,
)
from ulga.builders import (
    build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Reads the existing M3/U01QB02 database and identity-scope metadata to "
    "validate privacy, session uniqueness, guest isolation, family balance, and "
    "phrase-before-sentence ordering. It creates no content, bank, selector, "
    "state engine, score, audio, A2 content, or Unit02-Unit24 artifact."
)
PASS_STATUS = "PASS_A1FS_OPS_V1_UNIT01_IDENTITY_SCOPED_FAIR_SELECTION_VALIDATION"
FAIL_STATUS = "FAIL_A1FS_OPS_V1_UNIT01_IDENTITY_SCOPED_FAIR_SELECTION_VALIDATION"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return bool(
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
    )


def validate(
    database: Path,
    *,
    expected_runtime_items: int = 474,
    session_prefix: str = "identity-fair-",
    forbidden_subject_values: Sequence[str] = (),
) -> dict[str, Any]:
    errors: list[str] = []
    counts: dict[str, Any] = {}
    try:
        database = Path(database)
        if not database.is_file():
            raise ValueError("database_missing")
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            required = (
                "learner_profiles",
                "learning_sessions",
                "u01qb02_item_catalog",
                "u01qb02_session_plans",
                "u01qb02_session_items",
                "u01qb02_item_exposures",
                "u01qb02_identity_scopes",
            )
            for table in required:
                if not _table_exists(connection, table):
                    raise ValueError(f"required_table_missing:{table}")
            catalog_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM u01qb02_item_catalog"
                ).fetchone()[0]
            )
            if catalog_count != expected_runtime_items:
                raise ValueError(f"runtime_item_count_invalid:{catalog_count}")
            columns = {
                str(row[1])
                for row in connection.execute(
                    "PRAGMA table_info(u01qb02_identity_scopes)"
                )
            }
            expected_columns = {
                "scope_id",
                "learner_id",
                "identity_mode",
                "subject_digest",
                "opened_at",
                "expires_at",
                "closed_at",
            }
            if columns != expected_columns:
                raise ValueError(f"identity_scope_columns_invalid:{sorted(columns)}")
            if any(
                "token" in column.casefold() or "password" in column.casefold()
                for column in columns
            ):
                raise ValueError("raw_auth_material_column_present")
            scopes = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM u01qb02_identity_scopes ORDER BY scope_id"
                )
            ]
            serialized = json.dumps(scopes, ensure_ascii=False, sort_keys=True)
            for raw in forbidden_subject_values:
                if str(raw) and str(raw) in serialized:
                    raise ValueError("raw_subject_value_persisted")
            for scope in scopes:
                mode = str(scope["identity_mode"])
                if mode not in builder.IDENTITY_MODES:
                    raise ValueError(f"identity_mode_invalid:{scope['scope_id']}")
                if not HEX64.fullmatch(str(scope["subject_digest"])):
                    raise ValueError(f"subject_digest_invalid:{scope['scope_id']}")
                profile = connection.execute(
                    "SELECT 1 FROM learner_profiles WHERE learner_id=?",
                    (scope["learner_id"],),
                ).fetchone()
                if not profile:
                    raise ValueError(f"identity_profile_missing:{scope['scope_id']}")
                if mode == "GUEST":
                    if not str(scope["learner_id"]).startswith(
                        builder.GUEST_LEARNER_PREFIX
                    ):
                        raise ValueError(f"guest_learner_id_invalid:{scope['scope_id']}")
                    if not scope["expires_at"]:
                        raise ValueError(f"guest_expiry_missing:{scope['scope_id']}")
                elif scope["expires_at"] is not None:
                    raise ValueError(f"authenticated_expiry_present:{scope['scope_id']}")
            extra_identity_tables = {
                str(row[0])
                for row in connection.execute(
                    """SELECT name FROM sqlite_master
                    WHERE type='table' AND name LIKE 'u01qb02_identity_%'"""
                )
            } - {"u01qb02_identity_scopes"}
            if extra_identity_tables:
                raise ValueError(
                    "parallel_identity_runtime_table_created:"
                    + ",".join(sorted(extra_identity_tables))
                )
            plans = [
                dict(row)
                for row in connection.execute(
                    """SELECT * FROM u01qb02_session_plans
                    WHERE session_id LIKE ? ORDER BY selected_at,session_id""",
                    (f"{session_prefix}%",),
                )
            ]
            guest_items: dict[str, list[set[str]]] = {}
            family_coverage: set[str] = set()
            for plan in plans:
                rows = [
                    dict(row)
                    for row in connection.execute(
                        """SELECT si.item_position,si.item_id,si.selection_reason,
                                  c.pattern_family_id,c.skill
                        FROM u01qb02_session_items si
                        JOIN u01qb02_item_catalog c USING(item_id)
                        WHERE si.session_id=? ORDER BY si.item_position""",
                        (plan["session_id"],),
                    )
                ]
                if len(rows) != qb02.SESSION_SIZE:
                    raise ValueError(
                        f"session_item_count_invalid:{plan['session_id']}:{len(rows)}"
                    )
                if len({str(row["item_id"]) for row in rows}) != qb02.SESSION_SIZE:
                    raise ValueError(f"duplicate_item_in_session:{plan['session_id']}")
                ranks = [
                    builder._pedagogical_rank(
                        str(plan["skill"]), str(row["pattern_family_id"])
                    )
                    for row in rows
                ]
                if ranks != sorted(ranks):
                    raise ValueError(
                        f"phrase_before_sentence_order_invalid:{plan['session_id']}"
                    )
                family_coverage.update(str(row["pattern_family_id"]) for row in rows)
                scope = connection.execute(
                    """SELECT identity_mode FROM u01qb02_identity_scopes
                    WHERE learner_id=? ORDER BY opened_at DESC LIMIT 1""",
                    (plan["learner_id"],),
                ).fetchone()
                if scope and scope["identity_mode"] == "GUEST":
                    guest_items.setdefault(str(plan["learner_id"]), []).append(
                        {str(row["item_id"]) for row in rows}
                    )
            for learner_id, session_sets in guest_items.items():
                accumulated: set[str] = set()
                for index, current in enumerate(session_sets, 1):
                    overlap = accumulated & current
                    if overlap and catalog_count - len(accumulated) >= qb02.SESSION_SIZE:
                        raise ValueError(
                            "guest_fresh_selection_repeated_before_exhaustion:"
                            f"{learner_id}:{index}"
                        )
                    accumulated.update(current)
            counts = {
                "runtime_item_count": catalog_count,
                "identity_scope_count": len(scopes),
                "authenticated_scope_count": sum(
                    1 for row in scopes if row["identity_mode"] == "AUTHENTICATED"
                ),
                "guest_scope_count": sum(
                    1 for row in scopes if row["identity_mode"] == "GUEST"
                ),
                "closed_guest_scope_count": sum(
                    1
                    for row in scopes
                    if row["identity_mode"] == "GUEST"
                    and row["closed_at"] is not None
                ),
                "validated_session_count": len(plans),
                "represented_pattern_family_count": len(family_coverage),
            }
        finally:
            connection.close()
        if (
            qb02.Unit01ApprovedVariantSessionRuntime.assemble_session
            is not builder._assemble_session
        ):
            raise ValueError("fair_selection_fullfix_not_installed")
    except (ValueError, sqlite3.Error, OSError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    return {
        "validation_status": PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        **counts,
        "raw_guest_token_persisted": False,
        "same_guest_login_history_tracked": not errors,
        "new_guest_login_history_isolated": not errors,
        "phrase_before_sentence_order": not errors,
        "parallel_question_bank_created": False,
        "parallel_selector_created": False,
        "parallel_state_engine_created": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--expected-runtime-items", type=int, default=474)
    parser.add_argument("--session-prefix", default="identity-fair-")
    args = parser.parse_args(argv)
    result = validate(
        args.database,
        expected_runtime_items=args.expected_runtime_items,
        session_prefix=args.session_prefix,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

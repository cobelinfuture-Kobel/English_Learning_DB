#!/usr/bin/env python3
"""Run Unit01 R2R2 sentence-pool reconciliation through fresh R4/PDF acceptance.

This product wrapper is the only R2R2 operator entrypoint. It never mutates the
frozen source database: the capacity reconciler first creates a disposable SQLite
clone, replaces the 48 PF13/PF14/PF15 production slots from admitted U01SA05R2
sentence assets, and then delegates to the existing R2R1 fresh R4/PDF pipeline.
"""
from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from product.a1fs_v1_2_1 import (
    u01qb18h_r2r1_unit01_systemic_learner_facing_fullfix as r2r1,
)
from ulga.builders import (
    build_a1fs_v1_u01qb18h_r2r2_unit01_sentence_pool_driven_production_capacity_reconciliation
    as capacity,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Operator orchestration over the policy-bound R2R2 sentence-pool producer and "
    "the existing R2R1 fresh R4/PDF acceptance path. It authors no independent "
    "content, scoring authority, learner state, Unit02-24 content, or A2 content."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = (
    "A1FS-V1-U01QB18H-R2R2_"
    "Unit01SentencePoolDrivenFull240Closeout"
)
PASS_STATUS = (
    "PASS_A1FS_V1_U01QB18H_R2R2_"
    "UNIT01_SENTENCE_POOL_DRIVEN_FULL240_CLOSEOUT"
)
NEXT_SHORT_STEP = (
    "A1FS-V1-U01QB18H-R2R2_"
    "ActualTwelveFormPdfHumanVisualPedagogicalReacceptance"
)
DEFAULT_LEARNER_ID = "U01QB18H_R2R2_ACTUAL_TWELVE_FORM_REACCEPTANCE"


class R2R2Full240CloseoutError(ValueError):
    pass


@contextmanager
def r2r2_candidate_compatibility_hooks() -> Iterator[None]:
    """Install only the compatibility needed by sentence-derived R2R2 items.

    R2R1 historically carried an old PF13 alias in the ERROR_CHECK family map.
    R2R2 uses the canonical U01QB10 PF13 identity. New R2R2 items also carry an
    exact ``production_scene_ref_id`` and must never leak to another micro-scene
    that happens to share the same language pattern projection.
    """
    previous_guard = r2r1.candidate_guard
    previous_error_families = set(r2r1._ANGLE_FAMILIES.get("ERROR_CHECK", set()))

    def guard(
        item: Mapping[str, Any],
        *,
        task_angle: str,
        scene_ref_id: str = "",
        situation_family: str = "",
    ) -> bool:
        production_scene = str(item.get("production_scene_ref_id") or "")
        actual_scene = str(scene_ref_id or "")
        if production_scene and production_scene != actual_scene:
            return False
        return previous_guard(
            item,
            task_angle=task_angle,
            scene_ref_id=actual_scene,
            situation_family=situation_family,
        )

    r2r1.candidate_guard = guard
    r2r1._ANGLE_FAMILIES.setdefault("ERROR_CHECK", set()).add(capacity.u10.PF13)
    try:
        yield
    finally:
        r2r1.candidate_guard = previous_guard
        r2r1._ANGLE_FAMILIES["ERROR_CHECK"] = previous_error_families


def _fresh_output_root(path: Path) -> Path:
    path = Path(path).resolve()
    if path.exists():
        if any(path.iterdir()):
            raise R2R2Full240CloseoutError(f"OUTPUT_ROOT_NOT_EMPTY:{path}")
    else:
        path.mkdir(parents=True, exist_ok=False)
    return path


def _stamp_r2r2_manifest(
    *,
    pdf_root: Path,
    reconciliation: Mapping[str, Any],
) -> dict[str, Any]:
    path = Path(pdf_root) / r2r1.presentation.r1b.base.MANIFEST_NAME
    if not path.is_file():
        raise R2R2Full240CloseoutError(f"PDF_MANIFEST_MISSING:{path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise R2R2Full240CloseoutError("PDF_MANIFEST_OBJECT_REQUIRED")
    migration = reconciliation.get("runtime_migration") or {}
    manifest.update(
        {
            "latest_fullfix_task_id": TASK_ID,
            "latest_fullfix_validation_status": PASS_STATUS,
            "r2r2_capacity_task_id": capacity.TASK_ID,
            "r2r2_approved_artifact_sha256": reconciliation.get(
                "approved_artifact_sha256"
            ),
            "sentence_pool_capability_index_sha256": reconciliation.get(
                "sentence_pool_capability_index_sha256"
            ),
            "r2r2_runtime_item_count": migration.get("runtime_item_count"),
            "r2r2_source_database_mutated": migration.get(
                "source_database_mutated"
            ),
            "next_short_step": NEXT_SHORT_STEP,
        }
    )
    r2r1.presentation.r1b.base._atomic_json(path, manifest)
    return manifest


def _zip_acceptance(root: Path, zip_path: Path) -> None:
    root = Path(root).resolve()
    zip_path = Path(zip_path).resolve()
    if zip_path.exists():
        raise R2R2Full240CloseoutError(f"ACCEPTANCE_ZIP_ALREADY_EXISTS:{zip_path}")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.resolve() == zip_path:
                continue
            archive.write(path, path.relative_to(root))


def materialize_full240_closeout(
    *,
    source_database: Path,
    sentence_pool_capability_index: Path,
    output_root: Path,
    chromium_path: Path | None = None,
    learner_id: str = DEFAULT_LEARNER_ID,
) -> dict[str, Any]:
    output_root = _fresh_output_root(output_root)
    r2r2_root = output_root / "r2r2_capacity_reconciliation"
    r2r2_root.mkdir(parents=True, exist_ok=False)
    disposable_database = r2r2_root / "disposable_learner_runtime.sqlite3"
    candidate_path = r2r2_root / "sentence_pool_capacity.candidate.private.json"
    approved_path = r2r2_root / "sentence_pool_capacity.approved.private.json"
    capacity_report_path = r2r2_root / "sentence_pool_capacity_reconciliation.private.json"
    r4_report_path = output_root / "unit01_forms01_12_full_semantic_language_replay.json"
    pdf_root = output_root / "pdf_acceptance"

    reconciliation = capacity.materialize(
        source_database=Path(source_database),
        disposable_database=disposable_database,
        sentence_pool_capability_index=Path(sentence_pool_capability_index),
        candidate_path=candidate_path,
        approved_path=approved_path,
        report_path=capacity_report_path,
    )
    migration = reconciliation.get("runtime_migration") or {}
    if migration.get("source_database_mutated") is not False:
        raise R2R2Full240CloseoutError("SOURCE_DATABASE_MUTATION_GUARD_FAILED")
    if int(migration.get("runtime_item_count") or 0) != capacity.EXPECTED_RUNTIME_COUNT:
        raise R2R2Full240CloseoutError("R2R2_RUNTIME_DENOMINATOR_INVALID")

    with r2r2_candidate_compatibility_hooks():
        acceptance = r2r1.materialize_twelve_form_pdfs(
            database=disposable_database,
            replay_learner_id=str(learner_id),
            r4_report_path=r4_report_path,
            output_root=pdf_root,
            chromium_path=chromium_path,
        )

    if acceptance.get("actual_r4_replay_executed") is not True:
        raise R2R2Full240CloseoutError("R4_REPLAY_NOT_EXECUTED")
    if (
        str(acceptance.get("actual_r4_replay_validation_status") or "")
        != r2r1.r4.PASS_STATUS
    ):
        raise R2R2Full240CloseoutError(
            "R4_REPLAY_NOT_PASS:"
            f"{acceptance.get('actual_r4_replay_validation_status')}"
        )
    if int(acceptance.get("actual_r4_replay_form_count") or 0) != 12:
        raise R2R2Full240CloseoutError("R4_FORM_COUNT_INVALID")
    if int(acceptance.get("actual_r4_replay_activity_count") or 0) != 240:
        raise R2R2Full240CloseoutError("R4_ACTIVITY_COUNT_INVALID")
    if int(acceptance.get("form_count") or 0) != 12:
        raise R2R2Full240CloseoutError("PDF_FORM_COUNT_INVALID")
    if int(acceptance.get("materialized_pdf_count") or 0) != 12:
        raise R2R2Full240CloseoutError("PDF_FILE_COUNT_INVALID")
    if int(acceptance.get("machine_preflight_pass_count") or 0) != 12:
        raise R2R2Full240CloseoutError("PDF_MACHINE_PREFLIGHT_INVALID")

    manifest = _stamp_r2r2_manifest(
        pdf_root=pdf_root,
        reconciliation=reconciliation,
    )
    zip_path = output_root / "pr519_r2r2_fresh_r4_acceptance.zip"
    _zip_acceptance(output_root, zip_path)
    return {
        "validation_status": PASS_STATUS,
        "source_database": str(Path(source_database).resolve()),
        "source_database_mutated": False,
        "disposable_database": str(disposable_database.resolve()),
        "sentence_pool_capability_index": str(
            Path(sentence_pool_capability_index).resolve()
        ),
        "capacity_reconciliation": reconciliation,
        "r4_report": str(r4_report_path.resolve()),
        "pdf_root": str(pdf_root.resolve()),
        "acceptance_zip": str(zip_path.resolve()),
        "manifest": manifest,
        "actual_r4_replay_validation_status": acceptance.get(
            "actual_r4_replay_validation_status"
        ),
        "actual_r4_replay_form_count": acceptance.get(
            "actual_r4_replay_form_count"
        ),
        "actual_r4_replay_activity_count": acceptance.get(
            "actual_r4_replay_activity_count"
        ),
        "form_count": acceptance.get("form_count"),
        "materialized_pdf_count": acceptance.get("materialized_pdf_count"),
        "machine_preflight_pass_count": acceptance.get(
            "machine_preflight_pass_count"
        ),
        "next_short_step": NEXT_SHORT_STEP,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument(
        "--sentence-pool-capability-index",
        type=Path,
        required=True,
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--chromium-path", type=Path)
    parser.add_argument("--learner-id", default=DEFAULT_LEARNER_ID)
    args = parser.parse_args(argv)
    try:
        value = materialize_full240_closeout(
            source_database=args.database,
            sentence_pool_capability_index=args.sentence_pool_capability_index,
            output_root=args.output_root,
            chromium_path=args.chromium_path,
            learner_id=str(args.learner_id),
        )
    except Exception as exc:
        print(f"STATUS=FAIL_{TASK_ID}")
        print(f"ERROR={exc}")
        return 1
    reconciliation = value["capacity_reconciliation"]
    migration = reconciliation["runtime_migration"]
    print(f"STATUS={PASS_STATUS}")
    print(f"SOURCE_DATABASE_MUTATED={value['source_database_mutated']}")
    print(f"PRODUCTION_REQUIREMENTS={reconciliation['production_requirement_count']}")
    print(f"MATERIALIZED_ITEMS={reconciliation['materialized_item_count']}")
    print(f"BASE_ITEMS={migration['base_item_count']}")
    print(f"REAL62_EXTENSION_ITEMS={migration['extension_item_count']}")
    print(f"RUNTIME_ITEMS={migration['runtime_item_count']}")
    print(f"R4_REPLAY_STATUS={value['actual_r4_replay_validation_status']}")
    print(f"R4_REPLAY_FORMS={value['actual_r4_replay_form_count']}")
    print(f"R4_REPLAY_ACTIVITIES={value['actual_r4_replay_activity_count']}")
    print(f"PDF_FILES={value['materialized_pdf_count']}")
    print(f"MACHINE_PREFLIGHT_PASS={value['machine_preflight_pass_count']}")
    print(f"ACCEPTANCE_ZIP={value['acceptance_zip']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

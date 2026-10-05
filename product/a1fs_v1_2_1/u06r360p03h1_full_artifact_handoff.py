#!/usr/bin/env python3
"""Unit06 Reader360 R2 full Current360 + Spoken360 JSON/PDF handoff validation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TASK_ID = "A1FS-V1-U06R360P03H2_FullArtifactHandoffAfterDensityRewrite"
STATUS = "PASS_A1FS_V1_U06R360P03H2_FULL_ARTIFACT_HANDOFF_R2"
NEXT_SHORT_STEP = "A1FS-V1-U06R360P04_Pattern360GPT56SentenceFamilyMaterialization"

REPO_ROOT = Path(__file__).resolve().parents[2]
CURRENT_JSON = REPO_ROOT / "product/a1fs_v1_2_1/data/unit06_current360_360.json"
SPOKEN_JSON = REPO_ROOT / "product/a1fs_v1_2_1/data/unit06_spoken360_360.json"
CURRENT_PDF = REPO_ROOT / "product/a1fs_v1_2_1/pdf/unit06/unit06_current360_cards_60p.pdf"
SPOKEN_PDF = REPO_ROOT / "product/a1fs_v1_2_1/pdf/unit06/unit06_spoken360_cards_60p.pdf"

CURRENT_SHARDS = tuple(
    REPO_ROOT / f"product/a1fs_v1_2_1/data/u06r360p02_current360_gpt56_e{start:03d}_e{start+59:03d}.json"
    for start in (1, 61, 121, 181, 241, 301)
)
SPOKEN_SHARDS = tuple(
    REPO_ROOT / f"product/a1fs_v1_2_1/data/u06r360p03_spoken360_gpt56_e{start:03d}_e{start+59:03d}.json"
    for start in (1, 61, 121, 181, 241, 301)
)


class U06FullArtifactHandoffError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise U06FullArtifactHandoffError(f"MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise U06FullArtifactHandoffError(f"NOT_OBJECT:{path}")
    return value


def _validate_pdf(path: Path, expected_pages: int, first_id: str, last_id: str) -> int:
    if not path.is_file():
        raise U06FullArtifactHandoffError(f"PDF_MISSING:{path}")
    data = path.read_bytes()
    if not data.startswith(b"%PDF-"):
        raise U06FullArtifactHandoffError(f"PDF_HEADER_INVALID:{path}")
    page_count = data.count(b"/Type /Page /Parent")
    if page_count != expected_pages:
        raise U06FullArtifactHandoffError(
            f"PDF_PAGE_COUNT_DRIFT:{path.name}:{page_count}:{expected_pages}"
        )
    if f"/Count {expected_pages}".encode("ascii") not in data:
        raise U06FullArtifactHandoffError(f"PDF_COUNT_OBJECT_DRIFT:{path.name}")
    if first_id.encode("ascii") not in data or last_id.encode("ascii") not in data:
        raise U06FullArtifactHandoffError(f"PDF_ID_RANGE_DRIFT:{path.name}")
    if data.count(b"Target: ") != 360:
        raise U06FullArtifactHandoffError(f"PDF_CARD_COUNT_DRIFT:{path.name}")
    return len(data)


def build_report() -> dict[str, Any]:
    current = _load(CURRENT_JSON)
    spoken = _load(SPOKEN_JSON)
    if current.get("task_id") != "A1FS-V1-U06R360P02R2_Current360SixToEightSentenceKETFlyersSeededRewrite":
        raise U06FullArtifactHandoffError("CURRENT_CONSOLIDATED_REVISION_DRIFT")
    if spoken.get("task_id") != "A1FS-V1-U06R360P03R2_Spoken360SixToEightTurnKETFlyersSeededRewrite":
        raise U06FullArtifactHandoffError("SPOKEN_CONSOLIDATED_REVISION_DRIFT")

    current_rows = list(current.get("episodes") or [])
    spoken_rows = list(spoken.get("entries") or [])
    if len(current_rows) != 360 or len(spoken_rows) != 360:
        raise U06FullArtifactHandoffError(
            f"CONSOLIDATED_COUNT_DRIFT:{len(current_rows)}:{len(spoken_rows)}"
        )

    source_current = [
        row for path in CURRENT_SHARDS for row in (_load(path).get("episodes") or [])
    ]
    source_spoken = [
        row for path in SPOKEN_SHARDS for row in (_load(path).get("entries") or [])
    ]
    if current_rows != source_current:
        raise U06FullArtifactHandoffError("CURRENT_CONSOLIDATED_NOT_EXACT_SOURCE_JOIN")
    if spoken_rows != source_spoken:
        raise U06FullArtifactHandoffError("SPOKEN_CONSOLIDATED_NOT_EXACT_SOURCE_JOIN")

    current_pdf_bytes = _validate_pdf(
        CURRENT_PDF, 60, "U06-NEB-E001", "U06-NEB-E360"
    )
    spoken_pdf_bytes = _validate_pdf(
        SPOKEN_PDF, 60, "U06-SPOKEN360-E001", "U06-SPOKEN360-E360"
    )

    return {
        "schema_version": "a1fs.v1.u06.r360.full_artifact_handoff.v2",
        "task_id": TASK_ID,
        "status": STATUS,
        "current360": {
            "json_path": str(CURRENT_JSON.relative_to(REPO_ROOT)).replace("\\", "/"),
            "episode_count": 360,
            "sentence_range": "6_TO_8",
            "pdf_path": str(CURRENT_PDF.relative_to(REPO_ROOT)).replace("\\", "/"),
            "pdf_page_count": 60,
            "cards_per_page": 6,
            "pdf_bytes": current_pdf_bytes,
        },
        "spoken360": {
            "json_path": str(SPOKEN_JSON.relative_to(REPO_ROOT)).replace("\\", "/"),
            "entry_count": 360,
            "turn_range": "6_TO_8",
            "pdf_path": str(SPOKEN_PDF.relative_to(REPO_ROOT)).replace("\\", "/"),
            "pdf_page_count": 60,
            "cards_per_page": 6,
            "pdf_bytes": spoken_pdf_bytes,
        },
        "source_join_exact": True,
        "learner_facing_language_author": "GPT-5.6 Sol",
        "scope_safety": {
            "current360_rewritten_by_gpt56": True,
            "spoken360_rewritten_by_gpt56": True,
            "current360_rewritten_by_python": False,
            "spoken360_rewritten_by_python": False,
            "pattern360_materialized": False,
            "a2_a2plus_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    r = build_report()
    print(f"STATUS={r['status']}")
    print(f"CURRENT360={r['current360']['episode_count']} / {r['current360']['pdf_page_count']}p")
    print(f"SPOKEN360={r['spoken360']['entry_count']} / {r['spoken360']['pdf_page_count']}p")
    print(f"NEXT_SHORT_STEP={r['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

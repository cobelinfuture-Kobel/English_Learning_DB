from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ulga.builders import build_a1_a1plus_reading_private_revision_evidence as base
from ulga.builders import (
    rebuild_a1_a1plus_reading_private_revision_evidence_evidence_scoped as module,
)


def _candidate(answer: str = "Please") -> dict:
    return {
        "item_id": "E4S_A1V1_READING_SOURCE_034__CLOZE",
        "question_type": "cloze_vocabulary",
        "answer_model": {
            "answer_type": "normalized_text",
            "answer_key": answer,
            "case_sensitive": False,
        },
        "source_sentence_ids": ["S1"],
    }


def test_repeated_key_is_resolved_by_source_sentence_evidence() -> None:
    segments = [
        {
            "segment_id": "R1",
            "sentence": '"Please, please can I have soup?',
            "source_sentence_ids": ["S1"],
        },
        {
            "segment_id": "R2",
            "sentence": 'No more bread, please," said Mina.',
            "source_sentence_ids": ["S2"],
        },
    ]

    revision, problems = module.build_cloze_revision_evidence_scoped(
        _candidate(),
        segments,
        ["S1"],
    )

    assert revision is not None
    assert revision["prompt"] == 'Complete the source sentence: "____, please can I have soup?'
    assert revision["answer_model"]["answer_key"] == "Please"
    assert revision["accepted_answers"] == ["Please"]
    assert revision["source_sentence_ids"] == ["S1"]
    assert problems == ["CLOZE_SEGMENT_RESOLVED_BY_SOURCE_EVIDENCE"]


def test_multiple_evidence_linked_segments_still_fail_closed() -> None:
    segments = [
        {"segment_id": "R1", "sentence": "Please wait.", "source_sentence_ids": ["S1"]},
        {"segment_id": "R2", "sentence": "Please sit.", "source_sentence_ids": ["S1"]},
    ]

    revision, problems = module.build_cloze_revision_evidence_scoped(
        _candidate(),
        segments,
        ["S1"],
    )

    assert revision is None
    assert problems == ["CLOZE_EVIDENCE_SEGMENT_MATCH_COUNT_2"]


def test_install_replaces_only_original_cloze_selector() -> None:
    original = base._build_cloze_revision
    try:
        module.install_evidence_scoped_cloze_fullfix()
        assert base._build_cloze_revision is module.build_cloze_revision_evidence_scoped
    finally:
        base._build_cloze_revision = original


def test_direct_script_execution_bootstraps_repo_imports(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script = (
        repo_root
        / "ulga"
        / "builders"
        / "rebuild_a1_a1plus_reading_private_revision_evidence_evidence_scoped.py"
    )
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "--private-bank" in result.stdout
    assert "--materialized-decisions" in result.stdout

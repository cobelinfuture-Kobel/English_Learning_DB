#!/usr/bin/env python3
"""Select and balance Unit01 three-skill candidates from a complete RAZQ01B2 replay."""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as contract_builder
from ulga.builders import build_a1fs_v1_razq01b2_unit01_v2_approval_replay_consumer_reconciliation as replay_v2

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Selects source candidates and emits candidate-only coverage gap specifications; "
    "no learner-facing content, answer key, scoring, state, audio, A2, or canonical bank is written."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = (
    "A1FS-V1-RAZQ01C_"
    "Unit01ThreeSkillCandidateSelectionCoverageBalancingAndDeferredListeningReadback"
)
SCHEMA_VERSION = "a1fs.v1.razq01c.unit01_three_skill_candidate_selection.v1"
PASS_STATUS = "PASS_A1FS_V1_RAZQ01C_UNIT01_THREE_SKILL_CANDIDATE_SELECTION"
UNIT_ID = "GRAMMAR_ARTICLES_BASIC"
APPROVED_CONTRACT_SHA256 = replay_v2.APPROVED_CONTRACT_SHA256
DEFAULT_CONTRACT = contract_builder.DEFAULT_OUTPUT
OUTPUT_REPORT = "a1fs_v1_razq01c_unit01_three_skill_candidate_selection.json"
OUTPUT_VALIDATION = "a1fs_v1_razq01c_unit01_three_skill_candidate_selection_validation.json"
OUTPUT_MATRIX = "a1fs_v1_razq01c_unit01_coverage_matrix.csv"
NEXT_SHORT_STEP = (
    "A1FS-V1-RAZQ01D_Unit01ProjectAuthoredGapCandidateBuildAndHumanAdmission"
)

SELECTION_CLASSES = (
    "DIRECT_MODEL",
    "CONTROLLED_PRACTICE_SOURCE",
    "CONTEXT_SOURCE",
    "REWRITE_REQUIRED",
    "REJECT",
)
DIRECT_CLASSES = frozenset({"DIRECT_MODEL", "CONTROLLED_PRACTICE_SOURCE", "CONTEXT_SOURCE"})
WORD_RE = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)?")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
ORDINAL_RE = re.compile(
    r"\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b",
    re.I,
)
COMPARATIVE_RE = re.compile(
    r"\bas\s+\w+\s+as\b|\bmore\s+\w+\s+than\b|\b\w+er\s+than\b",
    re.I,
)
IRREGULAR_PAST_RE = re.compile(
    r"\b(went|saw|put|came|made|found|gave|took|had|was|were|ate|ran|wrote|read)\b",
    re.I,
)
NEGATIVE_IMPERATIVE_RE = re.compile(r"^\s*[\"“']?(do not|don't)\b", re.I)
INVERSION_RE = re.compile(r"^\s*(then|here|there)\s+(comes|goes|is|are)\b", re.I)
UNAPPROVED_MODAL_RE = re.compile(r"\b(can|can't|cannot)\b", re.I)
DIRECT_FRAME_PATTERNS = {
    "U01-F01": re.compile(r"^This is (?:a|an|the) .+\.$", re.I),
    "U01-F02": re.compile(r"^I have (?:a|an|the) .+\.$", re.I),
    "U01-F03": re.compile(r"^(?:A|An|The) .+ is in the .+\.$", re.I),
    "U01-F04": re.compile(r"^(?:A|An|The) .+ is near the .+\.$", re.I),
    "U01-F05": re.compile(r"^The .+ is (?:in|on|near) .+\.$", re.I),
    "U01-F06": re.compile(r"^I can see (?:a|an|the) .+\.$", re.I),
    "U01-AF01": re.compile(r"^This is (?:a|an|the) \w+ \w+\.$", re.I),
    "U01-AF02": re.compile(r"^I can see (?:a|an|the) \w+ \w+\.$", re.I),
    "U01-AF03": re.compile(r"^This is a very \w+ \w+\.$", re.I),
}
SEMANTIC_REWRITE_PATTERNS = {
    "SEMANTIC_COLLOCATION_BUILD_TREE": re.compile(r"\bbuild a tree\b", re.I),
    "SEMANTIC_COLLOCATION_TREE_FRIEND": re.compile(r"\bmake a tree friend\b", re.I),
    "SEMANTIC_COLLOCATION_BASKET_FOR_BAG": re.compile(r"\bbasket for a bag\b", re.I),
    "SEMANTIC_COLLOCATION_ICE_FORMS_WINDOW": re.compile(r"\bice forms on a window\b", re.I),
    "SEMANTIC_COLLOCATION_ROOM_IN_HOUSE": re.compile(r"\broom is in a house\b", re.I),
}


class SelectionError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SelectionError(f"UNREADABLE_JSON:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise SelectionError(f"OBJECT_REQUIRED:{path}")
    return value


def _words(text: str) -> list[str]:
    return [token.lower().replace("’", "'") for token in WORD_RE.findall(text)]


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE_RE.split(text.strip()) if part.strip()]


def _structural_flags(text: str) -> list[str]:
    flags: list[str] = []
    if text.count('"') % 2 or text.count("“") != text.count("”"):
        flags.append("UNBALANCED_QUOTATION")
    if text.rstrip().endswith(",") or re.match(
        r"^(in|on|near|through|out)\b", text.strip(), re.I
    ):
        flags.append("FRAGMENT_OR_TRAILING_PUNCTUATION")
    for code, pattern in (
        ("ORDINAL_PRESENT", ORDINAL_RE),
        ("COMPARATIVE_PRESENT", COMPARATIVE_RE),
        ("IRREGULAR_PAST_PRESENT", IRREGULAR_PAST_RE),
        ("NEGATIVE_IMPERATIVE_PRESENT", NEGATIVE_IMPERATIVE_RE),
        ("INVERSION_PRESENT", INVERSION_RE),
    ):
        if pattern.search(text):
            flags.append(code)
    modal_hits = UNAPPROVED_MODAL_RE.findall(text)
    if modal_hits and not re.match(r"^I can see\b", text.strip(), re.I):
        flags.append("UNAPPROVED_MODAL_SCAFFOLD")
    for code, pattern in SEMANTIC_REWRITE_PATTERNS.items():
        if pattern.search(text):
            flags.append(code)
    return sorted(set(flags))


def _matched_frames(text: str) -> list[str]:
    return sorted(
        fid for fid, pattern in DIRECT_FRAME_PATTERNS.items() if pattern.match(text.strip())
    )


def classify_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    text = str(candidate.get("text_excerpt") or "").strip()
    gate = candidate.get("contract_gate") or {}
    flags = _structural_flags(text)
    frames = _matched_frames(text)
    words = _words(text)
    sentences = _sentences(text)
    reasons: list[str] = []
    if (
        not text
        or not candidate.get("source_record_id")
        or not candidate.get("semantic_identity")
        or gate.get("classification") != "PASS"
    ):
        selection_class = "REJECT"
        reasons.append("STRICT_CANDIDATE_IDENTITY_OR_GATE_INVALID")
    elif "UNBALANCED_QUOTATION" in flags or "FRAGMENT_OR_TRAILING_PUNCTUATION" in flags:
        selection_class = "REJECT"
        reasons.extend(flags)
    elif flags:
        selection_class = "REWRITE_REQUIRED"
        reasons.extend(flags)
    elif frames:
        selection_class = "DIRECT_MODEL"
        reasons.append("APPROVED_SENTENCE_FRAME_MATCH")
    elif len(sentences) == 1 and 3 <= len(words) <= 8:
        selection_class = "CONTROLLED_PRACTICE_SOURCE"
        reasons.append("SHORT_SINGLE_SENTENCE_ARTICLE_PRACTICE")
    elif 1 <= len(sentences) <= 3 and len(words) <= 24:
        selection_class = "CONTEXT_SOURCE"
        reasons.append("SHORT_CONTEXT_WITH_APPROVED_ARTICLE_PHRASE")
    else:
        selection_class = "REWRITE_REQUIRED"
        reasons.append("DIRECT_TEACHING_COMPLEXITY_EXCEEDS_SELECTION_LIMIT")
    source_skills = set(candidate.get("skill_eligibility") or [])
    direct_skills: list[str] = []
    if selection_class in DIRECT_CLASSES:
        for source_name, task_name in (
            ("READING_SOURCE_ELIGIBLE", "READING_TASK_CANDIDATE"),
            ("SPEAKING_PROMPT_ELIGIBLE", "SPEAKING_TASK_CANDIDATE"),
            ("WRITING_SEED_ELIGIBLE", "WRITING_TASK_CANDIDATE"),
        ):
            if source_name in source_skills:
                direct_skills.append(task_name)
    return {
        "source_record_id": candidate.get("source_record_id"),
        "semantic_identity": candidate.get("semantic_identity"),
        "source_level": candidate.get("source_level"),
        "source_type": candidate.get("source_type"),
        "text_excerpt": text,
        "selection_class": selection_class,
        "selection_reasons": sorted(set(reasons)),
        "structural_flags": flags,
        "matched_sentence_frame_ids": frames,
        "direct_task_candidate_roles": sorted(direct_skills),
        "active_noun_hits": sorted(set(gate.get("active_noun_hits") or [])),
        "active_adjective_hits": sorted(set(gate.get("active_adjective_hits") or [])),
        "direct_noun_phrases": sorted(set(gate.get("direct_noun_phrases") or [])),
        "adjective_noun_phrases": sorted(
            set(gate.get("adjective_noun_phrases") or [])
        ),
        "very_adjective_noun_phrases": sorted(
            set(gate.get("very_adjective_noun_phrases") or [])
        ),
        "source_skill_eligibility": sorted(source_skills),
        "canonical_admission": False,
        "human_review_required": selection_class != "REJECT",
    }


def _article_coverage(candidates: Iterable[Mapping[str, Any]]) -> set[str]:
    result: set[str] = set()
    for candidate in candidates:
        for key in (
            "direct_noun_phrases",
            "adjective_noun_phrases",
            "very_adjective_noun_phrases",
        ):
            for phrase in candidate.get(key) or []:
                first = str(phrase).split(maxsplit=1)[0].lower()
                if first in {"a", "an", "the"}:
                    result.add(first)
    return result


def _source_coverage(
    selected: Sequence[Mapping[str, Any]], contract: Mapping[str, Any]
) -> dict[str, Any]:
    usable = [row for row in selected if row["selection_class"] in DIRECT_CLASSES]
    noun_targets = sorted(contract_builder.active_noun_lemmas(contract))
    adjective_targets = sorted(contract_builder.active_adjective_lemmas(contract))
    frame_targets = sorted(
        row["frame_id"]
        for section in ("core_frames", "adjective_expansion_frames")
        for row in contract["sentence_frame_contract"][section]
    )
    noun_hits = sorted({item for row in usable for item in row["active_noun_hits"]})
    adjective_hits = sorted(
        {item for row in usable for item in row["active_adjective_hits"]}
    )
    frame_hits = sorted(
        {item for row in usable for item in row["matched_sentence_frame_ids"]}
    )
    article_hits = sorted(_article_coverage(usable))
    return {
        "active_nouns": {
            "target": noun_targets,
            "covered": noun_hits,
            "missing": sorted(set(noun_targets) - set(noun_hits)),
        },
        "active_adjectives": {
            "target": adjective_targets,
            "covered": adjective_hits,
            "missing": sorted(set(adjective_targets) - set(adjective_hits)),
        },
        "articles": {
            "target": ["a", "an", "the"],
            "covered": article_hits,
            "missing": sorted({"a", "an", "the"} - set(article_hits)),
        },
        "sentence_frames": {
            "target": frame_targets,
            "covered": frame_hits,
            "missing": sorted(set(frame_targets) - set(frame_hits)),
        },
    }


def _gap_specs(
    coverage: Mapping[str, Any], contract: Mapping[str, Any]
) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    noun_rows = {
        row["lemma"]: row
        for row in contract["vocabulary_contract"]["active_vocabulary"]
    }
    adjective_rows = {
        row["lemma"]: row
        for row in contract["vocabulary_contract"]["active_adjectives"]
    }
    for lemma in coverage["active_nouns"]["missing"]:
        row = noun_rows[lemma]
        specs.append(
            {
                "gap_spec_id": f"U01-GAP-NOUN-{lemma.upper()}",
                "gap_dimension": "ACTIVE_NOUN",
                "target_lemmas": [lemma],
                "required_memory_forms": [
                    row["memory_form_indefinite"],
                    row["memory_form_definite"],
                ],
                "candidate_only": True,
                "generated": True,
                "review_status": "PENDING",
                "canonical_admission": False,
            }
        )
    for lemma in coverage["active_adjectives"]["missing"]:
        row = adjective_rows[lemma]
        specs.append(
            {
                "gap_spec_id": f"U01-GAP-ADJECTIVE-{lemma.upper()}",
                "gap_dimension": "ACTIVE_ADJECTIVE",
                "target_lemmas": [lemma],
                "required_memory_forms": [row["memory_phrase"]],
                "candidate_only": True,
                "generated": True,
                "review_status": "PENDING",
                "canonical_admission": False,
            }
        )
    for article in coverage["articles"]["missing"]:
        specs.append(
            {
                "gap_spec_id": f"U01-GAP-ARTICLE-{article.upper()}",
                "gap_dimension": "ARTICLE_FORM",
                "target_articles": [article],
                "candidate_only": True,
                "generated": True,
                "review_status": "PENDING",
                "canonical_admission": False,
            }
        )
    for frame_id in coverage["sentence_frames"]["missing"]:
        specs.append(
            {
                "gap_spec_id": f"U01-GAP-FRAME-{frame_id}",
                "gap_dimension": "SENTENCE_FRAME",
                "target_sentence_frame_ids": [frame_id],
                "candidate_only": True,
                "generated": True,
                "review_status": "PENDING",
                "canonical_admission": False,
            }
        )
    return specs


def _planned_coverage(coverage: Mapping[str, Any]) -> dict[str, Any]:
    planned = deepcopy(coverage)
    for item in planned.values():
        item["covered_after_gap_specs"] = list(item["target"])
        item["missing_after_gap_specs"] = []
    return planned


def _write_csv(report: Mapping[str, Any], path: Path) -> None:
    rows: list[dict[str, Any]] = []
    for dimension, item in report["coverage"]["source_coverage"].items():
        target = item["target"]
        covered = item["covered"]
        rows.append(
            {
                "unit_id": UNIT_ID,
                "dimension": dimension,
                "target_count": len(target),
                "source_covered_count": len(covered),
                "source_missing_count": len(item["missing"]),
                "planned_covered_count": len(target),
                "planned_missing_count": 0,
            }
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_selection(
    replay_report: Mapping[str, Any], contract: Mapping[str, Any]
) -> dict[str, Any]:
    contract_builder.verify_contract_digest(contract)
    if contract.get("contract_sha256") != APPROVED_CONTRACT_SHA256:
        raise SelectionError("UNIT01_V2_CONTRACT_DIGEST_INVALID")
    if replay_report.get("status") != replay_v2.PASS_STATUS:
        raise SelectionError("RAZQ01B2_REPLAY_STATUS_INVALID")
    if (
        replay_report.get("inputs", {}).get("approved_contract_sha256")
        != APPROVED_CONTRACT_SHA256
    ):
        raise SelectionError("RAZQ01B2_REPLAY_CONTRACT_DIGEST_INVALID")
    scope = replay_report.get("scope", {})
    if (
        scope.get("allowed_units") != [UNIT_ID]
        or scope.get("canonical_promotion") is not False
    ):
        raise SelectionError("RAZQ01B2_REPLAY_SCOPE_INVALID")
    unit = replay_report.get("unit", {})
    pass_count = int(unit.get("filter_funnel", {}).get("pass_count") or 0)
    strict = unit.get("samples", {}).get("PASS", [])
    if not isinstance(strict, list) or len(strict) != pass_count:
        actual = len(strict) if isinstance(strict, list) else -1
        raise SelectionError(
            "COMPLETE_STRICT_CANDIDATE_MANIFEST_REQUIRED:"
            f"expected={pass_count}:actual={actual}"
        )
    semantic_ids = [str(row.get("semantic_identity") or "") for row in strict]
    if len(set(semantic_ids)) != len(semantic_ids) or "" in semantic_ids:
        raise SelectionError("STRICT_CANDIDATE_SEMANTIC_IDENTITY_INVALID")
    selected = [classify_candidate(row) for row in strict]
    class_counts = Counter(row["selection_class"] for row in selected)
    skill_counts = Counter(
        role for row in selected for role in row["direct_task_candidate_roles"]
    )
    coverage = _source_coverage(selected, contract)
    gaps = _gap_specs(coverage, contract)
    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "scope": {
            "allowed_units": [UNIT_ID],
            "blocked_units": "UNIT_02_TO_UNIT_24",
            "canonical_promotion": False,
            "learner_facing_content_write": False,
            "a2_status": "LOCKED",
        },
        "inputs": {
            "approved_contract_sha256": APPROVED_CONTRACT_SHA256,
            "upstream_task_id": replay_report.get("task_id"),
            "upstream_records_scanned": replay_report.get("records_scanned"),
            "upstream_strict_pass_count": pass_count,
            "complete_strict_candidate_manifest": True,
        },
        "selection_policy": {
            "classes": list(SELECTION_CLASSES),
            "direct_task_classes": sorted(DIRECT_CLASSES),
            "raw_raz_text_learner_facing_copy_allowed": False,
            "human_review_required_before_admission": True,
        },
        "selection_summary": {
            "strict_candidate_count": pass_count,
            "classification_counts": {
                name: class_counts.get(name, 0) for name in SELECTION_CLASSES
            },
            "direct_task_candidate_counts": dict(sorted(skill_counts.items())),
        },
        "selected_candidates": selected,
        "coverage": {
            "source_coverage": coverage,
            "project_authored_gap_specs": gaps,
            "planned_coverage_after_gap_specs": _planned_coverage(coverage),
            "source_coverage_complete": not any(
                item["missing"] for item in coverage.values()
            ),
            "planned_coverage_complete": True,
        },
        "listening_readback": {
            "status": "DEFERRED_NO_LISTENING_LESSON_IN_UNIT01_RUNTIME",
            "listening_task_candidate_count": 0,
            "audio_enabled": False,
            "listening_claimed_complete": False,
        },
        "validation": {
            "unit01_only": True,
            "complete_strict_candidate_manifest": True,
            "all_strict_candidates_classified": len(selected) == pass_count,
            "coverage_balancing_applied": True,
            "gap_specs_candidate_only": all(row["candidate_only"] for row in gaps),
            "canonical_content_modified": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def write_outputs(report: Mapping[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / OUTPUT_REPORT).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    validation = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "selection_summary": report["selection_summary"],
        "coverage": report["coverage"],
        "listening_readback": report["listening_readback"],
        "validation": report["validation"],
        "next_short_step": NEXT_SHORT_STEP,
    }
    (output_dir / OUTPUT_VALIDATION).write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_csv(report, output_dir / OUTPUT_MATRIX)


def run(
    *, replay_report_path: Path, contract_path: Path, output_dir: Path
) -> dict[str, Any]:
    report = build_selection(_load(replay_report_path), _load(contract_path))
    write_outputs(report, output_dir)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay-report", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = run(
            replay_report_path=args.replay_report.resolve(),
            contract_path=args.contract.resolve(),
            output_dir=args.output_dir.resolve(),
        )
    except (SelectionError, ValueError, KeyError, TypeError) as exc:
        print(
            "STATUS=FAIL_A1FS_V1_RAZQ01C_UNIT01_THREE_SKILL_"
            "CANDIDATE_SELECTION"
        )
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={report['status']}")
    print(f"STRICT_CANDIDATES={report['selection_summary']['strict_candidate_count']}")
    for name, count in report["selection_summary"]["classification_counts"].items():
        print(f"CLASS={name} COUNT={count}")
    print(f"GAP_SPECS={len(report['coverage']['project_authored_gap_specs'])}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

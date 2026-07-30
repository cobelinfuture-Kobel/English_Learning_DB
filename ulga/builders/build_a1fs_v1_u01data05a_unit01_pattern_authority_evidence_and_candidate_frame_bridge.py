#!/usr/bin/env python3
"""Extract Unit01 Pattern Authority evidence and build a candidate-only frame bridge."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as contract_builder
from ulga.builders import build_a1fs_online_v1_2_u01e_s01_unit01_five_context_authority_admission as s01

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Extracts committed Pattern Authority and Unit01 frame metadata, detects unit-level "
    "pattern broadcast, and emits candidate-only evidence. It writes no canonical bridge, "
    "coverage, learner-facing content, scoring, state, audio, A2 target, or parallel bank."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = (
    "A1FS-V1-U01DATA05A_"
    "Unit01CanonicalPatternAuthorityEvidenceExtractionAndCandidateFrameBridge"
)
SCHEMA_VERSION = "a1fs.v1.u01data05a.unit01_pattern_authority_candidate_frame_bridge.v1"
PASS_STATUS = "PASS_A1FS_V1_U01DATA05A_UNIT01_PATTERN_AUTHORITY_CANDIDATE_FRAME_BRIDGE"
UNIT_ID = contract_builder.UNIT_ID
REPO_ROOT = Path(__file__).resolve().parents[2]
PATTERN_AUTHORITY_PATH = REPO_ROOT / "ulga/graph/pattern_vocabulary_constraints.json"
DEFAULT_OUTPUT = Path(
    "ulga/graph/a1fs_v1_u01data05a_unit01_pattern_authority_candidate_frame_bridge.json"
)
PATTERN_IDS = ("SP_000016", "SP_000017")
EXPECTED_CANONICAL_PATTERNS = {
    "SP_000016": "This is {noun_phrase}.",
    "SP_000017": "That is {noun_phrase}.",
}
CANDIDATE_FRAME_IDS = ("U01-F01", "U01-AF01", "U01-AF03")
NEXT_SHORT_STEP = (
    "A1FS-V1-U01DATA05B_"
    "Unit01ActivityLevelPatternTargetReconciliationAndFrameCoverageGate"
)
TOKEN_RE = re.compile(r"\{([A-Z_]+)\}|([A-Za-z]+)")


class EvidenceBuildError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_pattern_authority(path: Path = PATTERN_AUTHORITY_PATH) -> list[dict[str, Any]]:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise EvidenceBuildError("PATTERN_AUTHORITY_NOT_LIST")
    by_id = {
        str(row.get("pattern_id")): row
        for row in rows
        if isinstance(row, Mapping) and row.get("pattern_id")
    }
    selected = []
    for pattern_id in PATTERN_IDS:
        row = by_id.get(pattern_id)
        if not isinstance(row, Mapping):
            raise EvidenceBuildError(f"PATTERN_AUTHORITY_MISSING:{pattern_id}")
        if row.get("canonical_pattern") != EXPECTED_CANONICAL_PATTERNS[pattern_id]:
            raise EvidenceBuildError(f"PATTERN_CANONICAL_TEMPLATE_DRIFT:{pattern_id}")
        if row.get("active") is not True or row.get("generator_allowed") is not True:
            raise EvidenceBuildError(f"PATTERN_NOT_ACTIVE_GENERATOR_ALLOWED:{pattern_id}")
        if str(row.get("cefr_level")).upper() != "A1" or row.get("review_status") != "accepted":
            raise EvidenceBuildError(f"PATTERN_NOT_ACCEPTED_A1:{pattern_id}")
        selected.append(deepcopy(dict(row)))
    return selected


def unit_frame_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for frame_id, template, goal, support in contract_builder.CORE_SENTENCE_FRAMES:
        rows.append(
            {
                "frame_id": frame_id,
                "template": template,
                "frame_group": "CORE",
                "communicative_goal": goal,
                "support_level": support,
                "assessment_scope": "ARTICLE_SELECTION_AND_NOUN_PHRASE_ONLY",
            }
        )
    for frame_id, template, goal, support, egp_role in contract_builder.ADJECTIVE_SENTENCE_FRAMES:
        rows.append(
            {
                "frame_id": frame_id,
                "template": template,
                "frame_group": "ADJECTIVE",
                "communicative_goal": goal,
                "support_level": support,
                "egp_role": egp_role,
                "assessment_scope": "ARTICLE_SELECTION_BEFORE_ADJECTIVE_AND_ADJECTIVE_NOUN_PHRASE",
            }
        )
    for frame_id, template, grammar, role in contract_builder.SCAFFOLD_FRAMES:
        rows.append(
            {
                "frame_id": frame_id,
                "template": template,
                "frame_group": "SCAFFOLD",
                "external_grammar_ref": grammar,
                "support_level": role,
                "assessment_scope": "SCAFFOLD_ONLY_NOT_UNIT01_TARGET",
            }
        )
    if len(rows) != 11 or len({row["frame_id"] for row in rows}) != 11:
        raise EvidenceBuildError("UNIT01_FRAME_DENOMINATOR_INVALID")
    return rows


def template_tokens(template: str) -> list[str]:
    result = []
    for slot, literal in TOKEN_RE.findall(template):
        result.append(slot or literal.upper())
    return result


def pattern_signature(row: Mapping[str, Any]) -> dict[str, Any]:
    pattern = str(row["canonical_pattern"])
    subject = "THIS" if pattern.startswith("This is ") else "THAT" if pattern.startswith("That is ") else "OTHER"
    return {
        "comparison_level": "CLAUSE_WITH_GENERIC_COMPLEMENT",
        "subject_form": subject,
        "predicate": "BE_IS" if subject in {"THIS", "THAT"} else "OTHER",
        "complement_category": "NOUN_PHRASE",
        "complement_structure": ["NOUN_PHRASE"],
        "exact_frame_specificity": False,
    }


def frame_signature(row: Mapping[str, Any]) -> dict[str, Any]:
    template = str(row["template"])
    tokens = template_tokens(template)
    if tokens[:2] == ["THIS", "IS"]:
        subject = "THIS"
        predicate = "BE_IS"
        complement = tokens[2:]
    elif tokens[:2] == ["THAT", "IS"]:
        subject = "THAT"
        predicate = "BE_IS"
        complement = tokens[2:]
    else:
        subject = tokens[0] if tokens else "UNKNOWN"
        predicate = tokens[1] if len(tokens) > 1 else "UNKNOWN"
        complement = tokens[2:] if len(tokens) > 2 else []
    return {
        "comparison_level": "EXACT_UNIT_FRAME",
        "subject_form": subject,
        "predicate": predicate,
        "complement_category": "NOUN_PHRASE" if subject in {"THIS", "THAT"} and predicate == "BE_IS" else "OTHER",
        "complement_structure": complement,
        "contains_adjective_slot": "ADJECTIVE" in complement,
        "contains_intensifier": "VERY" in complement,
        "exact_frame_specificity": True,
    }


def relationship(pattern: Mapping[str, Any], frame: Mapping[str, Any]) -> tuple[str, str, bool]:
    pattern_id = str(pattern["pattern_id"])
    frame_id = str(frame["frame_id"])
    p_sig = pattern_signature(pattern)
    f_sig = frame_signature(frame)
    if (
        pattern_id == "SP_000016"
        and frame_id in CANDIDATE_FRAME_IDS
        and p_sig["subject_form"] == f_sig["subject_form"] == "THIS"
        and p_sig["predicate"] == f_sig["predicate"] == "BE_IS"
        and f_sig["complement_category"] == "NOUN_PHRASE"
    ):
        return (
            "FRAME_REFINES_PATTERN",
            "SAME_THIS_BE_CLAUSE;UNIT_FRAME_SPECIFIES_INTERNAL_NOUN_PHRASE_STRUCTURE",
            True,
        )
    if (
        pattern_id == "SP_000017"
        and f_sig["subject_form"] == "THIS"
        and f_sig["predicate"] == "BE_IS"
    ):
        return (
            "PARALLEL_DEMONSTRATIVE_NOT_FRAME_MATCH",
            "THAT_AND_THIS_SHARE_A_HIGH_LEVEL_DEMONSTRATIVE_BE_SHELL_BUT_ARE_NOT_THE_SAME_FRAME",
            False,
        )
    return (
        "NOT_EQUIVALENT",
        "CLAUSE_OR_COMPLEMENT_STRUCTURE_DOES_NOT_MATCH_THE_PATTERN_AUTHORITY",
        False,
    )


def activities(projection_report: Mapping[str, Any]) -> list[dict[str, Any]]:
    groups = projection_report.get("activity_projections") or {}
    if not isinstance(groups, Mapping):
        raise EvidenceBuildError("ACTIVITY_PROJECTIONS_NOT_OBJECT")
    rows = []
    for key in ("existing_response_contract_activities", "fixed_admitted_items"):
        value = groups.get(key) or []
        if not isinstance(value, list):
            raise EvidenceBuildError(f"ACTIVITY_GROUP_NOT_LIST:{key}")
        rows.extend(dict(row) for row in value if isinstance(row, Mapping))
    return rows


def activity_pattern_assessment(projection_report: Mapping[str, Any]) -> dict[str, Any]:
    rows = activities(projection_report)
    if len(rows) != 24:
        raise EvidenceBuildError(f"ACTIVITY_DENOMINATOR_INVALID:{len(rows)}")
    expected = list(PATTERN_IDS)
    sets = [sorted(str(value) for value in row.get("target_pattern_ids", [])) for row in rows]
    all_broadcast = all(value == expected for value in sets)
    counts = {
        pattern_id: sum(pattern_id in value for value in sets)
        for pattern_id in PATTERN_IDS
    }
    status = (
        "UNIT_LEVEL_BROADCAST_NOT_ACTIVITY_EVIDENCE"
        if all_broadcast
        else "ACTIVITY_LEVEL_PATTERN_VARIATION_PRESENT_REQUIRES_SEMANTIC_VALIDATION"
    )
    return {
        "activity_count": len(rows),
        "expected_unit_pattern_ids": expected,
        "distinct_activity_pattern_sets": sorted({tuple(value) for value in sets}),
        "pattern_activity_counts": counts,
        "every_activity_has_full_unit_pattern_set": all_broadcast,
        "lineage_status": status,
        "activity_level_pattern_evidence_usable_for_frame_coverage": False,
        "coverage_claim_allowed": False,
        "reason": (
            "S01 assigns the Unit-level pattern inventory to every activity; the field does not "
            "prove which clause or noun-phrase structure each item actually instantiates."
        ),
    }


def sentence_pattern_evidence(patterns: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    sentences = s01.sentence_rows()
    results = []
    for pattern in patterns:
        pattern_id = str(pattern["pattern_id"])
        prefix = "This is " if pattern_id == "SP_000016" else "That is "
        matched = [
            str(row["sentence_id"])
            for row in sentences
            if str(row.get("text", "")).startswith(prefix)
        ]
        results.append(
            {
                "pattern_id": pattern_id,
                "approved_unit01_sentence_count": len(matched),
                "approved_unit01_sentence_ids": matched,
                "instantiation_status": (
                    "DIRECT_SENTENCE_EVIDENCE_PRESENT"
                    if matched
                    else "NO_DIRECT_APPROVED_SENTENCE_INSTANTIATION"
                ),
            }
        )
    return results


def build_report(
    *,
    projection_report: Mapping[str, Any],
    pattern_authority_path: Path = PATTERN_AUTHORITY_PATH,
) -> dict[str, Any]:
    patterns = load_pattern_authority(pattern_authority_path)
    frames = unit_frame_rows()
    matrix = []
    for pattern in patterns:
        for frame in frames:
            relation, basis, candidate = relationship(pattern, frame)
            matrix.append(
                {
                    "pattern_id": str(pattern["pattern_id"]),
                    "pattern_template": str(pattern["canonical_pattern"]),
                    "pattern_signature": pattern_signature(pattern),
                    "unit_frame_id": str(frame["frame_id"]),
                    "unit_frame_template": str(frame["template"]),
                    "unit_frame_signature": frame_signature(frame),
                    "relationship": relation,
                    "decision_basis": basis,
                    "candidate_bridge": candidate,
                    "exact_equivalent": False,
                    "coverage_merge_allowed": False,
                    "canonical_write_allowed": False,
                    "evidence_refs": [
                        f"ulga/graph/pattern_vocabulary_constraints.json:{pattern['pattern_id']}",
                        f"ulga/builders/build_a1fs_v1_razq01b_unit01_content_contract.py:{frame['frame_id']}",
                    ],
                }
            )
    broadcast = activity_pattern_assessment(projection_report)
    report = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "pattern_authority": patterns,
        "unit_frame_authority": frames,
        "candidate_bridge_matrix": matrix,
        "candidate_summary": {
            "pattern_count": len(patterns),
            "unit_frame_count": len(frames),
            "matrix_row_count": len(matrix),
            "candidate_bridge_count": sum(bool(row["candidate_bridge"]) for row in matrix),
            "exact_equivalent_count": sum(bool(row["exact_equivalent"]) for row in matrix),
            "candidate_frame_ids_by_pattern": {
                pattern_id: sorted(
                    row["unit_frame_id"]
                    for row in matrix
                    if row["pattern_id"] == pattern_id and row["candidate_bridge"]
                )
                for pattern_id in PATTERN_IDS
            },
            "canonical_bridge_written": False,
            "frame_coverage_claimed": False,
        },
        "approved_sentence_pattern_evidence": sentence_pattern_evidence(patterns),
        "activity_pattern_lineage_assessment": broadcast,
        "operator_decision_requirement": {
            "required_now": False,
            "reason": (
                "Pattern Authority is sufficient to classify structural candidates, but activity-level "
                "pattern evidence is a Unit-level broadcast and cannot support canonical admission."
            ),
        },
        "boundaries": {
            "canonical_bridge_written": False,
            "frame_coverage_claimed": False,
            "learner_facing_content_written": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
            "pattern_authority_mutated": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    report["report_sha256"] = digest(report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projection-report", type=Path, required=True)
    parser.add_argument("--pattern-authority", type=Path, default=PATTERN_AUTHORITY_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        projection = json.loads(args.projection_report.read_text(encoding="utf-8"))
        report = build_report(
            projection_report=projection,
            pattern_authority_path=args.pattern_authority,
        )
        write_json(args.output, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (EvidenceBuildError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Read-only Unit03 Q2/Q4 delta-vs-cumulative provenance reconciliation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ulga.builders import build_a1fs_v1_u02ch02_unit01_unit02_cumulative_chunk_coverage_recheck as u02ch02

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Read-only Unit03 Q2/Q4 provenance reconciliation over existing curriculum-resource identities, Unit01 noun-whitelist evidence, Unit02 exact vocabulary inventory, and Unit01+Unit02 chunk authority; creates/promotes no vocabulary, chunk, grammar, SentenceAsset, QuestionBank, scene, runtime/state/scoring, or A2 authority."

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U03Q02Q04R1_Unit03VocabularyChunkDeltaVsCumulativeExactProvenanceRecheck"
SCHEMA_VERSION = "a1fs.v1.u03q02q04r1.vocabulary_chunk_provenance_recheck.v1"
PASS_STATUS = "PASS_A1FS_V1_U03Q02Q04R1_VOCABULARY_CHUNK_PROVENANCE_RECHECK"
NEXT_SHORT_STEP = "A1FS-V1-U03Q05R1_Unit03SubjectPronounSentencePatternFamilyAndExactFrameRecheck"
UNIT_ID = "GRAMMAR_SUBJECT_PRONOUNS"

ROOT = Path(__file__).resolve().parents[2]
VOCABULARY_PATH = ROOT / "vocabulary" / "json" / "vocabulary.json"
U02_VOCAB_REPORT_PATH = ROOT / "ulga" / "reports" / "a1fs_v1_u02qb01_exact_plain_s_active_vocabulary_inventory.json"

# Source-bound Unit03 support-resource identities. These are not a claim that the
# 40 rows are newly introduced vocabulary. Their provenance is what this task audits.
UNIT03_Q2_SOURCE_ROWS = (('KPOP-VR-001', 'v_7212', 'person', 'HUMAN', 'A1', 'noun'), ('KPOP-VR-002', 'v_5326', 'man', 'MALE', 'A1', 'noun'), ('KPOP-VR-003', 'v_9963', 'woman', '', 'A1', 'noun'), ('KPOP-VR-004', 'v_586', 'boy', '', 'A1', 'noun'), ('KPOP-VR-005', 'v_3825', 'girl', 'FEMALE CHILD', 'A1', 'noun'), ('KPOP-VR-006', 'v_974', 'child', '', 'A1', 'noun'), ('KPOP-VR-007', 'v_3871', 'friend', 'PERSON YOU LIKE', 'A1', 'noun'), ('KPOP-VR-008', 'v_4622', 'family', 'RELATED PEOPLE', 'A1', 'noun'), ('KPOP-VR-009', 'v_3869', 'father', '', 'A1', 'noun'), ('KPOP-VR-010', 'v_5364', 'mother', '', 'A1', 'noun'), ('KPOP-VR-011', 'v_630', 'brother', '', 'A1', 'noun'), ('KPOP-VR-012', 'v_8650', 'sister', '', 'A1', 'noun'), ('KPOP-VR-013', 'v_8983', 'school', 'PLACE', 'A1', 'noun'), ('KPOP-VR-014', 'v_8737', 'teacher', '', 'A1', 'noun'), ('KPOP-VR-015', 'v_8388', 'student', '', 'A1', 'noun'), ('KPOP-VR-016', 'v_1428', 'class', 'TEACHING GROUP', 'A1', 'noun'), ('KPOP-VR-017', 'v_5167', 'lesson', 'TEACHING PERIOD', 'A1', 'noun'), ('KPOP-VR-018', 'v_233', 'book', 'FOR READING', 'A1', 'noun'), ('KPOP-VR-019', 'v_6630', 'pen', '', 'A1', 'noun'), ('KPOP-VR-020', 'v_3659', 'homework', '', 'A1', 'noun'), ('KPOP-VR-021', 'v_5172', 'learn', 'GET KNOWLEDGE', 'A1', 'verb'), ('KPOP-VR-022', 'v_9186', 'study', 'UNIVERSITY/SCHOOL', 'A1', 'verb'), ('KPOP-VR-023', 'v_6698', 'read', 'WORDS', 'A1', 'verb'), ('KPOP-VR-024', 'v_10346', 'write', 'PRODUCE', 'A1', 'verb'), ('KPOP-VR-051', 'v_3897', 'football', 'GAME', 'A1', 'noun'), ('KPOP-VR-052', 'v_3891', 'game', 'ACTIVITY/SPORT', 'A1', 'noun'), ('KPOP-VR-053', 'v_8665', 'sport', 'GAME', 'A1', 'noun'), ('KPOP-VR-054', 'v_5033', 'music', 'SOUNDS', 'A1', 'noun'), ('KPOP-VR-055', 'v_3545', 'film', 'MOVING PICTURES', 'A1', 'noun'), ('KPOP-VR-056', 'v_6929', 'party', 'EVENT', 'A1', 'noun'), ('KPOP-VR-057', 'v_7546', 'play', 'SPORT', 'A1', 'verb'), ('KPOP-VR-058', 'v_9960', 'watch', 'LOOK AT', 'A1', 'verb'), ('KPOP-VR-059', 'v_5263', 'listen', 'HEAR', 'A1', 'verb'), ('KPOP-VR-060', 'v_5318', 'meet', 'COME TOGETHER', 'A1', 'verb'), ('KPOP-VR-061', 'v_9956', 'visit', 'SEE A PERSON', 'A1', 'verb'), ('KPOP-VR-062', 'v_5125', 'invite', 'SOCIAL', 'A1', 'verb'), ('KPOP-VR-063', 'v_361', 'ask', 'QUESTION', 'A1', 'verb'), ('KPOP-VR-064', 'v_8352', 'tell', 'SPEAK', 'A1', 'verb'), ('KPOP-VR-065', 'v_8354', 'thank', '', 'A2', 'verb'), ('KPOP-VR-066', 'v_9318', 'sorry', 'APOLOGY', 'A1', 'adjective'))

EXPECTED_Q2_SUPPORT_POOL = 40
EXPECTED_U02_EXACT_INHERITED = 16
EXPECTED_U01_NO_ACTIVE_SURFACE = 3
EXPECTED_U01_NON_PLAIN_S_SURFACE = 5
EXPECTED_SURFACE_POS_COLLISION = 1
EXPECTED_PREVIOUS_UNIT_UNRESOLVED = 15


def norm(value: str) -> str:
    return " ".join(str(value).casefold().split())


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _vocabulary_index() -> dict[str, dict[str, Any]]:
    rows = _load_json(VOCABULARY_PATH)
    return {str(row["vocab_id"]): dict(row) for row in rows}


def _u02_report() -> dict[str, Any]:
    return dict(_load_json(U02_VOCAB_REPORT_PATH))


def _u02_exact_ids(report: dict[str, Any]) -> set[str]:
    return {
        str(vocab_id)
        for row in report["inventory"]
        for vocab_id in row["vocabulary_ids"]
    }


def _unit01_noun_provenance(report: dict[str, Any]) -> tuple[set[str], set[str], dict[str, str]]:
    plain = {norm(row["singular"]) for row in report["inventory"]}
    no_active = {norm(value) for value in report["excluded_no_active_authority"]}
    non_plain: dict[str, str] = {}
    for reason, values in report["excluded_non_plain_s"].items():
        for value in values:
            non_plain[norm(value)] = str(reason)
    whitelist = plain | no_active | set(non_plain)
    if len(whitelist) != 221:
        raise AssertionError(f"UNIT01_NOUN_WHITELIST_DENOMINATOR_INVALID:{len(whitelist)}")
    return whitelist, no_active, non_plain


def q2_rows() -> list[dict[str, Any]]:
    vocabulary = _vocabulary_index()
    u02 = _u02_report()
    u02_exact = _u02_exact_ids(u02)
    u01_whitelist, u01_no_active, u01_non_plain = _unit01_noun_provenance(u02)
    rows: list[dict[str, Any]] = []

    for resource_id, vocab_id, word, guideword, level, part_of_speech in UNIT03_Q2_SOURCE_ROWS:
        canonical = vocabulary.get(vocab_id)
        if canonical is None:
            raise AssertionError(f"UNIT03_Q2_CANONICAL_VOCAB_ID_MISSING:{resource_id}:{vocab_id}")
        expected = {
            "word": word,
            "guideword": guideword,
            "level": level,
            "part_of_speech": part_of_speech,
        }
        for field, expected_value in expected.items():
            actual = str(canonical.get(field, ""))
            if norm(actual) != norm(expected_value):
                raise AssertionError(
                    f"UNIT03_Q2_CANONICAL_IDENTITY_DRIFT:{resource_id}:{vocab_id}:"
                    f"{field}:{actual!r}!={expected_value!r}"
                )

        nword = norm(word)
        pos = norm(part_of_speech)
        if vocab_id in u02_exact:
            delta_class = "INHERITED_EXACT_FROM_UNIT02"
            unit01_status = "UNIT01_NOUN_WHITELIST_SURFACE_PROVEN"
            unit02_status = "UNIT02_EXACT_VOCABULARY_IDENTITY"
        elif pos == "noun" and nword in u01_no_active:
            delta_class = "UNIT01_SURFACE_PROVEN_NO_U02_ACTIVE_TARGET"
            unit01_status = "UNIT01_NOUN_WHITELIST_SURFACE_PROVEN_NO_ACTIVE_U02_AUTHORITY"
            unit02_status = "NOT_IN_UNIT02_162_EXACT_IDENTITY"
        elif pos == "noun" and nword in u01_non_plain:
            delta_class = "UNIT01_SURFACE_PROVEN_NON_PLAIN_S_NOT_U02_TARGET"
            unit01_status = f"UNIT01_NOUN_WHITELIST_SURFACE_PROVEN_{u01_non_plain[nword]}"
            unit02_status = "NOT_IN_UNIT02_162_EXACT_IDENTITY"
        elif pos != "noun" and nword in u01_whitelist:
            delta_class = "SURFACE_COLLISION_DIFFERENT_POS_NOT_INHERITED_IDENTITY"
            unit01_status = "UNIT01_NOUN_SURFACE_COLLISION_ONLY"
            unit02_status = "NOT_IN_UNIT02_162_EXACT_IDENTITY"
        else:
            delta_class = "PREVIOUS_UNIT_PROVENANCE_UNRESOLVED"
            unit01_status = "NOT_PROVEN_BY_UNIT01_NOUN_WHITELIST_AUTHORITY"
            unit02_status = "NOT_IN_UNIT02_162_EXACT_IDENTITY"

        rows.append({
            "resource_id": resource_id,
            "vocabulary_id": vocab_id,
            "word": word,
            "guideword": guideword,
            "level": level,
            "part_of_speech": part_of_speech,
            "canonical_active": bool(canonical.get("active")),
            "unit01_provenance_status": unit01_status,
            "unit02_provenance_status": unit02_status,
            "unit03_delta_class": delta_class,
        })
    return rows


def build_report() -> dict[str, Any]:
    q2 = q2_rows()
    by_class: dict[str, int] = {}
    for row in q2:
        key = str(row["unit03_delta_class"])
        by_class[key] = by_class.get(key, 0) + 1

    q4_source = u02ch02.build_report()
    q4_counts = q4_source["coverage_denominators"]
    u01_rows = u02ch02.unit01_rows()
    u02_rows = u02ch02.unit02_rows()
    q4 = {
        "unit01_inherited_surface_rows": len(u01_rows),
        "unit02_native_inherited_surface_rows": len(u02_rows),
        "unit01_unit02_inherited_cumulative_surface_rows": q4_counts["cumulative_distinct_surface_rows"],
        "unit03_new_admitted_surface_rows": 0,
        "unit03_native_surface_rows": 0,
        "cumulative_distinct_surface_rows": q4_counts["cumulative_distinct_surface_rows"],
        "cumulative_direct_or_instructional_surface_rows": q4_counts["cumulative_direct_or_instructional_surface_rows"],
        "cumulative_receptive_only_surface_rows": q4_counts["cumulative_receptive_only_surface_rows"],
        "referenced_global_canonical_parent_id_count": q4_counts["referenced_global_canonical_parent_id_count"],
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "unit_id": UNIT_ID,
        "status": PASS_STATUS,
        "q2": {
            "support_pool_count": len(q2),
            "rows": q2,
            "provenance_class_counts": by_class,
            "unit03_definitely_new_vocabulary_count": None,
            "unit03_definitely_new_vocabulary_claimed": False,
            "unresolved_reason": (
                "The Unit01 221-row authority is noun-whitelist evidence, not an exhaustive "
                "all-POS Unit01 lexical-usage inventory. Therefore rows outside that authority "
                "cannot be truthfully labeled Unit03-new without a broader prior-unit audit."
            ),
        },
        "q4": q4,
        "claim_boundaries": {
            "q2_support_pool_is_not_unit03_new_count": True,
            "unresolved_q2_rows_are_not_labeled_new": True,
            "unit03_q4_new_chunk_count_is_zero": True,
            "canonical_vocabulary_mutated": False,
            "canonical_chunk_authority_mutated": False,
            "sentence_assets_created": False,
            "questionbank_items_created": False,
            "runtime_mutated": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def validate(report: dict[str, Any]) -> None:
    q2 = report["q2"]
    counts = q2["provenance_class_counts"]
    assert q2["support_pool_count"] == EXPECTED_Q2_SUPPORT_POOL
    assert counts["INHERITED_EXACT_FROM_UNIT02"] == EXPECTED_U02_EXACT_INHERITED
    assert counts["UNIT01_SURFACE_PROVEN_NO_U02_ACTIVE_TARGET"] == EXPECTED_U01_NO_ACTIVE_SURFACE
    assert counts["UNIT01_SURFACE_PROVEN_NON_PLAIN_S_NOT_U02_TARGET"] == EXPECTED_U01_NON_PLAIN_S_SURFACE
    assert counts["SURFACE_COLLISION_DIFFERENT_POS_NOT_INHERITED_IDENTITY"] == EXPECTED_SURFACE_POS_COLLISION
    assert counts["PREVIOUS_UNIT_PROVENANCE_UNRESOLVED"] == EXPECTED_PREVIOUS_UNIT_UNRESOLVED
    assert sum(counts.values()) == EXPECTED_Q2_SUPPORT_POOL

    q4 = report["q4"]
    assert q4["unit01_inherited_surface_rows"] == 24
    assert q4["unit02_native_inherited_surface_rows"] == 26
    assert q4["unit01_unit02_inherited_cumulative_surface_rows"] == 50
    assert q4["unit03_new_admitted_surface_rows"] == 0
    assert q4["cumulative_distinct_surface_rows"] == 50


def main() -> int:
    report = build_report()
    validate(report)
    print(f"STATUS={PASS_STATUS}")
    print(f"Q2_SUPPORT_POOL={report['q2']['support_pool_count']}")
    for key, value in sorted(report["q2"]["provenance_class_counts"].items()):
        print(f"Q2_{key}={value}")
    print(f"Q2_DEFINITELY_NEW_CLAIMED={report['q2']['unit03_definitely_new_vocabulary_claimed']}")
    print(f"Q4_U01_INHERITED={report['q4']['unit01_inherited_surface_rows']}")
    print(f"Q4_U02_NATIVE_INHERITED={report['q4']['unit02_native_inherited_surface_rows']}")
    print(f"Q4_UNIT03_NEW={report['q4']['unit03_new_admitted_surface_rows']}")
    print(f"Q4_CUMULATIVE={report['q4']['cumulative_distinct_surface_rows']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

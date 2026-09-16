from __future__ import annotations

import csv
import gzip
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

TASK_ID = "A1FS-V1-U04FSV2A_ApprovedCurrent360SectionA120BindingImplementation"
STATUS = "PASS_A1FS_V1_U04FSV2A_APPROVED_CURRENT360_SECTION_A_120_BINDING"
SECTION_A_REVISION = "CURRENT360_GPT5_6_OPERATOR_APPROVED_SECTION_A_120_V1"
SOURCE_AUTHORITY = "CURRENT360_EFFECTIVE_EPISODE_AUTHORITY"
OPERATOR_APPROVED = True
OPERATOR_APPROVAL_DATE = "2026-09-16"
GPT5_6_REQUIRED_STATUS = "PASS"
AT_POLICY = "DEFAULT_FORBIDDEN_SECTION_A_CURRENT360_GPT56_OPERATOR_APPROVED_ONLY"
DATA_PATH = Path(__file__).with_name("u04fsv2a_section_a_current360_approved120.tsv.gz")
TARGET_RELATIONS = ("in", "inside", "on", "near", "at", "under", "behind", "between")
FORM_COUNT = 20
ITEMS_PER_FORM = 6
TOTAL_ITEMS = 120
EXPECTED_RELATION_COUNT = 15
EXPECTED_AT_COUNT = 15

STAGE_FORMS = {
    "GUIDED": range(1, 5),
    "REDUCED_SUPPORT": range(5, 9),
    "INDEPENDENT": range(9, 13),
    "TRANSFER": range(13, 17),
    "RETENTION": range(17, 21),
}


class SectionABindingError(ValueError):
    pass


def _split_csv(value: Any) -> list[str]:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


@lru_cache(maxsize=1)
def _rows() -> tuple[dict[str, Any], ...]:
    if not DATA_PATH.exists():
        raise SectionABindingError(f"SECTION_A_AUTHORITY_MISSING:{DATA_PATH}")
    with gzip.open(DATA_PATH, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows: list[dict[str, Any]] = []
        for raw in reader:
            row = {
                "candidate_id": str(raw["candidate_id"]),
                "form_number": int(raw["form"]),
                "section_activity_ordinal": int(raw["local"]),
                "source_episode_id": str(raw["episode_id"]),
                "target_relation": str(raw["relation"]),
                "context": str(raw["context"]),
                "question": str(raw["question"]),
                "stem": str(raw["stem"]),
                "options": [part for part in str(raw["options"]).split("|") if part],
                "answer": str(raw["answer"]),
                "gpt5_6_semantic_review": str(raw["gpt56"]),
                "source_authority": SOURCE_AUTHORITY,
                "operator_approved": OPERATOR_APPROVED,
            }
            rows.append(row)
    _validate_rows(rows)
    return tuple(rows)


def _validate_rows(rows: list[dict[str, Any]]) -> None:
    if len(rows) != TOTAL_ITEMS:
        raise SectionABindingError(f"SECTION_A_COUNT_DRIFT:{len(rows)}")
    ids = [str(row["candidate_id"]) for row in rows]
    if len(set(ids)) != TOTAL_ITEMS:
        raise SectionABindingError("SECTION_A_CANDIDATE_ID_COLLISION")

    expected_slots = {
        (form_number, local)
        for form_number in range(1, FORM_COUNT + 1)
        for local in range(1, ITEMS_PER_FORM + 1)
    }
    actual_slots = {
        (int(row["form_number"]), int(row["section_activity_ordinal"]))
        for row in rows
    }
    if actual_slots != expected_slots:
        raise SectionABindingError("SECTION_A_SLOT_COVERAGE_DRIFT")

    relation_counts = Counter(str(row["target_relation"]) for row in rows)
    expected_relation_counts = Counter({relation: EXPECTED_RELATION_COUNT for relation in TARGET_RELATIONS})
    if relation_counts != expected_relation_counts:
        raise SectionABindingError(f"SECTION_A_RELATION_DISTRIBUTION_DRIFT:{dict(relation_counts)}")
    if relation_counts["at"] != EXPECTED_AT_COUNT:
        raise SectionABindingError(f"SECTION_A_AT_COUNT_DRIFT:{relation_counts['at']}")

    by_form: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        relation = str(row["target_relation"])
        if relation not in TARGET_RELATIONS:
            raise SectionABindingError(f"SECTION_A_UNKNOWN_RELATION:{relation}")
        if row["answer"] != relation:
            raise SectionABindingError(f"SECTION_A_ANSWER_RELATION_MISMATCH:{row['candidate_id']}")
        options = list(row["options"])
        if len(options) != 4 or len(set(options)) != 4 or relation not in options:
            raise SectionABindingError(f"SECTION_A_OPTION_CONTRACT_DRIFT:{row['candidate_id']}")
        if row["gpt5_6_semantic_review"] != GPT5_6_REQUIRED_STATUS:
            raise SectionABindingError(f"SECTION_A_GPT56_REVIEW_NOT_PASS:{row['candidate_id']}")
        if row["source_authority"] != SOURCE_AUTHORITY:
            raise SectionABindingError(f"SECTION_A_SOURCE_AUTHORITY_DRIFT:{row['candidate_id']}")
        if not row["operator_approved"]:
            raise SectionABindingError(f"SECTION_A_OPERATOR_APPROVAL_MISSING:{row['candidate_id']}")
        if relation == "at" and not (
            row["source_authority"] == SOURCE_AUTHORITY
            and row["gpt5_6_semantic_review"] == GPT5_6_REQUIRED_STATUS
            and row["operator_approved"]
        ):
            raise SectionABindingError(f"SECTION_A_AT_BOUNDED_EXCEPTION_REJECTED:{row['candidate_id']}")
        by_form[int(row["form_number"])].append(row)

    for form_number in range(1, FORM_COUNT + 1):
        form_rows = by_form[form_number]
        if len(form_rows) != ITEMS_PER_FORM:
            raise SectionABindingError(f"SECTION_A_FORM_COUNT_DRIFT:F{form_number:02d}")
        if len({str(row["target_relation"]) for row in form_rows}) != ITEMS_PER_FORM:
            raise SectionABindingError(f"SECTION_A_FORM_RELATION_DUPLICATE:F{form_number:02d}")
        if len({str(row["source_episode_id"]) for row in form_rows}) != ITEMS_PER_FORM:
            raise SectionABindingError(f"SECTION_A_FORM_EPISODE_DUPLICATE:F{form_number:02d}")

    for stage, forms in STAGE_FORMS.items():
        stage_rows = [row for row in rows if int(row["form_number"]) in forms]
        counts = Counter(str(row["target_relation"]) for row in stage_rows)
        if counts != Counter({relation: 3 for relation in TARGET_RELATIONS}):
            raise SectionABindingError(f"SECTION_A_STAGE_RELATION_DRIFT:{stage}:{dict(counts)}")


@lru_cache(maxsize=1)
def build_section_a_binding_index() -> dict[tuple[int, int], dict[str, Any]]:
    return {
        (int(row["form_number"]), int(row["section_activity_ordinal"])): dict(row)
        for row in _rows()
    }


def validate_current360_episode(candidate: Mapping[str, Any], episode: Mapping[str, Any]) -> None:
    candidate_id = str(candidate["candidate_id"])
    if str(episode.get("episode_id")) != str(candidate["source_episode_id"]):
        raise SectionABindingError(f"SECTION_A_EPISODE_ID_MISMATCH:{candidate_id}")
    relation = str(candidate["target_relation"])
    declared = set(_split_csv(episode.get("target_relations")))
    passage = str(episode.get("passage") or "").casefold()
    if relation not in declared and relation.casefold() not in passage.split():
        raise SectionABindingError(f"SECTION_A_CURRENT360_RELATION_NOT_SUPPORTED:{candidate_id}:{relation}")
    if relation == "at" and not (
        candidate.get("source_authority") == SOURCE_AUTHORITY
        and candidate.get("gpt5_6_semantic_review") == GPT5_6_REQUIRED_STATUS
        and candidate.get("operator_approved") is True
    ):
        raise SectionABindingError(f"SECTION_A_AT_RUNTIME_GATE_REJECTED:{candidate_id}")


def materialize_learner_activity(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "question_number": "",
        "skill": "GRAMMAR",
        "stimulus": f"Context:\n{candidate['context']}",
        "prompt": f"{candidate['question']}\n{candidate['stem']}",
        "options": [str(value) for value in candidate["options"]],
        "response_mode": "select_one",
        "capture_enabled": True,
        "practice_only": False,
    }


def compact_readback() -> dict[str, Any]:
    rows = list(_rows())
    counts = Counter(str(row["target_relation"]) for row in rows)
    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "section_a_revision": SECTION_A_REVISION,
        "item_count": len(rows),
        "relation_counts": {relation: counts[relation] for relation in TARGET_RELATIONS},
        "at_count": counts["at"],
        "at_policy": AT_POLICY,
        "source_authority": SOURCE_AUTHORITY,
        "gpt5_6_review_required": GPT5_6_REQUIRED_STATUS,
        "operator_approved": OPERATOR_APPROVED,
        "operator_approval_date": OPERATOR_APPROVAL_DATE,
    }

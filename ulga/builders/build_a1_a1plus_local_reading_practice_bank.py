#!/usr/bin/env python3
"""Bind selected A1/A1+ Reading metadata to local source text.

The private output may contain copyrighted source text and must stay under an ignored
local path. The safe report contains identifiers, hashes, counts, and review states
only and may be shared for project validation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.query.a1_canonical_validator_dispatcher import (
    available_grammar_ids,
    validate as dispatch_validate,
)
from ulga.validators.validate_a1_a1plus_selected_reading_source_manifest import (
    EXPECTED_FIELDS,
    INDEX_PATH,
    load_from_repo,
    validate_selected_manifest,
)

TASK_ID = "E4S-A1V1-M04B2_LocalReadingContentBindingAndPracticeBankMaterialization"
PRIVATE_SCHEMA = "e4s.a1v1.local_private_reading_practice_bank.v1"
SAFE_REPORT_SCHEMA = "e4s.a1v1.local_reading_binding_safe_report.v1"
EXPECTED_SOURCE_COUNT = 54
EXPECTED_ORDERING_COUNT = 36
LITERAL_TYPES = ("literal_who", "literal_what", "literal_where")
FORBIDDEN_SAFE_KEYS = {
    "clean_text",
    "reading_text",
    "page_text",
    "passage_text",
    "normalized_text",
    "raw_text",
    "text",
    "content",
    "sentence",
    "sentences",
    "source_sentences",
    "display_text",
    "prompt",
    "answer",
    "answer_text",
    "accepted_answers",
    "evidence_quote",
    "transcript_text",
}
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "had", "has", "have", "he", "her", "hers", "him", "his", "i", "in", "is",
    "it", "its", "me", "my", "of", "on", "or", "our", "ours", "she", "so",
    "that", "the", "their", "theirs", "them", "they", "this", "to", "was", "we",
    "were", "with", "you", "your", "yours",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _selected_records(index_path: Path = INDEX_PATH) -> list[dict[str, Any]]:
    index, shards = load_from_repo(index_path)
    report = validate_selected_manifest(index, shards)
    if report.get("validation_status") != "PASS_SELECTED_READING_SOURCE_MANIFEST":
        raise ValueError(f"selected_manifest_invalid:{report.get('errors', [])}")
    records: list[dict[str, Any]] = []
    for level in "ABCDEF":
        shard = shards[level]
        for row in shard["records"]:
            records.append(dict(zip(EXPECTED_FIELDS, row)))
    records.sort(key=lambda row: row["selection_id"])
    return records


def _resolve_level_source_path(source_root: Path, level: str) -> Path:
    expected = (
        source_root
        / "derived"
        / f"Level_{level}"
        / "enriched"
        / f"raz_{level}_page_unit_enriched.json"
    )
    if expected.is_file():
        return expected
    matches = sorted(source_root.rglob(f"raz_{level}_page_unit_enriched.json"))
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise FileNotFoundError(f"level_source_file_missing:{level}:{expected}")
    raise ValueError(f"level_source_file_ambiguous:{level}:{[str(path) for path in matches]}")


def load_local_source_indexes(source_root: Path) -> tuple[dict[str, dict[str, Mapping[str, Any]]], dict[str, str]]:
    indexes: dict[str, dict[str, Mapping[str, Any]]] = {}
    relative_paths: dict[str, str] = {}
    for level in "ABCDEF":
        path = _resolve_level_source_path(source_root, level)
        payload = _read_json(path)
        if not isinstance(payload, list):
            raise ValueError(f"level_source_not_list:{level}")
        by_id: dict[str, Mapping[str, Any]] = {}
        for row in payload:
            if not isinstance(row, Mapping):
                continue
            source_id = row.get("page_unit_id")
            if isinstance(source_id, str) and source_id:
                if source_id in by_id:
                    raise ValueError(f"duplicate_page_unit_id:{level}:{source_id}")
                by_id[source_id] = row
        indexes[level] = by_id
        relative_paths[level] = path.relative_to(source_root).as_posix()
    return indexes, relative_paths


def _split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text.strip())
    if not normalized:
        return []
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\s*\n+\s*", normalized) if part.strip()]
    return parts or [normalized]


def _word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text))


def _verify_source_record(selected: Mapping[str, Any], source: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    text = source.get("text")
    if not isinstance(text, str) or not text.strip():
        errors.append("source_text_missing")
        text = ""
    sentences = _split_sentences(text)
    checks = {
        "source_unit_ref": source.get("page_unit_id"),
        "source_level": source.get("level"),
        "book_id": str(source.get("book_id")) if source.get("book_id") is not None else None,
        "page_number": source.get("page_number"),
        "sentence_count": len(sentences),
        "word_count": _word_count(text),
        "character_count": len(text.strip()),
        "content_sha256": _sha256_text(text.strip()) if text else None,
        "record_sha256": _sha256_text(_canonical_json(source)),
    }
    for field, actual in checks.items():
        expected = selected.get(field)
        if actual != expected:
            errors.append(f"metadata_or_hash_mismatch:{field}:expected={expected!r}:actual={actual!r}")
    if source.get("authority_status") != "candidate_only":
        errors.append("source_authority_status_not_candidate_only")
    if source.get("promotion_status") != "not_promoted":
        errors.append("source_promotion_status_not_not_promoted")
    qa = source.get("qa_tags") if isinstance(source.get("qa_tags"), Mapping) else {}
    if qa.get("needs_human_review") is True:
        errors.append("source_marked_needs_human_review")
    if qa.get("warnings") not in (None, []):
        errors.append("source_qa_warnings_present")
    return errors


def _grammar_analysis(sentences: Iterable[str]) -> dict[str, Any]:
    by_sentence: list[dict[str, Any]] = []
    all_ids: set[str] = set()
    grammar_ids = available_grammar_ids()
    for sentence_index, sentence in enumerate(sentences, start=1):
        matches: list[dict[str, Any]] = []
        for grammar_id in grammar_ids:
            result = dispatch_validate(grammar_id, sentence)
            if result.get("dispatch_status") == "VALIDATOR_EXECUTED" and result.get("match") is True:
                matches.append(
                    {
                        "grammar_id": grammar_id,
                        "primitive_id": result.get("primitive_id"),
                        "reason": result.get("reason"),
                    }
                )
                all_ids.add(grammar_id)
        by_sentence.append(
            {
                "sentence_id": f"S{sentence_index}",
                "sentence": sentence,
                "matches": matches,
            }
        )
    if len(all_ids) == 1:
        binding_status = "UNIQUE_CANONICAL_MATCH_CANDIDATE"
    elif all_ids:
        binding_status = "MULTIPLE_CANONICAL_MATCHES_REVIEW_REQUIRED"
    else:
        binding_status = "NO_CANONICAL_MATCH_REVIEW_REQUIRED"
    return {
        "binding_status": binding_status,
        "candidate_grammar_ids": sorted(all_ids),
        "sentence_results": by_sentence,
        "operator_review_required": True,
    }


def _choose_cloze_token(sentence: str) -> tuple[str, str] | None:
    tokens = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", sentence)
    candidates = [token for token in tokens if len(token) >= 3 and token.casefold() not in STOPWORDS]
    if not candidates:
        candidates = [token for token in tokens if token.casefold() not in STOPWORDS]
    if not candidates:
        return None
    answer = candidates[0]
    prompt = re.sub(rf"\b{re.escape(answer)}\b", "____", sentence, count=1, flags=re.IGNORECASE)
    return prompt, answer


def _deterministic_items(selection_id: str, sentences: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    first = sentences[0]
    items.append(
        {
            "item_id": f"{selection_id}__TF",
            "question_type": "true_false",
            "status": "PRIVATE_REVIEW_CANDIDATE",
            "prompt": f"True or false: {first}",
            "answer_model": {"answer_type": "boolean", "answer_key": True},
            "source_sentence_ids": ["S1"],
            "deterministic_scoring_ready": True,
        }
    )
    cloze = _choose_cloze_token(first)
    if cloze:
        prompt, answer = cloze
        items.append(
            {
                "item_id": f"{selection_id}__CLOZE",
                "question_type": "cloze_vocabulary",
                "status": "PRIVATE_REVIEW_CANDIDATE",
                "prompt": f"Complete the local source sentence: {prompt}",
                "answer_model": {
                    "answer_type": "normalized_text",
                    "answer_key": answer,
                    "case_sensitive": False,
                },
                "source_sentence_ids": ["S1"],
                "deterministic_scoring_ready": True,
            }
        )
    if len(sentences) >= 2:
        ids = [f"S{index}" for index in range(1, len(sentences) + 1)]
        rotated = ids[1:] + ids[:1]
        sentence_map = {f"S{index}": sentence for index, sentence in enumerate(sentences, start=1)}
        items.append(
            {
                "item_id": f"{selection_id}__ORDER",
                "question_type": "sentence_ordering",
                "status": "PRIVATE_REVIEW_CANDIDATE",
                "prompt": "Put the local source sentences in their original order.",
                "display_order": [
                    {"sentence_id": sentence_id, "sentence": sentence_map[sentence_id]}
                    for sentence_id in rotated
                ],
                "answer_model": {"answer_type": "ordered_ids", "answer_key": ids},
                "source_sentence_ids": ids,
                "deterministic_scoring_ready": True,
            }
        )
    return items


def _literal_review_candidates(selection_id: str, selected: Mapping[str, Any], sentences: list[str]) -> list[dict[str, Any]]:
    types = [question_type for question_type in LITERAL_TYPES if question_type in selected["candidate_question_types"]]
    return [
        {
            "candidate_id": f"{selection_id}__{question_type.upper()}",
            "question_type": question_type,
            "status": "PENDING_OPERATOR_QUESTION_AND_ANSWER_REVIEW",
            "source_sentence_ids": [f"S{index}" for index in range(1, len(sentences) + 1)],
            "auto_answer_generated": False,
            "reason": "LITERAL_ANSWER_NOT_ASSUMED_FROM_HEURISTIC_SOURCE_METADATA",
        }
        for question_type in types
    ]


def _safe_record(
    selected: Mapping[str, Any],
    source_path: str,
    errors: list[str],
    grammar: Mapping[str, Any],
    items: list[Mapping[str, Any]],
    literal_candidates: list[Mapping[str, Any]],
) -> dict[str, Any]:
    item_types = Counter(str(item["question_type"]) for item in items)
    return {
        "selection_id": selected["selection_id"],
        "source_unit_ref": selected["source_unit_ref"],
        "source_level": selected["source_level"],
        "book_id": selected["book_id"],
        "page_number": selected["page_number"],
        "e4s_situation_domain": selected["e4s_situation_domain"],
        "source_file_locator": source_path,
        "content_sha256": selected["content_sha256"],
        "record_sha256": selected["record_sha256"],
        "source_integrity_status": "PASS" if not errors else "FAIL",
        "source_integrity_errors": errors,
        "grammar_binding_status": grammar["binding_status"],
        "candidate_grammar_ids": list(grammar["candidate_grammar_ids"]),
        "deterministic_item_count": len(items),
        "deterministic_item_types": dict(sorted(item_types.items())),
        "literal_review_candidate_types": sorted(
            str(candidate["question_type"]) for candidate in literal_candidates
        ),
        "operator_review_required": True,
    }


def _assert_safe_report(payload: Mapping[str, Any]) -> None:
    def visit(value: Any, path: str = "$") -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if key in FORBIDDEN_SAFE_KEYS:
                    raise ValueError(f"forbidden_text_key_in_safe_report:{path}.{key}")
                visit(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")
    visit(payload)


def materialize_local_reading_bank(
    selected_records: list[Mapping[str, Any]],
    source_indexes: Mapping[str, Mapping[str, Mapping[str, Any]]],
    source_paths: Mapping[str, str],
    *,
    require_full_selection: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    private_records: list[dict[str, Any]] = []
    safe_records: list[dict[str, Any]] = []
    for selected in selected_records:
        level = str(selected["source_level"])
        source_ref = str(selected["source_unit_ref"])
        source = source_indexes.get(level, {}).get(source_ref)
        if source is None:
            errors = ["selected_source_record_missing"]
            grammar = {
                "binding_status": "SOURCE_MISSING",
                "candidate_grammar_ids": [],
                "sentence_results": [],
                "operator_review_required": True,
            }
            items: list[dict[str, Any]] = []
            literal_candidates: list[dict[str, Any]] = []
            safe_records.append(
                _safe_record(selected, source_paths.get(level, ""), errors, grammar, items, literal_candidates)
            )
            continue
        errors = _verify_source_record(selected, source)
        text = str(source.get("text", "")).strip()
        sentences = _split_sentences(text)
        grammar = _grammar_analysis(sentences) if not errors else {
            "binding_status": "SOURCE_INTEGRITY_FAILED",
            "candidate_grammar_ids": [],
            "sentence_results": [],
            "operator_review_required": True,
        }
        items = _deterministic_items(str(selected["selection_id"]), sentences) if not errors else []
        literal_candidates = (
            _literal_review_candidates(str(selected["selection_id"]), selected, sentences)
            if not errors else []
        )
        private_records.append(
            {
                "selection": dict(selected),
                "source_file_locator": source_paths.get(level),
                "source_text": text,
                "source_sentences": [
                    {"sentence_id": f"S{index}", "sentence": sentence}
                    for index, sentence in enumerate(sentences, start=1)
                ],
                "source_integrity": {"status": "PASS" if not errors else "FAIL", "errors": errors},
                "grammar_analysis": grammar,
                "deterministic_items": items,
                "literal_review_candidates": literal_candidates,
            }
        )
        safe_records.append(
            _safe_record(selected, source_paths.get(level, ""), errors, grammar, items, literal_candidates)
        )

    integrity_pass_count = sum(row["source_integrity_status"] == "PASS" for row in safe_records)
    deterministic_counts = Counter()
    grammar_status_counts = Counter()
    literal_counts = Counter()
    for row in safe_records:
        deterministic_counts.update(row["deterministic_item_types"])
        grammar_status_counts[row["grammar_binding_status"]] += 1
        literal_counts.update(row["literal_review_candidate_types"])
    all_sources_resolved = integrity_pass_count == len(selected_records)
    full_count_ok = len(selected_records) == EXPECTED_SOURCE_COUNT if require_full_selection else True
    ordering_ok = deterministic_counts["sentence_ordering"] == EXPECTED_ORDERING_COUNT if require_full_selection else True
    validation_errors: list[str] = []
    if not full_count_ok:
        validation_errors.append(f"selected_source_count_not_{EXPECTED_SOURCE_COUNT}")
    if not all_sources_resolved:
        validation_errors.append("one_or_more_selected_sources_failed_integrity")
    if deterministic_counts["true_false"] != len(selected_records):
        validation_errors.append("true_false_materialization_incomplete")
    if deterministic_counts["cloze_vocabulary"] != len(selected_records):
        validation_errors.append("cloze_materialization_incomplete")
    if not ordering_ok:
        validation_errors.append(f"sentence_ordering_count_not_{EXPECTED_ORDERING_COUNT}")

    private_output = {
        "task_id": TASK_ID,
        "schema_version": PRIVATE_SCHEMA,
        "artifact_type": "local_private_source_grounded_reading_review_candidates",
        "policy": {
            "private_local_only": True,
            "must_not_be_committed": True,
            "not_for_public_export": True,
            "authority_status": "candidate_only",
            "promotion_status": "not_promoted",
            "operator_review_required": True,
        },
        "summary": {
            "selected_source_count": len(selected_records),
            "source_integrity_pass_count": integrity_pass_count,
            "deterministic_item_counts": dict(sorted(deterministic_counts.items())),
            "grammar_binding_status_counts": dict(sorted(grammar_status_counts.items())),
            "literal_review_candidate_counts": dict(sorted(literal_counts.items())),
        },
        "records": private_records,
        "claim_boundaries": {
            "reading_v1_complete": False,
            "items_promoted": False,
            "learner_evidence_created": False,
            "mastery_claimed": False,
            "retention_confirmed": False,
            "persistent_learner_state_write": False,
            "production_runtime_event": False,
            "a2_a2plus_in_scope": False,
        },
    }
    safe_report = {
        "task_id": TASK_ID,
        "schema_version": SAFE_REPORT_SCHEMA,
        "artifact_type": "local_reading_content_binding_safe_report",
        "validation_status": "PASS_LOCAL_READING_BINDING_EXECUTED" if not validation_errors else "FAIL",
        "error_count": len(validation_errors),
        "errors": validation_errors,
        "summary": private_output["summary"],
        "records": safe_records,
        "claim_boundaries": {
            "raw_source_text_included": False,
            "full_passage_text_included": False,
            "sentence_text_included": False,
            "source_payload_copied": False,
            "metadata_and_hashes_only": True,
            "reading_v1_complete": False,
            "items_promoted": False,
            "learner_evidence_created": False,
            "mastery_claimed": False,
            "retention_confirmed": False,
            "persistent_learner_state_write": False,
            "production_runtime_event": False,
            "a2_a2plus_in_scope": False,
        },
        "m04b2_local_binding_execution_complete": not validation_errors,
        "m04b3_operator_review_complete": False,
        "next_resume_task": "E4S-A1V1-M04B3_SourceGroundedReadingCandidateReviewAndPromotion",
    }
    _assert_safe_report(safe_report)
    return private_output, safe_report


def build_from_repo(
    source_root: Path,
    *,
    selected_index: Path = INDEX_PATH,
) -> tuple[dict[str, Any], dict[str, Any]]:
    selected = _selected_records(selected_index)
    source_indexes, source_paths = load_local_source_indexes(source_root.resolve())
    return materialize_local_reading_bank(selected, source_indexes, source_paths)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build local private Reading candidates and a safe report.")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--selected-index", type=Path, default=INDEX_PATH)
    parser.add_argument(
        "--private-output",
        type=Path,
        default=REPO_ROOT / ".local/e4s_a1v1/reading/a1_a1plus_private_reading_candidates.json",
    )
    parser.add_argument("--safe-report", type=Path, required=True)
    args = parser.parse_args(argv)
    private_output, safe_report = build_from_repo(
        args.source_root,
        selected_index=args.selected_index,
    )
    _write_json(args.private_output, private_output)
    _write_json(args.safe_report, safe_report)
    print(json.dumps(safe_report["summary"], ensure_ascii=False, sort_keys=True))
    print(f"validation_status={safe_report['validation_status']}")
    print(f"private_output={args.private_output}")
    print(f"safe_report={args.safe_report}")
    return 0 if safe_report["validation_status"] == "PASS_LOCAL_READING_BINDING_EXECUTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())

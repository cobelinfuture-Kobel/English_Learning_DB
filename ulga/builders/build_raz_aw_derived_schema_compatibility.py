#!/usr/bin/env python3
"""Load both RAZ derived schemas for A-W three-layer classification.

A-I expose page-unit enriched arrays. J-W expose enriched unit, sentence, and
book registries. This module reconstructs J-W page units deterministically and
then delegates classification to the existing A-W derived/review/bridge
classifier. Safe output remains text-free and unpromoted.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_ai_theme_sentence_scene_candidate_classification as classifier

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AW_DerivedSchemaCompatibilityFullFix"
DEFAULT_SOURCE_ROOT = REPO_ROOT / "raz_output_jsons"
DEFAULT_MANIFEST = REPO_ROOT / ".local/raz_af/a1_a1plus_reading_source_manifest.json"
DEFAULT_OUTPUT = classifier.DEFAULT_OUTPUT


class DerivedSchemaCompatibilityError(ValueError):
    """Fail-closed derived schema or three-layer join error."""


def discover_named(root: Path, level: str, kind: str, filename: str) -> Path:
    if kind == "derived":
        candidates = [
            root / "derived" / f"Level_{level}" / "enriched" / filename,
            root / f"Level_{level}" / "enriched" / filename,
            root / filename,
        ]
    elif kind == "review":
        candidates = [root / "review" / f"Level_{level}" / filename]
    elif kind == "bridge":
        candidates = [
            root / "bridge" / "reading_authority" / f"Level_{level}" / filename
        ]
    else:
        raise DerivedSchemaCompatibilityError(f"unknown_source_kind:{kind}")
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if path is None:
        found = list(root.rglob(filename))
        if kind == "bridge":
            found = [item for item in found if "bridge" in item.parts]
        elif kind == "review":
            found = [item for item in found if "review" in item.parts]
        elif kind == "derived":
            found = [item for item in found if "derived" in item.parts or item.parent == root]
        if len(found) == 1:
            path = found[0]
    if path is None:
        raise DerivedSchemaCompatibilityError(
            f"missing_{kind}_file:{level}:{filename}"
        )
    return path


def payload_records(payload: Any, owner: str) -> list[dict[str, Any]]:
    if not isinstance(payload, Mapping) or not isinstance(payload.get("records"), list):
        raise DerivedSchemaCompatibilityError(f"records_missing:{owner}")
    rows = [row for row in payload["records"] if isinstance(row, dict)]
    if len(rows) != len(payload["records"]):
        raise DerivedSchemaCompatibilityError(f"invalid_record:{owner}")
    return rows


def reconstruct_page_units(
    level: str,
    units_payload: Mapping[str, Any],
    sentences_payload: Mapping[str, Any],
    books_payload: Mapping[str, Any],
) -> list[dict[str, Any]]:
    expected = {
        "units": (units_payload, "raz_enriched_units.v1"),
        "sentences": (sentences_payload, "raz_enriched_sentences.v1"),
        "books": (books_payload, "raz_enriched_books.v1"),
    }
    for name, (payload, schema_version) in expected.items():
        if payload.get("schema_version") != schema_version:
            raise DerivedSchemaCompatibilityError(
                f"schema_mismatch:{level}:{name}:{payload.get('schema_version')}"
            )

    units = payload_records(units_payload, f"{level}:units")
    sentences = payload_records(sentences_payload, f"{level}:sentences")
    books = payload_records(books_payload, f"{level}:books")

    sentence_by_uid: dict[str, Mapping[str, Any]] = {}
    for row in sentences:
        uid = row.get("sentence_uid")
        if not isinstance(uid, str) or not uid or uid in sentence_by_uid:
            raise DerivedSchemaCompatibilityError(
                f"invalid_or_duplicate_sentence_uid:{level}:{uid}"
            )
        sentence_by_uid[uid] = row

    book_by_uid: dict[str, Mapping[str, Any]] = {}
    for row in books:
        uid = row.get("book_uid")
        if not isinstance(uid, str) or not uid or uid in book_by_uid:
            raise DerivedSchemaCompatibilityError(
                f"invalid_or_duplicate_book_uid:{level}:{uid}"
            )
        book_by_uid[uid] = row

    output: list[dict[str, Any]] = []
    seen_units: set[str] = set()
    sequence_tokens = {"first", "next", "then", "finally", "after", "before"}
    for unit in units:
        if unit.get("unit_type") != "page_unit":
            continue
        ref = unit.get("unit_uid")
        book_uid = unit.get("book_uid")
        if not isinstance(ref, str) or not ref or ref in seen_units:
            raise DerivedSchemaCompatibilityError(
                f"invalid_or_duplicate_unit_uid:{level}:{ref}"
            )
        if not isinstance(book_uid, str) or book_uid not in book_by_uid:
            raise DerivedSchemaCompatibilityError(
                f"unit_book_missing:{level}:{ref}:{book_uid}"
            )
        sentence_uids = unit.get("sentence_uids")
        if not isinstance(sentence_uids, list) or not sentence_uids:
            raise DerivedSchemaCompatibilityError(
                f"unit_sentence_uids_missing:{level}:{ref}"
            )
        sentence_rows = []
        for sentence_uid in sentence_uids:
            sentence = sentence_by_uid.get(sentence_uid)
            if sentence is None:
                raise DerivedSchemaCompatibilityError(
                    f"unit_sentence_missing:{level}:{ref}:{sentence_uid}"
                )
            sentence_rows.append(sentence)
        text = " ".join(
            str(sentence.get("text") or "").strip()
            for sentence in sentence_rows
            if str(sentence.get("text") or "").strip()
        )
        if not text:
            raise DerivedSchemaCompatibilityError(
                f"reconstructed_text_missing:{level}:{ref}"
            )

        book = book_by_uid[book_uid]
        theme_candidates = book.get("candidate_theme_tags")
        theme = (
            str(theme_candidates[0])
            if isinstance(theme_candidates, list) and theme_candidates
            else "Unknown"
        )
        punctuation_profiles = [
            row.get("punctuation_profile")
            for row in sentence_rows
            if isinstance(row.get("punctuation_profile"), Mapping)
        ]
        has_direct_speech = any(
            row.get("dialogue_candidate_flag") is True for row in sentence_rows
        ) or any(
            profile.get("contains_question_mark") is True
            or profile.get("contains_quote_mark") is True
            for profile in punctuation_profiles
        )
        page_match = re.search(r"_p(\d+)$", ref)
        output.append(
            {
                "page_unit_id": ref,
                "book_id": str(
                    book.get("book_id") or book_uid.rsplit("_", 1)[-1]
                ),
                "book_uid": book_uid,
                "level": level,
                "title": str(book.get("title") or ""),
                "page_number": int(page_match.group(1)) if page_match else None,
                "sentence_count": len(sentence_rows),
                "text": text,
                "content_unit_tags": {
                    "has_direct_speech": has_direct_speech,
                    "has_sequence": bool(
                        set(deep.tokens(text)) & sequence_tokens
                    ),
                },
                "theme_tags": {
                    "primary_theme": theme,
                    "mapped_theme": theme,
                },
                "reuse_tags": {
                    "reusability_tags": sorted(
                        {
                            str(value)
                            for value in unit.get("candidate_reuse_tags", [])
                            if isinstance(value, str)
                        }
                    )
                },
            }
        )
        seen_units.add(ref)
    if not output:
        raise DerivedSchemaCompatibilityError(
            f"no_reconstructed_page_units:{level}"
        )
    return output


def load_derived_level(
    root: Path, level: str
) -> tuple[list[dict[str, Any]], list[Path], str]:
    page_filename = f"raz_{level}_page_unit_enriched.json"
    try:
        page_path = discover_named(root, level, "derived", page_filename)
    except DerivedSchemaCompatibilityError:
        page_path = None
    if page_path is not None:
        payload = deep.read_json(page_path)
        if not isinstance(payload, list) or not all(
            isinstance(row, dict) for row in payload
        ):
            raise DerivedSchemaCompatibilityError(
                f"page_unit_enriched_not_list:{level}"
            )
        return payload, [page_path], "page_unit_enriched.v1"

    units_path = discover_named(
        root, level, "derived", f"raz_{level}_enriched_units.json"
    )
    sentences_path = discover_named(
        root, level, "derived", f"raz_{level}_enriched_sentences.json"
    )
    books_path = discover_named(
        root, level, "derived", f"raz_{level}_enriched_books.json"
    )
    rows = reconstruct_page_units(
        level,
        deep.read_json(units_path),
        deep.read_json(sentences_path),
        deep.read_json(books_path),
    )
    return (
        rows,
        [units_path, sentences_path, books_path],
        "reconstructed_enriched_v1",
    )


def source_ref(record: Mapping[str, Any]) -> str:
    trace = record.get("source_traceability")
    if not isinstance(trace, Mapping):
        return ""
    return str(
        trace.get("source_page_unit_id")
        or trace.get("source_passage_unit_id")
        or ""
    )


def load_three_layers(
    root: Path,
    levels: Sequence[str] = classifier.LEVELS,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    all_rows: list[dict[str, Any]] = []
    index: list[dict[str, Any]] = []
    global_refs: set[str] = set()
    for level in levels:
        derived, derived_paths, derived_schema = load_derived_level(root, level)
        review_path = discover_named(
            root,
            level,
            "review",
            f"raz_{level}_page_passage_review_candidates.json",
        )
        bridge_path = discover_named(
            root,
            level,
            "bridge",
            f"raz_{level}_reading_authority_bridge_candidates.json",
        )
        review_payload = deep.read_json(review_path)
        bridge_payload = deep.read_json(bridge_path)
        if review_payload.get("schema_version") != "raz_page_passage_review_contract.v1":
            raise DerivedSchemaCompatibilityError(
                f"review_schema_mismatch:{level}"
            )
        if bridge_payload.get("schema_version") != "raz_reading_authority_bridge_contract.v1":
            raise DerivedSchemaCompatibilityError(
                f"bridge_schema_mismatch:{level}"
            )
        review_records = payload_records(review_payload, f"{level}:review")
        bridge_records = payload_records(bridge_payload, f"{level}:bridge")
        review_by_ref = {source_ref(row): row for row in review_records}
        bridge_by_ref = {source_ref(row): row for row in bridge_records}
        if "" in review_by_ref or len(review_by_ref) != len(review_records):
            raise DerivedSchemaCompatibilityError(
                f"invalid_or_duplicate_review_ref:{level}"
            )
        if "" in bridge_by_ref or len(bridge_by_ref) != len(bridge_records):
            raise DerivedSchemaCompatibilityError(
                f"invalid_or_duplicate_bridge_ref:{level}"
            )

        level_refs: set[str] = set()
        books: set[str] = set()
        for row in derived:
            ref = str(row.get("page_unit_id") or "")
            if not ref or ref in global_refs:
                raise DerivedSchemaCompatibilityError(
                    f"invalid_or_duplicate_derived_ref:{level}:{ref}"
                )
            review = review_by_ref.get(ref)
            bridge = bridge_by_ref.get(ref)
            if review is None or bridge is None:
                raise DerivedSchemaCompatibilityError(
                    f"three_layer_join_missing:{ref}"
                )
            if bridge.get("source_review_candidate_uid") != review.get(
                "review_candidate_uid"
            ):
                raise DerivedSchemaCompatibilityError(
                    f"review_bridge_lineage_mismatch:{ref}"
                )
            enriched = dict(row)
            enriched["_review"] = review
            enriched["_bridge"] = bridge
            all_rows.append(enriched)
            global_refs.add(ref)
            level_refs.add(ref)
            books.add(str(row.get("book_id") or ""))
        if level_refs != set(review_by_ref) or level_refs != set(bridge_by_ref):
            raise DerivedSchemaCompatibilityError(
                f"three_layer_level_set_mismatch:{level}"
            )
        index.append(
            {
                "level": level,
                "derived_schema": derived_schema,
                "derived_paths": [
                    path.relative_to(root).as_posix() for path in derived_paths
                ],
                "review_path": review_path.relative_to(root).as_posix(),
                "bridge_path": bridge_path.relative_to(root).as_posix(),
                "derived_sha256s": [
                    deep.sha256_file(path) for path in derived_paths
                ],
                "review_sha256": deep.sha256_file(review_path),
                "bridge_sha256": deep.sha256_file(bridge_path),
                "record_count": len(level_refs),
                "book_count": len(books),
            }
        )
    return all_rows, index


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        rows, file_index = load_three_layers(args.source_root)
        package = classifier.build_package(
            rows,
            file_index,
            deep.load_authorities(),
            deep.load_manifest_grammar_tags(args.manifest),
        )
        leakage = classifier.scan_forbidden_safe_keys(package)
        if leakage:
            raise DerivedSchemaCompatibilityError(
                "safe_output_leakage:" + ";".join(leakage[:10])
            )
        deep.write_json_atomic(args.output, package)
        print(
            json.dumps(
                {
                    "task_id": TASK_ID,
                    "decision": package["classification_gate"]["decision"],
                    "record_count": package["source_scope"]["record_count"],
                    "package_sha256": package["package_sha256"],
                },
                sort_keys=True,
            )
        )
        return 0
    except (
        DerivedSchemaCompatibilityError,
        classifier.ClassificationError,
        deep.AlignmentError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

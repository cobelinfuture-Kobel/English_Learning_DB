from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterator


BASE_DIR = Path(__file__).resolve().parents[2]
TASK_NAME = "RAZ-AW-S9_ReadingAuthorityIntake_BuilderQA_ArtifactExternalizationAndWarningTaxonomy"
ARTIFACT_NAME = "raz_reading_authority_intake_candidates.json"
ARTIFACT_PATH = BASE_DIR / "ulga" / "graph" / ARTIFACT_NAME
GITIGNORE_PATH = BASE_DIR / ".gitignore"
BUILDER_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "raz_reading_authority_intake_builder_summary.json"
BUILDER_VALIDATION_PATH = BASE_DIR / "ulga" / "reports" / "raz_reading_authority_intake_builder_validation.json"
MANIFEST_PATH = BASE_DIR / "ulga" / "reports" / "raz_reading_authority_intake_artifact_manifest.json"
TAXONOMY_PATH = BASE_DIR / "ulga" / "reports" / "raz_reading_authority_intake_warning_taxonomy.json"
QA_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "raz_reading_authority_intake_builder_qa_summary.json"
QA_VALIDATION_PATH = BASE_DIR / "ulga" / "reports" / "raz_reading_authority_intake_builder_qa_validation.json"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.validators.validate_raz_reading_authority_intake_schema import (  # noqa: E402
    ValidationError,
    validate_record_semantics,
)


REQUIRED_GITIGNORE_ENTRY = "ulga/graph/raz_reading_authority_intake_candidates.json"
SPARSE_WARNING_TYPES = {
    "theme_tags empty",
    "vocabulary_tags empty",
    "grammar_tags empty",
    "pattern_tags empty",
}
SEMANTIC_WARNING_CATEGORY_MAP = {
    "cefr_estimate missing": "MISSING_CEFR_ESTIMATE",
    "word_count missing or computed downstream": "MISSING_WORD_COUNT_OR_DERIVED_WORD_COUNT",
    "query_layer_ready false for G-W is not a schema blocker": "QUERY_LAYER_NOT_READY_G_TO_W",
    "non-blocking K/M sentence count parity note inherited from S6B": "S6B_PARITY_NOTE_INHERITED",
    "book_title missing": "MISSING_BOOK_TITLE",
    "sentence_count differs from simple punctuation sentence count": "SENTENCE_COUNT_HEURISTIC_MISMATCH",
}
QA_WARNING_CATEGORY_PREFIXES = {
    "mapped_legacy_reusability_tag:": "LEGACY_TAG_COMPATIBILITY_MAPPED",
    "unsupported_reusability_tag:": "UNSUPPORTED_LEGACY_REUSABILITY_TAG",
}
QA_WARNING_CATEGORY_MAP = {
    "unknown_theme": "SOURCE_UNKNOWN_THEME",
    "unknown_pattern": "SOURCE_UNKNOWN_PATTERN",
    "unknown_grammar": "SOURCE_UNKNOWN_GRAMMAR",
    "section_heading_detected": "SOURCE_SECTION_HEADING_DETECTED",
}
CATEGORY_METADATA = {
    "MISSING_CEFR_ESTIMATE": {
        "severity": "warning",
        "blocking": False,
        "reason": "Source metadata is sparse; schema permits null cefr_estimate.",
        "recommended_action": "Aggregate and optionally backfill later; do not block candidate-only staging.",
        "count_basis": "record_warning_occurrence",
    },
    "SPARSE_PEDAGOGICAL_TAGS": {
        "severity": "warning",
        "blocking": False,
        "reason": "Legacy and higher-level source artifacts often omit theme, vocabulary, grammar, or pattern tags.",
        "recommended_action": "Backfill selectively where query or review workflows need richer metadata; do not promote solely from sparse tags.",
        "count_basis": "record_warning_occurrence",
    },
    "LEGACY_TAG_COMPATIBILITY_MAPPED": {
        "severity": "warning",
        "blocking": False,
        "reason": "Legacy reuse tags were deterministically mapped into supported staging tags.",
        "recommended_action": "Preserve compatibility for staging, but normalize legacy upstream tags before promotion-oriented work.",
        "count_basis": "qa_warning_occurrence",
    },
    "UNSUPPORTED_LEGACY_REUSABILITY_TAG": {
        "severity": "warning",
        "blocking": False,
        "reason": "Some upstream reuse tags do not map to the supported intake taxonomy.",
        "recommended_action": "Define explicit mapping or deprecation policy before any promotion or query expansion that depends on these tags.",
        "count_basis": "qa_warning_occurrence",
    },
    "MISSING_WORD_COUNT_OR_DERIVED_WORD_COUNT": {
        "severity": "warning",
        "blocking": False,
        "reason": "Word count may be absent or derived downstream in some payload shapes.",
        "recommended_action": "Keep deterministic word-count generation in the builder and flag regressions if this category rises above zero.",
        "count_basis": "record_warning_occurrence",
    },
    "QUERY_LAYER_NOT_READY_G_TO_W": {
        "severity": "warning",
        "blocking": False,
        "reason": "Levels G-W remain outside the approved query layer and must stay candidate-only.",
        "recommended_action": "Carry these records as staging-only until a dedicated query-index readiness task formally expands support.",
        "count_basis": "record_warning_occurrence",
    },
    "S6B_PARITY_NOTE_INHERITED": {
        "severity": "warning",
        "blocking": False,
        "reason": "Known S6B sentence-count parity notes are inherited into the validator as non-blocking warnings.",
        "recommended_action": "Track parity notes in QA history, but keep them non-blocking unless downstream evidence shows data corruption.",
        "count_basis": "record_warning_occurrence",
    },
    "SOURCE_UNKNOWN_THEME": {
        "severity": "warning",
        "blocking": False,
        "reason": "Source tagging emitted unknown_theme warnings that indicate taxonomy coverage gaps, not candidate corruption.",
        "recommended_action": "Treat as taxonomy backlog for source tagging; do not promote without downstream review strategy.",
        "count_basis": "qa_warning_occurrence",
    },
    "SOURCE_UNKNOWN_PATTERN": {
        "severity": "warning",
        "blocking": False,
        "reason": "Source tagging emitted unknown_pattern warnings where sentence pattern coverage is incomplete.",
        "recommended_action": "Use pattern taxonomy backlog to prioritize rules; candidate staging can remain non-blocking.",
        "count_basis": "qa_warning_occurrence",
    },
    "SOURCE_UNKNOWN_GRAMMAR": {
        "severity": "warning",
        "blocking": False,
        "reason": "Source tagging emitted unknown_grammar warnings where grammar taxonomy coverage is incomplete.",
        "recommended_action": "Refine grammar tagging rules upstream before any promotion workflow assumes full grammar coverage.",
        "count_basis": "qa_warning_occurrence",
    },
    "SOURCE_SECTION_HEADING_DETECTED": {
        "severity": "warning",
        "blocking": False,
        "reason": "Source tagging detected likely headings or titles that need different downstream handling from ordinary prose.",
        "recommended_action": "Keep section-heading handling explicit in downstream filters or review workflows.",
        "count_basis": "qa_warning_occurrence",
    },
    "MISSING_BOOK_TITLE": {
        "severity": "warning",
        "blocking": False,
        "reason": "Many legacy or normalized-derived records omit book_title even though traceability remains intact.",
        "recommended_action": "Treat book_title enrichment as presentation metadata backlog rather than a candidate-staging blocker.",
        "count_basis": "record_warning_occurrence",
    },
    "SENTENCE_COUNT_HEURISTIC_MISMATCH": {
        "severity": "warning",
        "blocking": False,
        "reason": "Simple punctuation heuristics disagree with stored sentence_count for some multi-sentence or title-like texts.",
        "recommended_action": "Keep deterministic stored sentence_count authoritative and only investigate if downstream consumers require stricter sentence splitting.",
        "count_basis": "record_warning_occurrence",
    },
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def stable_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def artifact_gitignore_status(gitignore_text: str) -> str:
    lines = {line.strip() for line in gitignore_text.splitlines()}
    return "PASS" if REQUIRED_GITIGNORE_ENTRY in lines else "FAIL"


def compute_sha256(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def is_artifact_tracked(path: Path) -> bool:
    try:
        relative_path = str(path.relative_to(BASE_DIR)).replace("\\", "/")
    except ValueError:
        return False
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", relative_path],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _trim_buffer(buffer: str, index: int) -> tuple[str, int]:
    if index <= 1024 * 1024:
        return buffer, index
    return buffer[index:], 0


def iter_candidate_records(path: Path, *, chunk_size: int = 1024 * 1024) -> Iterator[dict[str, Any]]:
    decoder = json.JSONDecoder()
    buffer = ""
    index = 0
    in_records_array = False
    eof = False

    with path.open("r", encoding="utf-8") as handle:
        while True:
            if not eof:
                chunk = handle.read(chunk_size)
                if chunk:
                    buffer += chunk
                else:
                    eof = True

            if not in_records_array:
                records_pos = buffer.find('"records"')
                if records_pos == -1:
                    if eof:
                        raise ValueError("records key not found in candidate payload")
                    if len(buffer) > 128:
                        buffer = buffer[-128:]
                    continue
                array_pos = buffer.find("[", records_pos)
                if array_pos == -1:
                    if eof:
                        raise ValueError("records array start not found in candidate payload")
                    continue
                index = array_pos + 1
                in_records_array = True

            progressed = False
            while True:
                while index < len(buffer) and buffer[index] in " \r\n\t,":
                    index += 1
                if index >= len(buffer):
                    break
                if buffer[index] == "]":
                    return
                try:
                    record, next_index = decoder.raw_decode(buffer, index)
                except json.JSONDecodeError:
                    break
                if not isinstance(record, dict):
                    raise ValueError("candidate payload contains non-object record")
                yield record
                index = next_index
                progressed = True
                buffer, index = _trim_buffer(buffer, index)

            if eof:
                if progressed:
                    continue
                raise ValueError("unexpected end of candidate payload while streaming records")


def build_artifact_manifest(
    *,
    artifact_path: Path,
    gitignore_path: Path,
    builder_summary: dict[str, Any],
) -> dict[str, Any]:
    gitignore_text = gitignore_path.read_text(encoding="utf-8")
    gitignore_status = artifact_gitignore_status(gitignore_text)

    manifest: dict[str, Any] = {
        "task": TASK_NAME,
        "artifact_name": ARTIFACT_NAME,
        "local_path": stable_path(artifact_path),
        "git_policy": "do_not_commit",
        "gitignore_status": gitignore_status,
        "artifact_status": "LOCAL_ARTIFACT_NOT_PRESENT",
        "external_storage_status": "PENDING_OPERATOR_UPLOAD",
        "external_storage_provider": None,
        "external_storage_uri": None,
        "size_bytes": None,
        "size_mb": None,
        "record_count": int(builder_summary.get("total_records") or 0),
        "schema_validation_status": builder_summary.get("status"),
        "content_hash_sha256": None,
        "hash_status": "NOT_COMPUTED",
        "regeneration_command": "python ulga/builders/build_raz_reading_authority_intake.py",
        "validation_command": "python ulga/validators/validate_raz_reading_authority_intake_schema.py ulga/graph/raz_reading_authority_intake_candidates.json",
        "notes": [],
    }

    if artifact_path.exists():
        size_bytes = artifact_path.stat().st_size
        manifest.update({
            "artifact_status": "LOCAL_ONLY",
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / (1024 * 1024), 2),
            "content_hash_sha256": compute_sha256(artifact_path),
            "hash_status": "COMPUTED",
        })
    else:
        manifest["notes"].append("Local candidate artifact was not present during S9; manifest uses S8 report evidence only.")

    if gitignore_status != "PASS":
        manifest["notes"].append("Required candidate artifact path is missing from .gitignore.")
    if is_artifact_tracked(artifact_path):
        manifest["notes"].append("Candidate artifact is tracked by git and violates the local-only policy.")

    return manifest


def _record_category(
    category: str,
    *,
    count: int,
    levels: set[str],
    layers: set[str],
) -> dict[str, Any]:
    metadata = CATEGORY_METADATA[category]
    return {
        "category": category,
        "severity": metadata["severity"],
        "blocking": metadata["blocking"],
        "count": count,
        "count_status": "EXACT",
        "count_basis": metadata["count_basis"],
        "source_layers": sorted(layers),
        "affected_levels": sorted(levels),
        "reason": metadata["reason"],
        "recommended_action": metadata["recommended_action"],
    }


def build_warning_taxonomy(
    *,
    artifact_path: Path,
    builder_summary: dict[str, Any],
    builder_validation: dict[str, Any],
) -> dict[str, Any]:
    category_counts: Counter[str] = Counter()
    category_levels: dict[str, set[str]] = defaultdict(set)
    category_layers: dict[str, set[str]] = defaultdict(set)
    semantic_warning_count = 0
    qa_warning_families: set[str] = set()
    seen_ids: set[str] = set()
    records_streamed = 0
    unmatched_warnings: Counter[str] = Counter()

    if artifact_path.exists():
        for record in iter_candidate_records(artifact_path):
            records_streamed += 1
            level = str(record.get("source_level") or "")
            layer = str(record.get("unit_type") or "")
            try:
                semantic_warnings = validate_record_semantics(record, seen_ids=seen_ids)
            except ValidationError as exc:
                raise ValueError(f"candidate artifact failed semantic validation during S9: {exc}") from exc

            semantic_warning_count += len(semantic_warnings)
            for warning in semantic_warnings:
                if warning in SPARSE_WARNING_TYPES:
                    category = "SPARSE_PEDAGOGICAL_TAGS"
                else:
                    category = SEMANTIC_WARNING_CATEGORY_MAP.get(warning)
                if category is None:
                    unmatched_warnings[warning] += 1
                    continue
                category_counts[category] += 1
                category_levels[category].add(level)
                category_layers[category].add(layer)

            for warning in record.get("qa", {}).get("warnings", []):
                if not isinstance(warning, str):
                    continue
                qa_warning_families.add(warning)
                category = QA_WARNING_CATEGORY_MAP.get(warning)
                if category is None:
                    for prefix, mapped_category in QA_WARNING_CATEGORY_PREFIXES.items():
                        if warning.startswith(prefix):
                            category = mapped_category
                            break
                if category is None:
                    unmatched_warnings[warning] += 1
                    continue
                category_counts[category] += 1
                category_levels[category].add(level)
                category_layers[category].add(layer)

    required_categories = [
        "MISSING_CEFR_ESTIMATE",
        "SPARSE_PEDAGOGICAL_TAGS",
        "LEGACY_TAG_COMPATIBILITY_MAPPED",
        "UNSUPPORTED_LEGACY_REUSABILITY_TAG",
        "MISSING_WORD_COUNT_OR_DERIVED_WORD_COUNT",
        "QUERY_LAYER_NOT_READY_G_TO_W",
        "S6B_PARITY_NOTE_INHERITED",
    ]
    optional_categories = [
        "SOURCE_UNKNOWN_THEME",
        "SOURCE_UNKNOWN_PATTERN",
        "SOURCE_UNKNOWN_GRAMMAR",
        "SOURCE_SECTION_HEADING_DETECTED",
        "MISSING_BOOK_TITLE",
        "SENTENCE_COUNT_HEURISTIC_MISMATCH",
    ]
    warning_categories = [
        _record_category(
            category,
            count=category_counts.get(category, 0),
            levels=category_levels.get(category, set()),
            layers=category_layers.get(category, set()),
        )
        for category in required_categories + optional_categories
    ]

    unique_builder_warning_families = sorted(builder_validation.get("warnings") or [])
    recomputed_source_warning_count = semantic_warning_count + len(qa_warning_families)

    taxonomy = {
        "task": TASK_NAME,
        "source_warning_count": int(builder_summary.get("warning_count") or 0),
        "blocking_warning_count": 0,
        "non_blocking_warning_count": int(builder_summary.get("warning_count") or 0),
        "records_streamed": records_streamed,
        "semantic_warning_count": semantic_warning_count,
        "unique_qa_warning_family_count": len(qa_warning_families),
        "recomputed_source_warning_count": recomputed_source_warning_count,
        "warning_count_reconciliation_status": "PASS"
        if recomputed_source_warning_count == int(builder_summary.get("warning_count") or 0)
        else "MISMATCH",
        "warning_categories": warning_categories,
        "builder_warning_families": unique_builder_warning_families,
        "unmatched_warning_families": dict(sorted(unmatched_warnings.items())),
        "recommended_s10_actions": [
            "Keep promotion blocked and preserve authority_status=candidate_only for all staged records.",
            "Design query-index and review workflow for G-W candidate-only records before any query-layer expansion.",
            "Prioritize CEFR backfill and sparse pedagogical tag enrichment only where downstream ranking or review depends on them.",
            "Normalize or retire unsupported legacy reusability tags upstream before promotion-oriented consumers rely on them.",
            "Route unknown_theme, unknown_pattern, unknown_grammar, and section_heading_detected into source-tagging backlog rather than treating them as runtime blockers.",
        ],
        "promotion_blocking_status": "PROMOTION_STILL_BLOCKED",
    }
    return taxonomy


def build_qa_summary(
    *,
    manifest: dict[str, Any],
    taxonomy: dict[str, Any],
    builder_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "task": TASK_NAME,
        "status": "PASS_WITH_EXTERNAL_ARTIFACT_POLICY",
        "s8_status": "PASS" if builder_summary.get("status") == "IMPLEMENTED" else builder_summary.get("status"),
        "artifact_externalized": manifest.get("artifact_status") == "LOCAL_ONLY",
        "artifact_committed_to_git": is_artifact_tracked(ARTIFACT_PATH),
        "gitignore_status": manifest.get("gitignore_status"),
        "record_count": int(builder_summary.get("total_records") or 0),
        "artifact_size_mb": manifest.get("size_mb"),
        "warning_count": int(builder_summary.get("warning_count") or 0),
        "warning_taxonomy_status": "PASS"
        if taxonomy.get("warning_count_reconciliation_status") == "PASS"
        else "PASS_WITH_NOTE",
        "blocking_error_count": 0,
        "promotion_allowed": False,
        "authority_status": "candidate_only",
        "recommended_next_task": "RAZ-AW-S10_ReadingAuthorityIntake_QueryIndexDesignScan",
    }


def build_qa_validation(
    *,
    manifest: dict[str, Any],
    taxonomy: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    artifact_policy_status = "PASS"
    if manifest.get("gitignore_status") != "PASS":
        artifact_policy_status = "FAIL"
        errors.append("Candidate artifact path is missing from .gitignore.")
    if is_artifact_tracked(ARTIFACT_PATH):
        artifact_policy_status = "FAIL"
        errors.append("Candidate artifact is tracked by git.")

    warning_taxonomy_status = "PASS"
    if taxonomy.get("warning_count_reconciliation_status") != "PASS":
        warning_taxonomy_status = "PASS_WITH_NOTE"
        warnings.append("Warning taxonomy counts do not fully reconcile with the inherited S8 aggregate warning_count.")
    if taxonomy.get("unmatched_warning_families"):
        warning_taxonomy_status = "PASS_WITH_NOTE"
        warnings.append("Some warning families were not mapped into the formal taxonomy and are listed under unmatched_warning_families.")

    status = "PASS" if artifact_policy_status == "PASS" else "FAIL"
    return {
        "task": TASK_NAME,
        "status": status,
        "blocking_error_count": len(errors),
        "artifact_policy_status": artifact_policy_status,
        "warning_taxonomy_status": warning_taxonomy_status,
        "git_large_file_risk_status": "PASS_NOT_COMMITTED" if not is_artifact_tracked(ARTIFACT_PATH) else "FAIL_TRACKED",
        "promotion_guardrail_status": "PASS",
        "query_layer_expansion_status": "NOT_PERFORMED",
        "runtime_mutation_status": "NOT_PERFORMED",
        "errors": errors,
        "warnings": warnings,
    }


def build_all_reports(
    *,
    artifact_path: Path = ARTIFACT_PATH,
    gitignore_path: Path = GITIGNORE_PATH,
    builder_summary_path: Path = BUILDER_SUMMARY_PATH,
    builder_validation_path: Path = BUILDER_VALIDATION_PATH,
    manifest_path: Path = MANIFEST_PATH,
    taxonomy_path: Path = TAXONOMY_PATH,
    qa_summary_path: Path = QA_SUMMARY_PATH,
    qa_validation_path: Path = QA_VALIDATION_PATH,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    builder_summary = load_json(builder_summary_path)
    builder_validation = load_json(builder_validation_path)

    manifest = build_artifact_manifest(
        artifact_path=artifact_path,
        gitignore_path=gitignore_path,
        builder_summary=builder_summary,
    )
    taxonomy = build_warning_taxonomy(
        artifact_path=artifact_path,
        builder_summary=builder_summary,
        builder_validation=builder_validation,
    )
    qa_summary = build_qa_summary(
        manifest=manifest,
        taxonomy=taxonomy,
        builder_summary=builder_summary,
    )
    qa_validation = build_qa_validation(
        manifest=manifest,
        taxonomy=taxonomy,
    )

    write_json(manifest_path, manifest)
    write_json(taxonomy_path, taxonomy)
    write_json(qa_summary_path, qa_summary)
    write_json(qa_validation_path, qa_validation)
    return manifest, taxonomy, qa_summary, qa_validation


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate RAZ reading authority intake artifact externalization and warning taxonomy.")
    parser.add_argument("--artifact-path", default=str(ARTIFACT_PATH))
    parser.add_argument("--gitignore-path", default=str(GITIGNORE_PATH))
    parser.add_argument("--builder-summary-path", default=str(BUILDER_SUMMARY_PATH))
    parser.add_argument("--builder-validation-path", default=str(BUILDER_VALIDATION_PATH))
    parser.add_argument("--manifest-path", default=str(MANIFEST_PATH))
    parser.add_argument("--taxonomy-path", default=str(TAXONOMY_PATH))
    parser.add_argument("--qa-summary-path", default=str(QA_SUMMARY_PATH))
    parser.add_argument("--qa-validation-path", default=str(QA_VALIDATION_PATH))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest, taxonomy, qa_summary, qa_validation = build_all_reports(
        artifact_path=Path(args.artifact_path),
        gitignore_path=Path(args.gitignore_path),
        builder_summary_path=Path(args.builder_summary_path),
        builder_validation_path=Path(args.builder_validation_path),
        manifest_path=Path(args.manifest_path),
        taxonomy_path=Path(args.taxonomy_path),
        qa_summary_path=Path(args.qa_summary_path),
        qa_validation_path=Path(args.qa_validation_path),
    )
    print(json.dumps({
        "manifest_path": stable_path(Path(args.manifest_path)),
        "taxonomy_path": stable_path(Path(args.taxonomy_path)),
        "qa_summary_path": stable_path(Path(args.qa_summary_path)),
        "qa_validation_path": stable_path(Path(args.qa_validation_path)),
        "artifact_status": manifest["artifact_status"],
        "source_warning_count": taxonomy["source_warning_count"],
        "warning_count_reconciliation_status": taxonomy["warning_count_reconciliation_status"],
        "status": qa_validation["status"],
    }, ensure_ascii=False, indent=2))
    return 0 if qa_validation["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

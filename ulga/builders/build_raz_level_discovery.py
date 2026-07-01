from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[2]
RAW_ROOT = BASE_DIR / "raz_output_jsons"
DERIVED_ROOT = RAW_ROOT / "derived"
INVENTORY_PATH = BASE_DIR / "ulga" / "graph" / "raz_level_discovery_inventory.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "raz_level_discovery_summary.json"
QUERY_LAYER_POLICY_PATH = BASE_DIR / "ulga" / "policies" / "raz_seed_query_layer_policy.json"

LEVEL_DIR_PATTERN = re.compile(r"^Level_(.+)$")
VALID_LEVEL_PATTERN = re.compile(r"^[A-Z]$")

READY_FOR_SENTENCE_PIPELINE = "READY_FOR_SENTENCE_PIPELINE"
READY_FOR_PAGE_UNIT_PIPELINE = "READY_FOR_PAGE_UNIT_PIPELINE"
READY_FOR_REUSE_UNIT_PIPELINE = "READY_FOR_REUSE_UNIT_PIPELINE"
PARTIAL_SOURCE_ONLY = "PARTIAL_SOURCE_ONLY"
MISSING_REQUIRED_INPUT = "MISSING_REQUIRED_INPUT"
INVALID_FORMAT = "INVALID_FORMAT"
SKIPPED_NO_DATA = "SKIPPED_NO_DATA"

ALL_VALID_LEVEL_CODES = tuple(chr(code) for code in range(ord("A"), ord("Z") + 1))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def stable_path(path: Path) -> str:
    try:
        return path.relative_to(BASE_DIR).as_posix()
    except ValueError:
        return path.as_posix()


def normalize_level_code(value: str | None) -> str | None:
    text = str(value or "").strip().upper()
    return text if VALID_LEVEL_PATTERN.fullmatch(text) else None


def is_valid_level_code(value: str | None) -> bool:
    return normalize_level_code(value) is not None


def _count_jsonl(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def _count_json_array(path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"expected list payload in {path}")
    return len(payload)


def _count_json_records(path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return len(payload["records"])
    raise ValueError(f"expected list payload or object.records list in {path}")


def _count_unit_typed_records(path: Path, unit_type: str) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict) and isinstance(payload.get("records"), list):
        records = payload["records"]
    else:
        raise ValueError(f"expected list payload or object.records list in {path}")
    return sum(1 for record in records if isinstance(record, dict) and record.get("unit_type") == unit_type)


def _read_raw_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object payload in {path}")
    return payload


def _resolve_derived_candidates(*paths: Path) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def _status_from_evidence(
    *,
    invalid_format: bool,
    timeline_json_count: int,
    sentence_candidate_count: int,
    page_unit_count: int,
    reuse_unit_count: int,
    clean_summary_count: int,
    missing_artifacts: list[str],
) -> str:
    if invalid_format:
        return INVALID_FORMAT
    if reuse_unit_count > 0 and page_unit_count > 0 and sentence_candidate_count > 0:
        return READY_FOR_REUSE_UNIT_PIPELINE
    if page_unit_count > 0 and sentence_candidate_count > 0:
        return READY_FOR_PAGE_UNIT_PIPELINE
    if sentence_candidate_count > 0:
        return READY_FOR_SENTENCE_PIPELINE
    if timeline_json_count > 0 or clean_summary_count > 0:
        return PARTIAL_SOURCE_ONLY
    if missing_artifacts:
        return MISSING_REQUIRED_INPUT
    return SKIPPED_NO_DATA


def _collect_level_names(raw_root: Path, derived_root: Path) -> list[str]:
    names: set[str] = set()
    for root in [raw_root, derived_root]:
        if not root.exists():
            continue
        for child in root.iterdir():
            if child.is_dir():
                match = LEVEL_DIR_PATTERN.fullmatch(child.name)
                if match:
                    names.add(match.group(1))
    return sorted(names, key=lambda value: (normalize_level_code(value) is None, normalize_level_code(value) or value))


def _make_empty_record(level_name: str) -> dict[str, Any]:
    normalized = normalize_level_code(level_name)
    return {
        "level": level_name,
        "normalized_level": normalized,
        "detected": False,
        "status": SKIPPED_NO_DATA if normalized else INVALID_FORMAT,
        "source_evidence": {
            "source_pdf_count": 0,
            "timeline_json_count": 0,
            "sentence_candidate_count": 0,
            "page_unit_count": 0,
            "reuse_unit_count": 0,
            "clean_summary_count": 0,
            "clean_summary_exists": False,
            "normalized_sentence_count": 0,
            "normalized_page_unit_count": 0,
            "normalized_reuse_unit_count": 0,
            "enriched_sentence_count": 0,
            "enriched_page_unit_count": 0,
            "enriched_reuse_unit_count": 0,
        },
        "available_artifacts": [],
        "missing_artifacts": [],
        "skip_reasons": [],
        "pipeline_capabilities": {
            "can_build_sentence_candidates": False,
            "can_build_page_units": False,
            "can_build_reuse_units": False,
            "can_validate_summary": False,
        },
        "query_layer_approved": False,
        "query_layer_ready": False,
        "authority_status": "candidate_only",
        "promotion_allowed": False,
        "warnings": [],
    }


def resolve_query_layer_policy_path(
    raw_root: Path = RAW_ROOT,
    derived_root: Path = DERIVED_ROOT,
    fallback_path: Path = QUERY_LAYER_POLICY_PATH,
) -> Path:
    candidate_bases = [
        derived_root.parent.parent if derived_root.parent.name == "raz_output_jsons" else None,
        raw_root.parent if raw_root.name == "raz_output_jsons" else None,
        fallback_path.parents[2],
    ]
    for base in candidate_bases:
        if base is None:
            continue
        candidate = base / "ulga" / "policies" / fallback_path.name
        if candidate.exists():
            return candidate
    return fallback_path


def load_query_layer_policy_levels(policy_path: Path = QUERY_LAYER_POLICY_PATH) -> set[str]:
    if not policy_path.exists():
        return set()
    payload = json.loads(policy_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object payload in {policy_path}")
    levels = payload.get("approved_levels") or []
    if not isinstance(levels, list):
        raise ValueError(f"approved_levels must be a list in {policy_path}")
    return {level for level in (normalize_level_code(value) for value in levels) if level}


def inspect_level(
    level_name: str,
    raw_root: Path = RAW_ROOT,
    derived_root: Path = DERIVED_ROOT,
    query_layer_policy_levels: set[str] | None = None,
) -> dict[str, Any]:
    record = _make_empty_record(level_name)
    normalized = record["normalized_level"]
    raw_level_dir = raw_root / f"Level_{level_name}"
    derived_level_dir = derived_root / f"Level_{level_name}"
    source_pdf_dir = BASE_DIR / "input" / "pdf" / str(level_name).lower()

    if normalized is None:
        record["detected"] = raw_level_dir.exists() or derived_level_dir.exists()
        record["skip_reasons"].append(f"invalid_level_code:{level_name}")
        record["warnings"].append("level_name_failed_validation")
        return record

    evidence = record["source_evidence"]
    available_artifacts: list[str] = []
    missing_artifacts: list[str] = []
    warnings: list[str] = []
    skip_reasons: list[str] = []

    evidence["source_pdf_count"] = len(list(source_pdf_dir.glob("*.pdf"))) if source_pdf_dir.exists() else 0
    if evidence["source_pdf_count"] > 0:
        available_artifacts.append("source_pdf")

    timeline_files = sorted(raw_level_dir.glob(f"raz_{normalized}_*_audio_timeline_extract.json")) if raw_level_dir.exists() else []
    evidence["timeline_json_count"] = len(timeline_files)
    if timeline_files:
        available_artifacts.append("timeline_json")
    else:
        missing_artifacts.append("timeline_json")

    invalid_format = False
    for path in timeline_files:
        try:
            payload = _read_raw_payload(path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            invalid_format = True
            warnings.append(f"malformed_raw_json:{stable_path(path)}")
            skip_reasons.append(f"malformed_raw_json:{path.name}")
            continue

        metadata = payload.get("book_metadata") or {}
        metadata_level = normalize_level_code(metadata.get("level"))
        if metadata_level not in {None, normalized}:
            invalid_format = True
            warnings.append(f"metadata_level_mismatch:{stable_path(path)}")
            skip_reasons.append(f"metadata_level_mismatch:{path.name}")

        evidence["sentence_candidate_count"] += len(payload.get("sentence_candidates") or [])
        evidence["page_unit_count"] += len(payload.get("page_units") or [])
        evidence["reuse_unit_count"] += len(payload.get("reuse_unit_candidates") or [])
        if payload.get("clean_summary") is not None:
            evidence["clean_summary_count"] += 1

    if evidence["sentence_candidate_count"] > 0:
        available_artifacts.append("sentence_candidates")
    else:
        missing_artifacts.append("sentence_candidates")

    if evidence["page_unit_count"] > 0:
        available_artifacts.append("page_units")
    else:
        missing_artifacts.append("page_units")

    if evidence["reuse_unit_count"] > 0:
        available_artifacts.append("reuse_unit_candidates")
    else:
        missing_artifacts.append("reuse_unit_candidates")

    evidence["clean_summary_exists"] = evidence["clean_summary_count"] > 0
    if evidence["clean_summary_exists"]:
        available_artifacts.append("clean_summary")
    else:
        missing_artifacts.append("clean_summary")

    derived_specs = [
        (
            "normalized_sentence_count",
            _resolve_derived_candidates(
                derived_level_dir / "normalized" / f"raz_{normalized}_sentence_normalized.jsonl",
                derived_level_dir / "normalized" / f"raz_{normalized}_normalized_sentences.json",
            ),
            None,
            "normalized_sentence",
        ),
        (
            "normalized_page_unit_count",
            _resolve_derived_candidates(
                derived_level_dir / "normalized" / f"raz_{normalized}_page_unit_normalized.json",
                derived_level_dir / "normalized" / f"raz_{normalized}_normalized_page_units.json",
            ),
            _count_json_records,
            "normalized_page_unit",
        ),
        (
            "normalized_reuse_unit_count",
            _resolve_derived_candidates(
                derived_level_dir / "normalized" / f"raz_{normalized}_reuse_unit_normalized.json",
                derived_level_dir / "normalized" / f"raz_{normalized}_normalized_reuse_units.json",
            ),
            _count_json_records,
            "normalized_reuse_unit",
        ),
        (
            "enriched_sentence_count",
            _resolve_derived_candidates(
                derived_level_dir / "enriched" / f"raz_{normalized}_sentence_enriched.jsonl",
                derived_level_dir / "enriched" / f"raz_{normalized}_enriched_sentences.json",
            ),
            None,
            "enriched_sentence",
        ),
        (
            "enriched_page_unit_count",
            _resolve_derived_candidates(
                derived_level_dir / "enriched" / f"raz_{normalized}_page_unit_enriched.json",
                derived_level_dir / "enriched" / f"raz_{normalized}_enriched_units.json",
            ),
            None,
            "enriched_page_unit",
        ),
        (
            "enriched_reuse_unit_count",
            _resolve_derived_candidates(
                derived_level_dir / "enriched" / f"raz_{normalized}_reuse_unit_enriched.json",
                derived_level_dir / "enriched" / f"raz_{normalized}_enriched_units.json",
            ),
            None,
            "enriched_reuse_unit",
        ),
    ]

    for evidence_key, path, counter, artifact_name in derived_specs:
        if path is None or not path.exists():
            missing_artifacts.append(artifact_name)
            continue
        try:
            if artifact_name == "normalized_sentence":
                evidence[evidence_key] = _count_jsonl(path) if path.suffix == ".jsonl" else _count_json_records(path)
            elif artifact_name == "enriched_sentence":
                evidence[evidence_key] = _count_jsonl(path) if path.suffix == ".jsonl" else _count_json_records(path)
            elif artifact_name == "enriched_page_unit" and path.name.endswith("_enriched_units.json"):
                evidence[evidence_key] = _count_unit_typed_records(path, "page_unit")
            elif artifact_name == "enriched_reuse_unit" and path.name.endswith("_enriched_units.json"):
                evidence[evidence_key] = _count_unit_typed_records(path, "reuse_unit")
            elif artifact_name in {"enriched_page_unit", "enriched_reuse_unit"}:
                evidence[evidence_key] = _count_json_records(path)
            elif counter is not None:
                evidence[evidence_key] = counter(path)
            else:
                raise ValueError(f"no counter configured for {artifact_name}: {path}")
            available_artifacts.append(artifact_name)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            invalid_format = True
            warnings.append(f"malformed_derived_artifact:{stable_path(path)}")
            skip_reasons.append(f"malformed_derived_artifact:{path.name}")
            missing_artifacts.append(artifact_name)

    if evidence["timeline_json_count"] == 0 and any(evidence[key] > 0 for key in ["enriched_sentence_count", "enriched_page_unit_count", "enriched_reuse_unit_count"]):
        warnings.append("derived_artifacts_without_raw_timeline")
        skip_reasons.append("derived_artifacts_without_raw_timeline")

    record["detected"] = bool(
        timeline_files
        or raw_level_dir.exists()
        or derived_level_dir.exists()
        or evidence["source_pdf_count"] > 0
        or any(evidence[key] > 0 for key in evidence if key.endswith("_count"))
    )
    record["available_artifacts"] = sorted(set(available_artifacts))
    record["missing_artifacts"] = sorted(set(missing_artifacts))
    record["skip_reasons"] = sorted(set(skip_reasons))
    record["warnings"] = sorted(set(warnings))
    record["pipeline_capabilities"] = {
        "can_build_sentence_candidates": evidence["timeline_json_count"] > 0,
        "can_build_page_units": evidence["timeline_json_count"] > 0 and evidence["sentence_candidate_count"] > 0,
        "can_build_reuse_units": evidence["timeline_json_count"] > 0 and evidence["page_unit_count"] > 0,
        "can_validate_summary": evidence["clean_summary_exists"],
    }
    record["status"] = _status_from_evidence(
        invalid_format=invalid_format,
        timeline_json_count=evidence["timeline_json_count"],
        sentence_candidate_count=evidence["sentence_candidate_count"],
        page_unit_count=evidence["page_unit_count"],
        reuse_unit_count=evidence["reuse_unit_count"],
        clean_summary_count=evidence["clean_summary_count"],
        missing_artifacts=record["missing_artifacts"],
    )
    policy_levels = query_layer_policy_levels if query_layer_policy_levels is not None else load_query_layer_policy_levels()
    enriched_artifact_names = {"enriched_sentence", "enriched_page_unit", "enriched_reuse_unit"}
    record["query_layer_approved"] = normalized in policy_levels
    record["query_layer_ready"] = bool(
        record["query_layer_approved"]
        and enriched_artifact_names <= set(record["available_artifacts"])
        and not (enriched_artifact_names & set(record["missing_artifacts"]))
    )
    if record["status"] in {MISSING_REQUIRED_INPUT, SKIPPED_NO_DATA} and not record["skip_reasons"]:
        if record["status"] == MISSING_REQUIRED_INPUT:
            record["skip_reasons"].append("required_input_not_found")
        else:
            record["skip_reasons"].append("no_data_detected")
    return record


def discover_raz_levels(raw_root: Path = RAW_ROOT, derived_root: Path = DERIVED_ROOT) -> list[dict[str, Any]]:
    level_names = _collect_level_names(raw_root, derived_root)
    policy_levels = load_query_layer_policy_levels(resolve_query_layer_policy_path(raw_root=raw_root, derived_root=derived_root))
    records = [
        inspect_level(
            level_name,
            raw_root=raw_root,
            derived_root=derived_root,
            query_layer_policy_levels=policy_levels,
        )
        for level_name in level_names
    ]
    records.sort(key=lambda item: (item["normalized_level"] is None, item["normalized_level"] or item["level"]))
    return records


def discover_queryable_levels(
    records: list[dict[str, Any]] | None = None,
    raw_root: Path = RAW_ROOT,
    derived_root: Path = DERIVED_ROOT,
) -> list[str]:
    rows = records if records is not None else discover_raz_levels(raw_root=raw_root, derived_root=derived_root)
    levels: list[str] = []
    for row in rows:
        level = row.get("normalized_level")
        if not level:
            continue
        if row.get("query_layer_ready") is True:
            levels.append(level)
    return sorted(set(levels))


def build_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(record["status"] for record in records)
    levels_by_status: dict[str, list[str]] = {}
    warnings: list[str] = []

    for record in records:
        label = record["normalized_level"] or record["level"]
        levels_by_status.setdefault(record["status"], []).append(label)
        warnings.extend(record.get("warnings", []))

    ready_levels = [
        record
        for record in records
        if record["status"] in {
            READY_FOR_SENTENCE_PIPELINE,
            READY_FOR_PAGE_UNIT_PIPELINE,
            READY_FOR_REUSE_UNIT_PIPELINE,
        }
    ]
    partial_levels = [record for record in records if record["status"] == PARTIAL_SOURCE_ONLY]
    skipped_levels = [record for record in records if record["status"] == SKIPPED_NO_DATA]
    invalid_levels = [record for record in records if record["status"] == INVALID_FORMAT]

    summary = {
        "task": "RAZ-S6D_LevelExpansionDynamicDiscovery_Implementation",
        "total_detected_levels": len(records),
        "ready_level_count": len(ready_levels),
        "skipped_level_count": len(skipped_levels),
        "partial_level_count": len(partial_levels),
        "invalid_level_count": len(invalid_levels),
        "missing_required_input_count": counts.get(MISSING_REQUIRED_INPUT, 0),
        "levels_by_status": {status: sorted(levels) for status, levels in sorted(levels_by_status.items())},
        "levels_ready_for_sentence_pipeline": sorted(
            record["normalized_level"]
            for record in records
            if record["normalized_level"]
            and record["status"] in {READY_FOR_SENTENCE_PIPELINE, READY_FOR_PAGE_UNIT_PIPELINE, READY_FOR_REUSE_UNIT_PIPELINE}
        ),
        "levels_ready_for_page_unit_pipeline": sorted(
            record["normalized_level"]
            for record in records
            if record["normalized_level"]
            and record["status"] in {READY_FOR_PAGE_UNIT_PIPELINE, READY_FOR_REUSE_UNIT_PIPELINE}
        ),
        "levels_ready_for_reuse_unit_pipeline": sorted(
            record["normalized_level"]
            for record in records
            if record["normalized_level"] and record["status"] == READY_FOR_REUSE_UNIT_PIPELINE
        ),
        "levels_query_layer_ready": sorted(
            record["normalized_level"]
            for record in records
            if record["normalized_level"] and record.get("query_layer_ready") is True
        ),
        "warnings": sorted(set(warnings)),
        "next_recommended_task": (
            "Route AUX-S6 builders/query layers through raz level discovery inventory."
            if ready_levels
            else "Restore at least one valid level with raw timeline evidence before AUX-S6 execution."
        ),
    }
    return summary


def build_and_write_artifacts(raw_root: Path = RAW_ROOT, derived_root: Path = DERIVED_ROOT) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records = discover_raz_levels(raw_root=raw_root, derived_root=derived_root)
    summary = build_summary(records)
    write_json(INVENTORY_PATH, records)
    write_json(SUMMARY_PATH, summary)
    return records, summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build deterministic RAZ level discovery inventory and summary artifacts.")
    parser.add_argument("--raw-root", default=str(RAW_ROOT), help="Root containing raw Level_* folders.")
    parser.add_argument("--derived-root", default=str(DERIVED_ROOT), help="Root containing derived Level_* folders.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    records, summary = build_and_write_artifacts(raw_root=Path(args.raw_root), derived_root=Path(args.derived_root))
    print(json.dumps({
        "inventory_path": stable_path(INVENTORY_PATH),
        "summary_path": stable_path(SUMMARY_PATH),
        "total_detected_levels": summary["total_detected_levels"],
        "ready_level_count": summary["ready_level_count"],
        "levels_ready_for_reuse_unit_pipeline": summary["levels_ready_for_reuse_unit_pipeline"],
    }, ensure_ascii=False, indent=2))
    return 0


__all__ = [
    "ALL_VALID_LEVEL_CODES",
    "BASE_DIR",
    "DERIVED_ROOT",
    "INVENTORY_PATH",
    "INVALID_FORMAT",
    "MISSING_REQUIRED_INPUT",
    "PARTIAL_SOURCE_ONLY",
    "RAW_ROOT",
    "READY_FOR_PAGE_UNIT_PIPELINE",
    "READY_FOR_REUSE_UNIT_PIPELINE",
    "READY_FOR_SENTENCE_PIPELINE",
    "SKIPPED_NO_DATA",
    "SUMMARY_PATH",
    "VALID_LEVEL_PATTERN",
    "build_and_write_artifacts",
    "build_summary",
    "discover_queryable_levels",
    "discover_raz_levels",
    "inspect_level",
    "is_valid_level_code",
    "normalize_level_code",
]


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[2]

INDEX_PATH = BASE_DIR / "ulga" / "graph" / "raz_reading_authority_intake_query_index.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "raz_reading_authority_intake_query_index_summary.json"
SOURCE_CANDIDATE_PATH = BASE_DIR / "ulga" / "graph" / "raz_reading_authority_intake_candidates.json"
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "raz_reading_authority_intake_query_index_readback_qa.json"

TASK_NAME = "RAZ-AW-S12_ReadingAuthorityIntake_QueryIndexReadbackQA"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def relative_path(path: Path) -> str:
    return path.relative_to(BASE_DIR).as_posix()


def classify_warning_groups(warnings: list[str]) -> dict[str, int]:
    counts = Counter()
    for warning in warnings:
        if "bridge/reading_authority/" in warning:
            counts["bridge_candidate_artifact"] += 1
        elif "raz_output_jsons/derived/" in warning:
            counts["derived_artifact"] += 1
        else:
            counts["other"] += 1
    return dict(sorted(counts.items()))


def analyze_source_candidate_payload(source_payload: Any) -> dict[str, Any]:
    records = source_payload.get("records", []) if isinstance(source_payload, dict) else []
    source_levels = Counter()
    missing_source_level = 0
    missing_reading_intake_id = 0
    for record in records:
        if not isinstance(record, dict):
            continue
        level = record.get("source_level") or record.get("normalized_level")
        if level:
            source_levels[str(level).strip().upper()] += 1
        else:
            missing_source_level += 1
        if not record.get("reading_intake_id"):
            missing_reading_intake_id += 1

    return {
        "record_count": len(records),
        "source_levels": dict(sorted(source_levels.items())),
        "missing_source_level_count": missing_source_level,
        "missing_reading_intake_id_count": missing_reading_intake_id,
    }


def analyze_index_payload(index_payload: dict[str, Any]) -> dict[str, Any]:
    items = index_payload.get("items", [])
    source_path_counter = Counter()
    unknown_source_path_counter = Counter()
    malformed_reusability_counter = Counter()
    missing_source_record_id_counter = Counter()

    promoted_count = 0
    generated_content_count = 0
    candidate_only_count = 0
    unknown_items = 0
    malformed_reusability_items = 0
    missing_source_record_id_items = 0

    for item in items:
        source_traceability = item.get("source_traceability") or {}
        source_path = str(source_traceability.get("source_path") or "")
        source_path_counter[source_path] += 1

        if item.get("promotion_status") == "promoted":
            promoted_count += 1
        if item.get("generated_content") is True:
            generated_content_count += 1
        if item.get("authority_status") == "candidate_only":
            candidate_only_count += 1

        if item.get("level") == "UNKNOWN":
            unknown_items += 1
            unknown_source_path_counter[source_path] += 1

        if not source_traceability.get("source_record_id"):
            missing_source_record_id_items += 1
            missing_source_record_id_counter[source_path] += 1

        for tag in (item.get("query_tags") or {}).get("reusability_tags", []):
            if isinstance(tag, str) and ("{" in tag or "}" in tag):
                malformed_reusability_items += 1
                malformed_reusability_counter[source_path] += 1
                break

    return {
        "total_items": len(items),
        "candidate_only_count": candidate_only_count,
        "promoted_count": promoted_count,
        "generated_content_count": generated_content_count,
        "unknown_items": unknown_items,
        "unknown_ratio": round((unknown_items / len(items)), 6) if items else 0.0,
        "malformed_reusability_items": malformed_reusability_items,
        "missing_source_record_id_items": missing_source_record_id_items,
        "top_source_paths": source_path_counter.most_common(10),
        "unknown_source_paths": unknown_source_path_counter.most_common(10),
        "malformed_reusability_items_by_source": malformed_reusability_counter.most_common(10),
        "missing_source_record_id_by_source": missing_source_record_id_counter.most_common(10),
    }


def build_findings(
    *,
    index_analysis: dict[str, Any],
    summary_payload: dict[str, Any],
    source_analysis: dict[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    if summary_payload.get("total_items") != index_analysis["total_items"]:
        findings.append(
            {
                "severity": "high",
                "code": "SUMMARY_TOTAL_MISMATCH",
                "message": "Summary total_items does not match index item count.",
                "details": {
                    "summary_total_items": summary_payload.get("total_items"),
                    "index_total_items": index_analysis["total_items"],
                },
            }
        )

    if (
        source_analysis["record_count"] > 0
        and index_analysis["unknown_source_paths"]
        and index_analysis["unknown_source_paths"][0][0] == relative_path(SOURCE_CANDIDATE_PATH)
        and index_analysis["unknown_source_paths"][0][1] == source_analysis["record_count"]
        and source_analysis["missing_source_level_count"] == 0
    ):
        findings.append(
            {
                "severity": "high",
                "code": "S10A_SOURCE_LEVELS_DROPPED",
                "message": "All S10A source candidates were indexed as UNKNOWN even though source levels exist.",
                "details": {
                    "source_path": relative_path(SOURCE_CANDIDATE_PATH),
                    "unknown_items_from_source": index_analysis["unknown_source_paths"][0][1],
                    "source_record_count": source_analysis["record_count"],
                    "source_levels_present": list(source_analysis["source_levels"].keys())[:10],
                },
            }
        )

    malformed_count = index_analysis["malformed_reusability_items"]
    if malformed_count:
        findings.append(
            {
                "severity": "high",
                "code": "MALFORMED_REUSABILITY_TAGS",
                "message": "Some reusability tags were serialized from dict-shaped metadata instead of normalized tag strings.",
                "details": {
                    "items_affected": malformed_count,
                    "sources": index_analysis["malformed_reusability_items_by_source"][:5],
                },
            }
        )

    missing_source_ids = dict(index_analysis["missing_source_record_id_by_source"])
    missing_from_s10a = missing_source_ids.get(relative_path(SOURCE_CANDIDATE_PATH), 0)
    if missing_from_s10a == source_analysis["record_count"] and missing_from_s10a > 0:
        findings.append(
            {
                "severity": "medium",
                "code": "SOURCE_RECORD_ID_NOT_PROPAGATED",
                "message": "S10A source records have stable reading_intake_id values, but the S11 index did not carry them into source_traceability.source_record_id.",
                "details": {
                    "source_path": relative_path(SOURCE_CANDIDATE_PATH),
                    "missing_source_record_id_count": missing_from_s10a,
                },
            }
        )

    warning_groups = classify_warning_groups(summary_payload.get("warnings", []))
    if warning_groups.get("derived_artifact", 0) > 0:
        findings.append(
            {
                "severity": "medium",
                "code": "WARNING_SCOPE_NOT_BRIDGE_ONLY",
                "message": "Readback warnings are not limited to bridge candidate artifacts; derived artifact warnings are also present.",
                "details": warning_groups,
            }
        )

    return findings


def audit_readback() -> dict[str, Any]:
    index_payload = load_json(INDEX_PATH)
    summary_payload = load_json(SUMMARY_PATH)
    source_payload = load_json(SOURCE_CANDIDATE_PATH) if SOURCE_CANDIDATE_PATH.exists() else {}

    index_analysis = analyze_index_payload(index_payload)
    source_analysis = analyze_source_candidate_payload(source_payload)
    findings = build_findings(
        index_analysis=index_analysis,
        summary_payload=summary_payload,
        source_analysis=source_analysis,
    )

    status = "PASS" if not findings else "FAIL"
    payload = {
        "task": TASK_NAME,
        "status": status,
        "index_path": relative_path(INDEX_PATH),
        "summary_path": relative_path(SUMMARY_PATH),
        "source_candidate_path": relative_path(SOURCE_CANDIDATE_PATH),
        "summary_status": summary_payload.get("status"),
        "warning_count": len(summary_payload.get("warnings", [])),
        "warning_groups": classify_warning_groups(summary_payload.get("warnings", [])),
        "index_analysis": index_analysis,
        "source_candidate_analysis": source_analysis,
        "findings": findings,
        "recommended_next_task": "RAZ-AW-S11_ReadingAuthorityIntake_QueryIndexBuilderPatch",
    }
    write_json(REPORT_PATH, payload)
    return payload


def main() -> int:
    result = audit_readback()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

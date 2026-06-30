from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[2]
INVENTORY_PATH = BASE_DIR / "ulga" / "graph" / "raz_level_discovery_inventory.json"
S6E_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "raz_level_discovery_downstream_integration_qa.json"
ALLOWLIST_PATH = BASE_DIR / "ulga" / "policies" / "raz_downstream_discovery_drift_allowlist.json"
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "raz_downstream_discovery_drift_validation.json"
SELF_RELATIVE_PATH = stable_self_path = "ulga/validators/validate_raz_downstream_discovery_drift.py"

TEXT_FILE_SUFFIXES = {".py", ".md"}
SCAN_ROOTS = ("tools", "ulga", "tests", "docs")
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", "raz_output_jsons", "input", "output"}

DISCOVERY_TOKENS = (
    "build_raz_level_discovery",
    "discover_queryable_levels(",
    "discover_raz_levels(",
    "raz_level_discovery_inventory.json",
)
REQUIRED_DISCOVERY_CONSUMERS = {
    "tools/raz_normalized_tagging_pipeline.py": (
        "build_raz_level_discovery",
        "discover_raz_levels(",
    ),
    "ulga/query/raz_reusable_content_seed_query_layer.py": (
        "build_raz_level_discovery",
        "discover_queryable_levels(",
    ),
    "ulga/validators/validate_raz_reusable_content_seed_query_layer.py": (
        "build_raz_level_discovery",
        "discover_queryable_levels(",
    ),
}

DIRECT_LEVEL_SCAN_REGEXES = (
    re.compile(r"""\b(?:glob|rglob)\(\s*f?["']Level_\*["']\s*\)"""),
)
FIXED_LEVEL_UNIVERSE_REGEXES = (
    re.compile(r"""\(\s*["']A["']\s*,\s*["']B["']\s*,\s*["']C["']\s*,\s*["']D["']\s*,\s*["']E["']\s*,\s*["']F["']\s*\)""", re.DOTALL),
    re.compile(r"""\[\s*["']A["']\s*,\s*["']B["']\s*,\s*["']C["']\s*,\s*["']D["']\s*,\s*["']E["']\s*,\s*["']F["']\s*\]""", re.DOTALL),
    re.compile(r"""\bfor\s+\w+\s+in\s+["']ABCDEF["']"""),
)
PATH_NAMING_REGEX = re.compile(r"""(?:raz_output_jsons/|derived/)?Level_\{?[A-Za-z_][^"'\n]*\}?""")
PROMOTION_TRUE_REGEXES = (
    re.compile(r"""promotion_allowed\s*=\s*true""", re.IGNORECASE),
    re.compile(r""""promotion_allowed"\s*:\s*true""", re.IGNORECASE),
    re.compile(r"""authority_promotion_allowed\s*=\s*true""", re.IGNORECASE),
    re.compile(r""""authority_promotion_allowed"\s*:\s*true""", re.IGNORECASE),
)

TASK_NAME = "RAZ-S6F_DownstreamDiscoveryDriftValidator_Implementation"


@dataclass(frozen=True)
class Finding:
    classification: str
    path: str
    line: int
    excerpt: str
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "path": self.path,
            "line": self.line,
            "excerpt": self.excerpt,
            "reason": self.reason,
        }


def stable_path(path: Path, base_dir: Path = BASE_DIR) -> str:
    try:
        return path.relative_to(base_dir).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_allowlist(allowlist_path: Path) -> dict[str, list[dict[str, Any]]]:
    if not allowlist_path.exists():
        return {"safe_single_level_utilities": [], "warning_legacy_references": []}
    payload = read_json(allowlist_path)
    if not isinstance(payload, dict):
        raise ValueError(f"allowlist must be an object: {allowlist_path}")
    return {
        "safe_single_level_utilities": list(payload.get("safe_single_level_utilities") or []),
        "warning_legacy_references": list(payload.get("warning_legacy_references") or []),
    }


def discover_scan_paths(base_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for root_name in SCAN_ROOTS:
        root = base_dir / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in TEXT_FILE_SUFFIXES:
                continue
            parts = set(path.parts)
            if parts & EXCLUDED_PARTS:
                continue
            rel = stable_path(path, base_dir).lower()
            if "raz" not in rel:
                continue
            paths.append(path)
    return sorted(set(paths), key=lambda item: stable_path(item, base_dir))


def line_number_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def compact_excerpt(text: str) -> str:
    return " ".join(text.strip().split())[:160]


def collect_regex_findings(
    *,
    text: str,
    path: str,
    regexes: tuple[re.Pattern[str], ...],
    classification: str,
    reason: str,
) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple[int, str]] = set()
    for regex in regexes:
        for match in regex.finditer(text):
            line = line_number_for_offset(text, match.start())
            excerpt = compact_excerpt(match.group(0))
            key = (line, excerpt)
            if key in seen:
                continue
            seen.add(key)
            findings.append(Finding(classification, path, line, excerpt, reason))
    findings.sort(key=lambda item: (item.path, item.line, item.excerpt))
    return findings


def file_kind(path: str) -> str:
    if path.startswith("tests/"):
        return "test"
    if path.endswith(".md"):
        return "doc"
    return "active"


def file_has_discovery_consumption(text: str) -> bool:
    return any(token in text for token in DISCOVERY_TOKENS)


def classify_file(
    *,
    relative_path: str,
    text: str,
    allowlist: dict[str, list[dict[str, Any]]],
) -> dict[str, list[Finding]]:
    buckets: dict[str, list[Finding]] = {
        "safe_discovery_consumers": [],
        "safe_test_fixtures": [],
        "safe_historical_docs": [],
        "safe_single_level_utilities": [],
        "safe_path_naming_patterns": [],
        "warnings": [],
        "risky_direct_level_scans": [],
        "risky_fixed_level_universes": [],
        "risky_independent_readiness_logic": [],
        "must_fix_findings": [],
    }
    kind = file_kind(relative_path)
    is_self_validator = relative_path == SELF_RELATIVE_PATH

    direct_scan_matches = collect_regex_findings(
        text=text,
        path=relative_path,
        regexes=DIRECT_LEVEL_SCAN_REGEXES,
        classification="RISKY_DIRECT_LEVEL_SCAN",
        reason="Direct Level_* scanning bypasses S6D discovery and can silently drift default readiness.",
    )
    fixed_universe_matches = collect_regex_findings(
        text=text,
        path=relative_path,
        regexes=FIXED_LEVEL_UNIVERSE_REGEXES,
        classification="RISKY_FIXED_LEVEL_UNIVERSE",
        reason="Hardcoding A-F as the full readiness universe bypasses dynamic S6D discovery.",
    )
    path_naming_matches = collect_regex_findings(
        text=text,
        path=relative_path,
        regexes=(PATH_NAMING_REGEX,),
        classification="SAFE_PATH_NAMING_PATTERN",
        reason="Path naming is acceptable only after the level was discovered or explicitly supplied.",
    )
    promotion_matches = collect_regex_findings(
        text=text,
        path=relative_path,
        regexes=PROMOTION_TRUE_REGEXES,
        classification="RISKY_INDEPENDENT_READINESS_LOGIC",
        reason="Active RAZ AUX-S6 code must not set promotion_allowed=true or authority_promotion_allowed=true.",
    )

    if kind == "doc":
        risky_matches = direct_scan_matches + fixed_universe_matches
        if risky_matches:
            for item in risky_matches:
                buckets["safe_historical_docs"].append(
                    Finding(
                        "SAFE_HISTORICAL_DOC",
                        item.path,
                        item.line,
                        item.excerpt,
                        "Historical documentation may mention Level_* or A-F without becoming runtime readiness authority.",
                    )
                )
        if path_naming_matches:
            buckets["safe_historical_docs"].extend(
                Finding(
                    "SAFE_HISTORICAL_DOC",
                    item.path,
                    item.line,
                    item.excerpt,
                    "Historical documentation may describe Level_* paths without becoming runtime readiness authority.",
                )
                for item in path_naming_matches
            )
        return dedupe_buckets(buckets)

    if kind == "test":
        safe_test_matches = direct_scan_matches + fixed_universe_matches + path_naming_matches
        buckets["safe_test_fixtures"].extend(
            Finding(
                "SAFE_TEST_FIXTURE",
                item.path,
                item.line,
                item.excerpt,
                "Tests may construct Level_* fixtures or fixed A-F data for regression coverage.",
            )
            for item in safe_test_matches
        )
        if promotion_matches:
            buckets["safe_test_fixtures"].extend(
                Finding(
                    "SAFE_TEST_FIXTURE",
                    item.path,
                    item.line,
                    item.excerpt,
                    "Tests may assert promotion guardrails using explicit true/false literals.",
                )
                for item in promotion_matches
            )
        return dedupe_buckets(buckets)

    matched_allowlist = False
    for entry in allowlist.get("safe_single_level_utilities", []):
        if relative_path == entry.get("path") and all(pattern in text for pattern in entry.get("required_patterns", [])):
            matched_allowlist = True
            buckets["safe_single_level_utilities"].append(
                Finding(
                    "SAFE_SINGLE_LEVEL_UTILITY",
                    relative_path,
                    1,
                    entry["path"],
                    str(entry.get("reason") or ""),
                )
            )
    for entry in allowlist.get("warning_legacy_references", []):
        if relative_path == entry.get("path") and all(pattern in text for pattern in entry.get("required_patterns", [])):
            matched_allowlist = True
            buckets["warnings"].append(
                Finding(
                    "WARNING_LEGACY_REFERENCE",
                    relative_path,
                    1,
                    entry["path"],
                    str(entry.get("reason") or ""),
                )
            )

    if file_has_discovery_consumption(text):
        buckets["safe_discovery_consumers"].append(
            Finding(
                "SAFE_DISCOVERY_CONSUMER",
                relative_path,
                1,
                relative_path,
                "Active file consumes S6D discovery artifacts or helpers instead of discovering readiness independently.",
            )
        )

    if is_self_validator:
        return dedupe_buckets(buckets)

    required_tokens = REQUIRED_DISCOVERY_CONSUMERS.get(relative_path)
    if required_tokens and not any(token in text for token in required_tokens):
        finding = Finding(
            "RISKY_INDEPENDENT_READINESS_LOGIC",
            relative_path,
            1,
            relative_path,
            "Known downstream consumer no longer references S6D discovery and may have drifted into independent readiness logic.",
        )
        buckets["risky_independent_readiness_logic"].append(finding)
        buckets["must_fix_findings"].append(to_must_fix(finding))

    if promotion_matches:
        buckets["risky_independent_readiness_logic"].extend(promotion_matches)
        buckets["must_fix_findings"].extend(to_must_fix(item) for item in promotion_matches)

    if direct_scan_matches:
        if matched_allowlist:
            buckets["safe_single_level_utilities"].extend(
                Finding(
                    "SAFE_SINGLE_LEVEL_UTILITY",
                    item.path,
                    item.line,
                    item.excerpt,
                    "Allowlisted single-level utility may reference Level_* naming without claiming readiness authority.",
                )
                for item in direct_scan_matches
            )
        else:
            buckets["risky_direct_level_scans"].extend(direct_scan_matches)
            buckets["must_fix_findings"].extend(to_must_fix(item) for item in direct_scan_matches)

    if fixed_universe_matches:
        if matched_allowlist:
            buckets["warnings"].extend(
                Finding(
                    "WARNING_LEGACY_REFERENCE",
                    item.path,
                    item.line,
                    item.excerpt,
                    "Allowlisted legacy utility contains fixed level references and must not be reused as readiness authority.",
                )
                for item in fixed_universe_matches
            )
        else:
            buckets["risky_fixed_level_universes"].extend(fixed_universe_matches)
            buckets["must_fix_findings"].extend(to_must_fix(item) for item in fixed_universe_matches)

    if path_naming_matches:
        if matched_allowlist:
            buckets["safe_single_level_utilities"].extend(
                Finding(
                    "SAFE_SINGLE_LEVEL_UTILITY",
                    item.path,
                    item.line,
                    item.excerpt,
                    "Allowlisted single-level utility builds a Level_* path after receiving an explicit level argument.",
                )
                for item in path_naming_matches
            )
        else:
            buckets["safe_path_naming_patterns"].extend(path_naming_matches)

    return dedupe_buckets(buckets)


def to_must_fix(finding: Finding) -> Finding:
    return Finding(
        "FAIL_MUST_USE_S6D_DISCOVERY",
        finding.path,
        finding.line,
        finding.excerpt,
        finding.reason,
    )


def dedupe_buckets(buckets: dict[str, list[Finding]]) -> dict[str, list[Finding]]:
    deduped: dict[str, list[Finding]] = {}
    for key, values in buckets.items():
        seen: set[tuple[str, int, str, str]] = set()
        ordered: list[Finding] = []
        for item in values:
            marker = (item.path, item.line, item.excerpt, item.classification)
            if marker in seen:
                continue
            seen.add(marker)
            ordered.append(item)
        ordered.sort(key=lambda item: (item.path, item.line, item.excerpt, item.reason))
        deduped[key] = ordered
    return deduped


def merge_bucket_lists(target: dict[str, list[Finding]], source: dict[str, list[Finding]]) -> None:
    for key, values in source.items():
        target[key].extend(values)


def evaluate_inventory_invariants(inventory_path: Path) -> tuple[bool, str, str, list[Finding]]:
    if not inventory_path.exists():
        finding = Finding(
            "FAIL_MUST_USE_S6D_DISCOVERY",
            stable_path(inventory_path),
            1,
            stable_path(inventory_path),
            "Canonical S6D discovery inventory is missing.",
        )
        return False, "FAIL", "FAIL", [finding]

    payload = read_json(inventory_path)
    findings: list[Finding] = []
    candidate_only_ok = True
    promotion_ok = True
    for index, row in enumerate(payload if isinstance(payload, list) else [], start=1):
        if row.get("authority_status") != "candidate_only":
            candidate_only_ok = False
            findings.append(
                Finding(
                    "RISKY_INDEPENDENT_READINESS_LOGIC",
                    stable_path(inventory_path),
                    index,
                    compact_excerpt(json.dumps(row, ensure_ascii=False)),
                    "Discovery inventory row lost candidate_only authority boundary.",
                )
            )
        if row.get("promotion_allowed") is not False:
            promotion_ok = False
            findings.append(
                Finding(
                    "RISKY_INDEPENDENT_READINESS_LOGIC",
                    stable_path(inventory_path),
                    index,
                    compact_excerpt(json.dumps(row, ensure_ascii=False)),
                    "Discovery inventory row allowed promotion, which is forbidden for RAZ AUX-S6.",
                )
            )
    return True, "PASS" if candidate_only_ok else "FAIL", "PASS" if promotion_ok else "FAIL", findings


def build_validation_report(
    *,
    base_dir: Path = BASE_DIR,
    inventory_path: Path = INVENTORY_PATH,
    s6e_report_path: Path = S6E_REPORT_PATH,
    allowlist_path: Path = ALLOWLIST_PATH,
    report_path: Path = REPORT_PATH,
    scan_paths: list[Path] | None = None,
) -> dict[str, Any]:
    allowlist = load_allowlist(allowlist_path)
    files = scan_paths or discover_scan_paths(base_dir)
    files = sorted(files, key=lambda item: stable_path(item, base_dir))

    merged: dict[str, list[Finding]] = {
        "safe_discovery_consumers": [],
        "safe_test_fixtures": [],
        "safe_historical_docs": [],
        "safe_single_level_utilities": [],
        "safe_path_naming_patterns": [],
        "warnings": [],
        "risky_direct_level_scans": [],
        "risky_fixed_level_universes": [],
        "risky_independent_readiness_logic": [],
        "must_fix_findings": [],
    }

    for path in files:
        relative_path = stable_path(path, base_dir)
        text = path.read_text(encoding="utf-8")
        merge_bucket_lists(
            merged,
            classify_file(
                relative_path=relative_path,
                text=text,
                allowlist=allowlist,
            ),
        )

    inventory_exists, candidate_only_invariant, promotion_allowed_invariant, invariant_findings = evaluate_inventory_invariants(inventory_path)
    if invariant_findings:
        merged["risky_independent_readiness_logic"].extend(invariant_findings)
        merged["must_fix_findings"].extend(to_must_fix(item) for item in invariant_findings)

    for key in merged:
        merged[key] = dedupe_buckets({key: merged[key]})[key]

    warning_count = len(merged["warnings"])
    must_fix_count = len(merged["must_fix_findings"])
    finding_count = sum(len(values) for values in merged.values())
    s6e_report_exists = s6e_report_path.exists()

    if must_fix_count or candidate_only_invariant == "FAIL" or promotion_allowed_invariant == "FAIL" or not inventory_exists or not s6e_report_exists:
        status = "FAIL"
    elif warning_count:
        status = "PASS_WITH_WARNINGS"
    else:
        status = "PASS"

    report = {
        "task": TASK_NAME,
        "status": status,
        "s6d_inventory_exists": inventory_exists,
        "s6e_report_exists": s6e_report_exists,
        "files_scanned": [stable_path(path, base_dir) for path in files],
        "safe_discovery_consumers": [item.as_dict() for item in merged["safe_discovery_consumers"]],
        "safe_test_fixtures": [item.as_dict() for item in merged["safe_test_fixtures"]],
        "safe_historical_docs": [item.as_dict() for item in merged["safe_historical_docs"]],
        "safe_single_level_utilities": [item.as_dict() for item in merged["safe_single_level_utilities"]],
        "safe_path_naming_patterns": [item.as_dict() for item in merged["safe_path_naming_patterns"]],
        "warnings": [item.as_dict() for item in merged["warnings"]],
        "risky_direct_level_scans": [item.as_dict() for item in merged["risky_direct_level_scans"]],
        "risky_fixed_level_universes": [item.as_dict() for item in merged["risky_fixed_level_universes"]],
        "risky_independent_readiness_logic": [item.as_dict() for item in merged["risky_independent_readiness_logic"]],
        "must_fix_findings": [item.as_dict() for item in merged["must_fix_findings"]],
        "candidate_only_invariant": candidate_only_invariant,
        "promotion_allowed_invariant": promotion_allowed_invariant,
        "summary": {
            "file_count": len(files),
            "finding_count": finding_count,
            "warning_count": warning_count,
            "must_fix_count": must_fix_count,
        },
        "next_recommended_task": (
            "Fix active downstream drift findings before adding new RAZ AUX-S6 modules."
            if status == "FAIL"
            else "Keep future RAZ AUX-S6 modules discovery-driven and rerun this validator in QA."
        ),
    }
    write_json(report_path, report)
    return report


def main() -> int:
    report = build_validation_report()
    print(
        json.dumps(
            {
                "task": report["task"],
                "status": report["status"],
                "candidate_only_invariant": report["candidate_only_invariant"],
                "promotion_allowed_invariant": report["promotion_allowed_invariant"],
                "summary": report["summary"],
                "report_path": stable_path(REPORT_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["status"] != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())

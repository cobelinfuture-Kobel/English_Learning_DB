#!/usr/bin/env python3
"""Build a text-free RAZ A-F material-yield and sufficiency report."""
from __future__ import annotations

import argparse, hashlib, json, os, tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Text-free observational report only; no canonical or learner-facing content."
TASK_ID = "RAZ-AF_Full4925MaterialYieldExtractionAndSufficiencyGate"
SCHEMA_VERSION = "raz.af.full_material_yield_and_sufficiency.v1"
PASS_STATUS = "PASS_RAZ_AF_FULL_MATERIAL_YIELD_REPORT"
LEVELS = ("A", "B", "C", "D", "E", "F")
EXPECTED_RECORDS, EXPECTED_BOOKS, EXPECTED_UNITS, EXPECTED_ROWS = 4925, 566, 24, 109
DEFAULT_S12B = REPO_ROOT / ".local/raz_af/observational_enrichment"
DEFAULT_S12C = REPO_ROOT / ".local/raz_af/full_coverage_query_index"
DEFAULT_UNITS = REPO_ROOT / "ulga/graph/a1_grammar_full_teachable_candidate_coverage.json"
DEFAULT_OUTPUT = REPO_ROOT / ".local/raz_af/full_material_yield/material_yield_and_sufficiency.safe.json"
AUTHORITY_PATHS = {
    "vocabulary": REPO_ROOT / "ulga/graph/vocabulary_nodes.json",
    "chunks": REPO_ROOT / "chunk_profile/json/chunks_generator_safe.json",
    "patterns": REPO_ROOT / "ulga/graph/sentence_patterns.json",
    "themes": REPO_ROOT / "ulga/graph/theme_nodes.json",
}
THRESHOLDS = {
    "vocabulary_rate": .85, "chunk_rate": .75, "pattern_rate": .80,
    "semantic_rate_before_gw": .95, "unit_records": 8, "unit_families": 3,
    "unit_micro_situations": 5, "unit_functions": 2, "unit_core_seeds": 8,
    "unit_passage_seeds": 2,
}
BOUNDARIES = {
    "source_scope": "RAZ_A_F_ONLY", "g_w_read_performed": False,
    "source_text_included": False, "learner_facing_material_created": False,
    "canonical_authority_write_performed": False, "core_sentence_candidate_created": False,
    "core_sentence_seed_count_only": True, "learning_unit_content_population_performed": False,
    "a2_a2plus_in_scope": False,
}
FORBIDDEN = {"text", "source_text", "passage", "sentence", "sentences", "transcript", "source_payload"}

class MaterialYieldError(ValueError): pass

def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def read_json(path: Path) -> Any:
    try: return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc: raise MaterialYieldError(f"json_unreadable:{path}:{exc}") from exc

def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def _rows(payload: Any) -> list[Mapping[str, Any]]:
    if isinstance(payload, list): return [x for x in payload if isinstance(x, Mapping)]
    if isinstance(payload, Mapping):
        for key in ("nodes", "items", "records", "themes", "patterns", "chunks"):
            if isinstance(payload.get(key), list): return [x for x in payload[key] if isinstance(x, Mapping)]
    raise MaterialYieldError("authority_rows_unavailable")

def _id(row: Mapping[str, Any]) -> str | None:
    for key in ("id", "node_id", "safe_id", "canonical_chunk_id", "theme_id", "pattern_id"):
        if isinstance(row.get(key), str) and row[key]: return row[key]
    return None

def load_baselines(paths: Mapping[str, Path] | None = None) -> dict[str, Any]:
    result = {}
    for name, path in (paths or AUTHORITY_PATHS).items():
        rows = _rows(read_json(path)); ids = sorted({value for row in rows if (value := _id(row))})
        result[name] = {"count": len(ids), "ids": ids, "source_path": str(path.relative_to(REPO_ROOT)), "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    return result

def load_records(root: Path, inventory: Mapping[str, Any]) -> list[dict[str, Any]]:
    records, seen = [], set()
    for entry in inventory.get("records", []):
        record = read_json(root / entry["path"]); ref = record.get("identity", {}).get("source_unit_ref")
        if not isinstance(ref, str) or not ref or ref in seen: raise MaterialYieldError(f"invalid_or_duplicate_source_ref:{ref}")
        seen.add(ref); records.append(record)
    return records

def _items(record: Mapping[str, Any], section: str) -> list[Mapping[str, Any]]:
    value = record.get("observations", {}).get(section, {}).get("items", [])
    return [x for x in value if isinstance(x, Mapping)]

def material(record: Mapping[str, Any]) -> dict[str, Any]:
    obs = record.get("observations", {})
    vocab = {r for i in _items(record, "vocabulary_exposure") for r in i.get("evp_candidate_refs", []) if isinstance(r, str)}
    chunks = {i["canonical_chunk_id"] for i in _items(record, "chunk_exposure") if isinstance(i.get("canonical_chunk_id"), str)}
    patterns = {r for i in _items(record, "sentence_pattern_observations") for r in i.get("pattern_authority_candidate_refs", []) if isinstance(r, str)}
    grammar = {r for i in _items(record, "sentence_pattern_observations") for r in i.get("grammar_candidate_refs", []) if isinstance(r, str)}
    sit = obs.get("situation_function_observations", {})
    values = lambda key: {x for x in sit.get(key, []) if isinstance(x, str)}
    macro, families, micro, functions = values("macro_domain_candidates"), values("situation_family_candidates"), values("micro_situation_candidates"), values("communicative_function_candidates")
    discourse = obs.get("discourse_observation", {}); shape = str(discourse.get("discourse_shape") or "unknown")
    picture = obs.get("pedagogical_signals", {}).get("picture_support_potential", {}).get("status") == "SUPPORTED"
    has_situation = bool(macro or families or micro)
    return {
        "vocabulary": vocab, "chunks": chunks, "patterns": patterns, "grammar": grammar,
        "macro": macro, "families": families, "micro": micro, "functions": functions,
        "shape": shape, "semantic": obs.get("quality_and_review", {}).get("semantic_pass_status") == "APPLIED",
        "core_seed": bool(grammar and vocab and (chunks or patterns) and has_situation),
        "passage_seed": bool(discourse.get("retelling_potential") or shape not in {"unknown", "single_description"}),
        "dialogue_seed": shape == "question_answer" or "asking_for_information" in functions,
        "scene_seed": picture or has_situation,
    }

def build_report(records: Sequence[Mapping[str, Any]], query: Mapping[str, Any], coverage: Mapping[str, Any], units_payload: Mapping[str, Any], baselines: Mapping[str, Any], *, expected_records: int = EXPECTED_RECORDS, expected_books: int = EXPECTED_BOOKS) -> dict[str, Any]:
    units = [x for x in units_payload.get("learning_units", []) if isinstance(x, Mapping)]
    grammar_rows = {r for u in units for r in u.get("canonical_egp_row_ids", []) if isinstance(r, str)}
    totals = {k: set() for k in ("vocabulary", "chunks", "patterns", "grammar", "macro", "families", "micro", "functions", "shapes")}
    refs, books, levels, mats = set(), set(), Counter(), []
    seeds, semantic = Counter(), 0
    for record in records:
        identity = record.get("identity", {}); ref, level, book = identity.get("source_unit_ref"), identity.get("source_level"), identity.get("source_book_id")
        if not isinstance(ref, str) or ref in refs or level not in LEVELS or not isinstance(book, str): raise MaterialYieldError("invalid_record_identity")
        refs.add(ref); books.add((level, book)); levels[level] += 1; m = material(record); mats.append((record, m))
        for key in ("vocabulary", "chunks", "patterns", "grammar", "macro", "families", "micro", "functions"): totals[key].update(m[key])
        totals["shapes"].add(m["shape"]); semantic += int(m["semantic"])
        for key in ("core_seed", "passage_seed", "dialogue_seed", "scene_seed"): seeds[key] += int(m[key])
    unit_reports = []
    for unit in units:
        uid = unit.get("grammar_unit_id") or unit.get("learning_unit_id") or unit.get("id")
        matched = [(r, m) for r, m in mats if uid in m["grammar"]]
        merge = lambda key: set().union(*(m[key] for _, m in matched)) if matched else set()
        counts = {
            "record_count": len(matched), "book_count": len({(r["identity"]["source_level"], r["identity"]["source_book_id"]) for r, _ in matched}),
            "vocabulary_ref_count": len(merge("vocabulary")), "chunk_ref_count": len(merge("chunks")), "pattern_ref_count": len(merge("patterns")),
            "macro_domain_count": len(merge("macro")), "situation_family_count": len(merge("families")), "micro_situation_count": len(merge("micro")), "communicative_function_count": len(merge("functions")),
            "core_sentence_seed_count": sum(m["core_seed"] for _, m in matched), "passage_seed_count": sum(m["passage_seed"] for _, m in matched),
            "dialogue_seed_count": sum(m["dialogue_seed"] for _, m in matched), "scene_seed_count": sum(m["scene_seed"] for _, m in matched),
        }
        checks = {
            "record_density": counts["record_count"] >= THRESHOLDS["unit_records"],
            "situation_family_density": counts["situation_family_count"] >= THRESHOLDS["unit_families"],
            "micro_situation_density": counts["micro_situation_count"] >= THRESHOLDS["unit_micro_situations"],
            "communicative_function_density": counts["communicative_function_count"] >= THRESHOLDS["unit_functions"],
            "core_sentence_seed_density": counts["core_sentence_seed_count"] >= THRESHOLDS["unit_core_seeds"],
            "passage_seed_density": counts["passage_seed_count"] >= THRESHOLDS["unit_passage_seeds"],
        }
        unit_reports.append({"grammar_unit_id": uid, "canonical_egp_row_count": len(unit.get("canonical_egp_row_ids", [])), **counts, "checks": checks, "sufficient": all(checks.values())})
    base_sets = {k: set(v.get("ids", [])) for k, v in baselines.items()}
    authority = {}
    for key, threshold_key in (("vocabulary", "vocabulary_rate"), ("chunks", "chunk_rate"), ("patterns", "pattern_rate")):
        total = len(base_sets.get(key, set())); observed = len(totals[key] & base_sets.get(key, set())); rate = round(observed / total, 6) if total else 0.0
        authority[key] = {"authority_count": total, "observed_authority_count": observed, "coverage_rate": rate, "threshold": THRESHOLDS[threshold_key], "pass": rate >= THRESHOLDS[threshold_key]}
    authority["themes"] = {"authority_count": len(base_sets.get("themes", set())), "macro_domain_count": len(totals["macro"]), "situation_family_count": len(totals["families"]), "micro_situation_count": len(totals["micro"])}
    summary = coverage.get("summary", {}); source_checks = {
        "record_count_exact": len(records) == expected_records, "book_count_exact": len(books) == expected_books,
        "levels_exact": set(levels) == set(LEVELS), "query_record_count_matches": query.get("record_count") == len(records),
        "coverage_record_count_matches": summary.get("s12c_records_indexed") == len(records), "coverage_book_count_matches": summary.get("represented_book_count") == len(books),
        "learning_unit_count_exact": len(units) == EXPECTED_UNITS, "grammar_row_count_exact": len(grammar_rows) == EXPECTED_ROWS,
    }
    source_pass, unit_pass, authority_pass = all(source_checks.values()), bool(unit_reports) and all(x["sufficient"] for x in unit_reports), all(authority[k]["pass"] for k in ("vocabulary", "chunks", "patterns"))
    semantic_rate = round(semantic / len(records), 6) if records else 0.0
    decision = "BLOCKED_SOURCE_INTEGRITY" if not source_pass else "AF_SUFFICIENT_FOR_CONTENT_POPULATION" if authority_pass and unit_pass else "DEEPEN_AF_SEMANTIC_EXTRACTION_BEFORE_GW" if semantic_rate < THRESHOLDS["semantic_rate_before_gw"] else "TARGETED_GW_EXPANSION_REQUIRED"
    report = {
        "task_id": TASK_ID, "schema_version": SCHEMA_VERSION, "validation_status": PASS_STATUS,
        "scope": {"levels": list(LEVELS), "expected_record_count": expected_records, "expected_book_count": expected_books, "g_w_read_performed": False},
        "source_accounting": {"record_count": len(records), "book_count": len(books), "level_counts": {x: levels[x] for x in LEVELS}, "query_record_count": query.get("record_count"), "coverage_record_count": summary.get("s12c_records_indexed"), "coverage_book_count": summary.get("represented_book_count"), "learning_unit_count": len(units), "canonical_grammar_row_count": len(grammar_rows)},
        "authority_baselines": {k: {x: v.get(x) for x in ("count", "source_path", "source_sha256")} for k, v in baselines.items()},
        "observed_material_yield": {"vocabulary_authority_ref_count": len(totals["vocabulary"]), "canonical_chunk_ref_count": len(totals["chunks"]), "sentence_pattern_ref_count": len(totals["patterns"]), "grammar_usage_ref_count": len(totals["grammar"]), "macro_domain_count": len(totals["macro"]), "situation_family_count": len(totals["families"]), "micro_situation_count": len(totals["micro"]), "communicative_function_count": len(totals["functions"]), "known_discourse_shape_count": len(totals["shapes"] - {"unknown"}), "core_sentence_seed_record_count": seeds["core_seed"], "passage_seed_record_count": seeds["passage_seed"], "dialogue_seed_record_count": seeds["dialogue_seed"], "scene_seed_record_count": seeds["scene_seed"], "semantic_annotation_applied_record_count": semantic, "semantic_completion_rate": semantic_rate},
        "authority_coverage": authority, "unit_suitability": sorted(unit_reports, key=lambda x: x["grammar_unit_id"]),
        "sufficiency_gate": {"source_integrity": {"checks": source_checks, "pass": source_pass}, "authority_alignment_pass": authority_pass, "unit_sufficiency_pass": unit_pass, "decision": decision, "af_sufficient_for_content_population": decision == "AF_SUFFICIENT_FOR_CONTENT_POPULATION", "targeted_gw_expansion_allowed": decision == "TARGETED_GW_EXPANSION_REQUIRED"},
        "thresholds": dict(THRESHOLDS), "claim_boundaries": dict(BOUNDARIES), "errors": [],
    }
    report["report_sha256"] = digest(report); return report

def scan_forbidden(value: Any, pointer: str = "$") -> list[str]:
    errors = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in FORBIDDEN: errors.append(f"forbidden_safe_key:{pointer}.{key}")
            errors += scan_forbidden(child, f"{pointer}.{key}")
    elif isinstance(value, list):
        for i, child in enumerate(value): errors += scan_forbidden(child, f"{pointer}[{i}]")
    return errors

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--s12b-root", type=Path, default=DEFAULT_S12B); parser.add_argument("--s12c-root", type=Path, default=DEFAULT_S12C); parser.add_argument("--learning-units", type=Path, default=DEFAULT_UNITS); parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT); args = parser.parse_args(argv)
    try:
        records = load_records(args.s12b_root, read_json(args.s12b_root / "inventory.json")); report = build_report(records, read_json(args.s12c_root / "query_index.json"), read_json(args.s12c_root / "coverage.json"), read_json(args.learning_units), load_baselines())
        if scan_forbidden(report): raise MaterialYieldError("safe_report_leakage")
        write_json(args.output, report); print(json.dumps({"task_id": TASK_ID, "decision": report["sufficiency_gate"]["decision"], "report_sha256": report["report_sha256"]}, sort_keys=True)); return 0
    except (MaterialYieldError, OSError, KeyError, TypeError, ValueError) as exc: print(f"FAIL:{exc}"); return 1

if __name__ == "__main__": raise SystemExit(main())

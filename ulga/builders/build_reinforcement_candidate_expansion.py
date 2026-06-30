import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

LEARNING_OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"
REINFORCEMENT_SIGNAL_PATH = BASE_DIR / "ulga" / "graph" / "reinforcement_signal.json"
DEPENDENCY_READINESS_RESOLUTION_PATH = BASE_DIR / "ulga" / "graph" / "dependency_readiness_resolution.json"
READING_STUBS_PATH = BASE_DIR / "ulga" / "graph" / "reading_stub_authority.json"
LEARNER_STATE_PATH = BASE_DIR / "ulga" / "learner_state" / "learner_state.json"
LEARNER_EXPOSURE_EVIDENCE_PATH = BASE_DIR / "ulga" / "graph" / "learner_exposure_evidence.json"

EXPANSION_OUT_PATH = BASE_DIR / "ulga" / "graph" / "reinforcement_candidate_expansion.json"
SUMMARY_OUT_PATH = BASE_DIR / "ulga" / "reports" / "reinforcement_candidate_expansion_summary.json"

SOURCE = "ULGA_S10J_REINFORCEMENT_CANDIDATE_EXPANSION"
CONTRACT_VERSION = "ULGA-S10J1"
GENERATED_AT = "2026-06-18T00:00:00Z"
VALID_SOURCES = {"direct_review", "dependency_parent", "theme_revisit", "exposure_evidence"}
VALID_DEPENDENCY_STATUSES = {"ready", "blocked", "unknown"}


def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_json_optional(path, default):
    if not path.exists():
        return default
    return read_json(path)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")


def dependency_overlay(resolution_payload):
    index = {}
    for resolution in resolution_payload.get("resolutions", []) if isinstance(resolution_payload, dict) else []:
        if not isinstance(resolution, dict):
            continue
        opportunity_id = resolution.get("opportunity_id")
        status = resolution.get("resolved_dependency_status")
        if opportunity_id and status in VALID_DEPENDENCY_STATUSES:
            index[opportunity_id] = status
    return index


def level_safety_overlay(resolution_payload):
    index = {}
    for resolution in resolution_payload.get("resolutions", []) if isinstance(resolution_payload, dict) else []:
        if not isinstance(resolution, dict):
            continue
        opportunity_id = resolution.get("opportunity_id")
        if not opportunity_id:
            continue
        evidence = resolution.get("evidence", {})
        index[opportunity_id] = evidence.get("level_ceiling_passed") is not False
    return index


def reading_ready_index(readings):
    ready = set()
    for reading in readings if isinstance(readings, list) else []:
        if not isinstance(reading, dict) or reading.get("delivery_ready") is not True:
            continue
        for opportunity_id in reading.get("linked_opportunities") or []:
            ready.add(opportunity_id)
    return ready


def opportunity_indexes(opportunities):
    by_id = {}
    by_theme = defaultdict(list)
    by_focus = defaultdict(list)
    for opportunity in opportunities if isinstance(opportunities, list) else []:
        if not isinstance(opportunity, dict) or not opportunity.get("opportunity_id"):
            continue
        by_id[opportunity["opportunity_id"]] = opportunity
        for theme_id in opportunity.get("theme_refs") or []:
            by_theme[theme_id].append(opportunity)
        for refs in (opportunity.get("focus_nodes") or {}).values():
            for ref in refs or []:
                by_focus[ref].append(opportunity)
    for values in by_theme.values():
        values.sort(key=lambda item: item["opportunity_id"])
    for values in by_focus.values():
        values.sort(key=lambda item: item["opportunity_id"])
    return by_id, by_theme, by_focus


def reinforced_refs_from_signal(signal):
    return signal.get("reinforced_node_refs") or []


def candidate_id_for(index):
    return f"RCE_{index:06d}"


def target_refs_for(source_record, opportunity):
    target_refs = {
        "vocabulary": [],
        "grammar": [],
        "pattern": [],
        "theme": [],
        "chunk": [],
    }
    node_type = source_record.get("node_type")
    node_id = source_record.get("node_id")
    if node_type == "theme" and node_id:
        target_refs["theme"] = [node_id]
    elif node_type == "vocabulary" and node_id:
        target_refs["vocabulary"] = [node_id]
    elif node_type == "grammar" and node_id:
        target_refs["grammar"] = [node_id]
    elif node_type in {"sentence_pattern", "pattern"} and node_id:
        target_refs["pattern"] = [node_id]
    elif node_type == "chunk" and node_id:
        target_refs["chunk"] = [node_id]
    else:
        for theme_id in opportunity.get("theme_refs") or []:
            if theme_id == node_id:
                target_refs["theme"] = [theme_id]
    return target_refs


def has_target_refs(target_refs):
    return any(bool(values) for values in target_refs.values())


def dependency_status_for(opportunity, dependency_status_by_opportunity):
    opportunity_id = opportunity["opportunity_id"]
    return dependency_status_by_opportunity.get(
        opportunity_id,
        opportunity.get("dependency", {}).get("status", "unknown"),
    )


def level_safe_for(opportunity, level_safe_by_opportunity):
    return level_safe_by_opportunity.get(opportunity["opportunity_id"], True)


def ineligible_reason_for(dependency_status, reading_ready, prior_exposure, level_safe):
    if dependency_status == "blocked":
        return "dependency_blocked"
    if dependency_status == "unknown":
        return "dependency_unknown"
    if not reading_ready:
        return "reading_missing"
    if not prior_exposure:
        return "no_prior_exposure"
    if not level_safe:
        return "level_blocked"
    return None


def make_candidate(
    candidate_source,
    opportunity,
    source_record,
    dependency_status_by_opportunity,
    reading_ready_opportunities,
    confidence,
):
    dependency_status = dependency_status_for(opportunity, dependency_status_by_opportunity)
    reading_ready = opportunity["opportunity_id"] in reading_ready_opportunities
    prior_exposure = bool(source_record.get("last_seen_at") or source_record.get("exposure_count"))
    target_refs = target_refs_for(source_record, opportunity)
    warnings = []
    if dependency_status != "ready":
        warnings.append(f"dependency_status_{dependency_status}")
    if not reading_ready:
        warnings.append("reading_not_ready")
    if not prior_exposure:
        warnings.append("prior_exposure_missing")
    if not has_target_refs(target_refs):
        warnings.append("target_refs_empty")
    planner_eligible = (
        prior_exposure
        and dependency_status == "ready"
        and reading_ready
        and has_target_refs(target_refs)
    )
    return {
        "candidate_id": "",
        "opportunity_id": opportunity["opportunity_id"],
        "candidate_source": candidate_source,
        "learner_id": source_record.get("learner_id"),
        "target_refs": target_refs,
        "evidence_refs": [],
        "evidence": {
            "learner_id": source_record.get("learner_id"),
            "source_node_id": source_record.get("node_id"),
            "source_node_type": source_record.get("node_type"),
            "review_due": bool(source_record.get("review_due_at")),
            "mastery_band": source_record.get("mastery_band"),
            "dependency_parent": candidate_source == "dependency_parent",
            "theme_revisit": candidate_source == "theme_revisit",
        },
        "planner_eligible": planner_eligible,
        "ineligible_reason": None if planner_eligible else ineligible_reason_for(
            dependency_status,
            reading_ready,
            prior_exposure,
            True,
        ),
        "dependency_status": dependency_status,
        "reading_ready": reading_ready,
        "prior_exposure": prior_exposure,
        "level_safe": True,
        "confidence": confidence,
        "warnings": warnings,
        "source": SOURCE,
    }


def source_record_from_exposure(evidence):
    source_node_type = evidence.get("source_node_type")
    source_node_id = evidence.get("source_node_id")
    node_type = "theme" if source_node_type == "theme" else source_node_type
    return {
        "learner_id": evidence.get("learner_id"),
        "node_id": source_node_id,
        "node_type": node_type,
        "last_seen_at": GENERATED_AT if evidence.get("prior_exposure") else None,
        "exposure_count": 1 if evidence.get("prior_exposure") else 0,
        "review_due_at": None,
        "mastery_band": evidence.get("confidence_band"),
    }


def exposure_evidence_candidates(
    exposure_payload,
    by_id,
    dependency_status_by_opportunity,
    level_safe_by_opportunity,
    reading_ready_opportunities,
):
    candidates = []
    seen = set()
    evidence_records = exposure_payload.get("evidence", []) if isinstance(exposure_payload, dict) else []
    for evidence in evidence_records:
        if not isinstance(evidence, dict):
            continue
        if evidence.get("target_type") != "opportunity" or evidence.get("prior_exposure") is not True:
            continue
        opportunity = by_id.get(evidence.get("target_id"))
        if opportunity is None:
            continue
        key = (evidence.get("learner_id"), evidence.get("target_id"), evidence.get("evidence_id"))
        if key in seen:
            continue
        seen.add(key)
        dependency_status = dependency_status_for(opportunity, dependency_status_by_opportunity)
        reading_ready = opportunity["opportunity_id"] in reading_ready_opportunities
        prior_exposure = evidence.get("prior_exposure") is True
        level_safe = level_safe_for(opportunity, level_safe_by_opportunity)
        source_record = source_record_from_exposure(evidence)
        target_refs = target_refs_for(source_record, opportunity)
        warnings = list(evidence.get("warnings") or [])
        if dependency_status != "ready":
            warnings.append(f"dependency_status_{dependency_status}")
        if not reading_ready:
            warnings.append("reading_not_ready")
        if not prior_exposure:
            warnings.append("prior_exposure_missing")
        if not level_safe:
            warnings.append("level_blocked")
        if not has_target_refs(target_refs):
            warnings.append("target_refs_empty")
        planner_eligible = (
            prior_exposure
            and dependency_status == "ready"
            and reading_ready
            and level_safe
            and has_target_refs(target_refs)
        )
        confidence = evidence.get("opportunity_exposure_score", 0.0)
        if not isinstance(confidence, (int, float)):
            confidence = 0.0
        candidates.append(
            {
                "candidate_id": "",
                "opportunity_id": opportunity["opportunity_id"],
                "candidate_source": "exposure_evidence",
                "learner_id": evidence.get("learner_id"),
                "target_refs": target_refs,
                "evidence_refs": [evidence.get("evidence_id")],
                "evidence": {
                    "learner_id": evidence.get("learner_id"),
                    "source_node_id": evidence.get("source_node_id"),
                    "source_node_type": evidence.get("source_node_type"),
                    "exposure_evidence": True,
                    "confidence_band": evidence.get("confidence_band"),
                    "mapping_type": evidence.get("mapping_type"),
                },
                "planner_eligible": planner_eligible,
                "ineligible_reason": None
                if planner_eligible
                else ineligible_reason_for(dependency_status, reading_ready, prior_exposure, level_safe),
                "dependency_status": dependency_status,
                "reading_ready": reading_ready,
                "prior_exposure": prior_exposure,
                "level_safe": level_safe,
                "confidence": round(max(0.0, min(1.0, float(confidence))), 6),
                "warnings": sorted(set(warnings)),
                "source": SOURCE,
            }
        )
    return candidates


def direct_review_candidates(records, by_theme, by_focus, dependency_status_by_opportunity, reading_ready_opportunities):
    candidates = []
    for record in records:
        if not isinstance(record, dict) or not record.get("node_id"):
            continue
        if not record.get("review_due_at") and record.get("mastery_band") != "practicing":
            continue
        opportunities = list(by_focus.get(record["node_id"], []))
        if record.get("node_type") == "theme":
            opportunities.extend(by_theme.get(record["node_id"], []))
        seen = set()
        for opportunity in opportunities:
            opportunity_id = opportunity["opportunity_id"]
            if opportunity_id in seen:
                continue
            seen.add(opportunity_id)
            candidates.append(
                make_candidate(
                    "direct_review",
                    opportunity,
                    record,
                    dependency_status_by_opportunity,
                    reading_ready_opportunities,
                    0.75,
                )
            )
    return candidates


def theme_revisit_candidates(records, by_theme, dependency_status_by_opportunity, reading_ready_opportunities):
    candidates = []
    for record in records:
        if not isinstance(record, dict) or record.get("node_type") != "theme" or not record.get("node_id"):
            continue
        if not record.get("last_seen_at"):
            continue
        for opportunity in by_theme.get(record["node_id"], []):
            candidates.append(
                make_candidate(
                    "theme_revisit",
                    opportunity,
                    record,
                    dependency_status_by_opportunity,
                    reading_ready_opportunities,
                    0.7,
                )
            )
    return candidates


def dependency_parent_candidates(
    signal_payload,
    resolution_payload,
    by_focus,
    dependency_status_by_opportunity,
    reading_ready_opportunities,
):
    candidates = []
    records = []
    for resolution in resolution_payload.get("resolutions", []) if isinstance(resolution_payload, dict) else []:
        if resolution.get("resolved_dependency_status") != "blocked":
            continue
        for required_ref in resolution.get("evidence", {}).get("required_refs") or []:
            records.append(
                {
                    "learner_id": None,
                    "node_id": required_ref,
                    "node_type": required_ref.split(":", 1)[0],
                    "last_seen_at": GENERATED_AT,
                    "exposure_count": 1,
                    "review_due_at": None,
                    "mastery_band": None,
                    "blocked_child_opportunity_id": resolution.get("opportunity_id"),
                }
            )
    signals = signal_payload.get("signals", []) if isinstance(signal_payload, dict) else []
    positive_refs = {
        ref
        for signal in signals
        if isinstance(signal, dict) and signal.get("signal_score", 0) > 0
        for ref in reinforced_refs_from_signal(signal)
    }
    seen = set()
    for record in records:
        if record["node_id"] not in positive_refs:
            continue
        for opportunity in by_focus.get(record["node_id"], []):
            key = (record["node_id"], opportunity["opportunity_id"])
            if key in seen:
                continue
            seen.add(key)
            candidate = make_candidate(
                "dependency_parent",
                opportunity,
                record,
                dependency_status_by_opportunity,
                reading_ready_opportunities,
                0.65,
            )
            candidate["evidence"]["blocked_child_opportunity_id"] = record["blocked_child_opportunity_id"]
            candidates.append(candidate)
    return candidates


def assign_candidate_ids(candidates):
    candidates.sort(
        key=lambda item: (
            item["candidate_source"],
            item["opportunity_id"],
            item.get("learner_id") or "",
            ",".join(item.get("evidence_refs", [])),
            json.dumps(item["target_refs"], sort_keys=True),
        )
    )
    for index, candidate in enumerate(candidates, start=1):
        candidate["candidate_id"] = candidate_id_for(index)
    return candidates


def build_summary(candidates, warnings):
    source_distribution = Counter(candidate["candidate_source"] for candidate in candidates)
    ineligible_reason_distribution = Counter(
        candidate["ineligible_reason"] for candidate in candidates if candidate.get("ineligible_reason")
    )
    status = "PASS_WITH_WARNINGS" if warnings or not any(candidate["planner_eligible"] for candidate in candidates) else "PASS"
    return {
        "status": status,
        "candidate_count": len(candidates),
        "planner_eligible_count": sum(1 for candidate in candidates if candidate["planner_eligible"]),
        "source_distribution": dict(sorted(source_distribution.items())),
        "ineligible_reason_distribution": dict(sorted(ineligible_reason_distribution.items())),
        "exposure_evidence_used_count": sum(
            len(candidate.get("evidence_refs", []))
            for candidate in candidates
            if candidate["candidate_source"] == "exposure_evidence"
        ),
        "dependency_ready_count": sum(1 for candidate in candidates if candidate["dependency_status"] == "ready"),
        "reading_ready_count": sum(1 for candidate in candidates if candidate["reading_ready"]),
        "warnings": warnings,
    }


def build_reinforcement_candidate_expansion(
    output_path=EXPANSION_OUT_PATH,
    summary_path=SUMMARY_OUT_PATH,
):
    warnings = []
    opportunities = read_json(LEARNING_OPPORTUNITIES_PATH)
    signal_payload = read_json_optional(REINFORCEMENT_SIGNAL_PATH, {})
    resolution_payload = read_json_optional(DEPENDENCY_READINESS_RESOLUTION_PATH, {})
    readings = read_json_optional(READING_STUBS_PATH, [])
    learner_state = read_json_optional(LEARNER_STATE_PATH, {})
    exposure_payload = read_json_optional(LEARNER_EXPOSURE_EVIDENCE_PATH, {})

    if not isinstance(opportunities, list):
        raise ValueError("learning_opportunities.json must contain a list")
    records = learner_state.get("learner_state_records", []) if isinstance(learner_state, dict) else []
    if not records:
        warnings.append("learner_state has no records; emitted no learner-driven candidates")
    exposure_records = exposure_payload.get("evidence", []) if isinstance(exposure_payload, dict) else []
    if not exposure_records:
        warnings.append("learner_exposure_evidence has no records; emitted no exposure-driven candidates")

    by_id, by_theme, by_focus = opportunity_indexes(opportunities)
    dependency_status_by_opportunity = dependency_overlay(resolution_payload)
    level_safe_by_opportunity = level_safety_overlay(resolution_payload)
    reading_ready_opportunities = reading_ready_index(readings)

    candidates = []
    candidates.extend(
        exposure_evidence_candidates(
            exposure_payload,
            by_id,
            dependency_status_by_opportunity,
            level_safe_by_opportunity,
            reading_ready_opportunities,
        )
    )
    candidates = assign_candidate_ids(candidates)
    if candidates and not any(candidate["planner_eligible"] for candidate in candidates):
        warnings.append("candidate expansion produced candidates, but none are planner eligible")

    payload = {
        "metadata": {
            "source": SOURCE,
            "contract_version": CONTRACT_VERSION,
            "version": "1.0",
            "generated_at": GENERATED_AT,
        },
        "candidates": candidates,
    }
    summary = build_summary(candidates, warnings)
    write_json(output_path, payload)
    write_json(summary_path, summary)
    print(f"Reinforcement Candidate Expansion build: {summary['status']}")
    print(f"Candidates: {summary['candidate_count']}")
    print(f"Planner eligible: {summary['planner_eligible_count']}")
    print(f"Warnings: {len(warnings)}")
    return summary


def main():
    try:
        build_reinforcement_candidate_expansion()
    except Exception as exc:
        print(f"Reinforcement Candidate Expansion build: FAIL - {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

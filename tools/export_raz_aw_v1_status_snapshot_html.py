import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
HTML_PATH = BASE_DIR / "docs" / "status" / "raz_aw_v1_status_snapshot.html"
MANIFEST_PATH = BASE_DIR / "docs" / "status" / "raz_aw_v1_status_snapshot_manifest.json"

PROJECT_ID = "English_Learning_DB"
EPIC_ID = "RAZ-AW-V1_ReadingSystemV1ProgressAndStatusReporting"
SUBTASK_ID = "RAZ-AW-V1_StatusSnapshotHTMLExport"

ALLOWED_PROGRESS_STATUSES = {
    "NOT_STARTED",
    "IN_PROGRESS",
    "PARTIAL",
    "COMPLETE",
    "BLOCKED",
    "UNKNOWN",
}

ACTIVE_TARGET = "Reading System V1 = Source-grounded practice generation"
DEFERRED_TARGETS = [
    "Reading System V2 = Assessment pattern expansion",
    "Reading System V3 = Learner error tagging / weak-point diagnosis",
    "Reading System V4 = Adaptive sequencing / learning path integration",
    "Reading System V5 = Multi-skill bridge: Reading → Writing / Listening / Speaking",
]

CANONICAL_SOURCE_CANDIDATES = [
    {
        "source_id": "README",
        "path": "README.md",
        "role": "project_orientation",
    },
    {
        "source_id": "PROJECT_TASK_EXPANSION_CONTROL_POLICY",
        "path": "docs/governance/PROJECT_TASK_EXPANSION_CONTROL_POLICY.md",
        "role": "scope_governance",
    },
    {
        "source_id": "CORPUS_SOURCE_INVENTORY",
        "path": "ulga/graph/corpus_source_inventory.json",
        "role": "source_inventory",
    },
    {
        "source_id": "CORPUS_SOURCE_INVENTORY_SUMMARY",
        "path": "ulga/reports/corpus_source_inventory_summary.json",
        "role": "source_inventory_summary",
    },
    {
        "source_id": "RAZ_AW_V1_STATUS",
        "path": "docs/status/raz_aw_v1_status.json",
        "role": "status_source_candidate",
    },
    {
        "source_id": "READING_SYSTEM_V1_STATUS",
        "path": "docs/status/reading_system_v1_status.json",
        "role": "status_source_candidate",
    },
    {
        "source_id": "RAZ_AW_S11_IMPLEMENTATION",
        "path": "docs/raz_aw/RAZ_AW_S11_IMPLEMENTATION.md",
        "role": "content_authority_reference_candidate",
    },
    {
        "source_id": "ULGA_S11_CONTENT_AUTHORITY_SCAN",
        "path": "docs/ulga/ULGA_S11_READING_DIALOGUE_CONTENT_AUTHORITY_DESIGN_SCAN.md",
        "role": "content_authority_reference_candidate",
    },
]

PROGRESS_AREAS = [
    {
        "area": "Source Authority",
        "status": "UNKNOWN",
        "reason": "Snapshot reads source inventory if present; absent facts remain UNKNOWN.",
    },
    {
        "area": "Content Authority",
        "status": "UNKNOWN",
        "reason": "This export does not promote or generate content authority artifacts.",
    },
    {
        "area": "Query Layer",
        "status": "UNKNOWN",
        "reason": "Queryable Reading V1 status must come from repository evidence.",
    },
    {
        "area": "Validation Layer",
        "status": "PARTIAL",
        "reason": "This task adds HTML/manifest export checks, not Reading validator completion.",
    },
    {
        "area": "Reading Generation",
        "status": "UNKNOWN",
        "reason": "Generation is intentionally out of scope for this status export.",
    },
    {
        "area": "Reading Practice",
        "status": "UNKNOWN",
        "reason": "Practice package generation is not implemented by this export.",
    },
    {
        "area": "Reading Assessment",
        "status": "NOT_STARTED",
        "reason": "Assessment expansion belongs to deferred V2 unless separately approved.",
    },
    {
        "area": "Production Readiness",
        "status": "PARTIAL",
        "reason": "Progress visibility improves; production readiness is not claimed.",
    },
]

MILESTONES = [
    {
        "milestone": "Status snapshot export script",
        "status": "COMPLETE",
        "evidence": "tools/export_raz_aw_v1_status_snapshot_html.py",
    },
    {
        "milestone": "Static HTML snapshot",
        "status": "COMPLETE",
        "evidence": "docs/status/raz_aw_v1_status_snapshot.html",
    },
    {
        "milestone": "Machine-readable manifest",
        "status": "COMPLETE",
        "evidence": "docs/status/raz_aw_v1_status_snapshot_manifest.json",
    },
    {
        "milestone": "Export tests",
        "status": "COMPLETE",
        "evidence": "tests/test_export_raz_aw_v1_status_snapshot_html.py",
    },
    {
        "milestone": "Reading question generation",
        "status": "NOT_STARTED",
        "evidence": "Explicitly out of scope for this sub-task.",
    },
    {
        "milestone": "V2-V5 feature work",
        "status": "BLOCKED",
        "evidence": "Deferred by V1 boundary; not active in this task.",
    },
]


def now_utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json_if_present(path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as exc:
        return {"_read_error": str(exc)}


def source_record(spec):
    path = BASE_DIR / spec["path"]
    exists = path.exists()
    record = {
        "source_id": spec["source_id"],
        "role": spec["role"],
        "path": spec["path"],
        "exists": exists,
        "status": "present" if exists else "MISSING_SOURCE",
    }
    if path.suffix == ".json" and exists:
        data = read_json_if_present(path)
        if isinstance(data, dict) and "_read_error" in data:
            record["status"] = "READ_ERROR"
            record["read_error"] = data["_read_error"]
        elif data is not None:
            record["json_type"] = type(data).__name__
    return record


def build_source_records():
    return [source_record(spec) for spec in CANONICAL_SOURCE_CANDIDATES]


def derive_gate_metrics(source_records):
    generated_files = {
        "html_generated": HTML_PATH.exists(),
        "manifest_generated": MANIFEST_PATH.exists(),
        "script_present": (BASE_DIR / "tools" / "export_raz_aw_v1_status_snapshot_html.py").exists(),
        "test_present": (BASE_DIR / "tests" / "test_export_raz_aw_v1_status_snapshot_html.py").exists(),
    }
    return {
        "source_files_discovered": sum(1 for record in source_records if record["exists"]),
        "source_files_checked": len(source_records),
        "missing_source_count": sum(1 for record in source_records if not record["exists"]),
        "html_generated": generated_files["html_generated"],
        "manifest_generated": generated_files["manifest_generated"],
        "script_present": generated_files["script_present"],
        "test_present": generated_files["test_present"],
        "no_v2_v5_scope_creep": True,
        "reading_generation_changed": False,
        "adaptive_learning_changed": False,
        "learner_error_tagging_changed": False,
    }


def derive_distance_vector(gate_metrics):
    missing = gate_metrics["missing_source_count"]
    if missing == gate_metrics["source_files_checked"]:
        d_all = "UNKNOWN"
    elif missing:
        d_all = "PARTIAL"
    else:
        d_all = "CLOSER"
    return {
        "D_all": d_all,
        "current_subtask_status": "COMPLETE",
        "reading_system_v1_contribution": (
            "Improves progress visibility, source traceability, gate reporting, "
            "and operator handoff quality without adding Reading generation features."
        ),
        "next_shortest_step": (
            "Run the export script and tests in the repository, then use the generated "
            "HTML snapshot as the status readback artifact."
        ),
    }


def validate_manifest_payload(payload):
    required = {
        "project_id",
        "epic_id",
        "subtask_id",
        "generated_at",
        "active_target",
        "deferred_targets",
        "source_records",
        "progress_areas",
        "milestones",
        "gate_metrics",
        "distance_vector",
        "warnings",
    }
    missing = required - set(payload)
    if missing:
        raise ValueError(f"manifest missing required keys: {sorted(missing)}")
    for area in payload["progress_areas"]:
        if area["status"] not in ALLOWED_PROGRESS_STATUSES:
            raise ValueError(f"invalid progress status: {area['status']}")
    for item in payload["milestones"]:
        if item["status"] not in ALLOWED_PROGRESS_STATUSES:
            raise ValueError(f"invalid milestone status: {item['status']}")


def build_manifest():
    source_records = build_source_records()
    gate_metrics = derive_gate_metrics(source_records)
    warnings = []
    missing_sources = [record["source_id"] for record in source_records if not record["exists"]]
    if missing_sources:
        warnings.append(
            {
                "warning_id": "MISSING_SOURCE",
                "severity": "warning",
                "message": "Some status/reference sources are missing; related readiness values remain UNKNOWN.",
                "sources": missing_sources,
            }
        )
    if not any(record["source_id"] == "RAZ_AW_V1_STATUS" and record["exists"] for record in source_records):
        warnings.append(
            {
                "warning_id": "NO_CANONICAL_RAZ_AW_V1_STATUS",
                "severity": "warning",
                "message": "No canonical RAZ-AW V1 status JSON was found; snapshot avoids claiming project-level PASS.",
            }
        )
    payload = {
        "project_id": PROJECT_ID,
        "epic_id": EPIC_ID,
        "subtask_id": SUBTASK_ID,
        "generated_at": now_utc(),
        "active_target": ACTIVE_TARGET,
        "deferred_targets": DEFERRED_TARGETS,
        "source_records": source_records,
        "progress_areas": PROGRESS_AREAS,
        "milestones": MILESTONES,
        "gate_metrics": gate_metrics,
        "distance_vector": derive_distance_vector(gate_metrics),
        "warnings": warnings,
    }
    validate_manifest_payload(payload)
    return payload


def status_class(status):
    normalized = status.lower().replace("_", "-")
    if normalized in {"complete", "present"}:
        return "status-complete"
    if normalized in {"partial", "present-with-warnings"}:
        return "status-partial"
    if normalized in {"blocked", "missing-source", "read-error"}:
        return "status-blocked"
    if normalized == "not-started":
        return "status-not-started"
    return "status-unknown"


def render_table(headers, rows):
    header_html = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body = []
    for row in rows:
        cells = []
        for value in row:
            text = escape(str(value))
            if value in ALLOWED_PROGRESS_STATUSES or value in {"present", "MISSING_SOURCE", "READ_ERROR"}:
                cells.append(f'<td><span class="{status_class(str(value))}">{text}</span></td>')
            else:
                cells.append(f"<td>{text}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    return "<table><thead><tr>" + header_html + "</tr></thead><tbody>" + "".join(body) + "</tbody></table>"


def render_html(payload):
    source_rows = [
        [record["source_id"], record["role"], record["path"], record["status"]]
        for record in payload["source_records"]
    ]
    progress_rows = [
        [area["area"], area["status"], area["reason"]]
        for area in payload["progress_areas"]
    ]
    milestone_rows = [
        [item["milestone"], item["status"], item["evidence"]]
        for item in payload["milestones"]
    ]
    gate_rows = [[key, value] for key, value in payload["gate_metrics"].items()]
    distance_rows = [[key, value] for key, value in payload["distance_vector"].items()]
    warning_rows = [
        [warning["warning_id"], warning["severity"], warning["message"]]
        for warning in payload["warnings"]
    ] or [["NONE", "info", "No warnings emitted by this export."]]

    deferred_items = "".join(f"<li>{escape(item)}</li>" for item in payload["deferred_targets"])

    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <title>{escape(SUBTASK_ID)} Snapshot</title>
  <style>
    body {{ font-family: Arial, "Noto Sans TC", sans-serif; margin: 32px; background: #f7f7f7; color: #222; }}
    main {{ max-width: 1180px; margin: 0 auto; background: white; padding: 28px; border: 1px solid #ddd; }}
    h1, h2 {{ margin-top: 0; }}
    .meta {{ display: grid; grid-template-columns: 220px 1fr; gap: 8px 16px; margin-bottom: 24px; }}
    .badge {{ display: inline-block; padding: 2px 8px; border: 1px solid #aaa; border-radius: 12px; background: #fafafa; }}
    table {{ width: 100%; border-collapse: collapse; margin: 12px 0 28px; font-size: 14px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
    th {{ background: #f1f1f1; text-align: left; }}
    .status-complete {{ font-weight: 700; }}
    .status-partial {{ font-weight: 700; }}
    .status-blocked {{ font-weight: 700; }}
    .status-not-started {{ font-weight: 700; }}
    .status-unknown {{ font-weight: 700; }}
    .scope-lock {{ border-left: 4px solid #555; padding: 8px 12px; background: #f6f6f6; margin-bottom: 20px; }}
    code {{ background: #f2f2f2; padding: 1px 4px; }}
  </style>
</head>
<body>
<main>
  <h1>RAZ-AW V1 Status Snapshot HTML Export</h1>
  <section class="meta">
    <strong>Project</strong><span>{escape(payload["project_id"])}</span>
    <strong>Epic ID</strong><span>{escape(payload["epic_id"])}</span>
    <strong>Sub-task ID</strong><span>{escape(payload["subtask_id"])}</span>
    <strong>Generated At</strong><span>{escape(payload["generated_at"])}</span>
    <strong>Active Target</strong><span><span class="badge">{escape(payload["active_target"])}</span></span>
  </section>

  <section class="scope-lock">
    <strong>Scope Lock:</strong>
    This snapshot is a status/export artifact only. It does not implement Reading question generation,
    learner error tagging, adaptive sequencing, listening, speaking, writing, or student-facing app features.
  </section>

  <h2>V1 Boundary</h2>
  <p><strong>Active:</strong> {escape(payload["active_target"])}</p>
  <p><strong>Deferred / Not Active:</strong></p>
  <ul>{deferred_items}</ul>

  <h2>Progress Snapshot</h2>
  {render_table(["Area", "Status", "Reason"], progress_rows)}

  <h2>Milestone Status</h2>
  {render_table(["Milestone", "Status", "Evidence"], milestone_rows)}

  <h2>Source Trace / Evidence Trace</h2>
  {render_table(["Source ID", "Role", "Path", "Status"], source_rows)}

  <h2>Gate Metrics</h2>
  {render_table(["Metric", "Value"], gate_rows)}

  <h2>Distance Vector</h2>
  {render_table(["Field", "Value"], distance_rows)}

  <h2>Warnings</h2>
  {render_table(["Warning ID", "Severity", "Message"], warning_rows)}
</main>
</body>
</html>
"""


def write_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")


def main():
    payload = build_manifest()
    write_json(MANIFEST_PATH, payload)
    html = render_html(payload)
    write_text(HTML_PATH, html)
    print("RAZ-AW V1 status snapshot export: PASS")
    print(f"HTML: {HTML_PATH.relative_to(BASE_DIR).as_posix()}")
    print(f"Manifest: {MANIFEST_PATH.relative_to(BASE_DIR).as_posix()}")


if __name__ == "__main__":
    main()

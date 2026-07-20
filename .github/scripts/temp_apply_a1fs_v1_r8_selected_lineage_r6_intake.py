from __future__ import annotations

from pathlib import Path


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def replace_block(text: str, start: str, end: str, replacement: str, *, label: str) -> str:
    left = text.find(start)
    if left < 0:
        raise SystemExit(f"{label}: start anchor not found")
    right = text.find(end, left)
    if right < 0:
        raise SystemExit(f"{label}: end anchor not found")
    return text[:left] + replacement + text[right:]


def replace_once_after(text: str, marker: str, old: str, new: str, *, label: str) -> str:
    marker_index = text.find(marker)
    if marker_index < 0:
        raise SystemExit(f"{label}: marker not found")
    prefix = text[:marker_index]
    suffix = text[marker_index:]
    return prefix + replace_once(suffix, old, new, label=label)


runner_path = Path("ulga/builders/run_a1fs_v1_r8_legacy_real_evidence_reconciliation_local.py")
text = runner_path.read_text(encoding="utf-8")

if 'LINEAGE_SCHEMA_VERSION = "a1fs.v1.r8.selected_deterministic_lineage.v1"' in text:
    raise SystemExit("runner already patched")

text = replace_once(
    text,
    "from ulga.builders import build_a1fs_v1_r2_complete_breadth_ontology_deployment_contract as r2\n"
    "from ulga.builders import build_a1fs_v1_r3r4_authority_reviewed_production_population as population\n"
    "from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4\n"
    "from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5\n",
    "from ulga.builders import build_a1fs_v1_r2_complete_breadth_ontology_deployment_contract as r2\n"
    "from ulga.builders import build_a1fs_v1_r3_complete_breadth_denominator_coverage_gap_planner as r3\n"
    "from ulga.builders import build_a1fs_v1_r3r4_authority_reviewed_production_population as population\n"
    "from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4\n"
    "from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5\n"
    "from ulga.builders import build_a1fs_v1_r6_gpt_diagnostic_package_controlled_recommendation_gate as r6\n",
    label="runner imports",
)

text = replace_once(
    text,
    'SCHEMA_VERSION = "a1fs.v1.r8.legacy_real_evidence_local_runner.v2"\n'
    'STATUS = "PASS_A1FS_V1_R8_LOCAL_RECONCILIATION_EXECUTED_AND_VALIDATED"\n'
    'BLOCKED = "BLOCKED_A1FS_V1_R8_LOCAL_RECONCILIATION_DISCOVERY"\n'
    'REPORT_NAME = "a1fs_v1_r8_reconciliation_local_runner.safe.json"\n'
    'NEXT_SHORT_STEP = reconciliation.NEXT_SHORT_STEP\n'
    'MATERIALIZATION_REVIEWED_AT = "2000-01-01T00:00:00Z"\n',
    'SCHEMA_VERSION = "a1fs.v1.r8.legacy_real_evidence_local_runner.v3"\n'
    'STATUS = "PASS_A1FS_V1_R8_LOCAL_RECONCILIATION_EXECUTED_AND_VALIDATED"\n'
    'BLOCKED = "BLOCKED_A1FS_V1_R8_LOCAL_RECONCILIATION_DISCOVERY"\n'
    'REPORT_NAME = "a1fs_v1_r8_reconciliation_local_runner.safe.json"\n'
    'LINEAGE_SCHEMA_VERSION = "a1fs.v1.r8.selected_deterministic_lineage.v1"\n'
    'LINEAGE_SAFE_SCHEMA_VERSION = "a1fs.v1.r8.selected_deterministic_lineage_safe.v1"\n'
    'LINEAGE_STATUS = "PASS_A1FS_V1_R8_SELECTED_DETERMINISTIC_LINEAGE_PERSISTED_AND_R6_INTAKE_READY"\n'
    'LINEAGE_PRIVATE_NAME = "selected_lineage.private.json"\n'
    'LINEAGE_SAFE_NAME = "selected_lineage.safe.json"\n'
    'R6_REQUEST_NAME = "a1fs_v1_r6_diagnostic_request.private.json"\n'
    'R6_SAFE_NAME = "a1fs_v1_r6_diagnostic_request.safe.json"\n'
    'NEXT_SHORT_STEP = "A1FS-V1-R6_ExternalDiagnosticResponseAndControlledDecisionMaterialization"\n'
    'MATERIALIZATION_REVIEWED_AT = "2000-01-01T00:00:00Z"\n',
    label="runner constants",
)

new_discover_current = '''def _discover_current(files: list[Path]) -> list[dict[str, Any]]:
    coverages: dict[str, list[Path]] = defaultdict(list)
    banks: list[tuple[Path, dict[str, Any]]] = []
    supplies: list[tuple[Path, dict[str, Any]]] = []
    for path in files:
        value = _read(path)
        if value is None:
            continue
        if (
            value.get("task_id") == r3.TASK_ID
            and value.get("schema_version") == r3.SCHEMA_VERSION
            and value.get("validation_status") == r3.STATUS
        ):
            core = {key: child for key, child in value.items() if key != "report_sha256"}
            if value.get("report_sha256") == r3.digest(core):
                coverages[str(value["report_sha256"])].append(path)
        if (
            value.get("task_id") == r4.TASK_ID
            and value.get("schema_version") == r4.BANK_SCHEMA_VERSION
            and value.get("validation_status") == r4.STATUS
            and value.get("private_local_only") is True
            and value.get("selection_contract", {}).get("authority_review_timestamp_externalized") is True
        ):
            core = {key: child for key, child in value.items() if key != "bank_sha256"}
            if value.get("bank_sha256") == r4.digest(core):
                banks.append((path, value))
        if (
            value.get("task_id") == r4.TASK_ID
            and value.get("schema_version") == r4.SCHEMA_VERSION
            and value.get("validation_status") == r4.STATUS
        ):
            core = {key: child for key, child in value.items() if key != "report_sha256"}
            if value.get("report_sha256") == r4.digest(core):
                supplies.append((path, value))

    pairs: dict[tuple[str, str, str], dict[str, Any]] = {}
    for bank_path, bank in banks:
        for supply_path, supply in supplies:
            if bank.get("source_bindings") != supply.get("source_bindings"):
                continue
            coverage_sha = str(supply.get("source_bindings", {}).get("coverage_sha256") or "")
            coverage_paths = coverages.get(coverage_sha, [])
            if not coverage_paths:
                continue
            coverage_path = _choose_path(coverage_paths)
            identity = (
                coverage_sha,
                str(bank["bank_sha256"]),
                str(supply["report_sha256"]),
            )
            candidate = {
                "current_coverage_path": coverage_path,
                "current_coverage_sha256": coverage_sha,
                "current_bank_path": bank_path,
                "current_supply_path": supply_path,
                "current_bank_sha256": bank["bank_sha256"],
                "current_supply_sha256": supply["report_sha256"],
            }
            previous = pairs.get(identity)
            if previous is None or (
                len(coverage_path.parts) + len(bank_path.parts) + len(supply_path.parts),
                str(coverage_path).casefold(),
                str(bank_path).casefold(),
            ) < (
                len(previous["current_coverage_path"].parts)
                + len(previous["current_bank_path"].parts)
                + len(previous["current_supply_path"].parts),
                str(previous["current_coverage_path"]).casefold(),
                str(previous["current_bank_path"]).casefold(),
            ):
                pairs[identity] = candidate
    return list(pairs.values())


'''
text = replace_block(
    text,
    "def _discover_current(",
    "def _merge_pairs(",
    new_discover_current,
    label="discover current block",
)

text = replace_once(
    text,
    '            identity = (str(row["current_bank_sha256"]), str(row["current_supply_sha256"]))\n',
    '            identity = (\n'
    '                str(row["current_coverage_sha256"]),\n'
    '                str(row["current_bank_sha256"]),\n'
    '                str(row["current_supply_sha256"]),\n'
    '            )\n',
    label="merge-pair identity",
)

text = replace_once(
    text,
    '        legacy.file_sha(chain["graph_path"]),\n'
    '        str(pair["current_bank_sha256"]),\n',
    '        legacy.file_sha(chain["graph_path"]),\n'
    '        str(pair["current_coverage_sha256"]),\n'
    '        str(pair["current_bank_sha256"]),\n',
    label="ready candidate rank",
)

lineage_helpers = '''def _load_digest_object(
    path: Path,
    *,
    task_id: str,
    schema_version: str,
    validation_status: str,
    digest_key: str,
    digest_fn,
    code: str,
) -> dict[str, Any]:
    value = _read(path)
    if value is None:
        raise LocalRunnerError(f"{code}_unreadable")
    if (
        value.get("task_id") != task_id
        or value.get("schema_version") != schema_version
        or value.get("validation_status") != validation_status
    ):
        raise LocalRunnerError(f"{code}_identity_or_status_invalid")
    core = {key: child for key, child in value.items() if key != digest_key}
    if value.get(digest_key) != digest_fn(core):
        raise LocalRunnerError(f"{code}_digest_invalid")
    return value


def _persist_selected_lineage_and_build_r6_intake(
    *,
    selected: Mapping[str, Any],
    selected_semantic_identity: tuple[str, str],
    output: Path,
    project: Mapping[str, Any],
) -> dict[str, Any]:
    pair = selected["pair"]
    coverage = _load_digest_object(
        pair["current_coverage_path"],
        task_id=r3.TASK_ID,
        schema_version=r3.SCHEMA_VERSION,
        validation_status=r3.STATUS,
        digest_key="report_sha256",
        digest_fn=r3.digest,
        code="selected_r3",
    )
    bank = _load_digest_object(
        pair["current_bank_path"],
        task_id=r4.TASK_ID,
        schema_version=r4.BANK_SCHEMA_VERSION,
        validation_status=r4.STATUS,
        digest_key="bank_sha256",
        digest_fn=r4.digest,
        code="selected_r4_bank",
    )
    supply = _load_digest_object(
        pair["current_supply_path"],
        task_id=r4.TASK_ID,
        schema_version=r4.SCHEMA_VERSION,
        validation_status=r4.STATUS,
        digest_key="report_sha256",
        digest_fn=r4.digest,
        code="selected_r4_supply",
    )
    if bank.get("source_bindings") != supply.get("source_bindings"):
        raise LocalRunnerError("selected_r4_source_binding_mismatch")
    if supply.get("source_bindings", {}).get("coverage_sha256") != coverage.get("report_sha256"):
        raise LocalRunnerError("selected_r3_r4_coverage_binding_mismatch")

    package_path = output / reconciliation.PACKAGE_NAME
    safe_path = output / reconciliation.SAFE_NAME
    package = _load_digest_object(
        package_path,
        task_id=r5.TASK_ID,
        schema_version=r5.PACKAGE_SCHEMA_VERSION,
        validation_status=r5.STATUS,
        digest_key="package_sha256",
        digest_fn=r5.digest,
        code="reconciled_r5_package",
    )
    safe = _load_digest_object(
        safe_path,
        task_id=r5.TASK_ID,
        schema_version=r5.SAFE_SCHEMA_VERSION,
        validation_status=r5.STATUS,
        digest_key="summary_sha256",
        digest_fn=r5.digest,
        code="reconciled_r5_safe",
    )
    export = project.get("export", {})
    if (
        package.get("package_sha256") != export.get("package_sha256")
        or safe.get("summary_sha256") != export.get("safe_summary_sha256")
    ):
        raise LocalRunnerError("reconciled_r5_export_binding_mismatch")

    coverage_cells = coverage.get("cells")
    supply_cells = supply.get("cell_supply")
    bank_items = bank.get("items")
    entries = package.get("entries")
    if not all(isinstance(rows, list) for rows in (coverage_cells, supply_cells, bank_items, entries)):
        raise LocalRunnerError("selected_lineage_collection_invalid")

    coverage_ids = {
        str(row.get("cell_id"))
        for row in coverage_cells
        if isinstance(row, Mapping) and str(row.get("cell_id") or "")
    }
    supply_by_cell = {
        str(row.get("breadth_cell_id")): row
        for row in supply_cells
        if isinstance(row, Mapping) and str(row.get("breadth_cell_id") or "")
    }
    bank_by_id = {
        str(row.get("item_id")): row
        for row in bank_items
        if isinstance(row, Mapping) and str(row.get("item_id") or "")
    }
    if len(supply_by_cell) != len(supply_cells) or len(bank_by_id) != len(bank_items):
        raise LocalRunnerError("selected_lineage_duplicate_identity")

    entry_cells: set[str] = set()
    entry_items: set[str] = set()
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise LocalRunnerError("reconciled_r5_entry_invalid")
        cell_id = str(entry.get("breadth_cell_id") or "")
        item_id = str(entry.get("item_id") or "")
        supply_row = supply_by_cell.get(cell_id)
        item = bank_by_id.get(item_id)
        if not cell_id or cell_id not in coverage_ids or supply_row is None:
            raise LocalRunnerError(f"reconciled_r5_cell_not_in_selected_lineage:{cell_id}")
        if item is None:
            raise LocalRunnerError(f"reconciled_r5_item_not_in_selected_bank:{item_id}")
        if item_id not in supply_row.get("approved_item_ids", []):
            raise LocalRunnerError(f"reconciled_r5_item_not_approved_for_cell:{item_id}")
        for key in (
            "breadth_cell_id",
            "capability_id",
            "life_task_id",
            "domain",
            "level",
            "skill",
            "purpose",
        ):
            if entry.get(key) != item.get(key):
                raise LocalRunnerError(f"reconciled_r5_bank_binding_mismatch:{item_id}:{key}")
        entry_cells.add(cell_id)
        entry_items.add(item_id)

    if len(entry_cells) != int(project.get("counts", {}).get("mapped_breadth_cell_count", -1)):
        raise LocalRunnerError("selected_lineage_breadth_denominator_mismatch")

    lineage_root = output / "lineage"
    r6_root = output / "r6_intake"
    shutil.rmtree(lineage_root, ignore_errors=True)
    shutil.rmtree(r6_root, ignore_errors=True)
    lineage_root.mkdir(parents=True, exist_ok=True)
    r6_root.mkdir(parents=True, exist_ok=True)

    coverage_output = lineage_root / population.COVERAGE_OUTPUT
    bank_output = lineage_root / population.BANK_OUTPUT
    supply_output = lineage_root / population.SUPPLY_OUTPUT
    _write(coverage_output, coverage)
    _write(bank_output, bank)
    _write(supply_output, supply)

    request, safe_request = r6.build_request(
        evidence_package_path=package_path,
        evidence_safe_path=safe_path,
        bank_path=bank_output,
        coverage_path=coverage_output,
        max_representatives_per_cell=6,
    )
    r6.safe_scan(safe_request)
    request_output = r6_root / R6_REQUEST_NAME
    safe_output = r6_root / R6_SAFE_NAME
    _write(request_output, request)
    _write(safe_output, safe_request)

    source_bindings = {
        "r3_report_sha256": coverage["report_sha256"],
        "r4_bank_sha256": bank["bank_sha256"],
        "r4_supply_sha256": supply["report_sha256"],
        "r5_package_sha256": package["package_sha256"],
        "r5_summary_sha256": safe["summary_sha256"],
        "r6_request_sha256": request["request_sha256"],
        "r6_safe_summary_sha256": safe_request["summary_sha256"],
        "evidence_semantic_identity_sha256": selected_semantic_identity[0],
        "mapping_semantic_identity_sha256": selected_semantic_identity[1],
    }
    claims = {
        "canonical_m1_modified": False,
        "canonical_m2_modified": False,
        "learner_evidence_created": False,
        "learner_outcome_modified": False,
        "model_invoked": False,
        "r6_queue_created": False,
        "r6_report_created": False,
        "r7_report_created": False,
        "mastery_claimed": False,
        "retention_confirmed": False,
        "a2_unlocked": False,
    }
    counts = {
        "attempt_count": len(entries),
        "breadth_cell_count": len(entry_cells),
        "item_count": len(entry_items),
        "representative_evidence_count": request["analysis_window"]["representative_evidence_count"],
    }
    private_core = {
        "task_id": TASK_ID,
        "schema_version": LINEAGE_SCHEMA_VERSION,
        "validation_status": LINEAGE_STATUS,
        "private_local_only": True,
        "source_bindings": source_bindings,
        "artifact_files": {
            "r3_coverage": population.COVERAGE_OUTPUT,
            "r4_bank": population.BANK_OUTPUT,
            "r4_supply": population.SUPPLY_OUTPUT,
            "r6_request": R6_REQUEST_NAME,
            "r6_safe": R6_SAFE_NAME,
        },
        "counts": counts,
        "claim_boundaries": claims,
        "next_short_step": NEXT_SHORT_STEP,
    }
    private_manifest = {**private_core, "lineage_sha256": r5.digest(private_core)}
    safe_core = {
        "task_id": TASK_ID,
        "schema_version": LINEAGE_SAFE_SCHEMA_VERSION,
        "validation_status": LINEAGE_STATUS,
        "source_bindings": source_bindings,
        "counts": counts,
        "r6_intake_ready": True,
        "claim_boundaries": claims,
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe_manifest = {**safe_core, "summary_sha256": r5.digest(safe_core)}
    r6.safe_scan(safe_manifest)
    _write(lineage_root / LINEAGE_PRIVATE_NAME, private_manifest)
    _write(lineage_root / LINEAGE_SAFE_NAME, safe_manifest)

    return {
        "selected_lineage": {
            "validation_status": LINEAGE_STATUS,
            "r3_report_sha256": coverage["report_sha256"],
            "r4_bank_sha256": bank["bank_sha256"],
            "r4_supply_sha256": supply["report_sha256"],
            "breadth_cell_count": len(entry_cells),
            "item_count": len(entry_items),
            "r6_intake_ready": True,
        },
        "r6_intake": {
            "request_sha256": request["request_sha256"],
            "safe_summary_sha256": safe_request["summary_sha256"],
            "representative_evidence_count": request["analysis_window"]["representative_evidence_count"],
            "model_invoked": False,
            "queue_created": False,
            "report_created": False,
        },
    }


'''
text = replace_once(
    text,
    "def _blocked_report(\n",
    lineage_helpers + "def _blocked_report(\n",
    label="lineage helper insertion",
)

text = replace_once(
    text,
    "        selected = next(iter(ready.values()))\n",
    "        selected_semantic_identity, selected = next(iter(ready.items()))\n",
    label="selected semantic identity",
)

text = replace_once(
    text,
    '        if (\n'
    '            project.get("validation_status") != reconciliation.PROJECTED_STATUS\n'
    '            or checked.get("error_count") != 0\n'
    '        ):\n'
    '            raise LocalRunnerError("reconciliation_projection_or_validation_failed")\n'
    '        core = {\n',
    '        if (\n'
    '            project.get("validation_status") != reconciliation.PROJECTED_STATUS\n'
    '            or checked.get("error_count") != 0\n'
    '        ):\n'
    '            raise LocalRunnerError("reconciliation_projection_or_validation_failed")\n'
    '        intake = _persist_selected_lineage_and_build_r6_intake(\n'
    '            selected=selected,\n'
    '            selected_semantic_identity=selected_semantic_identity,\n'
    '            output=output,\n'
    '            project=project,\n'
    '        )\n'
    '        core = {\n',
    label="success lineage invocation",
)

success_marker = '        intake = _persist_selected_lineage_and_build_r6_intake(\n'
text = replace_once_after(
    text,
    success_marker,
    '            "reconciliation": {\n'
    '                "legacy_real_attempt_count": project["counts"]["legacy_real_attempt_count"],\n'
    '                "exact_mapped_attempt_count": project["counts"]["exact_mapped_attempt_count"],\n'
    '                "mapped_breadth_cell_count": project["counts"]["mapped_breadth_cell_count"],\n'
    '                "pass_count": project["counts"]["pass_count"],\n'
    '                "failure_count": project["counts"]["failure_count"],\n'
    '                "package_sha256": project["export"]["package_sha256"],\n'
    '                "safe_summary_sha256": project["export"]["safe_summary_sha256"],\n'
    '            },\n'
    '            "claim_boundaries": {\n',
    '            "reconciliation": {\n'
    '                "legacy_real_attempt_count": project["counts"]["legacy_real_attempt_count"],\n'
    '                "exact_mapped_attempt_count": project["counts"]["exact_mapped_attempt_count"],\n'
    '                "mapped_breadth_cell_count": project["counts"]["mapped_breadth_cell_count"],\n'
    '                "pass_count": project["counts"]["pass_count"],\n'
    '                "failure_count": project["counts"]["failure_count"],\n'
    '                "package_sha256": project["export"]["package_sha256"],\n'
    '                "safe_summary_sha256": project["export"]["safe_summary_sha256"],\n'
    '            },\n'
    '            "selected_lineage": intake["selected_lineage"],\n'
    '            "r6_intake": intake["r6_intake"],\n'
    '            "claim_boundaries": {\n',
    label="success safe readback",
)

text = replace_once_after(
    text,
    success_marker,
    '                "canonical_m2_modified": False,\n'
    '                "mastery_claimed": False,\n',
    '                "canonical_m2_modified": False,\n'
    '                "selected_lineage_persisted": True,\n'
    '                "r6_request_built": True,\n'
    '                "model_invoked": False,\n'
    '                "r6_queue_created": False,\n'
    '                "r6_report_created": False,\n'
    '                "r7_report_created": False,\n'
    '                "mastery_claimed": False,\n',
    label="success claim boundaries",
)

text = replace_once_after(
    text,
    success_marker,
    '            "stop_reason": "REAL_LEARNER_ATTESTATION_REQUIRED",\n'
    '            "next_short_step": NEXT_SHORT_STEP,\n',
    '            "stop_reason": "R6_DIAGNOSTIC_RESPONSE_AND_CONTROLLED_DECISION_REQUIRED",\n'
    '            "next_short_step": NEXT_SHORT_STEP,\n',
    label="success next gate",
)

runner_path.write_text(text, encoding="utf-8")


test_path = Path("tests/ulga/test_a1fs_v1_r8_legacy_real_evidence_reconciliation_local_runner.py")
test_text = test_path.read_text(encoding="utf-8")

if "def _attach_current_r3_coverage(" in test_text:
    raise SystemExit("runner tests already patched")

test_text = replace_once(
    test_text,
    "from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4\n",
    "from ulga.builders import build_a1fs_v1_r3_complete_breadth_denominator_coverage_gap_planner as r3\n"
    "from ulga.builders import build_a1fs_v1_r4_central_question_supply_skill_projection_capacity_governance as r4\n",
    label="test r3 import",
)

test_helper = '''def _attach_current_r3_coverage(data: dict, bank_path: Path, supply_path: Path) -> Path:
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    supply = json.loads(supply_path.read_text(encoding="utf-8"))
    items_by_cell: dict[str, list[dict]] = {}
    for item in bank["items"]:
        items_by_cell.setdefault(str(item["breadth_cell_id"]), []).append(item)

    cells = []
    for row in supply["cell_supply"]:
        cell_id = str(row["breadth_cell_id"])
        items = items_by_cell[cell_id]
        skills = sorted({str(item["skill"]) for item in items})
        empty = {"required": [], "observed": [], "missing": []}
        cells.append({
            "cell_id": cell_id,
            "capability_node_id": f"REF:{row['capability_id']}",
            "capability_id": row["capability_id"],
            "obligation_id": f"OBLIGATION:{cell_id}",
            "life_task_id": row["life_task_id"],
            "domain": row["domain"],
            "status": "DEPLOYED",
            "dimension_coverage": {
                "skills": {"required": skills, "observed": skills, "missing": []},
                "support_levels": deepcopy(empty),
                "initiative_levels": deepcopy(empty),
                "variation_types": deepcopy(empty),
                "transfer_distances": deepcopy(empty),
                "evidence_levels": deepcopy(empty),
                "retention_stages": deepcopy(empty),
            },
            "matching_deployment_ids": [],
            "source_refs": [],
            "next_actions": [],
        })

    status_counts = {name: 0 for name in r3.CELL_STATUSES}
    status_counts["DEPLOYED"] = len(cells)
    core = {
        "task_id": r3.TASK_ID,
        "schema_version": r3.SCHEMA_VERSION,
        "validation_status": r3.STATUS,
        "source_bindings": {
            "ontology_sha256": "1" * 64,
            "graph_sha256": "2" * 64,
            "profiles_sha256": "3" * 64,
            "deployments_sha256": "4" * 64,
            "m10_structural_coverage": None,
        },
        "counts": {
            "required_mastery_node_count": len(cells),
            "required_capability_node_count": len(cells),
            "profile_defined_count": len(cells),
            "profile_missing_count": 0,
            "denominator_cell_count": len(cells),
            "deployment_contract_count": len(cells),
            "gap_count": 0,
            "status_counts": status_counts,
        },
        "coverage_metrics": {
            "structural_ready_count": len(cells),
            "structural_ready_percent": 100.0,
            "retention_complete_count": 0,
            "retention_complete_percent": 0.0,
            "false_100_percent_blocked": True,
            "completion_denominator_source": "FIXTURE_EXPLICIT_CELLS",
        },
        "profile_missing_capability_node_ids": [],
        "cells": cells,
        "ranked_gaps": [],
        "claim_boundaries": {
            "m1_graph_modified": False,
            "m10_structural_coverage_replaced": False,
            "cartesian_product_generated": False,
            "a2_unlocked": False,
            "mastery_claimed": False,
            "retention_claimed_from_structure": False,
            "audio_completion_required": False,
        },
        "next_short_step": r3.NEXT_SHORT_STEP,
    }
    coverage = {**core, "report_sha256": r3.digest(core)}
    coverage_path = data["root"] / "current_coverage.safe.json"
    coverage_path.write_text(
        json.dumps(coverage, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    bindings = dict(supply["source_bindings"])
    bindings["coverage_sha256"] = coverage["report_sha256"]
    bank["source_bindings"] = dict(bindings)
    supply["source_bindings"] = dict(bindings)
    bank_core = {key: value for key, value in bank.items() if key != "bank_sha256"}
    supply_core = {key: value for key, value in supply.items() if key != "report_sha256"}
    bank["bank_sha256"] = r4.digest(bank_core)
    supply["report_sha256"] = r4.digest(supply_core)
    bank_path.write_text(
        json.dumps(bank, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    supply_path.write_text(
        json.dumps(supply, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return coverage_path


'''
test_text = replace_once(
    test_text,
    "def build_local_fixture(root: Path) -> dict:\n",
    test_helper + "def build_local_fixture(root: Path) -> dict:\n",
    label="test coverage helper insertion",
)

test_text = replace_once(
    test_text,
    '    bank_path, supply_path = reconciliation_test.current_r4_fixture(data)\n'
    '    data["current_bank_path"] = bank_path\n'
    '    data["current_supply_path"] = supply_path\n'
    '    return data\n',
    '    bank_path, supply_path = reconciliation_test.current_r4_fixture(data)\n'
    '    coverage_path = _attach_current_r3_coverage(data, bank_path, supply_path)\n'
    '    data["current_coverage_path"] = coverage_path\n'
    '    data["current_bank_path"] = bank_path\n'
    '    data["current_supply_path"] = supply_path\n'
    '    return data\n',
    label="test fixture lineage attachment",
)

new_first_test = '''def test_runner_discovers_unique_chain_and_projects(fixture: dict) -> None:
    report = runner.run(local_root=fixture["local_root"], output_root=fixture["output_root"])
    assert report["validation_status"] == runner.STATUS
    assert report["reconciliation"]["legacy_real_attempt_count"] == 9
    assert report["reconciliation"]["exact_mapped_attempt_count"] == 9
    assert report["reconciliation"]["mapped_breadth_cell_count"] == 9
    assert report["reconciliation"]["pass_count"] == 7
    assert report["reconciliation"]["failure_count"] == 2
    assert report["stop_reason"] == "R6_DIAGNOSTIC_RESPONSE_AND_CONTROLLED_DECISION_REQUIRED"
    assert report["next_short_step"] == runner.NEXT_SHORT_STEP
    assert report["selected_lineage"]["breadth_cell_count"] == 9
    assert report["selected_lineage"]["item_count"] == 9
    assert report["selected_lineage"]["r6_intake_ready"] is True
    assert report["r6_intake"]["representative_evidence_count"] == 9
    assert report["r6_intake"]["model_invoked"] is False

    lineage_root = fixture["output_root"] / "lineage"
    r6_root = fixture["output_root"] / "r6_intake"
    assert (lineage_root / runner.population.COVERAGE_OUTPUT).is_file()
    assert (lineage_root / runner.population.BANK_OUTPUT).is_file()
    assert (lineage_root / runner.population.SUPPLY_OUTPUT).is_file()
    assert (lineage_root / runner.LINEAGE_PRIVATE_NAME).is_file()
    assert (lineage_root / runner.LINEAGE_SAFE_NAME).is_file()
    assert (r6_root / runner.R6_REQUEST_NAME).is_file()
    assert (r6_root / runner.R6_SAFE_NAME).is_file()


'''
test_text = replace_block(
    test_text,
    "def test_runner_discovers_unique_chain_and_projects(",
    "def test_runner_accepts_formal_192_item_m08_bank_with_nine_attempts(",
    new_first_test,
    label="first runner test",
)

test_path.write_text(test_text, encoding="utf-8")

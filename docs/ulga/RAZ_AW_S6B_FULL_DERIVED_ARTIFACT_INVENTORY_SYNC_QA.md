# RAZ-AW-S6B Full Derived Artifact Inventory Sync QA

## 1. Task

`RAZ-AW-S6B_FullDerivedArtifactInventorySyncQA`

## 2. Status

```text
OPERATOR_APPROVED = true
TASK_TYPE = QA / INVENTORY_SYNC_CONTRACT
FINAL_QA_REPORT = pending_local_execution
```

This document records the approved S6B execution contract. It is not itself the final local QA run result.

## 3. Purpose

The operator clarified that complete RAZ A-W JSON now exists. The previous S6A QA was based on older committed inventory evidence that still showed A-F/A-H/I-W split readiness.

S6B must reconcile the repository inventory and reports with the actual complete A-W derived artifacts.

Goal:

```text
Confirm complete A-W derived artifact availability.
Refresh or validate inventory/report evidence.
Remove stale A-F-only assumptions.
Prepare one unified A-W Reading Authority Intake path.
```

## 4. Non-Goals

S6B must not:

```text
promote Reading Authority content
create final reading_authority.json
modify learner state
modify planner runtime
modify API/dashboard/scheduler behavior
generate new learner-facing content
approve generated or rewritten content
weaken candidate_only or promotion_allowed=false guardrails
```

## 5. Required Inputs To Inspect

Local/Codex execution should inspect the actual committed or staged A-W derived artifacts, including:

```text
raz_output_jsons/derived/Level_{A-W}/normalized/*
raz_output_jsons/derived/Level_{A-W}/enriched/*
raz_output_jsons/derived/reports/*
ulga/graph/raz_level_discovery_inventory.json
ulga/reports/raz_level_discovery_summary.json
ulga/reports/raz_level_discovery_validation.json
ulga/reports/raz_reusable_content_seed_query_layer_summary.json
ulga/reports/raz_reusable_content_seed_query_layer_validation.json
ulga/reports/raz_downstream_discovery_drift_validation.json
```

If large A-W JSON files are stored outside GitHub, the QA must record the storage location and commit only lightweight inventory/report metadata to GitHub.

## 6. Required Checks

S6B must verify, for every level A-W:

```text
normalized sentence file exists
normalized page_unit file exists
normalized reuse_unit file exists
enriched sentence file exists
enriched page_unit file exists
enriched reuse_unit file exists
counts are greater than zero
raw/normalized/enriched count parity is explainable
missing_artifacts is empty or intentionally justified
query_layer_ready is accurate
candidate_only is preserved
promotion_allowed is false
```

Special check:

```text
Level I smoke-pilot evidence must align with current inventory and actual files.
```

## 7. Required Outputs

S6B should produce or refresh lightweight QA artifacts such as:

```text
docs/ulga/RAZ_AW_S6B_FULL_DERIVED_ARTIFACT_INVENTORY_SYNC_QA.md
ulga/reports/raz_aw_full_derived_inventory_sync_summary.json
ulga/reports/raz_aw_full_derived_inventory_sync_validation.json
ulga/graph/raz_level_discovery_inventory.json
ulga/reports/raz_level_discovery_summary.json
ulga/reports/raz_level_discovery_validation.json
```

If implementation chooses not to refresh an existing report, the final QA report must explain why.

## 8. Acceptance Criteria

S6B passes only if:

```text
A-W actual derived artifact availability is confirmed
A-W normalized/enriched state is reflected in inventory or explicitly reported
Level I discrepancy is resolved
A-F-only readiness language is no longer used as the final implementation path
A-W unified S7 readiness is either PASS or blocked with exact missing evidence
no content promotion occurs
no runtime behavior changes
```

## 9. Expected Final Verdict Format

The final local QA report should end with one of:

```text
RAZ-AW-S6B_STATUS = PASS_AW_READY_FOR_S7
RAZ-AW-S6B_STATUS = PASS_WITH_WARNINGS_AW_READY_FOR_S7
RAZ-AW-S6B_STATUS = BLOCKED_WITH_MISSING_ARTIFACTS
RAZ-AW-S6B_STATUS = BLOCKED_WITH_INVENTORY_MISMATCH
```

## 10. Recommended Next Task After S6B

If S6B passes:

```text
RAZ-AW-S7_ReadingAuthorityIntake_SchemaImplementation
```

If S6B is blocked:

```text
RAZ-AW-S6C_FullDerivedArtifactSyncFix
```

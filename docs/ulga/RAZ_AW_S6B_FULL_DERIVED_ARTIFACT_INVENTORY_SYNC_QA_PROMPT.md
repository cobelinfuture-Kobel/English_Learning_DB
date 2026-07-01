# RAZ-AW-S6B Full Derived Artifact Inventory Sync QA Prompt

Use this prompt in Codex/local repo execution.

## Task

`RAZ-AW-S6B_FullDerivedArtifactInventorySyncQA`

## Objective

Run a full A-W derived artifact inventory sync QA.

The operator has clarified that complete A-W JSON now exists. Do not keep the implementation path limited to A-F unless actual file evidence proves A-W is still unavailable.

## Scope

QA and inventory/report synchronization only.

Do not promote content. Do not create learner-facing Reading Authority items. Do not modify runtime, planner, learner state, API, dashboard, scheduler, or generated content pipelines.

## Preflight

Before modifying anything:

1. Parse existing JSON files that will be inspected.
2. Confirm `docs/ulga/RAZ_AW_S6B_FULL_DERIVED_ARTIFACT_INVENTORY_SYNC_QA.md` exists.
3. Confirm `docs/ulga/RAZ_AW_S6A_READING_AUTHORITY_INPUT_COVERAGE_QA.md` exists.
4. Inspect `ulga/graph/raz_level_discovery_inventory.json`.
5. Inspect `ulga/reports/raz_level_discovery_summary.json`.
6. Inspect `ulga/reports/raz_level_discovery_validation.json`.
7. Inspect actual `raz_output_jsons/derived/Level_{A-W}` folders.
8. Record whether A-W derived JSON is committed in GitHub or stored externally.

## Required File Presence Checks

For every level A-W, check the presence and count of:

```text
raz_output_jsons/derived/Level_{LEVEL}/normalized/raz_{LEVEL}_sentence_normalized.jsonl
raz_output_jsons/derived/Level_{LEVEL}/normalized/raz_{LEVEL}_page_unit_normalized.json
raz_output_jsons/derived/Level_{LEVEL}/normalized/raz_{LEVEL}_reuse_unit_normalized.json
raz_output_jsons/derived/Level_{LEVEL}/enriched/raz_{LEVEL}_sentence_enriched.jsonl
raz_output_jsons/derived/Level_{LEVEL}/enriched/raz_{LEVEL}_page_unit_enriched.json
raz_output_jsons/derived/Level_{LEVEL}/enriched/raz_{LEVEL}_reuse_unit_enriched.json
```

If filenames differ, do not silently assume failure. First inspect the directory and record actual filenames.

## Required Count Checks

For every level A-W, produce counts for:

```text
raw_sentence_candidate_count
raw_page_unit_count
raw_reuse_unit_count
normalized_sentence_count
normalized_page_unit_count
normalized_reuse_unit_count
enriched_sentence_count
enriched_page_unit_count
enriched_reuse_unit_count
missing_artifacts
query_layer_ready
query_layer_approved
authority_status
promotion_allowed
```

## Required Guardrails

All levels must preserve:

```text
authority_status = candidate_only
promotion_allowed = false
```

If any artifact claims promoted or approved learner-facing Reading Authority status, treat that as a blocker.

## Required Output Artifacts

Create or refresh:

```text
ulga/reports/raz_aw_full_derived_inventory_sync_summary.json
ulga/reports/raz_aw_full_derived_inventory_sync_validation.json
docs/ulga/RAZ_AW_S6B_FULL_DERIVED_ARTIFACT_INVENTORY_SYNC_QA.md
```

If the existing discovery inventory is stale and the project design permits refreshing it, refresh:

```text
ulga/graph/raz_level_discovery_inventory.json
ulga/reports/raz_level_discovery_summary.json
ulga/reports/raz_level_discovery_validation.json
```

If you choose not to refresh existing discovery artifacts, explain why in the final QA report.

## Validation Rules

S6B passes only if:

```text
A-W derived artifact availability is confirmed
A-W normalized/enriched counts are reflected in report evidence
Level I smoke-pilot mismatch is resolved or explicitly explained
A-F-only implementation is not recommended as the final path
A-W unified S7 path is either approved or blocked with exact missing evidence
no content promotion occurs
no runtime behavior changes
```

## Final Verdict

End the report with exactly one of:

```text
RAZ-AW-S6B_STATUS = PASS_AW_READY_FOR_S7
RAZ-AW-S6B_STATUS = PASS_WITH_WARNINGS_AW_READY_FOR_S7
RAZ-AW-S6B_STATUS = BLOCKED_WITH_MISSING_ARTIFACTS
RAZ-AW-S6B_STATUS = BLOCKED_WITH_INVENTORY_MISMATCH
```

## Recommended Next Task

If S6B passes:

```text
RAZ-AW-S7_ReadingAuthorityIntake_SchemaImplementation
```

If S6B is blocked:

```text
RAZ-AW-S6C_FullDerivedArtifactSyncFix
```

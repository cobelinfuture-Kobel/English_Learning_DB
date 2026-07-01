# RAZ-AW-S6A Reading Authority Input Coverage QA

## 1. Task

`RAZ-AW-S6A_ReadingAuthorityInputCoverageQA`

## 2. Scope

QA-only follow-up to `RAZ-AW-S6_ReadingAuthorityIntake_DesignScan`.

No builder, validator, runtime, learner-state, planner, extraction, or authority artifact was changed by this QA.

## 3. Files Inspected

```text
docs/ulga/RAZ_AW_S6_READING_AUTHORITY_INTAKE_DESIGNSCAN.md
ulga/reports/raz_level_discovery_summary.json
ulga/reports/raz_level_discovery_validation.json
ulga/graph/raz_level_discovery_inventory.json
ulga/reports/raz_reusable_content_seed_query_layer_summary.json
docs/ulga/RAZ_S6U_I_DERIVED_BUILD_THIRD_SMOKE_PILOT.md
docs/ulga/ULGA_S11_READING_DIALOGUE_CONTENT_AUTHORITY_DESIGN_SCAN.md
docs/ulga/ULGA_S11A_READING_AUTHORITY_DESIGN_SCAN.md
docs/ulga/ULGA_S11B_READING_STUB_AUTHORITY_IMPLEMENTATION.md
```

## 4. Evidence Summary

`raz_level_discovery_summary.json` reports:

```text
total_detected_levels = 23
ready_level_count = 23
levels = A-W
levels_ready_for_sentence_pipeline = A-W
levels_ready_for_page_unit_pipeline = A-W
levels_ready_for_reuse_unit_pipeline = A-W
levels_query_layer_ready = A-F
```

`raz_level_discovery_validation.json` reports:

```text
status = PASS
total_detected_levels = 23
READY_FOR_REUSE_UNIT_PIPELINE = A-W
```

The detailed inventory available during this QA gave a stricter readiness split:

```text
A-F: normalized/enriched counts present; query_layer_ready = true
G-H: normalized/enriched counts present; query_layer_ready = false
I-W: raw candidates present; normalized/enriched counts = 0; query_layer_ready = false
```

## 5. Operator Update After QA

After this QA was first written, the operator clarified that the project now has complete A-W JSON, whereas the earlier limitation came from only having A-F JSON available.

Therefore, this QA should not be used to justify building only A-F long-term.

Updated interpretation:

```text
If complete A-W JSON now exists, the correct route is to synchronize committed inventory/reports to the new A-W derived reality, then proceed with a unified A-W intake schema.
```

Key boundary:

```text
Do not build a permanent A-F half implementation.
Do not directly promote A-W content.
First refresh/sync inventory evidence, then implement A-W intake consistently.
```

## 6. Coverage Verdict

| Scope | Original QA Result | Updated Handling |
|---|---|---|
| A-F | PASS_FOR_S7_SCHEMA_PILOT | Still safe, but should not become the final-only scope. |
| G-H | PASS_FOR_OPTIONAL_DRY_RUN_ONLY | Include in full sync if A-W JSON is complete. |
| I-W | FAIL_FOR_S7_FULL_SCOPE based on stale/old inventory | Recheck through full derived inventory sync. |
| Full A-W | BLOCKED under old inventory | Target scope after inventory sync confirms complete JSON. |

## 7. Group Totals From Old Inventory

| Group | Levels | Sentence Records | Page Units | Reuse Units | Query Layer Ready |
|---|---|---:|---:|---:|---|
| A-F | 6 | 7,487 | 4,925 | 2,010 | Yes |
| G-H | 2 | 4,990 | 1,945 | 1,680 | No |
| I-W | 15 | 189,519 raw candidates | 15,762 raw page units | 15,642 raw reuse units | No |

These totals describe the older committed inventory view, not necessarily the operator-confirmed latest full A-W JSON state.

## 8. Level I Discrepancy

The S6U Level I smoke-pilot document reports Level I derived build parity and schema validation as passing.

However, the inventory inspected during this QA still reported Level I with zero normalized/enriched counts and missing normalized/enriched artifacts.

Updated interpretation:

```text
This is likely an inventory/report synchronization issue if A-W JSON now exists.
S6B should refresh and verify inventory against actual A-W derived artifacts before S7.
```

## 9. Revised Gate Verdicts

```text
FULL_AW_S7_GATE = PENDING_FULL_INVENTORY_SYNC
AF_ONLY_IMPLEMENTATION = NOT_RECOMMENDED_AS_FINAL_PATH
AW_UNIFIED_IMPLEMENTATION = RECOMMENDED_AFTER_SYNC
AUTHORITY_PROMOTION = STILL_NOT_ALLOWED
```

Required guardrails for the next stage:

```text
confirm A-W normalized/enriched artifacts
refresh inventory/report evidence
preserve candidate_only status
preserve promotion_allowed = false
no generated content promotion
no runtime mutation
no final reading_authority.json promotion during intake staging
```

## 10. Final Verdict

```text
RAZ-AW-S6A_ReadingAuthorityInputCoverageQA = COMPLETE
ORIGINAL_FULL_AW_READY_FROM_OLD_INVENTORY = false
OPERATOR_CONFIRMED_FULL_AW_JSON_AVAILABLE = true
NEXT_REQUIRED_ACTION = FULL_DERIVED_ARTIFACT_INVENTORY_SYNC_QA
```

## 11. Revised Recommended Next Task

Preferred next task:

```text
RAZ-AW-S6B_FullDerivedArtifactInventorySyncQA
```

Purpose:

```text
Confirm actual A-W JSON availability.
Refresh or validate inventory and reports against complete A-W derived artifacts.
Resolve stale A-F/A-H/I-W readiness evidence.
Decide the unified A-W S7 implementation scope.
Prevent a permanent A-F half implementation.
```

After S6B passes, proceed to:

```text
RAZ-AW-S7_ReadingAuthorityIntake_SchemaImplementation
```

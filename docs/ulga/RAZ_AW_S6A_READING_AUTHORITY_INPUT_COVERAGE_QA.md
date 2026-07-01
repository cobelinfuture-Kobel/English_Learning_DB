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

The detailed inventory gives a stricter readiness split:

```text
A-F: normalized/enriched counts present; query_layer_ready = true
G-H: normalized/enriched counts present; query_layer_ready = false
I-W: raw candidates present; normalized/enriched counts = 0; query_layer_ready = false
```

## 5. Coverage Verdict

| Scope | Result | Reason |
|---|---|---|
| A-F | PASS_FOR_S7_SCHEMA_PILOT | Normalized/enriched counts are present and query layer is ready. |
| G-H | PASS_FOR_OPTIONAL_DRY_RUN_ONLY | Normalized/enriched counts are present, but query layer is not ready. |
| I-W | FAIL_FOR_S7_FULL_SCOPE | Raw candidates exist, but inventory shows normalized/enriched counts as 0. |
| Full A-W | BLOCKED | Discovery readiness does not equal intake readiness. |

## 6. Group Totals

| Group | Levels | Sentence Records | Page Units | Reuse Units | Query Layer Ready |
|---|---|---:|---:|---:|---|
| A-F | 6 | 7,487 | 4,925 | 2,010 | Yes |
| G-H | 2 | 4,990 | 1,945 | 1,680 | No |
| I-W | 15 | 189,519 raw candidates | 15,762 raw page units | 15,642 raw reuse units | No |

## 7. Level I Discrepancy

The S6U Level I smoke-pilot document reports Level I derived build parity and schema validation as passing.

However, current committed `raz_level_discovery_inventory.json` still reports Level I with zero normalized/enriched counts and missing normalized/enriched artifacts.

QA interpretation:

```text
Level I has historical smoke-pilot evidence, but current committed inventory/content availability is not aligned enough to treat Level I as S7-ready.
```

This blocks full A-W implementation.

## 8. Gate Verdicts

```text
FULL_AW_S7_GATE = BLOCKED
AF_S7_SCHEMA_PILOT_GATE = PASS_WITH_GUARDRAILS
GH_DRY_RUN_GATE = PASS_WITH_WARNINGS
IW_GATE = FAIL
```

Guardrails for any S7 pilot:

```text
levels = A-F by default
no content promotion
no runtime mutation
no final reading_authority.json promotion
schema or staging only
```

## 9. Final Verdict

```text
RAZ-AW-S6A_ReadingAuthorityInputCoverageQA = COMPLETE
READING_AUTHORITY_INTAKE_FULL_AW_READY = false
READING_AUTHORITY_INTAKE_AF_PILOT_READY = true
```

## 10. Recommended Next Task

Preferred next task:

```text
RAZ-AW-S6B_LevelIAndGW_DerivedInventoryAlignmentPlan
```

Purpose:

```text
Resolve the mismatch between Level I smoke-pilot evidence and committed inventory state.
Decide whether G-W should be rebuilt, recommitted, or excluded from first intake implementation.
Clarify whether S7 should be A-F pilot-first or A-H dry-run plus A-F pilot.
```

Fast safe alternative:

```text
RAZ-AF-S7_ReadingAuthorityIntake_SchemaPilotImplementation
```

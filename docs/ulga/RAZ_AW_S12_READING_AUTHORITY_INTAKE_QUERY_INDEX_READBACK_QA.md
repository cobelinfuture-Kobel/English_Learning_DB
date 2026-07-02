# RAZ-AW-S12 Reading Authority Intake Query Index Readback QA

## 1. Task

`RAZ-AW-S12_ReadingAuthorityIntake_QueryIndexReadbackQA`

This stage performs readback QA against the locally generated S11 query index and summary artifacts. It does not rebuild upstream sources and does not modify runtime state.

## 2. Scope

- read back `ulga/graph/raz_reading_authority_intake_query_index.json`
- read back `ulga/reports/raz_reading_authority_intake_query_index_summary.json`
- compare index shape against summary counts
- inspect warning distribution
- inspect level coverage, source traceability, and tag normalization
- preserve candidate-only / no-promotion / no-generated-content boundaries

## 3. Files Created

- `ulga/audits/audit_raz_reading_authority_intake_query_index_readback.py`
- `tests/ulga/test_raz_reading_authority_intake_query_index_readback_qa.py`
- `docs/ulga/RAZ_AW_S12_READING_AUTHORITY_INTAKE_QUERY_INDEX_READBACK_QA.md`
- `ulga/reports/raz_reading_authority_intake_query_index_readback_qa.json`

## 4. Readback Result

Current local result: `FAIL`

This is not a promotion-safety failure. Candidate-only / no-promotion boundaries still hold. The failure is due to structural query-index quality defects that should be patched in S11 before downstream consumers depend on the index.

## 5. Findings

### High

1. `S10A_SOURCE_LEVELS_DROPPED`
   All `243,957` records read from `ulga/graph/raz_reading_authority_intake_candidates.json` were indexed as `level=UNKNOWN` even though the source artifact already carries level data via `source_level` / `normalized_level`.

2. `MALFORMED_REUSABILITY_TAGS`
   `28,465` indexed items contain dict-stringified reusability tags. This indicates metadata blobs were converted into query tags instead of normalized tag strings.

### Medium

1. `SOURCE_RECORD_ID_NOT_PROPAGATED`
   S10A source records have stable `reading_intake_id` values, but the corresponding S11 index items did not carry them into `source_traceability.source_record_id`.

2. `WARNING_SCOPE_NOT_BRIDGE_ONLY`
   The `202` warnings are not only bridge-candidate artifacts. They include both:
   - bridge candidate artifacts
   - derived artifact paths under `raz_output_jsons/derived/...`

## 6. Boundary Check

- authority promotion remains disabled
- generated content remains disabled
- candidate-only status remains preserved
- no runtime / scheduler / dashboard / learner-state integration was touched

## 7. Recommended Next Task

`RAZ-AW-S11_ReadingAuthorityIntake_QueryIndexBuilderPatch`

Minimal patch focus:

1. map S10A source levels from `source_level` / `normalized_level`
2. propagate `reading_intake_id` into `source_traceability.source_record_id`
3. reject dict-shaped `reusability_tags` inputs unless normalized to string tags first

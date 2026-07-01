# RAZ-AW-S8 Reading Authority Intake Builder Implementation Prompt

Use this prompt in Codex/local repo execution.

## 1. Task

`RAZ-AW-S8_ReadingAuthorityIntake_BuilderImplementation`

## 2. Objective

Implement the deterministic builder that converts existing RAZ A-W enriched derived artifacts into Reading Authority Intake candidate staging records.

S8 consumes the S7 schema contract and produces candidate-only staging output.

S8 must not promote content into final Reading Authority.

## 3. Required Predecessors

Required completed stages:

```text
RAZ-AW-S6_ReadingAuthorityIntake_DesignScan
RAZ-AW-S6A_ReadingAuthorityInputCoverageQA
RAZ-AW-S6B_FullDerivedArtifactInventorySyncQA
RAZ-AW-S6B1_CanonicalDerivedCounterCompatFullFix
RAZ-AW-S7_ReadingAuthorityIntake_SchemaImplementation
```

Required evidence:

```text
RAZ-AW-S6B_STATUS = PASS_AW_READY_FOR_S7
RAZ-AW-S7_ReadingAuthorityIntake_SchemaImplementation = PASS
```

S7 created a deterministic schema, validator, tests, fixture records, and reports, but did not implement builder output.

## 4. Strict Scope

Allowed:

```text
builder implementation
builder tests
builder output reports
candidate-only intake staging records
schema validator reuse
small deterministic helpers for source mapping
```

Forbidden:

```text
final reading_authority.json creation
Reading Authority promotion
promotion_allowed=true
final_eligible=true
authority_status other than candidate_only
LLM-generated learner-facing content
rewritten dialogue/writing/exercise content
query-layer approved-level expansion
runtime changes
learner state changes
planner changes
API/dashboard/scheduler changes
mutation of source RAZ derived artifacts
```

## 5. Input Artifacts

S8 must read actual A-W enriched artifacts:

```text
raz_output_jsons/derived/Level_{A-W}/enriched/raz_{LEVEL}_sentence_enriched.jsonl
raz_output_jsons/derived/Level_{A-W}/enriched/raz_{LEVEL}_page_unit_enriched.json
raz_output_jsons/derived/Level_{A-W}/enriched/raz_{LEVEL}_reuse_unit_enriched.json
```

If a level uses legacy names, inspect and support existing compatibility names already accepted by `build_raz_level_discovery.py`, but do not invent undocumented paths silently.

Also read:

```text
ulga/schemas/raz_reading_authority_intake.schema.json
ulga/validators/validate_raz_reading_authority_intake_schema.py
ulga/reports/raz_aw_full_derived_inventory_sync_summary.json
ulga/reports/raz_aw_full_derived_inventory_sync_validation.json
ulga/graph/raz_level_discovery_inventory.json
```

## 6. Required Output Artifacts

Preferred outputs:

```text
ulga/builders/build_raz_reading_authority_intake.py
ulga/graph/raz_reading_authority_intake_candidates.json
ulga/reports/raz_reading_authority_intake_builder_summary.json
ulga/reports/raz_reading_authority_intake_builder_validation.json
tests/ulga/test_raz_reading_authority_intake_builder.py
docs/ulga/RAZ_AW_S8_READING_AUTHORITY_INTAKE_BUILDER_IMPLEMENTATION.md
```

Do not create:

```text
ulga/graph/reading_authority.json
ulga/graph/final_reading_authority.json
```

unless the file is explicitly candidate-only and named as intake staging. Prefer `raz_reading_authority_intake_candidates.json`.

## 7. Builder Contract

The builder must generate `reading_intake_candidate` records conforming to:

```text
ulga/schemas/raz_reading_authority_intake.schema.json
```

The output payload should support validator-compatible format:

```json
{
  "task": "RAZ-AW-S8_ReadingAuthorityIntake_BuilderImplementation",
  "schema_version": "raz_reading_authority_intake.v1",
  "records": []
}
```

Each record must include:

```text
reading_intake_id
schema_version
source
source_level
normalized_level
unit_type
source_traceability
text
pedagogical_tags
authority
qa
query_layer_ready
query_layer_approved
```

## 8. ID Rules

Use deterministic IDs.

Recommended formats:

```text
RAZ_{LEVEL}_{BOOK_ID}_SENT_{NNNNNN}
RAZ_{LEVEL}_{BOOK_ID}_PAGE_{NNNNNN}
RAZ_{LEVEL}_{BOOK_ID}_REUSE_{NNNNNN}
```

If source record IDs already contain stable IDs, derive the intake ID from them deterministically.

ID collisions are blocking errors.

## 9. Source Mapping Rules

### 9.1 Sentence enriched input

Map to:

```text
unit_type = sentence
source_traceability.source_type = raz_enriched_sentence
```

Text should come from the best available original clean-text field. Inspect actual field names. Do not use generated/rewrite fields.

### 9.2 Page unit enriched input

Map to:

```text
unit_type = page_unit
source_traceability.source_type = raz_enriched_page_unit
```

Must preserve:

```text
page_number
page_unit_id
source_sentence_candidate_ids
sentence_count
clean_text
```

### 9.3 Reuse unit enriched input

Map to:

```text
unit_type = reuse_unit
source_traceability.source_type = raz_enriched_reuse_unit
```

Must preserve:

```text
source_page_unit_id or page_unit_id
source_sentence_candidate_ids
reusability_tags where available
sentence_count
clean_text
```

## 10. Authority Guardrails

Every output record must set:

```json
{
  "authority": {
    "authority_status": "candidate_only",
    "promotion_status": "not_promoted",
    "promotion_allowed": false,
    "requires_review": true,
    "review_status": "pending",
    "final_eligible": false
  }
}
```

Every source traceability must set:

```json
{
  "derived_from_original_text": true,
  "generated_content": false
}
```

If a source artifact indicates generated content, rewritten content, dialogue rewrite, writing rewrite, or exercise generation, the builder must block that record and report it. It must not silently include it.

## 11. Query Layer Rule

S8 must preserve current query-layer readiness from existing inventory/policy.

Current expected state after S6B/S7:

```text
query_layer_ready = A-F
query_layer_approved = A-F
G-W may have query_layer_ready=false
```

G-W query_layer_ready=false must not block intake candidate staging.

S8 is not query-layer expansion.

## 12. Required Summary Report

Create:

```text
ulga/reports/raz_reading_authority_intake_builder_summary.json
```

Suggested fields:

```json
{
  "task": "RAZ-AW-S8_ReadingAuthorityIntake_BuilderImplementation",
  "status": "IMPLEMENTED",
  "schema_version": "raz_reading_authority_intake.v1",
  "levels_processed": ["A", "...", "W"],
  "total_records": 0,
  "records_by_unit_type": {
    "sentence": 0,
    "page_unit": 0,
    "reuse_unit": 0
  },
  "records_by_level": {},
  "query_layer_ready_levels": ["A", "B", "C", "D", "E", "F"],
  "authority_status": "candidate_only",
  "promotion_allowed": false,
  "generated_content_allowed": false,
  "blocked_record_count": 0,
  "warning_count": 0,
  "recommended_next_task": "RAZ-AW-S9_ReadingAuthorityIntake_BuilderQA"
}
```

## 13. Required Validation Report

Create:

```text
ulga/reports/raz_reading_authority_intake_builder_validation.json
```

Suggested fields:

```json
{
  "task": "RAZ-AW-S8_ReadingAuthorityIntake_BuilderImplementation",
  "status": "PASS",
  "schema_validation_status": "PASS",
  "blocking_error_count": 0,
  "warning_count": 0,
  "records_checked": 0,
  "duplicate_id_count": 0,
  "promotion_violation_count": 0,
  "generated_content_violation_count": 0,
  "missing_traceability_count": 0,
  "blocked_records": [],
  "warnings": []
}
```

## 14. Required Tests

Add tests covering:

```text
builder maps valid sentence enriched record to intake candidate
builder maps valid page_unit enriched record to intake candidate
builder maps valid reuse_unit enriched record to intake candidate
A-W level support
candidate_only invariant
promotion_allowed=false invariant
generated_content=true source is blocked
missing clean_text is blocked or excluded with blocking report
missing source traceability is blocked
query_layer_ready=false for G-W is preserved and not blocking
duplicate intake IDs are blocked
output validates with S7 schema validator
reports are written deterministically
```

Use small temporary fixtures. Do not rely on the full A-W corpus for unit tests.

## 15. Required Commands

Run focused tests:

```powershell
python -m pytest tests/ulga/test_raz_reading_authority_intake_builder.py -q
```

Run schema tests:

```powershell
python -m pytest tests/ulga/test_raz_reading_authority_intake_schema.py -q
```

Run builder:

```powershell
python ulga/builders/build_raz_reading_authority_intake.py
```

Run validator:

```powershell
python ulga/validators/validate_raz_reading_authority_intake_schema.py ulga/graph/raz_reading_authority_intake_candidates.json
```

Run ULGA tests:

```powershell
python -m pytest tests/ulga -q
```

If feasible, run full tests:

```powershell
python -m pytest tests -q
```

Record unrelated pre-existing failures separately and do not mask them as S8 failures.

## 16. Acceptance Criteria

S8 passes only if:

```text
builder exists
candidate output exists
summary report exists
validation report exists
tests exist
focused tests pass
schema validation passes
all records are candidate_only
all records have promotion_allowed=false
all records have generated_content=false
A-W levels are processed or explicitly reported if skipped
G-W query_layer_ready=false does not block staging
no final Reading Authority promotion occurs
no runtime/learner-state/planner/API/dashboard/scheduler changes occur
```

## 17. Final Report Format

Final response must include:

```text
1. Preflight
2. Files inspected
3. Files created / modified
4. Builder mapping implemented
5. Output counts by level and unit_type
6. Blocking / warning summary
7. Tests added / modified
8. Commands executed
9. Test results
10. Guardrail confirmation
11. Final verdict
12. Recommended next task
```

Final verdict:

```text
RAZ-AW-S8_ReadingAuthorityIntake_BuilderImplementation = PASS
```

Recommended next task:

```text
RAZ-AW-S9_ReadingAuthorityIntake_BuilderQA
```

If S8 is blocked, use:

```text
RAZ-AW-S8B_ReadingAuthorityIntake_BuilderFix
```

# RAZ-AW-S7 Reading Authority Intake Schema Implementation

## 1. Task

`RAZ-AW-S7_ReadingAuthorityIntake_SchemaImplementation`

## 2. Scope

This task implements:

```text
schema JSON
schema validator
schema-level tests
summary / validation reports
small fixture records for schema validation
```

This task does not implement:

```text
final reading_authority.json
promotion
builder output
query-layer expansion
runtime / learner state / planner / API / dashboard / scheduler changes
learner-facing generated content
```

## 3. Files Inspected

```text
docs/ulga/RAZ_AW_S6_READING_AUTHORITY_INTAKE_DESIGNSCAN.md
docs/ulga/RAZ_AW_S6A_READING_AUTHORITY_INPUT_COVERAGE_QA.md
docs/ulga/RAZ_AW_S6B_FULL_DERIVED_ARTIFACT_INVENTORY_SYNC_QA.md
ulga/reports/raz_aw_full_derived_inventory_sync_summary.json
ulga/reports/raz_aw_full_derived_inventory_sync_validation.json
ulga/graph/raz_level_discovery_inventory.json
ulga/reports/raz_level_discovery_summary.json
ulga/reports/raz_level_discovery_validation.json
ulga/schemas/reading_content_authority_schema.json
ulga/validators/validate_reading_dialogue_content_authority_schema.py
tests/ulga/test_reading_dialogue_content_authority_schema.py
```

## 4. Files Created / Modified

```text
ulga/schemas/raz_reading_authority_intake.schema.json
ulga/schemas/sample_raz_reading_authority_intake_candidates.json
ulga/validators/validate_raz_reading_authority_intake_schema.py
tests/ulga/test_raz_reading_authority_intake_schema.py
ulga/reports/raz_reading_authority_intake_schema_summary.json
ulga/reports/raz_reading_authority_intake_schema_validation.json
docs/ulga/RAZ_AW_S7_READING_AUTHORITY_INTAKE_SCHEMA_IMPLEMENTATION.md
```

## 5. Implemented Contract

S7 defines a deterministic `reading_intake_candidate` staging record for original RAZ-derived:

```text
sentence
page_unit
reuse_unit
```

Supported payload shapes in the validator:

```text
single candidate object
list of candidate objects
object with records array
```

## 6. Schema Fields Implemented

Implemented top-level fields:

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

Implemented enforced constants / enums:

```text
schema_version = raz_reading_authority_intake.v1
source = RAZ
source_level enum = A-W
normalized_level enum = A-W
unit_type enum = sentence | page_unit | reuse_unit
authority.authority_status = candidate_only
authority.promotion_status = not_promoted
authority.promotion_allowed = false
authority.requires_review = true
authority.final_eligible = false
source_traceability.derived_from_original_text = true
source_traceability.generated_content = false
text.text_language = en
text.text_role = reading_source_text
```

## 7. Blocking Rules Implemented

The schema / validator blocks:

```text
missing reading_intake_id
invalid source_level outside A-W
invalid unit_type
missing source_traceability
missing source_artifact_path
missing source_record_id
missing book_id
empty source_sentence_candidate_ids
generated_content = true
derived_from_original_text != true
missing clean_text
empty clean_text
sentence_count <= 0
unit_type conflicts with source_type
authority_status != candidate_only
promotion_allowed != false
promotion_status != not_promoted
review_status missing
final_eligible = true
page_number missing for page_unit / reuse_unit
page_unit_id missing for page_unit / reuse_unit
duplicate intake ids inside one payload
```

Warnings but not blockers:

```text
cefr_estimate missing
theme / vocabulary / grammar / pattern tags empty
book_title missing
word_count missing or computed downstream
query_layer_ready false for G-W
non-blocking K/M sentence count parity note inherited from S6B
```

## 8. Test Coverage

Added tests for:

```text
valid sentence candidate passes
valid page_unit candidate passes
valid reuse_unit candidate passes
generated_content=true is blocked
promotion_allowed=true is blocked
authority_status != candidate_only is blocked
missing source_traceability is blocked
missing clean_text is blocked
invalid source_level is blocked
query_layer_ready false is not a schema blocker
object.records payload is accepted
list payload is accepted
validator script writes PASS reports
```

## 9. Reports

Generated report artifacts:

```text
ulga/reports/raz_reading_authority_intake_schema_summary.json
ulga/reports/raz_reading_authority_intake_schema_validation.json
```

Summary keeps these boundaries explicit:

```text
builder_implemented = false
authority_promotion_implemented = false
generated_content_allowed = false
promotion_allowed = false
```

## 10. Guardrails

Confirmed:

```text
No Reading Authority promotion
No final reading_authority.json
No query-layer approved-level expansion
No runtime changes
No learner state changes
No planner changes
No API/dashboard/scheduler changes
No derived artifact rebuild
```

## 11. Recommended Next Task

```text
RAZ-AW-S8_ReadingAuthorityIntake_BuilderImplementation
```

## 12. Final Verdict

```text
RAZ-AW-S7_ReadingAuthorityIntake_SchemaImplementation = PASS
```

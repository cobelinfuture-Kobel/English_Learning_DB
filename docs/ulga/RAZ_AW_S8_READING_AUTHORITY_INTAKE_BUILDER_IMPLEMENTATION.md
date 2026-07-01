# RAZ-AW-S8 Reading Authority Intake Builder Implementation

## 1. Task

`RAZ-AW-S8_ReadingAuthorityIntake_BuilderImplementation`

## 2. Execution Status

```text
S6B predecessor status = PASS_AW_READY_FOR_S7
S7 predecessor status = PASS
builder_implemented = true
promotion_implemented = false
runtime_mutation = false
learner_state_mutation = false
query_layer_expansion = false
```

## 3. Files Inspected

```text
docs/ulga/RAZ_AW_S8_READING_AUTHORITY_INTAKE_BUILDER_IMPLEMENTATION_PROMPT.md
ulga/schemas/raz_reading_authority_intake.schema.json
ulga/validators/validate_raz_reading_authority_intake_schema.py
ulga/reports/raz_aw_full_derived_inventory_sync_summary.json
ulga/reports/raz_aw_full_derived_inventory_sync_validation.json
ulga/graph/raz_level_discovery_inventory.json
raz_output_jsons/derived/Level_{A-W}/enriched/*
raz_output_jsons/derived/Level_{J-W}/normalized/*
```

## 4. Files Created / Modified

```text
ulga/builders/build_raz_reading_authority_intake.py
ulga/graph/raz_reading_authority_intake_candidates.json
ulga/reports/raz_reading_authority_intake_builder_summary.json
ulga/reports/raz_reading_authority_intake_builder_validation.json
tests/ulga/test_raz_reading_authority_intake_builder.py
docs/ulga/RAZ_AW_S8_READING_AUTHORITY_INTAKE_BUILDER_IMPLEMENTATION.md
```

Also updated:

```text
ulga/validators/validate_raz_reading_authority_intake_schema.py
```

to support validating an explicit payload path from CLI.

## 5. Builder Mapping Implemented

Implemented deterministic mappings:

```text
sentence enriched -> reading_intake_candidate(unit_type=sentence)
page_unit enriched -> reading_intake_candidate(unit_type=page_unit)
reuse_unit enriched -> reading_intake_candidate(unit_type=reuse_unit)
```

Compatibility coverage:

```text
canonical enriched sentence/page_unit/reuse_unit files
legacy enriched_sentences / enriched_units files
legacy normalized sentence/page_unit/reuse_unit files for traceability and text fallback
```

Legacy compatibility behavior:

```text
derive source IDs from sentence_uid / unit_uid
derive intake IDs deterministically
derive clean_text from sentence text joins when legacy unit payload lacks clean_text
derive page_unit_id for legacy reuse units from normalized page-unit lookups
preserve G-W query_layer_ready=false without blocking staging
```

## 6. Output Counts

Builder output:

```text
ulga/graph/raz_reading_authority_intake_candidates.json
total_records = 243957
```

By unit type:

```text
sentence = 201993
page_unit = 22632
reuse_unit = 19332
```

By level:

```text
A = 1616
B = 1658
C = 2120
D = 2304
E = 3193
F = 3531
G = 4067
H = 4548
I = 5428
J = 7275
K = 8411
L = 7747
M = 10038
N = 10103
O = 12843
P = 13022
Q = 13301
R = 16406
S = 21832
T = 20602
U = 20712
V = 26093
W = 27107
```

Query-layer-ready levels preserved:

```text
A-F
```

## 7. Blocking / Warning Summary

Builder validation result:

```text
status = PASS
schema_validation_status = PASS
records_checked = 243957
blocked_record_count = 0
duplicate_id_count = 0
promotion_violation_count = 0
generated_content_violation_count = 0
missing_traceability_count = 0
```

Warning summary:

```text
warning_count = 1646931
```

Primary warning drivers:

```text
missing cefr_estimate in many source records
legacy J-W records with sparse pedagogical metadata
non-blocking schema warnings inherited from S7 warning rules
```

These warnings do not block S8 because:

```text
all records remain candidate_only
all records keep promotion_allowed=false
all records keep generated_content=false
all records retain source traceability
```

## 8. Tests Added / Modified

Added:

```text
tests/ulga/test_raz_reading_authority_intake_builder.py
```

Coverage includes:

```text
canonical sentence/page/reuse mapping
legacy sentence/page/reuse mapping
query_layer_ready=false preserved and non-blocking
generated_content source blocked
duplicate intake ID blocked
builder output validates through S7 schema validator
builder script and validator CLI smoke
```

## 9. Commands Executed

```powershell
python -m pytest tests/ulga/test_raz_reading_authority_intake_builder.py -q
python -m pytest tests/ulga/test_raz_reading_authority_intake_schema.py -q
python ulga/builders/build_raz_reading_authority_intake.py
python ulga/validators/validate_raz_reading_authority_intake_schema.py ulga/graph/raz_reading_authority_intake_candidates.json
python -m pytest tests/ulga -q
python -m pytest tests -q
```

## 10. Guardrails

Confirmed:

```text
No final reading_authority.json
No Reading Authority promotion
No promotion_allowed=true
No final_eligible=true
No authority_status other than candidate_only
No runtime changes
No learner state changes
No planner changes
No API/dashboard/scheduler changes
No query-layer approved-level expansion
No mutation of source RAZ derived artifacts
```

## 11. Recommended Next Task

```text
RAZ-AW-S9_ReadingAuthorityIntake_BuilderQA
```

## 12. Final Verdict

```text
RAZ-AW-S8_ReadingAuthorityIntake_BuilderImplementation = PASS
```

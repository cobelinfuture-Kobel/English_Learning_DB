# RAZ-AW-S10A Reading Authority Intake Query Index Contract Implementation

## 1. Preflight

Executed:

```powershell
git status -sb
```

Confirmed unrelated pre-existing changes remain untouched:

```text
ulga/graph/static_candidate_ranking*.json
ulga/graph/corpus_source_inventory.json
ulga/reports/corpus_source_inventory_summary.json
ulga/reports/raz_downstream_discovery_drift_validation.json
docs/drive_manifest_guide.md
reports/raz/drive_manifest_hydration_plan.status.json
tests/test_drive_manifest_manager.py
tools/drive_manifest_manager.py
```

Confirmed `.gitignore` already contains:

```text
ulga/graph/raz_reading_authority_intake_candidates.json
```

S10A did not read, stream, or commit `ulga/graph/raz_reading_authority_intake_candidates.json`.

## 2. Files Inspected

```text
docs/ulga/RAZ_AW_S10A_READING_AUTHORITY_INTAKE_QUERY_INDEX_CONTRACT_IMPLEMENTATION_PROMPT.md
docs/ulga/RAZ_AW_S10_READING_AUTHORITY_INTAKE_QUERY_INDEX_DESIGNSCAN.md
docs/ulga/RAZ_AW_S10_READING_AUTHORITY_INTAKE_QUERY_INDEX_DESIGNSCAN_PROMPT.md
docs/ulga/RAZ_AW_S9_READING_AUTHORITY_INTAKE_BUILDER_QA_ARTIFACT_EXTERNALIZATION_AND_WARNING_TAXONOMY.md
ulga/schemas/raz_reading_authority_intake.schema.json
ulga/schemas/sample_raz_reading_authority_intake_candidates.json
ulga/validators/validate_raz_reading_authority_intake_schema.py
ulga/validators/validate_raz_reading_authority_intake_artifact_policy.py
ulga/reports/raz_reading_authority_intake_artifact_manifest.json
ulga/reports/raz_reading_authority_intake_warning_taxonomy.json
ulga/reports/raz_reading_authority_intake_builder_qa_summary.json
ulga/reports/raz_reading_authority_intake_builder_qa_validation.json
tests/ulga/test_raz_reading_authority_intake_schema.py
tests/ulga/test_raz_reading_authority_intake_artifact_policy.py
```

## 3. Files Created / Modified

Created:

```text
ulga/schemas/raz_reading_authority_intake_query_index.schema.json
ulga/schemas/sample_raz_reading_authority_intake_query_index.json
ulga/validators/validate_raz_reading_authority_intake_query_index.py
tests/ulga/test_raz_reading_authority_intake_query_index.py
ulga/reports/raz_reading_authority_intake_query_index_contract_summary.json
ulga/reports/raz_reading_authority_intake_query_index_contract_validation.json
docs/ulga/RAZ_AW_S10A_READING_AUTHORITY_INTAKE_QUERY_INDEX_CONTRACT_IMPLEMENTATION.md
```

## 4. Schema Contract Summary

Implemented compact metadata-only query-index contract:

```text
schema_version = raz_reading_authority_intake_query_index.v1
source = RAZ
unit_types = sentence | page_unit | reuse_unit
query_status = approved_candidate | staged_candidate_not_query_approved | blocked_from_query_policy | metadata_review_candidate
authority.authority_status = candidate_only
authority.candidate_only = true
authority.promotion_allowed = false
authority.promotion_status = not_promoted
authority.final_eligible = false
artifact_pointer.source_artifact = ulga/graph/raz_reading_authority_intake_candidates.json
artifact_pointer.source_artifact_status = LOCAL_ONLY
artifact_pointer.source_hash_sha256 = 96040b787816dd1ef193c680cefb4c350a08d6e78f8619759f8716a71a4e0fc6
```

Policy enforcement:

```text
A-F may use approved_candidate only with query_layer_ready=true and query_layer_approved=true
G-W must not use approved_candidate
G-W must not set query_layer_approved=true
G-W remains query_layer_ready=false in this contract stage
warning families are non-blocking filter flags
```

## 5. Sample Fixture Summary

Fixture file contains 5 Git-safe records:

```text
1. A-level approved sentence candidate
2. C-level approved page_unit candidate with sentence_count > 1
3. F-level approved reuse_unit candidate with reusability_tags
4. G-level staged sentence candidate with QUERY_LAYER_NOT_READY_G_TO_W
5. W-level staged reuse_unit candidate with sparse metadata warnings
```

The fixture uses only compact metadata and short `text_preview`; it does not duplicate full authoritative source text payloads.

## 6. Validator Behavior

Validator supports:

```powershell
python ulga/validators/validate_raz_reading_authority_intake_query_index.py ulga/schemas/sample_raz_reading_authority_intake_query_index.json
```

Validator checks:

```text
schema conformance
object / list / object-with-records payload shapes
A-F / G-W query policy
candidate_only invariants
promotion_allowed=false
final_eligible=false
recognized warning families only
warnings.count equals number of families
warnings.blocking remains false
source artifact pointer remains LOCAL_ONLY and hash-pinned
```

The validator writes:

```text
ulga/reports/raz_reading_authority_intake_query_index_contract_summary.json
ulga/reports/raz_reading_authority_intake_query_index_contract_validation.json
```

## 7. Tests Added / Modified

Added:

```text
tests/ulga/test_raz_reading_authority_intake_query_index.py
```

Coverage:

```text
sample fixture validates
A-F approved_candidate is accepted
G-W approved_candidate is rejected
promotion_allowed=true is rejected
final_eligible=true is rejected
authority_status != candidate_only is rejected
unknown warning family is rejected
warnings remain non-blocking
validator CLI produces PASS on sample fixture
```

## 8. Commands Executed

```powershell
git status -sb
python ulga/validators/validate_raz_reading_authority_intake_query_index.py ulga/schemas/sample_raz_reading_authority_intake_query_index.json
python -m pytest tests/ulga/test_raz_reading_authority_intake_query_index.py -q
python -m pytest tests/ulga/test_raz_reading_authority_intake_schema.py -q
python -m pytest tests/ulga/test_raz_reading_authority_intake_artifact_policy.py -q
```

## 9. Test Results

```text
validate_raz_reading_authority_intake_query_index.py = PASS
tests/ulga/test_raz_reading_authority_intake_query_index.py = PASS
tests/ulga/test_raz_reading_authority_intake_schema.py = PASS
tests/ulga/test_raz_reading_authority_intake_artifact_policy.py = PASS
```

Broad `tests/ulga` was not used in the PASS basis.

## 10. Git Scope Confirmation

Included in S10A scope:

```text
ulga/schemas/raz_reading_authority_intake_query_index.schema.json
ulga/schemas/sample_raz_reading_authority_intake_query_index.json
ulga/validators/validate_raz_reading_authority_intake_query_index.py
tests/ulga/test_raz_reading_authority_intake_query_index.py
ulga/reports/raz_reading_authority_intake_query_index_contract_summary.json
ulga/reports/raz_reading_authority_intake_query_index_contract_validation.json
docs/ulga/RAZ_AW_S10A_READING_AUTHORITY_INTAKE_QUERY_INDEX_CONTRACT_IMPLEMENTATION.md
```

Excluded from S10A scope:

```text
ulga/graph/raz_reading_authority_intake_candidates.json
ulga/graph/raz_reading_authority_intake_query_index_manifest.json
ulga/graph/raz_reading_authority_intake_query_index/**
existing static_candidate_ranking changes
existing corpus_source_inventory changes
existing drive_manifest files
existing raz_downstream_discovery_drift_validation.json changes
```

## 11. Guardrail Confirmation

Confirmed:

```text
full_index_built = false
large_artifact_required = false
promotion_allowed = false
authority_status = candidate_only
final_eligible = false
query_layer_expansion = false
runtime mutation = not performed
learner-state mutation = not performed
planner mutation = not performed
API/dashboard/scheduler mutation = not performed
source RAZ derived artifact mutation = not performed
```

## 12. Final Verdict

```text
RAZ-AW-S10A_ReadingAuthorityIntake_QueryIndexContractImplementation = PASS
```

PASS basis excludes any full-index build and excludes any large-artifact read.

## 13. Recommended Next Task

```text
RAZ-AW-S11_ReadingAuthorityIntake_QueryIndexBuilderImplementation
```

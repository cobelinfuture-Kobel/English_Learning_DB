# RAZ-AW-S10A Reading Authority Intake Query Index Contract Implementation Prompt

Use this prompt in Codex/local repo execution.

## 1. Task

`RAZ-AW-S10A_ReadingAuthorityIntake_QueryIndexContractImplementation`

## 2. Objective

Implement the first query-index contract layer for RAZ A-W Reading Authority Intake candidates.

S10A should implement only the contract surface required before the full query-index builder stage:

```text
schema
small fixture records
validator
focused tests
summary / validation reports
documentation
```

S10A must not build the full 243,957-record query index and must not read or commit the 619 MB full candidate artifact.

## 3. Required Predecessors

Required completed stages:

```text
RAZ-AW-S6B_FullDerivedArtifactInventorySyncQA = PASS_AW_READY_FOR_S7
RAZ-AW-S7_ReadingAuthorityIntake_SchemaImplementation = PASS
RAZ-AW-S8_ReadingAuthorityIntake_BuilderImplementation = PUSHED_WITH_LARGE_ARTIFACT_EXTERNALIZED
RAZ-AW-S9_ReadingAuthorityIntake_BuilderQA_ArtifactExternalizationAndWarningTaxonomy = PASS
RAZ-AW-S10_ReadingAuthorityIntake_QueryIndexDesignScan = PASS
```

Relevant S10 design decision:

```text
Use a hybrid strategy:
1. full candidate payload remains LOCAL_ONLY / externalized
2. compact query index is metadata-only
3. future full index is level + unit_type sharded JSONL
4. A-F may be approved_candidate
5. G-W must remain staged_candidate_not_query_approved
6. warning families are filter flags, not blockers
```

## 4. Strict Scope

Allowed:

```text
query-index schema JSON
small sample query-index fixture records
schema/contract validator
focused unit tests for schema and validator
small contract summary / validation reports
S10A implementation documentation
minor package/import adjustments if needed
```

Forbidden:

```text
building the full query index from 243,957 records
creating full sharded query-index output under ulga/graph/raz_reading_authority_intake_query_index/
creating final reading_authority.json
Reading Authority promotion
promotion_allowed=true
final_eligible=true
authority_status other than candidate_only
query-layer approved-level expansion beyond A-F
runtime query API changes
learner state changes
planner changes
API/dashboard/scheduler changes
mutation of source RAZ derived artifacts
committing ulga/graph/raz_reading_authority_intake_candidates.json
loading the entire 619 MB candidate artifact into memory
LLM-generated learner-facing content
rewritten dialogue/writing/exercise content
```

## 5. Required Preflight

Run:

```powershell
git status -sb
```

Confirm unrelated pre-existing changes, if still present, are not touched:

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

Confirm `.gitignore` contains:

```text
ulga/graph/raz_reading_authority_intake_candidates.json
```

Do not modify `.gitignore` unless that exclusion is missing.

## 6. Files to Inspect

Inspect:

```text
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

Do not require the local 619 MB candidate artifact for S10A.

## 7. Required Outputs

Create:

```text
ulga/schemas/raz_reading_authority_intake_query_index.schema.json
ulga/schemas/sample_raz_reading_authority_intake_query_index.json
ulga/validators/validate_raz_reading_authority_intake_query_index.py
tests/ulga/test_raz_reading_authority_intake_query_index.py
ulga/reports/raz_reading_authority_intake_query_index_contract_summary.json
ulga/reports/raz_reading_authority_intake_query_index_contract_validation.json
docs/ulga/RAZ_AW_S10A_READING_AUTHORITY_INTAKE_QUERY_INDEX_CONTRACT_IMPLEMENTATION.md
```

Do not create:

```text
ulga/graph/raz_reading_authority_intake_query_index_manifest.json
ulga/graph/raz_reading_authority_intake_query_index/{level}/{unit_type}.jsonl
ulga/graph/raz_reading_authority_intake_candidates.json
reading_authority.json
```

The graph manifest and full sharded JSONL index are S11 responsibilities.

## 8. Schema Contract

The schema should validate compact query-index records only.

Top-level required fields:

```text
reading_intake_id
schema_version
source
source_level
normalized_level
unit_type
query_status
query_layer_ready
query_layer_approved
book
text_meta
tags
warnings
artifact_pointer
authority
```

Required constants:

```text
schema_version = raz_reading_authority_intake_query_index.v1
source = RAZ
authority.authority_status = candidate_only
authority.candidate_only = true
authority.promotion_allowed = false
authority.promotion_status = not_promoted
authority.final_eligible = false
artifact_pointer.source_artifact_status = LOCAL_ONLY
```

Allowed levels:

```text
A B C D E F G H I J K L M N O P Q R S T U V W
```

Allowed unit types:

```text
sentence
page_unit
reuse_unit
```

Allowed query statuses:

```text
approved_candidate
staged_candidate_not_query_approved
blocked_from_query_policy
metadata_review_candidate
```

Policy rule:

```text
A-F may use query_status=approved_candidate with query_layer_ready=true and query_layer_approved=true.
G-W must not use query_status=approved_candidate and must not set query_layer_approved=true.
```

Warning families should include, at minimum:

```text
MISSING_CEFR_ESTIMATE
SPARSE_PEDAGOGICAL_TAGS
QUERY_LAYER_NOT_READY_G_TO_W
MISSING_BOOK_TITLE
LEGACY_TAG_COMPATIBILITY_MAPPED
UNSUPPORTED_LEGACY_REUSABILITY_TAG
S6B_PARITY_NOTE_INHERITED
SENTENCE_COUNT_HEURISTIC_MISMATCH
SOURCE_UNKNOWN_THEME
SOURCE_UNKNOWN_PATTERN
SOURCE_UNKNOWN_GRAMMAR
SOURCE_SECTION_HEADING_DETECTED
```

Warnings are filter flags, not blockers.

## 9. Proposed Compact Record Shape

The final schema may refine this shape but should stay close to it:

```json
{
  "reading_intake_id": "RAZ_A_1001_SENT_000001",
  "schema_version": "raz_reading_authority_intake_query_index.v1",
  "source": "RAZ",
  "source_level": "A",
  "normalized_level": "A",
  "unit_type": "sentence",
  "query_status": "approved_candidate",
  "query_layer_ready": true,
  "query_layer_approved": true,
  "book": {
    "book_id": "1001",
    "book_title": null,
    "page_number": 1,
    "page_unit_id": "RAZ_A_1001_P001"
  },
  "text_meta": {
    "sentence_count": 1,
    "word_count": 4,
    "text_language": "en",
    "text_role": "reading_source_text",
    "text_preview": "I see a cat."
  },
  "tags": {
    "cefr_estimate": null,
    "theme_tags": [],
    "vocabulary_tags": [],
    "grammar_tags": [],
    "pattern_tags": [],
    "skill_area": [],
    "reusability_tags": []
  },
  "warnings": {
    "families": ["MISSING_CEFR_ESTIMATE"],
    "count": 1,
    "blocking": false,
    "metadata_enrichment_needed": true
  },
  "artifact_pointer": {
    "source_artifact": "ulga/graph/raz_reading_authority_intake_candidates.json",
    "source_artifact_status": "LOCAL_ONLY",
    "source_hash_sha256": "96040b787816dd1ef193c680cefb4c350a08d6e78f8619759f8716a71a4e0fc6",
    "shard": null,
    "record_offset": null,
    "source_record_id": "RAZ_A_1001_SENT_000001"
  },
  "authority": {
    "authority_status": "candidate_only",
    "candidate_only": true,
    "promotion_allowed": false,
    "promotion_status": "not_promoted",
    "final_eligible": false
  }
}
```

## 10. Required Sample Fixture Records

The sample fixture file must include at least these records:

```text
1. A-level approved sentence candidate
2. C-level approved page_unit candidate with sentence_count > 1
3. F-level approved reuse_unit candidate with reusability_tags
4. G-level staged sentence candidate with QUERY_LAYER_NOT_READY_G_TO_W
5. W-level staged reuse_unit candidate with sparse metadata warnings
```

The fixture should be small and Git-safe.

## 11. Validator Requirements

The validator must:

```text
load the sample fixture or a provided JSON/JSONL file
validate every record against the query-index schema
assert A-F / G-W query policy
assert candidate_only invariants
assert no promotion_allowed=true
assert no final_eligible=true
assert warning families are recognized
assert warnings.blocking is false unless a future explicit blocking warning family is added
write a small validation report
exit non-zero on blocking violations
```

The validator should support CLI usage such as:

```powershell
python ulga/validators/validate_raz_reading_authority_intake_query_index.py ulga/schemas/sample_raz_reading_authority_intake_query_index.json
```

If no path is provided, it may default to the sample fixture.

## 12. Tests Required

Focused tests should cover:

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

Do not require the 619 MB local artifact in tests.

## 13. Reports Required

Create summary report:

```text
ulga/reports/raz_reading_authority_intake_query_index_contract_summary.json
```

Suggested fields:

```json
{
  "task": "RAZ-AW-S10A_ReadingAuthorityIntake_QueryIndexContractImplementation",
  "status": "PASS",
  "schema_path": "ulga/schemas/raz_reading_authority_intake_query_index.schema.json",
  "sample_fixture_path": "ulga/schemas/sample_raz_reading_authority_intake_query_index.json",
  "validator_path": "ulga/validators/validate_raz_reading_authority_intake_query_index.py",
  "records_in_fixture": 5,
  "full_index_built": false,
  "large_artifact_required": false,
  "promotion_allowed": false,
  "query_layer_expansion": false,
  "recommended_next_task": "RAZ-AW-S11_ReadingAuthorityIntake_QueryIndexBuilderImplementation"
}
```

Create validation report:

```text
ulga/reports/raz_reading_authority_intake_query_index_contract_validation.json
```

Suggested fields:

```json
{
  "task": "RAZ-AW-S10A_ReadingAuthorityIntake_QueryIndexContractImplementation",
  "status": "PASS",
  "schema_validation_status": "PASS",
  "policy_validation_status": "PASS",
  "blocking_error_count": 0,
  "promotion_violation_count": 0,
  "query_policy_violation_count": 0,
  "unknown_warning_family_count": 0,
  "full_artifact_touched": false
}
```

## 14. Commands to Run

Run at minimum:

```powershell
python ulga/validators/validate_raz_reading_authority_intake_query_index.py ulga/schemas/sample_raz_reading_authority_intake_query_index.json
python -m pytest tests/ulga/test_raz_reading_authority_intake_query_index.py -q
python -m pytest tests/ulga/test_raz_reading_authority_intake_schema.py -q
python -m pytest tests/ulga/test_raz_reading_authority_intake_artifact_policy.py -q
```

If time allows, run:

```powershell
python -m pytest tests/ulga -q
```

Do not report broad suite PASS unless it actually completed.

## 15. Required Documentation Structure

Create:

```text
docs/ulga/RAZ_AW_S10A_READING_AUTHORITY_INTAKE_QUERY_INDEX_CONTRACT_IMPLEMENTATION.md
```

Include:

```text
1. Preflight
2. Files inspected
3. Files created / modified
4. Schema contract summary
5. Sample fixture summary
6. Validator behavior
7. Tests added / modified
8. Commands executed
9. Test results
10. Git scope confirmation
11. Guardrail confirmation
12. Final verdict
13. Recommended next task
```

## 16. Git Scope

Expected files to add:

```text
ulga/schemas/raz_reading_authority_intake_query_index.schema.json
ulga/schemas/sample_raz_reading_authority_intake_query_index.json
ulga/validators/validate_raz_reading_authority_intake_query_index.py
tests/ulga/test_raz_reading_authority_intake_query_index.py
ulga/reports/raz_reading_authority_intake_query_index_contract_summary.json
ulga/reports/raz_reading_authority_intake_query_index_contract_validation.json
docs/ulga/RAZ_AW_S10A_READING_AUTHORITY_INTAKE_QUERY_INDEX_CONTRACT_IMPLEMENTATION.md
```

Do not add:

```text
ulga/graph/raz_reading_authority_intake_candidates.json
ulga/graph/raz_reading_authority_intake_query_index_manifest.json
ulga/graph/raz_reading_authority_intake_query_index/**
existing unrelated static_candidate_ranking changes
existing unrelated corpus_source_inventory changes
existing unrelated drive_manifest files
existing unrelated raz_downstream_discovery_drift_validation.json changes
```

## 17. Acceptance Criteria

S10A is PASS only if:

```text
schema exists and validates sample records
validator exists and passes sample fixture
focused tests pass
A-F / G-W query policy is enforced
candidate_only and promotion-blocked invariants are enforced
warning families are contract-bound and non-blocking
no full query index is built
619 MB local artifact is not touched or committed
no runtime / learner-state / planner / API / dashboard / scheduler changes occur
```

## 18. Final Verdict Format

Use:

```text
RAZ-AW-S10A_ReadingAuthorityIntake_QueryIndexContractImplementation = PASS
```

If local artifact or broad suite checks are intentionally not run, state that clearly and do not include them in the PASS basis.

## 19. Recommended Next Task

If S10A passes, recommend:

```text
RAZ-AW-S11_ReadingAuthorityIntake_QueryIndexBuilderImplementation
```

S11 should be local/Codex execution because it must stream the 619 MB local artifact, build real shards, run validators/tests, and check Git staging scope.

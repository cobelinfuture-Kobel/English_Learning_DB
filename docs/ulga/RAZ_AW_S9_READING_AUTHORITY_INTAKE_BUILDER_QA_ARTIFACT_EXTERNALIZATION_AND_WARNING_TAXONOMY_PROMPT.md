# RAZ-AW-S9 Reading Authority Intake Builder QA: Artifact Externalization and Warning Taxonomy Prompt

Use this prompt in Codex/local repo execution.

## 1. Task

`RAZ-AW-S9_ReadingAuthorityIntake_BuilderQA_ArtifactExternalizationAndWarningTaxonomy`

## 2. Objective

Close the post-S8 QA risks before any Reading Authority promotion work is considered.

S9 must validate and formalize two issues discovered during S8:

```text
1. The full intake candidate payload is a large local artifact and must not be committed to GitHub.
2. The builder emits a very large warning volume that must be classified, summarized, and made actionable.
```

S9 is a QA / governance task. It is not a promotion task and is not a content generation task.

## 3. Required Predecessors

Required completed stages:

```text
RAZ-AW-S6B_FullDerivedArtifactInventorySyncQA = PASS_AW_READY_FOR_S7
RAZ-AW-S7_ReadingAuthorityIntake_SchemaImplementation = PASS
RAZ-AW-S8_ReadingAuthorityIntake_BuilderImplementation = PUSHED_WITH_LARGE_ARTIFACT_EXTERNALIZED
```

Relevant S8 evidence:

```text
total_records = 243957
sentence = 201993
page_unit = 22632
reuse_unit = 19332
schema_validation_status = PASS
blocked_record_count = 0
duplicate_id_count = 0
promotion_violation_count = 0
generated_content_violation_count = 0
missing_traceability_count = 0
warning_count = 1646931
query_layer_ready = A-F
candidate artifact local size ~= 619 MB
```

## 4. Strict Scope

Allowed:

```text
QA report creation
artifact manifest / pointer creation
large artifact externalization policy
warning taxonomy report
warning aggregation script/helper if needed
small tests for manifest / taxonomy logic
small validator/report adjustments if needed
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
committing ulga/graph/raz_reading_authority_intake_candidates.json
```

## 5. Required Preflight

Run:

```powershell
git status -sb
```

Confirm these unrelated pre-existing changes, if still present, are not touched by S9:

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

If missing, add it.

Confirm the large artifact exists locally, if available:

```powershell
Get-Item "ulga\graph\raz_reading_authority_intake_candidates.json" | Select-Object Name, Length
"{0:N2} MB" -f ((Get-Item "ulga\graph\raz_reading_authority_intake_candidates.json").Length / 1MB)
```

If the local artifact is absent, S9 must still produce a policy/manifest stub using S8 report evidence, but must mark artifact hash/status as `LOCAL_ARTIFACT_NOT_PRESENT`.

## 6. Files to Inspect

Inspect:

```text
docs/ulga/RAZ_AW_S8_READING_AUTHORITY_INTAKE_BUILDER_IMPLEMENTATION_PROMPT.md
docs/ulga/RAZ_AW_S8_READING_AUTHORITY_INTAKE_BUILDER_IMPLEMENTATION.md
ulga/builders/build_raz_reading_authority_intake.py
ulga/reports/raz_reading_authority_intake_builder_summary.json
ulga/reports/raz_reading_authority_intake_builder_validation.json
ulga/validators/validate_raz_reading_authority_intake_schema.py
.gitignore
```

Optionally inspect the local large artifact only for metadata / streaming QA. Do not load the whole file into memory if avoidable.

## 7. Required Outputs

Create or update:

```text
ulga/reports/raz_reading_authority_intake_artifact_manifest.json
ulga/reports/raz_reading_authority_intake_warning_taxonomy.json
ulga/reports/raz_reading_authority_intake_builder_qa_summary.json
ulga/reports/raz_reading_authority_intake_builder_qa_validation.json
docs/ulga/RAZ_AW_S9_READING_AUTHORITY_INTAKE_BUILDER_QA_ARTIFACT_EXTERNALIZATION_AND_WARNING_TAXONOMY.md
```

Optional if needed:

```text
ulga/validators/validate_raz_reading_authority_intake_artifact_policy.py
tests/ulga/test_raz_reading_authority_intake_artifact_policy.py
```

Do not create or commit:

```text
ulga/graph/raz_reading_authority_intake_candidates.json
```

## 8. Artifact Manifest Contract

`ulga/reports/raz_reading_authority_intake_artifact_manifest.json` should include:

```json
{
  "task": "RAZ-AW-S9_ReadingAuthorityIntake_BuilderQA_ArtifactExternalizationAndWarningTaxonomy",
  "artifact_name": "raz_reading_authority_intake_candidates.json",
  "local_path": "ulga/graph/raz_reading_authority_intake_candidates.json",
  "git_policy": "do_not_commit",
  "gitignore_status": "PASS",
  "artifact_status": "LOCAL_ONLY",
  "external_storage_status": "PENDING_OPERATOR_UPLOAD",
  "external_storage_provider": null,
  "external_storage_uri": null,
  "size_bytes": 649406681,
  "size_mb": 619.32,
  "record_count": 243957,
  "schema_validation_status": "PASS",
  "content_hash_sha256": null,
  "hash_status": "PENDING_OR_COMPUTED",
  "regeneration_command": "python ulga/builders/build_raz_reading_authority_intake.py",
  "validation_command": "python ulga/validators/validate_raz_reading_authority_intake_schema.py ulga/graph/raz_reading_authority_intake_candidates.json",
  "notes": []
}
```

If the file exists locally, compute SHA-256 using streaming IO. Do not read the whole file at once.

If the file does not exist locally, set:

```text
artifact_status = LOCAL_ARTIFACT_NOT_PRESENT
hash_status = NOT_COMPUTED
size_bytes = null
size_mb = null
```

## 9. Warning Taxonomy Contract

`ulga/reports/raz_reading_authority_intake_warning_taxonomy.json` must classify the S8 warnings into stable categories.

Required top-level fields:

```json
{
  "task": "RAZ-AW-S9_ReadingAuthorityIntake_BuilderQA_ArtifactExternalizationAndWarningTaxonomy",
  "source_warning_count": 1646931,
  "blocking_warning_count": 0,
  "non_blocking_warning_count": 1646931,
  "warning_categories": [],
  "recommended_s10_actions": [],
  "promotion_blocking_status": "PROMOTION_STILL_BLOCKED"
}
```

Minimum warning categories:

```text
MISSING_CEFR_ESTIMATE
SPARSE_PEDAGOGICAL_TAGS
LEGACY_TAG_COMPATIBILITY_MAPPED
UNSUPPORTED_LEGACY_REUSABILITY_TAG
MISSING_WORD_COUNT_OR_DERIVED_WORD_COUNT
QUERY_LAYER_NOT_READY_G_TO_W
S6B_PARITY_NOTE_INHERITED
```

For each category, include:

```json
{
  "category": "MISSING_CEFR_ESTIMATE",
  "severity": "warning",
  "blocking": false,
  "count": 0,
  "source_layers": ["sentence", "page_unit", "reuse_unit"],
  "affected_levels": ["A", "...", "W"],
  "reason": "Source metadata is sparse; schema permits null cefr_estimate.",
  "recommended_action": "Aggregate and optionally backfill later; do not block S8 candidate staging."
}
```

If exact category counts are not available from current S8 validation output, add a small deterministic warning summarizer that reads the validation report and/or builder output metadata. If exact counts still cannot be recovered without rebuilding, clearly set:

```text
count_status = ESTIMATED_OR_UNAVAILABLE
```

Do not fabricate exact counts.

## 10. QA Summary Contract

`ulga/reports/raz_reading_authority_intake_builder_qa_summary.json` should include:

```json
{
  "task": "RAZ-AW-S9_ReadingAuthorityIntake_BuilderQA_ArtifactExternalizationAndWarningTaxonomy",
  "status": "PASS_WITH_EXTERNAL_ARTIFACT_POLICY",
  "s8_status": "PASS",
  "artifact_externalized": true,
  "artifact_committed_to_git": false,
  "gitignore_status": "PASS",
  "record_count": 243957,
  "artifact_size_mb": 619.32,
  "warning_count": 1646931,
  "warning_taxonomy_status": "PASS",
  "blocking_error_count": 0,
  "promotion_allowed": false,
  "authority_status": "candidate_only",
  "recommended_next_task": "RAZ-AW-S10_ReadingAuthorityIntake_QueryIndexDesignScan"
}
```

## 11. QA Validation Contract

`ulga/reports/raz_reading_authority_intake_builder_qa_validation.json` should include:

```json
{
  "task": "RAZ-AW-S9_ReadingAuthorityIntake_BuilderQA_ArtifactExternalizationAndWarningTaxonomy",
  "status": "PASS",
  "blocking_error_count": 0,
  "artifact_policy_status": "PASS",
  "warning_taxonomy_status": "PASS",
  "git_large_file_risk_status": "PASS_NOT_COMMITTED",
  "promotion_guardrail_status": "PASS",
  "query_layer_expansion_status": "NOT_PERFORMED",
  "runtime_mutation_status": "NOT_PERFORMED",
  "errors": [],
  "warnings": []
}
```

## 12. Tests

If adding policy helper/validator, add tests for:

```text
large candidate path is present in .gitignore
candidate artifact is marked do_not_commit
manifest handles local artifact present
manifest handles local artifact absent
warning taxonomy contains required categories
warning taxonomy does not mark sparse metadata as blocking
promotion remains blocked
```

Use small fixtures. Do not read or copy the 619 MB artifact in tests.

## 13. Commands

Run whatever focused tests are added, for example:

```powershell
python -m pytest tests/ulga/test_raz_reading_authority_intake_artifact_policy.py -q
```

Run existing S8/S7 tests:

```powershell
python -m pytest tests/ulga/test_raz_reading_authority_intake_builder.py -q
python -m pytest tests/ulga/test_raz_reading_authority_intake_schema.py -q
```

Run ULGA tests:

```powershell
python -m pytest tests/ulga -q
```

If feasible:

```powershell
python -m pytest tests -q
```

Do not rerun full builder unless needed. If rerunning, keep the candidate output untracked and ignored.

## 14. Acceptance Criteria

S9 passes only if:

```text
artifact manifest exists
warning taxonomy exists
QA summary exists
QA validation exists
large candidate artifact is not staged or committed
.gitignore blocks ulga/graph/raz_reading_authority_intake_candidates.json
warning categories are stable and actionable
sparse metadata warnings are explicitly non-blocking
promotion remains blocked
query-layer expansion is not performed
runtime / learner-state / planner / API / dashboard / scheduler untouched
focused tests pass
```

## 15. Git Scope

S9 commit may include:

```text
ulga/reports/raz_reading_authority_intake_artifact_manifest.json
ulga/reports/raz_reading_authority_intake_warning_taxonomy.json
ulga/reports/raz_reading_authority_intake_builder_qa_summary.json
ulga/reports/raz_reading_authority_intake_builder_qa_validation.json
docs/ulga/RAZ_AW_S9_READING_AUTHORITY_INTAKE_BUILDER_QA_ARTIFACT_EXTERNALIZATION_AND_WARNING_TAXONOMY.md
optional validator/test helper files
```

S9 commit must not include:

```text
ulga/graph/raz_reading_authority_intake_candidates.json
unrelated static_candidate_ranking files
unrelated corpus_source_inventory files
unrelated drive_manifest files
unrelated raz_downstream_discovery_drift_validation.json
```

Before commit:

```powershell
git diff --cached --name-only
```

## 16. Final Report Format

Final response must include:

```text
1. Preflight
2. Files inspected
3. Files created / modified
4. Artifact externalization result
5. Warning taxonomy result
6. Tests added / modified
7. Commands executed
8. Test results
9. Git scope confirmation
10. Guardrail confirmation
11. Final verdict
12. Recommended next task
```

Final verdict:

```text
RAZ-AW-S9_ReadingAuthorityIntake_BuilderQA_ArtifactExternalizationAndWarningTaxonomy = PASS
```

Recommended next task:

```text
RAZ-AW-S10_ReadingAuthorityIntake_QueryIndexDesignScan
```

If artifact policy fails:

```text
RAZ-AW-S9B_ArtifactExternalizationPolicyFix
```

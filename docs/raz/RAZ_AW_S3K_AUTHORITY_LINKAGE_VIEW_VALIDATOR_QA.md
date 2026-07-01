# RAZ-AW-S3K Authority Linkage View Validator QA

## 1. Preflight

Task:

```text
RAZ-AW-S3K_AuthorityLinkageViewValidator_QA
```

Mode:

```text
QA implementation
GitHub code only
Local execution required after pull
```

Predecessors:

```text
RAZ-AW-S3I_SourceTraceabilityBackfillEmitter_DesignScan
RAZ-AW-S3J_SourceTraceabilityBackfillEmitter_Implementation
```

S3J local run evidence expected before S3K local run:

```text
S3J emitter status: PASS
files_read_count: 161
records_emitted_count: 491832
warnings: []
blockers: []
```

Risk level:

```text
Low to Medium
```

Reason:

```text
This task adds a validator for local linkage-view artifacts. It does not mutate raw corpus, derived corpus, linkage artifacts, runtime, or authority state.
```

## 2. Files Changed

```text
tools/validate_raz_authority_linkage_view.py
docs/raz/RAZ_AW_S3K_AUTHORITY_LINKAGE_VIEW_VALIDATOR_QA.md
```

## 3. Scope Implemented

Implemented dedicated linkage-view validator:

```text
tools/validate_raz_authority_linkage_view.py
```

The validator scans:

```text
raz_output_jsons/linkage/Level_*/raz_*_authority_linkage_view.json
```

It emits sanitized report:

```text
reports/raz/raz_authority_linkage_view_validation.json
```

It checks:

```text
1. Linkage-view files exist.
2. Each package has schema_version=raz_authority_linkage_contract.v1.
3. Each record has required S3G fields.
4. source_traceability exists and is level-consistent.
5. promotion_status remains promotion_blocked.
6. authority_status is never promoted_authority.
7. generated_content remains false for deterministic RAZ linkage view records.
8. derived_from_original_text remains true.
9. allowed_authority_targets and blocked_authority_targets do not overlap.
10. AssessmentAuthority is not allowed unless assessment contract fields exist.
11. Sanitized QA report contains no sentence/page text or full records.
```

## 4. Local Execution Command

After pulling this commit locally, run:

```powershell
python tools/validate_raz_authority_linkage_view.py `
  --linkage-root raz_output_jsons/linkage `
  --reports-dir reports/raz `
  --schema schemas/raz/raz_authority_linkage_contract.schema.json
```

Expected report:

```text
reports/raz/raz_authority_linkage_view_validation.json
```

Expected PASS status:

```text
LINKAGE_VIEW_VALIDATION_PASS
```

## 5. Commit Policy After Local Run

Do not push:

```text
raz_output_jsons/linkage/**
raz_output_jsons/derived/**
raw corpus
text-bearing generated linkage views
```

Allowed to push after local run:

```text
reports/raz/raz_authority_linkage_view_validation.json
```

only if verified sanitized:

```text
contains_text_values=false
raw_mutation=false
derived_mutation=false
linkage_mutation=false
authority_promotion=false
```

## 6. Relationship to S3G1 Validator

S3G1 validator remains useful and should not be deleted or weakened.

S3G1 role:

```text
Validate legacy normalized/enriched derived artifacts and preserve the legacy gap baseline.
```

S3K role:

```text
Validate S3J linkage-view artifacts generated from the legacy corpus.
```

This separation preserves both signals:

```text
1. Legacy corpus still lacks S3G fields when scanned directly.
2. Linkage view can become contract-compliant without mutating legacy corpus.
```

## 7. Safety Boundaries Preserved

```text
No raw corpus modified.
No legacy derived corpus modified.
No linkage artifact mutation performed by validator.
No Authority promotion performed.
No runtime/API/scheduler/orchestrator changed.
No learner-facing content enabled.
No text-bearing report emitted.
```

## 8. Local Run Status

GitHub-side status:

```text
NOT_RUN_IN_GITHUB
```

Reason:

```text
The linkage view is local-only and not committed to GitHub. Local execution is required after pull.
```

## 9. Expected Interpretation

If status is:

```text
LINKAGE_VIEW_VALIDATION_PASS
```

then S3J/S3K can be considered linkage-view ready.

If status is:

```text
LINKAGE_VIEW_VALIDATION_BLOCKED
```

then inspect:

```text
issue_counts
sample_issues
blockers
```

Do not proceed to S4/S5 until S3K passes or only explicitly accepted non-blocking residuals remain.

## 10. Final Status

```text
IMPLEMENTED_PENDING_LOCAL_RUN
```

Controlled final statement:

```text
S3K validator code is available in GitHub. Pull locally, run the linkage-view validator against local raz_output_jsons/linkage, then inspect and push only the sanitized QA report if it passes the repository-safety checks.
```

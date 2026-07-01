# RAZ-AW-S3J Source Traceability Backfill Emitter Implementation

## 1. Preflight

Task:

```text
RAZ-AW-S3J_SourceTraceabilityBackfillEmitter_Implementation
```

Mode:

```text
Implementation
GitHub code only
Local execution required after pull
```

Predecessor:

```text
RAZ-AW-S3I_SourceTraceabilityBackfillEmitter_DesignScan
```

S3I verdict:

```text
BACKFILL_EMITTER_DESIGN_READY
```

Risk level:

```text
Medium
```

Reason:

```text
This task adds an executable emitter that reads local derived artifacts and writes local linkage-view artifacts. It does not run on GitHub and does not commit generated linkage views.
```

## 2. Files Changed

```text
tools/build_raz_authority_linkage_view.py
docs/raz/RAZ_AW_S3J_SOURCE_TRACEABILITY_BACKFILL_EMITTER_IMPLEMENTATION.md
```

## 3. Scope Implemented

Implemented emitter:

```text
tools/build_raz_authority_linkage_view.py
```

The emitter:

```text
1. Reads raz_output_jsons/derived/Level_*/normalized/*.json
2. Reads raz_output_jsons/derived/Level_*/enriched/*.json
3. Does not mutate legacy normalized/enriched artifacts
4. Builds contract-compliant authority-linkage records
5. Writes local linkage-view files under raz_output_jsons/linkage/Level_*/
6. Writes sanitized aggregate summary to reports/raz/raz_authority_linkage_backfill_emitter_summary.json
7. Emits no sentence text or page text in the sanitized summary
8. Sets promotion_status=promotion_blocked by default
9. Sets generated_content=false and derived_from_original_text=true for deterministic RAZ normalized/enriched artifacts
10. Keeps Authority promotion disabled
```

## 4. Local Execution Command

After pulling this commit locally, run:

```powershell
python tools/build_raz_authority_linkage_view.py `
  --derived-root raz_output_jsons/derived `
  --linkage-root raz_output_jsons/linkage `
  --reports-dir reports/raz
```

Expected local-only generated files:

```text
raz_output_jsons/linkage/Level_A/raz_A_authority_linkage_view.json
...
raz_output_jsons/linkage/Level_W/raz_W_authority_linkage_view.json
```

Expected GitHub-safe report generated locally:

```text
reports/raz/raz_authority_linkage_backfill_emitter_summary.json
```

## 5. Commit Policy

Do not push:

```text
raz_output_jsons/linkage/**
raz_output_jsons/derived/**
raw corpus
text-bearing generated linkage views
```

Allowed to push after local run:

```text
reports/raz/raz_authority_linkage_backfill_emitter_summary.json
```

only if verified sanitized:

```text
contains_text_values=false
raw_mutation=false
derived_mutation=false
authority_promotion=false
```

## 6. Safety Boundaries Preserved

```text
No raw corpus modified.
No legacy derived corpus modified.
No Authority promotion performed.
No runtime/API/scheduler/orchestrator changed.
No learner-facing content enabled.
No text-bearing linkage views pushed to GitHub.
```

## 7. Implementation Notes

The emitter creates records using schema version:

```text
raz_authority_linkage_contract.v1
```

It maps legacy fields into the S3G contract:

```text
level -> source_traceability.source_level
book_id -> source_traceability.source_book_id
book_uid -> source_traceability.source_book_uid
source_ref.* -> source_traceability raw/deterministic refs
sentence_uid / sentence_uids -> source_sentence_candidate_ids
page_unit_uid -> source_page_unit_id
reuse_unit_uid -> source_reuse_unit_id
```

Default authority safety fields:

```text
authority_status=candidate_only unless existing status is valid
promotion_status=promotion_blocked
review_status=legacy review_status or pending
required_review_before_promotion=artifact-layer policy
generated_content=false
derived_from_original_text=true
```

## 8. Expected Follow-up Validation

After local emitter run, run the existing S3G validator against the legacy root to preserve the gap baseline:

```powershell
python tools/raz_aw_validate_authority_linkage_contract.py `
  --derived-root raz_output_jsons/derived `
  --reports-dir reports/raz
```

S3K should then add or adapt a validator path for linkage-view files:

```text
RAZ-AW-S3K_AuthorityLinkageViewValidator_QA
```

S3K should verify that the linkage view passes the supplemental contract while the original legacy corpus remains unchanged.

## 9. Local Run Status

GitHub-side status:

```text
NOT_RUN_IN_GITHUB
```

Reason:

```text
The required text-bearing local derived corpus is not available in GitHub execution context, and generated linkage views must remain local-only unless separately sanitized.
```

## 10. Final Status

```text
IMPLEMENTED_PENDING_LOCAL_RUN
```

Controlled final statement:

```text
S3J emitter code is available in GitHub. Pull locally, run the emitter against local derived artifacts, then inspect the sanitized summary before deciding what to push next.
```

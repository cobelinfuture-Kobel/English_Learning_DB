# RAZ-AW-S4B Page Passage Unit Review Contract QA

## 1. Preflight

Task:

```text
RAZ-AW-S4B_PagePassageUnitReviewContract_QA
```

Mode:

```text
QA implementation
GitHub code only
Local execution required after pull
```

Predecessors:

```text
RAZ-AW-S4_PagePassageUnitReviewContract_DesignScan
RAZ-AW-S4A_PagePassageUnitReviewContract_Implementation
RAZ-AW-S4A1_PagePassageReviewCandidateCanonicalPageUnitFix
```

S4A1 local-run summary evidence:

```text
status: PAGE_PASSAGE_REVIEW_PRECHECK_PASS
records_read_count: 491832
review_candidates_emitted_count: 22632
canonical_page_unit_source_kind: normalized_page_units
review_state_counts.ready_for_review: 22632
skipped_source_kind_counts.enriched_units: 22632
issue_counts: {}
warnings: []
blockers: []
```

Risk level:

```text
Medium
```

Reason:

```text
This task adds an executable validator that reads local review candidate artifacts and emits a sanitized QA report. It does not mutate raw corpus, derived corpus, linkage view, or review artifacts.
```

## 2. Files Changed

```text
tools/validate_raz_page_passage_review_contract.py
docs/raz/RAZ_AW_S4B_PAGE_PASSAGE_UNIT_REVIEW_CONTRACT_QA.md
```

## 3. Scope Implemented

Implemented validator:

```text
tools/validate_raz_page_passage_review_contract.py
```

The validator reads:

```text
raz_output_jsons/review/Level_*/raz_*_page_passage_review_candidates.json
reports/raz/raz_page_passage_review_contract_summary.json
```

It emits sanitized QA report:

```text
reports/raz/raz_page_passage_review_contract_qa.json
```

It validates:

```text
1. Review candidate files exist.
2. Review candidate schema_version is raz_page_passage_review_contract.v1.
3. Candidate count matches S4A/S4A1 summary.
4. All candidates are unit_type=page_unit.
5. All candidates use canonical_source_kind=normalized_page_units.
6. All source_linkage_uid values end with ::normalized_page_units.
7. All candidates are ready_for_review.
8. review_status remains pending.
9. promotion_status remains promotion_blocked.
10. authority_status remains candidate_only.
11. LearningOpportunityBinding remains blocked.
12. AssessmentAuthority remains blocked.
13. source_traceability is internally consistent.
14. No candidate records or text values are emitted into the QA report.
```

## 4. Local Execution Command

After pulling this commit locally, run:

```powershell
python tools/validate_raz_page_passage_review_contract.py `
  --review-root raz_output_jsons/review `
  --reports-dir reports/raz `
  --summary reports/raz/raz_page_passage_review_contract_summary.json
```

Expected PASS status:

```text
PAGE_PASSAGE_REVIEW_QA_PASS
```

Expected candidate count:

```text
review_candidates_scanned_count: 22632
summary_expected_candidate_count: 22632
```

Expected key counters:

```text
review_state_counts.ready_for_review: 22632
canonical_source_kind_counts.normalized_page_units: 22632
promotion_status_counts.promotion_blocked: 22632
authority_status_counts.candidate_only: 22632
issue_counts: {}
warnings: []
blockers: []
```

## 5. Commit Policy

Do not push:

```text
raz_output_jsons/review/**
raz_output_jsons/linkage/**
raz_output_jsons/derived/**
raw corpus
text-bearing generated review candidates
```

Allowed to push after local run:

```text
reports/raz/raz_page_passage_review_contract_qa.json
```

only if verified sanitized:

```text
contains_text_values=false
raw_mutation=false
derived_mutation=false
linkage_mutation=false
review_artifact_mutation=false
authority_promotion=false
learner_facing_content_enabled=false
```

## 6. Safety Boundaries Preserved

```text
No raw corpus modified.
No legacy derived corpus modified.
No linkage view modified.
No review artifact modified by validator.
No Authority promotion performed.
No learner-facing content enabled.
No runtime/API/scheduler/orchestrator changed.
No text-bearing review artifacts pushed to GitHub.
```

## 7. Relationship to S5

S4B QA pass means:

```text
canonical page-unit review candidates are structurally valid and ready for human/QA review intake.
```

S4B QA pass does not mean:

```text
ReadingAuthority records exist.
Authority promotion is allowed.
Learner-facing content is enabled.
LearningOpportunityBinding is allowed.
AssessmentAuthority is allowed.
```

S5 may inspect S4B-passing candidates as bridge inputs only after this QA passes.

## 8. Final Status

```text
IMPLEMENTED_PENDING_LOCAL_RUN
```

Controlled final statement:

```text
S4B validator code is available in GitHub. Pull locally, run the validator against local raz_output_jsons/review and the S4A/S4A1 summary, then inspect the sanitized QA report before deciding what to push next.
```

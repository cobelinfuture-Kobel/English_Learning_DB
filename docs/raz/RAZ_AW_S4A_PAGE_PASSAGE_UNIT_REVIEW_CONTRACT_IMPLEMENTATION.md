# RAZ-AW-S4A Page Passage Unit Review Contract Implementation

## 1. Preflight

Task:

```text
RAZ-AW-S4A_PagePassageUnitReviewContract_Implementation
```

Mode:

```text
Implementation
GitHub code only
Local execution required after pull
```

Predecessor:

```text
RAZ-AW-S4_PagePassageUnitReviewContract_DesignScan
```

S4 verdict:

```text
PAGE_PASSAGE_REVIEW_CONTRACT_DESIGN_READY
```

Risk level:

```text
Medium
```

Reason:

```text
This task adds an executable builder that reads local linkage-view artifacts and writes local review candidate artifacts. It does not run on GitHub and does not commit generated review artifacts.
```

## 2. Files Changed

```text
tools/build_raz_page_passage_review_candidates.py
docs/raz/RAZ_AW_S4A_PAGE_PASSAGE_UNIT_REVIEW_CONTRACT_IMPLEMENTATION.md
```

## 3. Scope Implemented

Implemented builder:

```text
tools/build_raz_page_passage_review_candidates.py
```

The builder:

```text
1. Reads raz_output_jsons/linkage/Level_*/raz_*_authority_linkage_view.json
2. Selects artifact_layer=page_unit records only
3. Skips reuse_unit_candidate by default
4. Treats passage_unit as future-contract only
5. Applies deterministic page-unit precheck gates
6. Emits local-only review candidate artifacts under raz_output_jsons/review/Level_*/
7. Emits sanitized summary to reports/raz/raz_page_passage_review_contract_summary.json
8. Does not emit sentence text, page text, raw_text, or full records into the summary
9. Keeps promotion_status=promotion_blocked
10. Keeps authority_status=candidate_only
11. Keeps LearningOpportunityBinding and AssessmentAuthority blocked
12. Does not create learner-facing content
```

## 4. Local Execution Command

After pulling this commit locally, run:

```powershell
python tools/build_raz_page_passage_review_candidates.py `
  --linkage-root raz_output_jsons/linkage `
  --review-root raz_output_jsons/review `
  --reports-dir reports/raz
```

Expected local-only generated files:

```text
raz_output_jsons/review/Level_A/raz_A_page_passage_review_candidates.json
...
raz_output_jsons/review/Level_W/raz_W_page_passage_review_candidates.json
```

Expected GitHub-safe summary generated locally:

```text
reports/raz/raz_page_passage_review_contract_summary.json
```

Expected PASS status if the linkage view matches S4 assumptions:

```text
PAGE_PASSAGE_REVIEW_PRECHECK_PASS
```

Expected candidate count:

```text
45264 page_unit review candidates
```

Reason:

```text
S3K reported 45264 page_unit linkage records.
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
reports/raz/raz_page_passage_review_contract_summary.json
```

only if verified sanitized:

```text
contains_text_values=false
raw_mutation=false
derived_mutation=false
linkage_mutation=false
authority_promotion=false
learner_facing_content_enabled=false
```

## 6. Safety Boundaries Preserved

```text
No raw corpus modified.
No legacy derived corpus modified.
No linkage view modified.
No Authority promotion performed.
No learner-facing content enabled.
No runtime/API/scheduler/orchestrator changed.
No text-bearing review artifacts pushed to GitHub.
```

## 7. Implementation Notes

The builder creates records using schema version:

```text
raz_page_passage_review_contract.v1
```

It reads source records using schema version:

```text
raz_authority_linkage_contract.v1
```

It maps linkage records into review candidates:

```text
record_uid -> source_linkage_uid
record_uid + ::page_passage_review_v1 -> review_candidate_uid
source_traceability.source_level -> level
source_traceability.source_book_uid -> book_uid
source_traceability.source_book_id -> book_id
source_traceability.source_page_number -> page_number
source_traceability -> source_traceability
content_hash / clean_text_hash -> hash references only
```

Default review safety fields:

```text
unit_type=page_unit
authority_status=candidate_only
promotion_status=promotion_blocked
review_state=ready_for_review if deterministic precheck passes, otherwise precheck_failed
review_status=pending
required_review_before_promotion=page_unit_review
allowed_bridge_targets=[ReadingAuthorityBridge, ContentQueryLayer]
blocked_bridge_targets=[LearningOpportunityBinding, AssessmentAuthority, DialogueAuthority, WritingAuthority, ExerciseAuthority]
contains_text_values=false
```

## 8. Deliberate Non-Goals

S4A does not:

```text
1. Run human review.
2. Mark candidates as PAGE_PASSAGE_REVIEW_PASS.
3. Mark candidates as PAGE_PASSAGE_REVIEW_BRIDGE_ELIGIBLE.
4. Create ReadingAuthority records.
5. Promote Authority.
6. Enable learner-facing content.
7. Build passage_unit sequences.
8. Convert reuse_unit_candidate into reading candidates.
```

## 9. Expected Follow-up QA

Recommended next task after local S4A run:

```text
RAZ-AW-S4B_PagePassageUnitReviewContract_QA
```

S4B should validate:

```text
review candidate files exist
candidate count equals page_unit count unless explicitly justified
all candidates are unit_type=page_unit
review_state is ready_for_review or precheck_failed
promotion_status remains promotion_blocked
authority_status remains candidate_only
LearningOpportunityBinding remains blocked
AssessmentAuthority remains blocked
summary is sanitized and text-free
local-only review artifacts are not pushed
```

## 10. Local Run Status

GitHub-side status:

```text
NOT_RUN_IN_GITHUB
```

Reason:

```text
The required local linkage-view artifacts are not committed to GitHub. Local execution is required after pull.
```

## 11. Final Status

```text
IMPLEMENTED_PENDING_LOCAL_RUN
```

Controlled final statement:

```text
S4A builder code is available in GitHub. Pull locally, run the builder against local raz_output_jsons/linkage, then inspect the sanitized summary before deciding what to push next.
```

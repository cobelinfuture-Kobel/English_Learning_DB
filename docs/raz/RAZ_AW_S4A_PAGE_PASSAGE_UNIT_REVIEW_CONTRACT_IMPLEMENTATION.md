# RAZ-AW-S4A Page Passage Unit Review Contract Implementation

## 1. Preflight

Task:

```text
RAZ-AW-S4A1_PagePassageReviewCandidateCanonicalPageUnitFix
```

Mode:

```text
Implementation fix
GitHub code only
Local execution required after pull
```

Predecessors:

```text
RAZ-AW-S4_PagePassageUnitReviewContract_DesignScan
RAZ-AW-S4A_PagePassageUnitReviewContract_Implementation
```

Observed S4A local run before fix:

```text
status: PAGE_PASSAGE_REVIEW_PRECHECK_BLOCKED
records_read_count: 491832
review_candidates_emitted_count: 45264
review_state_counts.ready_for_review: 22632
review_state_counts.precheck_failed: 22632
blockers: [page_passage_precheck_failures]
```

Root cause:

```text
S4A accepted every artifact_layer=page_unit record. The linkage view contains both canonical normalized_page_units and enriched page_unit records. The enriched page_unit records are secondary views and may lack page_number, so they created duplicate review candidates and failed page_number_present precheck.
```

Risk level:

```text
Medium
```

Reason:

```text
This task changes the executable review candidate builder. It still only reads local linkage-view artifacts and writes local review candidate artifacts. It does not run on GitHub and does not commit generated review artifacts.
```

## 2. Files Changed

```text
tools/build_raz_page_passage_review_candidates.py
docs/raz/RAZ_AW_S4A_PAGE_PASSAGE_UNIT_REVIEW_CONTRACT_IMPLEMENTATION.md
```

## 3. Scope Implemented

Implemented canonical intake fix in:

```text
tools/build_raz_page_passage_review_candidates.py
```

The builder now:

```text
1. Reads raz_output_jsons/linkage/Level_*/raz_*_authority_linkage_view.json
2. Accepts only canonical page_unit records whose record_uid ends with ::normalized_page_units
3. Skips enriched page_unit duplicate records as non-canonical review identities
4. Skips reuse_unit_candidate by default
5. Treats passage_unit as future-contract only
6. Applies deterministic page-unit precheck gates only to canonical page units
7. Emits local-only review candidate artifacts under raz_output_jsons/review/Level_*/
8. Emits sanitized summary to reports/raz/raz_page_passage_review_contract_summary.json
9. Does not emit sentence text, page text, raw_text, or full records into the summary
10. Keeps promotion_status=promotion_blocked
11. Keeps authority_status=candidate_only
12. Keeps LearningOpportunityBinding and AssessmentAuthority blocked
13. Does not create learner-facing content
```

Canonical source policy:

```text
normalized_page_units = review candidate identity source
enriched page_unit records = secondary/enrichment metadata source, not review candidate identity
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

Expected PASS status after S4A1:

```text
PAGE_PASSAGE_REVIEW_PRECHECK_PASS
```

Expected candidate count:

```text
22632 canonical page_unit review candidates
```

Reason:

```text
S3K reported 45264 page_unit linkage records, but half are canonical normalized_page_units and half are enriched page_unit secondary views. S4A1 should emit review candidates only for the canonical normalized_page_units half.
```

Expected skipped source kind:

```text
enriched_units: 22632
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

It maps canonical linkage records into review candidates:

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
canonical_source_kind=normalized_page_units
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

S4A/S4A1 does not:

```text
1. Run human review.
2. Mark candidates as PAGE_PASSAGE_REVIEW_PASS.
3. Mark candidates as PAGE_PASSAGE_REVIEW_BRIDGE_ELIGIBLE.
4. Create ReadingAuthority records.
5. Promote Authority.
6. Enable learner-facing content.
7. Build passage_unit sequences.
8. Convert reuse_unit_candidate into reading candidates.
9. Treat enriched page_unit records as separate review candidate identities.
```

## 9. Expected Follow-up QA

Recommended next task after local S4A1 run:

```text
RAZ-AW-S4B_PagePassageUnitReviewContract_QA
```

S4B should validate:

```text
review candidate files exist
candidate count equals canonical normalized_page_units count unless explicitly justified
all candidates are unit_type=page_unit
all candidates have canonical_source_kind=normalized_page_units
all candidates are ready_for_review or explicitly precheck_failed
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
S4A1 canonical page-unit fix is available in GitHub. Pull locally, rerun the builder against local raz_output_jsons/linkage, then inspect the sanitized summary before deciding what to push next.
```

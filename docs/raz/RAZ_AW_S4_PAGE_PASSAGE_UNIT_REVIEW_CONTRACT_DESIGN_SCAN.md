# RAZ-AW-S4 Page Passage Unit Review Contract Design Scan

## 1. Preflight

Task:

```text
RAZ-AW-S4_PagePassageUnitReviewContract_DesignScan
```

Execution mode:

```text
DesignScan only
```

Predecessors:

```text
RAZ-AW-S3I_SourceTraceabilityBackfillEmitter_DesignScan
RAZ-AW-S3J_SourceTraceabilityBackfillEmitter_Implementation
RAZ-AW-S3K_AuthorityLinkageViewValidator_QA
```

Dependency status used:

```text
S3I: BACKFILL_EMITTER_DESIGN_READY
S3J: EMITTER_LOCAL_RUN_PASS
S3K: LINKAGE_VIEW_VALIDATION_PASS
```

Control flags:

| Control | Status |
| --- | --- |
| implementation allowed | false |
| corpus mutation allowed | false |
| raw corpus modification allowed | false |
| derived corpus modification allowed | false |
| linkage view mutation allowed | false |
| review data generation allowed | false |
| authority promotion allowed | false |
| runtime modification allowed | false |
| builder modification allowed | false |
| validator modification allowed | false |
| GitHub full-text corpus push allowed | false |

Risk level:

```text
Low
```

Reason:

```text
This task adds a documentation-only review contract. It does not modify code, schemas, validators, builders, runtime, raw corpus, derived corpus, linkage artifacts, review records, or authority records.
```

Repository-safe conclusion:

```text
S4 is safe to commit because it contains only sanitized contract design. It contains no RAZ raw text, no sentence text, no page text, and no full derived records.
```

---

## 2. Files Inspected

| Path | Role | Inspection status | Quote safety | Full-text risk |
| --- | --- | --- | --- | --- |
| `reports/raz/raz_authority_linkage_view_validation.json` | S3K validation evidence | directly inspected | safe aggregate counts only | no text values |
| `docs/raz/RAZ_AW_S3I_SOURCE_TRACEABILITY_BACKFILL_EMITTER_DESIGN_SCAN.md` | linkage view design basis | dependency accepted | safe_to_quote | no |
| `docs/raz/RAZ_AW_S3J_SOURCE_TRACEABILITY_BACKFILL_EMITTER_IMPLEMENTATION.md` | emitter implementation boundary | dependency accepted | safe_to_quote | no |
| `docs/raz/RAZ_AW_S3K_AUTHORITY_LINKAGE_VIEW_VALIDATOR_QA.md` | linkage validator QA boundary | dependency accepted | safe_to_quote | no |
| `raz_output_jsons/linkage/Level_*/raz_*_authority_linkage_view.json` | local linkage view | not opened in GitHub scan | local_only_do_not_push | may contain record-level metadata |
| `raz_output_jsons/derived/Level_*/...` | local derived corpus | not opened | full_text_do_not_quote | yes |

S3K aggregate evidence:

```text
status: LINKAGE_VIEW_VALIDATION_PASS
files_scanned_count: 23
records_scanned_count: 491832
promotion_status_counts: { promotion_blocked: 491832 }
authority_status_counts: { candidate_only: 491832 }
issue_counts: {}
warnings: []
blockers: []
```

S3K artifact-layer counts relevant to S4:

```text
page_unit: 45264
reuse_unit_candidate: 38664
raw_source_reference: 3918
sentence_normalized: 201993
sentence_enriched: 201993
```

S3K review-gate evidence:

```text
required_review_counts.page_unit_review: 45264
required_review_counts.human_review_required: 38664
required_review_counts.sentence_validation: 403986
```

---

## 3. Problem Statement

S3I/S3J/S3K created and validated a safe authority-linkage view. The linkage view is now usable as a contract-compliant intake layer for future review and bridge tasks.

However, a validated linkage view is not the same as reviewed Reading Authority content.

The next risk boundary is:

```text
page_unit and future passage_unit records may be structurally traceable, but they are not yet reviewed as reading units.
```

S4 must define the review contract before S5 Reading Authority Bridge design can safely consume page/passage candidates.

S4 answer:

```text
Introduce a dedicated Page/Passage Unit Review Contract. It converts contract-compliant candidate records into reviewable reading-unit candidates, but it does not promote them to Reading Authority.
```

---

## 4. Core Design Decision

S4 should not directly promote page units into Reading Authority.

S4 should define an intermediate review state:

```text
linkage_view.page_unit
        ↓ review intake
page_passage_review_candidate
        ↓ deterministic + human/QA review gates
reviewed_reading_candidate
        ↓ future S5 bridge intake
ReadingAuthority candidate intake only
        ↓ explicit future promotion task required
promoted ReadingAuthority
```

Controlled interpretation:

```text
S4 creates the review contract. It does not create Reading Authority and does not authorize learner-facing use.
```

---

## 5. Unit Types and Boundaries

### 5.1 `page_unit`

Definition:

```text
A page-level source-derived candidate unit traceable to a RAZ book, level, page number, and source sentence candidates.
```

Current S3K count:

```text
45264 page_unit linkage records
```

Default S4 status:

```text
review_status = pending
required_review_before_promotion = page_unit_review
promotion_status = promotion_blocked
authority_status = candidate_only
```

Allowed role:

```text
reading candidate review intake
content query support
source-traceable candidate inspection
```

Blocked role:

```text
formal ReadingAuthority
learner-facing approved content
LearningOpportunityBinding
AssessmentAuthority
DialogueAuthority
WritingAuthority
ExerciseAuthority
```

### 5.2 `passage_unit`

Definition:

```text
A multi-page or multi-page-unit reading candidate assembled from traceable page_unit records. It may represent a continuous reading passage, sequence, story segment, or reusable reading block.
```

Current implementation status:

```text
future_contract_only
```

Reason:

```text
S3J/S3K linkage view currently validates page_unit records and reuse_unit_candidate records. A formal passage_unit builder/reviewer is not yet implemented.
```

Default S4 status:

```text
review_status = pending
required_review_before_promotion = reading_authority_review or page_unit_review + passage_sequence_review
promotion_status = promotion_blocked
authority_status = candidate_only
```

### 5.3 `reuse_unit_candidate`

Definition:

```text
A reuse candidate that may support future reading, dialogue, exercise, writing, or query use, but is not automatically a Reading Authority candidate.
```

Current S3K count:

```text
38664 reuse_unit_candidate linkage records
```

S4 rule:

```text
reuse_unit_candidate must not be promoted directly into ReadingAuthority.
```

It may become page/passage review input only after a later mapping task explicitly classifies it as a reading-unit candidate and preserves source traceability.

---

## 6. Review State Machine

S4 review states:

```text
not_in_review
pending_review
precheck_failed
ready_for_review
in_review
review_passed
review_failed
needs_revision
eligible_for_bridge_intake
blocked_from_bridge
```

Allowed transitions:

```text
candidate_only + promotion_blocked
        ↓ intake precheck
pending_review
        ↓ deterministic checks pass
ready_for_review
        ↓ reviewer / QA action
in_review
        ↓ pass
review_passed
        ↓ bridge eligibility check
eligible_for_bridge_intake
```

Failure transitions:

```text
pending_review -> precheck_failed
ready_for_review -> review_failed
in_review -> review_failed
review_failed -> needs_revision
needs_revision -> ready_for_review
any unsafe state -> blocked_from_bridge
```

Forbidden transitions:

```text
candidate_only -> promoted_authority
page_unit -> promoted ReadingAuthority
reuse_unit_candidate -> promoted ReadingAuthority
passage_unit -> promoted ReadingAuthority
review_passed -> learner-facing content
eligible_for_bridge_intake -> promoted_authority
```

Important distinction:

```text
eligible_for_bridge_intake means S5 may inspect it. It does not mean Authority promotion is allowed.
```

---

## 7. Review Contract Record Shape

Recommended future artifact:

```text
reports/raz/raz_page_passage_review_contract_summary.json
```

Recommended local review-intake artifact:

```text
raz_output_jsons/review/Level_<LEVEL>/raz_<LEVEL>_page_passage_review_candidates.json
```

GitHub policy:

```text
Do not push text-bearing review candidate artifacts.
Only push sanitized aggregate reports unless explicitly proven text-free.
```

Recommended review candidate record shape:

```json
{
  "review_candidate_uid": "raz_A_100_p0001::page_passage_review_v1",
  "source_linkage_uid": "raz_A_100_p0001::authority_linkage_v1::normalized_page_units",
  "unit_type": "page_unit",
  "level": "A",
  "book_uid": "raz_A_100",
  "book_id": "100",
  "page_number": 1,
  "source_traceability": {},
  "authority_status": "candidate_only",
  "promotion_status": "promotion_blocked",
  "review_state": "pending_review",
  "review_status": "pending",
  "required_review_before_promotion": "page_unit_review",
  "allowed_bridge_targets": ["ReadingAuthorityBridge", "ContentQueryLayer"],
  "blocked_bridge_targets": ["LearningOpportunityBinding", "AssessmentAuthority", "DialogueAuthority", "WritingAuthority", "ExerciseAuthority"],
  "review_checks": {},
  "review_decision": null,
  "reviewer_notes_ref": null,
  "contains_text_values": false,
  "content_hash": "hash-only-if-available"
}
```

Text policy:

```text
Review reports should use ids, hashes, counts, and status codes. Do not include sentence text, page text, raw text, or full records in GitHub-safe outputs.
```

---

## 8. Deterministic Precheck Gates

S4 recommends a deterministic precheck before human/QA review.

Required precheck fields:

```text
source_traceability present
source_level present
source_book_uid present
source_book_id present
source_sentence_candidate_ids present for sentence-bearing units
source_page_unit_id present for page_unit
promotion_status == promotion_blocked
authority_status == candidate_only
review_status in pending / needs_review / not_required depending on artifact layer
generated_content == false for source-derived RAZ page/passage candidates
derived_from_original_text == true
allowed_authority_targets does not conflict with blocked_authority_targets
LearningOpportunityBinding remains blocked
AssessmentAuthority remains blocked unless assessment contract fields exist
```

Page-unit specific precheck:

```text
unit_type/page_unit artifact layer must be page_unit
required_review_before_promotion must be page_unit_review
page number must be available when source has page granularity
source sentence candidate ids must be non-empty or explicitly justified as unavailable
```

Passage-unit specific precheck:

```text
passage_unit must have ordered source_page_unit_ids
page sequence must be deterministic
source levels must not mix unless a later cross-level policy exists
book_uid must be consistent across the passage unless a later anthology policy exists
```

---

## 9. Review Dimensions

S4 review should evaluate page/passage candidates along these dimensions:

| Dimension | Purpose | Gate type |
| --- | --- | --- |
| source traceability | prove origin and audit path | deterministic |
| unit completeness | ensure page/passage is not fragmentary beyond policy | deterministic + review |
| sequence integrity | preserve page order / passage order | deterministic |
| reading usability | decide whether candidate is useful as a reading unit | review |
| level appropriateness | ensure candidate fits expected level band | review |
| topic/theme suitability | support query and curriculum use | review |
| language-skill fit | classify reading vs dialogue/writing/exercise suitability | review |
| safety / leakage | prevent raw text in GitHub reports | deterministic |
| promotion gate | keep all Authority promotion blocked | deterministic |

S4 should not require semantic judgment to be perfect before S5. It only needs enough review contract structure to prevent unsafe bridge intake.

---

## 10. Reading Bridge Eligibility Rules

A page/passage review candidate may be eligible for S5 bridge intake only if all are true:

```text
review_state == review_passed or eligible_for_bridge_intake
promotion_status == promotion_blocked
authority_status == candidate_only
source_traceability is complete enough for audit
required_review_before_promotion has been satisfied at review-contract level
LearningOpportunityBinding remains blocked
AssessmentAuthority remains blocked
no text-bearing payload is emitted into GitHub-safe reports
```

Even then, S5 may only treat it as:

```text
ReadingAuthorityBridge candidate input
```

S5 must not mark it as:

```text
promoted ReadingAuthority
learner-facing approved content
planner-ready content
assessment-ready content
```

---

## 11. Review Output Status Vocabulary

Recommended status values:

```text
PAGE_PASSAGE_REVIEW_CONTRACT_READY
PAGE_PASSAGE_REVIEW_PRECHECK_PASS
PAGE_PASSAGE_REVIEW_PRECHECK_BLOCKED
PAGE_PASSAGE_REVIEW_PENDING_HUMAN_REVIEW
PAGE_PASSAGE_REVIEW_PASS
PAGE_PASSAGE_REVIEW_FAIL
PAGE_PASSAGE_REVIEW_NEEDS_REVISION
PAGE_PASSAGE_REVIEW_BRIDGE_ELIGIBLE
PAGE_PASSAGE_REVIEW_BRIDGE_BLOCKED
```

S4 DesignScan final status uses:

```text
PAGE_PASSAGE_REVIEW_CONTRACT_DESIGN_READY
```

---

## 12. Proposed Future Implementation

Recommended next task after S4:

```text
RAZ-AW-S4A_PagePassageUnitReviewContract_Implementation
```

Purpose:

```text
Implement a sanitized review-intake/precheck builder that reads the validated linkage view and emits page/passage review candidates plus a sanitized precheck summary.
```

Expected code file:

```text
tools/build_raz_page_passage_review_candidates.py
```

Expected sanitized report:

```text
reports/raz/raz_page_passage_review_contract_summary.json
```

Expected local-only candidate artifact:

```text
raz_output_jsons/review/Level_*/raz_*_page_passage_review_candidates.json
```

Expected validator / QA follow-up:

```text
RAZ-AW-S4B_PagePassageUnitReviewContract_QA
```

S4A should not:

```text
modify legacy derived corpus
modify linkage view
promote authority
create learner-facing content
push text-bearing review artifacts
```

---

## 13. Interaction With S5 Reading Authority Bridge

S5 should depend on S4A/S4B, not just S3K.

Reason:

```text
S3K proves linkage-view contract compliance.
S4 proves page/passage review readiness.
S5 should consume reviewed page/passage candidates, not raw linkage-view page_unit records directly.
```

S5 bridge intake rule:

```text
Only units with PAGE_PASSAGE_REVIEW_BRIDGE_ELIGIBLE may be considered by ReadingAuthorityBridge design.
```

S5 must continue to preserve:

```text
promotion_status = promotion_blocked
authority_status = candidate_only
explicit future promotion task required
```

---

## 14. Risk Analysis

| Risk | Level | Impact | Mitigation |
| --- | --- | --- | --- |
| Page units are mistaken for ReadingAuthority | HIGH | unsafe authority use | keep promotion_status=promotion_blocked and add review_state gate |
| Reuse units bypass review | HIGH | mixed-purpose candidates become reading authority too early | block reuse_unit_candidate direct ReadingAuthority intake |
| Passage units assembled without sequence policy | MEDIUM | passage integrity unreliable | require ordered source_page_unit_ids and same-book policy |
| GitHub report leaks text | HIGH | repository hygiene violation | only ids, hashes, counts, statuses in reports |
| S5 starts before review contract | HIGH | bridge consumes unreviewed page units | make S4A/S4B prerequisite |
| Review status confused with promotion status | HIGH | review pass treated as promotion | review pass only means bridge eligibility, not authority promotion |
| Assessment target accidentally enabled | HIGH | unsafe learner-state effects | block AssessmentAuthority until assessment contract exists |

---

## 15. Final Verdict

Verdict:

```text
PAGE_PASSAGE_REVIEW_CONTRACT_DESIGN_READY
```

Reason:

```text
S3K validated that the authority-linkage view is contract-compliant, candidate-only, and fully promotion-blocked. S4 defines the next review layer required before page/passage records can safely feed a Reading Authority bridge.
```

Controlled final statement:

```text
Proceed to S4A Page/Passage Unit Review Contract Implementation. Do not proceed directly to S5 Reading Authority Bridge until S4A/S4B produce and validate review-eligible page/passage candidates.
```

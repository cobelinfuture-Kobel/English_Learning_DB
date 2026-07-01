# RAZ-AW-S5 Reading Authority Bridge Design Scan

## 1. Preflight

Task:

```text
RAZ-AW-S5_ReadingAuthorityBridge_DesignScan
```

Execution mode:

```text
DesignScan only
```

Predecessors:

```text
RAZ-AW-S3K_AuthorityLinkageViewValidator_QA
RAZ-AW-S4_PagePassageUnitReviewContract_DesignScan
RAZ-AW-S4A_PagePassageUnitReviewContract_Implementation
RAZ-AW-S4A1_PagePassageReviewCandidateCanonicalPageUnitFix
RAZ-AW-S4B_PagePassageUnitReviewContract_QA
```

Dependency status used:

```text
S3K: LINKAGE_VIEW_VALIDATION_PASS
S4:  PAGE_PASSAGE_REVIEW_CONTRACT_DESIGN_READY
S4A: PAGE_PASSAGE_REVIEW_PRECHECK_PASS
S4B: PAGE_PASSAGE_REVIEW_QA_PASS
```

Control flags:

| Control | Status |
| --- | --- |
| implementation allowed | false |
| bridge data generation allowed | false |
| review artifact mutation allowed | false |
| linkage view mutation allowed | false |
| raw corpus modification allowed | false |
| derived corpus modification allowed | false |
| authority promotion allowed | false |
| learner-facing content enablement allowed | false |
| LearningOpportunityBinding allowed | false |
| AssessmentAuthority allowed | false |
| runtime/API/scheduler modification allowed | false |
| GitHub full-text corpus push allowed | false |

Risk level:

```text
Medium
```

Reason:

```text
This task defines the bridge contract between S4B-validated page-unit review candidates and a future ReadingAuthority bridge. It does not create bridge artifacts, promote authority records, or enable learner-facing content.
```

Repository-safe conclusion:

```text
S5 is safe to commit because it is a documentation-only design scan. It contains aggregate counts, status codes, and contract rules only. It contains no RAZ raw text, sentence text, page text, review candidate records, or full derived records.
```

---

## 2. Files Inspected

| Path | Role | Inspection status | Quote safety | Full-text risk |
| --- | --- | --- | --- | --- |
| `reports/raz/raz_page_passage_review_contract_qa.json` | S4B QA evidence | directly inspected | safe aggregate counts only | no text values |
| `docs/raz/RAZ_AW_S4_PAGE_PASSAGE_UNIT_REVIEW_CONTRACT_DESIGN_SCAN.md` | review contract design | dependency accepted | safe_to_quote | no |
| `docs/raz/RAZ_AW_S4A_PAGE_PASSAGE_UNIT_REVIEW_CONTRACT_IMPLEMENTATION.md` | review builder contract | dependency accepted | safe_to_quote | no |
| `docs/raz/RAZ_AW_S4B_PAGE_PASSAGE_UNIT_REVIEW_CONTRACT_QA.md` | review QA contract | dependency accepted | safe_to_quote | no |
| `raz_output_jsons/review/Level_*/raz_*_page_passage_review_candidates.json` | local review candidates | not opened in GitHub scan | local_only_do_not_push | may contain record-level metadata |
| `raz_output_jsons/linkage/Level_*/raz_*_authority_linkage_view.json` | local linkage view | not opened in GitHub scan | local_only_do_not_push | may contain record-level metadata |
| `raz_output_jsons/derived/Level_*/...` | local derived corpus | not opened | full_text_do_not_quote | yes |

S4B aggregate evidence:

```text
status: PAGE_PASSAGE_REVIEW_QA_PASS
files_scanned_count: 23
review_candidates_scanned_count: 22632
summary_expected_candidate_count: 22632
review_state_counts.ready_for_review: 22632
canonical_source_kind_counts.normalized_page_units: 22632
unit_type_counts.page_unit: 22632
authority_status_counts.candidate_only: 22632
promotion_status_counts.promotion_blocked: 22632
review_status_counts.pending: 22632
issue_counts: {}
warnings: []
blockers: []
```

S4B safety evidence:

```text
sanitized: true
contains_text_values: false
raw_mutation: false
derived_mutation: false
linkage_mutation: false
review_artifact_mutation: false
authority_promotion: false
learner_facing_content_enabled: false
```

---

## 3. Problem Statement

S4B proves that canonical page-unit review candidates exist and are structurally valid. They are now safe for bridge inspection.

However, S4B pass does not mean they are ReadingAuthority records.

The bridge gap is:

```text
S4B page_unit review candidates are ready_for_review, but no contract yet defines how they become ReadingAuthorityBridge candidates.
```

S5 must define the bridge contract without crossing the promotion boundary.

S5 answer:

```text
Introduce a ReadingAuthorityBridge candidate layer. It can reference S4B-validated page-unit review candidates as bridge inputs, but it cannot create promoted ReadingAuthority records and cannot enable learner-facing content.
```

---

## 4. Core Design Decision

S5 should not promote page-unit candidates into ReadingAuthority.

S5 should define this intermediate bridge state:

```text
S4B validated page_unit review candidate
        ↓ bridge intake
ReadingAuthorityBridge candidate
        ↓ bridge QA
ReadingAuthority candidate intake only
        ↓ future explicit promotion task
promoted ReadingAuthority
```

Controlled interpretation:

```text
S5 creates the bridge contract. It does not create ReadingAuthority and does not authorize learner-facing use.
```

Important:

```text
ready_for_review is not review_passed.
bridge_intake_ready is not promoted_authority.
ReadingAuthorityBridge candidate is not ReadingAuthority.
```

---

## 5. Bridge Input Contract

Allowed input:

```text
source artifact: raz_output_jsons/review/Level_*/raz_*_page_passage_review_candidates.json
source schema: raz_page_passage_review_contract.v1
unit_type: page_unit
canonical_source_kind: normalized_page_units
review_state: ready_for_review
review_status: pending
promotion_status: promotion_blocked
authority_status: candidate_only
contains_text_values: false
```

Current eligible structural input count:

```text
22632 page-unit review candidates
```

Blocked input:

```text
raw_source_reference
sentence_normalized
sentence_enriched
reuse_unit_candidate
enriched_units as page_unit duplicate identities
passage_unit until a passage-unit builder exists
any generated_content=true record
any promotion_status != promotion_blocked record
any authority_status != candidate_only record
any learner-facing content
```

Reason:

```text
S5 bridge identity must come from canonical normalized_page_units after S4B QA. Enriched page-unit views may later contribute metadata but must not create separate bridge identities.
```

---

## 6. Bridge Candidate Record Shape

Recommended future local-only bridge artifact:

```text
raz_output_jsons/bridge/reading_authority/Level_<LEVEL>/raz_<LEVEL>_reading_authority_bridge_candidates.json
```

Recommended GitHub-safe summary:

```text
reports/raz/raz_reading_authority_bridge_summary.json
```

Recommended bridge candidate record:

```json
{
  "bridge_candidate_uid": "raz_A_100_p0001::reading_authority_bridge_v1",
  "source_review_candidate_uid": "raz_A_100_p0001::authority_linkage_v1::normalized_page_units::page_passage_review_v1",
  "source_linkage_uid": "raz_A_100_p0001::authority_linkage_v1::normalized_page_units",
  "bridge_type": "ReadingAuthorityBridge",
  "unit_type": "page_unit",
  "canonical_source_kind": "normalized_page_units",
  "level": "A",
  "book_uid": "raz_A_100",
  "book_id": "100",
  "page_number": 1,
  "source_traceability": {},
  "authority_status": "candidate_only",
  "promotion_status": "promotion_blocked",
  "bridge_status": "bridge_intake_ready",
  "review_state": "ready_for_review",
  "review_status": "pending",
  "required_review_before_promotion": "reading_authority_review",
  "allowed_authority_targets": ["ReadingAuthority", "ContentQueryLayer"],
  "blocked_authority_targets": ["LearningOpportunityBinding", "AssessmentAuthority", "DialogueAuthority", "WritingAuthority", "ExerciseAuthority", "SentenceAuthority"],
  "bridge_checks": {},
  "bridge_decision": null,
  "contains_text_values": false,
  "content_hash": "hash-only-if-available"
}
```

Text policy:

```text
Bridge reports must use ids, hashes, counts, and status codes only. Do not include sentence text, page text, raw text, full review records, or full bridge candidate records in GitHub-safe outputs.
```

---

## 7. Bridge State Machine

S5 bridge states:

```text
not_in_bridge
bridge_intake_ready
bridge_precheck_failed
bridge_candidate
bridge_qa_passed
bridge_qa_failed
bridge_blocked
eligible_for_reading_authority_intake
```

Allowed transitions:

```text
ready_for_review + candidate_only + promotion_blocked
        ↓ bridge precheck
bridge_intake_ready
        ↓ S5A builder
bridge_candidate
        ↓ S5B QA
bridge_qa_passed
        ↓ future ReadingAuthority intake task
eligible_for_reading_authority_intake
```

Failure transitions:

```text
bridge_intake_ready -> bridge_precheck_failed
bridge_candidate -> bridge_qa_failed
bridge_qa_failed -> bridge_blocked
any unsafe state -> bridge_blocked
```

Forbidden transitions:

```text
ready_for_review -> promoted_authority
bridge_intake_ready -> promoted_authority
bridge_candidate -> promoted_authority
bridge_qa_passed -> promoted_authority
eligible_for_reading_authority_intake -> learner-facing content
eligible_for_reading_authority_intake -> LearningOpportunityBinding
eligible_for_reading_authority_intake -> AssessmentAuthority
```

Important distinction:

```text
bridge_qa_passed means future ReadingAuthority intake may inspect it. It does not mean ReadingAuthority has been created or promoted.
```

---

## 8. Deterministic Bridge Precheck Gates

S5 recommends these deterministic gates before bridge candidate emission:

```text
source review candidate exists
source review schema_version == raz_page_passage_review_contract.v1
unit_type == page_unit
canonical_source_kind == normalized_page_units
source_linkage_uid ends with ::normalized_page_units
review_state == ready_for_review
review_status == pending
promotion_status == promotion_blocked
authority_status == candidate_only
contains_text_values == false
source_traceability present
source_traceability.source_type == raz
source_traceability.source_level == candidate.level
source_traceability.source_book_uid == candidate.book_uid
source_traceability.source_book_id == candidate.book_id
source_traceability.source_page_number == candidate.page_number
source_traceability.source_sentence_candidate_ids non-empty
source_traceability.generated_content == false
source_traceability.derived_from_original_text == true
LearningOpportunityBinding remains blocked
AssessmentAuthority remains blocked
allowed/blocked authority targets have no conflict
```

Bridge output must also assert:

```text
promotion_status == promotion_blocked
authority_status == candidate_only
bridge_status in bridge_intake_ready / bridge_candidate
learner_facing_content_enabled == false
contains_text_values == false
```

---

## 9. Reading Authority Bridge vs Reading Authority

S5 must preserve this separation:

| Layer | Meaning | Authority promotion? | Learner-facing? |
| --- | --- | --- | --- |
| S4B review candidate | Structurally valid page-unit review input | no | no |
| S5 ReadingAuthorityBridge candidate | Candidate mapped into ReadingAuthority bridge contract | no | no |
| future ReadingAuthority intake candidate | Candidate ready for explicit authority-review task | no | no |
| promoted ReadingAuthority | Formal authority record after explicit promotion task | yes | only after separate enablement policy |

Controlled rule:

```text
S5 cannot create promoted ReadingAuthority.
S5 cannot mark candidates as learner-facing.
S5 cannot connect candidates to LearningOpportunityBinding.
```

---

## 10. Bridge Output Status Vocabulary

Recommended status values:

```text
READING_AUTHORITY_BRIDGE_DESIGN_READY
READING_AUTHORITY_BRIDGE_PRECHECK_PASS
READING_AUTHORITY_BRIDGE_PRECHECK_BLOCKED
READING_AUTHORITY_BRIDGE_CANDIDATE_CREATED
READING_AUTHORITY_BRIDGE_QA_PASS
READING_AUTHORITY_BRIDGE_QA_BLOCKED
READING_AUTHORITY_BRIDGE_INTAKE_ELIGIBLE
READING_AUTHORITY_BRIDGE_INTAKE_BLOCKED
```

S5 DesignScan final status uses:

```text
READING_AUTHORITY_BRIDGE_DESIGN_READY
```

---

## 11. Proposed Future Implementation

Recommended next task after S5:

```text
RAZ-AW-S5A_ReadingAuthorityBridge_Implementation
```

Purpose:

```text
Implement a sanitized bridge builder that reads S4B-validated page-unit review candidates and emits local-only ReadingAuthorityBridge candidate artifacts plus a sanitized summary.
```

Expected code file:

```text
tools/build_raz_reading_authority_bridge_candidates.py
```

Expected local-only bridge artifact:

```text
raz_output_jsons/bridge/reading_authority/Level_*/raz_*_reading_authority_bridge_candidates.json
```

Expected sanitized summary:

```text
reports/raz/raz_reading_authority_bridge_summary.json
```

Expected QA follow-up:

```text
RAZ-AW-S5B_ReadingAuthorityBridge_QA
```

S5A should not:

```text
modify raw corpus
modify legacy derived corpus
modify linkage view
modify S4 review candidates
promote authority
create learner-facing content
create LearningOpportunityBinding
create AssessmentAuthority
push text-bearing bridge artifacts
```

---

## 12. GitHub Commit Policy for Future S5A/S5B

Do not push:

```text
raz_output_jsons/bridge/**
raz_output_jsons/review/**
raz_output_jsons/linkage/**
raz_output_jsons/derived/**
raw corpus
text-bearing bridge candidates
```

Allowed to push after local run only if sanitized:

```text
reports/raz/raz_reading_authority_bridge_summary.json
reports/raz/raz_reading_authority_bridge_qa.json
```

Required safety flags:

```text
contains_text_values=false
raw_mutation=false
derived_mutation=false
linkage_mutation=false
review_artifact_mutation=false
bridge_artifact_mutation=false only for validator; builder may create local bridge artifacts
review_candidate_mutation=false
authority_promotion=false
learner_facing_content_enabled=false
LearningOpportunityBinding_created=false
AssessmentAuthority_created=false
```

---

## 13. Risk Analysis

| Risk | Level | Impact | Mitigation |
| --- | --- | --- | --- |
| Bridge candidate mistaken for ReadingAuthority | HIGH | unsafe authority promotion | keep `promotion_status=promotion_blocked`; bridge layer only |
| Review-ready mistaken for review-passed | HIGH | unreviewed content enters authority path | S5 only consumes `ready_for_review` as bridge input, not final authority |
| Learner-facing content enabled too early | HIGH | unapproved content visible to learners | keep `learner_facing_content_enabled=false` |
| LearningOpportunityBinding enabled too early | HIGH | planner may use unpromoted content | explicitly block LearningOpportunityBinding |
| AssessmentAuthority enabled too early | HIGH | learner-state effects without assessment contract | explicitly block AssessmentAuthority |
| Enriched page-unit duplicate becomes bridge identity | MEDIUM | duplicate authority candidates | canonical source kind gate: normalized_page_units only |
| Text leakage in reports | HIGH | repository hygiene violation | reports use ids, counts, statuses, hashes only |
| Passage units skipped too long | MEDIUM | bridge initially page-level only | keep passage_unit as future-contract-only until passage builder exists |

---

## 14. Final Verdict

Verdict:

```text
READING_AUTHORITY_BRIDGE_DESIGN_READY
```

Reason:

```text
S4B validated 22632 canonical normalized_page_units page-unit review candidates. They are structurally ready for bridge inspection while remaining candidate_only, promotion_blocked, pending review, text-free in reports, and not learner-facing. S5 defines a ReadingAuthorityBridge candidate layer that preserves these boundaries and prevents direct authority promotion.
```

Controlled final statement:

```text
Proceed to S5A ReadingAuthorityBridge Implementation only after accepting this bridge contract. S5A may create local-only bridge candidates and a sanitized summary, but it must not create promoted ReadingAuthority, learner-facing content, LearningOpportunityBinding, or AssessmentAuthority.
```

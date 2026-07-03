# E4S-P3-S3 Official Source Reference Manifest Candidate Only

## 1. Current State

Task:

```text
E4S-P3-S3_OfficialSourceReferenceManifest_CandidateOnly
```

Phase:

```text
E4S-P3_SourceManifestAndUsePolicyGovernance
```

Task type:

```text
Candidate-only official source pointer manifest document
```

Deliverable:

```text
docs/e4s/E4S_P3_OFFICIAL_SOURCE_REFERENCE_MANIFEST_CANDIDATE_ONLY.md
```

Data sources:

```text
1. docs/e4s/E4S_P3_SOURCE_USE_POLICY_AND_LICENSING_BOUNDARY_DESIGN_SCAN.md
2. docs/e4s/E4S_P3_SOURCE_MANIFEST_CONTRACT_DESIGN_SCAN.md
3. docs/e4s/E4S_P3_GOVERNED_LAUNCH_PREFLIGHT.md
4. Cambridge English / Cambridge University Press & Assessment public official pages checked as URL pointers only.
```

This task creates no runtime code, validators, tests, source manifest JSON, JSON schema, official asset copies, official sample item copies, PDF downloads, source ingestion, generated question package, student-facing HTML, learner records, or source promotion.

---

## 2. Required Task Header

```text
Task:
E4S-P3-S3_OfficialSourceReferenceManifest_CandidateOnly

Scope:
Create a documentation-only candidate reference manifest for official source URL pointers. This task records pointer candidates, retrieval date, source role, and blocked use boundaries. It does not ingest, copy, download, validate, or promote any source.

Allowed files:
docs/e4s/E4S_P3_OFFICIAL_SOURCE_REFERENCE_MANIFEST_CANDIDATE_ONLY.md

Forbidden files:
tools/*
validators/*
tests/*
output/*
generated/*
site/*
learner_state/*

Current-task blockers:
- P3-S0 must exist.
- P3-S1 must exist.
- P3-S2 must exist.
- Source references must remain pointer-only.
- No official asset may be copied.
- No official sample item may be copied.
- No PDF may be downloaded into the repository.
- No source may be promoted.

Runtime impact:
None.

Promotion impact:
None.

Stop condition:
Stop after this candidate-only pointer manifest is written and P3-S4 is identified as next.
```

---

## 3. Candidate-Only Policy

All records in this file use this status:

```text
source_manifest_instance_status: candidate_only_documentation
promotion_allowed: false
learner_facing_allowed: false
copy_allowed: false
source_ingested: false
asset_copied: false
pdf_downloaded: false
validator_executed: false
```

Allowed use modes for these records:

```text
design_context
format_mapping
source_pointer
metadata_only
evidence_pointer_for_format_or_policy_only
```

Blocked use modes for these records:

```text
copy_full_text
copy_official_item
copy_official_asset
copy_pdf
generate_derivative_item_from_restricted_text
generate_answer_key_from_restricted_item
learner_facing_without_approval
promote_without_review
```

Retrieval date:

```text
2026-07-04
```

---

## 4. Candidate Source Pointer Records

### 4.1 P3SRC-CAMBRIDGE-YLE-PAPER-OVERVIEW

```text
source_manifest_id: P3SRC-CAMBRIDGE-YLE-PAPER-OVERVIEW
source_title: Paper-based Cambridge English Qualifications for young learners
source_provider: Cambridge English / Cambridge University Press & Assessment
source_type: official_exam_format_page
source_access_mode: public_url
source_url: https://www.cambridgeenglish.org/exams-and-tests/qualifications/young-learners/paper/
source_authority_status: format_baseline_only
use_policy_status: pointer_only
assessment_pattern_linkage_allowed: true
answer_evidence_allowed: false
distractor_evidence_allowed: false
promotion_allowed: false
```

### 4.2 P3SRC-CAMBRIDGE-PRE-A1-STARTERS-FORMAT

```text
source_manifest_id: P3SRC-CAMBRIDGE-PRE-A1-STARTERS-FORMAT
source_title: Pre A1 Starters exam format
source_provider: Cambridge English / Cambridge University Press & Assessment
source_type: official_exam_format_page
source_access_mode: public_url
source_url: https://www.cambridgeenglish.org/exams-and-tests/qualifications/young-learners/paper/starters/format/
source_authority_status: format_baseline_only
use_policy_status: pointer_only
assessment_pattern_linkage_allowed: true
answer_evidence_allowed: false
distractor_evidence_allowed: false
promotion_allowed: false
```

### 4.3 P3SRC-CAMBRIDGE-A1-MOVERS-FORMAT

```text
source_manifest_id: P3SRC-CAMBRIDGE-A1-MOVERS-FORMAT
source_title: A1 Movers exam format
source_provider: Cambridge English / Cambridge University Press & Assessment
source_type: official_exam_format_page
source_access_mode: public_url
source_url: https://www.cambridgeenglish.org/exams-and-tests/qualifications/young-learners/paper/movers/format/
source_authority_status: format_baseline_only
use_policy_status: pointer_only
assessment_pattern_linkage_allowed: true
answer_evidence_allowed: false
distractor_evidence_allowed: false
promotion_allowed: false
```

### 4.4 P3SRC-CAMBRIDGE-A2-FLYERS-FORMAT

```text
source_manifest_id: P3SRC-CAMBRIDGE-A2-FLYERS-FORMAT
source_title: A2 Flyers exam format
source_provider: Cambridge English / Cambridge University Press & Assessment
source_type: official_exam_format_page
source_access_mode: public_url
source_url: https://www.cambridgeenglish.org/exams-and-tests/qualifications/young-learners/paper/flyers/format/
source_authority_status: format_baseline_only
use_policy_status: pointer_only
assessment_pattern_linkage_allowed: true
answer_evidence_allowed: false
distractor_evidence_allowed: false
promotion_allowed: false
```

### 4.5 P3SRC-CAMBRIDGE-A2-KEY-FORMAT

```text
source_manifest_id: P3SRC-CAMBRIDGE-A2-KEY-FORMAT
source_title: A2 Key for Schools and A2 Key exam format
source_provider: Cambridge English / Cambridge University Press & Assessment
source_type: official_exam_format_page
source_access_mode: public_url
source_url: https://www.cambridgeenglish.org/exams-and-tests/qualifications/key/format/
source_authority_status: format_baseline_only
use_policy_status: pointer_only
assessment_pattern_linkage_allowed: true
answer_evidence_allowed: false
distractor_evidence_allowed: false
promotion_allowed: false
```

### 4.6 P3SRC-CAMBRIDGE-RIGHTS-PERMISSIONS

```text
source_manifest_id: P3SRC-CAMBRIDGE-RIGHTS-PERMISSIONS
source_title: Rights and Permissions
source_provider: Cambridge University Press & Assessment
source_type: public_reference_page
source_access_mode: public_url
source_url: https://www.cambridge.org/rights-and-permissions
source_authority_status: supporting_reference
use_policy_status: source_pointer
assessment_pattern_linkage_allowed: false
answer_evidence_allowed: false
distractor_evidence_allowed: false
promotion_allowed: false
```

---

## 5. Candidate Manifest Summary

| source_manifest_id | Role | Status | Pattern mapping | Answer evidence | Copy | Promotion |
|---|---|---|---|---|---|---|
| P3SRC-CAMBRIDGE-YLE-PAPER-OVERVIEW | YLE family pointer | candidate_only | yes | no | no | no |
| P3SRC-CAMBRIDGE-PRE-A1-STARTERS-FORMAT | Starters format pointer | candidate_only | yes | no | no | no |
| P3SRC-CAMBRIDGE-A1-MOVERS-FORMAT | Movers format pointer | candidate_only | yes | no | no | no |
| P3SRC-CAMBRIDGE-A2-FLYERS-FORMAT | Flyers format pointer | candidate_only | yes | no | no | no |
| P3SRC-CAMBRIDGE-A2-KEY-FORMAT | A2 Key format pointer | candidate_only | yes | no | no | no |
| P3SRC-CAMBRIDGE-RIGHTS-PERMISSIONS | policy pointer | candidate_only | no | no | no | no |

---

## 6. Deferred Pointer Candidates

Deferred because this task is pointer-only:

```text
- direct sample paper PDF URLs
- downloadable handbook PDFs
- vocabulary list PDFs
- teacher resource downloads
- preparation product pages
- paid or restricted materials
- RAZ source files
- non-Cambridge third-party materials
```

---

## 7. Future Validator Implications

P3-S3 does not implement validators.

A future source-reference validator should check:

```text
- source_manifest_id exists
- source_url exists
- source_provider exists
- source_access_mode is public_url
- retrieval_date exists
- source_authority_status is not authority_approved
- promotion_allowed is false
- copy_allowed is false
- learner_facing_allowed is false
- official format pages are format_baseline_only
- policy pointers are supporting_reference only
- no repository PDF asset path exists
- no official sample item text is stored
```

---

## 8. Non-Goals

This task does not define or implement:

```text
- actual source manifest JSON
- source database
- source ingestion pipeline
- PDF download
- PDF hashing
- page-level extraction
- official sample item copying
- legal review result for any source
- validator code
- validator CLI
- tests
- JSON schema file
- RAZ text extraction
- generated question package
- learner-facing rendering
- source promotion workflow implementation
```

---

## 9. Deferred Issues Register

```text
issue_id: P3-S3-U1-PDF-HASH-AND-PAGE-ANCHORS
classification: FUTURE_WORK
why_deferred: P3-S3 does not download PDFs or create file hashes/page anchors.
recommended_future_task: future source file audit task only after explicit operator approval
blocks_current_task: no
```

```text
issue_id: P3-S3-U2-SPECIFIC-SOURCE-USE-REVIEW
classification: FUTURE_WORK
why_deferred: P3-S3 records policy pointers only and does not decide source rights.
recommended_future_task: manual source-use review before copying, deriving, learner-facing, or redistributing any source content
blocks_current_task: no
```

```text
issue_id: P3-S3-U3-SOURCE-EVIDENCE-LINKAGE
classification: FUTURE_WORK
why_deferred: P3-S3 records source pointers but does not wire them into P2 assessment pattern evidence fields.
recommended_future_task: E4S-P3-S4_SourceEvidenceLinkageToAssessmentPatterns_DesignScan
blocks_current_task: no
```

---

## 10. Gate & Distance Update

### Gate Metrics

```text
[PASS] P3-S2 source-use policy and licensing boundary design scan exists.
[PASS] P3-S3 deliverable path is defined.
[PASS] Candidate-only source pointer policy is declared.
[PASS] Retrieval date is declared.
[PASS] YLE paper overview pointer is recorded.
[PASS] Pre A1 Starters format pointer is recorded.
[PASS] A1 Movers format pointer is recorded.
[PASS] A2 Flyers format pointer is recorded.
[PASS] A2 Key format pointer is recorded.
[PASS] Cambridge rights and permissions pointer is recorded.
[PASS] Candidate manifest summary is defined.
[PASS] Deferred pointer candidates are recorded.
[PASS] Future validator implications are defined.
[PASS] no actual source manifest JSON is created.
[PASS] no source database is created.
[PASS] no PDF is downloaded.
[PASS] no official asset is copied.
[PASS] no official sample item text is copied.
[PASS] no source-use decision is made.
[PASS] no source ingestion is performed.
[PASS] no runtime code is created.
[PASS] no validator code is created.
[PASS] no test is created.
[PASS] no generated JSON is created.
[PASS] no student-facing HTML is created.
[PASS] no learner record is created.
[PASS] no source is promoted.
```

### Distance Vector

```text
Total Distance for Phase 3:
D_P3 = 2 sub-tasks left after this candidate-only pointer manifest

Current Sub-task Status:
E4S-P3-S3_OfficialSourceReferenceManifest_CandidateOnly -> COMPLETED

Remaining:
P3-S4  SourceEvidenceLinkageToAssessmentPatterns_DesignScan NEXT
P3-S5  Phase3ReadbackQA                                     DEFERRED
```

### Phase 3 Current Status

```text
E4S-P3_STATUS = OFFICIAL_SOURCE_REFERENCE_MANIFEST_CANDIDATE_ONLY_COMPLETED
```

---

## 11. Next Shortest Step

```text
NEXT_SHORT_STEP:
E4S-P3-S4_SourceEvidenceLinkageToAssessmentPatterns_DesignScan
```

唯一執行動作：

```text
請下達：
E4S-P3-S4_SourceEvidenceLinkageToAssessmentPatterns_DesignScan
```

Next task boundary:

```text
P3-S4 may define how official source pointers link to P2 assessment-pattern evidence fields.
P3-S4 must not create source manifest JSON, copy official assets, copy official sample items, download PDFs into the repo, create learner-facing content, implement validators, implement schema, create generated question packages, or promote source authority.
```

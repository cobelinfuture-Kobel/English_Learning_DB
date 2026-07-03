# E4S-P3-S4 Source Evidence Linkage to Assessment Patterns Design Scan

## 1. Current State

當前主任務（Epic ID）：

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

中文名稱：

```text
英語四技能來源可追蹤練習系統
```

當前 Phase：

```text
E4S-P3_SourceManifestAndUsePolicyGovernance
```

當前子任務（Sub-task ID）：

```text
E4S-P3-S4_SourceEvidenceLinkageToAssessmentPatterns_DesignScan
```

本次任務類型：

```text
DesignScan only
```

核心資料來源與排序依據（Data Sources）：

```text
1. docs/e4s/E4S_P3_OFFICIAL_SOURCE_REFERENCE_MANIFEST_CANDIDATE_ONLY.md
   - P3-S4 is the next shortest step.
   - Official source pointers are candidate-only, pointer-only, not copied, not downloaded, and not promoted.
   - Format pages may support assessment pattern mapping but cannot support answer_evidence or distractor_evidence.

2. docs/e4s/E4S_P3_SOURCE_USE_POLICY_AND_LICENSING_BOUNDARY_DESIGN_SCAN.md
   - Defines copy, quote, summary, derivative, learner-facing, redistribution, and attribution boundaries.

3. docs/e4s/E4S_P3_SOURCE_MANIFEST_CONTRACT_DESIGN_SCAN.md
   - Defines source manifest fields, evidence linkage fields, authority status, synthetic fixture policy, and future validator implications.

4. docs/e4s/E4S_P2_ASSESSMENT_PATTERN_CONTRACT_DESIGN_SCAN.md
   - Defines assessment pattern source/evidence requirements and future answer evidence expectations.

5. docs/e4s/E4S_P2_ASSESSMENT_PATTERN_VALIDATOR_CONTRACT_DESIGN_SCAN.md
   - Defines future source_trace_validator and evidence_validator expectations.

6. 重點任務排程.txt
   - Every task must follow Current State / Core Execution / Gate & Distance Update / Next Shortest Step.
   - Anti-Scope-Creep applies.
```

外接儲存權限驗證：

```text
GitHub: [核准] 讀取專案 / 透過 API 寫入代碼或專案檔案
Google Drive: [核准] 讀取雲端硬碟參考檔案、Spec 或資料集
```

本次交握產出目標（Deliverable）：

```text
docs/e4s/E4S_P3_SOURCE_EVIDENCE_LINKAGE_TO_ASSESSMENT_PATTERNS_DESIGN_SCAN.md
```

本次任務不產出：

```text
- no runtime code
- no tools/*.py
- no validators/*.py
- no tests/*.py
- no source manifest JSON
- no evidence linkage JSON
- no JSON schema file
- no copied official assets
- no copied official sample items
- no downloaded official PDFs
- no source ingestion
- no generated question package
- no student-facing HTML
- no learner records
- no source-use decision
- no source promotion
```

---

## 2. Required Task Header

```text
Task:
E4S-P3-S4_SourceEvidenceLinkageToAssessmentPatterns_DesignScan

Scope:
Define how candidate official source pointers may link to P2 assessment-pattern evidence fields. This includes linkage roles, permitted evidence scopes, disallowed evidence uses, pattern-family linkage rules, source authority constraints, and future validator implications.

Allowed files:
docs/e4s/E4S_P3_SOURCE_EVIDENCE_LINKAGE_TO_ASSESSMENT_PATTERNS_DESIGN_SCAN.md

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
- P3-S3 must exist.
- Linkage design must remain documentation-only.
- No evidence linkage JSON may be created.
- No official source asset may be copied.
- No PDF may be downloaded.
- No answer key or distractor evidence may be derived from official format pages.
- No source may be promoted.

Warning policy:
Unresolved linkage, page-anchor, hash, PDF, sample-paper, and legal-use questions may be recorded as deferred issues. They must not expand this task into ingestion, validation, copying, or legal review.

Generated artifact policy:
Generated artifacts are not allowed in this task.

Runtime impact:
None.

Promotion impact:
None. This task defines linkage rules only. It does not approve, promote, ingest, copy, redistribute, or learner-face any source.

Stop condition:
Stop after the linkage design-scan document is written and P3-S5 is identified as the next shortest step.

Deferred issues register:
All actual linkage JSON, source manifest JSON, validators, schemas, PDF/file hashes, page-level source audits, official sample item evidence, learner-facing rendering, and promotion are deferred.
```

---

## 3. Core Execution

### 3.1 Purpose

P3-S4 defines the bridge between:

```text
P3 official source pointers
```

and

```text
P2 assessment pattern evidence fields
```

It answers:

```text
When a future assessment pattern record references an official source pointer, what may that pointer prove, and what must it not prove?
```

It does not create actual assessment pattern records.

It does not create source evidence JSON.

It does not validate source links by code.

---

### 3.2 Central Rule

Official format pages can support pattern-level claims.

They cannot support item-level answer correctness unless a future reviewed source explicitly permits that use.

Default rule:

```text
format_baseline_only -> pattern_structure_evidence only
format_baseline_only -> not answer_evidence
format_baseline_only -> not distractor_evidence
supporting_reference -> policy or context pointer only
synthetic_non_authority -> fixture design only
```

---

## 4. Source Evidence Linkage Object

Future linkage records should use a conceptual object:

```text
source_evidence_linkage_record
```

Required field groups:

```text
link_identity
source_pointer
assessment_pattern_target
linkage_role
allowed_evidence_scope
blocked_evidence_scope
use_policy_snapshot
traceability
review_status
```

This is a design contract only. It is not a JSON schema.

---

## 5. Required Linkage Fields

Required fields:

```text
linkage_id
source_manifest_id
source_authority_status
use_policy_status
assessment_pattern_id
assessment_pattern_family
question_type
cambridge_path_alias
linkage_role
evidence_scope
evidence_granularity
evidence_pointer_format
allowed_for_pattern_mapping
allowed_for_answer_evidence
allowed_for_distractor_evidence
copy_allowed
learner_facing_allowed
promotion_allowed
review_status
```

Rules:

```text
- source_manifest_id must reference a candidate source pointer.
- source_authority_status controls evidence scope.
- allowed_for_answer_evidence and allowed_for_distractor_evidence default to false.
- copy_allowed must remain false for P3 official source pointers.
- learner_facing_allowed must remain false unless future approval exists.
- promotion_allowed must remain false inside Phase 3.
```

---

## 6. Linkage Role Enum

Allowed linkage_role values:

```text
pattern_structure_evidence
exam_part_mapping_evidence
question_type_mapping_evidence
format_boundary_evidence
source_policy_reference
source_navigation_reference
candidate_fixture_context
not_allowed
```

Role rules:

```text
pattern_structure_evidence: supports that a pattern family exists or has a structure.
exam_part_mapping_evidence: supports mapping of an exam part to an internal pattern family.
question_type_mapping_evidence: supports mapping of external task form to internal question_type.
format_boundary_evidence: supports boundary decisions such as Reading vs Writing boundary.
source_policy_reference: points to rights / permissions / legal overview pages.
source_navigation_reference: helps locate official exam-family pages.
candidate_fixture_context: supports synthetic sample documentation only.
not_allowed: explicit blocked linkage.
```

Blocked roles for official format pages:

```text
answer_correctness_evidence
distractor_rejection_evidence
copied_item_content_evidence
learner_response_scoring_evidence
authority_promotion_evidence
```

---

## 7. Evidence Scope Matrix

| source_authority_status | Allowed evidence scope | Blocked evidence scope |
|---|---|---|
| format_baseline_only | pattern_structure, exam_part_mapping, question_type_mapping, format_boundary | answer_correctness, distractor_rejection, copied_content, learner_scoring |
| supporting_reference | policy_context, source_navigation, citation_context | pattern_answer_evidence, distractor_evidence, copied_content |
| synthetic_non_authority | fixture_context, design_example_context | official_format_claim, production_answer_evidence, promotion_evidence |
| authority_candidate | review_context, candidate_pointer | authority_approved_claim, learner_facing_claim, promotion_evidence |
| authority_approved | future policy-defined only | anything not explicitly allowed | 
| unknown_unverified | metadata_only | all assessment evidence |
| blocked_use | audit_metadata_only | all pattern, answer, distractor, learner-facing evidence |
```

Default:

```text
If a source authority status is unknown or ambiguous, block all assessment-pattern linkage except metadata-only audit context.
```

---

## 8. Pattern Family Linkage Rules

### 8.1 Cambridge YLE Pattern Families

Allowed source pointer records:

```text
P3SRC-CAMBRIDGE-YLE-PAPER-OVERVIEW
P3SRC-CAMBRIDGE-PRE-A1-STARTERS-FORMAT
P3SRC-CAMBRIDGE-A1-MOVERS-FORMAT
P3SRC-CAMBRIDGE-A2-FLYERS-FORMAT
```

Allowed linkage roles:

```text
source_navigation_reference
pattern_structure_evidence
exam_part_mapping_evidence
question_type_mapping_evidence
format_boundary_evidence
```

Blocked linkage:

```text
- answer_correctness_evidence
- distractor_rejection_evidence
- copied_item_content_evidence
- learner_response_scoring_evidence
```

Rule:

```text
YLE official format pages may support future pattern mapping records, but they cannot provide answer evidence or reusable item content in this Phase 3 linkage layer.
```

### 8.2 A2 Key / KET Pattern Families

Allowed source pointer record:

```text
P3SRC-CAMBRIDGE-A2-KEY-FORMAT
```

Allowed linkage roles:

```text
pattern_structure_evidence
exam_part_mapping_evidence
question_type_mapping_evidence
format_boundary_evidence
```

Special boundary:

```text
A2 Key Parts 1-5 may support Reading pattern mapping.
A2 Key Parts 6-7 may support writing_boundary documentation only.
```

Blocked linkage:

```text
- answer_correctness_evidence
- distractor_rejection_evidence
- copied_item_content_evidence
- writing_response_scoring_evidence
```

### 8.3 Rights / Permissions Policy Pointer

Allowed source pointer record:

```text
P3SRC-CAMBRIDGE-RIGHTS-PERMISSIONS
```

Allowed linkage roles:

```text
source_policy_reference
source_navigation_reference
```

Blocked linkage:

```text
- assessment_pattern_linkage
- answer_correctness_evidence
- distractor_rejection_evidence
- permission_granted_claim
- legal_decision_claim
```

Rule:

```text
A policy pointer can remind future tasks to review rights and permissions. It does not grant use rights by itself.
```

---

## 9. Evidence Pointer Format

Future linkage records should use pointer-based evidence references such as:

```text
source_manifest_id
source_url
retrieval_date
page_or_section_anchor_if_available
linkage_role
evidence_scope
use_policy_status
```

For P3-S4, copied source text is not allowed.

Allowed pointer styles:

```text
url_pointer
section_pointer
page_anchor_future
metadata_pointer
policy_pointer
```

Blocked pointer styles:

```text
copied_full_text
copied_sample_item
copied_answer_key
copied_image_or_audio
local_pdf_path_without_approval
```

---

## 10. Linkage Readiness Levels

Allowed readiness values:

```text
linkage_design_ready
candidate_pointer_ready
source_audit_required
policy_review_required
blocked_until_source_review
blocked_until_explicit_promotion
```

Rules:

```text
- format pages may be candidate_pointer_ready for pattern mapping.
- answer evidence linkage from official sample items is blocked_until_source_review.
- copied official assets are blocked_until_explicit_promotion and explicit use approval.
- unknown source rights imply policy_review_required.
```

---

## 11. Future Validator Implications

P3-S4 does not implement validators.

A future source-evidence-linkage validator should check:

```text
- linkage_id exists
- source_manifest_id exists
- assessment_pattern_id exists when linking to a real pattern record
- source_authority_status is compatible with evidence_scope
- format_baseline_only is not used for answer_correctness evidence
- supporting_reference is not used as assessment answer evidence
- policy pointer is not used as legal permission
- copy_allowed is false for official format pages unless future approval exists
- learner_facing_allowed is false unless future approval exists
- promotion_allowed is false inside Phase 3
- evidence_pointer_format does not contain copied item content
```

Future blocking error groups may include:

```text
E4S_P3_LINKAGE_MISSING_ID_*
E4S_P3_LINKAGE_MISSING_SOURCE_*
E4S_P3_LINKAGE_SOURCE_SCOPE_MISMATCH_*
E4S_P3_LINKAGE_FORMAT_USED_AS_ANSWER_EVIDENCE_*
E4S_P3_LINKAGE_POLICY_POINTER_MISUSED_*
E4S_P3_LINKAGE_COPIED_CONTENT_BLOCKED_*
E4S_P3_LINKAGE_LEARNER_FACING_BLOCKED_*
E4S_P3_LINKAGE_PROMOTION_BLOCKED_*
```

---

## 12. Non-Goals

This task does not define or implement:

```text
- actual source evidence linkage JSON
- actual source manifest JSON
- source database
- source ingestion pipeline
- validator code
- validator CLI
- tests
- JSON schema file
- PDF download
- PDF hashing
- page-level extraction
- official sample item copying
- legal review result for any source
- RAZ text extraction
- generated question package
- learner-facing rendering
- source promotion workflow implementation
```

---

## 13. Deferred Issues Register

```text
issue_id: P3-S4-U1-ACTUAL-LINKAGE-JSON
classification: FUTURE_WORK
why_deferred: P3-S4 defines linkage contract only and does not create data artifacts.
recommended_future_task: post-P3 implementation track after Phase 3 readback QA
blocks_current_task: no
```

```text
issue_id: P3-S4-U2-PDF-PAGE-ANCHORS
classification: FUTURE_WORK
why_deferred: P3-S4 does not download or inspect PDFs and therefore cannot assign file hashes or page-level anchors.
recommended_future_task: explicit source file audit task only after operator approval
blocks_current_task: no
```

```text
issue_id: P3-S4-U3-ANSWER-EVIDENCE-FROM-OFFICIAL-SAMPLES
classification: FUTURE_WORK
why_deferred: P3-S4 blocks official format pages from serving as answer evidence and does not review sample-paper use rights.
recommended_future_task: manual source-use review before any official sample item evidence is considered
blocks_current_task: no
```

```text
issue_id: P3-S4-U4-SOURCE-LINKAGE-VALIDATOR
classification: FUTURE_WORK
why_deferred: P3-S4 records future validator implications but does not implement validator code.
recommended_future_task: post-P3 validator implementation track only after Phase 3 readback QA
blocks_current_task: no
```

---

## 14. Gate & Distance Update

### Gate Metrics

```text
[PASS] P3-S3 candidate-only official source pointer manifest exists.
[PASS] P3-S4 deliverable path is defined.
[PASS] Source evidence linkage object is defined.
[PASS] Required linkage fields are defined.
[PASS] linkage_role enum is defined.
[PASS] Evidence scope matrix is defined.
[PASS] Cambridge YLE pattern linkage rules are defined.
[PASS] A2 Key / KET pattern linkage rules are defined.
[PASS] Rights / permissions policy pointer linkage rules are defined.
[PASS] Evidence pointer format is defined.
[PASS] Linkage readiness levels are defined.
[PASS] Future validator implications are defined.
[PASS] no actual source evidence linkage JSON is created.
[PASS] no actual source manifest JSON is created.
[PASS] no PDF is downloaded.
[PASS] no official asset is copied.
[PASS] no official sample item text is copied.
[PASS] no answer evidence is derived from official format pages.
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
D_P3 = 1 sub-task left after this design scan

Current Sub-task Status:
E4S-P3-S4_SourceEvidenceLinkageToAssessmentPatterns_DesignScan -> COMPLETED

Remaining:
P3-S5  Phase3ReadbackQA                                     NEXT
```

### Phase 3 Current Status

```text
E4S-P3_STATUS = SOURCE_EVIDENCE_LINKAGE_TO_ASSESSMENT_PATTERNS_DESIGN_SCAN_COMPLETED
```

---

## 15. Next Shortest Step

```text
NEXT_SHORT_STEP:
E4S-P3-S5_Phase3ReadbackQA
```

唯一執行動作：

```text
請下達：
E4S-P3-S5_Phase3ReadbackQA
```

Next task boundary:

```text
P3-S5 may perform documentation readback QA across P3-S0 through P3-S4.
P3-S5 must not create source manifest JSON, source linkage JSON, copy official assets, copy official sample items, download PDFs into the repo, create learner-facing content, implement validators, implement schema, create generated question packages, or promote source authority.
```

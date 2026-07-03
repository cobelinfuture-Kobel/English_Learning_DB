# E4S-P3-S2 Source Use Policy and Licensing Boundary Design Scan

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
E4S-P3-S2_SourceUsePolicyAndLicensingBoundary_DesignScan
```

本次任務類型：

```text
DesignScan only
```

核心資料來源與排序依據（Data Sources）：

```text
1. docs/e4s/E4S_P3_SOURCE_MANIFEST_CONTRACT_DESIGN_SCAN.md
   - P3-S2 is the next shortest step.
   - P3-S2 may define source-use policy and licensing boundary only.
   - P3-S2 must not create source manifest JSON, copy official assets, implement validators, implement schema, create generated question packages, create student-facing HTML, or promote source authority.

2. docs/e4s/E4S_P3_GOVERNED_LAUNCH_PREFLIGHT.md
   - Phase 3 only handles source manifest, source-use policy, source location fields, licensing/use boundary, and source governance before future schema/validator implementation.

3. docs/e4s/E4S_P2_PHASE2_READBACK_QA.md
   - P2 is closed as documentation-design line.
   - Production generation, validation, learner-facing use, and authority promotion are not ready.

4. 重點任務排程.txt
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
docs/e4s/E4S_P3_SOURCE_USE_POLICY_AND_LICENSING_BOUNDARY_DESIGN_SCAN.md
```

本次任務不產出：

```text
- no runtime code
- no tools/*.py
- no validators/*.py
- no tests/*.py
- no source manifest JSON
- no JSON schema file
- no official source ingestion
- no copied official assets
- no copied official sample items
- no downloaded official PDFs
- no RAZ text extraction
- no generated question package
- no student-facing HTML
- no learner records
- no legal determination
- no source promotion
```

---

## 2. Required Task Header

```text
Task:
E4S-P3-S2_SourceUsePolicyAndLicensingBoundary_DesignScan

Scope:
Define the source-use policy and licensing boundary contract for Phase 3. This includes allowed use modes, blocked use modes, quote/copy/summarize/derive/redistribute boundaries, learner-facing gates, commercial-use flags, attribution requirements, review states, and future validator implications.

Allowed files:
docs/e4s/E4S_P3_SOURCE_USE_POLICY_AND_LICENSING_BOUNDARY_DESIGN_SCAN.md

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
- This task must not create actual source manifest instances.
- This task must not copy or download official assets.
- This task must not make legal conclusions about any specific external source.
- This task must not implement validator or schema code.

Warning policy:
Unresolved licensing or use-policy questions must be recorded as deferred issues. They must not expand this task into ingestion, source copying, validator implementation, or legal advice.

Generated artifact policy:
Generated artifacts are not allowed in this task.

Runtime impact:
None.

Promotion impact:
None. This task defines policy gates only. It does not approve, promote, ingest, copy, or redistribute any source.

Stop condition:
Stop after the source-use policy and licensing boundary design-scan document is written and P3-S3 is identified as the next shortest step.

Deferred issues register:
All source manifest JSON creation, official source reference candidates, legal review, validator code, schema files, source ingestion, generated packages, learner-facing rendering, and promotion are deferred.
```

---

## 3. Core Execution

### 3.1 Purpose

P3-S2 defines how a future source manifest record must declare allowed and blocked uses.

It answers:

```text
Before a source is used by E4S, what policy must be known about quoting, copying, summarizing, deriving, referencing, validating, redistributing, and learner-facing use?
```

It does not answer:

```text
Is a specific external source legally licensed for this project?
```

This document is a design boundary. It is not legal advice.

---

### 3.2 Policy Principle

A source may be useful but still unusable for some modes.

A source-use policy must separate:

```text
- source discovery
- source reference
- source metadata use
- source excerpt use
- source copying
- source-derived item generation
- internal validation
- learner-facing presentation
- redistribution
- authority promotion
```

Default rule:

```text
When use rights are unknown, allow only metadata-level design reference and block copy, derivative generation, learner-facing use, redistribution, and promotion.
```

---

## 4. Source-Use Policy Object

Future source manifest records should include a conceptual field group:

```text
source_use_policy
```

Required subgroups:

```text
use_classification
allowed_use_modes
blocked_use_modes
copy_boundary
quote_boundary
summary_boundary
derivative_boundary
learner_facing_boundary
redistribution_boundary
attribution_boundary
review_boundary
```

This is not a committed JSON schema.

---

## 5. Use Classification

Required fields:

```text
use_policy_id
use_policy_status
rights_basis
rights_basis_detail
policy_review_status
policy_review_owner
policy_review_date
```

Allowed use_policy_status values:

```text
not_reviewed
design_reference_only
metadata_only
pointer_only
limited_excerpt_allowed
internal_use_only
candidate_validation_only
learner_facing_requires_future_approval
blocked
```

Allowed rights_basis values:

```text
unknown
internal_original
user_provided_for_review
public_reference_only
official_reference_pointer
licensed_content
open_license_claimed
third_party_restricted
blocked_source
```

Rules:

```text
- unknown defaults to metadata_only or pointer_only.
- public availability does not imply copy permission.
- official_reference_pointer supports source pointing and format mapping, not copying official items.
- open_license_claimed requires license details and future verification before learner-facing use.
- licensed_content requires license scope fields before any learner-facing or redistribution use.
```

Blocked states:

```text
- rights_basis unknown with copy_full_text allowed
- official_reference_pointer with copy_official_item allowed
- third_party_restricted with learner_facing use allowed
- blocked_source used for assessment evidence
```

---

## 6. Allowed Use Modes

Required field:

```text
allowed_use_modes
```

Allowed values:

```text
design_context
format_mapping
source_pointer
metadata_only
evidence_pointer
limited_short_quote
summary_only
internal_review
internal_validation
candidate_fixture
candidate_manifest_record
learner_facing_after_future_approval
```

Rules:

```text
- design_context allows discussing the source at design level.
- format_mapping allows using source to describe structure or task format.
- source_pointer allows storing URL, file pointer, page anchor, or section pointer.
- metadata_only allows non-content metadata such as title, provider, retrieval date, and source type.
- evidence_pointer allows linking to a location, not copying source content.
- limited_short_quote requires quote boundary fields.
- summary_only allows paraphrase-level design notes, not replacement content.
- internal_validation allows future validator checks only if source policy permits.
- learner_facing_after_future_approval is a gated mode, not immediate permission.
```

---

## 7. Blocked Use Modes

Required field:

```text
blocked_use_modes
```

Blocked values:

```text
copy_full_text
copy_official_item
copy_official_asset
copy_long_excerpt
copy_audio
copy_image
copy_pdf
redistribute_third_party_asset
generate_derivative_item_from_restricted_text
generate_answer_key_from_restricted_item
learner_facing_without_approval
commercial_use_without_review
train_model_without_policy
promote_without_review
```

Rules:

```text
- Official exam/sample items are blocked from copying unless a future explicit use policy says otherwise.
- Third-party reading text is blocked from full-copy use unless license scope explicitly allows it.
- Asset copying is separate from text copying.
- Answer key derivation from restricted official item content is blocked unless explicitly approved.
- Commercial or public redistribution requires future review.
```

---

## 8. Copy Boundary

Required fields:

```text
copy_policy
copy_allowed
copy_scope
copy_limit
copy_storage_allowed
copy_redistribution_allowed
copy_requires_review
```

Allowed copy_policy values:

```text
no_copy
metadata_only
pointer_only
short_quote_limited
internal_excerpt_limited
full_copy_allowed_by_license
blocked
```

Rules:

```text
- Default copy_policy is pointer_only when source rights are unknown.
- Official source pages may be referenced but not copied unless policy is explicitly approved.
- full_copy_allowed_by_license requires rights_basis = licensed_content or verified open license.
- copy_storage_allowed and copy_redistribution_allowed must be separately declared.
```

Blocked states:

```text
- copied official sample item without explicit approval
- full text stored when copy_policy is pointer_only
- copied source stored in generated package without redistribution permission
```

---

## 9. Quote Boundary

Required fields:

```text
quote_policy
quote_allowed
quote_limit
quote_context
quote_requires_citation
quote_requires_review
```

Allowed quote_policy values:

```text
no_quote
short_quote_for_design_context
short_quote_for_evidence_pointer
internal_excerpt_only
quote_allowed_by_license
blocked
```

Rules:

```text
- Short quote allowance is not the same as learner-facing allowance.
- Quote use must not recreate the source item, passage, worksheet, or official prompt.
- Quote context must be design, evidence pointer, or internal review unless future approval says otherwise.
```

Blocked states:

```text
- quoting enough text to reconstruct a protected item
- quoting official sample item stem/options/answer as reusable content
- learner-facing quote with no future approval
```

---

## 10. Summary Boundary

Required fields:

```text
summary_policy
summary_allowed
summary_scope
summary_must_avoid_reconstruction
summary_requires_citation
```

Allowed summary_policy values:

```text
no_summary
design_summary_only
format_summary_only
metadata_summary_only
internal_review_summary
summary_allowed_by_license
blocked
```

Rules:

```text
- Summary may describe source structure or policy relevance.
- Summary must not replace the original source as an item bank.
- Summary must not reconstruct official sample items or restricted reading passages.
```

---

## 11. Derivative Boundary

Required fields:

```text
derivative_policy
derivative_allowed
derivative_scope
derivative_requires_review
derivative_must_not_reconstruct_source
derivative_learner_facing_allowed
```

Allowed derivative_policy values:

```text
no_derivative
format_inspired_only
metadata_informed_only
internal_candidate_only
derivative_allowed_by_license
blocked
```

Rules:

```text
- format_inspired_only means the system may follow task shape, not copy content.
- metadata_informed_only means source may inform tags, not item text.
- internal_candidate_only means derived material cannot be learner-facing or promoted.
- derivative_allowed_by_license requires explicit license fields.
```

Blocked states:

```text
- generating questions by paraphrasing restricted official sample items
- deriving answer choices from copied restricted options
- making learner-facing derivatives before future approval
```

---

## 12. Learner-Facing Boundary

Required fields:

```text
learner_facing_policy
learner_facing_allowed
learner_facing_conditions
learner_facing_review_required
learner_facing_approval_task_ref
```

Allowed learner_facing_policy values:

```text
not_allowed
requires_future_approval
internal_preview_only
allowed_after_license_review
allowed_original_internal_content_only
blocked
```

Rules:

```text
- Default learner_facing_allowed is false.
- learner_facing_after_future_approval does not mean current approval.
- Official or third-party content cannot become learner-facing without explicit future approval.
- Synthetic fixtures remain not_allowed unless future operator opens a separate content creation/promotion task.
```

Blocked states:

```text
- learner-facing use with not_reviewed use policy
- learner-facing use of copied official sample item
- learner-facing use of restricted third-party text
```

---

## 13. Redistribution Boundary

Required fields:

```text
redistribution_policy
redistribution_allowed
redistribution_scope
redistribution_conditions
commercial_use_policy
```

Allowed redistribution_policy values:

```text
not_allowed
metadata_only
source_pointer_only
internal_repo_only
allowed_by_license
blocked
```

Rules:

```text
- Redistribution must be treated separately from internal reference.
- GitHub storage is not automatically redistribution-safe for third-party content.
- Google Drive storage is not automatically redistribution-safe for third-party content.
- Public site deployment requires learner-facing and redistribution approval.
```

---

## 14. Attribution and Citation Boundary

Required fields:

```text
citation_required
citation_format
attribution_required
attribution_text_policy
source_pointer_required
retrieval_date_required
```

Rules:

```text
- Official or public reference sources should preserve source pointer and retrieval date.
- Citation does not override blocked copy/derivative/redistribution modes.
- Attribution text should not imply endorsement by the source provider.
```

Blocked states:

```text
- using citation as substitute for permission
- missing source pointer for evidence usage
- source provider endorsement implied without approval
```

---

## 15. Policy Matrix by Source Authority Status

| source_authority_status | Default allowed | Default blocked | Notes |
|---|---|---|---|
| authority_candidate | metadata, pointer, design review | learner-facing, promotion | requires future review |
| authority_approved | policy-defined only | anything not explicitly allowed | requires promotion task reference |
| supporting_reference | design_context, source_pointer | final answer evidence alone | useful for context, not sole authority |
| format_baseline_only | format_mapping, source_pointer | copied items, answer keys | supports structure, not content copy |
| synthetic_non_authority | candidate_fixture, design_context | authority evidence, learner-facing | must remain non-authority |
| licensed_limited_use | license-defined only | unspecified rights | must attach license scope |
| blocked_use | none except audit metadata | all content use | cannot support candidates |
| unknown_unverified | metadata_only, pointer_only | copy, derivative, learner-facing | requires review |
| retired | historical reference only | new production use | needs explicit compatibility task |

---

## 16. Future Validator Implications

P3-S2 does not implement validators.

A future source-use-policy validator should check:

```text
- allowed_use_modes exists
- blocked_use_modes exists
- copy_policy exists
- quote_policy exists
- summary_policy exists
- derivative_policy exists
- learner_facing_policy exists
- redistribution_policy exists
- citation fields exist when source is external
- rights_basis is compatible with requested use modes
- official_reference_pointer does not allow copy_official_item
- unknown rights do not allow learner-facing or derivative generation
- synthetic_non_authority does not allow authority evidence
- learner-facing use has explicit future approval reference
- authority_approved has promotion_task_ref
```

Future blocking error groups may include:

```text
E4S_P3_USE_POLICY_MISSING_*
E4S_P3_USE_POLICY_INCOMPATIBLE_RIGHTS_*
E4S_P3_USE_POLICY_COPY_BLOCKED_*
E4S_P3_USE_POLICY_QUOTE_BLOCKED_*
E4S_P3_USE_POLICY_DERIVATIVE_BLOCKED_*
E4S_P3_USE_POLICY_LEARNER_FACING_BLOCKED_*
E4S_P3_USE_POLICY_REDISTRIBUTION_BLOCKED_*
E4S_P3_USE_POLICY_ATTRIBUTION_MISSING_*
E4S_P3_USE_POLICY_PROMOTION_BLOCKED_*
```

---

## 17. Non-Goals

This task does not define or implement:

```text
- legal review result for any specific source
- actual source manifest JSON
- official source candidate list
- source ingestion pipeline
- validator code
- validator CLI
- tests
- JSON schema file
- downloaded official PDFs
- copied official sample items
- RAZ text extraction
- generated question package
- learner-facing rendering
- source promotion workflow implementation
```

---

## 18. Deferred Issues Register

```text
issue_id: P3-S2-U1-SPECIFIC-SOURCE-LEGAL-REVIEW
severity: normal
classification: FUTURE_WORK
why_deferred: P3-S2 defines policy fields only and does not decide rights for any specific source.
recommended_future_task: manual legal/use review before learner-facing or redistribution use
blocks_current_task: no
```

```text
issue_id: P3-S2-U2-OFFICIAL-SOURCE-REFERENCE-MANIFEST
severity: normal
classification: FUTURE_WORK
why_deferred: P3-S2 does not create actual source manifest records.
recommended_future_task: E4S-P3-S3_OfficialSourceReferenceManifest_CandidateOnly
blocks_current_task: no
```

```text
issue_id: P3-S2-U3-SOURCE-EVIDENCE-LINKAGE
severity: normal
classification: FUTURE_WORK
why_deferred: P3-S2 defines use boundaries but does not wire sources to P2 assessment pattern evidence.
recommended_future_task: E4S-P3-S4_SourceEvidenceLinkageToAssessmentPatterns_DesignScan
blocks_current_task: no
```

```text
issue_id: P3-S2-U4-SOURCE-USE-POLICY-VALIDATOR
severity: normal
classification: FUTURE_WORK
why_deferred: P3-S2 records future validator implications but does not implement validator code.
recommended_future_task: post-P3 validator implementation track only after Phase 3 readback QA
blocks_current_task: no
```

---

## 19. Gate & Distance Update

### Gate Metrics

```text
[PASS] P3-S1 source manifest contract design scan exists.
[PASS] P3-S2 deliverable path is defined.
[PASS] Source-use policy object is defined.
[PASS] use_policy_status enum is defined.
[PASS] rights_basis enum is defined.
[PASS] allowed_use_modes are defined.
[PASS] blocked_use_modes are defined.
[PASS] copy boundary is defined.
[PASS] quote boundary is defined.
[PASS] summary boundary is defined.
[PASS] derivative boundary is defined.
[PASS] learner-facing boundary is defined.
[PASS] redistribution boundary is defined.
[PASS] attribution/citation boundary is defined.
[PASS] policy matrix by source authority status is defined.
[PASS] future validator implications are defined.
[PASS] no legal determination is made.
[PASS] no actual source manifest JSON is created.
[PASS] no official source candidate list is created.
[PASS] no official asset is copied.
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
D_P3 = 3 sub-tasks left after this design scan

Current Sub-task Status:
E4S-P3-S2_SourceUsePolicyAndLicensingBoundary_DesignScan -> COMPLETED

Remaining:
P3-S3  OfficialSourceReferenceManifest_CandidateOnly       NEXT
P3-S4  SourceEvidenceLinkageToAssessmentPatterns_DesignScan DEFERRED
P3-S5  Phase3ReadbackQA                                    DEFERRED
```

### Phase 3 Current Status

```text
E4S-P3_STATUS = SOURCE_USE_POLICY_AND_LICENSING_BOUNDARY_DESIGN_SCAN_COMPLETED
```

---

## 20. Next Shortest Step

```text
NEXT_SHORT_STEP:
E4S-P3-S3_OfficialSourceReferenceManifest_CandidateOnly
```

唯一執行動作：

```text
請下達：
E4S-P3-S3_OfficialSourceReferenceManifest_CandidateOnly
```

Next task boundary:

```text
P3-S3 may create a candidate-only reference manifest document for official source pointers only.
P3-S3 must not copy official assets, copy official sample items, download PDFs into the repo, create learner-facing content, implement validators, implement schema, create generated question packages, or promote source authority.
```

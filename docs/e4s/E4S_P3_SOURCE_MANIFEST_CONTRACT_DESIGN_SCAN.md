# E4S-P3-S1 Source Manifest Contract Design Scan

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
E4S-P3-S1_SourceManifestContract_DesignScan
```

本次任務類型：

```text
DesignScan only
```

核心資料來源與排序依據（Data Sources）：

```text
1. docs/e4s/E4S_P3_GOVERNED_LAUNCH_PREFLIGHT.md
   - P3-S1 is the next shortest step.
   - P3-S1 may define source manifest contract only.
   - P3-S1 must not create source manifest JSON, copy official assets, implement validators, implement schema, create generated question packages, create student-facing HTML, or promote source authority.

2. docs/e4s/E4S_P2_PHASE2_READBACK_QA.md
   - P2 closed as documentation-design line with warnings.
   - Source manifest / source-use policy remains deferred.

3. docs/e4s/E4S_P2_ASSESSMENT_PATTERN_VALIDATOR_CONTRACT_DESIGN_SCAN.md
   - Future validators require source_artifact_ref, source trace, evidence trace, and promotion controls.

4. docs/e4s/E4S_P2_ASSESSMENT_PATTERN_SAMPLE_PACKAGE_CANDIDATE_ONLY.md
   - Synthetic fixtures are non-authority and must not become promoted sources.

5. 重點任務排程.txt
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
docs/e4s/E4S_P3_SOURCE_MANIFEST_CONTRACT_DESIGN_SCAN.md
```

本次任務不產出：

```text
- no runtime code
- no tools/*.py
- no validators/*.py
- no tests/*.py
- no output/*
- no generated/*
- no source manifest JSON
- no JSON schema file
- no student-facing HTML
- no learner records
- no official source ingestion
- no copied official assets
- no generated question package
- no final authority content
- no promotion
```

---

## 2. Required Task Header

```text
Task:
E4S-P3-S1_SourceManifestContract_DesignScan

Scope:
Define the source manifest contract for Phase 3 source governance, including source identity fields, source type enum, source authority status, access mode, location references, version/hash policy, page/unit anchor policy, use-mode declarations, blocked use modes, synthetic fixture policy, and linkage expectations for P2 assessment patterns.

Allowed files:
docs/e4s/E4S_P3_SOURCE_MANIFEST_CONTRACT_DESIGN_SCAN.md

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
- P2-S7 readback QA must exist.
- Source manifest contract must not become a source manifest instance.
- No official source asset may be copied.
- No source may be promoted to authority.
- No validator or schema may be implemented.

Warning policy:
Contract gaps may be recorded as deferred issues. They must not expand this task into implementation or ingestion.

Generated artifact policy:
Generated artifacts are not allowed in this task.

Runtime impact:
None.

Promotion impact:
None. This task defines source manifest fields but does not promote any source, sample, source bundle, provider, or pattern.

Stop condition:
Stop after the source manifest contract design-scan document is written and P3-S2 is identified as the next shortest step.

Deferred issues register:
All source manifest JSON creation, official source ingestion, source-use policy finalization, validators, schemas, tests, generated packages, learner-facing rendering, and promotion are deferred.
```

---

## 3. Core Execution

### 3.1 Purpose

P3-S1 defines the contract for future source manifest records.

It answers:

```text
What fields must exist before a future source, source bundle, public format reference, official reference, synthetic fixture, or third-party material can be referenced by E4S assessment patterns?
```

It does not answer:

```text
Which specific sources are approved?
```

It does not create source records.

It does not ingest source files.

It does not copy official materials.

---

### 3.2 Contract Principle

A source manifest record is not content.

It is a governance record that describes:

```text
- what the source is
- where it came from
- how it can be referenced
- how precisely it can be located
- what its authority status is
- what use modes are allowed
- what use modes are blocked
- what evidence linkage is required before it can support assessment patterns
```

---

## 4. Source Manifest Object Contract

Future manifest records should be shaped around this conceptual object:

```text
source_manifest_record
```

Required top-level field groups:

```text
identity
classification
access
location
versioning
use_policy
authority_status
evidence_linkage
risk_controls
review_status
```

This is a design contract only. It is not a committed JSON schema.

---

## 5. Required Fields

### 5.1 Identity Fields

Required fields:

```text
source_manifest_id
source_id
source_title
source_provider
source_collection
source_language
source_description
```

Rules:

```text
- source_manifest_id identifies the manifest record.
- source_id identifies the source within E4S governance.
- source_title must be human-readable.
- source_provider must identify the publisher, platform, repository, or internal fixture owner.
- source_collection may be null only if the source is standalone.
- source_language should use a stable language tag when possible.
```

Blocked states:

```text
- source with no provider
- source with no title
- source_id reused for unrelated source
- synthetic fixture without explicit fixture owner
```

---

### 5.2 Classification Fields

Required fields:

```text
source_type
source_subtype
source_domain
intended_skill_scope
cefr_scope_hint
learner_level_scope_hint
```

Allowed source_type values:

```text
official_exam_format_page
official_sample_paper
official_wordlist
official_handbook
licensed_reading_text
internal_synthetic_fixture
internal_design_document
public_reference_page
user_provided_file
repository_artifact
google_drive_artifact
```

Rules:

```text
- source_type describes the kind of source, not whether it is approved.
- intended_skill_scope may include reading, writing, listening, speaking, grammar, vocabulary, assessment_pattern, or source_policy.
- cefr_scope_hint is advisory and must not override validated level metadata.
```

Blocked states:

```text
- official source recorded as public_reference_page to avoid use-policy checks
- synthetic fixture recorded as official source
- user_provided_file recorded without provenance
```

---

### 5.3 Access Fields

Required fields:

```text
source_access_mode
source_access_location
access_restriction
retrieval_method
retrieval_date
```

Allowed source_access_mode values:

```text
public_url
uploaded_file
google_drive_file
github_repo_file
licensed_local_file
synthetic_inline_fixture
unknown_or_unresolved
```

Rules:

```text
- public_url requires URL and retrieval_date.
- uploaded_file requires local or connector file reference and upload context.
- google_drive_file requires Drive file reference or folder context when available.
- github_repo_file requires repository path and ref when available.
- synthetic_inline_fixture must remain non-authority unless future review explicitly changes it.
- unknown_or_unresolved cannot support production validation.
```

Blocked states:

```text
- production candidate using unknown_or_unresolved source
- copied official asset without source-use policy
- external source with no retrieval date
```

---

### 5.4 Location Fields

Required fields:

```text
source_location_ref
source_url
source_file_ref
source_repo_path
source_page_anchor
source_unit_anchor
source_excerpt_policy
```

Rules:

```text
- At least one location reference must be present.
- source_page_anchor is required when citing a PDF or official handbook page.
- source_unit_anchor is required when citing a reading unit, item family, section, table, or row.
- source_excerpt_policy must define whether text can be quoted, summarized, referenced by pointer only, or not used directly.
```

Blocked states:

```text
- source reference with no stable location
- PDF source without page anchor when used for evidence
- source text copied into manifest when policy says pointer-only
```

---

### 5.5 Versioning and Hash Fields

Required fields:

```text
source_version_label
retrieval_date
content_hash
hash_algorithm
hash_scope
version_change_policy
```

Allowed hash_scope values:

```text
whole_file
single_page
selected_section
metadata_only
not_available
```

Rules:

```text
- whole_file hash is preferred for downloaded files.
- public web pages may use retrieval_date plus URL when hash is not stable.
- not_available requires reason.
- version_change_policy must state how future changes are handled.
```

Blocked states:

```text
- downloaded source file with no hash and no reason
- source update silently replacing prior evidence
- stale source used without version note
```

---

## 6. Authority Status Contract

Required field:

```text
source_authority_status
```

Allowed values:

```text
authority_candidate
authority_approved
supporting_reference
format_baseline_only
synthetic_non_authority
licensed_limited_use
blocked_use
unknown_unverified
retired
```

Rules:

```text
- authority_candidate means eligible for review, not approved.
- authority_approved requires explicit future promotion task.
- supporting_reference can support design context but not final item evidence alone.
- format_baseline_only can describe exam structure but not provide copied item content.
- synthetic_non_authority can support design fixtures only.
- licensed_limited_use requires explicit use constraints.
- blocked_use cannot support generated or learner-facing content.
- unknown_unverified cannot support production validation.
- retired cannot be used for new production candidates unless historical compatibility is explicitly approved.
```

Default:

```text
New sources default to authority_candidate or unknown_unverified; they do not default to authority_approved.
```

---

## 7. Use Policy Contract

Required fields:

```text
allowed_use_modes
blocked_use_modes
excerpt_policy
copy_policy
derivative_policy
learner_facing_policy
redistribution_policy
citation_requirement
```

Allowed use modes:

```text
design_context
format_mapping
source_pointer
evidence_pointer
metadata_only
candidate_fixture
internal_validation
learner_facing_after_future_approval
```

Blocked use modes:

```text
copy_full_text
copy_official_item
copy_official_asset
redistribute_third_party_asset
generate_derivative_item_from_restricted_text
learner_facing_without_approval
promote_without_review
```

Rules:

```text
- Every source must declare allowed_use_modes.
- Every source must declare blocked_use_modes.
- Official exam pages may support format_mapping and source_pointer unless a later use policy allows more.
- Synthetic fixtures may support candidate_fixture but not authority evidence.
- Licensed sources require explicit license/use details before learner-facing use.
```

---

## 8. Evidence Linkage Contract

Required fields:

```text
evidence_linkage_allowed
evidence_granularity
evidence_pointer_format
assessment_pattern_linkage_allowed
answer_evidence_allowed
distractor_evidence_allowed
```

Allowed evidence_granularity values:

```text
source_level
page_level
section_level
row_level
item_family_level
unit_level
sentence_level
span_level
metadata_level
```

Rules:

```text
- assessment_pattern_linkage_allowed means the source can support pattern design or pattern mapping.
- answer_evidence_allowed means the source can support answer correctness.
- distractor_evidence_allowed means the source can support distractor rejection reasons.
- format_baseline_only sources may support pattern mapping but not copied sample answers.
- synthetic_non_authority sources may support fixture design only.
```

Blocked states:

```text
- answer evidence linked to a source that allows only design_context
- distractor evidence linked to a source with no evidence granularity
- pattern mapping using an untraceable source
```

---

## 9. Synthetic Fixture Policy

Synthetic fixture records must include:

```text
synthetic_fixture_owner
synthetic_fixture_purpose
synthetic_fixture_scope
synthetic_fixture_limitations
synthetic_fixture_promotion_allowed
```

Required values:

```text
source_authority_status: synthetic_non_authority
synthetic_fixture_promotion_allowed: false
learner_facing_policy: not_allowed
```

Rules:

```text
- Synthetic fixtures are allowed for design scans and candidate-only documentation samples.
- Synthetic fixtures must not become authority content by reuse.
- Synthetic fixtures cannot support official format claims.
- Synthetic fixtures cannot support production answer evidence.
```

---

## 10. Review Status Contract

Required fields:

```text
review_status
review_owner
review_date
review_notes
promotion_candidate
promotion_task_ref
```

Allowed review_status values:

```text
not_reviewed
reviewed_for_design_context
reviewed_for_candidate_use
approved_for_internal_reference
approved_for_limited_use
blocked
retired
```

Rules:

```text
- review_status does not equal authority_status.
- promotion_candidate may be true only if future review permits.
- promotion_task_ref is required before authority_approved can be assigned.
```

Blocked states:

```text
- authority_approved with no promotion_task_ref
- learner-facing use with not_reviewed status
- production validator evidence from blocked or retired source
```

---

## 11. Future Validator Implications

P3-S1 does not implement validators.

A future source-manifest validator should check:

```text
- required identity fields exist
- source_type is allowed
- source_access_mode is allowed
- source_authority_status is allowed
- unknown_or_unresolved sources cannot support production validation
- synthetic_non_authority cannot become answer evidence authority
- allowed_use_modes and blocked_use_modes exist
- source_location_ref exists
- page/unit anchor exists when needed
- hash policy exists or explains why unavailable
- official assets are not copied without policy
- authority_approved requires promotion_task_ref
- learner-facing use requires future approval
```

Future blocking error groups may include:

```text
E4S_P3_SOURCE_IDENTITY_*
E4S_P3_SOURCE_CLASSIFICATION_*
E4S_P3_SOURCE_ACCESS_*
E4S_P3_SOURCE_LOCATION_*
E4S_P3_SOURCE_HASH_*
E4S_P3_SOURCE_AUTHORITY_*
E4S_P3_SOURCE_USE_POLICY_*
E4S_P3_SOURCE_EVIDENCE_LINKAGE_*
E4S_P3_SOURCE_SYNTHETIC_FIXTURE_*
E4S_P3_SOURCE_REVIEW_STATUS_*
E4S_P3_SOURCE_PROMOTION_*
```

---

## 12. Non-Goals

This task does not define or implement:

```text
- actual source manifest JSON
- source database
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

## 13. Deferred Issues Register

```text
issue_id: P3-S1-U1-SOURCE-USE-POLICY-DETAIL
severity: normal
classification: FUTURE_WORK
why_deferred: P3-S1 defines source manifest fields only. Full use-policy and licensing boundary should be handled in P3-S2.
recommended_future_task: E4S-P3-S2_SourceUsePolicyAndLicensingBoundary_DesignScan
blocks_current_task: no
```

```text
issue_id: P3-S1-U2-OFFICIAL-SOURCE-MANIFEST-CANDIDATES
severity: normal
classification: FUTURE_WORK
why_deferred: P3-S1 does not create source manifest instances.
recommended_future_task: E4S-P3-S3_OfficialSourceReferenceManifest_CandidateOnly
blocks_current_task: no
```

```text
issue_id: P3-S1-U3-SOURCE-EVIDENCE-LINKAGE
severity: normal
classification: FUTURE_WORK
why_deferred: P3-S1 defines linkage fields only. Assessment-pattern linkage should be designed separately.
recommended_future_task: E4S-P3-S4_SourceEvidenceLinkageToAssessmentPatterns_DesignScan
blocks_current_task: no
```

```text
issue_id: P3-S1-U4-SOURCE-MANIFEST-VALIDATOR
severity: normal
classification: FUTURE_WORK
why_deferred: P3-S1 records future validator implications but does not implement validator code.
recommended_future_task: post-P3 validator implementation track only after Phase 3 readback QA
blocks_current_task: no
```

---

## 14. Gate & Distance Update

### Gate Metrics

```text
[PASS] P3-S0 governed launch preflight exists.
[PASS] P3-S1 deliverable path is defined.
[PASS] Source manifest object contract is defined.
[PASS] Identity fields are defined.
[PASS] Classification fields are defined.
[PASS] source_type enum is defined.
[PASS] Access fields are defined.
[PASS] source_access_mode enum is defined.
[PASS] Location fields are defined.
[PASS] Versioning and hash fields are defined.
[PASS] source_authority_status enum is defined.
[PASS] Use policy fields are defined.
[PASS] Allowed use modes are defined.
[PASS] Blocked use modes are defined.
[PASS] Evidence linkage fields are defined.
[PASS] evidence_granularity enum is defined.
[PASS] Synthetic fixture policy is defined.
[PASS] Review status contract is defined.
[PASS] Future validator implications are defined.
[PASS] No source manifest JSON is created.
[PASS] No official asset is copied.
[PASS] No runtime code is created.
[PASS] No validator code is created.
[PASS] No test is created.
[PASS] No generated JSON is created.
[PASS] No student-facing HTML is created.
[PASS] No learner record is created.
[PASS] No source is promoted.
```

### Distance Vector

```text
Total Distance for Phase 3:
D_P3 = 4 sub-tasks left after this design scan

Current Sub-task Status:
E4S-P3-S1_SourceManifestContract_DesignScan -> COMPLETED

Remaining:
P3-S2  SourceUsePolicyAndLicensingBoundary_DesignScan      NEXT
P3-S3  OfficialSourceReferenceManifest_CandidateOnly       DEFERRED
P3-S4  SourceEvidenceLinkageToAssessmentPatterns_DesignScan DEFERRED
P3-S5  Phase3ReadbackQA                                    DEFERRED
```

### Phase 3 Current Status

```text
E4S-P3_STATUS = SOURCE_MANIFEST_CONTRACT_DESIGN_SCAN_COMPLETED
```

---

## 15. Next Shortest Step

```text
NEXT_SHORT_STEP:
E4S-P3-S2_SourceUsePolicyAndLicensingBoundary_DesignScan
```

唯一執行動作：

```text
請下達：
E4S-P3-S2_SourceUsePolicyAndLicensingBoundary_DesignScan
```

Next task boundary:

```text
P3-S2 may define source-use policy and licensing boundary only.
P3-S2 must not create source manifest JSON, copy official assets, implement validators, implement schema, create generated question packages, create student-facing HTML, or promote source authority.
```

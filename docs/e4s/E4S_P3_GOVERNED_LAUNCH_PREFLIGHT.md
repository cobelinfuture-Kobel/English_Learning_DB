# E4S-P3-S0 Governed Launch and Preflight

## 1. Current State

正式啟動 Phase 3。

當前主任務（Epic ID）：

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

中文名稱：

```text
英語四技能來源可追蹤練習系統
```

前置 Phase 狀態：

```text
E4S-P2_STATUS = PHASE_2_DOCUMENTATION_READBACK_QA_COMPLETED_WITH_WARNINGS
E4S-P2_PROMOTION_STATUS = NOT_PROMOTED
E4S-P2_IMPLEMENTATION_STATUS = NOT_IMPLEMENTED_DOCUMENTATION_ONLY
E4S-P2_SAMPLE_PACKAGE_STATUS = CANDIDATE_ONLY_DOCUMENTATION_NOT_VALIDATED
D_P2 = 0
```

當前 Phase：

```text
E4S-P3_SourceManifestAndUsePolicyGovernance
```

當前子任務（Sub-task ID）：

```text
E4S-P3-S0_GovernedLaunchAndPreflight
```

本次任務類型：

```text
Governed launch preflight only
```

核心資料來源與排序依據（Data Sources）：

```text
1. docs/e4s/E4S_P2_PHASE2_READBACK_QA.md
   - P2 documentation-design line is complete with warnings.
   - P2 remaining distance is zero.
   - P2 is not promoted and not implemented.
   - Post-P2 state is awaiting operator decision.

2. docs/e4s/E4S_P2_ASSESSMENT_PATTERN_VALIDATOR_CONTRACT_DESIGN_SCAN.md
   - Future validator requires source_artifact_ref and source trace.
   - Source manifest is prerequisite for production-grade validation.

3. docs/e4s/E4S_P2_ASSESSMENT_PATTERN_SAMPLE_PACKAGE_CANDIDATE_ONLY.md
   - P2 sample package uses synthetic non-authority fixtures.
   - Synthetic fixtures must not become authority content.

4. docs/e4s/E4S_P2_CAMBRIDGE_YLE_PATTERN_MAPPING_DESIGN_SCAN.md
   - Cambridge YLE mapping used public format baseline only.
   - Exact official source references, page anchors, hashes, and use policy are deferred.

5. docs/e4s/E4S_P2_KET_READING_PATTERN_MAPPING_DESIGN_SCAN.md
   - A2 Key mapping used current public format baseline only.
   - Exact official source references, page anchors, hashes, and use policy are deferred.

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
docs/e4s/E4S_P3_GOVERNED_LAUNCH_PREFLIGHT.md
```

本次任務不產出：

```text
- no runtime code
- no tools/*.py
- no validators/*.py
- no tests/*.py
- no generated JSON
- no JSON schema file
- no student-facing HTML
- no learner records
- no official source ingestion
- no copied Cambridge assets
- no generated question package
- no final authority content
- no promotion
```

---

## 2. Core Execution

### 2.1 Phase 3 Active Scope

Phase 3 is formally opened as a governed source-manifest and source-use-policy track.

Active Phase 3 objective:

```text
把 P2 已完成的 assessment pattern documentation line 接到可追蹤來源治理層。
Phase 3 只處理來源清單、來源使用政策、來源定位欄位、授權/使用邊界、以及後續 schema/validator 實作前需要的 source governance contract。
```

Phase 3 is not a request to add more question types.

Phase 3 is not a request to generate practice questions.

Phase 3 is not a request to implement validators.

### 2.2 Why Phase 3 Exists

P2 closeout is complete, but P2 intentionally left several warnings:

```text
- no executable validator exists yet
- no source manifest / source-use policy exists yet
- candidate sample package is not code-validated
- some sample coverage is intentionally deferred
- writing boundary remains deferred
```

Phase 3 addresses only the source-manifest and source-use-policy warning.

It does not address every P2 warning at once.

### 2.3 Phase 3 Hard Boundary

Phase 3 must prevent these mistakes:

```text
- treating synthetic fixtures as authority content
- treating public format snapshots as official source evidence
- copying official Cambridge or other third-party sample items into the repo without policy
- building validators before source references are stable
- building schema before source authority fields are stable
- expanding into student-facing practice or generated question banks
```

### 2.4 Phase 3 Forbidden Scope

The following are explicitly out of scope for Phase 3 launch:

```text
- bulk question generation
- generated question bank
- official Cambridge item reproduction
- RAZ text ingestion
- student-facing UI
- answer checker runtime
- validator implementation
- schema implementation
- adaptive learning
- learner weak-point diagnosis
- wrong-answer concept tagging
- writing generation
- listening audio
- speaking scoring
- ASR
- final authority promotion
```

### 2.5 Phase 3 Allowed Work Types

Phase 3 may define documentation contracts for:

```text
- source manifest object
- source identity fields
- source type enum
- source authority status enum
- source-use policy fields
- allowed/blocked source usage modes
- official source reference requirements
- file hash / URL / page anchor policy
- source evidence linkage to P2 assessment patterns
- synthetic fixture boundary
- third-party asset non-copy policy
- future source-manifest validator requirements
```

Phase 3 may not implement these contracts until a separate implementation task is approved.

---

## 3. Required Task Header Template for Phase 3 Subtasks

Every Phase 3 subtask must include:

```text
Task:
Scope:
Allowed files:
Forbidden files:
Current-task blockers:
Warning policy:
Generated artifact policy:
Runtime impact:
Promotion impact:
Stop condition:
Deferred issues register:
```

Default forbidden files for Phase 3 DesignScan tasks:

```text
tools/*
validators/*
tests/*
output/*
generated/*
site/*
learner_state/*
```

---

## 4. Phase 3 Initial Subtask Queue

The shortest safe sequence is:

```text
P3-S0  GovernedLaunchAndPreflight                         COMPLETED_BY_THIS_FILE
P3-S1  SourceManifestContract_DesignScan                  NEXT
P3-S2  SourceUsePolicyAndLicensingBoundary_DesignScan     DEFERRED
P3-S3  OfficialSourceReferenceManifest_CandidateOnly      DEFERRED
P3-S4  SourceEvidenceLinkageToAssessmentPatterns_DesignScan DEFERRED
P3-S5  Phase3ReadbackQA                                   DEFERRED
```

Distance:

```text
D_P3 = 5 sub-tasks left after this launch preflight
```

Anti-scope-creep rule:

```text
Do not add schema implementation, validator implementation, generated JSON package, or learner-facing output to the P3 queue unless the operator explicitly opens a post-P3 implementation track.
```

---

## 5. P3-S1 Proposed Scope

Recommended next task:

```text
E4S-P3-S1_SourceManifestContract_DesignScan
```

Allowed deliverable:

```text
docs/e4s/E4S_P3_SOURCE_MANIFEST_CONTRACT_DESIGN_SCAN.md
```

P3-S1 may define:

```text
- source_manifest_id
- source_id
- source_type
- source_title
- source_provider
- source_authority_status
- source_access_mode
- source_location_ref
- source_version_or_retrieval_date
- source_hash_policy
- page_or_unit_anchor_policy
- allowed_use_modes
- blocked_use_modes
- evidence_linkage_requirements
- synthetic_fixture_policy
```

P3-S1 must not create:

```text
- source manifest JSON
- official asset copies
- validators
- tests
- runtime code
- generated question packages
- student-facing HTML
- learner records
- promoted source authority
```

---

## 6. Gate & Distance Update

### Gate Metrics

```text
[PASS] P2 readback QA exists.
[PASS] P2 distance is zero.
[PASS] P2 remains not promoted.
[PASS] P2 remains documentation-only / not implemented.
[PASS] Operator formally approved Phase 3 start.
[PASS] GitHub write permission is acknowledged.
[PASS] Google Drive read permission is acknowledged.
[PASS] Phase 3 active scope is defined.
[PASS] Phase 3 forbidden scope is defined.
[PASS] Phase 3 initial subtask queue is defined.
[PASS] P3-S1 proposed next task is defined.
[PASS] No runtime code is created.
[PASS] No validator code is created.
[PASS] No test is created.
[PASS] No generated JSON is created.
[PASS] No student-facing HTML is created.
[PASS] No learner record is created.
[PASS] No official source asset is copied.
[PASS] No candidate or source is promoted.
```

### Distance Vector

```text
Total Distance for Phase 3:
D_P3 = 5 sub-tasks left after this launch preflight

Current Sub-task Status:
E4S-P3-S0_GovernedLaunchAndPreflight -> COMPLETED

Remaining:
P3-S1  SourceManifestContract_DesignScan                   NEXT
P3-S2  SourceUsePolicyAndLicensingBoundary_DesignScan      DEFERRED
P3-S3  OfficialSourceReferenceManifest_CandidateOnly       DEFERRED
P3-S4  SourceEvidenceLinkageToAssessmentPatterns_DesignScan DEFERRED
P3-S5  Phase3ReadbackQA                                    DEFERRED
```

### Phase 3 Current Status

```text
E4S-P3_STATUS = PHASE_3_STARTED_GOVERNED_PREFLIGHT_ONLY
```

---

## 7. Next Shortest Step

```text
NEXT_SHORT_STEP:
E4S-P3-S1_SourceManifestContract_DesignScan
```

唯一執行動作：

```text
請下達：
E4S-P3-S1_SourceManifestContract_DesignScan
```

Next task boundary:

```text
P3-S1 may define source manifest contract only.
P3-S1 must not create source manifest JSON, copy official assets, implement validators, implement schema, create generated question packages, create student-facing HTML, or promote source authority.
```

# E4S-P2 Assessment Pattern Expansion Launch Preflight

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
E4S-P2_AssessmentPatternExpansion
```

當前子任務（Sub-task ID）：

```text
E4S-P2-S0_AssessmentPatternExpansion_GovernedLaunchAndPreflight
```

本次交握狀態：

```text
PHASE_2_OPERATOR_APPROVED_START
```

核心資料來源與排序依據（Data Sources）：

```text
1. 重點任務排程.txt
   - 雲端智慧體開發交握公版
   - 單一任務聚焦
   - Current State / Core Execution / Gate / Next Shortest Step 格式

2. RAZ-AW-V1 Status Snapshot.txt
   - E4S-ROOT epic definition
   - E4S-P2_AssessmentPatternExpansion phase definition
   - P2 target: Cambridge / worksheet / formal assessment pattern expansion

3. RAZ-AW-S11 Implementation.txt
   - Reading System V2 = Assessment pattern expansion
   - P2/V2 boundary: standardize pattern contracts, not bulk generation
   - P2/V2 exclusions: no adaptive learning, no error diagnosis, no writing generation, no listening audio, no speaking scoring

4. GitHub repository
   - cobelinfuture-Kobel/English_Learning_DB
   - default branch: main
   - current write permission: verified
```

外接儲存權限驗證：

```text
GitHub: [已授權] 讀取專案 / 透過 API 寫入專案檔案
Google Drive: [已授權] 讀取雲端硬碟參考檔案、Spec 或資料集
```

本次交握產出目標（Deliverable）：

```text
Create this governed Phase 2 launch preflight document:

docs/e4s/E4S_P2_ASSESSMENT_PATTERN_EXPANSION_LAUNCH_PREFLIGHT.md
```

本次任務不產出：

```text
- no runtime code
- no generator
- no validator
- no generated question package
- no schema promotion
- no learner-facing artifact
- no adaptive or error-tagging feature
```

---

## 2. Core Execution

### 2.1 Phase 2 Active Scope

Phase 2 is now formally opened only as a governed assessment-pattern expansion track.

The active Phase 2 objective is:

```text
把 Reading 題型擴充到 Cambridge / worksheet / formal assessment pattern，
但第一步只建立可審核、可驗證、可追蹤來源的題型合約邊界。
```

The approved Phase 2 focus is not more question volume. It is pattern contract standardization.

Required contract dimensions:

```text
- question_type contract
- answer_model
- distractor policy
- validation rule
- difficulty rule
- source requirement
- evidence trace requirement
```

### 2.2 Phase 2 Candidate Pattern Families

Phase 2 may cover the following pattern families only after their contract is defined:

```text
- Cambridge Starters / Movers / Flyers pattern mapping
- KET-style reading item pattern
- matching
- multiple_choice
- gap_fill
- short_answer
- picture_text_matching
- reading_comprehension_set
```

These are candidate pattern families, not implemented artifacts.

### 2.3 Phase 2 Forbidden Scope

The following are explicitly out of scope for this launch task and must remain deferred:

```text
- adaptive learning
- learner weak-point diagnosis
- wrong-answer concept tagging
- writing generation
- listening audio
- speaking prompt / speaking scoring
- ASR
- student-facing app UI
- bulk AI-generated question bank
- final authority promotion
```

### 2.4 Anti-Scope-Creep Lock

This document only opens Phase 2 governance.

It does not authorize direct implementation of any Phase 2 generator, validator, schema, UI, dataset, or learner-facing practice package.

Any next implementation must start from a separate subtask with its own:

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

### 2.5 Phase 2 Initial Subtask Queue

The shortest safe sequence is:

```text
P2-S0  AssessmentPatternExpansion_GovernedLaunchAndPreflight        COMPLETED_BY_THIS_FILE
P2-S1  AssessmentPatternContract_DesignScan                         NEXT
P2-S2  CambridgeYLEPatternMapping_DesignScan                        DEFERRED
P2-S3  KETReadingPatternMapping_DesignScan                          DEFERRED
P2-S4  DistractorPolicyAndAnswerModel_DesignScan                    DEFERRED
P2-S5  AssessmentPatternValidatorContract_DesignScan                DEFERRED
P2-S6  AssessmentPatternSamplePackage_CandidateOnly                 DEFERRED
P2-S7  Phase2ReadbackQA                                             DEFERRED
```

### 2.6 P2-S1 Proposed Scope

Recommended next task:

```text
E4S-P2-S1_AssessmentPatternContract_DesignScan
```

Allowed deliverable for P2-S1:

```text
docs/e4s/E4S_P2_ASSESSMENT_PATTERN_CONTRACT_DESIGN_SCAN.md
```

P2-S1 must define, but not implement:

```text
- canonical assessment pattern object
- question_type enum
- answer_model families
- distractor policy fields
- evidence/source trace requirements
- validation requirement matrix
- difficulty tagging fields
- forbidden generated-content promotion rule
```

P2-S1 must not create:

```text
- tools/*.py
- validators/*.py
- tests/*.py
- generated JSON
- student-facing HTML
- learner records
```

---

## 3. Gate & Distance Update

### Gate Metrics

```text
[PASS] GitHub repository read permission verified.
[PASS] GitHub repository write permission verified.
[PASS] Phase 2 operator approval recorded.
[PASS] Phase 2 scope restricted to Assessment Pattern Expansion.
[PASS] P2 launch artifact written to GitHub.
[PASS] No runtime code changed.
[PASS] No generated dataset committed.
[PASS] No schema promotion performed.
[PASS] No learner-facing artifact created.
[PASS] Anti-scope-creep boundary recorded.
```

### Distance Vector

```text
Total Distance for Phase 2:
D_P2 = 7 sub-tasks left after this launch preflight

Current Sub-task Status:
E4S-P2-S0_AssessmentPatternExpansion_GovernedLaunchAndPreflight -> COMPLETED

Next Sub-task Status:
E4S-P2-S1_AssessmentPatternContract_DesignScan -> READY_FOR_OPERATOR_TRIGGER
```

### Phase 2 Current Status

```text
E4S-P2_STATUS = PHASE_2_STARTED_GOVERNED_PREFLIGHT_ONLY
```

---

## 4. Next Shortest Step

```text
NEXT_SHORT_STEP:
E4S-P2-S1_AssessmentPatternContract_DesignScan
```

唯一執行動作：

```text
請下達：
E4S-P2-S1_AssessmentPatternContract_DesignScan
```

After that, the next task should create only the Phase 2 assessment pattern contract design-scan document and must not implement code or generated artifacts.

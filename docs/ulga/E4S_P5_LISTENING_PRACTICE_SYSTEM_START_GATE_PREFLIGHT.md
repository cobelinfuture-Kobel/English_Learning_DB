# E4S P5 Listening Practice System Start Gate Preflight

## 1. Current State

Epic ID:

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

Chinese Name:

```text
英語四技能來源可追蹤練習系統
```

Requested Phase:

```text
E4S-P5_ListeningPracticeSystem
```

Current Sub-task:

```text
E4S-P5-S0_ListeningPracticeSystem_StartGate_Preflight
```

Data Sources and Ordering Basis:

```text
1. 雲端智慧體開發交握公版 / 重點任務排程
2. docs/ulga/E4S_CORPUS_AND_FOUR_SKILL_SYSTEM_ROADMAP.md
3. docs/ulga/E4S_P0_SOURCE_INVENTORY_CONTRACT.md
4. docs/ulga/E4S_AUTHORITY_MAPPING_MATRIX.md
5. docs/ulga/E4S_LEVEL_SITUATION_TAXONOMY.md
6. docs/ulga/E4S_LEARNING_PATH_BOUNDARY_CONTRACT.md
7. docs/status/RAZ_AW_STATUS_ARTIFACT_CLASSIFICATION.md
```

External Storage Authorization:

```text
GitHub: AUTHORIZED_READ_WRITE
Google Drive: AUTHORIZED_READ_REFERENCE_ONLY
```

Deliverable for This Sub-task:

```text
docs/ulga/E4S_P5_LISTENING_PRACTICE_SYSTEM_START_GATE_PREFLIGHT.md
```

This document records the operator request to formally start Phase 5 and evaluates whether Phase 5 can move from roadmap-only state into active implementation. It does not generate audio, create TTS output, add timing files, create a listening UI, create learner-facing output, update learner state, promote content, or modify runtime code.

---

## 2. Core Execution

### 2.1 Start Gate Decision

Operator request:

```text
Formal start of Phase 5.
```

Phase meaning:

```text
E4S-P5_ListeningPracticeSystem = convert verified sentence / dialogue / passage units into listening practice.
```

Current decision:

```text
PHASE5_START_GATE_CREATED
PHASE5_IMPLEMENTATION_NOT_OPENED
```

Reason:

```text
The existing E4S master roadmap classifies P5 as ROADMAP_ONLY and explicitly defers TTS, audio, timing, and playback work during P0. The later P0 files show P0 foundation reached READY_FOR_CLOSEOUT_READBACK, but the repository still requires an explicit closeout readback and a phase-opening contract before P5 implementation can safely begin.
```

Therefore this sub-task is limited to:

```text
1. Record the Phase 5 launch request.
2. Evaluate Phase 5 implementation gates.
3. Define the next shortest safe step.
4. Block premature audio/TTS/listening UI work.
```

---

### 2.2 Strict Anti-Scope-Creep Boundary

Allowed in this sub-task:

```text
Phase 5 start-gate documentation
Gate evaluation
Dependency check
Distance vector update
Next shortest step definition
```

Forbidden in this sub-task:

```text
TTS generation
audio file generation
audio timing / word timing generation
listening question generation
student-facing listening HTML
runtime code
source payload extraction
content promotion
learner-facing output
learner response event schema
learner state update
adaptive learning
large generated artifacts
```

Runtime impact:

```text
NONE
```

Source promotion impact:

```text
NONE
```

Learner-facing impact:

```text
NONE
```

---

### 2.3 Phase 5 Implementation Prerequisites

Phase 5 implementation must not begin until these prerequisites are either completed or explicitly waived by the operator in a separate task.

| Prerequisite | Required Status | Current Gate Result | Notes |
|---|---:|---:|---|
| P0 closeout readback | completed | BLOCKED | P0-S7 says P0 is ready for closeout, but closeout readback has not been recorded in this file. |
| Source manifest validator | pass | PARTIAL | Builder and validator exist, but this start gate does not execute CI or local tests. |
| Authority lane routing | available | PASS | Authority mapping matrix exists. |
| Level / situation taxonomy | available | PASS | Taxonomy exists and routes listening as deferred. |
| Learning path boundary | available | PASS | Boundary contract exists and blocks learner-state / adaptive use. |
| Verified sentence source | available for P5 | BLOCKED | P5 requires verified sentence/dialogue/passage units; this task does not verify content units. |
| Verified dialogue source | available for P5 if dialogue audio is used | BLOCKED | P4 is still not opened as an implementation phase. |
| Listening source eligibility contract | defined | BLOCKED | No P5-specific source eligibility contract exists yet. |
| Audio generation policy | defined | BLOCKED | No TTS/audio/timing/storage policy exists yet. |
| Listening validator contract | defined | BLOCKED | No P5 listening validator contract exists yet. |
| Learner-facing output permission | explicitly approved | BLOCKED | No learner-facing listening output is allowed by this preflight. |

---

### 2.4 Phase 5 Minimum Safe Opening Contract

The first real Phase 5 task should be a design scan, not implementation.

Recommended first active task:

```text
E4S-P5-S1_ListeningSourceEligibilityAndAudioPolicy_DesignScan
```

It must define:

```text
1. Which source units may become listening candidates.
2. Required source trace for sentence, dialogue, and passage audio.
3. Whether TTS is allowed, and under what conditions.
4. Audio asset storage policy.
5. Voice / accent / speed policy.
6. Timing metadata policy.
7. Listening question type boundary.
8. Validator requirements before learner-facing use.
9. Public distribution restrictions.
10. Explicit no-learner-state / no-adaptive-use boundary.
```

It must not implement:

```text
TTS generation
audio files
playback UI
student-facing listening HTML
large listening dataset generation
learner response scoring
adaptive scheduling
```

---

## 3. Gate & Distance Update

### 3.1 Gate Metrics

| Gate | Result | Evidence |
|---|---:|---|
| GitHub write authorized | PASS | Operator authorization in current request |
| Phase 5 start request recorded | PASS | This file |
| Phase 5 mapped to correct E4S phase | PASS | E4S-P5_ListeningPracticeSystem |
| Existing roadmap boundary respected | PASS | P5 implementation not opened |
| TTS/audio generation avoided | PASS | Documentation only |
| Runtime modification avoided | PASS | No runtime files changed |
| Source extraction avoided | PASS | No source payload touched |
| Content promotion avoided | PASS | No authority promotion |
| Learner-facing output avoided | PASS | No listening UI/output created |
| Phase 5 implementation gate | BLOCKED | Missing P5 source eligibility/audio policy/validator contract |

---

### 3.2 Distance Vector

Current Epic:

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

Requested Phase:

```text
E4S-P5_ListeningPracticeSystem
```

Current Sub-task:

```text
E4S-P5-S0_ListeningPracticeSystem_StartGate_Preflight
```

Sub-task Status:

```text
E4S-P5-S0_ListeningPracticeSystem_StartGate_Preflight -> COMPLETED_WITH_BLOCKING_GATES
```

Phase 5 implementation state:

```text
E4S-P5_ListeningPracticeSystem -> NOT_OPENED_FOR_IMPLEMENTATION
```

Minimum distance to safe P5 implementation opening:

```text
D_P5_OPEN = 2 required gates left
```

Required gates:

```text
1. E4S-P0-CLOSEOUT_SourceAuthorityFoundation_ReadbackQA
2. E4S-P5-S1_ListeningSourceEligibilityAndAudioPolicy_DesignScan
```

Implementation remains blocked until the above gates pass or the operator explicitly approves a scoped waiver in a separate handoff.

---

## 4. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P0-CLOSEOUT_SourceAuthorityFoundation_ReadbackQA
```

Only next allowed action:

```text
Perform a P0 closeout readback that verifies all eight P0 deliverables exist, summarizes PASS / WARNING / DEFERRED state, confirms D_P0 = 0, and then explicitly decides whether Phase 5 may proceed to E4S-P5-S1_ListeningSourceEligibilityAndAudioPolicy_DesignScan.
```

Stop condition:

```text
Stop here. Do not generate audio, TTS, timing, playback, listening questions, or listening UI from this start gate.
```

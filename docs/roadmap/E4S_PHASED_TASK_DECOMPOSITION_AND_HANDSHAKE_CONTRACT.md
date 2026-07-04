# E4S Phased Task Decomposition and Handshake Contract

## 1. Purpose

This document is the task-control contract for the E4S long-running workstream.

It decomposes the project into:

```text
Root Big Task -> Phase Big Tasks -> Middle Tasks -> Small Tasks -> Handoff Checks
```

Every future task handoff must check this file before continuing. A task is not allowed to expand beyond this contract unless the operator explicitly approves a documentation patch to this file.

---

## 2. Source of Truth Order

Every task must read and reconcile these sources in order:

```text
1. docs/roadmap/E4S_PHASED_TASK_DECOMPOSITION_AND_HANDSHAKE_CONTRACT.md
2. docs/ulga/E4S_P0_SOURCE_AUTHORITY_FOUNDATION_CLOSEOUT_READBACK_QA.md
3. docs/ulga/E4S_CORPUS_AND_FOUR_SKILL_SYSTEM_ROADMAP.md
4. phase-specific contract or design document for the current phase
5. source manifest / validator / matrix documents only when relevant to the task
```

If these sources disagree, the task must stop and produce a documentation reconciliation task instead of implementing new features.

---

## 3. Current Baseline

Current completed foundation:

```text
E4S-P0_SourceAuthorityAndCorpusRoadmap -> CLOSED_AS_SOURCE_AUTHORITY_FOUNDATION
D_P0 = 0 sub-tasks left
```

Current next phase state:

```text
E4S-P1_ReadingV1SourceGroundedPractice -> NOT_STARTED_BLOCKED_UNTIL_OPERATOR_APPROVAL
```

P0 closeout confirmed that P0 does not authorize:

```text
Reading V1 question generation
student-facing Reading HTML
worksheet generation
listening audio generation
speaking prompt generation
writing practice generation
assessment item generation
learner state creation
learner placement
mastery scoring
adaptive recommendation
spaced review scheduling
source/content authority promotion
large generated JSON artifacts
```

These capabilities are not separate root projects. They belong to the phased E4S root task and must be activated only through their owning phase and gates.

---

## 4. Root Big Task

Root Task ID:

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

Root Objective:

```text
Build a source-grounded, validator-gated English four-skill practice system that can gradually produce Reading, Assessment, Writing, Dialogue/Speaking, and Listening practice, then later connect validated learner response events and diagnostic signals to learner-state and adaptive learning-path integration.
```

Plain-language objective:

```text
Start from trusted source records.
Create validated practice candidates.
Only after validation, expose learner-facing practice.
Only after learner-event and diagnostic gates, create learner state and adaptive path.
```

Non-goal:

```text
Do not build all skills, UI, learner state, and adaptive path in one task.
```

---

## 5. Phase Big Tasks

| Phase | Big Task ID | Big Task Objective | Status |
|---|---|---|---|
| P0 | `E4S-P0_SourceAuthorityAndCorpusRoadmap` | Establish source authority, manifest, validator, lane mapping, taxonomy, learning-path boundary, status artifact classification | `CLOSED_AS_SOURCE_AUTHORITY_FOUNDATION` |
| P1 | `E4S-P1_ReadingV1SourceGroundedPractice` | Build first source-grounded Reading practice candidate pipeline | `NEXT_ALLOWED_WITH_OPERATOR_APPROVAL` |
| P2 | `E4S-P2_AssessmentPatternExpansion` | Build assessment-pattern and item-generation foundation after Reading/source gates | `DEFERRED` |
| P3 | `E4S-P3_WritingPracticeSystem` | Build writing practice generation from reviewed templates and source-grounded constraints | `DEFERRED` |
| P4 | `E4S-P4_DialogueSpeakingPromptSystem` | Build dialogue/speaking prompt candidates from reviewed functional/dialogue sources | `DEFERRED` |
| P5 | `E4S-P5_ListeningPracticeSystem` | Build listening candidate pipeline and audio policy after text/content gates | `DEFERRED` |
| P6 | `E4S-P6_ErrorTaggingAndWeakPointDiagnosis` | Build error-tag signal and weak-point diagnosis candidates without learner-state mutation | `DEFERRED` |
| P7 | `E4S-P7_AdaptiveLearningPathIntegration` | Build learner state, mastery, dependency, review, and adaptive recommendation after required gates | `BLOCKED_UNTIL_P1_P6_SIGNALS_EXIST` |
| P8 | `E4S-P8_FourSkillBridgeAndProductLayer` | Bridge validated skills into product-facing interfaces and exports | `DEFERRED` |

---

## 6. Capability Ownership Matrix

| Capability | Owning Phase | Activation Rule | Not Allowed Before |
|---|---|---|---|
| Reading V1 question generation | P1 | after P1 schema, source routing, and validator gates | P1-S0/S1 scope gates |
| student-facing Reading HTML | P1 late or P8 | after validated Reading packages and explicit UI/export task | Reading package validator |
| worksheet generation | P1/P2/P3 or P8 | only as export format after validated content | relevant skill validator |
| assessment item generation | P2 | after assessment pattern schema and validator | P2 start approval |
| writing practice generation | P3 | after writing template schema and validator | P3 start approval |
| speaking prompt generation | P4 | after dialogue/speaking source review and prompt validator | P4 start approval |
| listening audio generation | P5 | after listening text/audio policy and validator | P5 start approval |
| learner state creation | P7 | after event schema, privacy policy, diagnostic signals, and P7 gates | P7 start approval |
| learner placement | P7 | after placement policy and learner-state schema | P7 gates |
| mastery scoring | P7 | after learner response event schema and scoring policy | P7 gates |
| adaptive recommendation | P7 | after mastery, dependency, review, and scheduler policies | P7 gates |
| spaced review scheduling | P7 | after scheduler policy and learner-state persistence policy | P7 gates |
| source/content authority promotion | independent promotion gate | only through explicit promotion review task | all non-promotion tasks |
| large generated JSON artifacts | phase-specific expansion gate | only after pilot, QA, validator, and operator approval | initial pilot tasks |

---

## 7. P1 Reading V1 Middle and Small Tasks

P1 Big Task:

```text
E4S-P1_ReadingV1SourceGroundedPractice
```

P1 Objective:

```text
Create a source-grounded Reading V1 candidate pipeline that can select approved reading sources, define reading item schemas, generate a small pilot candidate set, validate the pilot, and prepare for later learner-facing Reading output without creating learner state or adaptive behavior.
```

### P1-M0 Activation and Scope Gate

Middle Task ID:

```text
E4S-P1-M0_ActivationAndScopeGate
```

Small tasks:

| Order | Small Task ID | Purpose | Deliverable | Allowed Output |
|---:|---|---|---|---|
| 0 | `E4S-P1-S0_ReadingV1SourceGroundedPractice_ActivationAndScopeGate` | Confirm P0 closeout, allowed source lanes, blocked outputs, and P1 first milestone | `docs/ulga/E4S_P1_READING_V1_ACTIVATION_SCOPE_GATE.md` | documentation only |
| 1 | `E4S-P1-S1_ReadingV1_SourceEligibilityAndInputContract_DesignScan` | Define which manifest records may support Reading V1 and how RAZ reading corpus / RAZ wordlist may be used | `docs/ulga/E4S_P1_READING_V1_SOURCE_ELIGIBILITY_CONTRACT.md` | documentation only |
| 2 | `E4S-P1-S2_ReadingV1_TaskQueueAndDistanceVector_DesignScan` | Define P1 task queue, distance vector, and handoff sequence | `docs/ulga/E4S_P1_READING_V1_TASK_QUEUE.md` | documentation only |

Exit gate:

```text
P1-M0 exits only when Reading V1 source eligibility, first safe milestone, blocked outputs, and next task are explicit.
```

### P1-M1 Reading Schema and Candidate Contract

Middle Task ID:

```text
E4S-P1-M1_ReadingSchemaAndCandidateContract
```

Small tasks:

| Order | Small Task ID | Purpose | Deliverable | Allowed Output |
|---:|---|---|---|---|
| 0 | `E4S-P1-S3_ReadingV1_ItemSchema_DesignScan` | Define Reading V1 item schema: passage ref, question, answer, evidence, level/situation metadata | `docs/ulga/E4S_P1_READING_V1_ITEM_SCHEMA.md` | documentation only |
| 1 | `E4S-P1-S4_ReadingV1_PilotCandidateSchema_Implementation` | Create small machine-readable schema or template for pilot candidates | `ulga/schemas/reading_v1_candidate.schema.json`; tests if needed | schema only |
| 2 | `E4S-P1-S5_ReadingV1_ValidatorContract_DesignScan` | Define validation rules before generating any pilot | `docs/ulga/E4S_P1_READING_V1_VALIDATOR_CONTRACT.md` | documentation only |

Exit gate:

```text
P1-M1 exits only when Reading V1 candidate shape and validation rules exist.
```

### P1-M2 Query and Source Routing

Middle Task ID:

```text
E4S-P1-M2_QueryAndSourceRouting
```

Small tasks:

| Order | Small Task ID | Purpose | Deliverable | Allowed Output |
|---:|---|---|---|---|
| 0 | `E4S-P1-S6_ReadingV1_SourceQueryLayer_DesignScan` | Define query logic over approved Reading candidates without learner-facing output | `docs/ulga/E4S_P1_READING_V1_SOURCE_QUERY_LAYER.md` | documentation only |
| 1 | `E4S-P1-S7_ReadingV1_SourceQueryLayer_Implementation` | Implement deterministic source query helper for metadata/candidate selection | `tools/query_e4s_reading_v1_sources.py`; tests | metadata query only |
| 2 | `E4S-P1-S8_ReadingV1_SourceQueryLayer_ReadbackQA` | Verify query helper does not promote sources or extract disallowed payloads | `docs/ulga/E4S_P1_READING_V1_SOURCE_QUERY_READBACK_QA.md` | QA readback only |

Exit gate:

```text
P1-M2 exits only when source selection is deterministic, traceable, and blocked from learner-facing output.
```

### P1-M3 Small Pilot Candidate Generation

Middle Task ID:

```text
E4S-P1-M3_SmallPilotCandidateGeneration
```

Small tasks:

| Order | Small Task ID | Purpose | Deliverable | Allowed Output |
|---:|---|---|---|---|
| 0 | `E4S-P1-S9_ReadingV1_PilotGenerationPolicy_DesignScan` | Define strict pilot size, source trace, allowed question types, and blocked outputs | `docs/ulga/E4S_P1_READING_V1_PILOT_GENERATION_POLICY.md` | documentation only |
| 1 | `E4S-P1-S10_ReadingV1_PilotCandidateBuilder_Implementation` | Build tiny pilot candidate JSON from approved source traces | `tools/build_reading_v1_pilot_candidates.py`; `ulga/reports/reading_v1_pilot_summary.json`; tests | small pilot only |
| 2 | `E4S-P1-S11_ReadingV1_PilotCandidateReadbackQA` | Read back pilot candidate safety, source trace, and blocked learner-facing use | `docs/ulga/E4S_P1_READING_V1_PILOT_READBACK_QA.md` | QA readback only |

Exit gate:

```text
P1-M3 exits only when a small pilot exists, passes schema/trace checks, and is not student-facing.
```

### P1-M4 Reading Validator and QA

Middle Task ID:

```text
E4S-P1-M4_ReadingValidatorAndQA
```

Small tasks:

| Order | Small Task ID | Purpose | Deliverable | Allowed Output |
|---:|---|---|---|---|
| 0 | `E4S-P1-S12_ReadingV1_CandidateValidator_Implementation` | Implement validator for Reading V1 pilot candidates | `tools/validate_reading_v1_candidates.py`; tests | validator only |
| 1 | `E4S-P1-S13_ReadingV1_CandidateValidationReport_ReadbackQA` | Verify validator report and blocked output state | `docs/ulga/E4S_P1_READING_V1_VALIDATION_READBACK_QA.md` | QA readback only |
| 2 | `E4S-P1-S14_ReadingV1_ManualReviewQueue_DesignScan` | Define manual review queue shape without creating learner-facing practice | `docs/ulga/E4S_P1_READING_V1_MANUAL_REVIEW_QUEUE.md` | documentation only |

Exit gate:

```text
P1-M4 exits only when candidate validation exists and manual review expectations are defined.
```

### P1-M5 Learner-Facing Output Decision Gate

Middle Task ID:

```text
E4S-P1-M5_LearnerFacingOutputDecisionGate
```

Small tasks:

| Order | Small Task ID | Purpose | Deliverable | Allowed Output |
|---:|---|---|---|---|
| 0 | `E4S-P1-S15_ReadingV1_LearnerFacingOutputGate_DesignScan` | Decide whether Reading HTML / worksheet export is allowed yet | `docs/ulga/E4S_P1_READING_V1_LEARNER_FACING_OUTPUT_GATE.md` | documentation only |
| 1 | `E4S-P1-S16_ReadingV1_HTMLExport_Implementation` | Only if S15 approves: create non-adaptive student-facing Reading HTML from validated package | `site/` or approved export path | learner-facing HTML only after gate |
| 2 | `E4S-P1-S17_ReadingV1_WorksheetExport_Implementation` | Only if S15 approves: worksheet export from validated package | approved export path | worksheet only after gate |

Exit gate:

```text
P1-M5 exits only when learner-facing output is either explicitly approved or explicitly remains blocked.
```

### P1-M6 Reading V1 Closeout

Middle Task ID:

```text
E4S-P1-M6_ReadingV1Closeout
```

Small tasks:

| Order | Small Task ID | Purpose | Deliverable | Allowed Output |
|---:|---|---|---|---|
| 0 | `E4S-P1-S18_ReadingV1_EndToEndReadbackQA` | Verify all P1 deliverables, gates, warnings, deferred items, and next phase handoff | `docs/ulga/E4S_P1_READING_V1_CLOSEOUT_READBACK_QA.md` | closeout readback only |

Exit gate:

```text
P1 closes only when source-grounded Reading V1 is validated and all blocked capabilities remain blocked unless explicitly approved.
```

---

## 8. P2-P8 Middle Task Skeletons

These phases are intentionally skeletal until the operator explicitly starts them. They must not be expanded into implementation tasks before their activation gates.

### P2 Assessment Pattern Expansion

| Middle Task | Purpose | First Small Task |
|---|---|---|
| `E4S-P2-M0_ActivationAndScopeGate` | Confirm assessment source authority and P1/P0 dependencies | `E4S-P2-S0_AssessmentPatternExpansion_ActivationAndScopeGate` |
| `E4S-P2-M1_AssessmentPatternSchema` | Define assessment pattern/item schema | deferred |
| `E4S-P2-M2_AssessmentPilotGeneration` | Build small validated assessment pilot | deferred |
| `E4S-P2-M3_AssessmentValidatorQA` | Validate assessment items | deferred |
| `E4S-P2-M4_AssessmentCloseout` | Closeout P2 | deferred |

### P3 Writing Practice System

| Middle Task | Purpose | First Small Task |
|---|---|---|
| `E4S-P3-M0_ActivationAndScopeGate` | Confirm writing template source authority and blocked outputs | `E4S-P3-S0_WritingPracticeSystem_ActivationAndScopeGate` |
| `E4S-P3-M1_WritingTemplateSchema` | Define writing task/template schema | deferred |
| `E4S-P3-M2_WritingPilotGeneration` | Build small writing pilot | deferred |
| `E4S-P3-M3_WritingValidatorQA` | Validate writing practice candidates | deferred |
| `E4S-P3-M4_WritingCloseout` | Closeout P3 | deferred |

### P4 Dialogue / Speaking Prompt System

| Middle Task | Purpose | First Small Task |
|---|---|---|
| `E4S-P4-M0_ActivationAndScopeGate` | Confirm dialogue/speaking source boundaries | `E4S-P4-S0_DialogueSpeakingPromptSystem_ActivationAndScopeGate` |
| `E4S-P4-M1_DialoguePromptSchema` | Define prompt/dialogue schema | deferred |
| `E4S-P4-M2_SpeakingPromptPilot` | Build small speaking prompt pilot | deferred |
| `E4S-P4-M3_DialogueValidatorQA` | Validate prompts | deferred |
| `E4S-P4-M4_DialogueSpeakingCloseout` | Closeout P4 | deferred |

### P5 Listening Practice System

| Middle Task | Purpose | First Small Task |
|---|---|---|
| `E4S-P5-M0_ActivationAndScopeGate` | Confirm listening source and audio policy boundaries | `E4S-P5-S0_ListeningPracticeSystem_ActivationAndScopeGate` |
| `E4S-P5-M1_ListeningTextSchema` | Define listening text/item schema | deferred |
| `E4S-P5-M2_AudioPolicyAndPilot` | Define audio policy and small pilot only after approval | deferred |
| `E4S-P5-M3_ListeningValidatorQA` | Validate listening candidates/audio metadata | deferred |
| `E4S-P5-M4_ListeningCloseout` | Closeout P5 | deferred |

### P6 Error Tagging and Weak Point Diagnosis

| Middle Task | Purpose | First Small Task |
|---|---|---|
| `E4S-P6-M0_ActivationAndScopeGate` | Confirm error-tag source and learner-state boundaries | `E4S-P6-S0_ErrorTaggingWeakPointDiagnosis_ActivationAndScopeGate` |
| `E4S-P6-M1_ErrorTagSchema` | Define error tag signal schema | deferred |
| `E4S-P6-M2_DiagnosticSignalPilot` | Build signal-only pilot, no learner state mutation | deferred |
| `E4S-P6-M3_ErrorTagValidatorQA` | Validate error tags/signals | deferred |
| `E4S-P6-M4_ErrorTaggingCloseout` | Closeout P6 | deferred |

### P7 Adaptive Learning Path Integration

| Middle Task | Purpose | First Small Task |
|---|---|---|
| `E4S-P7-M0_ActivationAndScopeGate` | Confirm P1-P6 signals, privacy, learner-state prerequisites | `E4S-P7-S0_AdaptiveLearningPathIntegration_ActivationAndScopeGate` |
| `E4S-P7-M1_LearnerStateSchema` | Define learner state schema | deferred |
| `E4S-P7-M2_ResponseEventAndMasteryPolicy` | Define response event and mastery policy | deferred |
| `E4S-P7-M3_DependencyAndSchedulerPolicy` | Define dependency and scheduler policy | deferred |
| `E4S-P7-M4_AdaptivePilot` | Build strictly bounded adaptive pilot | deferred |
| `E4S-P7-M5_AdaptiveCloseout` | Closeout P7 | deferred |

### P8 Four-Skill Bridge and Product Layer

| Middle Task | Purpose | First Small Task |
|---|---|---|
| `E4S-P8-M0_ActivationAndScopeGate` | Confirm which validated skill outputs can be productized | `E4S-P8-S0_FourSkillBridgeProductLayer_ActivationAndScopeGate` |
| `E4S-P8-M1_ProductExportPolicy` | Define export/UI constraints | deferred |
| `E4S-P8-M2_MultiSkillBridge` | Bridge validated skills only | deferred |
| `E4S-P8-M3_ProductQA` | Validate final product-facing behavior | deferred |
| `E4S-P8-M4_ProductCloseout` | Closeout P8 | deferred |

---

## 9. Mandatory Handoff Protocol

Every future task must end with a handoff block that includes all of the following:

```text
1. GOVERNANCE_MD_CHECK = PASS / FAIL
2. CURRENT_TASK_IN_CONTRACT = PASS / FAIL
3. CURRENT_TASK_SCOPE_LOCK = PASS / FAIL
4. FORBIDDEN_OUTPUT_CHECK = PASS / FAIL
5. FILES_CREATED_OR_MODIFIED = list
6. ACCEPTANCE_GATES = PASS / WARNING / FAIL
7. DISTANCE_VECTOR_UPDATE = current phase remaining tasks
8. NEXT_TASK_IN_CONTRACT = PASS / FAIL
9. NEXT_TASK_ID = exact next task
10. DRIFT_RISK = none / low / medium / high
```

If `CURRENT_TASK_IN_CONTRACT = FAIL`, the task must not proceed. It must produce a proposed governance patch instead.

If `NEXT_TASK_IN_CONTRACT = FAIL`, the next task must not be started. The next task must be converted into a documentation patch or operator decision.

---

## 10. Per-Task Preflight Checklist

Before any new task starts, the assistant or agent must verify:

```text
- Read this governance MD.
- Read the current phase contract or closeout document.
- Confirm the requested task ID appears in this document or in a phase-specific task queue created under this document.
- Confirm the task type: DesignScan / DocumentationPatch / Implementation / QA / Closeout.
- Confirm allowed files.
- Confirm forbidden files.
- Confirm forbidden outputs.
- Confirm whether source promotion, learner state, adaptive scheduling, or learner-facing output is allowed.
- If not explicitly allowed, treat it as forbidden.
```

---

## 11. Drift Control Rules

The project must not drift by doing any of the following:

```text
- Turning a DesignScan into implementation.
- Turning a pilot into large-scale generation.
- Treating source metadata as learner placement.
- Treating status artifacts as learner progress.
- Treating generated candidates as source authority.
- Treating Reading V1 as permission to build all four skills.
- Starting UI/export before validated content package gates.
- Starting P7 adaptive work before learner-event, error-tag, dependency, privacy, and scheduler prerequisites exist.
```

Any drift risk must be reported as:

```text
DRIFT_RISK = low / medium / high
DRIFT_REASON = <one sentence>
REQUIRED_ACTION = continue / stop / documentation patch / operator approval
```

---

## 12. Status Vocabulary

Allowed task statuses:

```text
NOT_STARTED
ACTIVE
COMPLETED
PASS_WITH_WARNINGS
PASS_WITH_DEFERRED_FUTURE_WORK
BLOCKED
DEFERRED
CLOSED
```

Allowed phase statuses:

```text
ROADMAP_ONLY
NEXT_ALLOWED_WITH_OPERATOR_APPROVAL
ACTIVE
CLOSED_AS_FOUNDATION
CLOSED_AS_SOURCE_AUTHORITY_FOUNDATION
BLOCKED_UNTIL_DEPENDENCIES_EXIST
DEFERRED
```

---

## 13. Current Next Task

Current next allowed task:

```text
E4S-P1-S0_ReadingV1SourceGroundedPractice_ActivationAndScopeGate
```

Current next task type:

```text
DesignScan / ActivationGate
```

Allowed output:

```text
docs/ulga/E4S_P1_READING_V1_ACTIVATION_SCOPE_GATE.md
```

Blocked outputs in this next task:

```text
Reading V1 question generation
student-facing Reading HTML
worksheet generation
learner state creation
learner placement
mastery scoring
adaptive recommendation
spaced review scheduling
source/content authority promotion
large generated JSON artifacts
```

Stop condition:

```text
Stop after P1-S0 verifies P0 closeout, confirms Reading V1 scope, defines allowed source lanes, records blocked outputs, and proposes P1-S1.
```

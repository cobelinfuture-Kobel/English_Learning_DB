# E4S P1 Reading V1 Task Queue and Distance Vector Design Scan

## 1. Current State

Epic ID:

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

Current Phase:

```text
E4S-P1_ReadingV1SourceGroundedPractice
```

Current Middle Task:

```text
E4S-P1-M0_ActivationAndScopeGate
```

Current Small Task:

```text
E4S-P1-S2_ReadingV1_TaskQueueAndDistanceVector_DesignScan
```

Deliverable:

```text
docs/ulga/E4S_P1_READING_V1_TASK_QUEUE.md
```

This task defines the P1 Reading V1 task queue, distance vector, next-task sequence, phase gates, and mandatory handoff checks before P1 can move into schema design. It does not implement schemas, query helpers, validators, pilot generation, learner-facing output, learner state, adaptive scheduling, source payload extraction, or source/content promotion.

---

## 2. Mandatory Governance Readback

Governance source:

```text
docs/roadmap/E4S_PHASED_TASK_DECOMPOSITION_AND_HANDSHAKE_CONTRACT.md
```

Governance result:

```text
GOVERNANCE_MD_CHECK = PASS
CURRENT_TASK_IN_CONTRACT = PASS
```

Predecessor tasks:

```text
E4S-P1-S0_ReadingV1SourceGroundedPractice_ActivationAndScopeGate -> COMPLETED
E4S-P1-S1_ReadingV1_SourceEligibilityAndInputContract_DesignScan -> COMPLETED
```

P1-S2 is a DesignScan / TaskQueue task only.

---

## 3. Task Boundary

Task type:

```text
DesignScan / TaskQueueAndDistanceVector
```

Allowed file:

```text
docs/ulga/E4S_P1_READING_V1_TASK_QUEUE.md
```

Forbidden files and paths:

```text
tools/query_e4s_reading_v1_sources.py
tools/build_reading_v1_pilot_candidates.py
tools/validate_reading_v1_candidates.py
ulga/schemas/reading_v1_candidate.schema.json
ulga/reports/reading_v1_pilot_summary.json
site HTML
student-facing Reading practice HTML
worksheet exports
large generated artifacts
source corpus payloads
learner event files
learner state files
learner profile files
adaptive scheduling files
dependency graph artifacts
promotion artifacts
```

Generated artifact policy:

```text
No generated Reading questions, Reading candidate JSON, schemas, validators, query helpers, learner-facing files, learner events, or large JSON artifacts are allowed in P1-S2.
```

Runtime impact:

```text
NONE
```

Promotion impact:

```text
NONE. P1-S2 performs no source/content authority promotion.
```

---

## 4. P1 Phase Objective

P1 objective:

```text
Create a source-grounded Reading V1 candidate pipeline that can select approved reading sources, define reading item schemas, generate a small pilot candidate set, validate the pilot, and prepare for later learner-facing Reading output without creating learner state or adaptive behavior.
```

P1 success requires:

```text
1. P1-M0 activation / source eligibility gates close.
2. P1-M1 item schema and validator contract exist.
3. P1-M2 source query / routing exists and is readback-verified.
4. P1-M3 small pilot candidate generation is strictly bounded and validated.
5. P1-M4 candidate validator and manual review queue exist.
6. P1-M5 decides whether learner-facing output remains blocked or becomes explicitly approved.
7. P1-M6 closes Reading V1 with readback QA.
```

---

## 5. P1 Task Queue

### P1-M0 Activation and Scope Gate

| Order | Small Task ID | Type | Deliverable | Status | May Implement? |
|---:|---|---|---|---|---:|
| 0 | `E4S-P1-S0_ReadingV1SourceGroundedPractice_ActivationAndScopeGate` | DesignScan / ActivationGate | `docs/ulga/E4S_P1_READING_V1_ACTIVATION_SCOPE_GATE.md` | `COMPLETED` | no |
| 1 | `E4S-P1-S1_ReadingV1_SourceEligibilityAndInputContract_DesignScan` | DesignScan / SourceEligibilityContract | `docs/ulga/E4S_P1_READING_V1_SOURCE_ELIGIBILITY_CONTRACT.md` | `COMPLETED` | no |
| 2 | `E4S-P1-S2_ReadingV1_TaskQueueAndDistanceVector_DesignScan` | DesignScan / TaskQueue | `docs/ulga/E4S_P1_READING_V1_TASK_QUEUE.md` | `COMPLETED` | no |

P1-M0 exit gate:

```text
P1-M0 exits only when activation, source eligibility, blocked outputs, task queue, and next safe milestone are explicit.
```

P1-M0 close result after this task:

```text
E4S-P1-M0_ActivationAndScopeGate -> COMPLETED
```

### P1-M1 Reading Schema and Candidate Contract

| Order | Small Task ID | Type | Deliverable | Status | May Implement? |
|---:|---|---|---|---|---:|
| 3 | `E4S-P1-S3_ReadingV1_ItemSchema_DesignScan` | DesignScan / SchemaDesign | `docs/ulga/E4S_P1_READING_V1_ITEM_SCHEMA.md` | `NEXT` | no |
| 4 | `E4S-P1-S4_ReadingV1_PilotCandidateSchema_Implementation` | Implementation / SchemaOnly | `ulga/schemas/reading_v1_candidate.schema.json`; tests if needed | `PLANNED` | yes, schema only |
| 5 | `E4S-P1-S5_ReadingV1_ValidatorContract_DesignScan` | DesignScan / ValidatorContract | `docs/ulga/E4S_P1_READING_V1_VALIDATOR_CONTRACT.md` | `PLANNED` | no |

P1-M1 exit gate:

```text
P1-M1 exits only when Reading V1 candidate shape and validation rules exist.
```

### P1-M2 Query and Source Routing

| Order | Small Task ID | Type | Deliverable | Status | May Implement? |
|---:|---|---|---|---|---:|
| 6 | `E4S-P1-S6_ReadingV1_SourceQueryLayer_DesignScan` | DesignScan / QueryDesign | `docs/ulga/E4S_P1_READING_V1_SOURCE_QUERY_LAYER.md` | `PLANNED` | no |
| 7 | `E4S-P1-S7_ReadingV1_SourceQueryLayer_Implementation` | Implementation / MetadataQueryOnly | `tools/query_e4s_reading_v1_sources.py`; tests | `PLANNED` | yes, metadata query only |
| 8 | `E4S-P1-S8_ReadingV1_SourceQueryLayer_ReadbackQA` | QA / Readback | `docs/ulga/E4S_P1_READING_V1_SOURCE_QUERY_READBACK_QA.md` | `PLANNED` | no |

P1-M2 exit gate:

```text
P1-M2 exits only when source selection is deterministic, traceable, and blocked from learner-facing output.
```

### P1-M3 Small Pilot Candidate Generation

| Order | Small Task ID | Type | Deliverable | Status | May Implement? |
|---:|---|---|---|---|---:|
| 9 | `E4S-P1-S9_ReadingV1_PilotGenerationPolicy_DesignScan` | DesignScan / PilotPolicy | `docs/ulga/E4S_P1_READING_V1_PILOT_GENERATION_POLICY.md` | `PLANNED` | no |
| 10 | `E4S-P1-S10_ReadingV1_PilotCandidateBuilder_Implementation` | Implementation / SmallPilotOnly | `tools/build_reading_v1_pilot_candidates.py`; `ulga/reports/reading_v1_pilot_summary.json`; tests | `PLANNED` | yes, tiny pilot only |
| 11 | `E4S-P1-S11_ReadingV1_PilotCandidateReadbackQA` | QA / Readback | `docs/ulga/E4S_P1_READING_V1_PILOT_READBACK_QA.md` | `PLANNED` | no |

P1-M3 exit gate:

```text
P1-M3 exits only when a small pilot exists, passes schema/trace checks, and is not student-facing.
```

### P1-M4 Reading Validator and QA

| Order | Small Task ID | Type | Deliverable | Status | May Implement? |
|---:|---|---|---|---|---:|
| 12 | `E4S-P1-S12_ReadingV1_CandidateValidator_Implementation` | Implementation / ValidatorOnly | `tools/validate_reading_v1_candidates.py`; tests | `PLANNED` | yes, validator only |
| 13 | `E4S-P1-S13_ReadingV1_CandidateValidationReport_ReadbackQA` | QA / Readback | `docs/ulga/E4S_P1_READING_V1_VALIDATION_READBACK_QA.md` | `PLANNED` | no |
| 14 | `E4S-P1-S14_ReadingV1_ManualReviewQueue_DesignScan` | DesignScan / ReviewQueue | `docs/ulga/E4S_P1_READING_V1_MANUAL_REVIEW_QUEUE.md` | `PLANNED` | no |

P1-M4 exit gate:

```text
P1-M4 exits only when candidate validation exists and manual review expectations are defined.
```

### P1-M5 Learner-Facing Output Decision Gate

| Order | Small Task ID | Type | Deliverable | Status | May Implement? |
|---:|---|---|---|---|---:|
| 15 | `E4S-P1-S15_ReadingV1_LearnerFacingOutputGate_DesignScan` | DesignScan / OutputGate | `docs/ulga/E4S_P1_READING_V1_LEARNER_FACING_OUTPUT_GATE.md` | `PLANNED` | no |
| 16 | `E4S-P1-S16_ReadingV1_HTMLExport_Implementation` | Implementation / HTMLExportOnly | `site/` or approved export path | `BLOCKED_UNTIL_S15_APPROVES` | yes, only if S15 approves |
| 17 | `E4S-P1-S17_ReadingV1_WorksheetExport_Implementation` | Implementation / WorksheetExportOnly | approved export path | `BLOCKED_UNTIL_S15_APPROVES` | yes, only if S15 approves |

P1-M5 exit gate:

```text
P1-M5 exits only when learner-facing output is either explicitly approved or explicitly remains blocked.
```

### P1-M6 Reading V1 Closeout

| Order | Small Task ID | Type | Deliverable | Status | May Implement? |
|---:|---|---|---|---|---:|
| 18 | `E4S-P1-S18_ReadingV1_EndToEndReadbackQA` | Closeout / ReadbackQA | `docs/ulga/E4S_P1_READING_V1_CLOSEOUT_READBACK_QA.md` | `PLANNED` | no |

P1-M6 close gate:

```text
P1 closes only when source-grounded Reading V1 is validated and all blocked capabilities remain blocked unless explicitly approved.
```

---

## 6. Dependency Rules

P1 task order is linear unless the operator explicitly approves a governance patch.

Dependency rules:

```text
P1-S3 cannot start until P1-M0 is complete.
P1-S4 cannot start until P1-S3 item schema design is complete.
P1-S5 cannot start until P1-S3 is complete and must be reconciled with S4 schema if S4 already exists.
P1-S6 cannot start until source eligibility and schema boundaries are known.
P1-S7 cannot start until P1-S6 query design is complete.
P1-S8 cannot start until P1-S7 implementation exists.
P1-S9 cannot start until schema, validator contract, and query design boundaries exist.
P1-S10 cannot start until P1-S9 explicitly allows a tiny pilot.
P1-S11 cannot start until P1-S10 pilot artifact exists.
P1-S12 cannot start until pilot candidate schema and pilot artifact expectations exist.
P1-S15 cannot start until validation and manual review boundaries exist.
P1-S16 and P1-S17 cannot start unless P1-S15 explicitly approves learner-facing output.
P1-S18 cannot start until all prior P1 gates are complete or explicitly deferred by operator-approved closeout.
```

---

## 7. Phase-Level Blocked Outputs

The following remain blocked across P1 unless a later task explicitly permits them:

```text
large-scale Reading question generation
student-facing Reading HTML before S15 approval
worksheet export before S15 approval
source payload redistribution
public distribution of restricted sources
learner event creation
learner state creation
learner placement
mastery scoring
adaptive recommendation
spaced review scheduling
source/content authority promotion
multi-skill expansion into Writing / Listening / Speaking / Assessment
P7 adaptive integration
```

---

## 8. Distance Vector

P0 state:

```text
E4S-P0_SourceAuthorityAndCorpusRoadmap -> CLOSED_AS_SOURCE_AUTHORITY_FOUNDATION
D_P0 = 0
```

P1 state after this task:

```text
E4S-P1_ReadingV1SourceGroundedPractice -> ACTIVE_SCHEMA_GATE_READY
```

Current task status:

```text
E4S-P1-S2_ReadingV1_TaskQueueAndDistanceVector_DesignScan -> COMPLETED
```

P1-M0 state:

```text
E4S-P1-M0_ActivationAndScopeGate -> COMPLETED
D_P1_M0 = 0 small tasks left
```

P1 remaining small-task distance:

```text
D_P1 = 16 small tasks left
```

Next middle task:

```text
E4S-P1-M1_ReadingSchemaAndCandidateContract
```

Next small task:

```text
E4S-P1-S3_ReadingV1_ItemSchema_DesignScan
```

---

## 9. Acceptance Gates for P1-S2

| Gate | Result | Evidence |
|---|---:|---|
| Governance MD checked | PASS | Section 2 |
| Current task appears in governance contract | PASS | Section 2 |
| P1-S0 completion checked | PASS | Section 2 |
| P1-S1 completion checked | PASS | Section 2 |
| Allowed file scope locked | PASS | Section 3 |
| Forbidden files listed | PASS | Section 3 |
| P1 task queue defined | PASS | Section 5 |
| P1-M0 close state defined | PASS | Section 5 |
| P1-M1 through P1-M6 task sequence defined | PASS | Section 5 |
| Dependency rules defined | PASS | Section 6 |
| Phase-level blocked outputs defined | PASS | Section 7 |
| Distance vector updated | PASS | Section 8 |
| Runtime impact avoided | PASS | Documentation only |
| Schema implementation avoided | PASS | No schema file |
| Query implementation avoided | PASS | No Python query helper |
| Pilot generation avoided | PASS | No candidate JSON |
| Validator implementation avoided | PASS | No validator code |
| Source payload extraction avoided | PASS | No payload copied |
| Learner state avoided | PASS | No learner files |
| Student-facing output avoided | PASS | No HTML / worksheet output |
| Promotion avoided | PASS | Design only |

---

## 10. Warning Register

```text
warning_id: E4S-P1-S2-WARN-001
severity: medium
classification: TASK_QUEUE_NOT_RUNTIME_QUEUE
message: This task queue is a planning/control artifact, not a runtime scheduler or learner assignment queue.
blocks_current_task: no
```

```text
warning_id: E4S-P1-S2-WARN-002
severity: medium
classification: NO_TEST_RUN
message: This DesignScan is documentation-only. No local Python tests or GitHub Actions CI were run.
blocks_current_task: no
```

---

## 11. Deferred Issues Register

```text
issue_id: E4S-P1-S2-DEFER-001
severity: high
affected_file_or_artifact: Reading V1 item schema
classification: FUTURE_WORK
why_deferred: P1-S2 defines task queue only. P1-S3 must define the Reading V1 item schema.
recommended_future_task: E4S-P1-S3_ReadingV1_ItemSchema_DesignScan
blocks_current_task: no
```

```text
issue_id: E4S-P1-S2-DEFER-002
severity: high
affected_file_or_artifact: Reading V1 candidate schema implementation
classification: FUTURE_WORK
why_deferred: Machine-readable schema belongs to P1-S4 after item schema design.
recommended_future_task: E4S-P1-S4_ReadingV1_PilotCandidateSchema_Implementation
blocks_current_task: no
```

```text
issue_id: E4S-P1-S2-DEFER-003
severity: high
affected_file_or_artifact: Reading V1 query / pilot / validator implementation
classification: FUTURE_WORK
why_deferred: Implementation tasks are scheduled later and remain blocked until their design gates.
recommended_future_task: follow P1 task queue sequence
blocks_current_task: no
```

---

## 12. Mandatory Handoff Block

```text
GOVERNANCE_MD_CHECK = PASS
CURRENT_TASK_IN_CONTRACT = PASS
CURRENT_TASK_SCOPE_LOCK = PASS
FORBIDDEN_OUTPUT_CHECK = PASS
FILES_CREATED_OR_MODIFIED = docs/ulga/E4S_P1_READING_V1_TASK_QUEUE.md
ACCEPTANCE_GATES = PASS_WITH_WARNINGS
DISTANCE_VECTOR_UPDATE = D_P1_M0 = 0; D_P1 = 16
NEXT_TASK_IN_CONTRACT = PASS
NEXT_TASK_ID = E4S-P1-S3_ReadingV1_ItemSchema_DesignScan
DRIFT_RISK = low
DRIFT_REASON = P1-M0 is now closed, but the next task remains DesignScan only and cannot implement schema yet.
REQUIRED_ACTION = continue with P1-S3 only
```

---

## 13. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P1-S3_ReadingV1_ItemSchema_DesignScan
```

Only next allowed action:

```text
Create docs/ulga/E4S_P1_READING_V1_ITEM_SCHEMA.md to define the Reading V1 item schema, candidate boundaries, source trace fields, question/answer/evidence shape, and blocked outputs before any machine-readable schema is implemented.
```

Stop here until the operator explicitly starts P1-S3.

# E4S P1 Reading V1 Source-Grounded Practice Activation Scope Gate

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
E4S-P1-S0_ReadingV1SourceGroundedPractice_ActivationAndScopeGate
```

Deliverable:

```text
docs/ulga/E4S_P1_READING_V1_ACTIVATION_SCOPE_GATE.md
```

This task activates P1 as a scoped phase, not as implementation. It confirms that P0 source authority foundation is closed, P1 is allowed to start only as a Reading V1 scope gate, and all learner-facing / adaptive / large-generation outputs remain blocked until later gates.

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

Required source-of-truth order for future P1 tasks:

```text
1. docs/roadmap/E4S_PHASED_TASK_DECOMPOSITION_AND_HANDSHAKE_CONTRACT.md
2. docs/ulga/E4S_P0_SOURCE_AUTHORITY_FOUNDATION_CLOSEOUT_READBACK_QA.md
3. docs/ulga/E4S_CORPUS_AND_FOUR_SKILL_SYSTEM_ROADMAP.md
4. docs/ulga/E4S_P1_READING_V1_ACTIVATION_SCOPE_GATE.md
5. phase-specific P1 contract / task queue documents created after this gate
6. source manifest / authority matrix / taxonomy / boundary documents only when relevant
```

If a future P1 task conflicts with this order, it must stop and produce a documentation reconciliation task.

---

## 3. P0 Closeout Dependency

P0 foundation state required before P1:

```text
E4S-P0_SourceAuthorityAndCorpusRoadmap -> CLOSED_AS_SOURCE_AUTHORITY_FOUNDATION
D_P0 = 0 sub-tasks left
```

P1 pre-start state:

```text
E4S-P1_ReadingV1SourceGroundedPractice -> NOT_STARTED_BLOCKED_UNTIL_OPERATOR_APPROVAL
```

Operator instruction received:

```text
啟動 E4S-P1-S0_ReadingV1SourceGroundedPractice_ActivationAndScopeGate
```

Activation result:

```text
P1_ACTIVATION_SCOPE_GATE = ACTIVE
```

This does not activate Reading implementation, question generation, HTML export, worksheet export, learner state, or adaptive learning path.

---

## 4. Task Boundary

Task type:

```text
DesignScan / ActivationGate
```

Allowed file:

```text
docs/ulga/E4S_P1_READING_V1_ACTIVATION_SCOPE_GATE.md
```

Forbidden files and paths:

```text
tools/build_e4s_source_manifest.py
tools/validate_e4s_source_manifest.py
ulga/graph/e4s_source_manifest.json
ulga/reports/e4s_source_manifest_summary.json
docs/roadmap/E4S_PHASED_TASK_DECOMPOSITION_AND_HANDSHAKE_CONTRACT.md
docs/ulga/E4S_P0_SOURCE_AUTHORITY_FOUNDATION_CLOSEOUT_READBACK_QA.md
runtime files
generators
validators
source adapters
site HTML
student-facing Reading practice HTML
worksheet exports
large generated artifacts
source corpus payloads
learner state files
learner profile files
adaptive scheduling files
dependency graph artifacts
promotion artifacts
```

Generated artifact policy:

```text
No generated Reading questions, practice packages, student-facing files, learner events, or large JSON artifacts are allowed in P1-S0.
```

Runtime impact:

```text
NONE
```

Promotion impact:

```text
NONE. P1-S0 performs no source/content authority promotion.
```

---

## 5. P1 Reading V1 Objective

P1 big-task objective:

```text
Create a source-grounded Reading V1 candidate pipeline that can select approved reading sources, define reading item schemas, generate a small pilot candidate set, validate the pilot, and prepare for later learner-facing Reading output without creating learner state or adaptive behavior.
```

P1-S0 objective:

```text
Confirm P1 is allowed to start, define the first safe Reading V1 scope, record blocked outputs, identify source lanes that may be examined by P1-S1, and establish the next task.
```

P1-S0 is not a content task. It is only the activation and scope boundary for later P1 work.

---

## 6. Reading V1 Initial Scope

P1 Reading V1 may eventually support:

```text
source-grounded Reading candidate selection
Reading item schema design
small pilot Reading candidate generation after schema gates
candidate validation
manual review queue design
later learner-facing output decision gate
```

P1 Reading V1 must initially remain limited to:

```text
source eligibility
input contract
schema design
validator contract
query design
small pilot only after explicit policy
QA readback
```

P1 Reading V1 must not expand into Writing, Listening, Speaking, Assessment, P7 learner state, or P8 product layer.

---

## 7. Preliminary Source Lane Scope for P1-S1

P1-S0 does not decide final source eligibility. It only identifies source lanes that P1-S1 must review.

Source lanes to inspect in P1-S1:

| Source / Lane | Preliminary P1 Role | Allowed P1-S1 Use | Blocked Use |
|---|---|---|---|
| `raz_reading_corpus` / `LANE_RAZ_READING_CANDIDATE` | primary Reading candidate lane | define input contract and trace requirements | direct learner-facing output, public distribution, direct authority |
| `raz_wordlist` / `LANE_RAZ_EVIDENCE` | exposure evidence only | support source ordering / selection constraints | direct vocabulary authority, direct question generation |
| `grammar_profile` / `LANE_CORE_AUTHORITY_REFERENCE` | reference only | future schema / validation reference | direct grammar authority, learner-facing output |
| `vocabulary_profile` / `LANE_CORE_AUTHORITY_REFERENCE` | reference only | future vocabulary constraint reference | direct vocabulary authority, learner-facing output |
| `frequency_profile` / `LANE_CORE_AUTHORITY_REFERENCE` | reference only | future readability / frequency reference | final vocabulary authority, learner-facing output |
| `chunk_authority` / `LANE_CORE_AUTHORITY_REFERENCE` | reference only | future sentence/chunk constraint reference | automatic promotion, learner-facing output |
| `status_artifact` / `LANE_STATUS_ONLY` | project progress only | audit / readback only | Reading source, learner progress, learner-facing output |
| `generated_content_candidate` / `LANE_GENERATED_CANDIDATE_REVIEW` | candidate review only | no use in P1-S1 except as blocked example | authority, learner-facing output, large-scale generation |

P1-S1 must convert this preliminary scope into a formal source eligibility and input contract.

---

## 8. Blocked Outputs in P1-S0

P1-S0 explicitly blocks:

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
source payload extraction beyond metadata/readback references
```

Blocked means:

```text
not generated
not modified
not promoted
not implied by this document
not allowed as next task unless the governance contract says so
```

---

## 9. P1 First Milestone Plan

P1-M0 Activation and Scope Gate consists of:

| Order | Small Task ID | Purpose | Deliverable | Status |
|---:|---|---|---|---|
| 0 | `E4S-P1-S0_ReadingV1SourceGroundedPractice_ActivationAndScopeGate` | Confirm P0 closeout, source lanes, blocked outputs, and first milestone | `docs/ulga/E4S_P1_READING_V1_ACTIVATION_SCOPE_GATE.md` | `COMPLETED` |
| 1 | `E4S-P1-S1_ReadingV1_SourceEligibilityAndInputContract_DesignScan` | Define which manifest records may support Reading V1 and how RAZ reading corpus / RAZ wordlist may be used | `docs/ulga/E4S_P1_READING_V1_SOURCE_ELIGIBILITY_CONTRACT.md` | `NEXT` |
| 2 | `E4S-P1-S2_ReadingV1_TaskQueueAndDistanceVector_DesignScan` | Define P1 task queue, distance vector, and handoff sequence | `docs/ulga/E4S_P1_READING_V1_TASK_QUEUE.md` | `PLANNED` |

P1-S0 does not authorize P1-M1 / P1-M2 implementation. Those require the prior P1-M0 gates.

---

## 10. Acceptance Gates for P1-S0

| Gate | Result | Evidence |
|---|---:|---|
| Governance MD checked | PASS | Section 2 |
| Current task appears in governance contract | PASS | Section 2 |
| P0 closeout dependency checked | PASS | Section 3 |
| P1 activated only as scope gate | PASS | Section 4 |
| Allowed file scope locked | PASS | Section 4 |
| Forbidden files listed | PASS | Section 4 |
| Reading V1 objective defined | PASS | Section 5 |
| Initial Reading V1 scope defined | PASS | Section 6 |
| Preliminary source lane scope identified | PASS | Section 7 |
| Blocked outputs recorded | PASS | Section 8 |
| P1-M0 first milestone plan defined | PASS | Section 9 |
| Runtime impact avoided | PASS | Documentation only |
| Manifest modification avoided | PASS | No JSON change |
| Builder / validator modification avoided | PASS | No Python change |
| Learner state avoided | PASS | No learner files |
| Student-facing output avoided | PASS | No HTML / worksheet output |
| Promotion avoided | PASS | Design only |

---

## 11. Warning Register

```text
warning_id: E4S-P1-S0-WARN-001
severity: medium
classification: SOURCE_ELIGIBILITY_NOT_YET_FINAL
message: P1-S0 identifies preliminary source lanes only. P1-S1 must define the formal source eligibility and input contract.
blocks_current_task: no
```

```text
warning_id: E4S-P1-S0-WARN-002
severity: medium
classification: NO_TEST_RUN
message: This activation scope gate is documentation-only. No local Python tests or GitHub Actions CI were run.
blocks_current_task: no
```

---

## 12. Deferred Issues Register

```text
issue_id: E4S-P1-S0-DEFER-001
severity: high
affected_file_or_artifact: Reading V1 source eligibility
classification: FUTURE_WORK
why_deferred: P1-S0 activates scope only. P1-S1 must define exact eligible manifest records and source-input rules.
recommended_future_task: E4S-P1-S1_ReadingV1_SourceEligibilityAndInputContract_DesignScan
blocks_current_task: no
```

```text
issue_id: E4S-P1-S0-DEFER-002
severity: high
affected_file_or_artifact: Reading item schema / candidate schema
classification: FUTURE_WORK
why_deferred: Schema work belongs to P1-M1 after P1-M0 scope gates.
recommended_future_task: E4S-P1-S3_ReadingV1_ItemSchema_DesignScan
blocks_current_task: no
```

```text
issue_id: E4S-P1-S0-DEFER-003
severity: high
affected_file_or_artifact: Reading V1 pilot generation
classification: FUTURE_WORK
why_deferred: Pilot generation is blocked until source eligibility, schema, validator contract, and pilot policy exist.
recommended_future_task: E4S-P1-S10_ReadingV1_PilotCandidateBuilder_Implementation after required gates
blocks_current_task: no
```

```text
issue_id: E4S-P1-S0-DEFER-004
severity: high
affected_file_or_artifact: learner-facing Reading HTML / worksheet export
classification: FUTURE_WORK
why_deferred: Learner-facing output is blocked until validated package and learner-facing output decision gate.
recommended_future_task: E4S-P1-S15_ReadingV1_LearnerFacingOutputGate_DesignScan
blocks_current_task: no
```

---

## 13. Distance Vector

P0 state:

```text
E4S-P0_SourceAuthorityAndCorpusRoadmap -> CLOSED_AS_SOURCE_AUTHORITY_FOUNDATION
D_P0 = 0
```

P1 state after this task:

```text
E4S-P1_ReadingV1SourceGroundedPractice -> ACTIVE_SCOPE_GATE
```

Current task status:

```text
E4S-P1-S0_ReadingV1SourceGroundedPractice_ActivationAndScopeGate -> COMPLETED
```

P1-M0 remaining tasks:

```text
D_P1_M0 = 2 small tasks left
```

P1 remaining small-task distance:

```text
D_P1 = 18 small tasks left
```

Remaining P1-M0 tasks:

```text
E4S-P1-S1_ReadingV1_SourceEligibilityAndInputContract_DesignScan
E4S-P1-S2_ReadingV1_TaskQueueAndDistanceVector_DesignScan
```

---

## 14. Mandatory Handoff Block

```text
GOVERNANCE_MD_CHECK = PASS
CURRENT_TASK_IN_CONTRACT = PASS
CURRENT_TASK_SCOPE_LOCK = PASS
FORBIDDEN_OUTPUT_CHECK = PASS
FILES_CREATED_OR_MODIFIED = docs/ulga/E4S_P1_READING_V1_ACTIVATION_SCOPE_GATE.md
ACCEPTANCE_GATES = PASS_WITH_WARNINGS
DISTANCE_VECTOR_UPDATE = D_P1_M0 = 2; D_P1 = 18
NEXT_TASK_IN_CONTRACT = PASS
NEXT_TASK_ID = E4S-P1-S1_ReadingV1_SourceEligibilityAndInputContract_DesignScan
DRIFT_RISK = low
DRIFT_REASON = P1 is newly activated, but this task remained documentation-only and did not implement Reading generation.
REQUIRED_ACTION = continue with P1-S1 only
```

---

## 15. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P1-S1_ReadingV1_SourceEligibilityAndInputContract_DesignScan
```

Only next allowed action:

```text
Create docs/ulga/E4S_P1_READING_V1_SOURCE_ELIGIBILITY_CONTRACT.md to define exactly which source families / manifest records may support Reading V1, how RAZ reading corpus may be used, how RAZ wordlist remains evidence-only, and what inputs remain blocked.
```

Stop here until the operator explicitly starts P1-S1.

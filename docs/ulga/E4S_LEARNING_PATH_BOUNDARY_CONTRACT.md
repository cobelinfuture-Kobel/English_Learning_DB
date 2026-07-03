# E4S Learning Path Boundary Contract Design Scan

## 1. Current State

Epic ID:

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

Current Phase:

```text
E4S-P0_SourceAuthorityAndCorpusRoadmap
```

Current Sub-task:

```text
E4S-P0-S6_LearningPathBoundaryContract_DesignScan
```

Deliverable:

```text
docs/ulga/E4S_LEARNING_PATH_BOUNDARY_CONTRACT.md
```

This task defines the boundary between source metadata, practice routing, learner placement, dependency graph, adaptive scheduling, and future P7 learning-path integration. It does not create learner state, adaptive runtime, dependency graph artifacts, recommendation logic, placement logic, generated practice, Reading HTML, validators, builders, or source promotion.

---

## 2. Task Boundary

Task:

```text
E4S-P0-S6_LearningPathBoundaryContract_DesignScan
```

Scope:

```text
Define what current E4S source-level, situation-level, authority-lane, and practice-routing signals may and may not mean before the future learning-path / adaptive layer exists.
```

Allowed files:

```text
docs/ulga/E4S_LEARNING_PATH_BOUNDARY_CONTRACT.md
```

Forbidden files:

```text
tools/build_e4s_source_manifest.py
tools/validate_e4s_source_manifest.py
ulga/graph/e4s_source_manifest.json
ulga/reports/e4s_source_manifest_summary.json
docs/ulga/E4S_AUTHORITY_MAPPING_MATRIX.md
docs/ulga/E4S_LEVEL_SITUATION_TAXONOMY.md
tests/test_build_e4s_source_manifest.py
tests/test_validate_e4s_source_manifest.py
runtime files
generators
validators
source adapters
site HTML
student-facing Reading practice HTML
large generated artifacts
source corpus payloads
learner state files
learner profile files
review queue files
adaptive scheduling files
dependency graph artifacts
promotion artifacts
```

Current-task blockers:

```text
- No explicit boundary between source level metadata and learner placement.
- No explicit boundary between practice routing and adaptive recommendation.
- No explicit boundary between dependency evidence and dependency graph authority.
- No explicit boundary between candidate practice packages and learner-state updates.
- No explicit future handoff contract for P7 adaptive learning path integration.
```

Warning policy:

```text
Any missing learner model, dependency graph, scheduler, answer history, error tag, mastery score, or review queue is FUTURE_WORK unless it prevents this document from defining boundary rules.
```

Generated artifact policy:

```text
No generated artifacts are allowed in this task.
```

Runtime impact:

```text
NONE
```

Promotion impact:

```text
NONE. This contract defines boundary rules only and performs no learner-state, dependency, placement, or promotion action.
```

Stop condition:

```text
Stop after boundary layers, allowed current meanings, blocked meanings, future P7 prerequisites, invalid transitions, gates, distance vector, deferred issues, and next shortest step are documented.
```

---

## 3. Contract Purpose

The Learning Path Boundary Contract prevents premature adaptive-learning behavior.

It separates these concepts:

```text
source level claim != learner placement
source situation label != recommended practice
practice candidate != assigned task
answer correctness != mastery score
error tag != dependency diagnosis
dependency hint != dependency graph authority
reviewed content != adaptive scheduling permission
```

Until future P7 gates exist, E4S may register, classify, validate, and route source-grounded practice candidates, but it must not update learner path state or recommend a next lesson based on learner performance.

---

## 4. Boundary Layer Model

| Layer ID | Layer Name | Owns | May Exist in P0? | May Drive Learner Path? |
|---|---|---|---:|---:|
| `L0_SOURCE_METADATA` | Source metadata layer | source family, source path, license, review status | yes | no |
| `L1_AUTHORITY_LANE` | Authority lane layer | authority role, lane mapping, blocked use | yes | no |
| `L2_LEVEL_SITUATION_CLAIM` | Level/situation claim layer | raw level, normalized band, situation label, skill fit | design only | no |
| `L3_QUERY_ROUTING` | Query routing layer | source trace, candidate selection, item-type eligibility | P1+ | no |
| `L4_PRACTICE_PACKAGE_CANDIDATE` | Practice candidate layer | generated/assembled practice packages | P1+ | no |
| `L5_VALIDATED_PRACTICE_PACKAGE` | Validated practice layer | validator-approved packages | future | no, unless P7 consumes it |
| `L6_LEARNER_RESPONSE_EVENT` | Learner response layer | answers, attempts, timestamps | future | no, raw event only |
| `L7_ERROR_TAG_SIGNAL` | Error tag signal layer | grammar/vocab/strategy error tags | future P6 | no, signal only |
| `L8_DEPENDENCY_SIGNAL` | Dependency signal layer | prerequisite hints, concept relations | future | no, signal only |
| `L9_LEARNER_MODEL` | Learner model layer | mastery, weakness, confidence, review need | future P7 | yes, after P7 gates |
| `L10_ADAPTIVE_SCHEDULER` | Adaptive scheduler layer | next task, spacing, review sequence | future P7+ | yes, after P7 gates |

---

## 5. Current Phase Meaning Boundaries

### 5.1 P0 Meaning

P0 may say:

```text
This source exists or is registered as a reference.
This source belongs to an authority lane.
This source has a level/situation claim boundary.
This source is blocked from learner-facing output unless later gates pass.
This source may be eligible for future query design or candidate selection.
```

P0 must not say:

```text
This learner is at this level.
This source is appropriate for this learner.
This item should be assigned next.
This error means the learner lacks a prerequisite.
This student has mastered or failed a concept.
This content is ready for adaptive scheduling.
```

### 5.2 P1-P6 Meaning

P1-P6 may create or validate skill-specific artifacts within their future scopes, but those artifacts still do not update learner path unless P7 explicitly consumes them.

```text
P1 Reading may create source-grounded Reading candidates after P0 gates.
P2 Assessment may define pattern-reviewed assessment candidates.
P3 Writing may derive writing practice candidates.
P4 Dialogue/Speaking may derive speaking prompt candidates.
P5 Listening may derive listening candidates.
P6 Error Tagging may create error tag signals.
```

P1-P6 still must not perform:

```text
learner placement
mastery scoring
adaptive recommendation
spaced review scheduling
dependency graph mutation
learner state mutation
```

### 5.3 P7 Meaning

P7 is the first phase allowed to integrate:

```text
validated practice packages
learner response events
error tag signals
dependency signals
mastery estimates
review scheduling
adaptive next-step recommendations
```

P7 is not active during P0.

---

## 6. Boundary Input Classes

| Input Class | Examples | Current Status | Can P7 Use Later? | Required Gate Before P7 Use |
|---|---|---|---:|---|
| `source_metadata` | source_family, path, license_status | active P0 | yes | manifest + validator pass |
| `authority_lane` | evidence_only, candidate_only, status_only | active P0 | yes | authority matrix alignment |
| `level_claim` | RAZ_D, A1_LOW, PRE_A1 | design P0 | yes | level validation / cross-source alignment |
| `situation_claim` | classroom, reading_passage, story_sequence | design P0 | yes | situation taxonomy validation |
| `practice_candidate` | future Reading/Writing/Dialogue item | future | yes | skill validator pass |
| `validated_practice_package` | future validator-approved package | future | yes | package validator pass |
| `learner_response_event` | answer, attempt, timestamp | future | yes | event schema + privacy gate |
| `error_tag_signal` | vocab_misread, tense_error, inference_error | future P6 | yes | error tag validator pass |
| `dependency_signal` | prerequisite hint, concept relation | future | yes | dependency contract pass |
| `manual_review_signal` | reviewer accepted/rejected | future | yes | review schema pass |

---

## 7. Explicitly Blocked Transitions

The following transitions are invalid before P7 gates exist:

| Blocked Transition | Reason | Required Handling |
|---|---|---|
| `source_metadata -> learner_placement` | metadata is about source, not learner | block |
| `level_claim -> learner_level` | source level is not learner state | block |
| `RAZ_level -> CEFR_learner_level` | RAZ is not CEFR equivalence | block |
| `situation_claim -> recommended_task` | situation is routing metadata only | block |
| `authority_lane -> assigned_practice` | authority lane is not scheduler | block |
| `practice_candidate -> learner_assignment` | candidate is not validated and not scheduled | block |
| `validated_practice_package -> adaptive_next_step` | validation is not scheduling | block until P7 |
| `answer_correctness -> mastery_score` | raw correctness is not mastery model | block until learner model |
| `error_tag_signal -> dependency_diagnosis` | tag is signal, not diagnosis | block until dependency model |
| `dependency_signal -> dependency_graph_authority` | hint is not graph authority | block until dependency review |
| `status_artifact -> learner_progress` | project status is not learner status | block |
| `generated_candidate -> learning_path_node` | generated content is candidate only | block |

---

## 8. Allowed Current Transitions

These transitions are allowed in or after P0, if the owning phase approves them:

| Allowed Transition | Owner | Constraint |
|---|---|---|
| `source_metadata -> manifest_summary` | P0 | metadata only |
| `source_family -> authority_lane` | P0-S4 | no promotion by implication |
| `level_claim -> routing_metadata` | P0-S5 | not learner placement |
| `situation_claim -> routing_metadata` | P0-S5 | not item generation |
| `reading_corpus_candidate -> Reading query design` | P1 | requires source trace |
| `assessment_pattern_candidate -> assessment pattern design` | P2 | no item generation before review |
| `template_corpus -> writing template design` | P3 | no learner-facing worksheet before validation |
| `dialogue_corpus_candidate -> dialogue prompt design` | P4 | no prompt authority before review |
| `listening_candidate -> listening design` | P5 | no audio generation before review |
| `error_tag_signal -> diagnostic candidate` | P6 | no mastery update |
| `validated_signals -> learning path integration` | P7 | only after P7 boundary gates |

---

## 9. Future P7 Prerequisites

P7 must not start until these prerequisites are satisfied or explicitly deferred with operator approval:

```text
1. Source manifest validator passes.
2. Authority lane mapping is available.
3. Level / situation taxonomy is available.
4. Learning path boundary contract exists.
5. Validated practice package schema exists for at least one skill.
6. Learner response event schema exists.
7. Error tag signal schema exists or is explicitly out of scope.
8. Dependency signal / prerequisite contract exists or is explicitly out of scope.
9. Learner state schema exists.
10. Privacy and persistence policy exists for learner records.
11. Adaptive scheduler policy exists.
12. Manual override and review policy exists.
```

During P0, only items 1-4 are in scope.

---

## 10. Learning Path Data Classes

Future learning-path work must distinguish these data classes:

| Data Class | Meaning | P0 Status | Mutation Allowed in P0? |
|---|---|---|---:|
| `source_record` | registered source metadata | active | yes, only via approved manifest tasks |
| `content_candidate` | possible item/source candidate | future | no |
| `validated_content_item` | validator-approved practice item | future | no |
| `practice_event` | learner was shown or assigned an item | future | no |
| `response_event` | learner answered or skipped | future | no |
| `error_signal` | raw error tag or observation | future | no |
| `diagnostic_inference` | interpreted weakness or misconception | future | no |
| `dependency_node` | concept or prerequisite node | future | no |
| `dependency_edge` | prerequisite relationship | future | no |
| `learner_state` | per-learner mastery/review model | future P7 | no |
| `scheduler_decision` | selected next task/review | future P7 | no |

---

## 11. Practice Routing vs Learning Path

Practice routing is not learning path.

Practice routing may answer:

```text
Which source lane can support this future practice type?
Which level/situation labels may be considered as metadata?
Which skill phase owns this candidate?
Which validator must run before learner-facing use?
```

Learning path may answer only in future P7:

```text
Which item should this learner do next?
Which prerequisite is missing?
Which concept needs review?
When should the learner review this item?
How confident is the system about mastery?
```

Until P7, all learning-path outputs must remain blocked.

---

## 12. Dependency Graph Boundary

Dependency graph work is not active in P0.

Allowed in P0:

```text
Mention that future dependencies may exist.
Record dependency-related work as deferred.
Prevent source metadata from acting as dependency graph authority.
```

Blocked in P0:

```text
creating dependency_node artifacts
creating dependency_edge artifacts
calculating prerequisite distance
ranking next concepts
updating mastery by dependency
using grammar/vocabulary tags as dependency truth
```

Future dependency graph prerequisites:

```text
canonical concept IDs
dependency edge schema
edge evidence policy
edge confidence policy
validator for cycles / invalid edges
manual review policy
learner-state consumption policy
```

---

## 13. Learner State Boundary

Learner state work is not active in P0.

Blocked state fields in P0:

```text
learner_id
mastery_score
confidence_score
last_seen_at
next_review_at
weakness_tags
assigned_items
completed_items
response_history
scheduler_queue
placement_level
adaptive_band
```

If any future task needs these fields before P7, it must be explicitly scoped and approved.

---

## 14. Adaptive Scheduling Boundary

Adaptive scheduling is not active in P0.

Blocked scheduler actions in P0:

```text
select next item
schedule review
rank learner weaknesses
space repetition
increase/decrease difficulty for a learner
advance or demote learner level
merge learner history with source metadata
```

Allowed scheduler-related wording in P0:

```text
future P7 adaptive scheduling
blocked until learner-state and scheduler policy exist
deferred adaptive integration
```

---

## 15. Skill Phase Handoff Rules

| Source / Signal | Skill Phase Owner | May Update Learning Path Before P7? | Handoff Requirement |
|---|---|---:|---|
| Reading candidate | P1 | no | validated package schema |
| Assessment pattern | P2 | no | assessment validator |
| Writing template candidate | P3 | no | writing item validator |
| Dialogue/Speaking candidate | P4 | no | dialogue/speaking review |
| Listening candidate | P5 | no | listening validator / audio policy |
| Error tag signal | P6 | no | error tag schema and validator |
| Learner response event | P7 | yes, after gates | event schema + privacy policy |
| Dependency signal | P7 | yes, after gates | dependency contract |
| Manual review signal | P7 | yes, after gates | review schema |

---

## 16. Invalid Claims

These claims must be rejected in readbacks, docs, builders, validators, and future task prompts unless a later approved task changes the boundary:

```text
The learner is A1 because a source is A1.
The learner should read this because the passage is RAZ_D.
The learner has mastered vocabulary because one item was correct.
The learner has a grammar weakness because one generated item was wrong.
The system can recommend next lesson from source metadata alone.
A status artifact is evidence of learner progress.
A generated candidate can be placed into a learning path without review.
A source authority lane is equivalent to learner readiness.
A situation label is enough to create a learner-facing task.
```

---

## 17. Required Future Contract Fields

Future P7 or pre-P7 tasks may define these fields, but this task does not add them to any schema:

```text
learner_id
content_item_id
validated_package_id
practice_event_id
response_event_id
error_signal_id
dependency_node_id
dependency_edge_id
mastery_score
confidence_score
review_due_at
scheduler_policy_version
placement_policy_version
dependency_policy_version
privacy_policy_version
manual_override_status
```

These fields remain forbidden outside explicitly approved learner-state / P7 tasks.

---

## 18. Acceptance Gates for P0-S6

| Gate | Result | Evidence |
|---|---:|---|
| Boundary layer model defined | PASS | Section 4 |
| P0 / P1-P6 / P7 meaning boundaries defined | PASS | Section 5 |
| Boundary input classes defined | PASS | Section 6 |
| Blocked transitions defined | PASS | Section 7 |
| Allowed current transitions defined | PASS | Section 8 |
| Future P7 prerequisites defined | PASS | Section 9 |
| Learning path data classes separated | PASS | Section 10 |
| Practice routing vs learning path separated | PASS | Section 11 |
| Dependency graph boundary defined | PASS | Section 12 |
| Learner state boundary defined | PASS | Section 13 |
| Adaptive scheduling boundary defined | PASS | Section 14 |
| Skill phase handoff rules defined | PASS | Section 15 |
| Invalid claims defined | PASS | Section 16 |
| Runtime impact avoided | PASS | Documentation only |
| Manifest modification avoided | PASS | No JSON change |
| Validator modification avoided | PASS | No Python change |
| Learner state avoided | PASS | No learner files |
| Promotion avoided | PASS | Design only |

---

## 19. Distance Vector

Current Epic:

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

Current Phase:

```text
E4S-P0_SourceAuthorityAndCorpusRoadmap
```

Current Sub-task:

```text
E4S-P0-S6_LearningPathBoundaryContract_DesignScan
```

Sub-task Status:

```text
E4S-P0-S6_LearningPathBoundaryContract_DesignScan -> COMPLETED
```

P0 remaining distance after this sub-task:

```text
D_P0 = 1 sub-task left
```

Remaining P0 task:

```text
E4S-P0-S7_StatusArtifactReclassification_DocumentationPatch
```

---

## 20. Deferred Issues Register

```text
issue_id: E4S-P0-S6-DEFER-001
severity: high
affected_file_or_artifact: learner_state schema
classification: FUTURE_WORK
why_deferred: P0-S6 defines the boundary but does not create learner state.
recommended_future_task: future P7 learner state schema task
blocks_current_task: no
```

```text
issue_id: E4S-P0-S6-DEFER-002
severity: high
affected_file_or_artifact: adaptive scheduler
classification: FUTURE_WORK
why_deferred: P0-S6 blocks adaptive scheduling until P7 gates exist.
recommended_future_task: future P7 scheduler policy task
blocks_current_task: no
```

```text
issue_id: E4S-P0-S6-DEFER-003
severity: high
affected_file_or_artifact: dependency graph
classification: FUTURE_WORK
why_deferred: P0-S6 documents dependency boundaries but does not create graph artifacts.
recommended_future_task: future dependency graph contract / validator task
blocks_current_task: no
```

```text
issue_id: E4S-P0-S6-DEFER-004
severity: medium
affected_file_or_artifact: practice event / response event schema
classification: FUTURE_WORK
why_deferred: Response event data belongs to future learner-facing and P7 integration tasks.
recommended_future_task: future learner response event schema task
blocks_current_task: no
```

```text
issue_id: E4S-P0-S6-DEFER-005
severity: medium
affected_file_or_artifact: privacy and persistence policy
classification: FUTURE_WORK
why_deferred: Learner data persistence is outside P0 source authority scope.
recommended_future_task: future privacy / learner data governance task
blocks_current_task: no
```

---

## 21. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P0-S7_StatusArtifactReclassification_DocumentationPatch
```

Only next allowed action:

```text
Create docs/status/RAZ_AW_STATUS_ARTIFACT_CLASSIFICATION.md to classify status snapshots / status HTML / readback artifacts as progress-tracking artifacts, not student-facing Reading HTML or content authority.
```

Stop here until the operator explicitly starts E4S-P0-S7.

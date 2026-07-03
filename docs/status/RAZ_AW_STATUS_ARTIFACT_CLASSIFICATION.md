# RAZ-AW Status Artifact Classification Documentation Patch

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
E4S-P0-S7_StatusArtifactReclassification_DocumentationPatch
```

Deliverable:

```text
docs/status/RAZ_AW_STATUS_ARTIFACT_CLASSIFICATION.md
```

This task classifies RAZ-AW status snapshots, status HTML, readback reports, and progress-tracking artifacts as project status artifacts only. They are not student-facing Reading HTML, Reading source authority, content authority, learner progress evidence, learner state, practice packages, or adaptive-learning input.

---

## 2. Task Boundary

Task:

```text
E4S-P0-S7_StatusArtifactReclassification_DocumentationPatch
```

Scope:

```text
Document how status snapshots, status HTML, readback artifacts, and progress reports must be classified so they cannot be mistaken for student-facing Reading practice, content source authority, learner-facing output, or learner state.
```

Allowed files:

```text
docs/status/RAZ_AW_STATUS_ARTIFACT_CLASSIFICATION.md
```

Forbidden files:

```text
tools/build_e4s_source_manifest.py
tools/validate_e4s_source_manifest.py
ulga/graph/e4s_source_manifest.json
ulga/reports/e4s_source_manifest_summary.json
docs/ulga/E4S_AUTHORITY_MAPPING_MATRIX.md
docs/ulga/E4S_LEVEL_SITUATION_TAXONOMY.md
docs/ulga/E4S_LEARNING_PATH_BOUNDARY_CONTRACT.md
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
adaptive scheduling files
dependency graph artifacts
promotion artifacts
```

Current-task blockers:

```text
- Status snapshots can be confused with source authority evidence.
- Status HTML can be confused with student-facing Reading HTML.
- Readback reports can be confused with generated practice packages.
- Project progress artifacts can be confused with learner progress evidence.
```

Warning policy:

```text
Any missing inventory linkage, old filename inconsistency, or future status cleanup need is FUTURE_WORK unless it prevents this classification document from defining the boundary.
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
NONE. Status artifacts are explicitly blocked from source/content/learner promotion.
```

Stop condition:

```text
Stop after status artifact definition, classification matrix, allowed uses, blocked uses, invalid transitions, file naming policy, gates, distance vector, deferred issues, and next shortest step are documented.
```

---

## 3. Classification Purpose

This documentation patch prevents this failure:

```text
status artifact -> content source
status artifact -> Reading practice HTML
status artifact -> learner progress
status artifact -> adaptive signal
status artifact -> authority evidence
```

Status artifacts may describe what the project has done. They must not become what the learner studies, what the content system trusts, or what the adaptive layer consumes.

---

## 4. Status Artifact Definition

A status artifact is any file or report whose primary purpose is to describe project state, task progress, implementation state, readback QA, operator handoff, or roadmap position.

Included artifact types:

```text
status snapshot
status HTML
status markdown
readback report
QA readback
operator handoff summary
progress dashboard export
implementation completion report
local or CI result summary
roadmap distance report
```

Not included:

```text
source corpus
Reading passage
Reading question set
student-facing worksheet
student-facing Reading HTML
validated practice package
learner answer record
learner progress record
learner state artifact
content authority graph
```

---

## 5. Classification Matrix

| Artifact Class | Example | Classification | Allowed Use | Blocked Use |
|---|---|---|---|---|
| Status snapshot | `RAZ-AW-V1 Status Snapshot.txt` | `status_artifact` | progress tracking, roadmap readback | content authority, learner-facing output |
| Status HTML | RAZ-AW status page export | `status_artifact` | project dashboard / human review | student-facing Reading HTML, app runtime content |
| Readback report | task completion summary | `status_artifact` | operator handoff, audit trail | source authority, generated practice |
| QA readback | PASS / FAIL summary | `status_artifact` | QA evidence for project work | learner progress, mastery evidence |
| Implementation report | builder/validator completion note | `status_artifact` | project history | practice package, adaptive signal |
| Roadmap distance report | `D_P0 = n` style update | `status_artifact` | progress tracking | learner path distance |
| CI/local test summary | test result text | `status_artifact` | engineering verification | learner-facing proof, content validation unless separately scoped |

---

## 6. Required Manifest Classification

If a status artifact is registered in a future manifest or manifest expansion, it must use:

```text
source_family = status_artifact
authority_role = status_only
promotion_rule = status_artifact_never_content
```

Required blocked use:

```text
learner_facing_output
direct_reading_authority
automatic_promotion
final_authority_promotion
app_runtime_use
```

Recommended risk flags:

```text
status_not_content
learner_facing_blocked
```

Recommended target lane:

```text
LANE_STATUS_ONLY
```

---

## 7. Allowed Uses

Status artifacts may be used for:

```text
project progress tracking
operator handoff
readback QA
human audit trail
roadmap distance update
implementation history
scope-control evidence
status dashboard reference
```

Status artifacts may support documentation statements such as:

```text
This task completed.
This gate passed.
This file was created.
This phase has N remaining tasks.
This warning is deferred.
This next shortest step is proposed.
```

---

## 8. Blocked Uses

Status artifacts must not be used for:

```text
student-facing Reading HTML
Reading passage source
Reading question source
Vocabulary Authority
Grammar Authority
Dialogue Authority
Writing Authority
Assessment Authority
learner progress evidence
learner state update
adaptive recommendation
placement decision
mastery score
review scheduling
source promotion
content promotion
large-scale candidate generation
```

---

## 9. Status HTML vs Student-facing Reading HTML

Status HTML and student-facing Reading HTML must remain separate.

| Dimension | Status HTML | Student-facing Reading HTML |
|---|---|---|
| Purpose | project status / progress dashboard | learner practice interface |
| User | operator / developer / reviewer | learner |
| Source role | status only | future validated practice package |
| May contain task gates | yes | no, unless hidden debug tool approved |
| May contain Reading questions | no | yes, only after P1 validators |
| May update learner state | no | no until P7 gates, even if learner-facing later |
| May be content authority | no | no; learner-facing output is not authority |
| Promotion rule | `status_artifact_never_content` | controlled by future practice package validators |

Hard rule:

```text
A status page that visually looks like an app page is still a status artifact if its purpose is progress tracking.
A learner-facing page that displays questions is not allowed to exist under P0.
```

---

## 10. Status Artifact vs Learner Progress

Project progress is not learner progress.

Invalid statements:

```text
The learner progressed because P0 progressed.
The learner completed Reading because the Reading system task completed.
The learner mastered a concept because a validator passed.
The learner should advance because CI passed.
The learner has review debt because a status report says a task is incomplete.
```

Allowed statements:

```text
The project completed a source authority gate.
The project created a manifest.
The project defined a boundary contract.
The project has not yet created learner-facing Reading practice.
The learner path layer remains blocked until P7.
```

---

## 11. Invalid Transitions

The following transitions must remain invalid:

| Invalid Transition | Reason | Required Handling |
|---|---|---|
| `status_artifact -> reading_corpus_candidate` | Status is not source content | fail / block |
| `status_artifact -> direct_reading_authority` | Status is not Reading authority | fail / block |
| `status_artifact -> learner_facing_output` | Status is not student practice | fail / block |
| `status_html -> student_reading_html` | Different artifact classes | block |
| `readback_report -> generated_practice_package` | Readback describes work; it is not practice | block |
| `QA_pass -> learner_progress` | Engineering pass is not learner outcome | block |
| `distance_vector -> learner_path_distance` | Project distance is not learner path | block |
| `status_snapshot -> adaptive_signal` | Status is not learner event | block |
| `CI_result -> content_authority` | CI may verify code; it does not promote content | block |

---

## 12. Naming and Location Policy

Recommended status artifact locations:

```text
docs/status/
docs/roadmap/
docs/ulga/ only when the artifact is a ULGA design/readback document
ulga/reports/ only when it is a machine-readable report explicitly scoped by a builder/validator task
```

Recommended status naming patterns:

```text
*_STATUS_*.md
*_STATUS_*.txt
*_READBACK*.md
*_QA_READBACK*.md
*_CLASSIFICATION.md
*_SUMMARY.json when generated by an approved reporting task
```

Blocked naming behavior:

```text
Do not name status HTML as reading_practice.html.
Do not place student-facing practice under docs/status/.
Do not place status snapshots in source corpus folders unless explicitly marked status_only.
Do not use status filenames as source IDs for content authority.
```

---

## 13. Readback Policy

Readback responses may cite status artifacts as evidence of project progress only.

Readback may say:

```text
The status artifact records that P0-S7 completed.
The status artifact records remaining distance.
The status artifact records a deferred issue.
```

Readback must not say:

```text
The status artifact is a Reading source.
The status artifact proves learner readiness.
The status artifact can generate questions.
The status artifact is learner-facing output.
```

---

## 14. Relationship to P0 Source Authority Foundation

This classification completes the final P0 source-boundary document.

P0 now has these source-foundation components:

```text
1. E4S master roadmap
2. Source inventory contract
3. Source manifest builder
4. Source manifest validator
5. Authority mapping matrix
6. Level / situation taxonomy
7. Learning path boundary contract
8. Status artifact reclassification
```

P0 still does not create:

```text
Reading V1 questions
student-facing Reading HTML
learner state
adaptive scheduler
error-tagging notebook
assessment engine
writing system
dialogue/speaking system
listening system
```

---

## 15. Future Enforcement Expectations

Future validators or review tasks may enforce:

```text
status_artifact must use authority_role=status_only.
status_artifact must use promotion_rule=status_artifact_never_content.
status_artifact must block learner_facing_output.
status_artifact must block direct_reading_authority.
status_artifact must block app_runtime_use when registered as status dashboard only.
status artifact filenames must not be used as content source IDs.
status HTML must not be emitted into student-facing practice output folders.
```

This task documents the expectation only; it does not update validator code.

---

## 16. Acceptance Gates for P0-S7

| Gate | Result | Evidence |
|---|---:|---|
| Status artifact definition created | PASS | Section 4 |
| Classification matrix created | PASS | Section 5 |
| Required manifest classification defined | PASS | Section 6 |
| Allowed uses defined | PASS | Section 7 |
| Blocked uses defined | PASS | Section 8 |
| Status HTML vs student-facing Reading HTML separated | PASS | Section 9 |
| Status artifact vs learner progress separated | PASS | Section 10 |
| Invalid transitions defined | PASS | Section 11 |
| Naming and location policy defined | PASS | Section 12 |
| Readback policy defined | PASS | Section 13 |
| P0 source foundation relationship documented | PASS | Section 14 |
| Runtime impact avoided | PASS | Documentation only |
| Manifest modification avoided | PASS | No JSON change |
| Validator modification avoided | PASS | No Python change |
| Learner state avoided | PASS | No learner files |
| Promotion avoided | PASS | Documentation only |

---

## 17. Distance Vector

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
E4S-P0-S7_StatusArtifactReclassification_DocumentationPatch
```

Sub-task Status:

```text
E4S-P0-S7_StatusArtifactReclassification_DocumentationPatch -> COMPLETED
```

P0 remaining distance after this sub-task:

```text
D_P0 = 0 sub-tasks left
```

P0 foundation state:

```text
E4S-P0_SourceAuthorityAndCorpusRoadmap -> READY_FOR_CLOSEOUT_READBACK
```

P1 status:

```text
E4S-P1_ReadingV1SourceGroundedPractice -> NOT_STARTED
```

---

## 18. Deferred Issues Register

```text
issue_id: E4S-P0-S7-DEFER-001
severity: medium
affected_file_or_artifact: tools/validate_e4s_source_manifest.py
classification: FUTURE_WORK
why_deferred: This task documents classification rules but does not update validator code.
recommended_future_task: future status artifact validator enforcement patch if needed
blocks_current_task: no
```

```text
issue_id: E4S-P0-S7-DEFER-002
severity: medium
affected_file_or_artifact: existing status HTML / dashboard exports
classification: FUTURE_WORK
why_deferred: This task classifies status artifacts but does not rename, move, or rewrite existing exports.
recommended_future_task: future status artifact cleanup task if inventory finds ambiguity
blocks_current_task: no
```

```text
issue_id: E4S-P0-S7-DEFER-003
severity: high
affected_file_or_artifact: student-facing Reading HTML
classification: FUTURE_WORK
why_deferred: P0 explicitly blocks learner-facing Reading output.
recommended_future_task: P1 Reading V1 implementation only after P0 closeout and operator approval
blocks_current_task: no
```

```text
issue_id: E4S-P0-S7-DEFER-004
severity: high
affected_file_or_artifact: learner state / learner progress tracking
classification: FUTURE_WORK
why_deferred: Status artifacts are project progress only, not learner progress.
recommended_future_task: future P7 learner-state work after required gates
blocks_current_task: no
```

---

## 19. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P0-CLOSEOUT_SourceAuthorityFoundation_ReadbackQA
```

Only next allowed action:

```text
Perform a P0 closeout readback that verifies all eight P0 deliverables exist, summarizes PASS / WARNING / DEFERRED state, confirms D_P0 = 0, and keeps P1 Reading V1 blocked until the operator explicitly starts P1.
```

Do not start P1 Reading implementation from this document alone.

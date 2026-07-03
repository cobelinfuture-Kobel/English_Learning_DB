# E4S-P2-S6 Assessment Pattern Sample Package Candidate Only

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
E4S-P2-S6_AssessmentPatternSamplePackage_CandidateOnly
```

本次任務類型：

```text
Candidate-only documentation package
```

核心資料來源與排序依據（Data Sources）：

```text
1. docs/e4s/E4S_P2_ASSESSMENT_PATTERN_VALIDATOR_CONTRACT_DESIGN_SCAN.md
   - P2-S6 is the next shortest step.
   - P2-S6 may define or create a candidate-only sample package only if it remains non-promoted and non-learner-facing.
   - P2-S6 must not implement validator code, runtime answer checking, student-facing HTML, or promotion.

2. docs/e4s/E4S_P2_DISTRACTOR_POLICY_AND_ANSWER_MODEL_DESIGN_SCAN.md
   - Defines answer model families and distractor policy.
   - Defines candidate-only generated distractor rule.
   - Defines rubric_scored_response as writing_boundary_only.

3. docs/e4s/E4S_P2_KET_READING_PATTERN_MAPPING_DESIGN_SCAN.md
   - Defines A2 Key Reading parts 1–5 as reading candidates.
   - Defines A2 Key parts 6–7 as writing-boundary only.

4. docs/e4s/E4S_P2_CAMBRIDGE_YLE_PATTERN_MAPPING_DESIGN_SCAN.md
   - Defines Cambridge YLE task-shape mappings and path aliases.

5. docs/e4s/E4S_P2_ASSESSMENT_PATTERN_CONTRACT_DESIGN_SCAN.md
   - Defines canonical assessment pattern object and source/evidence/promotion requirements.

6. 重點任務排程.txt
   - Every task must follow Current State / Core Execution / Gate & Distance Update / Next Shortest Step.
   - Anti-Scope-Creep applies.
```

外接儲存權限驗證：

```text
GitHub: [已授權] 讀取專案 / 透過 API 寫入專案檔案
Google Drive: [已授權] 讀取雲端硬碟參考檔案、Spec 或資料集
```

本次交握產出目標（Deliverable）：

```text
docs/e4s/E4S_P2_ASSESSMENT_PATTERN_SAMPLE_PACKAGE_CANDIDATE_ONLY.md
```

本次任務不產出：

```text
- no runtime code
- no tools/*.py
- no validators/*.py
- no tests/*.py
- no student-facing HTML
- no learner records
- no schema promotion
- no official Cambridge asset copy
- no official Cambridge sample reproduction
- no validated generated JSON artifact
- no final authority sample item bank
```

---

## 2. Required Task Header

```text
Task:
E4S-P2-S6_AssessmentPatternSamplePackage_CandidateOnly

Scope:
Create a documentation-only candidate sample package that demonstrates how Phase 2 assessment pattern contracts, answer models, distractor policy, evidence requirements, and promotion gates should fit together.

Allowed files:
docs/e4s/E4S_P2_ASSESSMENT_PATTERN_SAMPLE_PACKAGE_CANDIDATE_ONLY.md

Forbidden files:
tools/*
validators/*
tests/*
output/*
generated/*
site/*
learner_state/*

Current-task blockers:
- P2-S1 must exist.
- P2-S2 must exist.
- P2-S3 must exist.
- P2-S4 must exist.
- P2-S5 must exist.
- Samples must remain synthetic, candidate-only, non-promoted, non-learner-facing, and non-official.
- Samples must not reproduce Cambridge official sample items.
- Samples must not imply validator pass because no validator code is executed.

Warning policy:
Sample gaps may be recorded as deferred issues. They must not expand into implementation.

Generated artifact policy:
This file may contain documentation-only pseudo-payloads. It must not create standalone generated JSON artifacts.

Runtime impact:
None.

Promotion impact:
None. This task does not promote any pattern, sample item, source, answer model, distractor, or package into final authority.

Stop condition:
Stop after the candidate-only sample package document is written and P2-S7 is identified as the next shortest step.

Deferred issues register:
All validator code, tests, JSON schema files, runtime answer checking, official source ingestion, learner-facing rendering, and final promotion are deferred.
```

---

## 3. Core Execution

### 3.1 Purpose

P2-S6 creates a small documentation-only sample package to test whether the Phase 2 design documents can be read together coherently.

It answers:

```text
Can we represent representative Phase 2 assessment pattern candidates using the contract, answer model, distractor policy, source evidence, validator contract, and promotion gates already designed?
```

It does not answer:

```text
Can the system generate, validate, score, render, or deploy these items?
```

No validator is run in this task.

---

### 3.2 Package Status

```text
sample_package_id: E4S_P2_S6_SAMPLE_PACKAGE_CANDIDATE_ONLY_V0
package_status: candidate_only_documentation
learner_facing_allowed: false
promotion_allowed: false
validator_executed: false
runtime_available: false
official_exam_content_used: false
synthetic_design_fixture_used: true
```

Rules:

```text
- This package is not a production dataset.
- This package is not a generated question bank.
- This package is not learner-facing.
- This package is not validated by code.
- This package is a design fixture for P2-S7 ReadbackQA.
```

---

### 3.3 Synthetic Source Bundle

The following source snippets are synthetic design fixtures. They are deliberately simple and are not copied from any official exam, RAZ book, worksheet, or Cambridge sample.

```text
SYN_SRC_001:
source_type: synthetic_design_fixture
source_unit_type: short_real_world_text
source_text: The school library is closed today. It will open tomorrow at nine.
source_authority_status: synthetic_non_authority

SYN_SRC_002:
source_type: synthetic_design_fixture
source_unit_type: short_text_set
source_text_A: Tom wants a quiet place to read after lunch.
source_text_B: Mia wants to buy a pencil before class.
source_text_C: Ben wants to play football with his friends.
source_authority_status: synthetic_non_authority

SYN_SRC_003:
source_type: synthetic_design_fixture
source_unit_type: short_factual_text
source_text: Frogs live near water. They can jump well. Many frogs eat small insects.
source_authority_status: synthetic_non_authority

SYN_SRC_004:
source_type: synthetic_design_fixture
source_unit_type: picture_scene_metadata
scene_metadata: one girl is reading under a tree; one boy is kicking a ball; two birds are in the tree
source_authority_status: synthetic_non_authority

SYN_SRC_005:
source_type: synthetic_design_fixture
source_unit_type: short_dialogue
source_text: A: Can you help me carry this box? B: Yes, I can. Where should I put it?
source_authority_status: synthetic_non_authority
```

Blocking boundary:

```text
Synthetic source fixtures are suitable only for documentation-level design checks.
They are not authority content and cannot be promoted.
```

---

## 4. Candidate Sample Index

| Sample ID | Pattern family | Question type | Answer model | Distractor model | Status |
|---|---|---|---|---|
| P2S6_ITEM_001 | short_real_world_text_main_message | multiple_choice | choice_id | distractor_set | candidate_only_documentation |
| P2S6_ITEM_002 | question_to_short_text_matching | matching | matching_pairs | unmatched_options optional | candidate_only_documentation |
| P2S6_ITEM_003 | factual_text_vocabulary_multiple_choice_cloze | gap_fill | choice_id | distractor_set | candidate_only_documentation |
| P2S6_ITEM_004 | picture_scene_yes_no | true_false | boolean | none | candidate_only_documentation |
| P2S6_ITEM_005 | dialogue_response_choice | multiple_choice | choice_id | distractor_set | candidate_only_documentation |
| P2S6_ITEM_006 | open_cloze_lite | gap_fill | accepted_answer_set | none | candidate_only_documentation |
| P2S6_ITEM_007 | writing_boundary_record | writing_prompt | rubric_scored_response | not applicable | boundary_only_documentation |

Coverage note:

```text
The sample package intentionally covers representative answer/distractor contracts, not every Cambridge YLE or A2 Key part.
```

---

## 5. Candidate Samples

### 5.1 P2S6_ITEM_001 — Multiple Choice / Main Message

Purpose:

```text
Demonstrate A2 Key-style short real-world text main-message pattern without copying official exam content.
```

Candidate payload sketch:

```text
item_id: P2S6_ITEM_001
status: candidate_only_documentation
learner_facing_allowed: false
promotion_allowed: false
pattern_family: short_real_world_text_main_message
question_type: multiple_choice
answer_model.family: choice_id
source_ref: SYN_SRC_001
prompt_surface: text
stem: What is the main message?
```

Choice set:

| choice_id | display_text | role | evidence_ref / reason_not_correct |
|---|---|---|---|
| C1 | The library is not open today. | correct | supported by `closed today` |
| C2 | The library opens today at nine. | distractor | reason_not_correct: source says tomorrow at nine |
| C3 | The school is closed tomorrow. | distractor | reason_not_correct: source only says library opens tomorrow |

Answer contract:

```text
correct_choice_ids: [C1]
answer_evidence: SYN_SRC_001 span "closed today"
cardinality: single
```

Distractor contract:

```text
D1 -> C2
provenance: near_surface_match
reason_for_plausibility: uses same time phrase "at nine"
reason_not_correct: wrong day
ambiguity_risk: low
candidate_only: true

D2 -> C3
provenance: semantic_contrast
reason_for_plausibility: uses related school/library setting
reason_not_correct: source discusses library, not whole school
ambiguity_risk: low
candidate_only: true
```

Validator expectation:

```text
Expected future profile: candidate_acceptance
Expected result if encoded correctly: PASS or PASS_WITH_WARNINGS
Actual validator_executed: false
```

---

### 5.2 P2S6_ITEM_002 — Matching / Question to Short Text

Purpose:

```text
Demonstrate A2 Key-style question-to-short-text matching at contract level.
```

Candidate payload sketch:

```text
item_id: P2S6_ITEM_002
status: candidate_only_documentation
learner_facing_allowed: false
promotion_allowed: false
pattern_family: question_to_short_text_matching
question_type: matching
answer_model.family: matching_pairs
source_ref: SYN_SRC_002
reuse_policy: right_item_may_repeat
```

Left items:

| left_item_id | question_text |
|---|---|
| L1 | Who needs a quiet place? |
| L2 | Who wants to buy something for class? |
| L3 | Who wants to play a sport? |

Right items:

| right_item_id | source_segment |
|---|---|
| R_A | Tom wants a quiet place to read after lunch. |
| R_B | Mia wants to buy a pencil before class. |
| R_C | Ben wants to play football with his friends. |

Pair set:

```text
L1 -> R_A, evidence: quiet place to read
L2 -> R_B, evidence: buy a pencil before class
L3 -> R_C, evidence: play football
```

Distractor / option policy:

```text
unmatched_options: none
reuse_policy: right_item_may_repeat documented for future compatibility, but not used in this sample
```

Validator expectation:

```text
Expected future profile: candidate_acceptance
Expected focus layers: matching_pairs, source_trace, evidence, option_set, promotion
Actual validator_executed: false
```

---

### 5.3 P2S6_ITEM_003 — Multiple-Choice Cloze / Vocabulary in Context

Purpose:

```text
Demonstrate factual text vocabulary multiple-choice cloze.
```

Candidate payload sketch:

```text
item_id: P2S6_ITEM_003
status: candidate_only_documentation
learner_facing_allowed: false
promotion_allowed: false
pattern_family: factual_text_vocabulary_multiple_choice_cloze
question_type: gap_fill
answer_model.family: choice_id
source_ref: SYN_SRC_003
local_gap_context: Many frogs eat small ____.
```

Choice set:

| choice_id | display_text | role | evidence_ref / reason_not_correct |
|---|---|---|---|
| C1 | insects | correct | source span: small insects |
| C2 | desks | distractor | reason_not_correct: not living thing / not supported by source |
| C3 | coats | distractor | reason_not_correct: not food / not supported by source |

Answer contract:

```text
correct_choice_ids: [C1]
answer_evidence: SYN_SRC_003 span "small insects"
primary_skill: vocabulary_in_context
```

Distractor contract:

```text
D1 -> C2
provenance: semantic_contrast
reason_for_plausibility: common concrete noun at simple level
reason_not_correct: source says frogs eat insects, not desks
ambiguity_risk: low
candidate_only: true

D2 -> C3
provenance: same_level_vocabulary
reason_for_plausibility: simple concrete noun
reason_not_correct: source says frogs eat insects, not coats
ambiguity_risk: low
candidate_only: true
```

Validator expectation:

```text
Expected future profile: candidate_acceptance
Expected focus layers: answer_model, distractor, evidence, difficulty
Actual validator_executed: false
```

---

### 5.4 P2S6_ITEM_004 — Boolean / Picture Scene Yes-No

Purpose:

```text
Demonstrate picture-scene yes/no pattern using synthetic metadata instead of image assets.
```

Candidate payload sketch:

```text
item_id: P2S6_ITEM_004
status: candidate_only_documentation
learner_facing_allowed: false
promotion_allowed: false
pattern_family: picture_scene_yes_no
question_type: true_false
answer_model.family: boolean
source_ref: SYN_SRC_004
answer_surface: yes_no
claim: A girl is reading under a tree.
```

Answer contract:

```text
truth_value: true
supporting_evidence: SYN_SRC_004 scene_metadata "one girl is reading under a tree"
false_rationale_if_false: not applicable because truth_value is true
```

Distractor contract:

```text
distractor_model: none
false_rationale_required_if_false: true
```

Validator expectation:

```text
Expected future profile: candidate_acceptance
Expected focus layers: boolean, evidence, source_trace, difficulty
Actual validator_executed: false
```

---

### 5.5 P2S6_ITEM_005 — Dialogue Response Choice

Purpose:

```text
Demonstrate dialogue response multiple-choice pattern without official Cambridge dialogue text.
```

Candidate payload sketch:

```text
item_id: P2S6_ITEM_005
status: candidate_only_documentation
learner_facing_allowed: false
promotion_allowed: false
pattern_family: dialogue_response_choice
question_type: multiple_choice
answer_model.family: choice_id
source_ref: SYN_SRC_005
stem: Choose the best next response.
context: A asks for help carrying a box. B agrees and asks where to put it.
```

Choice set:

| choice_id | display_text | role | evidence_ref / reason_not_correct |
|---|---|---|---|
| C1 | Put it on the table, please. | correct | coherent response to "Where should I put it?" |
| C2 | I ate lunch yesterday. | distractor | unrelated to carrying or placing the box |
| C3 | No, I cannot help you. | distractor | contradicts B's previous answer "Yes, I can." |

Answer contract:

```text
correct_choice_ids: [C1]
answer_evidence: dialogue context asks for a place to put the box
primary_skill: dialogue_coherence
```

Distractor contract:

```text
D1 -> C2
provenance: semantic_contrast
reason_for_plausibility: grammatically simple sentence
reason_not_correct: pragmatically unrelated to the dialogue turn
ambiguity_risk: low
candidate_only: true

D2 -> C3
provenance: grammar_contrast
reason_for_plausibility: uses same help topic
reason_not_correct: contradicts previous response "Yes, I can."
ambiguity_risk: low
candidate_only: true
```

Validator expectation:

```text
Expected future profile: candidate_acceptance
Expected focus layers: choice_id, distractor, evidence, source_trace
Actual validator_executed: false
```

---

### 5.6 P2S6_ITEM_006 — Open Cloze Lite / Accepted Answer Set

Purpose:

```text
Demonstrate bounded accepted_answer_set for one-word open cloze.
```

Synthetic source:

```text
SYN_SRC_006:
source_type: synthetic_design_fixture
source_unit_type: short_email
source_text: Hi Sam, I am at the park. I can see two dogs. Please come here soon.
source_authority_status: synthetic_non_authority
```

Candidate payload sketch:

```text
item_id: P2S6_ITEM_006
status: candidate_only_documentation
learner_facing_allowed: false
promotion_allowed: false
pattern_family: email_open_cloze_one_word
question_type: gap_fill
answer_model.family: accepted_answer_set
source_ref: SYN_SRC_006
local_gap_context: I can see two ____.
authorized_answer_length: one_word
```

Answer contract:

```text
canonical_answer: dogs
accepted_answers: [dogs]
answer_evidence: SYN_SRC_006 span "two dogs"
answer_length_limit: one_word
normalization_policy: trim_outer_space + collapse_internal_space + case_insensitive
```

Distractor contract:

```text
distractor_model: none
rejected_answer_examples_optional: [cats, birds, dog]
```

Validator expectation:

```text
Expected future profile: candidate_acceptance
Expected focus layers: accepted_answer_set, evidence, option_set, generated_content
Actual validator_executed: false
```

---

### 5.7 P2S6_ITEM_007 — Writing Boundary Record

Purpose:

```text
Demonstrate how A2 Key-style writing parts are represented only as boundary records, not Reading generation targets.
```

Candidate payload sketch:

```text
item_id: P2S6_ITEM_007
status: boundary_only_documentation
learner_facing_allowed: false
promotion_allowed: false
pattern_family: guided_email_or_note_writing
question_type: writing_prompt
answer_model.family: rubric_scored_response
source_ref: synthetic_prompt_boundary
scoring_allowed: false
```

Boundary contract:

```text
minimum_word_count: 25_or_more_if_future_writing_task_confirms
rubric_required_future_task: E4S-WRITING-S0_WritingAssessmentRubricBoundary_DesignScan
reading_generation_allowed: false
runtime_answer_checking_allowed: false
```

Validator expectation:

```text
Expected future profile: candidate_acceptance
Expected result if used as Reading generation target: BLOCKED_BY_SCOPE
Actual validator_executed: false
```

---

## 6. Package-Level Candidate Gate

Package-level status:

```text
candidate_only_documentation
```

Package-level rules:

```text
- No item may be promoted by package inclusion.
- No item may become learner-facing by package inclusion.
- No item may claim validator PASS because no validator has executed.
- No item may claim official Cambridge equivalence.
- No synthetic source may become authority content.
```

Expected future validator profile:

```text
sample_package_acceptance
```

Required future layers:

```text
- candidate_acceptance layers for every child item
- composite_set checks if future package includes reading_comprehension_set
- promotion_validator at package level
```

---

## 7. Contract Coverage Matrix

| Contract area | Covered by sample(s) | Notes |
|---|---|---|
| choice_id | P2S6_ITEM_001, P2S6_ITEM_003, P2S6_ITEM_005 | stable choice_id required |
| matching_pairs | P2S6_ITEM_002 | reuse_policy recorded |
| boolean | P2S6_ITEM_004 | no distractor set; false rationale rule recorded |
| accepted_answer_set | P2S6_ITEM_006 | finite one-word answer |
| distractor_set | P2S6_ITEM_001, P2S6_ITEM_003, P2S6_ITEM_005 | reason_not_correct required |
| source_trace | all reading samples | synthetic fixtures only |
| answer_evidence | all reading samples | evidence span or metadata reference required |
| generated candidate boundary | all samples | candidate_only, non-promoted |
| writing boundary | P2S6_ITEM_007 | blocked from Reading generation |
| promotion control | package level | promotion_allowed false |

Coverage gaps intentionally deferred:

```text
- ordered_sequence sample
- composite_set sample
- picture_text_matching sample
- Cambridge official source manifest sample
- validator output fixture
```

---

## 8. Future Validator Readiness Notes

P2-S6 prepares P2-S7 ReadbackQA by giving the readback task concrete objects to inspect manually.

P2-S7 should check:

```text
1. Whether every sample has candidate_only / learner_facing_allowed false / promotion_allowed false.
2. Whether answer_model family is explicit in every sample.
3. Whether each answer has evidence or boundary justification.
4. Whether each distractor has reason_not_correct where distractor_set exists.
5. Whether open cloze uses bounded accepted_answer_set.
6. Whether writing_boundary sample is blocked from Reading generation.
7. Whether no official Cambridge item is reproduced.
8. Whether no runtime, validator, tests, generated JSON artifact, or site file was created.
```

---

## 9. Non-Goals

This task does not define or implement:

```text
- validator code
- validator CLI
- validator tests
- JSON schema file
- standalone generated JSON package
- production sample item bank
- learner-facing quiz renderer
- runtime answer checker
- official source manifest
- Cambridge asset ingestion
- promotion workflow implementation
- human review workflow implementation
- final authority content
```

---

## 10. Deferred Issues Register

```text
issue_id: P2-S6-U1-VALIDATOR-EXECUTION
severity: normal
affected_file_or_artifact: future validator run report
classification: FUTURE_WORK
why_deferred: P2-S6 creates documentation-only candidates and no validator code exists yet.
recommended_future_task: future E4S-P2 validator implementation task after P2 readback QA
blocks_current_task: no
```

```text
issue_id: P2-S6-U2-STANDALONE-SAMPLE-PACKAGE-JSON
severity: normal
affected_file_or_artifact: future generated or curated JSON sample package
classification: FUTURE_WORK
why_deferred: P2-S6 avoids creating standalone generated JSON artifacts.
recommended_future_task: future E4S-P2 sample package implementation task after schema/validator approval
blocks_current_task: no
```

```text
issue_id: P2-S6-U3-OFFICIAL-SOURCE-MANIFEST
severity: normal
affected_file_or_artifact: future source manifest
classification: FUTURE_WORK
why_deferred: P2-S6 uses synthetic design fixtures and does not ingest official sources.
recommended_future_task: future E4S-P2 source manifest design / implementation task
blocks_current_task: no
```

```text
issue_id: P2-S6-U4-COVERAGE-GAPS
severity: normal
affected_file_or_artifact: future sample package expansion
classification: FUTURE_WORK
why_deferred: P2-S6 intentionally covers representative contracts only.
recommended_future_task: future E4S-P2 candidate sample package expansion after P2-S7
blocks_current_task: no
```

```text
issue_id: P2-S7-READBACK-QA
severity: normal
affected_file_or_artifact: future Phase 2 readback QA
classification: FUTURE_WORK
why_deferred: Readback QA is the next planned subtask after this candidate-only package.
recommended_future_task: E4S-P2-S7_Phase2ReadbackQA
blocks_current_task: no
```

---

## 11. Gate & Distance Update

### Gate Metrics

```text
[PASS] P2-S1 assessment pattern contract design scan exists.
[PASS] P2-S2 Cambridge YLE pattern mapping design scan exists.
[PASS] P2-S3 KET / A2 Key reading pattern mapping design scan exists.
[PASS] P2-S4 distractor policy and answer model design scan exists.
[PASS] P2-S5 assessment pattern validator contract design scan exists.
[PASS] P2-S6 deliverable path is defined.
[PASS] Candidate-only package status is declared.
[PASS] learner_facing_allowed is false at package level.
[PASS] promotion_allowed is false at package level.
[PASS] validator_executed is false.
[PASS] official_exam_content_used is false.
[PASS] synthetic design fixture boundary is declared.
[PASS] Multiple-choice sample is defined.
[PASS] Matching sample is defined.
[PASS] Multiple-choice cloze sample is defined.
[PASS] Boolean picture-scene sample is defined.
[PASS] Dialogue-response choice sample is defined.
[PASS] Open cloze accepted-answer-set sample is defined.
[PASS] Writing-boundary sample is defined.
[PASS] Package-level candidate gate is defined.
[PASS] Contract coverage matrix is defined.
[PASS] P2-S7 readback readiness notes are defined.
[PASS] Validator execution is deferred.
[PASS] Standalone JSON package is deferred.
[PASS] Official source manifest is deferred.
[PASS] No runtime code is created.
[PASS] No validator code is created.
[PASS] No test is created.
[PASS] No student-facing HTML is created.
[PASS] No learner record is created.
[PASS] No candidate is promoted.
```

### Distance Vector

```text
Total Distance for Phase 2:
D_P2 = 1 sub-task left after this candidate-only sample package

Current Sub-task Status:
E4S-P2-S6_AssessmentPatternSamplePackage_CandidateOnly -> COMPLETED

Remaining:
P2-S7  Phase2ReadbackQA                                   NEXT
```

### Phase 2 Current Status

```text
E4S-P2_STATUS = ASSESSMENT_PATTERN_SAMPLE_PACKAGE_CANDIDATE_ONLY_COMPLETED
```

---

## 12. Next Shortest Step

```text
NEXT_SHORT_STEP:
E4S-P2-S7_Phase2ReadbackQA
```

唯一執行動作：

```text
請下達：
E4S-P2-S7_Phase2ReadbackQA
```

Next task boundary:

```text
P2-S7 may perform documentation readback QA across P2-S0 through P2-S6.
P2-S7 must not implement validator code, tests, generated JSON, runtime answer checking, student-facing HTML, or promotion.
```

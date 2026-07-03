# E4S-P2-S4 Distractor Policy and Answer Model Design Scan

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
E4S-P2-S4_DistractorPolicyAndAnswerModel_DesignScan
```

本次任務類型：

```text
DesignScan only
```

核心資料來源與排序依據（Data Sources）：

```text
1. docs/e4s/E4S_P2_KET_READING_PATTERN_MAPPING_DESIGN_SCAN.md
   - P2-S4 is the next shortest step.
   - P2-S4 may define distractor policy and answer model details only.
   - P2-S4 must not implement code, validators, generated JSON, student-facing HTML, or promotion.

2. docs/e4s/E4S_P2_CAMBRIDGE_YLE_PATTERN_MAPPING_DESIGN_SCAN.md
   - Cambridge YLE mapping records distractor and answer-model implications by task family.
   - Generated Cambridge-style items must remain candidate_only.

3. docs/e4s/E4S_P2_ASSESSMENT_PATTERN_CONTRACT_DESIGN_SCAN.md
   - Defines the canonical assessment pattern contract.
   - Requires answer_model to be explicit.
   - Requires answer evidence.
   - Requires distractors to be non-correct, non-ambiguous, and level-safe.
   - Requires generated-content promotion control.

4. 重點任務排程.txt
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
docs/e4s/E4S_P2_DISTRACTOR_POLICY_AND_ANSWER_MODEL_DESIGN_SCAN.md
```

本次任務不產出：

```text
- no runtime code
- no tools/*.py
- no validators/*.py
- no tests/*.py
- no generated JSON
- no student-facing HTML
- no learner records
- no schema promotion
- no generated question package
- no sample item bank
```

---

## 2. Required Task Header

```text
Task:
E4S-P2-S4_DistractorPolicyAndAnswerModel_DesignScan

Scope:
Define Phase 2 distractor policy details and answer model details for Reading / Cambridge YLE / A2 Key assessment pattern families.

Allowed files:
docs/e4s/E4S_P2_DISTRACTOR_POLICY_AND_ANSWER_MODEL_DESIGN_SCAN.md

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
- The design must define answer model families, answer normalization, distractor provenance, distractor rejection reasons, ambiguity controls, level-safety controls, and candidate-only generated distractor rules.
- The design must not create validator code or generated question samples.

Warning policy:
Policy gaps may be recorded as deferred issues. They must not expand into implementation.

Generated artifact policy:
Generated artifacts are not allowed in this task.

Runtime impact:
None.

Promotion impact:
None. This task does not promote any answer model, distractor set, generated distractor, sample item, or pattern into final authority.

Stop condition:
Stop after the distractor policy and answer model design-scan document is written and P2-S5 is identified as the next shortest step.

Deferred issues register:
All validator implementation, JSON schema implementation, generated sample packages, and readback QA are deferred.
```

---

## 3. Core Execution

### 3.1 Purpose

P2-S4 turns the earlier contract-level fields into a stricter design policy for:

```text
- how answers are represented
- how answers are normalized
- how distractors are represented
- how distractors are rejected as incorrect
- how ambiguity is blocked
- how generated distractors remain candidate-only
```

This task still does not implement validation.

It defines what a future validator must check.

---

### 3.2 Core Invariants

Every future Phase 2 question item must satisfy these invariants before it can become a candidate item:

```text
1. The answer_model family is explicit.
2. The canonical answer exists when required.
3. The answer evidence span or evidence object exists.
4. Accepted answers are bounded when open text is allowed.
5. Distractors are represented with provenance and rejection reason.
6. Distractors are not also correct.
7. Distractors do not create unresolved ambiguity.
8. Distractors stay within declared level and cognitive-load bounds.
9. Generated distractors remain candidate support material only.
10. Candidate-only artifacts cannot be promoted by implication.
```

---

## 4. Answer Model Contract

### 4.1 Answer Model Families

Phase 2 answer models are restricted to the following families:

| Family | Primary use | Open-ended? | Reading-safe? |
|---|---|---|---|
| exact_text | spelling, single-token cloze | no | yes |
| choice_id | multiple choice, title choice, picture-text choice | no | yes |
| boolean | true/false, yes/no, tick/cross | no | yes |
| ordered_sequence | sentence/story ordering | no | yes |
| matching_pairs | matching tasks | no | yes |
| cloze_tokens | word-box cloze, multi-gap cloze | bounded | yes |
| accepted_answer_set | short answer, open cloze-lite | bounded | yes with strict gate |
| composite_set | reading comprehension set | depends on child models | yes if all child models are safe |
| rubric_scored_response | writing response | yes | no; boundary-only in Phase 2 Reading |

Rules:

```text
- Reading-safe does not mean learner-facing allowed.
- rubric_scored_response is recorded only for official combined Reading/Writing formats such as A2 Key Parts 6–7.
- rubric_scored_response must not be generated, scored, or accepted inside Phase 2 Reading.
```

---

### 4.2 exact_text

Required fields:

```text
family: exact_text
canonical_answer
normalization_policy
answer_evidence
case_sensitive
punctuation_sensitive
allowed_variants
```

Default normalization:

```text
trim_outer_space: true
collapse_internal_space: true
case_sensitive: false
punctuation_sensitive: pattern_specific
```

Acceptance rule:

```text
The normalized learner answer must equal canonical_answer or one of the approved allowed_variants.
```

Blocked cases:

```text
- no canonical_answer
- no normalization_policy
- answer not evidence-backed
- unlimited free-text acceptance
```

---

### 4.3 choice_id

Required fields:

```text
family: choice_id
choice_set
correct_choice_ids
answer_evidence
choice_display_order
choice_randomization_allowed
```

Choice object:

```json
{
  "choice_id": "C1",
  "display_text_or_asset_ref": "...",
  "is_correct": true,
  "evidence_ref": "E1",
  "distractor_ref": null
}
```

Rules:

```text
- primary answer key must be choice_id, not display text.
- single-answer tasks must have exactly one correct_choice_id.
- multi-answer tasks must declare cardinality explicitly.
- randomization may change display order but must not change choice_id.
```

Blocked cases:

```text
- answer key stored only as display text
- duplicate choice_id
- correct choice without evidence
- distractor that also satisfies the evidence
```

---

### 4.4 boolean

Required fields:

```text
family: boolean
truth_value
answer_surface
supporting_evidence
false_rationale_if_false
normalization_policy
```

Allowed answer surfaces:

```text
true_false
yes_no
tick_cross
right_wrong
```

Rules:

```text
- answer_surface defines how the learner sees the task.
- truth_value stores the normalized answer.
- false items need a rationale showing why the statement is false.
```

Blocked cases:

```text
- false item without rationale
- ambiguous image/text claim
- yes/no answer stored as raw string without truth_value
```

---

### 4.5 ordered_sequence

Required fields:

```text
family: ordered_sequence
ordered_item_ids
source_order_trace
allow_partial_credit
sequence_granularity
```

Allowed sequence granularity:

```text
sentence
picture
step
event
paragraph
```

Rules:

```text
- ordering must be grounded in source order, time order, or explicit story order.
- partial credit is not allowed unless a future scoring task defines it.
- each ordered item must be uniquely identified.
```

Blocked cases:

```text
- duplicate ordered item id
- no source_order_trace
- multiple valid orders without explicit allowance
```

---

### 4.6 matching_pairs

Required fields:

```text
family: matching_pairs
left_item_ids
right_item_ids
pair_set
pair_evidence
reuse_policy
```

Reuse policy values:

```text
no_reuse
right_item_may_repeat
left_item_may_repeat
many_to_many_explicit
```

Rules:

```text
- default reuse_policy is no_reuse.
- every required left item must have a valid right item.
- evidence must explain why each pair is correct.
```

Blocked cases:

```text
- matching pair with no evidence
- unmarked repeated right item
- ambiguous pair with two equally valid targets
```

---

### 4.7 cloze_tokens

Required fields:

```text
family: cloze_tokens
gap_ids
canonical_tokens
accepted_tokens
source_gap_context
option_set_if_any
normalization_policy
```

Rules:

```text
- every gap must have one canonical answer.
- accepted_tokens must be bounded.
- word-box cloze answers must come from option_set_if_any.
- open cloze answers require stricter accepted-token review.
```

Blocked cases:

```text
- gap without local context
- unbounded accepted tokens
- answer not supported by source_gap_context
- generated alternative accepted without review
```

---

### 4.8 accepted_answer_set

Required fields:

```text
family: accepted_answer_set
canonical_answer
accepted_answers
rejected_answer_examples_optional
answer_evidence
answer_length_limit
normalization_policy
```

Rules:

```text
- accepted_answers must be finite.
- answer_length_limit must be declared.
- every accepted answer must be evidence-backed or authority-backed.
- short_answer and open_cloze_lite cannot become free writing.
```

Blocked cases:

```text
- accepted_answers = any
- missing answer_length_limit
- no evidence for alternative answer
- response requires rubric scoring
```

---

### 4.9 composite_set

Required fields:

```text
family: composite_set
parent_source_trace
child_item_ids
child_answer_models
set_level_rule
set_level_evidence
```

Rules:

```text
- every child item must have its own answer model.
- every child item must have its own evidence.
- composite_set is valid only if all child answer models are valid.
```

Blocked cases:

```text
- child item without answer model
- child item without evidence
- set-level answer key replacing child-level answer keys
```

---

### 4.10 rubric_scored_response

Boundary status:

```text
writing_boundary_only
```

Required fields if recorded as boundary metadata:

```text
family: rubric_scored_response
prompt_requirements
minimum_word_count
rubric_required_future_task
scoring_allowed: false
learner_facing_allowed: false
```

Rules:

```text
- rubric_scored_response is not Reading-safe for Phase 2 generation.
- it may be recorded because A2 Key Reading/Writing combines Reading and Writing parts.
- it requires a future Writing Authority / Assessment Rubric task.
```

Blocked cases:

```text
- auto-scoring writing response inside Phase 2 Reading
- generated writing prompt inside P2-S4
- learner-facing writing task created by this task
```

---

## 5. Distractor Policy Contract

### 5.1 Distractor Object

Every distractor must use this design shape in future candidate items:

```json
{
  "distractor_id": "D1",
  "display_text_or_asset_ref": "...",
  "provenance": "same_level_vocabulary",
  "reason_for_plausibility": "same topic and same CEFR band",
  "reason_not_correct": "not supported by the source span",
  "level_band": "A1",
  "source_relation": "same_theme_not_answer",
  "ambiguity_risk": "low",
  "generated": true,
  "candidate_only": true
}
```

This is a design target only. It is not a committed JSON schema in this task.

---

### 5.2 Required Distractor Fields

```text
distractor_id
display_text_or_asset_ref
provenance
reason_for_plausibility
reason_not_correct
level_band
source_relation
ambiguity_risk
generated
candidate_only
```

Hard rule:

```text
No reason_not_correct -> invalid distractor.
```

---

### 5.3 Allowed Provenance Values

```text
source_neighbor
same_theme_authority
same_level_vocabulary
same_pattern_family
same_part_competitor
grammar_contrast
semantic_contrast
near_surface_match
generated_candidate
```

Definitions:

| Provenance | Meaning |
|---|---|
| source_neighbor | Comes from nearby source text but is not the answer. |
| same_theme_authority | Comes from an approved same-theme authority list. |
| same_level_vocabulary | Same CEFR / vocabulary band as the answer. |
| same_pattern_family | Same assessment pattern family. |
| same_part_competitor | Plausible within the same Cambridge YLE / A2 Key part shape. |
| grammar_contrast | Contrasts tense, agreement, preposition, pronoun, or structure. |
| semantic_contrast | Similar semantic field but wrong meaning in context. |
| near_surface_match | Looks similar by spelling or phrase surface but is wrong. |
| generated_candidate | Produced by AI or generator and remains candidate-only. |

---

### 5.4 Source Relation Values

```text
same_source_wrong_span
same_text_wrong_paragraph
same_scene_wrong_object
same_theme_not_answer
same_level_not_contextual
opposite_meaning
near_synonym_wrong_context
grammar_form_wrong_context
outside_source_not_allowed
```

Rules:

```text
- literal items should prefer same_source_wrong_span, same_scene_wrong_object, or same_theme_not_answer.
- vocabulary cloze may use grammar_form_wrong_context or near_synonym_wrong_context.
- outside_source_not_allowed is a rejection label, not a recommended distractor source.
```

---

### 5.5 Ambiguity Risk Scale

Allowed values:

```text
low
medium
high
blocked
```

Rules:

```text
- low: acceptable if all other checks pass.
- medium: acceptable only with explicit reason_not_correct and evidence contrast.
- high: blocked unless a future human-review workflow approves it.
- blocked: never accepted.
```

Default:

```text
Generated distractors default to medium until validated.
```

---

### 5.6 Distractor Count Policy

| Pattern family | Default count | Minimum | Maximum | Notes |
|---|---:|---:|---:|---|
| multiple_choice | 2–3 distractors | 2 | 4 | single correct answer unless cardinality says otherwise |
| title_choice | 2 distractors | 2 | 3 | whole-text gist required |
| true_false / yes_no | 0 distractors | 0 | 0 | false rationale required instead |
| matching_pairs | extra unmatched options optional | 0 | pattern-specific | reuse_policy required |
| word_box_cloze | unused options optional | 0 | pattern-specific | options must be listed |
| open_cloze_lite | 0 distractors | 0 | 0 | accepted answer set required |
| ordered_sequence | 0 distractors | 0 | 0 | order ambiguity check required |

Rules:

```text
- not every assessment pattern has distractors.
- false rationale, unused options, and rejected answers are not always distractors.
- the future validator must distinguish distractor_set from option_set and accepted_answer_set.
```

---

### 5.7 Distractor Rejection Rules

A distractor is blocked if any of the following is true:

```text
- it is also correct under the answer evidence.
- it has no reason_not_correct.
- it has no provenance.
- it creates unresolved ambiguity.
- it exceeds declared CEFR / vocabulary / cognitive-load band without warning.
- it requires outside knowledge for a literal item.
- it contradicts the source in a way that changes the task type.
- it turns the item into writing, listening, speaking, or adaptive diagnosis.
- it is generated but not marked candidate_only.
```

---

## 6. Pattern-Specific Distractor and Answer Rules

### 6.1 true_false / yes_no

Answer model:

```text
boolean
```

Distractor model:

```text
none
```

Required control:

```text
false_rationale_if_false
```

Rules:

```text
- do not create distractor objects.
- false statement must have a rationale and evidence contrast.
- image-based yes/no claims must be grounded in scene metadata.
```

---

### 6.2 multiple_choice

Answer model:

```text
choice_id
```

Distractor model:

```text
distractor_set required
```

Rules:

```text
- correct choice must have evidence.
- every distractor must have reason_not_correct.
- display order may be randomized only if choice_id remains stable.
- distractors must match task focus: main message, detail, title, grammar, or vocabulary.
```

---

### 6.3 matching

Answer model:

```text
matching_pairs
```

Distractor model:

```text
unmatched_options optional
```

Rules:

```text
- reuse_policy must be explicit.
- every matched pair must have pair evidence.
- unmatched options must be marked as option_not_used, not as answer distractors unless a future implementation chooses that representation.
```

---

### 6.4 gap_fill / cloze

Answer model:

```text
cloze_tokens | accepted_answer_set | choice_id
```

Distractor model depends on task:

```text
word_box_cloze -> unused_options
multiple_choice_cloze -> distractor_set
open_cloze_lite -> no distractor_set; accepted_answer_set required
```

Rules:

```text
- local gap context is mandatory.
- grammar/vocabulary focus should be declared.
- accepted answers must be finite.
- generated alternatives require review and evidence.
```

---

### 6.5 short_answer

Answer model:

```text
accepted_answer_set
```

Distractor model:

```text
none by default
```

Rules:

```text
- answer length limit must be declared.
- accepted answers must be bounded.
- rejected_answer_examples may be stored for QA but are not required as distractors.
```

---

### 6.6 reading_comprehension_set

Answer model:

```text
composite_set
```

Distractor model:

```text
child_item_specific
```

Rules:

```text
- set-level item must not hide child-level answer models.
- each child question owns its own answer and distractor policy.
- parent source trace must be preserved.
```

---

### 6.7 writing_boundary_only

Answer model:

```text
rubric_scored_response
```

Distractor model:

```text
not applicable
```

Rules:

```text
- writing boundary records are not Reading generation targets.
- no auto-scoring is allowed.
- no distractor policy applies until a future writing assessment task defines one.
```

---

## 7. Candidate-Only Generated Distractor Rule

Generated distractors may be useful for future candidate packages, but they are never authority by default.

Required generated distractor fields:

```text
generated: true
candidate_only: true
generation_method: required_future_field
generation_source_context: required_future_field
human_review_status: not_reviewed | reviewed | rejected
```

Rules:

```text
- generated distractors default to human_review_status = not_reviewed.
- generated distractors must not be promoted with the parent item.
- generated distractors require explicit future review or validator approval.
- generated distractors with medium/high ambiguity risk must not become learner-facing.
```

---

## 8. Future Validator Implications

P2-S4 does not implement validators. It defines future validator implications:

```text
1. Answer model validator
   - Checks allowed family, required fields, cardinality, normalization, and evidence.

2. Choice validator
   - Checks stable choice_id, correct_choice_ids, display order, and evidence.

3. Accepted answer validator
   - Checks finite accepted answers, answer length limit, and evidence support.

4. Distractor validator
   - Checks required distractor fields, provenance, reason_not_correct, level band, source relation, and ambiguity risk.

5. Option-set validator
   - Distinguishes distractor_set from option_set, unused_options, and accepted_answer_set.

6. Ambiguity validator
   - Blocks distractors that are also correct or unresolved.

7. Generated-content validator
   - Ensures generated distractors remain candidate_only and not promoted by implication.

8. Writing-boundary validator
   - Blocks rubric_scored_response from Reading generation.

9. Promotion validator
   - Blocks candidate-only artifacts from becoming final authority without future promotion task.
```

---

## 9. Non-Goals

This task does not define or implement:

```text
- validator code
- JSON schema file
- generated distractor set
- generated question package
- sample item bank
- learner-facing quiz renderer
- answer checker runtime
- writing rubric scoring
- Cambridge asset ingestion
- source manifest
- official PDF storage
- adaptive sequencing
- learner error diagnosis
```

---

## 10. Deferred Issues Register

```text
issue_id: P2-S5-VALIDATOR-CONTRACT
severity: normal
affected_file_or_artifact: future validator contract
classification: FUTURE_WORK
why_deferred: P2-S4 defines validation obligations only; validator contract is separate.
recommended_future_task: E4S-P2-S5_AssessmentPatternValidatorContract_DesignScan
blocks_current_task: no
```

```text
issue_id: P2-S6-SAMPLE-PACKAGE
severity: normal
affected_file_or_artifact: future candidate sample package
classification: FUTURE_WORK
why_deferred: P2-S4 must not generate sample question or distractor packages.
recommended_future_task: E4S-P2-S6_AssessmentPatternSamplePackage_CandidateOnly
blocks_current_task: no
```

```text
issue_id: P2-S4-U1-ANSWER-MODEL-SCHEMA
severity: normal
affected_file_or_artifact: future JSON schema
classification: FUTURE_WORK
why_deferred: P2-S4 is a design scan, not schema implementation.
recommended_future_task: E4S-P2-S5_AssessmentPatternValidatorContract_DesignScan
blocks_current_task: no
```

```text
issue_id: P2-S4-U2-GENERATED-DISTRACTOR-REVIEW-WORKFLOW
severity: normal
affected_file_or_artifact: future generated distractor review workflow
classification: FUTURE_WORK
why_deferred: Generated distractor review workflow requires implementation and QA outside this design scan.
recommended_future_task: future E4S-P2 generated-content QA task
blocks_current_task: no
```

```text
issue_id: P2-S4-U3-WRITING-RUBRIC-BOUNDARY
severity: normal
affected_file_or_artifact: future Writing Authority / Assessment Rubric design
classification: FUTURE_WORK
why_deferred: rubric_scored_response is boundary-only for Reading Phase 2.
recommended_future_task: E4S-WRITING-S0_WritingAssessmentRubricBoundary_DesignScan
blocks_current_task: no
```

---

## 11. Gate & Distance Update

### Gate Metrics

```text
[PASS] P2-S1 assessment pattern contract design scan exists.
[PASS] P2-S2 Cambridge YLE pattern mapping design scan exists.
[PASS] P2-S3 KET / A2 Key reading pattern mapping design scan exists.
[PASS] P2-S4 deliverable path is defined.
[PASS] Answer model families are detailed.
[PASS] Answer normalization policy is defined.
[PASS] choice_id stability rule is defined.
[PASS] boolean false-rationale rule is defined.
[PASS] matching reuse_policy rule is defined.
[PASS] cloze accepted-token boundedness rule is defined.
[PASS] accepted_answer_set finite-answer rule is defined.
[PASS] composite_set child-answer rule is defined.
[PASS] rubric_scored_response is boundary-only.
[PASS] Distractor object shape is defined.
[PASS] Required distractor fields are defined.
[PASS] Distractor provenance values are defined.
[PASS] Distractor source relation values are defined.
[PASS] Ambiguity risk scale is defined.
[PASS] Distractor rejection rules are defined.
[PASS] Candidate-only generated distractor rule is defined.
[PASS] Validator implications are documented as future work only.
[PASS] No runtime code is created.
[PASS] No validator is created.
[PASS] No test is created.
[PASS] No generated JSON is created.
[PASS] No student-facing HTML is created.
[PASS] No learner record is created.
[PASS] No candidate is promoted.
```

### Distance Vector

```text
Total Distance for Phase 2:
D_P2 = 3 sub-tasks left after this design scan

Current Sub-task Status:
E4S-P2-S4_DistractorPolicyAndAnswerModel_DesignScan -> COMPLETED

Remaining:
P2-S5  AssessmentPatternValidatorContract_DesignScan      NEXT
P2-S6  AssessmentPatternSamplePackage_CandidateOnly       DEFERRED
P2-S7  Phase2ReadbackQA                                   DEFERRED
```

### Phase 2 Current Status

```text
E4S-P2_STATUS = DISTRACTOR_POLICY_AND_ANSWER_MODEL_DESIGN_SCAN_COMPLETED
```

---

## 12. Next Shortest Step

```text
NEXT_SHORT_STEP:
E4S-P2-S5_AssessmentPatternValidatorContract_DesignScan
```

唯一執行動作：

```text
請下達：
E4S-P2-S5_AssessmentPatternValidatorContract_DesignScan
```

Next task boundary:

```text
P2-S5 may define future validator contract only.
P2-S5 must not implement validator code, tests, generated JSON, student-facing HTML, or promotion.
```

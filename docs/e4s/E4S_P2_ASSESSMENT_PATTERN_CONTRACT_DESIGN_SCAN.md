# E4S-P2-S1 Assessment Pattern Contract Design Scan

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
E4S-P2-S1_AssessmentPatternContract_DesignScan
```

本次任務類型：

```text
DesignScan only
```

核心資料來源與排序依據（Data Sources）：

```text
1. docs/e4s/E4S_P2_ASSESSMENT_PATTERN_EXPANSION_LAUNCH_PREFLIGHT.md
   - P2-S1 is the next shortest step.
   - P2-S1 may create only this design-scan document.
   - P2-S1 must define assessment pattern contracts but must not implement code or generated artifacts.

2. RAZ-AW-V1 Status Snapshot.txt
   - E4S-P2 = Assessment Pattern Expansion.
   - Phase 2 expands Reading patterns toward Cambridge / worksheet / formal assessment patterns.
   - V2 focus is contract standardization, not more generated questions.

3. RAZ-AW-S11 Implementation.txt
   - Reading System V2 = Assessment pattern expansion.
   - V2 must define question_type contract, answer_model, distractor policy, validation rule, difficulty rule, and source requirement.
   - V2 must not do learner adaptive, error diagnosis, writing generation, listening audio, or speaking scoring.

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
docs/e4s/E4S_P2_ASSESSMENT_PATTERN_CONTRACT_DESIGN_SCAN.md
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
```

---

## 2. Required Task Header

```text
Task:
E4S-P2-S1_AssessmentPatternContract_DesignScan

Scope:
Define the design contract for Phase 2 assessment patterns.

Allowed files:
docs/e4s/E4S_P2_ASSESSMENT_PATTERN_CONTRACT_DESIGN_SCAN.md

Forbidden files:
tools/*
validators/*
tests/*
output/*
generated/*
site/*
learner_state/*

Current-task blockers:
- P2-S0 must exist.
- P2-S1 deliverable path must be unique.
- The design must include canonical pattern object, question_type enum, answer_model families, distractor policy, evidence/source trace requirements, validation matrix, difficulty tagging fields, and generated-content promotion control.

Warning policy:
Documentation warnings may be recorded as future work. They must not expand into implementation.

Generated artifact policy:
Generated artifacts are not allowed in this task.

Runtime impact:
None.

Promotion impact:
None. This task does not promote any candidate pattern or question item into final authority.

Stop condition:
Stop after the design-scan document is written and P2-S2 is identified as the next shortest step.

Deferred issues register:
All implementation, validator, sample package, Cambridge mapping, KET mapping, and QA work is deferred.
```

---

## 3. Core Execution

### 3.1 Purpose

Phase 2 must not begin by producing more questions.

Phase 2 begins by defining a stable assessment pattern contract so that later Reading / Cambridge / worksheet items can be:

```text
- source-grounded
- answerable
- evidence-backed
- validator-readable
- difficulty-tagged
- candidate-only unless explicitly promoted
```

This contract is a design boundary, not an executable schema.

---

### 3.2 Core Definitions

#### Assessment Pattern

An `assessment_pattern` is the reusable structure of a question type.

It defines:

```text
- what the student sees
- how the answer is represented
- what source evidence is required
- what distractors are allowed
- what validators must later check
- what difficulty metadata must be attached
```

It does not contain a final learner-facing question package.

#### Question Item

A `question_item` is one instantiated question created from an assessment pattern.

Example relationship:

```text
assessment_pattern = multiple_choice_literal_what
question_item = one concrete question generated from one source sentence or passage
```

P2-S1 does not create question items.

#### Practice Package

A `practice_package` is a group of question items.

P2-S1 does not create practice packages.

#### Source Evidence

`source_evidence` is the traceable source span, page unit, sentence candidate, passage unit, or content unit that supports the answer.

Every later Phase 2 item must have evidence. If evidence cannot be attached, the item must remain invalid.

---

### 3.3 Canonical Assessment Pattern Object

The proposed canonical object is:

```json
{
  "assessment_pattern_id": "AP_P2_000001",
  "pattern_family": "multiple_choice",
  "question_type": "multiple_choice_literal",
  "skill_area": "reading",
  "phase": "E4S-P2",
  "status": "contract_candidate",
  "learner_facing_allowed": false,

  "input_requirements": {
    "source_unit_types": ["sentence", "page_unit", "passage_unit"],
    "minimum_sentence_count": 1,
    "maximum_sentence_count": 8,
    "requires_answer_evidence_span": true,
    "requires_source_trace": true
  },

  "prompt_contract": {
    "prompt_surface": "text",
    "stem_policy": "source_grounded",
    "instruction_language": "zh-TW_or_en",
    "allowed_prompt_transforms": ["literal_question", "controlled_rephrase"]
  },

  "answer_model": {
    "family": "choice_id",
    "cardinality": "single",
    "requires_canonical_answer": true,
    "requires_accepted_answers": false
  },

  "distractor_policy": {
    "required": true,
    "minimum_count": 2,
    "maximum_count": 4,
    "source_grounded_distractors_allowed": true,
    "generated_distractors_allowed": true,
    "must_not_contradict_source": true,
    "must_match_level_band": true
  },

  "difficulty_contract": {
    "cefr_level_required": true,
    "raz_level_hint_allowed": true,
    "cambridge_path_hint_allowed": true,
    "cognitive_load_required": true
  },

  "validation_contract": {
    "structural_validation_required": true,
    "answer_validation_required": true,
    "evidence_validation_required": true,
    "difficulty_validation_required": true,
    "promotion_validation_required": true
  },

  "promotion_policy": {
    "default_status": "candidate_only",
    "auto_promotion_allowed": false,
    "requires_future_promotion_task": true
  }
}
```

This object is a design target only. It is not a committed JSON schema in this task.

---

### 3.4 Canonical Field Groups

#### Identity Fields

```text
assessment_pattern_id
pattern_family
question_type
skill_area
phase
status
version
```

Rules:

```text
- assessment_pattern_id must be stable.
- question_type must come from the controlled enum.
- status must not imply authority promotion.
```

#### Source Fields

```text
source_unit_types
source_trace_required
answer_evidence_span_required
allowed_source_authority
blocked_source_authority
```

Rules:

```text
- every later question item must preserve source trace.
- every later answer must have evidence.
- generated content cannot replace source evidence.
```

#### Prompt Fields

```text
prompt_surface
stem_policy
instruction_language
allowed_prompt_transforms
blocked_prompt_transforms
```

Rules:

```text
- prompt may rephrase source only if the answer remains evidence-backed.
- prompt must not introduce facts not present in the source.
```

#### Answer Fields

```text
answer_model.family
answer_model.cardinality
canonical_answer
accepted_answers
answer_evidence_span
answer_normalization_policy
```

Rules:

```text
- answer_model must be explicit.
- exact-text answers must define normalization policy.
- multiple-choice answers must use choice_id rather than raw display text as the primary key.
```

#### Distractor Fields

```text
distractor_policy.required
distractor_policy.minimum_count
distractor_policy.maximum_count
distractor_policy.provenance
distractor_policy.level_match_required
distractor_policy.semantic_distance_policy
```

Rules:

```text
- distractors must not be accidentally correct.
- distractors must not contradict the source in a way that creates ambiguity.
- distractors must be level-safe.
```

#### Difficulty Fields

```text
cefr_level
raz_level_hint
cambridge_path_hint
cognitive_load
source_length_band
vocabulary_load
answer_inference_level
```

Rules:

```text
- CEFR is difficulty authority, not learning path authority.
- Cambridge path hint may be used for child-learning progression.
- difficulty must include cognitive load, not only level label.
```

#### Validation Fields

```text
structural_validation
answer_validation
evidence_validation
distractor_validation
difficulty_validation
promotion_validation
```

Rules:

```text
- missing source trace blocks acceptance.
- missing answer evidence blocks acceptance.
- invalid distractors block acceptance.
- candidate-only artifacts must not be promoted by implication.
```

---

### 3.5 Question Type Enum V1 for Phase 2

The controlled enum begins with the Phase 1 Reading V1 types and adds Phase 2 pattern families.

#### Carried from Reading V1

```text
literal_who
literal_what
literal_where
true_false
sentence_ordering
cloze_vocabulary
```

#### Added for Phase 2 Contract Design

```text
matching
multiple_choice
gap_fill
short_answer
picture_text_matching
reading_comprehension_set
cambridge_yle_pattern_placeholder
ket_reading_pattern_placeholder
```

These are contract-level names only. They do not create items.

---

### 3.6 Pattern Family Rules

#### matching

Purpose:

```text
Match text to text, text to picture, question to answer, sentence to source unit, or vocabulary to meaning.
```

Required answer model:

```text
matching_pairs
```

Minimum validation requirements:

```text
- every left item has one valid right item
- no duplicate valid target unless explicitly allowed
- all pairs are supported by source or approved authority
```

#### multiple_choice

Purpose:

```text
Select one or more correct choices from a finite option set.
```

Required answer model:

```text
choice_id
```

Minimum validation requirements:

```text
- correct option has evidence
- distractors are not also correct
- options are level-safe
```

#### gap_fill

Purpose:

```text
Complete a source-grounded sentence or passage gap.
```

Required answer model:

```text
exact_text_or_token_set
```

Minimum validation requirements:

```text
- gap answer comes from source or controlled authority
- normalization policy is explicit
- grammar and vocabulary gates are declared for later validator work
```

#### short_answer

Purpose:

```text
Answer a source-grounded literal or near-literal question using a short phrase.
```

Required answer model:

```text
accepted_answer_set
```

Minimum validation requirements:

```text
- answer evidence span exists
- accepted answers are bounded
- open-ended writing is not allowed in this pattern
```

#### picture_text_matching

Purpose:

```text
Match a picture, picture label, or visual description to a text source.
```

Required answer model:

```text
choice_id_or_matching_pairs
```

Minimum validation requirements:

```text
- image source trace is required if real images are used
- generated image prompts are candidate-only
- no image asset is created in P2-S1
```

#### reading_comprehension_set

Purpose:

```text
Bundle multiple source-grounded questions under one passage or page unit.
```

Required answer model:

```text
composite_set
```

Minimum validation requirements:

```text
- each child question has its own answer model
- each child question has its own evidence
- set-level source trace must point to the parent passage or page unit
```

#### cambridge_yle_pattern_placeholder

Purpose:

```text
Reserve a future mapping space for Starters / Movers / Flyers assessment patterns.
```

Rules:

```text
- no direct mapping is implemented in P2-S1
- future P2-S2 must define the exact YLE pattern matrix
- placeholder cannot be used for generation
```

#### ket_reading_pattern_placeholder

Purpose:

```text
Reserve a future mapping space for KET-style reading patterns.
```

Rules:

```text
- no direct KET mapping is implemented in P2-S1
- future P2-S3 must define the exact KET pattern matrix
- placeholder cannot be used for generation
```

---

### 3.7 Answer Model Families

Phase 2 contracts must use one of these answer model families:

```text
exact_text
choice_id
boolean
ordered_sequence
matching_pairs
cloze_tokens
accepted_answer_set
composite_set
```

#### exact_text

Use for:

```text
gap_fill
cloze_vocabulary
```

Requires:

```text
canonical_answer
normalization_policy
answer_evidence_span
```

#### choice_id

Use for:

```text
multiple_choice
picture_text_matching
```

Requires:

```text
correct_choice_ids
choice_set
answer_evidence_span
```

#### boolean

Use for:

```text
true_false
```

Requires:

```text
truth_value
supporting_evidence_span
false_statement_rationale_if_false
```

#### ordered_sequence

Use for:

```text
sentence_ordering
story_ordering
```

Requires:

```text
ordered_item_ids
source_order_trace
```

#### matching_pairs

Use for:

```text
matching
picture_text_matching
```

Requires:

```text
pair_set
left_item_ids
right_item_ids
pair_evidence
```

#### cloze_tokens

Use for:

```text
gap_fill with multiple blanks
```

Requires:

```text
gap_ids
canonical_tokens
accepted_tokens
normalization_policy
```

#### accepted_answer_set

Use for:

```text
short_answer
```

Requires:

```text
canonical_answer
accepted_answers
rejected_answer_examples_optional
answer_evidence_span
```

#### composite_set

Use for:

```text
reading_comprehension_set
```

Requires:

```text
child_question_items
child_answer_models
parent_source_trace
```

---

### 3.8 Distractor Policy

Distractors are not decoration. They are part of the assessment contract.

Required fields:

```text
distractor_id
display_text_or_asset_ref
provenance
reason_for_plausibility
reason_not_correct
level_band
source_relation
```

Allowed provenance values:

```text
source_neighbor
same_theme_authority
same_level_vocabulary
same_pattern_family
generated_candidate
```

Blocked distractor types:

```text
- distractor that is also correct
- distractor with no reason_not_correct
- distractor that exceeds the declared level band without warning
- distractor that relies on knowledge outside the source when the item is literal
- distractor that changes the task into writing, listening, speaking, or adaptive diagnosis
```

Default rule:

```text
Distractors may be generated only as candidate support material. Generated distractors do not become authority.
```

---

### 3.9 Source Evidence Contract

Every later question item must carry:

```text
source_type
source_id
source_unit_id
source_location
source_text_or_asset_ref
answer_evidence_span
source_authority_status
```

Recommended source types:

```text
raz_sentence
raz_page_unit
raz_passage_unit
cambridge_pattern_reference
worksheet_pattern_reference
authority_vocabulary_entry
authority_grammar_entry
authority_pattern_entry
```

Required rule:

```text
No answer evidence -> no accepted question item.
```

---

### 3.10 Difficulty Contract

Difficulty must not be represented by CEFR alone.

Required fields:

```text
cefr_level
reading_level_hint
cambridge_path_hint
cognitive_load
source_length_band
vocabulary_load
syntax_load
answer_location_type
inference_level
```

Recommended values:

```text
cognitive_load: low | medium | high
source_length_band: sentence | page_unit | short_passage | passage_set
answer_location_type: explicit_span | paraphrase_span | cross_sentence
inference_level: literal | near_literal | local_inference
```

Phase 2 default:

```text
Only literal, near_literal, and local_inference may be designed.
Global inference and open response must be deferred.
```

---

### 3.11 Validation Requirement Matrix

| Validation Layer | Purpose | Blocks P2 Candidate Acceptance? |
|---|---|---|
| structural_validation | Required fields and enum values exist | yes |
| answer_validation | Answer model is complete and answerable | yes |
| evidence_validation | Answer has source evidence | yes |
| distractor_validation | Distractors are not correct / ambiguous | yes |
| difficulty_validation | Level and cognitive load fields exist | yes |
| source_trace_validation | Source identity and location are traceable | yes |
| promotion_validation | Candidate is not promoted by implication | yes |
| scope_validation | Item does not become writing/listening/speaking/adaptive | yes |

No validator is implemented in this task. This matrix defines future validator obligations.

---

### 3.12 Promotion Control

Default artifact status:

```text
candidate_only
```

Allowed statuses:

```text
contract_candidate
design_accepted
implementation_ready
candidate_only
promotion_blocked
promoted_by_future_task
```

Forbidden status transitions in P2-S1:

```text
contract_candidate -> implementation_ready
candidate_only -> promoted_by_future_task
any status -> learner_facing_allowed
```

Promotion requires a future explicit task.

---

### 3.13 Non-Goals

This task does not define or implement:

```text
- Cambridge YLE exact part-by-part mapping
- KET exact part-by-part mapping
- generated sample question package
- JSON schema file
- validator code
- quiz renderer
- answer checker
- learner error tagging
- adaptive sequencing
- listening / speaking / writing bridge
```

---

### 3.14 Deferred Issues Register

```text
issue_id: P2-S2-CAMBRIDGE-YLE-MAPPING
severity: normal
affected_file_or_artifact: future docs/e4s/E4S_P2_CAMBRIDGE_YLE_PATTERN_MAPPING_DESIGN_SCAN.md
classification: FUTURE_WORK
why_deferred: P2-S1 only defines the general contract.
recommended_future_task: E4S-P2-S2_CambridgeYLEPatternMapping_DesignScan
blocks_current_task: no
```

```text
issue_id: P2-S3-KET-MAPPING
severity: normal
affected_file_or_artifact: future docs/e4s/E4S_P2_KET_READING_PATTERN_MAPPING_DESIGN_SCAN.md
classification: FUTURE_WORK
why_deferred: KET-specific pattern mapping is outside the generic contract design.
recommended_future_task: E4S-P2-S3_KETReadingPatternMapping_DesignScan
blocks_current_task: no
```

```text
issue_id: P2-S4-DISTRACTOR-DETAIL-POLICY
severity: normal
affected_file_or_artifact: future distractor policy design
classification: FUTURE_WORK
why_deferred: P2-S1 defines required fields only; detailed distractor generation rules need a separate design.
recommended_future_task: E4S-P2-S4_DistractorPolicyAndAnswerModel_DesignScan
blocks_current_task: no
```

```text
issue_id: P2-S5-VALIDATOR-CONTRACT
severity: normal
affected_file_or_artifact: future validator contract
classification: FUTURE_WORK
why_deferred: P2-S1 defines validation obligations only; validator contract is separate.
recommended_future_task: E4S-P2-S5_AssessmentPatternValidatorContract_DesignScan
blocks_current_task: no
```

```text
issue_id: P2-S6-SAMPLE-PACKAGE
severity: normal
affected_file_or_artifact: future candidate sample package
classification: FUTURE_WORK
why_deferred: P2-S1 must not generate sample question packages.
recommended_future_task: E4S-P2-S6_AssessmentPatternSamplePackage_CandidateOnly
blocks_current_task: no
```

---

## 4. Gate & Distance Update

### Gate Metrics

```text
[PASS] P2-S0 launch preflight exists.
[PASS] P2-S1 deliverable path is defined.
[PASS] Canonical assessment pattern object is defined.
[PASS] question_type enum is defined.
[PASS] answer_model families are defined.
[PASS] distractor policy fields are defined.
[PASS] evidence/source trace requirements are defined.
[PASS] validation requirement matrix is defined.
[PASS] difficulty tagging fields are defined.
[PASS] generated-content promotion rule is defined.
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
D_P2 = 6 sub-tasks left after this design scan

Current Sub-task Status:
E4S-P2-S1_AssessmentPatternContract_DesignScan -> COMPLETED

Remaining:
P2-S2  CambridgeYLEPatternMapping_DesignScan              NEXT
P2-S3  KETReadingPatternMapping_DesignScan                DEFERRED
P2-S4  DistractorPolicyAndAnswerModel_DesignScan          DEFERRED
P2-S5  AssessmentPatternValidatorContract_DesignScan      DEFERRED
P2-S6  AssessmentPatternSamplePackage_CandidateOnly       DEFERRED
P2-S7  Phase2ReadbackQA                                   DEFERRED
```

### Phase 2 Current Status

```text
E4S-P2_STATUS = PHASE_2_CONTRACT_DESIGN_SCAN_COMPLETED
```

---

## 5. Next Shortest Step

```text
NEXT_SHORT_STEP:
E4S-P2-S2_CambridgeYLEPatternMapping_DesignScan
```

唯一執行動作：

```text
請下達：
E4S-P2-S2_CambridgeYLEPatternMapping_DesignScan
```

Next task boundary:

```text
P2-S2 may define Cambridge Starters / Movers / Flyers pattern mapping only.
P2-S2 must not implement code, validators, generated JSON, student-facing HTML, or promotion.
```

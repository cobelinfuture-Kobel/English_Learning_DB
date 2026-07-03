# E4S-P2-S3 KET / A2 Key Reading Pattern Mapping Design Scan

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
E4S-P2-S3_KETReadingPatternMapping_DesignScan
```

本次任務類型：

```text
DesignScan only
```

核心資料來源與排序依據（Data Sources）：

```text
1. docs/e4s/E4S_P2_CAMBRIDGE_YLE_PATTERN_MAPPING_DESIGN_SCAN.md
   - P2-S3 is the next shortest step.
   - P2-S3 may define KET / A2 Key Reading pattern mapping only.
   - P2-S3 must not implement code, validators, generated JSON, student-facing HTML, or promotion.

2. docs/e4s/E4S_P2_ASSESSMENT_PATTERN_CONTRACT_DESIGN_SCAN.md
   - Defines the canonical assessment pattern contract.
   - Defines question_type enum, answer_model families, source evidence requirements, validation matrix, difficulty fields, and promotion control.

3. Cambridge English A2 Key / A2 Key for Schools official exam-format page checked during this task
   - Current Reading and Writing component: 7 parts / 32 questions.
   - Parts 1–5 are about reading.
   - Parts 6–7 are mainly about writing.
   - A2 Key and A2 Key for Schools share the same format.

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
docs/e4s/E4S_P2_KET_READING_PATTERN_MAPPING_DESIGN_SCAN.md
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
- no Cambridge official asset copy
```

---

## 2. Required Task Header

```text
Task:
E4S-P2-S3_KETReadingPatternMapping_DesignScan

Scope:
Define how current A2 Key / A2 Key for Schools Reading and Writing task shapes map into the internal E4S-P2 assessment pattern contract, with emphasis on Reading parts 1–5 and boundary treatment for Writing parts 6–7.

Allowed files:
docs/e4s/E4S_P2_KET_READING_PATTERN_MAPPING_DESIGN_SCAN.md

Forbidden files:
tools/*
validators/*
tests/*
output/*
generated/*
site/*
learner_state/*

Current-task blockers:
- P2-S2 must exist.
- Mapping must use the current A2 Key 7-part / 32-question Reading and Writing format, not the legacy 9-part / 56-question KET format.
- Mapping must cover A2 Key Reading and Writing Parts 1–7 at design-contract level.
- Mapping must distinguish Reading parts from Writing-output parts.
- Mapping must classify exact implementation work as future work.

Warning policy:
Official format assumptions must be treated as source-snapshot assumptions until a future source-manifest task stores exact official source references, retrieval date, page line anchors, and use policy.

Generated artifact policy:
Generated artifacts are not allowed in this task.

Runtime impact:
None.

Promotion impact:
None. This task does not promote any A2 Key pattern, sample item, or generated item into final authority.

Stop condition:
Stop after the KET / A2 Key pattern mapping design-scan document is written and P2-S4 is identified as the next shortest step.

Deferred issues register:
All implementation, validator, sample package, official asset ingestion, license policy, and QA work is deferred.
```

---

## 3. Core Execution

### 3.1 Purpose

This task maps current Cambridge A2 Key / A2 Key for Schools Reading and Writing task shapes into the E4S-P2 internal assessment pattern contract.

This mapping is not a question bank.

It answers:

```text
Which A2 Key Reading and Writing task shapes correspond to which internal question_type, answer_model, source_evidence requirement, difficulty signal, and future validator obligation?
```

It does not answer:

```text
How do we generate actual A2 Key-style questions?
```

That belongs to a later candidate-only sample package task.

---

### 3.2 Source Snapshot Boundary

This design uses the current Cambridge English public format baseline:

```text
A2 Key / A2 Key for Schools Reading and Writing:
- 1 hour
- 7 parts
- 32 questions
- 50% of total marks
- Parts 1–5: Reading
- Parts 6–7: mainly Writing
```

Important boundary:

```text
This task records the mapping design only. A future source-ingestion task should attach exact official sample-paper references, page numbers, URLs, file hashes, and licensing/use policy.
```

Legacy format warning:

```text
Older KET references may mention 9 parts / 56 questions. That legacy format must not be used for E4S-P2-S3 mapping unless an explicit historical-compatibility task is later approved.
```

---

### 3.3 Internal Mapping Principles

A2 Key pattern mapping must follow these principles:

```text
1. Map task shape, not copyrighted content.
2. Preserve source trace for every future item.
3. Treat A2 Key / KET labels as assessment metadata, not final authority.
4. Keep Reading pattern mapping separate from Writing production tasks.
5. Include Writing parts only as boundary mappings because the official component combines Reading and Writing.
6. Do not create learner-facing tasks in this design scan.
7. Do not generate A2 Key-style items until a later implementation task defines exact generator gates.
8. Do not promote generated A2 Key-style items by implication.
```

---

### 3.4 CEFR / Cambridge Path Layer

A2 Key maps into the E4S internal path as follows:

| Cambridge exam | CEFR anchor | Internal path hint | Role in E4S |
|---|---|---|---|
| A2 Key | A2 | Cambridge.A2Key | general A2 reading/writing assessment pattern source |
| A2 Key for Schools | A2 | Cambridge.A2KeyForSchools | school-aged A2 reading/writing assessment pattern source |
| KET legacy label | A2 | Cambridge.KET_LegacyAlias | alias only; do not use legacy format by default |

Rules:

```text
- CEFR anchor is difficulty metadata.
- Cambridge path hint is assessment-pattern metadata.
- KET is treated as a legacy alias for A2 Key unless a historical-format task is explicitly approved.
- Neither CEFR nor Cambridge path hint equals Learning Path Authority.
```

---

## 4. A2 Key Reading and Writing Mapping Matrix

### 4.1 Part 1 — Multiple Choice: Six Short Real-World Texts

External task shape:

```text
Read six short real-world texts for the main message. Each item is multiple choice.
```

Internal mapping:

```text
question_type: multiple_choice
pattern_family: short_real_world_text_main_message
answer_model: choice_id
source_unit_type: short_real_world_text
answer_evidence: whole_short_text_message
cognitive_load: medium
inference_level: near_literal_to_local_inference
source_length_band: short_text
primary_skill: reading_gist
```

Future validator obligations:

```text
- each item must have one correct choice_id.
- answer evidence should point to the full short text or decisive phrase.
- distractors must be plausible but not supported by the main message.
- text type should be recorded when available: sign, notice, message, advertisement, brochure, email snippet, or equivalent.
```

---

### 4.2 Part 2 — Multiple Matching: Seven Questions + Three Short Texts

External task shape:

```text
Read seven questions and three short texts on the same topic, then match the questions to the texts.
```

Internal mapping:

```text
question_type: matching
pattern_family: question_to_short_text_matching
answer_model: matching_pairs
source_unit_type: question_list + short_text_set
answer_evidence: matching_text_span_or_whole_text
cognitive_load: medium_to_high
inference_level: near_literal_to_local_inference
source_length_band: text_set
primary_skill: reading_specific_information
```

Future validator obligations:

```text
- every question must map to one text unless task-specific rule allows reuse.
- each matched text must contain evidence for the question.
- all short texts must share one topic group.
- distractor text selection must not create ambiguity.
```

---

### 4.3 Part 3 — Multiple Choice: One Long Text

External task shape:

```text
Read one longer text for detailed understanding and main ideas. Answer five multiple-choice questions.
```

Internal mapping:

```text
question_type: multiple_choice
pattern_family: long_text_detail_and_main_idea
answer_model: choice_id
source_unit_type: long_text + question_set
answer_evidence: paragraph_span_or_whole_text_gist
cognitive_load: medium_to_high
inference_level: literal_to_local_inference
source_length_band: long_text
primary_skill: detailed_reading_and_main_idea
```

Future validator obligations:

```text
- each question must have answer evidence.
- detail questions should point to local spans.
- main-idea questions may point to whole-text gist evidence.
- distractors must not be answerable from a different paragraph unless explicitly designed as contrast distractors.
```

---

### 4.4 Part 4 — Multiple-Choice Cloze: Factual Text Vocabulary Gaps

External task shape:

```text
Read a factual text and choose the correct vocabulary item to complete each gap.
```

Internal mapping:

```text
question_type: gap_fill
pattern_family: factual_text_vocabulary_multiple_choice_cloze
answer_model: choice_id
source_unit_type: factual_text + gap_options
answer_evidence: local_gap_context
cognitive_load: medium
inference_level: literal_to_local_inference
source_length_band: short_text
primary_skill: vocabulary_in_context
```

Future validator obligations:

```text
- each gap must have a local context span.
- correct option must fit meaning and collocation.
- distractors must include reason_not_correct.
- item focus should be tagged as vocabulary_in_context unless grammar is explicitly mixed in a later contract.
```

---

### 4.5 Part 5 — Open Cloze: Email Gap Completion

External task shape:

```text
Complete gaps in an email, and sometimes the reply too, using one word per gap.
```

Internal mapping:

```text
question_type: gap_fill
pattern_family: email_open_cloze_one_word
answer_model: accepted_answer_set
source_unit_type: email_text_with_gaps
answer_evidence: local_email_context
authorized_answer_length: one_word
cognitive_load: medium_to_high
inference_level: local_inference
source_length_band: short_text
primary_skill: grammar_vocabulary_in_context
```

Future validator obligations:

```text
- accepted answer set must be bounded before candidate acceptance.
- one-word answer rule must be enforced.
- answer normalization must be explicit.
- generated alternatives must not be accepted unless evidence-backed and reviewed.
```

---

### 4.6 Part 6 — Guided Writing: Email or Note

External task shape:

```text
Write a short email or note of 25 words or more.
```

Internal mapping:

```text
question_type: writing_prompt
pattern_family: guided_email_or_note_writing
answer_model: rubric_scored_response
source_unit_type: writing_prompt + communicative_requirements
answer_evidence: prompt_requirements
cognitive_load: high_for_A2
inference_level: production
source_length_band: prompt
primary_skill: writing
```

Boundary classification:

```text
P2-S3 records Part 6 because the official component combines Reading and Writing. However, E4S Reading V1/V2 must not generate or score writing responses in Phase 2 unless a future Writing Authority or Assessment Rubric task explicitly approves it.
```

Future validator obligations:

```text
- prompt requirements must be structured.
- rubric model must be defined in a future writing/assessment task.
- no auto-scoring is allowed in this design scan.
- no learner-facing writing item is created here.
```

---

### 4.7 Part 7 — Picture Story

External task shape:

```text
Write a short story of 35 words or more based on three picture prompts.
```

Internal mapping:

```text
question_type: writing_prompt
pattern_family: three_picture_story_writing
answer_model: rubric_scored_response
source_unit_type: picture_sequence_prompt
answer_evidence: picture_prompt_requirements
cognitive_load: high_for_A2
inference_level: production
source_length_band: picture_sequence
primary_skill: writing
```

Boundary classification:

```text
P2-S3 records Part 7 as an assessment-pattern boundary only. It belongs downstream to Writing Authority / picture-sequence narrative assessment, not to Reading question generation.
```

Future validator obligations:

```text
- picture sequence metadata must be represented.
- minimum word count must be declared.
- rubric scoring must be defined in a future writing/assessment task.
- no generated picture-story prompt is created in this task.
```

---

## 5. Internal Pattern Family Consolidation

A2 Key Reading and Writing parts consolidate into these reusable internal families:

| Internal family | Used by | Primary answer model | Phase 2 status |
|---|---|---|---|
| short_real_world_text_main_message | A2 Key P1 | choice_id | reading_candidate |
| question_to_short_text_matching | A2 Key P2 | matching_pairs | reading_candidate |
| long_text_detail_and_main_idea | A2 Key P3 | choice_id | reading_candidate |
| factual_text_vocabulary_multiple_choice_cloze | A2 Key P4 | choice_id | reading_candidate |
| email_open_cloze_one_word | A2 Key P5 | accepted_answer_set | reading_candidate_with_strict_gate |
| guided_email_or_note_writing | A2 Key P6 | rubric_scored_response | writing_boundary_only |
| three_picture_story_writing | A2 Key P7 | rubric_scored_response | writing_boundary_only |

Design implication:

```text
E4S-P2 may proceed with Reading parts 1–5 as assessment-pattern candidates.
Parts 6–7 must remain boundary records until Writing Authority / Assessment Rubric tasks are approved.
```

---

## 6. A2 Key Path Alias Contract

Future instantiated assessment patterns should support an `a2_key_path_alias` field:

```json
{
  "a2_key_path_alias": {
    "suite": "CambridgeEnglishQualifications",
    "exam": "A2Key",
    "variant": "A2Key_or_A2KeyForSchools",
    "paper": "ReadingWriting",
    "part": 1,
    "external_shape": "short_real_world_text_main_message"
  }
}
```

Rules:

```text
- a2_key_path_alias is metadata.
- a2_key_path_alias is not authority by itself.
- exact source reference must be attached separately.
- generated A2 Key-style items remain candidate_only.
- KET legacy label may be stored as alias metadata, not as a legacy-format selector.
```

---

## 7. Source Evidence Requirements by Pattern Group

| Pattern group | Minimum evidence required |
|---|---|
| short real-world text main message | full short text + decisive phrase if available |
| question-to-text matching | question text + matched short text + local supporting span |
| long text detail/main idea | long text + paragraph span or whole-text gist evidence |
| vocabulary multiple-choice cloze | factual text + local gap context + option set |
| email open cloze | email text + local gap context + bounded accepted answer set |
| guided email/note writing | prompt requirements + expected communicative points |
| picture story writing | picture sequence metadata + narrative prompt requirements |

Blocking rule:

```text
If source evidence cannot be represented, the pattern may be documented but cannot be accepted for candidate generation.
```

---

## 8. Difficulty and Cognitive Load Mapping

### Reading Parts 1–5

```text
Default CEFR anchor: A2
Default cognitive_load: medium
Allowed inference_level: literal | near_literal | local_inference
Allowed source_length_band: short_text | text_set | long_text | short_email
```

### Writing Boundary Parts 6–7

```text
Default CEFR anchor: A2
Default cognitive_load: high_for_A2
Allowed inference_level: production
Allowed source_length_band: prompt | picture_sequence
Status: writing_boundary_only
```

Global inference, open essay scoring, and adaptive writing feedback remain out of scope for Phase 2 unless later explicitly approved.

---

## 9. Validator Implications for Future Tasks

P2-S3 does not implement validators. It defines future validator implications:

```text
1. A2 Key alias validator
   - Checks exam, variant, paper, and part values.

2. Pattern family validator
   - Checks that each A2 Key part maps to an allowed internal pattern family.

3. Answer model validator
   - Checks that the answer_model matches the mapped pattern family.

4. Evidence validator
   - Checks that required source evidence exists.

5. Distractor validator
   - Checks choice correctness, plausibility, and reason_not_correct for Parts 1, 3, and 4.

6. Matching validator
   - Checks unambiguous matching for Part 2.

7. Open cloze validator
   - Checks bounded accepted answers and one-word answer rule for Part 5.

8. Writing boundary validator
   - Blocks Parts 6–7 from Reading generation unless a future Writing Authority / Assessment Rubric task approves them.

9. Promotion validator
   - Blocks candidate-only items from becoming final authority without future promotion task.
```

---

## 10. Non-Goals

This task does not define or implement:

```text
- exact Cambridge official sample item ingestion
- official PDF storage
- copyrighted sample reproduction
- generated A2 Key-style question items
- generated A2 Key-style practice package
- validator implementation
- JSON schema implementation
- YLE mapping changes
- B1 Preliminary mapping
- Listening mapping
- Speaking mapping
- Writing Authority implementation
- rubric scoring
- learner error diagnosis
- adaptive sequencing
- student-facing HTML
```

---

## 11. Deferred Issues Register

```text
issue_id: P2-S3-U1-OFFICIAL-SOURCE-INGESTION
severity: normal
affected_file_or_artifact: future source manifest / official sample references
classification: FUTURE_WORK
why_deferred: P2-S3 maps task shapes only and does not ingest official assets.
recommended_future_task: E4S-P2-S3A_A2KeyOfficialSourceManifest_DesignScan
blocks_current_task: no
```

```text
issue_id: P2-S3-U2-A2KEY-ASSET-LICENSE-POLICY
severity: normal
affected_file_or_artifact: future license/use policy
classification: FUTURE_WORK
why_deferred: P2-S3 does not copy or store Cambridge assets.
recommended_future_task: E4S-P2-S3B_A2KeySourceUsePolicy_DesignScan
blocks_current_task: no
```

```text
issue_id: P2-S3-U3-WRITING-BOUNDARY
severity: normal
affected_file_or_artifact: future Writing Authority / Assessment Rubric design
classification: FUTURE_WORK
why_deferred: A2 Key Parts 6–7 are writing-production tasks and must not be implemented inside Reading pattern mapping.
recommended_future_task: E4S-WRITING-S0_WritingAssessmentRubricBoundary_DesignScan
blocks_current_task: no
```

```text
issue_id: P2-S4-DISTRACTOR-DETAIL-POLICY
severity: normal
affected_file_or_artifact: future distractor policy design
classification: FUTURE_WORK
why_deferred: P2-S3 maps A2 Key task shapes only; detailed distractor generation rules belong to P2-S4.
recommended_future_task: E4S-P2-S4_DistractorPolicyAndAnswerModel_DesignScan
blocks_current_task: no
```

```text
issue_id: P2-S5-VALIDATOR-CONTRACT
severity: normal
affected_file_or_artifact: future validator contract
classification: FUTURE_WORK
why_deferred: P2-S3 lists validator implications only; no validator contract is implemented here.
recommended_future_task: E4S-P2-S5_AssessmentPatternValidatorContract_DesignScan
blocks_current_task: no
```

---

## 12. Gate & Distance Update

### Gate Metrics

```text
[PASS] P2-S2 Cambridge YLE pattern mapping design scan exists.
[PASS] P2-S3 deliverable path is defined.
[PASS] Current A2 Key / A2 Key for Schools Reading and Writing format baseline is recorded.
[PASS] Legacy KET 9-part / 56-question format is explicitly blocked by default.
[PASS] A2 Key Part 1 mapping is defined.
[PASS] A2 Key Part 2 mapping is defined.
[PASS] A2 Key Part 3 mapping is defined.
[PASS] A2 Key Part 4 mapping is defined.
[PASS] A2 Key Part 5 mapping is defined.
[PASS] A2 Key Parts 6–7 are recorded as writing-boundary patterns only.
[PASS] Internal pattern family consolidation is defined.
[PASS] A2 Key path alias contract is defined.
[PASS] Source evidence requirements by pattern group are defined.
[PASS] Difficulty and cognitive load mapping is defined.
[PASS] Validator implications are documented as future work only.
[PASS] Official asset ingestion is deferred.
[PASS] License/use policy is deferred.
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
D_P2 = 4 sub-tasks left after this design scan

Current Sub-task Status:
E4S-P2-S3_KETReadingPatternMapping_DesignScan -> COMPLETED

Remaining:
P2-S4  DistractorPolicyAndAnswerModel_DesignScan          NEXT
P2-S5  AssessmentPatternValidatorContract_DesignScan      DEFERRED
P2-S6  AssessmentPatternSamplePackage_CandidateOnly       DEFERRED
P2-S7  Phase2ReadbackQA                                   DEFERRED
```

### Phase 2 Current Status

```text
E4S-P2_STATUS = KET_A2KEY_READING_PATTERN_MAPPING_DESIGN_SCAN_COMPLETED
```

---

## 13. Next Shortest Step

```text
NEXT_SHORT_STEP:
E4S-P2-S4_DistractorPolicyAndAnswerModel_DesignScan
```

唯一執行動作：

```text
請下達：
E4S-P2-S4_DistractorPolicyAndAnswerModel_DesignScan
```

Next task boundary:

```text
P2-S4 may define distractor policy and answer model details only.
P2-S4 must not implement code, validators, generated JSON, student-facing HTML, or promotion.
```

# E4S-P2-S2 Cambridge YLE Pattern Mapping Design Scan

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
E4S-P2-S2_CambridgeYLEPatternMapping_DesignScan
```

本次任務類型：

```text
DesignScan only
```

核心資料來源與排序依據（Data Sources）：

```text
1. docs/e4s/E4S_P2_ASSESSMENT_PATTERN_CONTRACT_DESIGN_SCAN.md
   - P2-S2 is the next shortest step.
   - P2-S2 may define Cambridge Starters / Movers / Flyers pattern mapping only.
   - P2-S2 must not implement code, validators, generated JSON, student-facing HTML, or promotion.

2. docs/e4s/E4S_P2_ASSESSMENT_PATTERN_EXPANSION_LAUNCH_PREFLIGHT.md
   - Phase 2 is Assessment Pattern Expansion.
   - Phase 2 focus is pattern contract standardization, not bulk generation.

3. Cambridge Young Learners public format baseline checked during this task
   - Pre A1 Starters Reading & Writing: 5 parts / 25 questions.
   - A1 Movers Reading & Writing: 6 parts / 40 questions.
   - A2 Flyers Reading & Writing: 7 parts / 50 questions.

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
docs/e4s/E4S_P2_CAMBRIDGE_YLE_PATTERN_MAPPING_DESIGN_SCAN.md
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
E4S-P2-S2_CambridgeYLEPatternMapping_DesignScan

Scope:
Define how Cambridge Young Learners English Reading & Writing pattern families map into the internal E4S-P2 assessment pattern contract.

Allowed files:
docs/e4s/E4S_P2_CAMBRIDGE_YLE_PATTERN_MAPPING_DESIGN_SCAN.md

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
- Mapping must cover Pre A1 Starters, A1 Movers, and A2 Flyers Reading & Writing parts.
- Mapping must stay at design-contract level and must not create generated questions.
- Mapping must classify exact implementation work as future work.

Warning policy:
Format assumptions must be treated as source-snapshot assumptions until future source-ingestion or official document evidence is committed.

Generated artifact policy:
Generated artifacts are not allowed in this task.

Runtime impact:
None.

Promotion impact:
None. This task does not promote any Cambridge pattern, sample item, or generated item into final authority.

Stop condition:
Stop after the Cambridge YLE pattern mapping design-scan document is written and P2-S3 is identified as the next shortest step.

Deferred issues register:
All implementation, validator, sample package, KET mapping, asset ingestion, and QA work is deferred.
```

---

## 3. Core Execution

### 3.1 Purpose

This task maps Cambridge Young Learners English Reading & Writing task shapes into the E4S-P2 internal assessment pattern contract.

This mapping is not a question bank.

It answers:

```text
Which Cambridge YLE Reading & Writing task shapes correspond to which internal question_type, answer_model, source_evidence requirement, and future validator obligation?
```

It does not answer:

```text
How do we generate actual Cambridge-style questions?
```

That belongs to a later candidate-only sample package task.

---

### 3.2 Source Snapshot Boundary

This design uses the following public format baseline:

```text
Pre A1 Starters Reading & Writing:
- 5 parts
- 25 questions

A1 Movers Reading & Writing:
- 6 parts
- 40 questions

A2 Flyers Reading & Writing:
- 7 parts
- 50 questions
```

Important boundary:

```text
This task records the mapping design only. A future source-ingestion task should attach exact official sample-paper references, page numbers, URLs, file hashes, and licensing/use policy.
```

---

### 3.3 Internal Mapping Principles

Cambridge YLE pattern mapping must follow these principles:

```text
1. Map task shape, not copyrighted content.
2. Preserve source trace for every future item.
3. Treat Cambridge-style pattern labels as assessment metadata, not final authority.
4. Keep Reading & Writing pattern mapping separate from Listening and Speaking.
5. Do not create learner-facing tasks in this design scan.
6. Do not use Cambridge placeholder names for generation until a later implementation task defines exact generator gates.
7. Do not promote generated Cambridge-style items by implication.
```

---

### 3.4 CEFR / Cambridge Path Layer

Cambridge YLE levels map into the E4S internal path as follows:

| Cambridge level | CEFR anchor | Internal path hint | Role in E4S |
|---|---|---|---|
| Pre A1 Starters | Pre-A1 | CambridgeYLE.Starters | recognition, copying, picture-supported reading |
| A1 Movers | A1 | CambridgeYLE.Movers | sentence comprehension, short dialogue response, controlled cloze |
| A2 Flyers | A2 | CambridgeYLE.Flyers | longer text comprehension, grammar choice, open cloze-lite |

Rules:

```text
- CEFR anchor is difficulty metadata.
- Cambridge path hint is assessment-pattern metadata.
- Neither CEFR nor Cambridge path hint equals Learning Path Authority.
```

---

## 4. Cambridge YLE Reading & Writing Mapping Matrix

### 4.1 Pre A1 Starters Reading & Writing

#### Starters Part 1

External task shape:

```text
Object picture + short sentence. Learner marks true/false with tick/cross.
```

Internal mapping:

```text
question_type: true_false
pattern_family: picture_sentence_verification
answer_model: boolean
source_unit_type: image_item + sentence
answer_evidence: picture_object_identity + sentence_claim
cognitive_load: low
inference_level: literal
```

Future validator obligations:

```text
- sentence claim must be directly checkable from the image/source metadata.
- answer must be boolean.
- no open response allowed.
```

#### Starters Part 2

External task shape:

```text
Big picture + sentences. Learner writes yes/no.
```

Internal mapping:

```text
question_type: true_false
pattern_family: picture_scene_yes_no
answer_model: boolean
source_unit_type: image_scene + sentence_claim
answer_evidence: image_scene_fact
cognitive_load: low
inference_level: literal
```

Future validator obligations:

```text
- answer text must normalize to yes/no.
- claim must be visually grounded.
- no external world knowledge allowed.
```

#### Starters Part 3

External task shape:

```text
Object pictures + jumbled letters. Learner orders letters to spell the object word.
```

Internal mapping:

```text
question_type: word_ordering
pattern_family: object_word_spelling
answer_model: exact_text
source_unit_type: image_item + letter_set
answer_evidence: object_identity
cognitive_load: low
inference_level: literal
```

Future validator obligations:

```text
- all letters must be consumed unless task-specific rule allows otherwise.
- canonical answer must match approved vocabulary authority.
- answer normalization must be explicit.
```

#### Starters Part 4

External task shape:

```text
Short text with gaps. Learner chooses words from a picture/word box and copies them.
```

Internal mapping:

```text
question_type: cloze_vocabulary
pattern_family: picture_supported_word_box_cloze
answer_model: cloze_tokens
source_unit_type: short_text + word_box
answer_evidence: local_text_gap + candidate_word_box
cognitive_load: low_to_medium
inference_level: literal
```

Future validator obligations:

```text
- each gap answer must come from the supplied word box.
- unused options may exist.
- answer must fit local sentence context.
```

#### Starters Part 5

External task shape:

```text
Three story pictures with one or two questions per picture. Learner writes one-word answers.
```

Internal mapping:

```text
question_type: short_answer
pattern_family: picture_story_one_word_answer
answer_model: accepted_answer_set
source_unit_type: image_sequence + short_question
answer_evidence: specific_picture_fact
cognitive_load: low_to_medium
inference_level: literal
```

Future validator obligations:

```text
- answer length must be one word unless a later source-specific rule allows otherwise.
- each question must point to a specific picture or picture range.
- accepted answer set must be bounded.
```

---

### 4.2 A1 Movers Reading & Writing

#### Movers Part 1

External task shape:

```text
Object pictures with words + definitions. Learner matches word to definition and copies the word.
```

Internal mapping:

```text
question_type: matching
pattern_family: word_definition_matching
answer_model: matching_pairs
source_unit_type: word_list + definition_list
answer_evidence: vocabulary_definition_authority_or_source_definition
cognitive_load: medium
inference_level: literal_to_near_literal
```

Future validator obligations:

```text
- every definition must have exactly one correct word unless multi-answer is explicitly allowed.
- copied answer must match supplied word.
- vocabulary level must not exceed Movers band without warning.
```

#### Movers Part 2

External task shape:

```text
Big picture + six sentences. Learner writes yes/no.
```

Internal mapping:

```text
question_type: true_false
pattern_family: picture_scene_yes_no
answer_model: boolean
source_unit_type: image_scene + sentence_claim
answer_evidence: image_scene_fact
cognitive_load: low_to_medium
inference_level: literal
```

Future validator obligations:

```text
- visual claim must be grounded.
- yes/no normalization required.
- no external inference allowed.
```

#### Movers Part 3

External task shape:

```text
Short conversation with missing responses. Learner chooses correct response from options.
```

Internal mapping:

```text
question_type: multiple_choice
pattern_family: dialogue_response_choice
answer_model: choice_id
source_unit_type: dialogue_context + response_options
answer_evidence: dialogue_turn_context
cognitive_load: medium
inference_level: near_literal
```

Future validator obligations:

```text
- correct option must be pragmatically coherent with previous turn.
- distractors must be plausible but not correct.
- dialogue context must be preserved.
```

#### Movers Part 4

External task shape:

```text
Short text with gaps, word/picture options, and best-title choice.
```

Internal mapping:

```text
question_type: reading_comprehension_set
pattern_family: text_cloze_plus_title_choice
answer_model: composite_set
source_unit_type: short_text + option_box + title_options
answer_evidence: local_gap_context + whole_text_gist
cognitive_load: medium
inference_level: literal_to_near_literal
```

Child item mapping:

```text
- gap items -> cloze_tokens
- title item -> choice_id
```

Future validator obligations:

```text
- each gap answer must come from options.
- title choice must be supported by whole-text gist.
- composite set must preserve child answer models.
```

#### Movers Part 5

External task shape:

```text
Picture story. Learner completes sentences about the story using one, two, or three words.
```

Internal mapping:

```text
question_type: gap_fill
pattern_family: picture_story_sentence_completion
answer_model: accepted_answer_set
source_unit_type: image_sequence + sentence_completion
answer_evidence: picture_story_fact
cognitive_load: medium
inference_level: literal_to_near_literal
```

Future validator obligations:

```text
- answer length limit must be declared.
- each answer must be supported by story picture evidence.
- accepted answers must be bounded.
```

#### Movers Part 6

External task shape:

```text
Factual text with gaps. Learner chooses one of three answers for each gap.
```

Internal mapping:

```text
question_type: gap_fill
pattern_family: grammar_vocabulary_multiple_choice_cloze
answer_model: choice_id
source_unit_type: short_factual_text + options
answer_evidence: local_sentence_context
cognitive_load: medium
inference_level: literal_to_local_inference
```

Future validator obligations:

```text
- correct option must fit local grammar and meaning.
- distractors must be grammatically or semantically invalid in context.
- validation must record whether the item primarily targets grammar, vocabulary, or both.
```

---

### 4.3 A2 Flyers Reading & Writing

#### Flyers Part 1

External task shape:

```text
Words and definitions. Learner writes the correct word next to each definition.
```

Internal mapping:

```text
question_type: matching
pattern_family: word_definition_matching
answer_model: matching_pairs_or_exact_text
source_unit_type: word_list + definition_list
answer_evidence: definition_match
cognitive_load: medium
inference_level: literal_to_near_literal
```

Future validator obligations:

```text
- definition must uniquely identify the target word.
- copied word must match provided word list.
- vocabulary level must be checked against A2/Flyers band.
```

#### Flyers Part 2

External task shape:

```text
Big picture + seven sentences. Learner writes yes/no.
```

Internal mapping:

```text
question_type: true_false
pattern_family: picture_scene_yes_no
answer_model: boolean
source_unit_type: image_scene + sentence_claim
answer_evidence: image_scene_fact
cognitive_load: low_to_medium
inference_level: literal
```

Future validator obligations:

```text
- visual grounding required.
- yes/no normalization required.
- no external inference allowed.
```

#### Flyers Part 3

External task shape:

```text
Short conversation with missing responses. Learner chooses from a larger response option list.
```

Internal mapping:

```text
question_type: multiple_choice
pattern_family: dialogue_response_choice_extended
answer_model: choice_id
source_unit_type: dialogue_context + response_option_list
answer_evidence: dialogue_turn_context
cognitive_load: medium_to_high
inference_level: near_literal_to_local_inference
```

Future validator obligations:

```text
- response must be pragmatically coherent.
- larger option pool must preserve one correct answer per gap unless explicitly designed otherwise.
- distractors must be plausible but incompatible with local dialogue flow.
```

#### Flyers Part 4

External task shape:

```text
Text with gaps using nouns, adjectives, or verbs; word box; final best-title choice.
```

Internal mapping:

```text
question_type: reading_comprehension_set
pattern_family: multi_pos_cloze_plus_title_choice
answer_model: composite_set
source_unit_type: short_text + word_box + title_options
answer_evidence: local_gap_context + whole_text_gist
cognitive_load: medium_to_high
inference_level: literal_to_local_inference
```

Child item mapping:

```text
- gap items -> cloze_tokens
- title item -> choice_id
```

Future validator obligations:

```text
- each gap must record target POS when available.
- title answer must be supported by text gist.
- all gap answers must come from supplied options.
```

#### Flyers Part 5

External task shape:

```text
Complete story + sentences with gaps. Learner completes each sentence with one to four words.
```

Internal mapping:

```text
question_type: gap_fill
pattern_family: story_sentence_completion
answer_model: accepted_answer_set
source_unit_type: story_text + sentence_completion
answer_evidence: story_text_span
cognitive_load: medium_to_high
inference_level: literal_to_local_inference
```

Future validator obligations:

```text
- answer length limit must be declared.
- accepted answers must be evidence-backed.
- answer may require locating information across sentence boundaries.
```

#### Flyers Part 6

External task shape:

```text
Factual text with gaps; three choices for each gap; focuses on text understanding and simple grammar.
```

Internal mapping:

```text
question_type: gap_fill
pattern_family: grammar_vocabulary_multiple_choice_cloze
answer_model: choice_id
source_unit_type: short_factual_text + options
answer_evidence: local_text_context
cognitive_load: medium_to_high
inference_level: literal_to_local_inference
```

Future validator obligations:

```text
- correct option must fit grammar and meaning.
- distractors must be rejected with reason_not_correct.
- item focus must declare grammar, vocabulary, or mixed target.
```

#### Flyers Part 7

External task shape:

```text
Short letter or diary text with gaps. Learner supplies missing words without a word list.
```

Internal mapping:

```text
question_type: gap_fill
pattern_family: open_cloze_lite
answer_model: accepted_answer_set
source_unit_type: short_text_with_gaps
answer_evidence: local_text_context
cognitive_load: high_for_YLE
inference_level: local_inference
```

Future validator obligations:

```text
- accepted answer set must be bounded before candidate acceptance.
- no fully open writing is allowed.
- answer normalization must be strict enough to prevent ambiguous acceptance.
```

---

## 5. Internal Pattern Family Consolidation

The Cambridge YLE parts consolidate into these reusable internal families:

| Internal family | Used by | Primary answer model |
|---|---|---|
| picture_sentence_verification | Starters P1 | boolean |
| picture_scene_yes_no | Starters P2, Movers P2, Flyers P2 | boolean |
| object_word_spelling | Starters P3 | exact_text |
| picture_supported_word_box_cloze | Starters P4 | cloze_tokens |
| picture_story_one_word_answer | Starters P5 | accepted_answer_set |
| word_definition_matching | Movers P1, Flyers P1 | matching_pairs / exact_text |
| dialogue_response_choice | Movers P3, Flyers P3 | choice_id |
| text_cloze_plus_title_choice | Movers P4 | composite_set |
| picture_story_sentence_completion | Movers P5 | accepted_answer_set |
| grammar_vocabulary_multiple_choice_cloze | Movers P6, Flyers P6 | choice_id |
| multi_pos_cloze_plus_title_choice | Flyers P4 | composite_set |
| story_sentence_completion | Flyers P5 | accepted_answer_set |
| open_cloze_lite | Flyers P7 | accepted_answer_set |

Design implication:

```text
Phase 2 does not need a separate generator for every external Cambridge part.
It should first build reusable internal pattern families, then attach Cambridge path aliases.
```

---

## 6. Cambridge Path Alias Contract

Future instantiated assessment patterns should support a `cambridge_path_alias` field:

```json
{
  "cambridge_path_alias": {
    "suite": "CambridgeYLE",
    "level": "Starters",
    "paper": "ReadingWriting",
    "part": 1,
    "external_shape": "picture_sentence_verification"
  }
}
```

Rules:

```text
- cambridge_path_alias is metadata.
- cambridge_path_alias is not authority by itself.
- exact source reference must be attached separately.
- generated Cambridge-style items remain candidate_only.
```

---

## 7. Source Evidence Requirements by Pattern Group

| Pattern group | Minimum evidence required |
|---|---|
| picture verification | image item / scene metadata + sentence claim |
| word definition matching | word list + definition source or vocabulary authority reference |
| spelling / jumbled letters | object identity + canonical word |
| word-box cloze | text gap + supplied option set |
| dialogue response | dialogue turn context + option list |
| story completion | story text or picture-sequence evidence |
| title choice | whole-text gist evidence |
| open cloze-lite | local text context + bounded accepted answer set |

Blocking rule:

```text
If source evidence cannot be represented, the pattern may be documented but cannot be accepted for candidate generation.
```

---

## 8. Difficulty and Cognitive Load Mapping

### Starters

```text
Default cognitive_load: low
Allowed inference_level: literal
Allowed source_length_band: image_item | image_scene | short_text
```

### Movers

```text
Default cognitive_load: medium
Allowed inference_level: literal | near_literal | local_inference
Allowed source_length_band: image_scene | short_dialogue | short_text | picture_story
```

### Flyers

```text
Default cognitive_load: medium_to_high
Allowed inference_level: literal | near_literal | local_inference
Allowed source_length_band: image_scene | short_dialogue | short_text | story_text
```

Global inference remains out of scope for Phase 2 unless later explicitly approved.

---

## 9. Validator Implications for Future Tasks

P2-S2 does not implement validators. It defines future validator implications:

```text
1. Cambridge alias validator
   - Checks suite, level, paper, and part values.

2. Pattern family validator
   - Checks that each Cambridge part maps to an allowed internal pattern family.

3. Answer model validator
   - Checks that the answer_model matches the mapped pattern family.

4. Evidence validator
   - Checks that required source evidence exists.

5. Distractor validator
   - Checks correctness, plausibility, and reason_not_correct.

6. Promotion validator
   - Blocks candidate-only items from becoming final authority without future promotion task.
```

---

## 10. Non-Goals

This task does not define or implement:

```text
- exact Cambridge official sample item ingestion
- official PDF storage
- copyrighted sample reproduction
- generated Cambridge-style question items
- generated Cambridge-style practice package
- validator implementation
- JSON schema implementation
- KET mapping
- Listening mapping
- Speaking mapping
- Writing production tasks
- learner error diagnosis
- adaptive sequencing
- student-facing HTML
```

---

## 11. Deferred Issues Register

```text
issue_id: P2-S2-U1-OFFICIAL-SOURCE-INGESTION
severity: normal
affected_file_or_artifact: future source manifest / official sample references
classification: FUTURE_WORK
why_deferred: P2-S2 maps task shapes only and does not ingest official assets.
recommended_future_task: E4S-P2-S2A_CambridgeYLEOfficialSourceManifest_DesignScan
blocks_current_task: no
```

```text
issue_id: P2-S2-U2-CAMBRIDGE-ASSET-LICENSE-POLICY
severity: normal
affected_file_or_artifact: future license/use policy
classification: FUTURE_WORK
why_deferred: P2-S2 does not copy or store Cambridge assets.
recommended_future_task: E4S-P2-S2B_CambridgeYLESourceUsePolicy_DesignScan
blocks_current_task: no
```

```text
issue_id: P2-S3-KET-MAPPING
severity: normal
affected_file_or_artifact: future docs/e4s/E4S_P2_KET_READING_PATTERN_MAPPING_DESIGN_SCAN.md
classification: FUTURE_WORK
why_deferred: P2-S2 is limited to Cambridge YLE Starters / Movers / Flyers.
recommended_future_task: E4S-P2-S3_KETReadingPatternMapping_DesignScan
blocks_current_task: no
```

```text
issue_id: P2-S4-DISTRACTOR-DETAIL-POLICY
severity: normal
affected_file_or_artifact: future distractor policy design
classification: FUTURE_WORK
why_deferred: P2-S2 maps Cambridge task shapes only; detailed distractor generation rules belong to P2-S4.
recommended_future_task: E4S-P2-S4_DistractorPolicyAndAnswerModel_DesignScan
blocks_current_task: no
```

```text
issue_id: P2-S5-VALIDATOR-CONTRACT
severity: normal
affected_file_or_artifact: future validator contract
classification: FUTURE_WORK
why_deferred: P2-S2 lists validator implications only; no validator contract is implemented here.
recommended_future_task: E4S-P2-S5_AssessmentPatternValidatorContract_DesignScan
blocks_current_task: no
```

---

## 12. Gate & Distance Update

### Gate Metrics

```text
[PASS] P2-S1 assessment pattern contract design scan exists.
[PASS] P2-S2 deliverable path is defined.
[PASS] Pre A1 Starters Reading & Writing mapping is defined.
[PASS] A1 Movers Reading & Writing mapping is defined.
[PASS] A2 Flyers Reading & Writing mapping is defined.
[PASS] Internal pattern family consolidation is defined.
[PASS] Cambridge path alias contract is defined.
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
D_P2 = 5 sub-tasks left after this design scan

Current Sub-task Status:
E4S-P2-S2_CambridgeYLEPatternMapping_DesignScan -> COMPLETED

Remaining:
P2-S3  KETReadingPatternMapping_DesignScan                NEXT
P2-S4  DistractorPolicyAndAnswerModel_DesignScan          DEFERRED
P2-S5  AssessmentPatternValidatorContract_DesignScan      DEFERRED
P2-S6  AssessmentPatternSamplePackage_CandidateOnly       DEFERRED
P2-S7  Phase2ReadbackQA                                   DEFERRED
```

### Phase 2 Current Status

```text
E4S-P2_STATUS = CAMBRIDGE_YLE_PATTERN_MAPPING_DESIGN_SCAN_COMPLETED
```

---

## 13. Next Shortest Step

```text
NEXT_SHORT_STEP:
E4S-P2-S3_KETReadingPatternMapping_DesignScan
```

唯一執行動作：

```text
請下達：
E4S-P2-S3_KETReadingPatternMapping_DesignScan
```

Next task boundary:

```text
P2-S3 may define KET / A2 Key Reading pattern mapping only.
P2-S3 must not implement code, validators, generated JSON, student-facing HTML, or promotion.
```

# E4S-P6-S1 Error Tagging Taxonomy Contract

## 1. Current State

Current Epic:

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

Current Phase:

```text
E4S-P6_ErrorTaggingAndWeakPointDiagnosis
```

Current Sub-task:

```text
E4S-P6-S1_ErrorTaggingTaxonomyContract_DesignScan
```

Data Sources:

```text
- docs/ulga/E4S_P6_ERROR_TAGGING_STARTUP.md
- 重點任務排程.txt
- RAZ-AW-V1 Status Snapshot.txt
- 標籤化錯題分析.txt
```

External Permission:

```text
GitHub: APPROVED - read/write project files by API
Google Drive: APPROVED - read reference files/specs/datasets
```

Deliverable:

```text
docs/ulga/E4S_P6_ERROR_TAGGING_TAXONOMY_CONTRACT.md
```

This deliverable defines controlled taxonomy values only. It does not implement runtime code, validators, generated data, learner state, adaptive recommendation, or UI.

---

## 2. Core Execution

### 2.1 Scope Lock

P6-S1 defines canonical controlled values for the Phase 6 diagnostic chain:

```text
Question -> Question Tags -> Answer Record -> Error Tags -> Weak-point Summary -> Remediation Tags
```

P6-S1 may define:

```text
- question_type values
- skill_area values
- concept_tags values
- cognitive_skill values
- error_type values
- error_detail values
- remediation_tag values
- taxonomy naming rules
- safe use / blocked use boundaries
```

P6-S1 must not define or implement:

```text
- Python builder
- Python validator
- learner mastery scoring
- adaptive path recommendation
- UI / HTML
- database tables
- generated exercise files
- production diagnosis engine
```

### 2.2 Naming Rules

All canonical taxonomy values must use:

```text
lower_snake_case
```

Blocked forms:

```text
- free text labels
- mixed English/Chinese labels
- spaces
- camelCase
- punctuation-heavy labels
- per-book ad hoc tags
- per-student ad hoc tags
```

Every canonical value must be stable enough to support later aggregation across:

```text
- RAZ
- Cambridge Pre-A1 / A1 / A2
- school exam items
- workbook items
- custom generated practice
```

### 2.3 Taxonomy Layer Separation

The taxonomy must preserve four layers:

```text
1. question_type
   What the question looks like.

2. skill_area + concept_tags + cognitive_skill
   What the question tests.

3. error_type + error_detail
   Why the answer is wrong.

4. remediation_tag
   What should be practiced next.
```

A single wrong answer must not automatically become a stable concept diagnosis. Stable weak-point diagnosis requires repeated evidence across multiple questions, dates, or source types.

---

## 3. Controlled Taxonomy

### 3.1 question_type

`question_type` describes the surface format of the question. It does not define the underlying concept.

Allowed V1 values:

| Value | Meaning | Phase 6 Use |
|---|---|---|
| `literal_who` | Explicit who-question from source text | Reading V1 active |
| `literal_what` | Explicit what-question from source text | Reading V1 active |
| `literal_where` | Explicit where-question from source text | Reading V1 active |
| `true_false` | True/false based on explicit source evidence | Reading V1 active |
| `sentence_ordering` | Reorder source sentences or events | Reading V1 active |
| `cloze_vocabulary` | Fill a missing word from source/evidence | Reading V1 active |

Allowed future-compatible values:

| Value | Meaning | Status |
|---|---|---|
| `multiple_choice` | Choose one correct option | Deferred |
| `fill_blank` | General blank-fill item | Deferred |
| `matching` | Match words, pictures, sentences, or meanings | Deferred |
| `short_answer` | Short typed answer | Deferred |
| `word_ordering` | Reorder words into a sentence | Deferred |
| `error_correction` | Correct an error in a sentence | Deferred |
| `reading_comprehension` | General reading comprehension item | Deferred |
| `picture_description` | Produce description from image | Deferred |
| `listening_choice` | Listen and choose | Deferred |
| `dictation` | Listen and write | Deferred |
| `translation` | Translate sentence or phrase | Deferred |
| `writing_prompt` | Produce written output | Deferred |
| `speaking_response` | Produce spoken response | Deferred |

Rules:

```text
- Reading V1 generation may only use Reading V1 active values.
- Future-compatible values may be documented but must not be activated without later approval.
- `question_type` must not be used alone to infer concept mastery.
```

### 3.2 skill_area

`skill_area` describes the primary skill being measured.

Allowed values:

| Value | Meaning |
|---|---|
| `reading` | Understanding written source text |
| `grammar` | Applying grammar structure or rule |
| `vocabulary` | Understanding or using word meaning |
| `sentence_structure` | Building or ordering sentence structure |
| `spelling` | Spelling accuracy |
| `phonics` | Sound-letter decoding / early reading |
| `listening` | Understanding spoken input |
| `writing` | Producing written output |
| `speaking` | Producing spoken output |
| `comprehension` | General understanding across text or source |
| `inference` | Reasoning beyond explicit literal text |

Reading V1 preferred values:

```text
reading
vocabulary
sentence_structure
comprehension
```

Rules:

```text
- Each question must have one primary skill_area.
- Optional secondary skill areas may be added later, but P6-S1 only defines the primary value contract.
- Do not use `skill_area` as a replacement for `concept_tags`.
```

### 3.3 concept_tags

`concept_tags` identify the learning concept being tested or affected. Multiple concept tags are allowed.

#### 3.3.1 Grammar concept tags

Allowed values:

```text
be_verb
am_is_are
present_simple
third_person_singular_s
do_does_question
present_continuous
past_simple
regular_past_ed
irregular_past
there_is_are
singular_plural
articles_a_an_the
article_a
article_an
article_the
preposition_place
preposition_time
preposition_in
preposition_on
preposition_under
preposition_with
pronouns
possessive_adjectives
wh_questions
who_question
what_question
where_question
when_question
why_question
yes_no_questions
sentence_order
subject_verb_agreement
auxiliary_do_does
word_order
verb_tense
```

#### 3.3.2 Vocabulary concept tags

Allowed values:

```text
animal_words
school_objects
family_words
food_words
color_words
number_words
action_verbs
emotion_words
place_words
body_parts
clothes_words
weather_words
transportation_words
home_words
shopping_words
health_words
hobby_words
time_words
```

#### 3.3.3 Reading concept tags

Allowed values:

```text
main_idea
detail_finding
explicit_detail
sequence
cause_effect
inference
character_action
setting
reference_word
picture_text_matching
literal_comprehension
who_reference
what_reference
where_reference
source_sentence_order
```

#### 3.3.4 Writing concept tags

Allowed values:

```text
simple_sentence
svo_sentence
svc_sentence
add_time
add_place
add_reason
sequence_words
paragraph_structure
topic_sentence
supporting_detail
ending_sentence
picture_description
present_continuous_description
```

Rules:

```text
- Every question should have at least one concept_tag.
- Tags must be stable concepts, not temporary explanations.
- For Reading V1 literal questions, prefer concept tags such as `literal_comprehension`, `detail_finding`, `who_reference`, `what_reference`, `where_reference`, and source-relevant vocabulary tags.
- A concept_tag does not mean the learner has a confirmed weakness. It only marks the concept involved in the item.
```

### 3.4 cognitive_skill

`cognitive_skill` describes the mental action required from the learner.

Allowed values:

| Value | Meaning |
|---|---|
| `recognize` | Identify a known word, form, or answer |
| `recall` | Retrieve known information from memory |
| `locate_information` | Find explicit information in source text |
| `match_information` | Match text, answer, picture, or meaning |
| `sequence_information` | Put events or sentences in order |
| `apply_rule` | Apply a grammar or spelling rule |
| `choose_answer` | Select the correct answer from options |
| `produce_word` | Produce one word or short phrase |
| `produce_sentence` | Produce a complete sentence |
| `correct_error` | Identify and correct an error |
| `infer_meaning` | Infer from context beyond explicit statement |
| `summarize` | Condense source meaning |

Reading V1 preferred values:

```text
locate_information
match_information
sequence_information
choose_answer
produce_word
```

Rules:

```text
- `cognitive_skill` should describe the task demand, not the topic.
- Do not use `infer_meaning` for literal Reading V1 items unless the source contract explicitly allows inference.
```

### 3.5 error_type

`error_type` describes the broad reason class for an incorrect answer.

Allowed values:

| Value | Meaning |
|---|---|
| `concept_error` | Repeated evidence suggests the learner lacks the concept |
| `rule_application_error` | Learner may know the rule but applied it incorrectly |
| `vocabulary_gap` | Learner likely does not know the word or phrase |
| `question_misread` | Learner likely misunderstood the question wording |
| `careless_error` | Evidence suggests slip, not stable concept weakness |
| `spelling_error` | Incorrect spelling affects the answer |
| `sentence_structure_error` | Output structure is incomplete or incorrect |
| `insufficient_output` | Answer is too incomplete to satisfy expected response |
| `reading_detail_error` | Learner missed explicit source detail |
| `source_evidence_error` | Answer conflicts with source evidence |
| `answer_format_error` | Answer may be conceptually correct but wrong format |
| `unknown_error` | Cannot classify safely yet |

Rules:

```text
- `concept_error` should be used conservatively.
- One wrong answer should usually begin as `rule_application_error`, `reading_detail_error`, `vocabulary_gap`, `question_misread`, `answer_format_error`, or `unknown_error` unless repeated evidence exists.
- `unknown_error` is allowed when the diagnosis lacks evidence.
```

### 3.6 error_detail

`error_detail` describes the specific diagnosed issue.

Allowed grammar-related values:

```text
missing_third_person_s
wrong_be_verb
there_is_are_confusion
there_are_plural_noun_error
singular_plural_confusion
wrong_preposition
wrong_word_order
wrong_auxiliary_do_does
wrong_tense
article_missing
article_confusion
pronoun_confusion
subject_verb_agreement_error
verb_form_error
```

Allowed reading-related values:

```text
missed_explicit_detail
wrong_who_reference
wrong_what_reference
wrong_where_reference
wrong_sequence_order
source_sentence_mismatch
picture_text_mismatch
literal_question_misread
unsupported_answer_from_source
```

Allowed vocabulary-related values:

```text
unknown_word
wrong_word_meaning
confused_similar_words
wrong_topic_word
color_word_confusion
number_word_confusion
place_word_confusion
action_verb_confusion
```

Allowed output/format values:

```text
incomplete_answer
answer_too_short
wrong_answer_format
spelling_blocks_answer
missing_article_and_be_verb
sentence_fragment
missing_subject
missing_verb
```

Fallback values:

```text
not_enough_evidence
needs_human_review
```

Rules:

```text
- `error_detail` must be compatible with `error_type`.
- `error_detail` must not contain learner names.
- `error_detail` must not quote long source text.
- If no safe classification exists, use `not_enough_evidence` or `needs_human_review`.
```

### 3.7 remediation_tag

`remediation_tag` describes the next practice direction.

Allowed grammar remediation values:

```text
practice_third_person_s
practice_present_simple_he_she_it
review_there_is_are
practice_there_is_are_plural
practice_preposition_in_on_under
practice_articles_a_an_the
practice_be_verb_am_is_are
practice_do_does_questions
practice_word_order
practice_subject_verb_agreement
```

Allowed reading remediation values:

```text
practice_reading_detail_questions
practice_literal_who_questions
practice_literal_what_questions
practice_literal_where_questions
practice_sentence_ordering
practice_source_evidence_lookup
practice_picture_text_matching
```

Allowed vocabulary remediation values:

```text
vocabulary_school_objects_review
vocabulary_food_words_review
vocabulary_animal_words_review
vocabulary_color_words_review
vocabulary_number_words_review
vocabulary_home_words_review
vocabulary_place_words_review
vocabulary_action_verbs_review
```

Allowed writing/output remediation values:

```text
rebuild_svo_sentence
practice_simple_sentence
practice_picture_description_present_continuous
practice_complete_answer_sentence
practice_sentence_fragment_repair
practice_spelling_target_words
```

Fallback remediation values:

```text
human_review_required
no_remediation_assigned
```

Rules:

```text
- Every incorrect answer should receive one remediation_tag unless classification is impossible.
- `human_review_required` is required when the system cannot classify safely.
- Remediation tags are practice directions, not generated exercise content.
```

---

## 4. Cross-field Compatibility Rules

### 4.1 Required Fields for a Tagged Question

A P6-compatible tagged question should include:

```text
question_id
source_type
level
question_type
skill_area
concept_tags
cognitive_skill
correct_answer
source_evidence_ref
```

### 4.2 Required Fields for an Incorrect Answer Diagnosis

A P6-compatible incorrect answer diagnosis should include:

```text
answer_id
question_id
learner_answer
is_correct
error_type
error_detail
remediation_tag
confidence
source_evidence_ref
```

### 4.3 Compatibility Examples

#### Example A: Reading detail error

```json
{
  "question_type": "literal_what",
  "skill_area": "reading",
  "concept_tags": ["literal_comprehension", "detail_finding", "what_reference"],
  "cognitive_skill": "locate_information",
  "error_type": "reading_detail_error",
  "error_detail": "missed_explicit_detail",
  "remediation_tag": "practice_reading_detail_questions"
}
```

#### Example B: There is / There are confusion

```json
{
  "question_type": "fill_blank",
  "skill_area": "grammar",
  "concept_tags": ["there_is_are", "singular_plural"],
  "cognitive_skill": "apply_rule",
  "error_type": "rule_application_error",
  "error_detail": "there_are_plural_noun_error",
  "remediation_tag": "practice_there_is_are_plural"
}
```

#### Example C: Vocabulary gap

```json
{
  "question_type": "cloze_vocabulary",
  "skill_area": "vocabulary",
  "concept_tags": ["food_words"],
  "cognitive_skill": "produce_word",
  "error_type": "vocabulary_gap",
  "error_detail": "unknown_word",
  "remediation_tag": "vocabulary_food_words_review"
}
```

---

## 5. Phase 6 Safety Rules

### 5.1 Diagnosis Conservatism

Phase 6 must avoid over-diagnosis.

```text
One wrong answer = evidence item
Repeated wrong answers across concepts/sources/dates = possible weak point
```

### 5.2 Source Trace Requirement

Any diagnosis produced from Reading V1 must preserve source traceability.

Required reference field:

```text
source_evidence_ref
```

The taxonomy does not define the source evidence object itself. That belongs to the question package and answer record contracts.

### 5.3 Human Review Escape Hatch

If automatic diagnosis is not safe, use:

```text
error_type: unknown_error
error_detail: needs_human_review
remediation_tag: human_review_required
```

### 5.4 Future Phase Boundary

P6-S1 taxonomy may be used by future:

```text
- Reading weak-point summary
- Assessment feedback
- Writing correction analysis
- Listening dictation error review
- Speaking response scoring
```

But this file does not activate those systems.

---

## 6. Gate and Distance Update

Gate Metrics:

```text
PASS - Controlled values defined for question_type
PASS - Controlled values defined for skill_area
PASS - Controlled values defined for concept_tags
PASS - Controlled values defined for cognitive_skill
PASS - Controlled values defined for error_type
PASS - Controlled values defined for error_detail
PASS - Controlled values defined for remediation_tag
PASS - Runtime/code untouched
PASS - Validator implementation deferred
PASS - Adaptive recommendation remains out of scope
```

Distance Vector:

```text
D_P6 = 7 sub-tasks left after P6-S1
E4S-P6-S1_ErrorTaggingTaxonomyContract_DesignScan -> COMPLETED
E4S-P6 -> TAXONOMY_CONTRACT_DEFINED
ERROR_TAGGING_RUNTIME -> NOT_STARTED
WEAK_POINT_ENGINE -> NOT_STARTED
```

---

## 7. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P6-S2_ErrorTaggingRecordSchemaContract_DesignScan
```

Unique next action:

```text
Create docs/ulga/E4S_P6_ERROR_TAGGING_RECORD_SCHEMA_CONTRACT.md
```

P6-S2 should define the record schema for:

```text
- tagged_question_record
- learner_answer_record
- error_diagnosis_record
- remediation_link_record
```

P6-S2 must not implement builders, validators, UI, generated data, learner mastery scoring, or adaptive recommendation.

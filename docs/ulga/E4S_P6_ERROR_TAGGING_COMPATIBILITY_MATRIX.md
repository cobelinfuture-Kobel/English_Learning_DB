# E4S-P6-S3 Error Tagging Compatibility Matrix

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
E4S-P6-S3_ErrorTaggingCompatibilityMatrix_DesignScan
```

Data Sources:

```text
- docs/ulga/E4S_P6_ERROR_TAGGING_STARTUP.md
- docs/ulga/E4S_P6_ERROR_TAGGING_TAXONOMY_CONTRACT.md
- docs/ulga/E4S_P6_ERROR_TAGGING_RECORD_SCHEMA_CONTRACT.md
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
docs/ulga/E4S_P6_ERROR_TAGGING_COMPATIBILITY_MATRIX.md
```

This deliverable defines compatibility rules only. It does not implement builders, validators, generated data, weak-point aggregation, learner mastery scoring, UI, or adaptive recommendation.

---

## 2. Core Execution

### 2.1 Scope Lock

P6-S3 defines compatibility rules between these P6-S1 taxonomy fields:

```text
question_type
skill_area
concept_tags
cognitive_skill
error_type
error_detail
remediation_tag
```

The rules are intended to support later validation, but this file is not a validator implementation.

P6-S3 may define:

```text
- allowed pairings
- warning pairings
- blocked pairings
- Reading V1 active compatibility
- future-compatible but inactive mappings
- fallback behavior for unsafe diagnosis
```

P6-S3 must not implement:

```text
- Python builder
- Python validator
- JSON output generation
- learner state update
- weak-point aggregation
- remediation exercise generation
- UI / HTML
- adaptive recommendation
```

### 2.2 Compatibility Status Codes

The matrix uses these status codes:

| Status | Meaning | Later Validator Behavior |
|---|---|---|
| `ALLOW` | Safe and expected combination | May pass |
| `WARN` | Possible but needs caution or later review | May pass with warning |
| `BLOCK` | Incompatible or misleading combination | Must fail later validation |
| `DEFER` | Future-compatible, not active in Reading V1 | Must not be activated in V1 |
| `REVIEW` | Human review required | Must not auto-diagnose |

### 2.3 Global Compatibility Rules

```text
G1. question_type describes surface format only. It must not be used alone to infer concept mastery.
G2. skill_area describes the primary measured skill. It must be compatible with concept_tags and cognitive_skill.
G3. concept_tags describe involved concepts. They do not automatically prove learner weakness.
G4. error_type and error_detail must be compatible.
G5. remediation_tag must be derived from error_type, error_detail, and concept_tags, not from question_type alone.
G6. A single wrong answer is only evidence. Stable weak point requires repeated evidence.
G7. If compatibility is unsafe, use unknown_error + needs_human_review + human_review_required.
```

---

## 3. Reading V1 Active Question Type Matrix

### 3.1 question_type -> skill_area

| question_type | ALLOW skill_area | WARN skill_area | BLOCK skill_area |
|---|---|---|---|
| `literal_who` | `reading`, `comprehension` | `vocabulary` | `writing`, `speaking`, `listening`, `phonics`, `spelling` |
| `literal_what` | `reading`, `comprehension`, `vocabulary` | `sentence_structure` | `writing`, `speaking`, `listening`, `phonics` |
| `literal_where` | `reading`, `comprehension` | `vocabulary` | `writing`, `speaking`, `listening`, `phonics` |
| `true_false` | `reading`, `comprehension` | `vocabulary`, `sentence_structure` | `writing`, `speaking`, `listening`, `phonics` |
| `sentence_ordering` | `reading`, `sentence_structure`, `comprehension` | `grammar` | `speaking`, `listening`, `phonics` |
| `cloze_vocabulary` | `vocabulary`, `reading` | `grammar`, `sentence_structure` | `speaking`, `listening`, `phonics` |

Rules:

```text
- Reading V1 must use only the active question_type values above.
- If a Reading V1 item uses a blocked skill_area, it should fail later validation.
- Future-compatible question types from P6-S1 remain DEFER until explicitly activated.
```

### 3.2 question_type -> cognitive_skill

| question_type | ALLOW cognitive_skill | WARN cognitive_skill | BLOCK cognitive_skill |
|---|---|---|---|
| `literal_who` | `locate_information`, `choose_answer`, `produce_word` | `match_information` | `infer_meaning`, `summarize`, `correct_error` |
| `literal_what` | `locate_information`, `choose_answer`, `produce_word`, `match_information` | `recall` | `summarize`, `correct_error` |
| `literal_where` | `locate_information`, `choose_answer`, `produce_word` | `match_information` | `infer_meaning`, `summarize`, `correct_error` |
| `true_false` | `locate_information`, `choose_answer`, `match_information` | `recognize` | `produce_sentence`, `summarize` |
| `sentence_ordering` | `sequence_information`, `match_information` | `locate_information` | `infer_meaning`, `summarize` |
| `cloze_vocabulary` | `produce_word`, `recognize`, `choose_answer` | `recall`, `apply_rule` | `summarize`, `correct_error` |

Rules:

```text
- `infer_meaning` is BLOCK for literal Reading V1 question types unless a later inference contract activates it.
- `summarize` is BLOCK for Reading V1 active item types because V1 does not define summary scoring.
- `correct_error` belongs to future error_correction tasks, not Reading V1.
```

---

## 4. skill_area -> concept_tags Matrix

### 4.1 Reading skill_area

| skill_area | ALLOW concept_tags | WARN concept_tags | BLOCK concept_tags |
|---|---|---|---|
| `reading` | `literal_comprehension`, `detail_finding`, `explicit_detail`, `sequence`, `character_action`, `setting`, `who_reference`, `what_reference`, `where_reference`, `source_sentence_order`, `picture_text_matching` | vocabulary topic tags such as `food_words`, `animal_words`, `home_words` | pure output tags such as `paragraph_structure`, `topic_sentence`, `ending_sentence` |
| `comprehension` | `main_idea`, `detail_finding`, `explicit_detail`, `sequence`, `cause_effect`, `literal_comprehension` | `inference` | grammar-only tags when no grammar task exists |

### 4.2 Vocabulary skill_area

| skill_area | ALLOW concept_tags | WARN concept_tags | BLOCK concept_tags |
|---|---|---|---|
| `vocabulary` | `animal_words`, `school_objects`, `family_words`, `food_words`, `color_words`, `number_words`, `action_verbs`, `emotion_words`, `place_words`, `body_parts`, `clothes_words`, `weather_words`, `transportation_words`, `home_words`, `shopping_words`, `health_words`, `hobby_words`, `time_words` | reading tags when source detail is involved | writing structure tags without lexical target |

### 4.3 Grammar and sentence structure skill_area

| skill_area | ALLOW concept_tags | WARN concept_tags | BLOCK concept_tags |
|---|---|---|---|
| `grammar` | `be_verb`, `am_is_are`, `present_simple`, `third_person_singular_s`, `do_does_question`, `there_is_are`, `singular_plural`, `articles_a_an_the`, `preposition_place`, `wh_questions`, `subject_verb_agreement`, `auxiliary_do_does`, `verb_tense` | vocabulary topic tags when grammar item is contextualized | pure reading tags without grammar operation |
| `sentence_structure` | `sentence_order`, `word_order`, `simple_sentence`, `svo_sentence`, `svc_sentence`, `subject_verb_agreement`, `sentence_fragment` | grammar tags when structure is involved | pure vocabulary topic tags without structure task |

Rules:

```text
- A concept tag may be allowed as secondary context, but P6-S3 only controls primary compatibility.
- A Reading V1 literal item should normally include at least one reading concept tag.
- A cloze_vocabulary item should include at least one vocabulary concept tag.
```

---

## 5. error_type -> error_detail Matrix

### 5.1 Allowed error detail mappings

| error_type | ALLOW error_detail |
|---|---|
| `reading_detail_error` | `missed_explicit_detail`, `wrong_who_reference`, `wrong_what_reference`, `wrong_where_reference`, `wrong_sequence_order`, `source_sentence_mismatch`, `picture_text_mismatch`, `literal_question_misread`, `unsupported_answer_from_source` |
| `source_evidence_error` | `source_sentence_mismatch`, `unsupported_answer_from_source`, `picture_text_mismatch` |
| `vocabulary_gap` | `unknown_word`, `wrong_word_meaning`, `confused_similar_words`, `wrong_topic_word`, `color_word_confusion`, `number_word_confusion`, `place_word_confusion`, `action_verb_confusion` |
| `question_misread` | `literal_question_misread`, `wrong_who_reference`, `wrong_what_reference`, `wrong_where_reference` |
| `rule_application_error` | `missing_third_person_s`, `wrong_be_verb`, `there_is_are_confusion`, `there_are_plural_noun_error`, `singular_plural_confusion`, `wrong_preposition`, `wrong_word_order`, `wrong_auxiliary_do_does`, `wrong_tense`, `article_missing`, `article_confusion`, `pronoun_confusion`, `subject_verb_agreement_error`, `verb_form_error` |
| `concept_error` | same as `rule_application_error`, but only with repeated evidence or human confirmation |
| `spelling_error` | `spelling_blocks_answer` |
| `sentence_structure_error` | `wrong_word_order`, `sentence_fragment`, `missing_subject`, `missing_verb`, `missing_article_and_be_verb` |
| `insufficient_output` | `incomplete_answer`, `answer_too_short`, `sentence_fragment` |
| `answer_format_error` | `wrong_answer_format`, `incomplete_answer`, `answer_too_short` |
| `unknown_error` | `not_enough_evidence`, `needs_human_review` |

### 5.2 Blocked error detail mappings

```text
- reading_detail_error + grammar-only details such as missing_third_person_s = BLOCK
- vocabulary_gap + grammar-only details such as wrong_be_verb = BLOCK
- rule_application_error + unknown_word = BLOCK unless the item is explicitly grammar-vocabulary mixed and later review allows it
- concept_error + any detail from a single isolated wrong answer with high confidence = BLOCK
- unknown_error + a specific grammar/vocabulary/reading detail = BLOCK; use the specific error_type instead
```

### 5.3 Confidence restrictions

| error_type | high confidence allowed from one answer? | Rule |
|---|---:|---|
| `reading_detail_error` | Yes, if source evidence is explicit | Source evidence required |
| `source_evidence_error` | Yes, if source conflict is explicit | Source evidence required |
| `vocabulary_gap` | Warn only | Prefer medium or low unless repeated evidence exists |
| `rule_application_error` | Warn only | High confidence requires repeated same-rule evidence or human review |
| `concept_error` | No | Requires repeated evidence or human confirmation |
| `question_misread` | No | Usually low/medium unless human confirmed |
| `careless_error` | No | Should be REVIEW unless strong evidence exists |
| `unknown_error` | No | Confidence must be low |

---

## 6. error_detail -> remediation_tag Matrix

### 6.1 Reading remediation mappings

| error_detail | ALLOW remediation_tag |
|---|---|
| `missed_explicit_detail` | `practice_reading_detail_questions`, `practice_source_evidence_lookup` |
| `wrong_who_reference` | `practice_literal_who_questions`, `practice_source_evidence_lookup` |
| `wrong_what_reference` | `practice_literal_what_questions`, `practice_reading_detail_questions` |
| `wrong_where_reference` | `practice_literal_where_questions`, `practice_source_evidence_lookup` |
| `wrong_sequence_order` | `practice_sentence_ordering` |
| `source_sentence_mismatch` | `practice_source_evidence_lookup` |
| `picture_text_mismatch` | `practice_picture_text_matching` |
| `literal_question_misread` | `practice_reading_detail_questions` |
| `unsupported_answer_from_source` | `practice_source_evidence_lookup` |

### 6.2 Grammar remediation mappings

| error_detail | ALLOW remediation_tag |
|---|---|
| `missing_third_person_s` | `practice_third_person_s`, `practice_present_simple_he_she_it` |
| `wrong_be_verb` | `practice_be_verb_am_is_are` |
| `there_is_are_confusion` | `review_there_is_are` |
| `there_are_plural_noun_error` | `practice_there_is_are_plural` |
| `singular_plural_confusion` | `practice_there_is_are_plural` |
| `wrong_preposition` | `practice_preposition_in_on_under` |
| `wrong_auxiliary_do_does` | `practice_do_does_questions` |
| `article_missing` | `practice_articles_a_an_the` |
| `article_confusion` | `practice_articles_a_an_the` |
| `subject_verb_agreement_error` | `practice_subject_verb_agreement` |
| `wrong_word_order` | `practice_word_order` |

### 6.3 Vocabulary remediation mappings

| error_detail | ALLOW remediation_tag |
|---|---|
| `unknown_word` | vocabulary topic review tag matching concept_tags |
| `wrong_word_meaning` | vocabulary topic review tag matching concept_tags |
| `confused_similar_words` | vocabulary topic review tag matching concept_tags |
| `wrong_topic_word` | vocabulary topic review tag matching concept_tags |
| `color_word_confusion` | `vocabulary_color_words_review` |
| `number_word_confusion` | `vocabulary_number_words_review` |
| `place_word_confusion` | `vocabulary_place_words_review` |
| `action_verb_confusion` | `vocabulary_action_verbs_review` |

### 6.4 Output remediation mappings

| error_detail | ALLOW remediation_tag |
|---|---|
| `incomplete_answer` | `practice_complete_answer_sentence` |
| `answer_too_short` | `practice_complete_answer_sentence` |
| `wrong_answer_format` | `practice_complete_answer_sentence` or `human_review_required` |
| `spelling_blocks_answer` | `practice_spelling_target_words` |
| `missing_article_and_be_verb` | `practice_simple_sentence` |
| `sentence_fragment` | `practice_sentence_fragment_repair`, `rebuild_svo_sentence` |
| `missing_subject` | `rebuild_svo_sentence` |
| `missing_verb` | `rebuild_svo_sentence` |

### 6.5 Fallback mappings

| error_detail | REQUIRED remediation_tag |
|---|---|
| `not_enough_evidence` | `human_review_required` or `no_remediation_assigned` |
| `needs_human_review` | `human_review_required` |

Rules:

```text
- remediation_tag must not be selected from question_type alone.
- remediation_tag should primarily follow error_detail, then concept_tags.
- When concept_tags and error_detail conflict, use human_review_required.
```

---

## 7. Reading V1 Active Compatibility Profiles

### 7.1 literal_who profile

```text
question_type: literal_who
ALLOW skill_area: reading, comprehension
ALLOW concept_tags: literal_comprehension, detail_finding, who_reference, character_action
ALLOW cognitive_skill: locate_information, choose_answer, produce_word
ALLOW error_type: reading_detail_error, question_misread, source_evidence_error, answer_format_error, unknown_error
ALLOW error_detail: wrong_who_reference, missed_explicit_detail, literal_question_misread, unsupported_answer_from_source, not_enough_evidence, needs_human_review
ALLOW remediation_tag: practice_literal_who_questions, practice_reading_detail_questions, practice_source_evidence_lookup, human_review_required
```

### 7.2 literal_what profile

```text
question_type: literal_what
ALLOW skill_area: reading, comprehension, vocabulary
ALLOW concept_tags: literal_comprehension, detail_finding, what_reference, explicit_detail, vocabulary topic tags
ALLOW cognitive_skill: locate_information, choose_answer, produce_word, match_information
ALLOW error_type: reading_detail_error, vocabulary_gap, question_misread, source_evidence_error, answer_format_error, unknown_error
ALLOW error_detail: wrong_what_reference, missed_explicit_detail, unknown_word, wrong_word_meaning, literal_question_misread, unsupported_answer_from_source, not_enough_evidence, needs_human_review
ALLOW remediation_tag: practice_literal_what_questions, practice_reading_detail_questions, vocabulary topic review tag, practice_source_evidence_lookup, human_review_required
```

### 7.3 literal_where profile

```text
question_type: literal_where
ALLOW skill_area: reading, comprehension
ALLOW concept_tags: literal_comprehension, detail_finding, where_reference, setting, place_words
ALLOW cognitive_skill: locate_information, choose_answer, produce_word
ALLOW error_type: reading_detail_error, vocabulary_gap, question_misread, source_evidence_error, answer_format_error, unknown_error
ALLOW error_detail: wrong_where_reference, missed_explicit_detail, place_word_confusion, literal_question_misread, unsupported_answer_from_source, not_enough_evidence, needs_human_review
ALLOW remediation_tag: practice_literal_where_questions, vocabulary_place_words_review, practice_source_evidence_lookup, human_review_required
```

### 7.4 true_false profile

```text
question_type: true_false
ALLOW skill_area: reading, comprehension
ALLOW concept_tags: literal_comprehension, explicit_detail, detail_finding, source_sentence_order
ALLOW cognitive_skill: locate_information, choose_answer, match_information
ALLOW error_type: reading_detail_error, source_evidence_error, question_misread, unknown_error
ALLOW error_detail: missed_explicit_detail, source_sentence_mismatch, unsupported_answer_from_source, literal_question_misread, not_enough_evidence, needs_human_review
ALLOW remediation_tag: practice_reading_detail_questions, practice_source_evidence_lookup, human_review_required
```

### 7.5 sentence_ordering profile

```text
question_type: sentence_ordering
ALLOW skill_area: reading, sentence_structure, comprehension
ALLOW concept_tags: sequence, source_sentence_order, sentence_order, word_order
ALLOW cognitive_skill: sequence_information, match_information
ALLOW error_type: reading_detail_error, sentence_structure_error, source_evidence_error, unknown_error
ALLOW error_detail: wrong_sequence_order, source_sentence_mismatch, wrong_word_order, not_enough_evidence, needs_human_review
ALLOW remediation_tag: practice_sentence_ordering, practice_word_order, practice_source_evidence_lookup, human_review_required
```

### 7.6 cloze_vocabulary profile

```text
question_type: cloze_vocabulary
ALLOW skill_area: vocabulary, reading
ALLOW concept_tags: vocabulary topic tags, detail_finding, explicit_detail
ALLOW cognitive_skill: produce_word, recognize, choose_answer
ALLOW error_type: vocabulary_gap, reading_detail_error, answer_format_error, spelling_error, unknown_error
ALLOW error_detail: unknown_word, wrong_word_meaning, confused_similar_words, wrong_topic_word, missed_explicit_detail, wrong_answer_format, spelling_blocks_answer, not_enough_evidence, needs_human_review
ALLOW remediation_tag: vocabulary topic review tag, practice_reading_detail_questions, practice_spelling_target_words, human_review_required
```

---

## 8. Block Rules

The following combinations are blocked for P6-compatible records:

```text
B1. literal_who + remediation_tag selected from food/color/number vocabulary review without matching concept_tags = BLOCK
B2. literal_where + error_detail missing_third_person_s = BLOCK
B3. cloze_vocabulary + error_type concept_error + high confidence from one answer = BLOCK
B4. sentence_ordering + remediation_tag practice_literal_who_questions = BLOCK unless error_detail is wrong_who_reference and human review confirms
B5. true_false + cognitive_skill summarize = BLOCK
B6. any Reading V1 active question_type + skill_area speaking/listening = BLOCK
B7. unknown_error + specific remediation other than human_review_required/no_remediation_assigned = BLOCK
B8. concept_error + diagnosis_confidence high without repeated_same_error or human_review_note = BLOCK
B9. remediation_link_record that creates generated content instead of a tag link = BLOCK
B10. error_detail not compatible with error_type = BLOCK
```

---

## 9. Warning Rules

The following combinations are allowed only with warning:

```text
W1. literal_what + vocabulary_gap = WARN unless the target answer is explicitly a vocabulary item.
W2. cloze_vocabulary + grammar skill_area = WARN unless the blank tests grammar form.
W3. sentence_ordering + grammar skill_area = WARN unless word_order or sentence_order is the tested concept.
W4. careless_error = REVIEW unless human evidence exists.
W5. question_misread = WARN because automatic proof is weak without learner explanation.
W6. vocabulary_gap from one wrong answer = WARN; prefer low/medium confidence.
W7. rule_application_error from one wrong answer = WARN; high confidence requires repetition or review.
W8. remediation_tag based only on concept_tags without error_detail = WARN.
```

---

## 10. Later Validator Hint

A later validator may implement this compatibility order:

```text
1. Validate question_type is active or deferred.
2. Validate skill_area is compatible with question_type.
3. Validate concept_tags are compatible with skill_area.
4. Validate cognitive_skill is compatible with question_type.
5. Validate error_type is compatible with error_detail.
6. Validate remediation_tag is compatible with error_detail and concept_tags.
7. Apply confidence restrictions.
8. Apply block rules.
9. Apply warning rules.
10. Require human_review_required for unsafe diagnosis.
```

This is only an implementation hint. P6-S3 does not create a validator.

---

## 11. Gate and Distance Update

Gate Metrics:

```text
PASS - question_type to skill_area compatibility defined
PASS - question_type to cognitive_skill compatibility defined
PASS - skill_area to concept_tags compatibility defined
PASS - error_type to error_detail compatibility defined
PASS - error_detail to remediation_tag compatibility defined
PASS - Reading V1 active profiles defined
PASS - block rules defined
PASS - warning rules defined
PASS - runtime/code untouched
PASS - validator implementation deferred
PASS - weak-point aggregation remains out of scope
PASS - adaptive recommendation remains out of scope
```

Distance Vector:

```text
D_P6 = 5 sub-tasks left after P6-S3
E4S-P6-S3_ErrorTaggingCompatibilityMatrix_DesignScan -> COMPLETED
E4S-P6 -> COMPATIBILITY_MATRIX_DEFINED
ERROR_TAGGING_RUNTIME -> NOT_STARTED
WEAK_POINT_ENGINE -> NOT_STARTED
```

---

## 12. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P6-S4_ErrorTaggingValidatorContract_DesignScan
```

Unique next action:

```text
Create docs/ulga/E4S_P6_ERROR_TAGGING_VALIDATOR_CONTRACT.md
```

P6-S4 should define validator responsibilities, inputs, outputs, PASS/WARN/FAIL behavior, and non-goals.

P6-S4 must not implement the validator code, builders, UI, generated data, learner mastery scoring, weak-point aggregation, or adaptive recommendation.

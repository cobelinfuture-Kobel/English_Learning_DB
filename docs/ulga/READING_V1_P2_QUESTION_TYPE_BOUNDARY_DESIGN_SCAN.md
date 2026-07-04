# ReadingV1 P2 Question Type Boundary Design Scan

Task:
ReadingV1_P2_QuestionTypeBoundary_DesignScan

Scope:
Define allowed, deferred, and blocked question types for P2 private-homework assessment-like practice.

---

## 1. Allowed Question Types

```text
literal_who
literal_what
literal_where
literal_when
yes_no_text_check
true_false_text_check
single_detail_match
picture_word_match
simple_sequence_order
```

Allowed constraints:

```text
private homework only
learner-facing display payload only
no hidden source payload display
no public export
no learner-state scoring
```

---

## 2. Deferred Question Types

```text
why_question
how_question
main_idea
inference
summary
open_response
multi_sentence_explanation
```

Reason:
Requires stronger scoring, review, and answer-key boundaries.

---

## 3. Blocked Question Types

```text
public_exam_simulation
high_stakes_assessment
automatic_grade_promotion
source_text_reconstruction
commercial_export_item
```

Reason:
Outside P2 design-only private homework boundary.

---

## 4. Boundary Result

```text
allowed_question_type_count = 9
deferred_question_type_count = 7
blocked_question_type_count = 5
```

Next task:

```text
ReadingV1_P2_ScoringBoundary_DesignScan
```

Task status:

```text
ReadingV1_P2_QuestionTypeBoundary_DesignScan -> COMPLETED
```

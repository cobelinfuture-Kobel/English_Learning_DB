# RAZ Pattern-Based Private Homework Policy Design Scan

## 1. Current State

```text
Project: English_Learning_DB / E4S Reading V1 follow-up
Task: RAZ_PatternBasedPrivateHomeworkPolicy_DesignScan
Deliverable: docs/ulga/RAZ_PATTERN_BASED_PRIVATE_HOMEWORK_POLICY_DESIGN_SCAN.md
Task type: Policy DesignScan
```

This document defines a pattern-based private-homework lane for using RAZ as a source of level/topic/skill inspiration without storing or outputting RAZ source text.

This is documentation-only. It does not copy RAZ source text, does not create HTML, does not create worksheet output, does not create public preview, does not create learner state, does not create adaptive recommendation, and does not promote source/content authority.

Baseline before this task:

```text
RAZ private homework lane = conditionally allowed
RAZ public/general payload display = blocked
RAZ evidence text display = blocked
bulk RAZ text database = blocked
current Reading V1 candidates = internal review records only
```

---

## 2. Policy Problem

The operator asked whether RAZ can be used without outputting original text, by taking the same sentence pattern and changing nouns/adjectives.

Policy answer:

```text
Using abstract sentence/grammar patterns is allowed under a private-homework lane if source text is not stored, not output, and not closely paraphrased.
```

However, the system must distinguish:

```text
allowed: abstract grammar pattern + new slot values + newly generated sentence
blocked: original sentence copy
blocked: near-copy with only nouns/adjectives swapped
blocked: sequence-preserving paraphrase of a RAZ passage
blocked: bulk pattern extraction that reconstructs the book/passage
```

---

## 3. Pattern-Based Lane Decision

New lane:

```text
LANE_D_RAZ_PATTERN_BASED_PRIVATE_HOMEWORK
```

Status:

```text
CONDITIONALLY_ALLOWED
```

Scope:

```text
private homework only
private repository only
locator-first
source_text_stored = false
source_payload_copied = false
not GitHub Pages
not public preview
not commercial worksheet
not bulk RAZ text database
```

---

## 4. Allowed Pattern Abstraction

Allowed pattern abstraction means the artifact stores only a generalized language frame, not the source expression.

Examples of allowed abstraction:

```text
The [adjective] [noun] is in the [place].
I can see a [adjective] [noun].
[Person] has a [adjective] [object].
There is a [noun] on the [place].
[Person] likes the [adjective] [noun].
```

Allowed derived metadata:

```text
grammar_focus
slot_types
allowed_slot_values
question_type_fit
level_band_hint
source_locator
source_level_hint
topic_hint
review_status
```

Allowed generated output:

```text
operator-authored or system-generated new sentences
new slot values not copied from the source sentence
new topic variants
private household homework practice
local/private printable HTML in a future gated task
```

---

## 5. Blocked Pattern Use

Blocked uses:

```text
store original RAZ sentence
store original RAZ passage
store full book text
store sequence of sentence patterns that reconstructs a RAZ passage
swap only one or two nouns/adjectives while preserving the source sentence expression
keep unique RAZ story characters, scene order, event sequence, or distinctive phrasing
bulk extract all sentence frames from a book/level
publish pattern-generated materials to GitHub Pages
sell or share generated worksheets outside household
```

Hard rule:

```text
Pattern abstraction must not be reversible into the original RAZ passage.
```

---

## 6. Difference Between Pattern Use and Close Paraphrase

Allowed pattern use:

```text
source_text_stored = false
source_sentence_stored = false
pattern_abstraction = generalized grammar frame
slot_values = new/operator-controlled words
output_sentence = newly generated text
story_sequence_preserved = false
```

Blocked close paraphrase:

```text
source_text_stored = true or source_sentence_stored = true
pattern keeps distinctive source wording
only nouns/adjectives are swapped
same character/setting/event sequence is preserved
output could be recognized as the source sentence/passage
```

Decision rule:

```text
If a reviewer can identify the RAZ original from the generated output and locator alone, the output is too close and must be revised.
```

---

## 7. Required Fields for Future Pattern Artifacts

Any future pattern artifact must include:

```text
pattern_id
source_locator
source_level_hint
source_topic_hint
source_text_stored = false
source_sentence_stored = false
source_payload_copied = false
pattern_abstraction
pattern_abstraction_method
slot_schema
allowed_slot_values
blocked_source_specific_values
grammar_focus
question_type_fit
generated_text_origin
private_homework_scope = true
repo_visibility_required = private
github_pages_allowed = false
public_distribution_allowed = false
commercial_use_allowed = false
bulk_pattern_extraction_allowed = false
near_paraphrase_check_required = true
review_status
```

Recommended values:

```text
pattern_abstraction_method = grammar_frame_only | syntax_frame_only | function_frame_only
generated_text_origin = operator_authored | system_generated_from_pattern | human_reviewed_pattern_generated
review_status = draft | needs_review | passed_private_homework_review | rejected_too_close_to_source
```

---

## 8. Slot Replacement Policy

Slot replacement must be broad enough to create new text.

Allowed slot categories:

```text
person_name
animal
object
color
adjective
place
action_verb
preposition
time_phrase
feeling_word
quantity
```

Slot replacement rules:

```text
use project-controlled word lists
prefer A1 / RAZ-level-appropriate vocabulary
avoid source-specific named characters
avoid source-specific object sequences
avoid copying rare adjective-noun combinations from source
avoid preserving original story order
```

Minimum novelty guideline:

```text
At least two meaningful slots should change for simple sentence drills.
For paragraph-style output, character, setting, event order, and noun/adjective sets must be newly generated.
```

---

## 9. Future Validator Rules

Future validators should block pattern artifacts if:

```text
source_text_stored != false
source_sentence_stored != false
source_payload_copied != false
github_pages_allowed != false
public_distribution_allowed != false
commercial_use_allowed != false
bulk_pattern_extraction_allowed != false
near_paraphrase_check_required != true
pattern_abstraction is empty
slot_schema is empty
generated_text_origin is missing
```

Future validators should warn if:

```text
source_locator is missing
source_level_hint is missing
grammar_focus is missing
question_type_fit is missing
blocked_source_specific_values is empty
review_status != passed_private_homework_review
```

Future validators should add a qualitative/manual review checkpoint:

```text
CLOSE_PARAPHRASE_RISK_REVIEW_REQUIRED
```

Manual review must ask:

```text
Does the generated sentence preserve distinctive source wording?
Does it preserve a source-specific story sequence?
Does it merely replace nouns/adjectives?
Could a reader identify the RAZ passage from the generated output?
```

---

## 10. Example Artifact Shape

Example only. This file does not create actual pattern artifacts.

```json
{
  "pattern_id": "raz_pattern_private_homework_001",
  "source_locator": "RAZ_LEVEL_A_BOOK_X_PAGE_Y",
  "source_level_hint": "RAZ_A",
  "source_topic_hint": "school_objects",
  "source_text_stored": false,
  "source_sentence_stored": false,
  "source_payload_copied": false,
  "pattern_abstraction": "The [adjective] [noun] is in the [place].",
  "pattern_abstraction_method": "grammar_frame_only",
  "slot_schema": {
    "adjective": ["small", "big", "red", "happy"],
    "noun": ["cat", "dog", "ball", "robot"],
    "place": ["box", "bag", "room", "yard"]
  },
  "blocked_source_specific_values": ["source character names", "source-specific object sequence"],
  "grammar_focus": "be verb + prepositional phrase",
  "question_type_fit": ["literal_what", "literal_where", "literal_yes_no"],
  "generated_text_origin": "system_generated_from_pattern",
  "private_homework_scope": true,
  "repo_visibility_required": "private",
  "github_pages_allowed": false,
  "public_distribution_allowed": false,
  "commercial_use_allowed": false,
  "bulk_pattern_extraction_allowed": false,
  "near_paraphrase_check_required": true,
  "review_status": "draft"
}
```

---

## 11. Output Policy for Future HTML

A future private homework HTML export may display:

```text
pattern_id
pattern_abstraction
generated new sentences
slot practice table
private homework questions
answer key for generated sentences
source locator for internal reference
not-for-public-export notice
```

It must not display:

```text
RAZ original sentence
RAZ passage text
RAZ evidence text
full book/page text
source-specific story sequence
GitHub Pages/public preview link
commercial worksheet packaging
```

---

## 12. Relationship to Existing Policies

This policy does not replace `RAZ_PRIVATE_HOMEWORK_USE_POLICY_DESIGN_SCAN.md`.

It specializes it:

```text
RAZ private homework lane = conditionally allowed
RAZ source text storage = still blocked by default
RAZ pattern abstraction = conditionally allowed
RAZ pattern-generated new text = conditionally allowed for private homework
public/commercial output = still blocked
```

This policy also does not replace `E4S_P1_READING_V1_SOURCE_PAYLOAD_DISPLAY_POLICY.md`.

For public/general Reading V1 output, existing blocks remain:

```text
source_quote_display = blocked
source_excerpt_display = blocked
full_source_payload_display = blocked
evidence_text_display = blocked
```

---

## 13. What This Enables Later

This design scan enables a future task such as:

```text
RAZ_PatternArtifactSchema_DesignScan
```

or:

```text
RAZ_PatternBasedPrivateHomeworkGenerator_DesignScan
```

Potential later implementation, if approved:

```text
RAZ_PatternBasedPrivateHomeworkGenerator_Implementation
```

But those later tasks must remain bounded:

```text
no RAZ source text storage
no public output
no GitHub Pages
no commercial worksheet
no bulk pattern extraction
private homework only
```

---

## 14. Acceptance Gates

| Gate | Result | Evidence |
|---|---:|---|
| Existing private homework policy respected | PASS | Sections 1, 12 |
| Existing public/source payload block respected | PASS | Sections 1, 12 |
| Pattern lane defined separately | PASS | Section 3 |
| Pattern abstraction allowed only without source text | PASS | Sections 4, 6, 7 |
| Close paraphrase blocked | PASS | Sections 5, 6, 9 |
| Required future fields defined | PASS | Section 7 |
| Slot replacement policy defined | PASS | Section 8 |
| Validator rules defined | PASS | Section 9 |
| Future HTML output boundaries defined | PASS | Section 11 |
| No RAZ source text copied | PASS | Documentation only |
| No HTML created | PASS | Documentation only |
| No worksheet created | PASS | Documentation only |
| No learner state/adaptive output created | PASS | Documentation only |
| No source/content authority promotion | PASS | Documentation only |

Result:

```text
ACCEPTANCE_GATES = PASS_WITH_WARNINGS
```

---

## 15. Known Warnings

```text
warning_id: RAZ-PATTERN-WARN-001
severity: medium
classification: CLOSE_PARAPHRASE_REVIEW_REQUIRED
message: Pattern-generated output must be reviewed to avoid close paraphrase or reconstruction of the source sentence/passage.
blocks_current_task: no
```

```text
warning_id: RAZ-PATTERN-WARN-002
severity: medium
classification: NO_PATTERN_ARTIFACT_CREATED
message: This DesignScan defines policy only; no pattern artifact, schema, generator, HTML, or worksheet was created.
blocks_current_task: no
```

```text
warning_id: RAZ-PATTERN-WARN-003
severity: medium
classification: NO_TEST_RUN
message: Documentation-only design scan; no local tests or GitHub Actions CI were run.
blocks_current_task: no
```

---

## 16. Handoff Block

```text
CURRENT_TASK = RAZ_PatternBasedPrivateHomeworkPolicy_DesignScan
FILES_CREATED_OR_MODIFIED = docs/ulga/RAZ_PATTERN_BASED_PRIVATE_HOMEWORK_POLICY_DESIGN_SCAN.md
ACCEPTANCE_GATES = PASS_WITH_WARNINGS
RAZ_PATTERN_BASED_PRIVATE_HOMEWORK = CONDITIONALLY_ALLOWED
SOURCE_TEXT_STORED_ALLOWED = false
SOURCE_SENTENCE_STORED_ALLOWED = false
SOURCE_PAYLOAD_COPIED_ALLOWED = false
CLOSE_PARAPHRASE_ALLOWED = false
BULK_PATTERN_EXTRACTION_ALLOWED = false
PRIVATE_REPO_REQUIRED = true
GITHUB_PAGES_ALLOWED = false
PUBLIC_PREVIEW_ALLOWED = false
COMMERCIAL_USE_ALLOWED = false
NEXT_RECOMMENDED_TASK = RAZ_PatternArtifactSchema_DesignScan
DRIFT_RISK = low
DRIFT_REASON = Pattern policy is separated from source payload display; no runtime/export/source-text behavior changed.
```

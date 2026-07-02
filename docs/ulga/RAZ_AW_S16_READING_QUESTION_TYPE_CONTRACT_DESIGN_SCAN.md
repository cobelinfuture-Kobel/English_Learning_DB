# RAZ-AW-S16 Reading Question Type Contract Design Scan

## 1. Task

`RAZ-AW-S16_ReadingQuestionTypeContract_DesignScan`

This task defines the V1 Reading question-type contracts that sit between the S15 source selector and the later S17 candidate item builder.

The task is documentation-only. It defines exact prompt, answer, evidence, distractor, rejection, and validation requirements for the six approved Reading System V1 question-type families.

S16 does not generate Reading items, does not write a builder, does not write a validator, and does not rebuild any generated index.

## 2. Scope

This design scan defines:

1. Question-type contract purpose and boundary.
2. Approved V1 question-type families.
3. Shared question-type requirements.
4. Per-type source feature requirements.
5. Per-type prompt construction rules.
6. Per-type answer construction rules.
7. Per-type distractor policy.
8. Per-type evidence support rules.
9. Per-type rejection rules.
10. Per-type validator expectations for S18.
11. S17 implementation handoff requirements.
12. S18 validation handoff requirements.

## 3. Allowed Files

This task may create or modify only:

```text
docs/ulga/RAZ_AW_S16_READING_QUESTION_TYPE_CONTRACT_DESIGN_SCAN.md
```

## 4. Forbidden Files

This task must not modify:

```text
ulga/builders/*
ulga/validators/*
ulga/audits/*
tests/*
ulga/graph/*
ulga/reports/*
site/*
runtime/*
learner_state/*
dashboard/*
```

## 5. Current-task Blockers

S16 is blocked if it fails to define any of the following:

1. All six approved V1 question-type families.
2. Source feature requirements for each family.
3. Prompt construction rules for each family.
4. Answer construction rules for each family.
5. Distractor policy for choice-based families.
6. Evidence support rule for each family.
7. Rejection rules for each family.
8. Handoff requirements for S17 and S18.
9. Explicit boundary that S16 does not generate items.

## 6. Warning Policy

Allowed warnings:

```text
exact NLP implementation deferred to S17
validator implementation deferred to S18
output package implementation deferred to S19
closeout QA deferred to S20
some source records may be structurally eligible but rejected by question-type feature rules
heuristic extraction may be used later only if validator can prove evidence support
```

Blocking warnings:

```text
question type has no evidence rule
question type has no answer model mapping
question type permits unsupported answer generation
question type requires learner-facing promotion
question type requires generated artifacts in S16
question type requires builder implementation in S16
```

## 7. Generated Artifact Policy

No generated artifacts are allowed in this task.

This task must not create, rebuild, commit, or move:

```text
ulga/graph/raz_reading_authority_intake_query_index.json
ulga/reports/raz_reading_authority_intake_query_index_summary.json
ulga/reports/raz_reading_authority_intake_query_index_readback_qa.json
ulga/graph/reading_practice_items.json
ulga/reports/reading_practice_items_summary.json
reading_source_selection.json
reading_question_type_contracts.json
reading_practice_items.json
reading_practice_package_summary.json
```

## 8. Runtime Impact

None.

This task does not affect runtime, app code, dashboards, APIs, schedulers, learner state, adaptive planner state, or student-facing output.

## 9. Promotion Impact

None.

All future items using these contracts remain:

```text
candidate_only
not_promoted
not learner_facing
not final authority
```

S16 does not approve final Reading Authority promotion and does not approve learner-facing delivery.

## 10. Stop Condition

S16 passes when this document defines:

1. The six approved V1 question-type contracts.
2. Compatible source types per question type.
3. Compatible answer model type per question type.
4. Source feature requirements per question type.
5. Prompt construction rules per question type.
6. Answer construction rules per question type.
7. Distractor policy per question type.
8. Evidence support rule per question type.
9. Rejection rules per question type.
10. Validator expectations for S18.
11. Handoff requirements for S17 and S18.

S16 must stop after this contract is defined. It must not write a builder, validator, test, generated JSON, runtime output, or learner-facing artifact.

## 11. Deferred Issues Register

| Issue ID | Classification | Why deferred | Recommended future task | Blocks S16? |
|---|---|---|---|---|
| `S17-ITEM-BUILDER` | `FUTURE_WORK` | Builder implementation is forbidden in S16 | `RAZ-AW-S17_ReadingCandidateItemBuilder_Implementation` | No |
| `S18-VALIDATOR` | `FUTURE_WORK` | Validator implementation is forbidden in S16 | `RAZ-AW-S18_ReadingItemValidator_Implementation` | No |
| `S19-OUTPUT-PACKAGE` | `FUTURE_WORK` | Quiz/worksheet output is downstream of item generation and validation | `RAZ-AW-S19_ReadingPracticeOutputPackage_Implementation` | No |
| `S20-CLOSEOUT-QA` | `FUTURE_WORK` | System-level closeout belongs after generated items, validator, and output package | `RAZ-AW-S20_ReadingPracticeCloseoutQA` | No |
| `INFERENCE-QUESTIONS` | `FUTURE_WORK` | Inference requires semantic/rubric policy outside V1 | Reading System V2 or later | No |
| `MAIN-IDEA-QUESTIONS` | `FUTURE_WORK` | Main idea requires passage-level abstraction and longer-context validation | Reading System V2 or later | No |
| `OPEN-ENDED-SHORT-ANSWER` | `FUTURE_WORK` | Open-ended scoring requires rubric and semantic validation | Reading System V2/V3 | No |
| `LEARNER-ERROR-TAGGING` | `FUTURE_WORK` | Error diagnosis requires learner answer-attempt data | Reading System V3 | No |

## 12. Source References

S16 follows S14, which defines `READING_PRACTICE_ITEM_V1`, its top-level item fields, the source object, evidence object, prompt object, answer model, tags, validation object, and lifecycle boundary.

S14 approves these generic answer model types for V1:

```text
single_choice
true_false
ordered_sequence
cloze_text
```

S14 maps those answer types to the V1 question-type families:

| Answer type | Compatible question-type families |
|---|---|
| `single_choice` | `literal_who`, `literal_what`, `literal_where` |
| `true_false` | `true_false` |
| `ordered_sequence` | `sentence_ordering` |
| `cloze_text` | `cloze_vocabulary` |

S16 also follows S15, which defines approved source input families, sentence-count policy, reusability tag policy, source suitability matrix, ranking bands, and source mapping into the S14 item source/evidence objects.

S15 explicitly requires S16 to decide, per question type:

1. Whether source text is shown to the learner.
2. Whether answer phrase extraction is deterministic or heuristic.
3. Whether choices are required.
4. Whether distractors must come from the same source, same level, same theme, or fixed safe pool.
5. Which source records must be rejected even if S15 says they are structurally eligible.

## 13. Approved V1 Question-Type Families

S16 approves exactly these V1 question-type families:

```text
literal_who
literal_what
literal_where
true_false
sentence_ordering
cloze_vocabulary
```

No other question-type family may be generated during Reading System V1 without a later contract patch.

## 14. Shared V1 Question-Type Requirements

Every V1 question type must satisfy the following:

1. Source text is selected through the S15 selector contract.
2. Source traceability is preserved in the S14 `source` object.
3. Evidence text is copied from source text, not invented.
4. Correct answer is supported by evidence.
5. Answer model type is compatible with the question-type family.
6. Generated item remains candidate-only and not learner-facing.
7. Validator status begins as `not_run` unless S18 validation is explicitly in scope.
8. No generated passage may be used as original source text.
9. No open-ended semantic grading is permitted in V1.
10. No source promotion is implied by question generation.

## 15. Shared Prompt Rules

All V1 prompts must include:

```text
stem
instructions
```

Choice-based prompts must include:

```text
choices
```

Display of source text is controlled per question type.

Default instruction style:

| Question type | Default instruction |
|---|---|
| `literal_who` | `Choose the correct answer.` |
| `literal_what` | `Choose the correct answer.` |
| `literal_where` | `Choose the correct answer.` |
| `true_false` | `Choose True or False.` |
| `sentence_ordering` | `Put the sentences in the correct order.` |
| `cloze_vocabulary` | `Choose the word that completes the sentence.` |

Prompt text may be rewritten by S17 only within these contracts and only if evidence support remains provable.

## 16. Shared Distractor Rules

Distractors must be safe, level-appropriate, and non-contradictory with evidence rules.

Allowed distractor sources for V1:

```text
same_source_non_answer_token
same_level_safe_pool
same_theme_safe_pool
fixed_question_type_safe_pool
```

Forbidden distractors:

```text
unsupported answer marked as correct
source text invented as if original
higher-level vocabulary without policy
semantically offensive or inappropriate text
ambiguous alternative that could also be correct
metadata strings, file names, IDs, or page labels
```

S17 may use fixed safe pools if same-source distractors are not available, but the item must report the distractor policy in `answer_model.distractor_policy`.

## 17. Shared Evidence Rules

Every generated item must preserve an `evidence` object with:

```text
evidence_text
evidence_sentences
sentence_count
evidence_source
supports_answer
```

`supports_answer` may be emitted as `false` or `unknown` before S18 only if the validator has not run, but S18 must require it to be true for accepted items.

The final accepted item must satisfy:

```text
correct_answer is explicitly supported by evidence_text
```

V1 does not allow inference-only answers.

## 18. Question Type Contract: literal_who

### 18.1 Purpose

`literal_who` asks the learner to identify a person, animal, character, or explicitly named subject from source text.

Example source:

```text
The boy runs.
```

Example prompt:

```text
Who runs?
```

Correct answer:

```text
The boy
```

### 18.2 Compatible Answer Model

```text
single_choice
```

### 18.3 Compatible Source Types

Preferred:

```text
sentence_candidate
enriched_reading_unit
```

Allowed:

```text
page_unit
```

Not preferred:

```text
reuse_unit_candidate
normalized_reading_unit
```

unless S17 can identify a clear subject in a short evidence span.

### 18.4 Sentence Count

Preferred:

```text
1 sentence
```

Allowed:

```text
1-5 sentences
```

Reject if the answer subject cannot be linked to a specific evidence sentence.

### 18.5 Required Source Feature

Source must contain an explicit who-like answer candidate:

```text
person noun phrase
character name
family-role noun phrase
animal subject if context treats the animal as the actor
pronoun only if antecedent is explicitly recoverable from same evidence span
```

Reject if the only candidate is an unresolved pronoun such as `he`, `she`, `they`, or `it` without a local antecedent.

### 18.6 Prompt Construction Rule

Default stem pattern:

```text
Who + verb phrase?
```

Allowed fallback pattern:

```text
Who is in the text?
```

Fallback is allowed only when the source explicitly names a participant and the answer is unambiguous.

### 18.7 Answer Construction Rule

Correct answer must be the explicit subject/participant phrase from evidence.

The correct answer may be normalized for capitalization and article consistency, but must not introduce new content.

### 18.8 Distractor Policy

Allowed distractors:

```text
same-level person/character safe pool
same-source non-answer person if clearly not correct
same-theme safe person/role nouns
```

Forbidden distractors:

```text
another answer that evidence could support
unseen named character presented as if from source
object/place distractors for a who question
```

### 18.9 Evidence Support Rule

Evidence must explicitly show the person/character/actor and action or presence that the question asks about.

### 18.10 Rejection Rules

Reject `literal_who` if:

1. No explicit who-like candidate exists.
2. Candidate is an unresolved pronoun.
3. More than one candidate can answer the same stem.
4. Correct answer requires inference.
5. Evidence sentence is abnormal extraction noise.
6. The item would require a non-source answer.

## 19. Question Type Contract: literal_what

### 19.1 Purpose

`literal_what` asks the learner to identify an explicit object, action, event, or thing from source text.

Example source:

```text
The girl has a kite.
```

Example prompt:

```text
What does the girl have?
```

Correct answer:

```text
a kite
```

### 19.2 Compatible Answer Model

```text
single_choice
```

### 19.3 Compatible Source Types

Preferred:

```text
sentence_candidate
enriched_reading_unit
```

Allowed:

```text
page_unit
```

### 19.4 Sentence Count

Preferred:

```text
1 sentence
```

Allowed:

```text
1-5 sentences
```

### 19.5 Required Source Feature

Source must contain one explicit what-like candidate:

```text
object noun phrase
action phrase
event phrase
thing named by the source text
```

For V1, concrete noun/object answers are preferred over abstract event answers.

### 19.6 Prompt Construction Rule

Default stem patterns:

```text
What does/do + subject + verb?
What is/are + source participant + doing?
What is in/on/at + place phrase?
```

S17 must choose a stem that matches the grammar of the evidence.

### 19.7 Answer Construction Rule

Correct answer must be copied or minimally normalized from the source phrase.

Allowed normalization:

```text
article normalization
singular/plural preservation
capitalization normalization
```

Forbidden normalization:

```text
synonym replacement
semantic paraphrase not present in source
higher-level vocabulary replacement
```

### 19.8 Distractor Policy

Allowed distractors:

```text
same-level object safe pool
same-theme object safe pool
same-source non-answer object if unambiguous
```

Forbidden distractors:

```text
answer also supported by evidence
person-only distractor for object-target stem
place-only distractor for object-target stem
```

### 19.9 Evidence Support Rule

Evidence must explicitly contain the target object/action/event and the participant or context used in the prompt.

### 19.10 Rejection Rules

Reject `literal_what` if:

1. No explicit object/action/event candidate exists.
2. The stem would be answerable by multiple source phrases.
3. Correct answer requires inference.
4. Correct answer requires synonym substitution.
5. Source sentence is too long or complex for V1 extraction.
6. Object/action cannot be tied to the prompt subject.

## 20. Question Type Contract: literal_where

### 20.1 Purpose

`literal_where` asks the learner to identify an explicit place or location from source text.

Example source:

```text
The cat is on the bed.
```

Example prompt:

```text
Where is the cat?
```

Correct answer:

```text
on the bed
```

### 20.2 Compatible Answer Model

```text
single_choice
```

### 20.3 Compatible Source Types

Preferred:

```text
sentence_candidate
enriched_reading_unit
```

Allowed:

```text
page_unit
```

### 20.4 Sentence Count

Preferred:

```text
1 sentence
```

Allowed:

```text
1-5 sentences
```

### 20.5 Required Source Feature

Source must contain an explicit location expression:

```text
prepositional phrase
place noun
room/place name
there/here only if antecedent place is explicit in same evidence span
```

Preferred V1 location patterns:

```text
in the ___
on the ___
at the ___
under the ___
near the ___
next to the ___
```

### 20.6 Prompt Construction Rule

Default stem patterns:

```text
Where is + subject?
Where are + plural subject?
Where does/do + subject + verb?
```

The stem must preserve number agreement when possible.

### 20.7 Answer Construction Rule

Correct answer must be the explicit location phrase from source text.

For V1, source phrase should be preserved with its preposition, for example:

```text
on the bed
```

not only:

```text
the bed
```

unless S16/S17 later defines a specific location-short-answer variant.

### 20.8 Distractor Policy

Allowed distractors:

```text
same-level location safe pool
same-theme location safe pool
same-source non-answer location if unambiguous
```

Forbidden distractors:

```text
location phrase also supported by evidence
object distractor without place meaning
person distractor
```

### 20.9 Evidence Support Rule

Evidence must explicitly contain both the subject being located and the location phrase.

### 20.10 Rejection Rules

Reject `literal_where` if:

1. No explicit place/location phrase exists.
2. Location depends on a picture rather than text.
3. Location is only inferable.
4. Multiple locations could answer the same prompt.
5. The source contains `there` or `here` without a recoverable place.
6. The prompt subject is not explicitly tied to the location.

## 21. Question Type Contract: true_false

### 21.1 Purpose

`true_false` asks the learner to decide whether a literal statement is supported by source evidence.

Example source:

```text
The dog is big.
```

True statement:

```text
The dog is big.
```

False statement:

```text
The dog is small.
```

### 21.2 Compatible Answer Model

```text
true_false
```

### 21.3 Compatible Source Types

Preferred:

```text
sentence_candidate
page_unit
reuse_unit_candidate
enriched_reading_unit
```

Allowed:

```text
normalized_reading_unit
```

if traceability and sentence order are preserved.

### 21.4 Sentence Count

Preferred:

```text
1-3 sentences
```

Allowed:

```text
1-5 sentences
```

### 21.5 Required Source Feature

Source must contain a literal proposition that can be converted into a true or false statement without inference.

Good V1 proposition types:

```text
subject + be + adjective
subject + verb + object
there is/are + noun phrase
subject + be + location phrase
```

### 21.6 Prompt Construction Rule

Default prompt shape:

```text
Read the sentence. Choose True or False.
```

Statement field should contain the proposition to evaluate.

### 21.7 Answer Construction Rule

Correct answer must be boolean:

```text
true
false
```

The answer model should use:

```text
answer_type = true_false
scoring.mode = boolean_match
```

### 21.8 False Statement Policy

False statements may be created only by safe local substitution:

```text
adjective swap
number swap
object swap
location swap
subject swap only if not confusing
```

The false variant must be clearly contradicted or unsupported by source evidence, and must not require external world knowledge.

### 21.9 Forbidden False Variants

Do not create false statements by:

```text
negation that creates grammar ambiguity
deleting critical context
using world knowledge
using a distractor that could also be true
using a picture-only detail
inventing an unsupported new source event
```

### 21.10 Evidence Support Rule

For true items, evidence must directly support the statement.

For false items, evidence must support why the statement is not the same as the source fact, or the validator must be able to identify the altered token/phrase.

### 21.11 Rejection Rules

Reject `true_false` if:

1. The source proposition is ambiguous.
2. A false variant cannot be safely generated.
3. The true/false answer depends on outside knowledge.
4. The altered phrase could still be correct.
5. The source text is longer than V1 can validate.
6. The statement is not grounded in the evidence text.

## 22. Question Type Contract: sentence_ordering

### 22.1 Purpose

`sentence_ordering` asks the learner to put source sentences back into their original order.

Example source:

```text
I get up.
I eat breakfast.
I go to school.
```

Prompt:

```text
Put the sentences in the correct order.
```

Correct answer:

```text
[1, 2, 3]
```

### 22.2 Compatible Answer Model

```text
ordered_sequence
```

### 22.3 Compatible Source Types

Preferred:

```text
page_unit
reuse_unit_candidate
enriched_reading_unit
```

Allowed:

```text
normalized_reading_unit
```

Not allowed:

```text
sentence_candidate
```

unless it is part of a selected multi-sentence unit.

### 22.4 Sentence Count

Preferred:

```text
3-5 sentences
```

Allowed:

```text
2-5 sentences
```

Reject by default:

```text
1 sentence
>5 sentences
```

### 22.5 Required Source Feature

Source must preserve stable sentence order and provide separate sentence boundaries.

Best source types have:

```text
source_sentence_candidate_ids
ordered sentence list
page_number or unit order
```

### 22.6 Prompt Construction Rule

Prompt must display shuffled sentences as choices/items.

Each displayed sentence must have a stable option ID, for example:

```text
A, B, C, D, E
```

### 22.7 Answer Construction Rule

Correct answer must store the original order by option IDs or source sentence IDs.

Allowed answer model shape:

```json
{
  "answer_type": "ordered_sequence",
  "correct_answer": ["B", "A", "C"],
  "acceptable_answers": [["B", "A", "C"]],
  "scoring": {
    "mode": "sequence_exact_match",
    "points": 1
  }
}
```

Partial credit is not allowed in V1.

### 22.8 Shuffling Policy

S17 must shuffle deterministically if it implements this type.

Default deterministic seed components:

```text
source_record_id
question_type
item_id
```

The shuffled order must not equal the original order unless no alternative is possible; if no alternative is possible, reject the item.

### 22.9 Evidence Support Rule

Evidence must include the original ordered sentence list.

### 22.10 Rejection Rules

Reject `sentence_ordering` if:

1. Source has fewer than 2 sentences.
2. Sentence order is not preserved.
3. Sentences are not separable.
4. More than 5 sentences are required.
5. Shuffled order equals original order.
6. Source text is a list of fragments rather than readable sentences.
7. The ordering requires story inference beyond source order.

## 23. Question Type Contract: cloze_vocabulary

### 23.1 Purpose

`cloze_vocabulary` asks the learner to choose or supply a missing vocabulary token from source text.

Example source:

```text
I eat rice.
```

Prompt display:

```text
I eat ____.
```

Correct answer:

```text
rice
```

### 23.2 Compatible Answer Model

```text
cloze_text
```

### 23.3 Compatible Source Types

Preferred:

```text
sentence_candidate
enriched_reading_unit
```

Allowed:

```text
page_unit
```

### 23.4 Sentence Count

Preferred:

```text
1 sentence
```

Allowed:

```text
1-5 sentences
```

For V1, cloze should use one evidence sentence even if the source is a page unit.

### 23.5 Required Source Feature

Source must contain a removable vocabulary token that is:

```text
single word or approved simple multi-word chunk
not a function word unless explicitly approved
not punctuation
not a proper noun unless used as vocabulary focus
not required to preserve basic grammar of the sentence after removal
```

Preferred target token classes:

```text
concrete noun
common verb
basic adjective
simple place word
simple food/animal/school/home vocabulary
```

### 23.6 Prompt Construction Rule

Prompt display must show the source sentence with exactly one blank:

```text
I eat ____.
```

The stem may be:

```text
Choose the word that completes the sentence.
```

### 23.7 Answer Construction Rule

Correct answer must equal the removed source token or approved chunk.

Allowed scoring modes:

```text
exact_match
choice_id_match
```

For V1, multiple blanks are not allowed.

### 23.8 Distractor Policy

Allowed distractors:

```text
same-level vocabulary safe pool
same-theme vocabulary safe pool
same-source non-answer token if grammar-safe
same part-of-speech when available
```

Forbidden distractors:

```text
word that also makes a valid source-supported answer
higher-level vocabulary without policy
function word distractor for content-word target
malformed token
metadata token
```

### 23.9 Evidence Support Rule

Evidence must contain the original unblanked sentence.

The blanked prompt must be reconstructable from evidence by replacing exactly one token/chunk with a blank.

### 23.10 Rejection Rules

Reject `cloze_vocabulary` if:

1. No safe removable token exists.
2. More than one blank would be needed.
3. Removed token is not present in source evidence.
4. Blank makes the sentence unreadable or grammatically misleading.
5. Distractors are all unsafe or ambiguous.
6. Target token is a file name, ID, page marker, or metadata artifact.
7. Target token requires vocabulary authority not available to V1.

## 24. Source Text Display Policy

| Question type | Show source text by default? | Notes |
|---|---|---|
| `literal_who` | Yes | Required for pure Reading practice unless item is generated from displayed passage package |
| `literal_what` | Yes | Required for V1 evidence visibility |
| `literal_where` | Yes | Required for V1 evidence visibility |
| `true_false` | Yes | Show source sentence/passage plus statement |
| `sentence_ordering` | Yes | Show shuffled sentences, not original order |
| `cloze_vocabulary` | Yes | Show blanked sentence |

If S19 later packages multiple questions under one displayed passage, item-level `display_text` may be omitted only if package-level display text preserves source/evidence traceability.

## 25. Question Type Compatibility Table

| Question type | Answer type | Required source count | Choices required? | Default source display |
|---|---|---:|---|---|
| `literal_who` | `single_choice` | 1-5 sentences | Yes | source sentence/passage |
| `literal_what` | `single_choice` | 1-5 sentences | Yes | source sentence/passage |
| `literal_where` | `single_choice` | 1-5 sentences | Yes | source sentence/passage |
| `true_false` | `true_false` | 1-5 sentences | Yes: True/False | source sentence/passage + statement |
| `sentence_ordering` | `ordered_sequence` | 2-5 sentences | Yes: ordered options | shuffled sentence list |
| `cloze_vocabulary` | `cloze_text` | 1-5 sentences | Preferred yes | blanked sentence |

## 26. S17 Builder Handoff

S17 may implement the candidate item builder only after S14-S16 are complete.

S17 must:

1. Read approved source candidates using S15 rules.
2. Apply the S16 question-type compatibility table.
3. Generate only the six approved V1 question types.
4. Emit `READING_PRACTICE_ITEM_V1` candidate items.
5. Preserve S14 source, evidence, answer_model, validation, tags, and lifecycle requirements.
6. Set `validation.validator_status = not_run` unless validation is explicitly included in S17 scope.
7. Keep every item candidate-only and not learner-facing.
8. Write only approved generated outputs.

S17 must not invent source text, promote items, or create a student-facing package.

## 27. S18 Validator Handoff

S18 validator must enforce:

1. Question type is one of the six approved values.
2. Answer model type is compatible with question type.
3. Source type is compatible with question type.
4. Sentence count is compatible with question type.
5. Evidence text supports the correct answer.
6. Distractors are not also correct.
7. Prompt does not require external knowledge.
8. Source text is not generated content.
9. Candidate-only/no-promotion/no-learner-facing boundary is intact.
10. Tags are arrays of strings where required.

S18 must reject unsupported, ambiguous, unsourced, promoted, or malformed items.

## 28. S19 Output Package Handoff

S19 may package validated candidate items only after S17/S18 produce and validate them.

S19 must preserve:

```text
item_id
source traceability
evidence text
answer model
question type
validator status
candidate-only lifecycle
```

S19 must not turn candidate output into learner-facing production without a later promotion task.

## 29. S16 Closeout Result

Status:

```text
PASS
```

Files changed:

```text
docs/ulga/RAZ_AW_S16_READING_QUESTION_TYPE_CONTRACT_DESIGN_SCAN.md
```

Reading System Progress Tracker:

```text
Task ID: RAZ-AW-S16_ReadingQuestionTypeContract_DesignScan
Task name: Reading Question Type Contract Design Scan
Reading system target: Reading System V1
Stage: S16
Input source: S15 Reading Source Selector Contract Design Scan; S14 Reading Practice Item Contract Design Scan; S13 Reading Practice System Goal and Progress Tracker Design Scan; S11/S12 intake query-index boundary; Project Task Expansion Control Policy
Output artifact: S16 design scan markdown
Progress contribution: Defines exact V1 question-type contracts for literal_who, literal_what, literal_where, true_false, sentence_ordering, and cloze_vocabulary, including source features, prompt rules, answer construction, distractor policy, evidence rules, rejection rules, and S17/S18 handoff requirements
Completed stage count: 6 / 10 after S16
Remaining stage count: 4 / 10 after S16
Blocking issue: None
Deferred issue: S17 builder, S18 validator, S19 output package, S20 closeout QA, V2-V5 roadmap
Generated artifact policy: No generated artifacts created or committed
Runtime impact: None
Promotion impact: None
Closeout status: PASS
Next allowed task: RAZ-AW-S17_ReadingCandidateItemBuilder_Implementation
```

## 30. Next Allowed Task

```text
RAZ-AW-S17_ReadingCandidateItemBuilder_Implementation
```

S17 may implement candidate Reading item generation only within the S14-S16 contracts.

S17 must keep generated items candidate-only and must not promote, package for learners, or alter runtime behavior.

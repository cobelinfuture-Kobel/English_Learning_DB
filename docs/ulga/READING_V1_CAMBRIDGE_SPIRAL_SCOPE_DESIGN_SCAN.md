# ReadingV1 Cambridge Spiral Scope Design Scan

## 1. Current State

Task:
ReadingV1_CambridgeSpiralScope_DesignScan

Scope:
Define the Cambridge / CEFR / YLE-aligned spiral learning scope for ReadingV1 before PracticeBank contract or implementation starts.

Allowed files:
- docs/ulga/READING_V1_CAMBRIDGE_SPIRAL_SCOPE_DESIGN_SCAN.md

Forbidden files:
- runtime code
- builders
- validators
- tests
- generated JSON artifacts
- PracticeBank artifacts
- HTML output artifacts
- RAZ raw text, full passage text, or full book text

Current-task blockers:
- Missing ReadingV1-specific spiral scope matrix
- Missing stage-level grammar / pattern / vocabulary / chunk / theme / question-type boundary
- Missing html_ready and validator requirement contract for downstream P1-M3 / P1-M4

Warning policy:
- Documentation-only warnings are acceptable if they do not block the current DesignScan.
- Any need for implementation, schema change, source import, or generated artifact is classified as FUTURE_WORK.

Generated artifact policy:
- No generated artifact is allowed in this task.
- This task writes one design document only.

Runtime impact:
- None.

Promotion impact:
- None.
- This task does not promote candidates, source units, RAZ-derived records, PracticeBank items, or learner-facing content.

Stop condition:
- Stop after defining the ReadingV1 spiral scope matrix, spiral rule, html_ready rule, validator requirements, Gate PASS checklist, and next task.
- Do not create ReadingV1 PracticeBank.
- Do not create HTML.
- Do not implement validator code.

Deferred issues register:
- P1-M3 PracticeBank contract is deferred.
- P1-M4 PracticeBank implementation is deferred.
- P2 formal Cambridge / worksheet assessment expansion is deferred.
- V3 error tagging / weak-point diagnosis is deferred.
- Adaptive learning path / mastery engine is deferred.

---

## 2. Source Basis and Role Separation

ReadingV1 must be treated as:

```text
Cambridge-aligned
+
RAZ-source-grounded
+
ULGA-controlled
+
private-homework-safe
```

The roles are separated as follows:

| Layer | Role in ReadingV1 | Boundary |
|---|---|---|
| Cambridge / CEFR / YLE | Level standard, difficulty reference, child-learning sequence reference | Does not by itself define the full learning path |
| EGP / Grammar Authority | Grammar difficulty and usage authority | Must be filtered into ReadingV1 stage scope before use |
| EVP / NGSL / Vocabulary Authority | Vocabulary difficulty and frequency authority | Must be filtered into ReadingV1 stage scope before generator use |
| EVP Chunk Authority | Chunk / phrase authority | Must be filtered by stage, usage class, priority, and safety |
| ULGA | Internal graph layer linking grammar, vocabulary, pattern, chunk, and theme | Query/control layer, not learner-facing output by itself |
| RAZ / Reading source | Reading source and private-homework material source | No raw full text persisted to repo; local/private use only |
| ReadingV1 | PracticeBank and private homework HTML pipeline | V1 only; no formal assessment expansion |

Critical boundary:

```text
CEFR level != teaching order
YLE-like sequence != formal Cambridge exam clone
RAZ level != Cambridge level
ReadingV1 stage != final promotion authority
```

This task defines a scope contract. It does not produce learner-facing content.

---

## 3. ReadingV1 Stage Model

ReadingV1 uses four controlled stages.

| Stage ID | Stage Name | Standard Role | Main Purpose |
|---|---|---|---|
| RV1-S0 | PreA1 / Starters-like | entry-level familiar-object reading | identify concrete words, people, objects, places |
| RV1-S1 | A1 Core / Movers-entry | early A1 sentence reading | read simple location, possession, and existence sentences |
| RV1-S2 | A1+ / Movers-expansion | expanded A1 reading | read action, ability, preference, and short routine sentences |
| RV1-S3 | A2-lite bridge / Flyers-entry | bridge into short connected text | read short sequences, simple past exposure, and cloze/order tasks |

Stage progression rule:

```text
RV1-S0 -> RV1-S1 -> RV1-S2 -> RV1-S3
```

But stage progression must remain query-controlled. A learner does not advance only because a CEFR label is higher. A downstream planner must still check prerequisite grammar, vocabulary familiarity, pattern readiness, theme familiarity, and reinforcement need.

---

## 4. Spiral Scope Matrix

### 4.1 RV1-S0 PreA1 / Starters-like

Purpose:
- Build recognition of concrete people, objects, colors, animals, classroom items, and simple places.
- Keep reading units very short and visually / contextually grounded.

Grammar focus:
- be verb: `is`, `are` in simple recognition contexts
- singular and plural nouns in controlled exposure
- articles: `a`, `an`, `the` as surface reading support, not explicit grammar teaching
- demonstratives: `this`, `that` in simple identification
- basic prepositions: `in`, `on`, `under` only when visually grounded

Sentence patterns:
- `This is a ___.`
- `It is ___.`
- `I see a ___.`
- `The ___ is ___.`
- `The ___ is in/on/under the ___.`

Vocabulary band:
- concrete high-frequency nouns
- colors
- numbers 1-10
- classroom objects
- animals
- family words
- body parts
- common food items

Chunk policy:
- Allow only transparent, literal chunks.
- Prefer location chunks: `in the ___`, `on the ___`, `under the ___`.
- Block idioms, abstract phrases, low-frequency compounds, grammar terms, and metaphorical chunks.

Theme / situation scope:
- Personal / greeting
- Classroom
- Home objects
- Family
- Animals
- Food basics
- Body basics

Allowed Reading question types:
- literal_what
- literal_where
- true_false with one visible fact

Blocked question types:
- literal_who unless the source explicitly names or identifies the person
- sentence_ordering
- cloze_vocabulary unless the missing word is a concrete noun with direct evidence
- inference
- matching to unseen paraphrase

html_ready rule:
- Text length is short enough for single-screen display.
- Every answer must be supported by one explicit source fact.
- No distractor requires inference.
- No raw RAZ full passage text is stored in repo.

Validator requirements:
- stage_id == `RV1-S0`
- question_type in allowed list
- grammar_focus subset of RV1-S0 grammar scope
- all vocabulary items are concrete and stage-allowed
- chunk usage is literal and stage-allowed
- answer evidence is direct

---

### 4.2 RV1-S1 A1 Core / Movers-entry

Purpose:
- Move from word/object recognition into simple sentence comprehension.
- Introduce existence, possession, and simple location.

Grammar focus:
- `there is` / `there are` in controlled contexts
- `have` / `has` for possession
- simple present for stable facts
- subject pronouns: `I`, `you`, `he`, `she`, `it`, `we`, `they`
- prepositions: `in`, `on`, `under`, `next to`, `near`

Sentence patterns:
- `There is a ___ in the ___.`
- `There are ___ in the ___.`
- `I have a ___.`
- `He/She has a ___.`
- `The ___ is next to the ___.`
- `This is my ___.`

Vocabulary band:
- home rooms and objects
- school places and objects
- food and drink core nouns
- clothes basics
- simple places
- simple adjectives: big, small, new, old, happy, sad

Chunk policy:
- Allow transparent compound nouns when stage-appropriate.
- Allow location chunks: `next to`, `near the ___`, `at school`, `at home`.
- Allow high-utility noun compounds only if vocabulary level and theme match.
- Block abstract / idiomatic / formal chunks.

Theme / situation scope:
- Home
- School
- Food
- Clothes
- Toys
- Family
- Simple shopping objects, without transaction complexity

Allowed Reading question types:
- literal_who
- literal_what
- literal_where
- true_false

Blocked question types:
- sentence_ordering unless the text has explicit sequence markers
- cloze_vocabulary if more than one plausible answer exists
- inference
- formal Cambridge-style matching

html_ready rule:
- Each practice item has one clear display_text or source locator.
- Each item has explicit level_stage, theme, grammar_focus, pattern, vocabulary_refs, chunk_refs, question_type, answer_key, answer_model, and source_trace.
- Public export flags remain blocked.

Validator requirements:
- stage_id == `RV1-S1`
- grammar includes only RV1-S0/RV1-S1 material unless marked as preview only
- question answer must be literal
- source trace must exist
- no full source payload persisted

---

### 4.3 RV1-S2 A1+ / Movers-expansion

Purpose:
- Expand from static description into action, ability, preference, and routine reading.
- Keep texts short but allow two to four connected sentences.

Grammar focus:
- `can` for ability
- `like` / `likes` for preference
- simple present routines
- present continuous in highly visible action contexts
- wh-questions as comprehension labels: who / what / where
- conjunction preview: `and`, `but` in controlled short sentences

Sentence patterns:
- `I can ___ .`
- `He/She can ___ .`
- `I like ___ .`
- `He/She likes ___ .`
- `The ___ is ___ing.`
- `They are ___ing.`
- `I go to ___ .`
- `We play ___ .`

Vocabulary band:
- actions and hobbies
- transport basics
- places in town
- weather basics
- daily routine words
- expanded school / home / food vocabulary
- common verbs: go, play, eat, drink, read, write, draw, run, jump, see, make, help

Chunk policy:
- Allow stage-safe action/location chunks: `go to`, `at school`, `after school`, `play with`, `look at`.
- Allow transparent compound nouns from safe chunk layer when theme matches.
- Block idioms and abstract collocations.
- Low-priority chunks require explicit review before generator use.

Theme / situation scope:
- Daily routine
- School activities
- Hobbies
- Travel / transport basics
- Weather
- Food preference
- Health basics

Allowed Reading question types:
- literal_who
- literal_what
- literal_where
- true_false
- cloze_vocabulary with direct local evidence

Blocked question types:
- sentence_ordering unless markers or temporal sequence are explicit
- inference beyond one direct sentence
- formal test formats reserved for P2

html_ready rule:
- Practice item may contain short multi-sentence unit if source trace and sentence order are preserved.
- Cloze item must have exactly one valid answer from local context.
- Every new focus item must be accompanied by reinforcement tags.

Validator requirements:
- stage_id == `RV1-S2`
- new knowledge count must be bounded
- old knowledge reinforcement must be present
- cloze answer must be unique and directly recoverable
- source trace and evidence trace must exist

---

### 4.4 RV1-S3 A2-lite bridge / Flyers-entry

Purpose:
- Bridge into short connected reading while remaining inside V1 private homework scope.
- Introduce sequence, simple past exposure, and controlled sentence-order / cloze tasks.

Grammar focus:
- simple present review
- present continuous review
- `can` / `like` review
- sequence markers: `first`, `then`, `after that`, `finally`
- simple past exposure only for common regular or high-frequency known forms when source-supported
- time expressions: today, yesterday, in the morning, after school

Sentence patterns:
- `First, ___. Then, ___.`
- `After that, ___.`
- `Finally, ___.`
- `Yesterday, I ___ .`
- `We went to ___ .` as source-supported recognition only, not productive grammar target
- `I want to ___ .`
- `Can you ___ ?` as reading comprehension pattern, not speaking assessment

Vocabulary band:
- daily routine expansion
- travel / transport expansion
- shopping basics
- simple restaurant / food ordering vocabulary
- weather and simple plans
- common past-time expressions
- sequence words

Chunk policy:
- Allow time and sequence chunks: `after school`, `in the morning`, `at the park`, `go to`, `want to`.
- Allow only source-supported simple past chunks.
- Block formal assessment phrases, abstract discourse markers, idioms, and advanced multi-word expressions.

Theme / situation scope:
- Daily routine
- Travel / transport
- Shopping basics
- Food / restaurant basics
- School events
- Park / hobbies
- Weather and simple plans

Allowed Reading question types:
- literal_who
- literal_what
- literal_where
- true_false
- sentence_ordering when explicit sequence evidence exists
- cloze_vocabulary with direct evidence

Blocked question types:
- multi-paragraph comprehension
- inference-heavy reading
- matching headings
- multiple-choice distractor strategy
- formal Cambridge exam simulation

html_ready rule:
- Multi-sentence display unit must preserve original order and source trace.
- Sentence ordering item must contain explicit sequence evidence.
- Cloze item must not require grammar generation beyond V1 scope.
- Any simple past exposure must be marked as recognition/exposure unless a later task promotes it.

Validator requirements:
- stage_id == `RV1-S3`
- sequence tasks require sequence evidence
- past exposure must be source-supported and flagged
- no P2 formal assessment pattern leakage
- no raw source payload persisted

---

## 5. Cross-Stage Spiral Rule

ReadingV1 follows the rule:

```text
old knowledge + small new knowledge + explicit source evidence + validator gate
```

A PracticeBank item may introduce new focus only if it also reinforces earlier knowledge.

Required fields for downstream PracticeBank items:

```text
level_stage
stage_new_focus
stage_reinforcement
spiral_from_stage
spiral_to_stage
source_trace
answer_evidence
html_ready
validator_status
```

Stage transition examples:

| From | To | Reinforced | New Focus |
|---|---|---|---|
| RV1-S0 | RV1-S1 | concrete nouns, color, simple place | there is / there are |
| RV1-S1 | RV1-S2 | home, school, simple location | action, can, like, routine |
| RV1-S2 | RV1-S3 | action/routine reading | sequence, cloze, sentence ordering |

The system must not use CEFR label alone as the transition rule.

---

## 6. ReadingV1 V1 Question-Type Whitelist

Allowed in V1:

```text
literal_who
literal_what
literal_where
true_false
sentence_ordering
cloze_vocabulary
```

Question-type stage availability:

| Question Type | RV1-S0 | RV1-S1 | RV1-S2 | RV1-S3 | Notes |
|---|---:|---:|---:|---:|---|
| literal_what | allowed | allowed | allowed | allowed | direct evidence required |
| literal_where | allowed | allowed | allowed | allowed | direct location evidence required |
| literal_who | limited | allowed | allowed | allowed | requires explicit named/person evidence |
| true_false | limited | allowed | allowed | allowed | one explicit fact only in S0 |
| cloze_vocabulary | blocked/limited | limited | allowed | allowed | unique answer required |
| sentence_ordering | blocked | blocked/limited | limited | allowed | explicit sequence evidence required |

Deferred to P2:

```text
matching
multiple_choice_with_distractors
gap_fill_formal
short_answer_formal
picture_text_matching
reading_comprehension_set
Cambridge mock exam pattern
KET-style reading item set
```

---

## 7. HTML Ready Contract

A ReadingV1 item is `html_ready = true` only if all checks pass:

```text
level_stage exists
question_type is allowed for stage
theme exists
grammar_focus exists
pattern exists
vocabulary_refs exist
chunk_refs are valid or explicitly empty
source_trace exists
answer_key exists
answer_model exists
answer_evidence exists
private_homework_only == true
not_for_public_export == true
not_for_commercial_distribution == true
raw_raz_text_persisted == false
full_passage_text_persisted == false
public_preview_allowed == false
validator_status == PASS
```

HTML-ready does not mean public-ready. In P1, HTML-ready means local/private homework render-ready only.

---

## 8. Validator Requirement Contract

The future P1-M3 / P1-M4 validator must check at least:

### 8.1 Stage Scope Validation

```text
stage_id is one of RV1-S0, RV1-S1, RV1-S2, RV1-S3
grammar_focus subset of stage grammar scope
pattern subset of stage pattern scope
question_type allowed by stage
```

### 8.2 Vocabulary Validation

```text
vocabulary_refs exist
vocabulary items are within stage band or marked preview
preview vocabulary count is bounded
abstract / low-frequency words are blocked unless reviewed
```

### 8.3 Chunk Validation

```text
chunk_refs use safe chunk layer or approved local pattern chunk
chunk usage_class is allowed for stage
idiomatic / abstract / formal chunks are blocked in V1
low-priority chunk requires review flag
```

### 8.4 Theme / Situation Validation

```text
theme exists
theme is stage-allowed
situation is concrete and familiar for RV1-S0/RV1-S1
multi-theme items are blocked unless one primary theme is explicit
```

### 8.5 Question / Answer Validation

```text
question_type in V1 whitelist
answer_key exists
answer_model exists
answer evidence is direct
cloze has exactly one valid local answer
sentence_ordering has explicit sequence evidence
```

### 8.6 Policy / Storage Validation

```text
private_homework_only == true
not_for_public_export == true
not_for_commercial_distribution == true
raw_raz_text_persisted == false
full_passage_text_persisted == false
source payload copied to repo == false
```

---

## 9. Reading System Progress Update

This task advances ReadingV1 readiness by defining the learning-standard scope required before PracticeBank contract and implementation.

| Dimension | Before | After This DesignScan |
|---|---|---|
| Source Authority | PARTIAL / available from existing authority layers | unchanged |
| Content Authority | PARTIAL | unchanged |
| Query Layer | PARTIAL | unchanged |
| Validation Layer | PARTIAL | scope contract available for future validator |
| Reading Generation | NOT_STARTED | still NOT_STARTED |
| Reading Practice | NOT_STARTED | still NOT_STARTED |
| Reading Assessment | NOT_STARTED | still NOT_STARTED; P2 deferred |
| Production Readiness | NOT_STARTED | unchanged |
| Cambridge Spiral Scope | NOT_STARTED | DESIGN_DEFINED |

Estimated P1 readiness after this task:

```text
P1-M0 Governance / Scope Lock ............ PARTIAL_DONE
P1-M1 Policy & Private Homework Safety ... MOSTLY_DONE
P1-M2 Cambridge Spiral Scope ............. COMPLETED_BY_DESIGN
P1-M3 PracticeBank Contract .............. NOT_STARTED
P1-M4 PracticeBank Implementation ........ NOT_STARTED
P1-M5 Private Homework Overlay ........... NOT_STARTED
P1-M6 Local Runtime Pipeline ............. NOT_STARTED
P1-M7 Output Gate ........................ NOT_STARTED
P1-M8 HTML Practice Export ............... NOT_STARTED
P1-M9 P1 Closeout QA ..................... NOT_STARTED
```

---

## 10. Gate PASS Checklist

| Gate | Result | Evidence |
|---|---|---|
| Every stage has grammar focus | PASS | Section 4 |
| Every stage has sentence patterns | PASS | Section 4 |
| Every stage has vocabulary band | PASS | Section 4 |
| Every stage has chunk policy | PASS | Section 4 |
| Every stage has theme / situation scope | PASS | Section 4 |
| Every stage has question-type scope | PASS | Section 4 and Section 6 |
| Cambridge / CEFR / YLE roles separated | PASS | Section 2 |
| CEFR is not treated as sole learning path | PASS | Section 2 and Section 5 |
| P2 formal assessment expansion excluded | PASS | Section 6 |
| No PracticeBank item generated | PASS | Documentation-only task |
| No HTML generated | PASS | Documentation-only task |
| No runtime modified | PASS | Documentation-only task |
| No RAZ raw text stored | PASS | Documentation-only task |

Task status:

```text
ReadingV1_CambridgeSpiralScope_DesignScan -> COMPLETED_BY_DESIGN
```

---

## 11. Deferred Issues Register

### D1

issue_id:
P1-M3_PracticeBank_Contract

severity:
required_next_step

affected_file_or_artifact:
docs/ulga/READING_V1_PRIVATE_HOMEWORK_PRACTICE_BANK_CONTRACT.md

classification:
FUTURE_WORK

why_deferred:
This task defines the learning scope only. PracticeBank schema is the next task.

recommended_future_task:
ReadingV1_PrivateHomeworkPracticeBank_DesignScan

blocks_current_task:
no

### D2

issue_id:
P1-M4_PracticeBank_Implementation

severity:
required_later_step

affected_file_or_artifact:
PracticeBank builder, reports, tests

classification:
FUTURE_WORK

why_deferred:
Implementation must wait until P1-M3 defines the schema contract.

recommended_future_task:
ReadingV1_PrivateHomeworkPracticeBank_Implementation

blocks_current_task:
no

### D3

issue_id:
P2_Formal_Assessment_Expansion

severity:
deferred_phase

affected_file_or_artifact:
Cambridge / worksheet / formal assessment pattern contracts

classification:
FUTURE_WORK

why_deferred:
V1 is limited to source-grounded private homework practice. Formal assessment expansion is P2.

recommended_future_task:
E4S-P2_AssessmentPatternExpansion_DesignScan

blocks_current_task:
no

---

## 12. Next Shortest Step

NEXT_SHORT_STEP:

```text
ReadingV1_PrivateHomeworkPracticeBank_DesignScan
```

唯一執行動作:

```text
建立 docs/ulga/READING_V1_PRIVATE_HOMEWORK_PRACTICE_BANK_CONTRACT.md
```

Next task boundary:

```text
Use this Cambridge spiral scope as input.
Define PracticeBank schema only.
Do not implement builder.
Do not generate 12-item PracticeBank yet.
Do not generate HTML.
Do not enter P2 formal assessment expansion.
```
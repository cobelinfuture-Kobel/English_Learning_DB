# ReadingV1 Private Homework PracticeBank Contract

## 1. Current State

Task:
ReadingV1_PrivateHomeworkPracticeBank_DesignScan

Scope:
Define the ReadingV1 PracticeBank contract for private homework generation, using the approved Cambridge spiral scope as the upstream stage authority.

Allowed files:
- docs/ulga/READING_V1_PRIVATE_HOMEWORK_PRACTICE_BANK_CONTRACT.md

Forbidden files:
- runtime code
- builders
- validators
- tests
- generated JSON artifacts
- candidate PracticeBank output
- HTML output
- RAZ raw text, full passage text, or full book text
- public export artifacts

Current-task blockers:
- Missing PracticeBank item schema
- Missing package schema
- Missing source trace / evidence trace contract
- Missing private homework policy flags
- Missing html_ready derivation rule
- Missing future validator gate contract

Warning policy:
- Documentation-only warnings are acceptable if they do not block this contract.
- Any implementation requirement is classified as FUTURE_WORK.
- Any policy ambiguity around source text persistence is a blocker for implementation, but not for this documentation-only contract if the contract explicitly blocks raw/full-text persistence.

Generated artifact policy:
- No generated artifact is allowed in this task.
- This task writes one design document only.

Runtime impact:
- None.

Promotion impact:
- None.
- This contract defines candidate-only PracticeBank records.
- It does not promote any source unit, RAZ-derived unit, generated item, or learner-facing content to authority status.

Stop condition:
- Stop after defining PracticeBank package schema, item schema, evidence schema, policy flags, html_ready rule, validator gates, Gate PASS checklist, deferred issues, and next task.
- Do not implement a builder.
- Do not generate sample PracticeBank JSON.
- Do not generate HTML.
- Do not copy or persist raw source text.

Deferred issues register:
- P1-M4 PracticeBank implementation is deferred.
- P1-M5 Private Homework Candidate Overlay is deferred.
- P1-M6 Local Runtime / In-Memory Source Pipeline is deferred.
- P1-M7 Private Homework Output Gate is deferred.
- P1-M8 HTML Practice Export is deferred.
- P2 Assessment Pattern Expansion is deferred.

---

## 2. Upstream Contract Inputs

This PracticeBank contract depends on the approved ReadingV1 Cambridge spiral scope.

Required upstream concepts:

```text
RV1-S0
RV1-S1
RV1-S2
RV1-S3
```

Required upstream spiral fields:

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

Required V1 question-type whitelist:

```text
literal_who
literal_what
literal_where
true_false
sentence_ordering
cloze_vocabulary
```

Required private homework rule:

```text
html_ready != public_ready
html_ready only means local/private homework render-ready
```

---

## 3. PracticeBank Artifact Boundary

ReadingV1 PracticeBank is a candidate package, not an authority artifact.

It may be:

```text
searchable
auditable
validator-checkable
local/private homework render-ready
```

It must not be:

```text
final authority
public export
commercial worksheet
formal Cambridge mock exam
adaptive learner-state recommendation
raw RAZ text storage
full passage storage
```

PracticeBank output is candidate-only until a later explicit promotion-readiness task approves otherwise.

---

## 4. PracticeBank Package Schema

A PracticeBank package is the top-level unit passed from the future builder to the private homework overlay and HTML export gate.

Schema:

```json
{
  "practice_bank_id": "RV1_PB_YYYYMMDD_000001",
  "schema_version": "reading_v1_practice_bank.v1",
  "pipeline_stage": "candidate_practice_bank",
  "authority_status": "candidate_only",
  "promotion_status": "not_promoted",
  "private_homework_only": true,
  "not_for_public_export": true,
  "not_for_commercial_distribution": true,
  "source_payload_policy": {
    "raw_source_text_persisted": false,
    "full_passage_text_persisted": false,
    "source_payload_copied_to_repo": false,
    "display_text_policy": "derived_or_locator_only"
  },
  "scope": {
    "level_stage": "RV1-S1",
    "stage_name": "A1 Core / Movers-entry",
    "theme": "Home",
    "situation": "home_description",
    "question_types": ["literal_what", "literal_where", "true_false"],
    "item_count": 12
  },
  "spiral_plan": {
    "spiral_from_stage": "RV1-S0",
    "spiral_to_stage": "RV1-S1",
    "stage_new_focus": ["there_is", "there_are"],
    "stage_reinforcement": ["concrete_nouns", "simple_places", "colors"]
  },
  "source_selection": {
    "source_family": "reading_source",
    "source_system": "RAZ_or_reading_authority_query_index",
    "source_query_ref": "query_ref_or_manifest_id",
    "source_unit_refs": []
  },
  "items": [],
  "validation_summary": {
    "validator_status": "NOT_RUN",
    "html_ready_count": 0,
    "blocked_count": 0,
    "warning_count": 0,
    "error_count": 0
  },
  "build_metadata": {
    "builder_name": null,
    "builder_version": null,
    "built_at": null,
    "git_commit": null
  }
}
```

Required package-level invariants:

```text
private_homework_only == true
not_for_public_export == true
not_for_commercial_distribution == true
raw_source_text_persisted == false
full_passage_text_persisted == false
source_payload_copied_to_repo == false
authority_status == candidate_only
promotion_status == not_promoted
```

---

## 5. PracticeBank Item Schema

Each PracticeBank item is one answerable ReadingV1 practice question.

Schema:

```json
{
  "item_id": "RV1_ITEM_000001",
  "schema_version": "reading_v1_practice_item.v1",
  "authority_status": "candidate_only",
  "promotion_status": "not_promoted",
  "level_stage": "RV1-S1",
  "stage_name": "A1 Core / Movers-entry",
  "theme": "Home",
  "situation": "home_description",
  "question_type": "literal_where",
  "skill_area": "reading",
  "cambridge_alignment": {
    "cefr_band": "A1",
    "yle_band": "Movers-entry",
    "alignment_role": "difficulty_reference_not_exam_clone"
  },
  "spiral_binding": {
    "spiral_from_stage": "RV1-S0",
    "spiral_to_stage": "RV1-S1",
    "stage_new_focus": ["there_is"],
    "stage_reinforcement": ["home_objects", "simple_location"]
  },
  "content_binding": {
    "grammar_focus": ["there_is"],
    "patterns": ["There is a ___ in the ___."],
    "vocabulary_refs": [],
    "chunk_refs": [],
    "theme_refs": []
  },
  "source_trace": {
    "source_family": "reading_source",
    "source_system": "RAZ_or_reading_authority_query_index",
    "source_level": null,
    "source_book_ref": null,
    "source_unit_ref": null,
    "source_sentence_refs": [],
    "source_page_ref": null,
    "source_locator": null,
    "source_payload_stored": false
  },
  "display_payload": {
    "display_text": null,
    "display_text_type": "derived_or_locator_only",
    "display_text_source": "private_runtime_or_reviewed_candidate",
    "raw_source_text_copied": false,
    "full_passage_text_copied": false
  },
  "question": {
    "prompt": "Where is the ___?",
    "prompt_language": "en",
    "options": [],
    "requires_image": false,
    "requires_audio": false
  },
  "answer_model": {
    "answer_type": "short_text",
    "answer_key": null,
    "accepted_answers": [],
    "case_sensitive": false,
    "requires_exact_match": false
  },
  "answer_evidence": {
    "evidence_type": "direct_literal_text_or_locator",
    "evidence_refs": [],
    "evidence_quote_allowed": false,
    "source_sentence_ref": null,
    "source_locator": null,
    "directness": "direct"
  },
  "policy_flags": {
    "private_homework_only": true,
    "not_for_public_export": true,
    "not_for_commercial_distribution": true,
    "public_preview_allowed": false,
    "raw_raz_text_persisted": false,
    "full_passage_text_persisted": false,
    "source_payload_copied_to_repo": false
  },
  "html_gate": {
    "html_ready": false,
    "html_ready_reason": null,
    "render_mode": "local_private_homework_only"
  },
  "validator_status": {
    "status": "NOT_RUN",
    "errors": [],
    "warnings": []
  }
}
```

---

## 6. Question-Type Contracts

### 6.1 literal_who

Required:

```text
source explicitly identifies a person, role, character, or speaker
answer evidence is direct
no inference from pronoun-only context unless antecedent is explicit
```

Answer model:

```text
answer_type = short_text
accepted_answers allowed
case_sensitive = false
```

Blocked:

```text
implicit identity inference
ambiguous pronoun resolution
multi-person answer unless item explicitly asks for plural answer
```

### 6.2 literal_what

Required:

```text
answer is an explicitly named object, action, animal, food, place type, or concrete noun phrase
source evidence is direct
```

Answer model:

```text
answer_type = short_text or single_choice
```

Blocked:

```text
abstract answer
interpretive answer
paraphrase-only answer
```

### 6.3 literal_where

Required:

```text
source contains direct location evidence
location relation is stage-allowed
preposition is stage-allowed
```

Answer model:

```text
answer_type = short_text
accepted_answers may include normalized location phrase
```

Blocked:

```text
location inferred from world knowledge
ambiguous picture-only location without source locator
```

### 6.4 true_false

Required:

```text
statement maps to one explicit source fact
answer is true or false
false statements must contradict exactly one source fact
```

Answer model:

```text
answer_type = boolean
answer_key = true / false
```

Blocked:

```text
multiple facts in one statement
trick wording
inference-based falsehood
```

### 6.5 sentence_ordering

Required:

```text
level_stage allows sentence_ordering
source unit has explicit sequence evidence
sequence markers or preserved original order exist
```

Answer model:

```text
answer_type = ordered_ids
answer_key = ["sent_001", "sent_002", "sent_003"]
```

Blocked:

```text
no sequence marker and no preserved order evidence
ambiguous ordering
multi-paragraph ordering
```

### 6.6 cloze_vocabulary

Required:

```text
missing word has one valid local answer
answer vocabulary is stage-allowed or marked preview
cloze does not require advanced grammar generation
```

Answer model:

```text
answer_type = cloze_text
answer_key = normalized_word_or_phrase
accepted_answers may include singular/plural variants only if validated
```

Blocked:

```text
multiple plausible answers
abstract word gap
grammar transformation gap
formal exam gap-fill strategy
```

---

## 7. Source Trace and Evidence Contract

PracticeBank must preserve traceability without storing raw source payload in GitHub.

Allowed source_trace values:

```text
source_family
source_system
source_level
source_book_ref
source_unit_ref
source_sentence_refs
source_page_ref
source_locator
source_query_ref
```

Blocked source_trace values:

```text
raw_full_page_text
raw_full_passage_text
raw_full_book_text
unreviewed copied passage payload
```

Evidence can be represented by:

```text
evidence_ref
evidence_locator
source_sentence_ref
source_unit_ref
reviewed short display text when policy allows
```

Evidence must not become a hidden full-text copy of the source.

---

## 8. html_ready Derivation Rule

An item is `html_ready = true` only when:

```text
level_stage exists
question_type is allowed for level_stage
theme exists
grammar_focus exists
patterns exists or is explicitly empty for pure vocabulary item
vocabulary_refs exists
chunk_refs exists or is explicitly empty
source_trace exists
source_payload_stored == false
question.prompt exists
answer_model.answer_key exists
answer_evidence exists
private_homework_only == true
not_for_public_export == true
not_for_commercial_distribution == true
public_preview_allowed == false
raw_raz_text_persisted == false
full_passage_text_persisted == false
source_payload_copied_to_repo == false
validator_status.status == PASS
```

Package `html_ready` is true only if every selected item is html_ready and package policy flags pass.

---

## 9. Future Validator Gate Contract

The future P1-M4 implementation should provide validators for these gates.

### 9.1 Required Blocking Errors

```text
RV1_PB_ERR_SCHEMA_VERSION_MISSING
RV1_PB_ERR_INVALID_LEVEL_STAGE
RV1_PB_ERR_QUESTION_TYPE_NOT_ALLOWED_FOR_STAGE
RV1_PB_ERR_SOURCE_TRACE_MISSING
RV1_PB_ERR_SOURCE_PAYLOAD_STORED
RV1_PB_ERR_RAW_RAZ_TEXT_PERSISTED
RV1_PB_ERR_FULL_PASSAGE_TEXT_PERSISTED
RV1_PB_ERR_PUBLIC_EXPORT_ALLOWED
RV1_PB_ERR_COMMERCIAL_DISTRIBUTION_ALLOWED
RV1_PB_ERR_ANSWER_KEY_MISSING
RV1_PB_ERR_ANSWER_EVIDENCE_MISSING
RV1_PB_ERR_EVIDENCE_NOT_DIRECT
RV1_PB_ERR_CLOZE_NOT_UNIQUE
RV1_PB_ERR_SEQUENCE_EVIDENCE_MISSING
RV1_PB_ERR_FORMAL_ASSESSMENT_PATTERN_LEAKAGE
RV1_PB_ERR_AUTHORITY_STATUS_NOT_CANDIDATE
RV1_PB_ERR_PROMOTION_STATUS_NOT_NOT_PROMOTED
```

### 9.2 Allowed Warnings

```text
RV1_PB_WARN_PREVIEW_VOCABULARY
RV1_PB_WARN_LOW_PRIORITY_CHUNK_REVIEW_REQUIRED
RV1_PB_WARN_STAGE_TRANSITION_REINFORCEMENT_WEAK
RV1_PB_WARN_DISPLAY_TEXT_REQUIRES_PRIVATE_RUNTIME
```

Warnings do not imply automatic PASS. The future validator must decide whether a warning blocks html_ready for the current item.

---

## 10. Minimal Future File Layout Recommendation

This is a recommendation only, not implemented in this task.

```text
ulga/schemas/reading_v1_practice_bank.schema.json
ulga/builders/build_reading_v1_practice_bank.py
ulga/validators/validate_reading_v1_practice_bank.py
ulga/reports/reading_v1_practice_bank_summary.json
output/reading_v1/private_homework/*.json
```

Implementation must remain blocked until P1-M4 explicitly starts.

---

## 11. Reading System Progress Update

| Dimension | Before | After This DesignScan |
|---|---|---|
| Source Authority | PARTIAL | unchanged |
| Content Authority | PARTIAL | unchanged |
| Query Layer | PARTIAL | unchanged |
| Validation Layer | PARTIAL | contract defined for PracticeBank validation |
| Reading Generation | NOT_STARTED | still NOT_STARTED |
| Reading Practice | NOT_STARTED | PracticeBank contract defined |
| Reading Assessment | NOT_STARTED | still NOT_STARTED; P2 deferred |
| Production Readiness | NOT_STARTED | unchanged |
| Cambridge Spiral Scope | DESIGN_DEFINED | unchanged |
| PracticeBank Contract | NOT_STARTED | DESIGN_DEFINED |

Estimated P1 readiness after this task:

```text
P1-M0 Governance / Scope Lock ............ PARTIAL_DONE
P1-M1 Policy & Private Homework Safety ... MOSTLY_DONE
P1-M2 Cambridge Spiral Scope ............. COMPLETED_BY_DESIGN
P1-M3 PracticeBank Contract .............. COMPLETED_BY_DESIGN
P1-M4 PracticeBank Implementation ........ NOT_STARTED
P1-M5 Private Homework Overlay ........... NOT_STARTED
P1-M6 Local Runtime Pipeline ............. NOT_STARTED
P1-M7 Output Gate ........................ NOT_STARTED
P1-M8 HTML Practice Export ............... NOT_STARTED
P1-M9 P1 Closeout QA ..................... NOT_STARTED
```

---

## 12. Gate PASS Checklist

| Gate | Result | Evidence |
|---|---|---|
| Required task header exists | PASS | Section 1 |
| Stop condition exists | PASS | Section 1 |
| Package schema defined | PASS | Section 4 |
| Item schema defined | PASS | Section 5 |
| Question-type contracts defined | PASS | Section 6 |
| Source trace contract defined | PASS | Section 7 |
| Evidence contract defined | PASS | Section 7 |
| html_ready derivation rule defined | PASS | Section 8 |
| Future validator gates defined | PASS | Section 9 |
| Candidate-only boundary preserved | PASS | Sections 3-5 |
| Private homework policy preserved | PASS | Sections 4, 5, 8 |
| No PracticeBank generated | PASS | Documentation-only task |
| No HTML generated | PASS | Documentation-only task |
| No runtime modified | PASS | Documentation-only task |
| No RAZ raw text stored | PASS | Documentation-only task |

Task status:

```text
ReadingV1_PrivateHomeworkPracticeBank_DesignScan -> COMPLETED_BY_DESIGN
```

---

## 13. Deferred Issues Register

### D1

issue_id:
P1-M4_PracticeBank_Implementation

severity:
required_next_step

affected_file_or_artifact:
ulga/schemas, ulga/builders, ulga/validators, tests, reports

classification:
FUTURE_WORK

why_deferred:
This task defines the contract only. Implementation requires a separate task.

recommended_future_task:
ReadingV1_PrivateHomeworkPracticeBank_Implementation

blocks_current_task:
no

### D2

issue_id:
P1-M5_PrivateHomeworkCandidateOverlay

severity:
required_later_step

affected_file_or_artifact:
private homework overlay artifacts

classification:
FUTURE_WORK

why_deferred:
Overlay must wait until PracticeBank implementation exists.

recommended_future_task:
ReadingV1_PrivateHomeworkCandidateOverlay_DesignScan

blocks_current_task:
no

### D3

issue_id:
P1-M8_HTMLPracticeExport

severity:
required_later_step

affected_file_or_artifact:
HTML renderer / export artifacts

classification:
FUTURE_WORK

why_deferred:
HTML export must wait until output gate and private homework package are defined.

recommended_future_task:
ReadingV1_HTMLPracticeExport_Implementation

blocks_current_task:
no

---

## 14. Next Shortest Step

NEXT_SHORT_STEP:

```text
ReadingV1_PrivateHomeworkPracticeBank_Implementation
```

唯一執行動作:

```text
建立 PracticeBank schema / validator / minimal builder scaffolding，並加入不含 RAZ raw text 的 contract-level tests。
```

Next task boundary:

```text
Use this PracticeBank contract as input.
Implement schema and validator first.
Builder may emit only synthetic/local contract fixtures, not real RAZ source text.
Do not generate learner-facing homework HTML.
Do not enter P2 formal assessment expansion.
Do not promote PracticeBank output.
```
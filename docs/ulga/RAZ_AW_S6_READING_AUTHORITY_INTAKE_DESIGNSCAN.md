# RAZ-AW-S6 Reading Authority Intake DesignScan

## 1. Task Name

`RAZ-AW-S6_ReadingAuthorityIntake_DesignScan`

## 2. Task Classification

This task is a design scan only.

```text
design_only = true
implementation_allowed = false
runtime_change_allowed = false
authority_promotion_allowed = false
generated_content_allowed = false
```

This document defines the future intake contract for turning existing RAZ A-W derived sentence, page-unit, and reuse-unit artifacts into a Reading Authority intake layer.

It does not implement builders, validators, tests, graph outputs, reports, runtime behavior, learner-state behavior, scheduler behavior, or authority promotion.

## 3. Preflight Result

### 3.1 Repository scope

Repository inspected through the GitHub connector:

```text
cobelinfuture-Kobel/English_Learning_DB
```

### 3.2 Target document status before write

Target document did not exist before this task:

```text
docs/ulga/RAZ_AW_S6_READING_AUTHORITY_INTAKE_DESIGNSCAN.md
```

This task therefore creates a new design document.

### 3.3 Current RAZ state from inspected artifacts

Current inspected RAZ state shows:

```text
RAZ level discovery detects A-W.
A-W are ready for sentence, page-unit, and reuse-unit pipeline paths.
Current reusable seed query layer coverage is A-F.
Level I derived build has been smoke-piloted separately.
Reading stub authority already exists, but it is metadata-only and not learner-facing content.
```

Important distinction:

```text
A-W pipeline-ready
!=
A-W query-layer-ready
!=
A-W promoted Reading Authority
```

## 4. Files Inspected

The following files were inspected or used as grounding references for this design scan:

```text
docs/ulga/RAZ_S6U_I_DERIVED_BUILD_THIRD_SMOKE_PILOT.md
ulga/reports/raz_level_discovery_summary.json
ulga/reports/raz_reusable_content_seed_query_layer_summary.json
docs/ulga/ULGA_S11_READING_DIALOGUE_CONTENT_AUTHORITY_DESIGN_SCAN.md
docs/ulga/ULGA_S11A_READING_AUTHORITY_DESIGN_SCAN.md
docs/ulga/ULGA_S11B_READING_STUB_AUTHORITY_IMPLEMENTATION.md
```

Related existing RAZ components identified from prior implementation documentation:

```text
raz_output_jsons/derived/Level_{LEVEL}/normalized/raz_{LEVEL}_sentence_normalized.jsonl
raz_output_jsons/derived/Level_{LEVEL}/normalized/raz_{LEVEL}_page_unit_normalized.json
raz_output_jsons/derived/Level_{LEVEL}/normalized/raz_{LEVEL}_reuse_unit_normalized.json
raz_output_jsons/derived/Level_{LEVEL}/enriched/raz_{LEVEL}_sentence_enriched.jsonl
raz_output_jsons/derived/Level_{LEVEL}/enriched/raz_{LEVEL}_page_unit_enriched.json
raz_output_jsons/derived/Level_{LEVEL}/enriched/raz_{LEVEL}_reuse_unit_enriched.json
raz_output_jsons/derived/reports/raz_tagging_summary.json
raz_output_jsons/derived/reports/raz_tagging_warnings.json
raz_output_jsons/derived/reports/raz_tagging_schema_validation.json
ulga/graph/raz_level_discovery_inventory.json
ulga/reports/raz_level_discovery_summary.json
ulga/reports/raz_level_discovery_validation.json
ulga/reports/raz_reusable_content_seed_query_layer_summary.json
ulga/reports/raz_reusable_content_seed_query_layer_validation.json
ulga/reports/raz_downstream_discovery_drift_validation.json
tools/raz_normalized_tagging_pipeline.py
tests/test_raz_normalized_tagging_pipeline.py
ulga/policies/raz_seed_query_layer_policy.json
ulga/query/raz_reusable_content_seed_query_layer.py
ulga/validators/validate_raz_reusable_content_seed_query_layer.py
```

## 5. Current Artifact Inventory

### 5.1 RAZ level discovery

The current level discovery summary reports:

```text
total_detected_levels = 23
ready_level_count = 23
skipped_level_count = 0
partial_level_count = 0
invalid_level_count = 0
missing_required_input_count = 0
```

Detected ready levels:

```text
A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W
```

The same A-W range is reported ready for:

```text
sentence pipeline
page-unit pipeline
reuse-unit pipeline
```

### 5.2 Current query-layer coverage

The current reusable content seed query-layer summary is narrower than the A-W discovery range.

Current query-layer-ready levels:

```text
A, B, C, D, E, F
```

Current seed-card totals from the inspected summary:

```text
total_seed_cards = 14422
sentence = 7487
page_unit = 4925
reuse_unit = 2010
```

By level:

| Level | Sentence | Page Unit | Reuse Unit | Total |
|---|---:|---:|---:|---:|
| A | 808 | 804 | 4 | 1616 |
| B | 829 | 802 | 27 | 1658 |
| C | 1064 | 808 | 248 | 2120 |
| D | 1180 | 735 | 389 | 2304 |
| E | 1670 | 904 | 619 | 3193 |
| F | 1936 | 872 | 723 | 3531 |

Known query-layer guardrails:

```text
static_only = true
authority_promotion_allowed = false
generated_content_returned = false
unknown_theme_excluded_by_default = true
section_heading_excluded_by_default = true
human_review_required_excluded_by_default = true
max_limit = 100
```

Known QA warning counts:

```text
unknown_theme = 2038
unknown_pattern = 549
unknown_grammar = 391
section_heading_detected = 34
```

These warning counts must be preserved as intake risk signals. They must not be silently ignored by future Reading Authority intake.

### 5.3 Level I smoke-pilot evidence

The Level I smoke pilot confirms that derived output generation can preserve parity for a newly built level:

```text
raw_sentence_candidate_count = 3341
raw_page_unit_count = 1087
raw_reuse_unit_count = 1000
normalized_sentence_count = 3341
normalized_page_unit_count = 1087
normalized_reuse_unit_count = 1000
enriched_sentence_count = 3341
enriched_page_unit_count = 1087
enriched_reuse_unit_count = 1000
count_parity = PASS
schema_validation = PASS
```

This supports the design assumption that higher levels can be handled through the same sentence/page/reuse distinction, but this DesignScan does not claim A-W Reading Authority implementation.

### 5.4 Existing Reading Authority state

Reading Authority already has design and stub work:

```text
ULGA_S11A_READING_AUTHORITY_DESIGN_SCAN.md
ULGA_S11B_READING_STUB_AUTHORITY_IMPLEMENTATION.md
ulga/graph/reading_stub_authority.json
ulga/reports/reading_stub_summary.json
ulga/validators/validate_reading_stub_authority.py
```

The stub implementation created metadata-only reading records:

```text
reading_count = 1344
linked_opportunities = 1344
content_status = stub
coverage_ratio = 1.0
```

Critical boundary:

```text
Reading stub authority
!=
approved learner-facing readings
```

RAZ intake must not overwrite or reinterpret stub records as approved content.

## 6. Problem Statement

RAZ derived outputs now contain sentence, page-unit, and reuse-unit data that can support a future Reading Authority. However, without an explicit intake contract, the system risks mixing several different concepts:

```text
raw RAZ source text
sentence-level grammar/vocabulary evidence
page-level short reading text
multi-sentence reusable seed
rewritten/generated dialogue candidate
writing model candidate
exercise candidate
approved Reading Authority content
```

The intake layer must preserve these distinctions.

Core question:

```text
How can RAZ A-W derived artifacts be admitted as Reading Authority intake candidates without promoting raw, incomplete, generated, or rewritten material into learner-facing authority content?
```

## 7. Design Boundaries

### 7.1 In scope

This DesignScan covers:

```text
RAZ-derived sentence intake design
RAZ-derived page-unit intake design
RAZ-derived passage/reuse-unit intake design
source traceability
candidate-only lifecycle rules
metadata mapping rules
promotion blocking rules
validator design
future builder/test plan
```

### 7.2 Out of scope

This DesignScan does not:

```text
implement builders
implement validators
modify extraction code
modify RAZ_BookID.py
rebuild RAZ outputs
create reading_authority.json
promote any RAZ content
create generated reading passages
create generated dialogues
create writing templates
create assessment items
modify learner state
modify planner runtime
modify dashboard/API/scheduler behavior
```

## 8. Required Layer Separation

Future implementation must explicitly separate these layers:

```text
1. RAZ source artifact
2. sentence candidate
3. sentence authority candidate
4. page unit
5. passage unit
6. reusable content seed
7. derived content candidate
8. Reading Authority intake candidate
9. promoted Reading Authority item
```

### 8.1 RAZ source artifact

Original source artifact or derived source reference from RAZ extraction.

Examples:

```text
raw timeline extraction JSON
book/page source metadata
raw extracted page text
```

This is not authority content by itself.

### 8.2 Sentence candidate

A single sentence candidate extracted or normalized from RAZ.

Purpose:

```text
grammar tagging
vocabulary tagging
pattern tagging
chunk tagging
sentence-level validation
```

A sentence candidate may later support Reading Authority metadata, but it is not automatically a full reading asset.

### 8.3 Sentence authority candidate

A reviewed sentence candidate that may be used as a tiny reading unit or as evidence for grammar/vocabulary/pattern coverage.

It must still remain:

```text
authority_status = candidate_only
promotion_status = not_promoted
```

unless a later promotion task explicitly approves it.

### 8.4 Page unit

A page-level unit preserving sentence order and multi-sentence relationship.

Purpose:

```text
short reading candidate
page-level reading seed
sequencing seed
reading comprehension seed
vocabulary exposure evidence
```

Key rule:

```text
sentence split is allowed
but page-order relationship must be preserved
```

### 8.5 Passage unit

A multi-page or larger unit that may become a fuller Reading Authority intake candidate.

If current artifacts only expose page units and reuse units, passage units should be treated as a future aggregation layer rather than invented during S6.

### 8.6 Reusable content seed

A reusable unit with future derivation potential.

Examples:

```text
short_reading_seed
writing_model_seed
dialogue_rewrite_seed
exercise_seed
sequencing_seed
picture_prompt_seed
listening_audio_seed
assessment_seed
future_unknown_use
```

Reusable content seed records must remain candidate-only.

### 8.7 Derived content candidate

A derived candidate is any content that has been transformed beyond the original RAZ text.

Examples:

```text
RAZ page rewritten as dialogue
RAZ sentence turned into writing template
RAZ page transformed into quiz items
RAZ text expanded by GPT into a longer story
```

Derived content may be useful, but must not be treated as original RAZ authority.

### 8.8 Reading Authority intake candidate

A candidate record designed for future Reading Authority review and promotion.

This layer can hold imported RAZ text with traceability, metadata, and validation status.

### 8.9 Promoted Reading Authority item

A learner-facing or planner-facing approved reading record after later validation and review.

This is out of scope for S6.

## 9. Critical Authority Rule

The core rule for future implementation:

```text
RAZ original sentence/page/passage
-> may become Reading Authority intake candidate

RAZ rewritten/generated dialogue/writing/exercise
-> must stay derived_content_candidate
-> cannot become original RAZ authority
```

Generated or rewritten content may later enter Dialogue Authority, Writing Authority, Exercise Authority, or Assessment Authority only through a separate generated-content approval pipeline.

## 10. Proposed Schema: `reading_intake_candidate`

Future implementation may create a static artifact such as:

```text
ulga/graph/reading_intake_candidates.json
```

or a derived staging artifact such as:

```text
raz_output_jsons/derived/reading_intake/raz_aw_reading_intake_candidates.json
```

This DesignScan does not create those files.

Proposed record shape:

```json
{
  "reading_intake_id": "RAZ_A_READ_INTAKE_000001",
  "source": "RAZ",
  "source_level": "A",
  "source_book_id": "RAZ_A_BOOK_0001",
  "source_book_title": "",
  "source_page_number": null,
  "source_sentence_ids": [],
  "source_page_unit_id": null,
  "source_passage_unit_id": null,
  "clean_text": "",
  "sentence_count": 1,
  "unit_type": "sentence | page_unit | passage_unit",
  "authority_status": "candidate_only",
  "promotion_status": "not_promoted",
  "generated_content": false,
  "derived_from_original_text": true,
  "requires_review": true
}
```

### 10.1 Required field semantics

| Field | Meaning |
|---|---|
| `reading_intake_id` | Stable deterministic intake ID. |
| `source` | Must be `RAZ` for original RAZ intake candidates. |
| `source_level` | RAZ level A-W. |
| `source_book_id` | Stable book identifier from source metadata. |
| `source_book_title` | Human-readable book title if available. |
| `source_page_number` | Source page number when page-bound. |
| `source_sentence_ids` | Ordered sentence candidate IDs. |
| `source_page_unit_id` | Source page unit ID when applicable. |
| `source_passage_unit_id` | Source passage unit ID when applicable. |
| `clean_text` | Clean original-derived text, not generated expansion. |
| `sentence_count` | Materialized count, not query-time guess. |
| `unit_type` | One of `sentence`, `page_unit`, `passage_unit`. |
| `authority_status` | Must remain `candidate_only` in S6/S7 intake. |
| `promotion_status` | Must remain `not_promoted` until explicit later promotion. |
| `generated_content` | Must be false for original RAZ authority intake. |
| `derived_from_original_text` | Must be true for RAZ intake candidates. |
| `requires_review` | Must be true unless a later approval process changes it. |

## 11. Proposed Schema: `reading_intake_metadata`

Proposed metadata shape:

```json
{
  "level_estimate": null,
  "raz_level": "A",
  "cefr_estimate": null,
  "theme_tags": [],
  "vocabulary_tags": [],
  "grammar_tags": [],
  "pattern_tags": [],
  "chunk_tags": [],
  "word_count": 0,
  "sentence_count": 0,
  "readability_notes": [],
  "coverage_notes": []
}
```

### 11.1 Metadata rules

1. `raz_level` is source level, not CEFR.
2. `cefr_estimate` must be treated as estimated metadata unless validated against CEFR authority.
3. Empty tags are allowed for candidate records but must produce warnings.
4. `word_count` and `sentence_count` must be materialized for deterministic reporting.
5. `coverage_notes` should preserve unknown theme, unknown grammar, unknown pattern, and warning states from upstream RAZ tagging.
6. Intake must not silently coerce unknown metadata into broad generic tags unless the validator records the fallback.

## 12. Proposed Schema: `source_traceability`

Proposed traceability shape:

```json
{
  "source_type": "raz_pdf_extraction | raz_derived_json | raz_page_unit",
  "source_file": "",
  "source_artifact_path": "",
  "source_hash": null,
  "book_id": "",
  "page_number": null,
  "candidate_ids": [],
  "extraction_stage": "",
  "build_stage": "",
  "review_stage": "pending"
}
```

### 12.1 Traceability rules

Blocking rule:

```text
No source traceability -> no Reading Authority intake candidate.
```

Future builder must preserve:

```text
source path
source level
book id
page number when applicable
sentence candidate ids
page unit id when applicable
reuse unit id when applicable
extraction/build stage
review stage
```

If source hash is not yet available, `source_hash` may be `null` in candidate-only intake, but the validator must warn.

## 13. Proposed Schema: `reusability_tags`

Reusable tags should be controlled but extensible.

Minimum allowed values:

```text
short_reading_seed
writing_model_seed
dialogue_rewrite_seed
exercise_seed
sequencing_seed
picture_prompt_seed
listening_audio_seed
comprehension_question_seed
grammar_pattern_seed
vocabulary_exposure_seed
assessment_seed
future_unknown_use
sentence_only
```

### 13.1 Tag rules

1. `sentence_only` should be used for records that are safe as sentence-level evidence but not useful as page/passage content.
2. Multi-sentence page units should usually have at least one reuse-oriented tag.
3. `future_unknown_use` is allowed when the unit appears reusable but the final downstream authority is not yet known.
4. Tags must not imply promotion.
5. Tags must not imply generated content approval.

Mandatory status for reusable content:

```text
authority_status = candidate_only
promotion_status = not_promoted
```

## 14. Multi-Sentence Page / Passage Handling

From RAZ-C and above, multi-sentence units become increasingly important.

Future implementation must preserve two parallel views:

```text
sentence layer
page/passage layer
```

### 14.1 Sentence layer

Purpose:

```text
grammar validation
vocabulary validation
pattern validation
chunk validation
sentence length checks
sentence-level query
```

### 14.2 Page / passage layer

Purpose:

```text
short reading candidate
reading comprehension seed
sequencing seed
vocabulary exposure sequence
picture prompt support
listening audio script candidate
```

### 14.3 Required order preservation

The following must be preserved:

```text
source sentence order
page order when available
book-level sequence when available
```

Blocking error if violated:

```text
page_unit losing sentence order
```

### 14.4 Do not collapse layers

Future implementation must not treat a page unit as only a bag of sentences.

It must also not treat every sentence as an independent reading passage unless explicitly marked as `unit_type = sentence`.

## 15. Generated / Rewritten Content Blocking Rules

Generated or rewritten content must be blocked from original RAZ authority promotion.

### 15.1 Examples of blocked promotion

```text
RAZ page rewritten into A/B dialogue
RAZ sentence expanded into a longer story
RAZ page converted into worksheet questions
RAZ text paraphrased by an LLM
RAZ page transformed into writing scaffold
```

These can become:

```text
derived_content_candidate
```

They cannot become:

```text
original_raz_reading_authority
```

### 15.2 Future derived-content path

Safe future route:

```text
RAZ original text
-> reusable content seed
-> derived content candidate
-> generated-content validator
-> manual/review approval
-> relevant downstream authority candidate
```

Relevant downstream authority may include:

```text
Dialogue Authority
Writing Authority
Exercise Authority
Assessment Authority
```

not original RAZ Reading Authority.

## 16. Reading Authority Intake vs Existing Reading Stub Authority

Existing `reading_stub_authority.json` is a planner-contract skeleton.

RAZ intake is different.

| Layer | Purpose | Content text? | Approved learner-facing content? |
|---|---|---:|---:|
| Reading Stub Authority | Validate Opportunity -> Reading delivery chain | No | No |
| RAZ Reading Intake | Stage imported RAZ-derived text for review | Yes | No |
| Reading Authority | Approved/queryable learner-facing reading content | Yes | Later only |

RAZ intake must not overwrite stub authority.

Future implementation may later create linkage between RAZ intake candidates and learning opportunities, but that must be done through explicit matching rules, not by assuming a `1:1` stub replacement.

## 17. Linkage to ULGA and Learning Opportunity

Future RAZ intake should connect downstream through content authority contracts already defined in S11.

Recommended future linkage fields:

```json
{
  "linked_opportunities": [],
  "focus_vocabulary_refs": [],
  "reinforcement_vocabulary_refs": [],
  "grammar_refs": [],
  "pattern_refs": [],
  "chunk_refs": [],
  "theme_refs": [],
  "dependency_refs": []
}
```

### 17.1 Linkage rules

1. RAZ intake should not become the source of truth for ULGA nodes.
2. RAZ intake should reference existing authority nodes where available.
3. Missing refs are warnings for candidate-only records and blockers for approved records.
4. Learning Opportunity linkage should remain `N:N` in future design.
5. `CONTENT_PRECEDES_CONTENT` must not be treated as `REQUIRES`.
6. Page order or book sequence may support sequencing, but not prerequisite truth.

## 18. Validator Design

A future validator such as:

```text
ulga/validators/validate_raz_reading_authority_intake.py
```

should fail closed for malformed records.

### 18.1 Blocking errors

Future implementation must define blocking errors for:

1. Missing source traceability.
2. Missing book ID.
3. Missing source level.
4. Empty clean text.
5. Generated content marked as original authority.
6. Derived dialogue/writing/exercise candidate promoted as RAZ authority.
7. Page unit losing sentence order.
8. Duplicate intake ID.
9. Unit type inconsistent with sentence count.
10. Missing review status.
11. Missing promotion status.
12. Mixed original and generated text in the same authority candidate.
13. `authority_status` not equal to `candidate_only` during S6/S7 intake.
14. `promotion_status` not equal to `not_promoted` during S6/S7 intake.
15. Invalid `unit_type`.
16. Source level outside discovered A-W scope.
17. Candidate references source sentence IDs that do not exist.
18. Candidate references page unit ID that does not exist.
19. Candidate has conflicting `generated_content` and `derived_from_original_text` flags.
20. Candidate claims approved Reading Authority status without explicit promotion task.

### 18.2 Warnings

Future implementation should define warnings for:

1. Missing CEFR estimate.
2. Missing theme tags.
3. Missing vocabulary tags.
4. Missing grammar tags.
5. Very short page unit.
6. Very long page unit.
7. Multi-sentence page with no reusability tags.
8. Ambiguous source level.
9. Missing page number when expected.
10. Missing source hash.
11. Unknown theme inherited from RAZ tagging.
12. Unknown grammar inherited from RAZ tagging.
13. Unknown pattern inherited from RAZ tagging.
14. Section-heading-like text detected.
15. Human review required.
16. Text appears to be metadata rather than reading content.
17. Duplicate clean text across book/page scope.
18. Weak opportunity-link confidence.
19. Missing book title.
20. Empty `coverage_notes` when upstream warnings exist.

## 19. Future Builder Design

A future builder such as:

```text
ulga/builders/build_raz_reading_authority_intake.py
```

should be static/offline and deterministic.

### 19.1 Inputs

Potential inputs:

```text
raz_output_jsons/derived/Level_{LEVEL}/enriched/raz_{LEVEL}_sentence_enriched.jsonl
raz_output_jsons/derived/Level_{LEVEL}/enriched/raz_{LEVEL}_page_unit_enriched.json
raz_output_jsons/derived/Level_{LEVEL}/enriched/raz_{LEVEL}_reuse_unit_enriched.json
ulga/graph/raz_level_discovery_inventory.json
ulga/reports/raz_level_discovery_summary.json
ulga/policies/raz_seed_query_layer_policy.json
```

### 19.2 Outputs

Potential outputs:

```text
ulga/graph/raz_reading_intake_candidates.json
ulga/reports/raz_reading_intake_summary.json
ulga/reports/raz_reading_intake_validation.json
```

or, if the team wants to keep RAZ staging outside `ulga/graph` initially:

```text
raz_output_jsons/derived/reading_intake/raz_aw_reading_intake_candidates.json
raz_output_jsons/derived/reports/raz_reading_intake_summary.json
raz_output_jsons/derived/reports/raz_reading_intake_validation.json
```

Decision deferred to implementation task.

### 19.3 Builder behavior

Future builder should:

1. Discover levels through `raz_level_discovery_inventory.json`, not hard-code A-W.
2. Allow scoped `--levels` execution.
3. Preserve sentence/page/reuse unit distinction.
4. Preserve source ordering.
5. Produce deterministic IDs.
6. Materialize counts.
7. Preserve warning metadata.
8. Set all records to candidate-only.
9. Block generated content from original RAZ intake.
10. Produce summary and validation reports.

## 20. Future Test Plan

Future tests should cover:

1. Builder runs for a single level.
2. Builder runs for multiple levels.
3. Builder respects level discovery.
4. Sentence records preserve source sentence IDs.
5. Page units preserve sentence order.
6. Reuse units preserve reusability tags.
7. Generated content cannot be promoted.
8. Derived content cannot be original RAZ authority.
9. Duplicate IDs fail validation.
10. Empty text fails validation.
11. Missing source traceability fails validation.
12. Missing metadata creates warnings but does not approve records.
13. Summary counts match output counts.
14. A-W discovery does not imply A-W query-layer promotion.
15. Existing reading stub authority is not modified.
16. Existing learning opportunities are not modified.
17. Existing RAZ derived outputs are not modified unless explicitly rebuilding.
18. Full validator remains deterministic.

## 21. Risks and Open Questions

### 21.1 Risks

Primary risks:

```text
A-W pipeline readiness being mistaken for A-W Reading Authority readiness
query-layer A-F coverage being mistaken for full A-W coverage
raw RAZ text being promoted without review
multi-sentence context being lost during sentence splitting
generated dialogue/writing/exercise content being treated as original RAZ authority
unknown theme/grammar/pattern metadata being silently accepted
stub reading records being confused with imported RAZ reading text
content sequence being mistaken for dependency truth
```

### 21.2 Open questions

1. Should the first implementation output live under `ulga/graph` or under `raz_output_jsons/derived/reading_intake`?
2. Should A-W be built in one pass or staged A-F, G-I, J-W based on existing query-layer maturity?
3. Should Level I smoke-pilot findings become the template for J-W expansion QA?
4. Should page units become the first Reading Authority intake target, with sentence records used only as metadata evidence?
5. Should reuse units be included in the same intake artifact or remain a separate reusable-content seed layer?
6. Should source hashes be blocking in V1 or warning-only until all upstream artifacts expose stable hashes?
7. Should opportunity matching be implemented in the intake builder or in a later query/match layer?
8. How should RAZ book title normalization be handled across levels?

## 22. Recommended Implementation Sequence

Preferred sequence:

```text
RAZ-AW-S6A_ReadingAuthorityInputCoverageQA
RAZ-AW-S7_ReadingAuthorityIntake_SchemaImplementation
RAZ-AW-S8_ReadingAuthorityIntake_BuilderImplementation
RAZ-AW-S9_ReadingAuthorityIntake_ValidatorQA
RAZ-AW-S10_ReadingAuthorityOpportunityMatch_DesignScan
```

Reasoning:

```text
A-W are discovery-ready, but current reusable seed query layer is A-F.
Before implementing A-W intake, run a dedicated input coverage QA to confirm which levels have stable enriched sentence/page/reuse outputs available on main.
```

## 23. Recommended Next Task

Because the inspected summary shows A-W pipeline readiness but A-F query-layer readiness, the safer next task is:

```text
RAZ-AW-S6A_ReadingAuthorityInputCoverageQA
```

Only after that confirms stable enriched inputs across the intended scope should implementation proceed to:

```text
RAZ-AW-S7_ReadingAuthorityIntake_SchemaImplementation
```

## 24. Final Verdict

```text
RAZ-AW-S6_ReadingAuthorityIntake_DesignScan = COMPLETE
```

This scan defines the intake boundary and schema direction for RAZ A-W Reading Authority candidates.

It does not implement Reading Authority intake.
It does not promote RAZ content.
It does not approve generated content.
It does not modify runtime behavior.
It does not alter planner, learner state, dashboard, scheduler, or API behavior.

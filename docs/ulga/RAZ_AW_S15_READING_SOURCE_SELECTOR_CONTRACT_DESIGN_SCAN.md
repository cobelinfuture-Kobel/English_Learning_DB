# RAZ-AW-S15 Reading Source Selector Contract Design Scan

## 1. Task

`RAZ-AW-S15_ReadingSourceSelectorContract_DesignScan`

This task defines how Reading System V1 may read, filter, rank, and hand off source candidates from the S11/S12 Reading intake query layer into later Reading practice item generation.

The task is documentation-only. It defines source-selection rules. It does not generate Reading items, does not write a builder, does not write a validator, and does not rebuild the S11 intake query index.

## 2. Scope

This design scan defines:

1. Source selector purpose and boundary.
2. Approved source input families.
3. Candidate eligibility rules.
4. Required source traceability minimums.
5. Level filters.
6. Source type filters.
7. Sentence count filters.
8. Reusability tag filters.
9. Generated-content exclusion rules.
10. Candidate-only / no-promotion rules.
11. Source suitability matrix for V1 question-type families.
12. Sampling and ranking policy for later S17 implementation.
13. Selector output contract handed to S16/S17.

## 3. Allowed Files

This task may create or modify only:

```text
docs/ulga/RAZ_AW_S15_READING_SOURCE_SELECTOR_CONTRACT_DESIGN_SCAN.md
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

S15 is blocked if it fails to define any of the following:

1. Which source types are eligible for Reading System V1.
2. Which source types are excluded.
3. Which source traceability fields are mandatory.
4. How source level is filtered.
5. How sentence count affects eligibility.
6. How reusability tags affect eligibility.
7. How generated content is excluded.
8. How candidate-only and no-promotion boundaries are preserved.
9. How selected source records are handed to S17 without changing the S14 item schema.

## 6. Warning Policy

Allowed warnings:

```text
question-type-specific prompt construction deferred to S16
builder implementation deferred to S17
validator implementation deferred to S18
output package implementation deferred to S19
source-ranking weights may be adjusted by later QA if source distribution is poor
unknown CEFR estimate may be allowed if RAZ level is source-declared
```

Blocking warnings:

```text
selector permits source records with no traceability
selector permits generated source content as original source
selector permits promoted or learner-facing content inside V1
selector requires generated artifacts in S15
selector changes the S14 item schema without a schema-blocker
selector cannot support any S16 question-type contract
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
reading_practice_items.json
reading_practice_package_summary.json
```

S15 defines the selector contract only. S17 may later implement selector use inside the candidate item builder if S15 and S16 are complete.

## 8. Runtime Impact

None.

This task does not affect runtime, app code, dashboards, APIs, schedulers, learner state, adaptive planner state, or student-facing output.

## 9. Promotion Impact

None.

Selected source records remain:

```text
candidate_only
not_promoted
not learner_facing
not final authority
```

S15 does not approve final Reading Authority promotion and does not approve learner-facing delivery.

## 10. Stop Condition

S15 passes when this document defines:

1. Approved source input families.
2. Required selector input fields.
3. Required selector output fields.
4. Eligibility rules.
5. Exclusion rules.
6. Level filtering policy.
7. Source type filtering policy.
8. Sentence count filtering policy.
9. Reusability tag filtering policy.
10. Source suitability matrix for V1 question types.
11. Sampling/ranking policy.
12. Handoff requirements for S16, S17, and S18.

S15 must stop after this contract is defined. It must not write a selector implementation, item builder, validator, test, generated JSON, runtime output, or learner-facing artifact.

## 11. Deferred Issues Register

| Issue ID | Classification | Why deferred | Recommended future task | Blocks S15? |
|---|---|---|---|---|
| `S16-QUESTION-TYPES` | `FUTURE_WORK` | Exact prompt/answer construction rules belong to question-type contracts | `RAZ-AW-S16_ReadingQuestionTypeContract_DesignScan` | No |
| `S17-ITEM-BUILDER` | `FUTURE_WORK` | Builder implementation is forbidden in S15 | `RAZ-AW-S17_ReadingCandidateItemBuilder_Implementation` | No |
| `S18-VALIDATOR` | `FUTURE_WORK` | Validator implementation is forbidden in S15 | `RAZ-AW-S18_ReadingItemValidator_Implementation` | No |
| `S19-OUTPUT-PACKAGE` | `FUTURE_WORK` | Quiz/worksheet output is downstream of item generation and validation | `RAZ-AW-S19_ReadingPracticeOutputPackage_Implementation` | No |
| `READING-V2-ASSESSMENT-PATTERNS` | `FUTURE_WORK` | Cambridge/KET pattern selection is outside V1 source selector | Reading System V2 | No |
| `LEARNER-ADAPTIVE-SOURCE-SELECTION` | `FUTURE_WORK` | Learner-state driven source selection belongs to adaptive roadmap | Reading System V4 | No |
| `LOCAL-GENERATED-ARTIFACT-PERSISTENCE` | `FUTURE_WORK` | Artifact persistence is separate from source-selection contract | Generated artifact persistence policy | No |

## 12. Source References

S15 follows S14, which requires Reading practice items to preserve source traceability, evidence support, answer model validity, candidate-only lifecycle, and no learner-facing promotion.

S14 recognizes these schema-compatible source types:

```text
sentence_candidate
page_unit
reuse_unit_candidate
normalized_reading_unit
enriched_reading_unit
```

S14 explicitly assigns S15 the task of deciding which source types are eligible for each question type and states that S14 itself does not decide sampling, ranking, or source-selection priority.

S14 also requires S15 to define eligible source types per question-type family, level filters, sentence count filters, reusability tag filters, traceability minimums, candidate-only/generated-content exclusions, and sampling/ranking policy.

## 13. Selector Purpose

The Reading source selector is the controlled bridge between:

```text
S11/S12 Reading intake query index
```

and:

```text
S17 candidate Reading item builder
```

Its purpose is to choose source records that are safe and suitable for V1 Reading practice item generation.

The selector answers:

```text
Which source record may be used for this question-type family?
```

It does not answer:

```text
How should the final question prompt be written?
How should distractors be generated?
How should the item be validated?
How should the quiz package be formatted?
```

Those are S16, S17, S18, and S19 responsibilities.

## 14. Approved Selector Input Families

S15 allows the selector to inspect source candidates from approved Reading source layers only.

Approved input families:

| Source family | Description | V1 status |
|---|---|---|
| `sentence_candidate` | Single extracted sentence candidate from RAZ-derived source | Eligible with filters |
| `page_unit` | Page-level text unit preserving sentence order and page context | Eligible with filters |
| `reuse_unit_candidate` | Multi-sentence reusable content seed preserving future-use metadata | Eligible with filters |
| `normalized_reading_unit` | Normalized reading unit from derived layer | Eligible with filters |
| `enriched_reading_unit` | Enriched reading unit with additional metadata/tags | Eligible with filters |

S15 does not approve arbitrary raw files, free-floating LLM output, learner-written text, dialogue rewrites, audio-only records, image-only records, or final promoted authority records as V1 source inputs.

## 15. Required Selector Input Fields

A source candidate is selector-readable only if it can expose these conceptual fields:

```text
source_system
source_intake_id
source_record_id
source_type
source_level
clean_text
sentence_count
generated_content
authority_status
promotion_status
source_traceability
```

Conditional fields:

```text
book_id
page_number
source_path
sentence_candidate_ids
reusability_tags
query_tags
theme_tags
vocabulary_tags
grammar_tags
```

The selector must treat missing required fields as a current-source rejection, not as permission to infer or invent metadata.

## 16. Required Selector Output Shape

S17 may later consume selected source records through this conceptual output shape:

```json
{
  "selection_id": "READING_SOURCE_SELECTION_000001",
  "selection_task": "RAZ-AW-S17_ReadingCandidateItemBuilder_Implementation",
  "source": {
    "source_system": "RAZ",
    "source_intake_id": "RAZ_READING_INTAKE_A_000001",
    "source_record_id": "RAZ_A_BOOK001_P003",
    "source_type": "sentence_candidate",
    "source_level": "A",
    "book_id": "RAZ_A_BOOK001",
    "page_number": 3,
    "source_path": "raz_output_jsons/derived/Level_A/example.json",
    "generated_content": false,
    "authority_status": "candidate_only",
    "promotion_status": "not_promoted"
  },
  "selector": {
    "eligible": true,
    "eligible_question_types": [
      "literal_who"
    ],
    "selection_reasons": [
      "source_traceability_present",
      "sentence_count_allowed",
      "candidate_only_boundary_present"
    ],
    "rejection_reasons": [],
    "ranking_band": "preferred"
  },
  "evidence_seed": {
    "evidence_text": "The boy runs.",
    "evidence_sentences": [
      "The boy runs."
    ],
    "sentence_count": 1,
    "evidence_source": "source_sentence"
  }
}
```

S15 does not require this exact JSON file to be produced. This is the contract shape for S17 implementation planning.

## 17. Eligibility Rules

A source candidate is eligible only when all required conditions pass:

1. `source_system` is approved for V1. Current approved value: `RAZ`.
2. `source_type` is in the approved source family list.
3. `source_intake_id` or equivalent approved intake reference is present.
4. `source_record_id` or equivalent original source record reference is present.
5. `clean_text` or approved source text is non-empty.
6. `sentence_count >= 1`.
7. `generated_content = false` for the underlying source text.
8. `authority_status = candidate_only`.
9. `promotion_status = not_promoted`.
10. The source can supply evidence text for the requested question-type family.

If any required condition fails, the source must not be selected for S17 item generation.

## 18. Exclusion Rules

The selector must exclude:

```text
missing source traceability
missing source text
empty clean_text
sentence_count = 0
unknown source_type
free-floating generated text
generated dialogue rewrite used as original reading source
promoted final authority records
learner-facing records
records with malformed reusability/tag objects
records whose clean_text is abnormal extraction noise
records whose source level is missing and cannot be used even for structural testing
```

A rejected record may be counted in later QA, but must not be passed to S17 as selected input.

## 19. Level Filter Policy

V1 source selection should prefer RAZ source-declared level.

Approved V1 level handling:

| Level condition | Selector behavior |
|---|---|
| RAZ level present | Eligible if other filters pass |
| CEFR estimate present | May be copied into item `level.cefr_estimate` |
| CEFR estimate absent | Allow `unknown` only if RAZ level is source-declared |
| RAZ level absent and CEFR absent | Reject except for explicitly approved structural smoke tests |
| Level conflicts with source path | Reject or mark blocked until readback QA resolves it |

S15 does not derive new CEFR levels. Derivation belongs to a future enrichment or QA task.

## 20. Source Type Filter Policy

Each source type has a default role:

| Source type | Default role | V1 selector status |
|---|---|---|
| `sentence_candidate` | Single-sentence literal comprehension and cloze seed | Preferred for single-sentence items |
| `page_unit` | Multi-sentence context, ordering, and page-level evidence | Preferred for sequence/context items |
| `reuse_unit_candidate` | Multi-sentence reusable exercise/assessment seed | Preferred when `reusability_tags` match |
| `normalized_reading_unit` | Clean normalized reading unit | Eligible if traceability preserved |
| `enriched_reading_unit` | Metadata-rich reading unit | Eligible if no tag malformation and traceability preserved |

S15 does not add new source types. Adding source types requires a later contract patch.

## 21. Sentence Count Filter Policy

Sentence count controls question-type eligibility.

| Sentence count | Selector interpretation |
|---:|---|
| 0 | Reject |
| 1 | Eligible for literal single-sentence questions and cloze |
| 2-5 | Eligible for literal questions, true/false, sentence ordering, and short multi-sentence evidence |
| 6-10 | Eligible only if S16 confirms the question type can handle longer context |
| >10 | Defer from V1 unless explicitly approved by S16/S17 QA |

Default V1 preference:

```text
1 sentence for literal_who / literal_what / literal_where / cloze_vocabulary
2-5 sentences for true_false / sentence_ordering
```

## 22. Reusability Tag Filter Policy

Reusability tags are selection signals, not promotion signals.

Preferred tags for V1:

```text
exercise_seed
comprehension_question_seed
sequencing_seed
vocabulary_exposure_seed
assessment_seed
short_reading_seed
future_unknown_use
```

Question-type preferences:

| Question type | Preferred reusability tags |
|---|---|
| `literal_who` | `exercise_seed`, `comprehension_question_seed`, `short_reading_seed` |
| `literal_what` | `exercise_seed`, `comprehension_question_seed`, `short_reading_seed` |
| `literal_where` | `exercise_seed`, `comprehension_question_seed`, `short_reading_seed` |
| `true_false` | `exercise_seed`, `assessment_seed`, `comprehension_question_seed` |
| `sentence_ordering` | `sequencing_seed`, `short_reading_seed`, `exercise_seed` |
| `cloze_vocabulary` | `vocabulary_exposure_seed`, `exercise_seed`, `assessment_seed` |

The selector may still use records with no reusability tags if source type, traceability, and evidence requirements are strong. Missing tags are a warning, not an automatic rejection.

Malformed tags are blocking for enriched/reuse records.

## 23. Source Suitability Matrix

| Question type | Preferred source types | Allowed sentence count | Required source feature |
|---|---|---:|---|
| `literal_who` | `sentence_candidate`, `page_unit`, `enriched_reading_unit` | 1-5 | Explicit person/character noun phrase or subject candidate |
| `literal_what` | `sentence_candidate`, `page_unit`, `enriched_reading_unit` | 1-5 | Explicit action/object/event candidate |
| `literal_where` | `sentence_candidate`, `page_unit`, `enriched_reading_unit` | 1-5 | Explicit place or prepositional phrase candidate |
| `true_false` | `sentence_candidate`, `page_unit`, `reuse_unit_candidate`, `enriched_reading_unit` | 1-5 | Evidence can support a true statement and safe false variant |
| `sentence_ordering` | `page_unit`, `reuse_unit_candidate`, `normalized_reading_unit`, `enriched_reading_unit` | 2-5 | Stable sentence order preserved |
| `cloze_vocabulary` | `sentence_candidate`, `page_unit`, `enriched_reading_unit` | 1-5 | Removable vocabulary token from source text |

S16 must define exact per-question feature extraction and rejection rules.

## 24. Ranking Band Policy

S15 defines ranking bands but does not implement numeric scoring.

Ranking bands:

```text
preferred
acceptable
structural_only
rejected
```

`preferred` sources:

```text
complete traceability
source-declared RAZ level
clean text
sentence count matches question-type preference
candidate_only / not_promoted
useful reusability tag or strong source type match
```

`acceptable` sources:

```text
traceability present
clean text present
candidate-only boundary present
minor metadata gaps that do not block evidence support
```

`structural_only` sources:

```text
usable for schema/build smoke testing only
not enough metadata for quality item generation
must be reported separately
```

`rejected` sources:

```text
violates any required eligibility or exclusion rule
```

## 25. Sampling Policy

S17 should later sample selected sources deterministically.

Recommended deterministic ordering keys:

```text
source_level
source_type
book_id
page_number
source_record_id
source_intake_id
```

S17 should not randomly sample by default. If sampling is needed, it must use a stable seed and report sampling policy in the generated summary.

S15 does not implement sampling.

## 26. Duplicate and Near-duplicate Policy

The selector should avoid selecting duplicate source records for the same generated item batch when duplicates are detectable by:

```text
source_record_id
source_intake_id
normalized clean_text
book_id + page_number
```

Duplicate suppression must not delete source records. It only controls batch selection for S17.

## 27. Abnormal Text Policy

The selector must reject source text that appears to be extraction noise, including:

```text
replacement characters
high symbol density
empty text
page marker only
non-reading metadata only
malformed JSON string payloads
```

Exact abnormal-text detection belongs to S17/S18 implementation if not already available upstream. S15 only defines the rejection requirement.

## 28. Selector Output to S14 Item Source Object

S17 must map selected source fields into the S14 item `source` object without inventing metadata.

Required mapping:

| Selector output | S14 item field |
|---|---|
| `source_system` | `source.source_system` |
| `source_intake_id` | `source.source_intake_id` |
| `source_record_id` | `source.source_record_id` |
| `source_type` | `source.source_type` |
| `source_level` | `source.source_level` and `level.source_level` |
| `book_id` | `source.book_id` |
| `page_number` | `source.page_number` |
| `source_path` | `source.source_path` |
| `generated_content` | `source.generated_content` |
| `authority_status` | `source.authority_status` and `lifecycle.authority_status` |
| `promotion_status` | `source.promotion_status` and `lifecycle.promotion_status` |
| `clean_text` | `evidence.evidence_text` or prompt display source, as allowed by S16 |
| `sentence_count` | `evidence.sentence_count` |

## 29. Validator Expectations for S18

S18 must later verify that selected sources used by generated items satisfy:

1. Source fields are present.
2. Source type is approved.
3. Source is candidate-only.
4. Source is not promoted.
5. Source text is not generated content.
6. Evidence text came from selected source text.
7. Sentence count matches question-type requirement.
8. Reusability tags, if present, are arrays of strings.
9. The item does not become learner-facing.

## 30. Handoff to S16

S16 must consume the S15 source suitability matrix and define exact source feature requirements for each question-type family.

S16 must decide, per question type:

1. Whether source text is shown to the learner.
2. Whether answer phrase extraction is deterministic or heuristic.
3. Whether choices are required.
4. Whether distractors must come from same source, same level, same theme, or fixed safe pool.
5. Which source records must be rejected even if S15 says they are structurally eligible.

S16 must not generate items.

## 31. Handoff to S17

S17 may implement source selection only after S15 and S16 are complete.

S17 builder must:

1. Read approved source candidates from approved paths.
2. Apply S15 eligibility and ranking bands.
3. Apply S16 question-type-specific feature rules.
4. Emit `READING_PRACTICE_ITEM_V1` candidate items.
5. Preserve source traceability exactly.
6. Mark items candidate-only and not learner-facing.
7. Write only approved generated outputs.

## 32. Handoff to S18

S18 validator must enforce S15 source-selection requirements when validating generated items.

S18 must reject items if:

```text
source was not eligible
source traceability is incomplete
source text cannot support evidence
source generated_content is true
source lifecycle is promoted or learner-facing
source_type is incompatible with question_type
sentence_count violates the question-type contract
```

## 33. S15 Closeout Result

Status:

```text
PASS
```

Files changed:

```text
docs/ulga/RAZ_AW_S15_READING_SOURCE_SELECTOR_CONTRACT_DESIGN_SCAN.md
```

Reading System Progress Tracker:

```text
Task ID: RAZ-AW-S15_ReadingSourceSelectorContract_DesignScan
Task name: Reading Source Selector Contract Design Scan
Reading system target: Reading System V1
Stage: S15
Input source: S14 Reading Practice Item Contract Design Scan; S13 Reading Practice System Goal and Progress Tracker Design Scan; S11/S12 intake query-index boundary; Project Task Expansion Control Policy
Output artifact: S15 design scan markdown
Progress contribution: Defines approved V1 source input families, selector eligibility rules, exclusion rules, level/source-type/sentence-count/reusability filters, source suitability matrix, ranking bands, sampling policy, and S16-S18 handoff requirements
Completed stage count: 5 / 10 after S15
Remaining stage count: 5 / 10 after S15
Blocking issue: None
Deferred issue: S16 question type contract, S17 builder, S18 validator, S19 output package, S20 closeout QA, V2-V5 roadmap
Generated artifact policy: No generated artifacts created or committed
Runtime impact: None
Promotion impact: None
Closeout status: PASS
Next allowed task: RAZ-AW-S16_ReadingQuestionTypeContract_DesignScan
```

## 34. Next Allowed Task

```text
RAZ-AW-S16_ReadingQuestionTypeContract_DesignScan
```

S16 may define exact V1 question-type contracts for literal who/what/where, true/false, sentence ordering, and cloze vocabulary.

S16 must not generate Reading items.

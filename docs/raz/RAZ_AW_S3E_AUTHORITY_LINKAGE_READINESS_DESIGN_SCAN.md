# RAZ-AW-S3E Authority Linkage Readiness Design Scan

## Preflight

Task:

```text
RAZ-AW-S3E_AuthorityLinkageReadinessDesignScan
```

Execution mode:

```text
DesignScan only
```

Scope:

```text
Evaluate whether current RAZ normalized/enriched candidate artifacts are structurally ready
for future Reading / Dialogue / Writing / Exercise / Assessment / Query / Opportunity bridges.
No runtime code changes.
No schema changes.
No corpus mutation.
No authority promotion.
```

Files to create or modify:

```text
docs/raz/RAZ_AW_S3E_AUTHORITY_LINKAGE_READINESS_DESIGN_SCAN.md
```

Risk level:

```text
Low
```

Reason:

```text
This task adds documentation only.
It does not modify text-bearing corpus artifacts, validators, builders, runtime, scheduler, API, or ULGA graph truth.
```

Real-trading impact:

```text
None
```

Restart required:

```text
No
```

Repository-safe conclusion:

```text
The current RAZ A-W normalized/enriched layer is safe for authority-linkage design work,
but not safe for authority promotion or learner-facing delivery.
```

## Files Inspected

- `docs/raz/prompts/RAZ_AW_S3E_AUTHORITY_LINKAGE_READINESS_DESIGN_SCAN_PROMPT.md`
- `docs/raz/RAZ_AW_S3_RAW_HYDRATION_TO_NORMALIZED_ENRICHED_READINESS_DESIGN_SCAN.md`
- `docs/raz/RAZ_AW_S3D3_ENRICHED_CANDIDATE_LAYER_CLOSEOUT.md`
- `schemas/raz/raz_normalized_books.schema.json`
- `schemas/raz/raz_normalized_sentences.schema.json`
- `schemas/raz/raz_normalized_page_units.schema.json`
- `schemas/raz/raz_normalized_reuse_units.schema.json`
- `schemas/raz/raz_enriched_sentences.schema.json`
- `schemas/raz/raz_enriched_units.schema.json`
- `reports/raz/enriched_candidate_layer_closeout.json`
- `reports/raz/raz_aw_enriched_query_facet_readiness_summary.json`
- `reports/raz/authority_linkage_gap_report.json`
- `docs/ulga/ULGA_S11_READING_DIALOGUE_CONTENT_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S11A_READING_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S11B_READING_STUB_AUTHORITY_IMPLEMENTATION.md`
- `ulga/reports/static_candidate_query_layer_closeout.json`
- `raz_output_jsons/derived/Level_K/normalized/raz_K_normalized_sentences.json`
- `raz_output_jsons/derived/Level_K/normalized/raz_K_normalized_page_units.json`
- `raz_output_jsons/derived/Level_K/normalized/raz_K_normalized_reuse_units.json`
- `raz_output_jsons/derived/Level_K/enriched/raz_K_enriched_sentences.json`
- `raz_output_jsons/derived/Level_K/enriched/raz_K_enriched_units.json`

## Current Artifact Inventory

### Sentence-level artifacts

| Path | Role | Coverage | Status | Safe for authority linkage | Safe for GitHub storage |
| --- | --- | --- | --- | --- | --- |
| `schemas/raz/raz_normalized_sentences.schema.json` | normalized sentence contract | A-W by schema intent | normalized schema | yes, design input only | yes |
| `schemas/raz/raz_enriched_sentences.schema.json` | enriched sentence contract | A-W by schema intent | enriched schema | yes, candidate linkage only | yes |
| `raz_output_jsons/derived/Level_K/normalized/raz_K_normalized_sentences.json` | local text-bearing normalized sentence sample | inspected local sample K; A-W existence evidenced by reports | candidate normalized | yes, design input only | no |
| `raz_output_jsons/derived/Level_K/enriched/raz_K_enriched_sentences.json` | local text-bearing enriched sentence sample | inspected local sample K; A-W existence evidenced by reports | candidate enriched | yes, candidate linkage only | no |

Observed sentence facts:

```text
sentence_count: 201993
authority_linkage_status exists
review_status exists
candidate_vocab_refs / candidate_grammar_refs / candidate_pattern_refs exist
current candidate_ref_counts in sanitized QA summary are all 0
```

### Page / passage unit artifacts

| Path | Role | Coverage | Status | Safe for authority linkage | Safe for GitHub storage |
| --- | --- | --- | --- | --- | --- |
| `schemas/raz/raz_normalized_page_units.schema.json` | page-unit contract | A-W by schema intent | normalized schema | yes, Reading bridge design input | yes |
| `raz_output_jsons/derived/Level_K/normalized/raz_K_normalized_page_units.json` | local text-bearing page-unit sample | inspected local sample K; A-W existence evidenced by reports | candidate normalized | yes, design input only | no |
| `schemas/raz/raz_enriched_units.schema.json` | enriched unit contract for page/reuse units | A-W by schema intent | enriched schema | yes, candidate linkage only | yes |
| `raz_output_jsons/derived/Level_K/enriched/raz_K_enriched_units.json` | local enriched unit sample | inspected local sample K; A-W existence evidenced by reports | candidate enriched | yes, candidate linkage only | no |

Observed unit facts:

```text
unit_count: 41964
page_unit_count: 22632
reuse_unit_count: 19332
unit_type: page_unit / reuse_unit
candidate_use_cases includes reading / dialogue / exercise / assessment / review in schema
sanitized counts currently show reading / dialogue / exercise / review, but no observed assessment count
```

### Reuse unit artifacts

| Path | Role | Coverage | Status | Safe for authority linkage | Safe for GitHub storage |
| --- | --- | --- | --- | --- | --- |
| `schemas/raz/raz_normalized_reuse_units.schema.json` | reuse-unit contract | A-W by schema intent | normalized schema | partial; must remain candidate-only | yes |
| `raz_output_jsons/derived/Level_K/normalized/raz_K_normalized_reuse_units.json` | local reuse-unit sample | inspected local sample K; A-W existence evidenced by reports | candidate normalized | partial; promotion unsafe | no |

### Derived candidate artifacts

| Path | Role | Coverage | Status | Safe for authority linkage | Safe for GitHub storage |
| --- | --- | --- | --- | --- | --- |
| `docs/ulga/ULGA_S11B_READING_STUB_AUTHORITY_IMPLEMENTATION.md` | future Reading stub contract evidence | ULGA reading stub only | derived/stub authority doc | partial; stub only | yes |
| `ulga/reports/static_candidate_query_layer_closeout.json` | downstream query readiness evidence | ULGA static query layer | report | partial; bridge consumers exist, authority not implemented | yes |
| `reports/raz/raz_aw_enriched_query_facet_readiness_summary.json` | enriched downstream facet/readiness evidence | A-W aggregate | report | yes, design only | yes |
| `reports/raz/authority_linkage_gap_report.json` | manifest-only linkage gap evidence | manifest aggregate | report | limited; not field-complete | yes |

Expected but not present in GitHub as first-class authority artifacts:

```text
reading_authority.json -> not_present_in_github
dialogue_authority.json -> not_present_in_github
writing_authority.json -> not_present_in_github
exercise_authority.json -> not_present_in_github
assessment_authority.json -> not_present_in_github
RAZ-derived dialogue candidate corpus -> not_present_in_github
RAZ-derived writing seed corpus -> not_present_in_github
RAZ-derived exercise seed corpus -> not_present_in_github
RAZ-derived assessment seed corpus -> not_present_in_github
```

### Summary / validation reports

| Path | Role | Coverage | Status | Safe for authority linkage | Safe for GitHub storage |
| --- | --- | --- | --- | --- | --- |
| `reports/raz/enriched_candidate_layer_closeout.json` | candidate layer closeout | A-W aggregate | report | yes, design gate only | yes |
| `reports/raz/raz_aw_enriched_query_facet_readiness_summary.json` | query-facet evidence | A-W aggregate | report | yes, placeholder-only | yes |
| `reports/raz/authority_linkage_gap_report.json` | manifest-only gap evidence | manifest aggregate | report | limited | yes |

### Design / roadmap docs

| Path | Role | Coverage | Status | Safe for authority linkage | Safe for GitHub storage |
| --- | --- | --- | --- | --- | --- |
| `docs/ulga/ULGA_S11_READING_DIALOGUE_CONTENT_AUTHORITY_DESIGN_SCAN.md` | Reading/Dialogue authority target contract | ULGA future authority | design | yes | yes |
| `docs/ulga/ULGA_S11A_READING_AUTHORITY_DESIGN_SCAN.md` | Reading authority target contract | ULGA future authority | design | yes | yes |
| `docs/raz/RAZ_AW_S3_RAW_HYDRATION_TO_NORMALIZED_ENRICHED_READINESS_DESIGN_SCAN.md` | upstream layer separation and source-ref rules | A-W aggregate | design | yes | yes |
| `docs/raz/RAZ_AW_S3D3_ENRICHED_CANDIDATE_LAYER_CLOSEOUT.md` | candidate-only closeout | A-W aggregate | closeout | yes | yes |

## Linkage Readiness Matrix

| Target layer | Required fields | Currently available fields | Missing fields | Promotion risk | Readiness |
| --- | --- | --- | --- | --- | --- |
| Reading Authority | stable source trace, level, book/page order, sentence/page/reuse grouping, clean text, review/promotion gate | `source_ref`, `level`, `book_id`, `page_number`, `sentence_uids`, `text`, `authority_status`, `review_status` | explicit `page_unit_id`, `passage_unit_id`, `sentence_final_id`, `clean_text`, `candidate_order`, `source_traceability`, allow/block targets | medium | PARTIAL |
| Dialogue Authority | multi-sentence grouping, dialogue suitability, generated-content boundary, opportunity linkage | `candidate_use_cases`, `dialogue_candidate_flag`, `sentence_uids`, `review_status`, `authority_linkage_status` | `generated_content`, `derived_from_original_text`, `allowed_authority_targets`, `blocked_authority_targets`, dialogue turn contract, promotion gate | high | NOT_READY |
| Writing Authority | source-to-seed derivation trace, template boundary, generated-content flag, review contract | candidate signals only via reuse/use-case metadata | writing seed artifact, derivation contract, source sentence mapping, promotion gate fields | high | NOT_READY |
| Exercise Authority | source linkage, exercise candidate boundary, question schema entry point | `candidate_use_cases` includes exercise, source sentence/unit references exist upstream | exercise seed artifact, question structure, answer schema, generated-content fields | high | NOT_READY |
| Assessment Authority | question schema, answer key, scoring rule, error diagnosis, learner-state-safe linkage | only `candidate_use_cases` enum mentions `assessment`; no evidence of populated assessment seed records | `question_type`, `skill_area`, `concept_tags`, `cognitive_skill`, `correct_answer`, `answer_key`, `error_type`, `remediation_tag`, `scoring_rule` | high | NOT_READY |
| Content Query Layer | deterministic joins, candidate filters, linkage placeholders, content-mode filtering | books/sentences/units join ready, query facets ready, linkage placeholders ready, static query layer exists downstream | explicit authority-target allow/block fields, final content-mode bridge contract, candidate exclusion rules per target | medium | PARTIAL |
| Learning Opportunity Binding | authority refs, content-opportunity bridge ids, source trace, promotion-safe content status | ULGA opportunity layer exists; Reading stub shows future linkage pattern | `linked_opportunity` or `linked_opportunities` on RAZ artifacts, allowed targets, review-before-promotion gate, approved authority refs | high | NOT_READY |

## Required Linkage Field Contract

| Field | Status | Depends on / needed by |
| --- | --- | --- |
| `source_type` | present | all layers |
| `source_level` | partially_present | all layers |
| `book_id` | present | all layers |
| `page_number` | partially_present | Reading, Query |
| `page_unit_id` | missing | Reading, Query, Opportunity Binding |
| `passage_unit_id` | missing | Reading, Dialogue, Query |
| `sentence_candidate_id` | partially_present | Reading, Dialogue, Writing, Exercise |
| `sentence_final_id` | missing | all promotion targets |
| `source_sentence_candidate_ids` | missing | Dialogue, Writing, Exercise, Assessment |
| `clean_text` | missing | Reading, Dialogue, Writing |
| `sentence_count` | partially_present | Reading, Dialogue, Exercise, Assessment |
| `candidate_order` | missing | Reading, Dialogue |
| `has_multi_sentence_unit` | missing | Reading, Dialogue, Exercise |
| `belongs_to_reuse_unit` | missing | Reading, Dialogue, Writing, Exercise |
| `reuse_unit_id` | partially_present | Reading, Dialogue, Writing, Exercise |
| `reusability_tags` | partially_present | Dialogue, Writing, Exercise, Assessment |
| `derivation_potential` | missing | Dialogue, Writing, Exercise, Assessment |
| `authority_status` | present | all layers |
| `promotion_status` | missing | all promotion targets |
| `review_status` | present | all layers |
| `generated_content` | missing | Dialogue, Writing, Exercise, Assessment |
| `derived_from_original_text` | missing | Dialogue, Writing, Exercise, Assessment |
| `source_traceability` | missing | all layers |
| `allowed_authority_targets` | missing | all bridge targets |
| `blocked_authority_targets` | missing | all bridge targets |
| `required_review_before_promotion` | missing | all promotion targets |

Classification notes:

```text
present
= explicit field exists in current schema or inspected local sample

partially_present
= equivalent information exists but under different names or incomplete shape

missing
= not found in inspected current artifacts
```

Equivalence observed during scan:

```text
source_level ~= level
sentence_candidate_id ~= sentence_uid
reuse_unit_id ~= reuse_unit_uid
sentence_count ~= unit_sentence_count for units only
```

## Authority Boundary Rules

Required future rules:

```text
1. RAZ original sentence can become sentence authority only after sentence-level validation.
2. RAZ original page / passage unit may become Reading / Passage Authority only after page-unit review.
3. RAZ reuse_unit_candidates must remain candidate_only.
4. RAZ-derived dialogue rewrites must be marked generated_content=true or derived_from_original_text=true and must never be mixed with original RAZ sentence authority records.
5. Writing model seeds are not Writing Authority until template extraction and review are completed.
6. Exercise / Assessment seeds are not Assessment Authority until question schema, answer key, scoring rule, and error tagging contract exist.
7. Generated content must remain candidate_only with review_status=pending unless a later explicit authority-promotion task promotes it.
8. Any bridge implementation must reject candidate_only records unless the target layer explicitly accepts candidates.
9. Reading stub or other planner-validation placeholders must stay outside approved learner-facing authority.
10. Sequence guidance must not be treated as prerequisite truth without a separate dependency contract.
```

Current boundary evidence already present:

```text
authority_status: candidate_only
content_authority_status: not_promoted
authority_linkage_status: candidate_only / not_evaluated
review_status: pending / needs_review / rejected
```

Current boundary gaps:

```text
No explicit generated_content field in normalized/enriched records
No explicit promotion_status field
No explicit allowed_authority_targets / blocked_authority_targets field
No explicit required_review_before_promotion field
```

## Risk Analysis

| Risk | Level | Impact | Recommended mitigation |
| --- | --- | --- | --- |
| accidental promotion of `candidate_only` units | HIGH | candidate content could be treated as approved Reading/Dialogue/Exercise content | add `promotion_status`, target allow/block fields, and bridge validators that fail closed |
| mixing original RAZ text with generated or rewritten content | HIGH | authority corruption and audit ambiguity | add `generated_content`, `derived_from_original_text`, reviewer gate, separate storage/query views |
| losing page order or sentence order | MEDIUM | Reading reconstruction and passage continuity become unstable | materialize `candidate_order`, `page_unit_id`, `passage_unit_id`, and deterministic ordering validators |
| losing source traceability | HIGH | future review cannot map authority items back to RAZ source evidence | add normalized `source_traceability` object and keep sentence-to-unit lineage arrays |
| over-linking RAZ units to Dialogue / Writing / Assessment too early | HIGH | future content layers may inherit unreviewed or pedagogically weak candidates | default all non-Reading targets to blocked until dedicated contracts exist |
| missing fields that block ULGA Content Query bridge | MEDIUM | downstream query views can read candidates but cannot safely filter by target authority policy | add allow/block target fields and content-mode readiness contract |
| missing fields that block Learning Opportunity binding | HIGH | no explicit content-opportunity bridge ids or approved-target gating | add `linked_opportunity`/`linked_opportunities` in future bridge layer, not directly in source candidates |
| assessment linkage without question / answer / remediation structure | HIGH | learner-state evidence would be unsafe or misleading | require assessment seed contract before any Assessment Authority bridge |
| GitHub storage risk from full text-bearing derived dumps | HIGH | copyright/scope and repository hygiene risk | keep full text-bearing `raz_output_jsons/derived/Level_*` local; commit only schemas, docs, sanitized reports |
| duplicate execution creating duplicate bridge records later | MEDIUM | content authority catalogs may drift or double-link | stable IDs, idempotent bridge builder, duplicate fingerprint validator |
| process restart during future bridge build | MEDIUM | partial bridge outputs may leave mixed promotion states | atomic write strategy and resumable checkpoints in later implementation |
| empty or zero-ref candidate tag state | MEDIUM | bridge may claim vocabulary/grammar/pattern readiness without actual authority refs | keep Reading as PARTIAL and all other pedagogical targets as NOT_READY until candidate refs are populated and validated |

## Assessment Linkage Note

Current evidence:

```text
`candidate_use_cases` schema allows `assessment`
sanitized aggregate counts do not show observed assessment-bearing units
no RAZ assessment seed artifact was found
no question schema or answer-key contract was found in current RAZ artifacts
ULGA static candidate query closeout marks `assessment_authority: FUTURE_NOT_READY`
```

Assessment linkage field check:

| Field | Status |
| --- | --- |
| `question_type` | missing |
| `skill_area` | missing |
| `concept_tags` | missing |
| `cognitive_skill` | missing |
| `correct_answer` | missing |
| `answer_key` | missing |
| `student_answer` | not_applicable |
| `is_correct` | not_applicable |
| `error_type` | missing |
| `error_detail` | missing |
| `remediation_tag` | missing |
| `scoring_rule` | missing |

Assessment linkage status:

```text
NOT_READY
```

Reason:

```text
Current RAZ artifacts expose candidate-use-case hints only.
They do not expose a question schema, answer key, scoring rule, or error-diagnosis contract.
Assessment Authority must not be marked READY or PARTIAL from current evidence.
```

## Recommended Next Tasks

### 1. `RAZ-AW-S3F_SourceTraceabilityContractPatch_DesignScan`

Purpose:

```text
Define a minimal patch for page/passage/sentence lineage fields and explicit source_traceability.
```

Expected files to inspect:

```text
schemas/raz/raz_normalized_*.schema.json
schemas/raz/raz_enriched_*.schema.json
docs/raz/RAZ_AW_S3A_NORMALIZED_ENRICHED_SCHEMA_CONTRACT.md
```

Expected files to create or modify:

```text
docs/raz/RAZ_AW_S3F_SOURCE_TRACEABILITY_CONTRACT_PATCH_DESIGN_SCAN.md
```

Type:

```text
DesignScan
```

Risk:

```text
Low
```

### 2. `RAZ-AW-S3G_ReuseUnitPromotionGateValidator_Implementation`

Purpose:

```text
Add a fail-closed validator that prevents reuse units and candidate-only records from leaking into approved authority targets.
```

Expected files to inspect:

```text
tools/raz_aw_validate_normalized.py
tools/raz_aw_validate_enriched.py
schemas/raz/raz_normalized_reuse_units.schema.json
schemas/raz/raz_enriched_units.schema.json
```

Expected files to create or modify:

```text
tools/raz_aw_validate_enriched.py
reports/raz/raz_aw_enriched_validator_qa_report.json
reports/raz/raz_aw_enriched_validator_safety_report.json
```

Type:

```text
Implementation
```

Risk:

```text
Medium
```

### 3. `RAZ-AW-S4_PagePassageUnitReviewContract_DesignScan`

Purpose:

```text
Define how page_unit and future passage_unit records become reviewable Reading candidates without losing order or source lineage.
```

Expected files to inspect:

```text
schemas/raz/raz_normalized_page_units.schema.json
schemas/raz/raz_enriched_units.schema.json
docs/ulga/ULGA_S11A_READING_AUTHORITY_DESIGN_SCAN.md
```

Expected files to create or modify:

```text
docs/raz/RAZ_AW_S4_PAGE_PASSAGE_UNIT_REVIEW_CONTRACT_DESIGN_SCAN.md
```

Type:

```text
DesignScan
```

Risk:

```text
Low
```

### 4. `RAZ-AW-S5_ReadingAuthorityBridge_DesignScan`

Purpose:

```text
Design the minimal bridge from RAZ candidate sentences/page units into future Reading Authority or Reading Stub intake.
```

Expected files to inspect:

```text
docs/ulga/ULGA_S11A_READING_AUTHORITY_DESIGN_SCAN.md
docs/ulga/ULGA_S11B_READING_STUB_AUTHORITY_IMPLEMENTATION.md
reports/raz/raz_aw_enriched_query_facet_readiness_summary.json
```

Expected files to create or modify:

```text
docs/raz/RAZ_AW_S5_READING_AUTHORITY_BRIDGE_DESIGN_SCAN.md
```

Type:

```text
DesignScan
```

Risk:

```text
Medium
```

### 5. `RAZ-AW-S6_AssessmentSeedContract_DesignScan`

Purpose:

```text
Define the first safe contract for exercise/assessment seeds, answer keys, scoring, and remediation tags before any learner-state linkage.
```

Expected files to inspect:

```text
docs/ulga/ULGA_S11_READING_DIALOGUE_CONTENT_AUTHORITY_DESIGN_SCAN.md
ulga/reports/static_candidate_query_layer_closeout.json
ulga/learner_state/evidence_event_schema.json
```

Expected files to create or modify:

```text
docs/raz/RAZ_AW_S6_ASSESSMENT_SEED_CONTRACT_DESIGN_SCAN.md
```

Type:

```text
DesignScan
```

Risk:

```text
Medium
```

### 6. `ULGA-S16_ContentQueryLayer_RAZBridge_DesignScan`

Purpose:

```text
Define how RAZ bridge outputs will be exposed to static content-query consumers without silently widening candidate eligibility.
```

Expected files to inspect:

```text
ulga/reports/static_candidate_query_layer_closeout.json
docs/ulga/ULGA_S11_READING_DIALOGUE_CONTENT_AUTHORITY_DESIGN_SCAN.md
reports/raz/raz_aw_enriched_query_facet_readiness_summary.json
```

Expected files to create or modify:

```text
docs/ulga/ULGA_S16_CONTENT_QUERY_LAYER_RAZ_BRIDGE_DESIGN_SCAN.md
```

Type:

```text
DesignScan
```

Risk:

```text
Medium
```

## Final Readiness Verdict

Verdict:

```text
PARTIAL_READY_REQUIRES_CONTRACT_PATCH
```

Reason:

```text
The repository already has the correct candidate-layer separation:
raw -> normalized -> enriched -> downstream query/readiness summaries.

It also already preserves stable source references, candidate-only status, review status,
page-unit and reuse-unit separation, and downstream query placeholders.

However, future authority bridges still lack explicit contract fields for:
promotion_status
generated_content
derived_from_original_text
source_traceability
allowed_authority_targets
blocked_authority_targets
required_review_before_promotion
page/passage lineage normalization
assessment seed structure

Because of those gaps, Reading is only PARTIAL, while Dialogue, Writing, Exercise,
Assessment, and Learning Opportunity binding are not safe to bridge yet.
```

Controlled final statement:

```text
The current RAZ A-W candidate corpus is ready for bridge design continuation,
but not ready for content authority promotion.
```

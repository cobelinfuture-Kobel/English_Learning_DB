# RAZ-AW-S3D Enriched Builder Implementation Plan

## 1. Preflight

Task:

```text
RAZ-AW-S3D_EnrichedBuilderImplementationPlan
```

Scope:

```text
ENRICHED BUILDER IMPLEMENTATION PLAN ONLY
SANITIZED CONTRACT DESIGN ONLY
NO NORMALIZED / ENRICHED BUILD EXECUTION
NO RAW RAZ JSON READ
NO RAW RAZ JSON MUTATION
NO RAW RAZ JSON COMMIT
NO FULL NORMALIZED CORPUS COMMIT
NO FULL ENRICHED CORPUS COMMIT
NO TEXT-BEARING GITHUB REPORTS
NO CONTENT AUTHORITY PROMOTION
NO TAG AUTHORITY PROMOTION
NO GRAMMAR / VOCABULARY / PATTERN AUTHORITY LINKAGE APPROVAL
NO READING / DIALOGUE / EXERCISE GENERATION
NO RUNTIME / API / SCHEDULER / DASHBOARD CHANGE
```

Upstream dependencies:

```text
RAZ-AW-S3C3_NormalizedCandidateLayerCloseout: PASS
Normalized candidate layer: CLOSED_AS_PASS
safe_for_enriched_builder_design: true
safe_for_enriched_builder_implementation: true, after operator approval
safe_for_content_authority_promotion: false
safe_for_generation: false
```

Files created by this task:

```text
docs/raz/RAZ_AW_S3D_ENRICHED_BUILDER_IMPLEMENTATION_PLAN.md
reports/raz/enriched_builder_implementation_plan.json
```

Risk level:

```text
Low
```

Reason:

```text
This task creates an enriched builder plan only. It does not run enrichment and does not emit text-bearing enriched artifacts.
```

---

## 2. Purpose

S3D defines how to convert the validated normalized candidate layer into an enriched candidate layer.

The enriched layer is for:

```text
query facets
candidate learning signals
candidate tag hints
candidate vocabulary / grammar / pattern references
candidate reading / dialogue / exercise usefulness signals
future authority-linkage QA input
```

The enriched layer is not for:

```text
final content authority
approved tag authority
approved grammar/vocabulary/pattern linkage
learner-facing generation
runtime/API serving
```

---

## 3. Input Contract

Primary local input root:

```text
G:\HomeWork\English_Learning_DB\raz_output_jsons\derived
```

Expected normalized input files per level:

```text
raz_output_jsons/derived/Level_<LEVEL>/normalized/raz_<LEVEL>_normalized_books.json
raz_output_jsons/derived/Level_<LEVEL>/normalized/raz_<LEVEL>_normalized_sentences.json
raz_output_jsons/derived/Level_<LEVEL>/normalized/raz_<LEVEL>_normalized_page_units.json
raz_output_jsons/derived/Level_<LEVEL>/normalized/raz_<LEVEL>_normalized_reuse_units.json
```

Required upstream sanitized reports:

```text
reports/raz/raz_aw_normalized_build_summary.json
reports/raz/raz_aw_normalized_validator_qa_report.json
reports/raz/raz_aw_normalized_validator_safety_report.json
reports/raz/normalized_candidate_layer_closeout.json
```

Required schema contracts:

```text
schemas/raz/raz_enriched_books.schema.json
schemas/raz/raz_enriched_sentences.schema.json
schemas/raz/raz_enriched_units.schema.json
```

Required upstream counts:

```text
book_count: 1959
sentence_count: 201993
page_unit_count: 22632
reuse_unit_count: 19332
```

---

## 4. Output Contract

Selected local/Drive-derived enriched output pattern:

```text
raz_output_jsons/derived/Level_<LEVEL>/enriched/raz_<LEVEL>_enriched_books.json
raz_output_jsons/derived/Level_<LEVEL>/enriched/raz_<LEVEL>_enriched_sentences.json
raz_output_jsons/derived/Level_<LEVEL>/enriched/raz_<LEVEL>_enriched_units.json
```

Selected local/Drive-derived cross-level reports:

```text
raz_output_jsons/derived/reports/raz_aw_enriched_local_manifest.json
raz_output_jsons/derived/reports/raz_aw_enriched_count_reconciliation.json
```

GitHub-safe reports only:

```text
reports/raz/raz_aw_enriched_build_summary.json
reports/raz/raz_aw_enriched_safety_report.json
reports/raz/raz_aw_enriched_count_reconciliation_summary.json
```

GitHub forbidden for S3D/S3E:

```text
raz_output_jsons/derived/Level_*/enriched/*.json
full enriched sentence corpus
full text-bearing enriched corpora
full normalized sentence corpus
raw RAZ files
raw or normalized text dumps
```

---

## 5. Enriched Record Contracts

### 5.1 Enriched books

One enriched book record per normalized book.

Required status boundaries:

```text
enrichment_status: candidate_enriched
authority_linkage_status: candidate_only or not_evaluated
review_status: pending
validation_status: not_evaluated before validator, pass after validator
```

Candidate fields:

```text
sentence_count
page_unit_count
reuse_unit_count
estimated_text_complexity_bucket
candidate_theme_tags
candidate_content_unit_tags
candidate_pedagogical_tags
```

Initial deterministic policy:

```text
estimated_text_complexity_bucket is derived from sentence/token statistics only.
candidate tags remain hints, not authority tags.
```

### 5.2 Enriched sentences

One enriched sentence record per normalized sentence.

Required status boundaries:

```text
enrichment_status: candidate_enriched
authority_linkage_status: candidate_only or not_evaluated
review_status: pending
validation_status: not_evaluated before validator, pass after validator
```

Candidate fields:

```text
normalized_token_count
candidate_vocab_refs
candidate_grammar_refs
candidate_pattern_refs
sentence_length_bucket
punctuation_profile
dialogue_candidate_flag
reading_sentence_candidate_flag
```

Initial deterministic policy:

```text
candidate_vocab_refs: empty array until cross-source vocabulary bridge is explicitly approved.
candidate_grammar_refs: empty array until grammar authority linkage is explicitly approved.
candidate_pattern_refs: empty array until pattern authority linkage is explicitly approved.
sentence_length_bucket is derived from normalized_token_count.
punctuation_profile is derived from normalized sentence text but no text is emitted to GitHub reports.
dialogue_candidate_flag is a deterministic punctuation/quote/speaker-signal heuristic only.
reading_sentence_candidate_flag defaults to true for accepted normalized sentence candidates.
```

### 5.3 Enriched units

One enriched unit record per normalized page unit and normalized reuse unit.

Required status boundaries:

```text
enrichment_status: candidate_enriched
authority_linkage_status: candidate_only or not_evaluated
review_status: pending
validation_status: not_evaluated before validator, pass after validator
```

Candidate fields:

```text
unit_type
sentence_uids
unit_sentence_count
unit_token_count
candidate_use_cases
candidate_reuse_tags
reading_usefulness_score_candidate
dialogue_usefulness_score_candidate
exercise_usefulness_score_candidate
```

Initial deterministic policy:

```text
page_unit -> unit_type page_unit
reuse_unit -> unit_type reuse_unit
candidate_use_cases are heuristic only.
usefulness scores are candidate scores only, not planner authority.
```

---

## 6. Deterministic Enrichment Rules

Allowed deterministic features:

```text
book sentence/page/reuse counts
token counts
sentence length bucket
terminal punctuation
contains comma / question mark / exclamation mark / quote mark
page/reuse unit sentence counts
page/reuse unit token counts
simple candidate use-case scoring
```

Blocked until later authority work:

```text
formal CEFR assertion
approved vocabulary authority references
approved grammar authority references
approved pattern authority references
approved content/tag authority promotion
learner-facing recommendation rank
exercise generation
```

---

## 7. Planned Builder

Planned tool:

```text
tools/raz_aw_build_enriched_from_normalized.py
```

Planned command:

```powershell
cd G:\HomeWork\English_Learning_DB
python tools\raz_aw_build_enriched_from_normalized.py --derived-root G:\HomeWork\English_Learning_DB\raz_output_jsons\derived
```

Responsibilities:

```text
read normalized local/Drive-derived artifacts
build enriched candidate books/sentences/units
preserve candidate-only status boundaries
emit full enriched artifacts to local/Drive-derived surface only
emit sanitized summaries to reports/raz only
```

---

## 8. Planned Validator

Planned tool:

```text
tools/raz_aw_validate_enriched.py
```

Required validation order:

```text
1. enriched file presence validation
2. schema_version validation
3. stable ID validation
4. normalized reference validation
5. candidate-only / no-promotion validation
6. feature-range validation
7. count reconciliation validation
8. forbidden text/payload leakage validation
9. GitHub output safety validation
```

Required blockers:

```text
missing enriched files
schema_version mismatch
unresolved normalized references
approved/promoted/final_authority status values
text values emitted to GitHub reports
raw payload keys emitted to GitHub reports
book/sentence/unit count mismatch against normalized summaries
```

---

## 9. Commit Policy

Allowed to commit:

```text
tools/raz_aw_build_enriched_from_normalized.py
tools/raz_aw_validate_enriched.py
reports/raz/raz_aw_enriched_build_summary.json
reports/raz/raz_aw_enriched_safety_report.json
reports/raz/raz_aw_enriched_count_reconciliation_summary.json
reports/raz/raz_aw_enriched_validator_qa_report.json
reports/raz/raz_aw_enriched_validator_safety_report.json
docs/raz/*enriched*.md
```

Not allowed to commit:

```text
raz_output_jsons/derived/Level_*/enriched/*.json
raz_output_jsons/derived/Level_*/normalized/*.json
raw RAZ files
full text-bearing normalized or enriched corpora
scratch dumps
```

Do not run:

```powershell
git add .
```

---

## 10. Task Breakdown

### S3D1 — Enriched Builder Implementation

Create:

```text
tools/raz_aw_build_enriched_from_normalized.py
```

Expected outputs after operator run:

```text
raz_output_jsons/derived/Level_<LEVEL>/enriched/*.json
reports/raz/raz_aw_enriched_build_summary.json
reports/raz/raz_aw_enriched_safety_report.json
reports/raz/raz_aw_enriched_count_reconciliation_summary.json
```

### S3D2 — Enriched Validator QA

Create:

```text
tools/raz_aw_validate_enriched.py
```

Expected outputs after operator run:

```text
reports/raz/raz_aw_enriched_validator_qa_report.json
reports/raz/raz_aw_enriched_validator_safety_report.json
reports/raz/raz_aw_enriched_schema_validation_summary.json
reports/raz/raz_aw_enriched_reference_validation_summary.json
```

### S3D3 — Enriched Candidate Layer Closeout

Close out whether enriched candidate layer is safe for later authority-linkage candidate design.

---

## 11. S3D Decision

```text
RAZ-AW-S3D_EnrichedBuilderImplementationPlan: PASS
```

Readiness decision:

```text
S3D1 enriched builder implementation: READY
S3D2 enriched validator QA: READY_AFTER_BUILDER
S3D3 enriched candidate layer closeout: NOT_YET
Content authority promotion: NOT_YET
Tag authority promotion: NOT_YET
Grammar/vocabulary/pattern authority linkage approval: NOT_YET
Generation: NOT_YET
Runtime/API integration: NOT_YET
```

Recommended next task:

```text
RAZ-AW-S3D1_EnrichedBuilderImplementation
```

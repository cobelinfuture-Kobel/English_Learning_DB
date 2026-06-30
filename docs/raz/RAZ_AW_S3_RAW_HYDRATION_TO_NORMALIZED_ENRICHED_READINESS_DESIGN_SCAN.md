# RAZ-AW-S3 Raw Hydration To Normalized / Enriched Readiness Design Scan

## 1. Preflight

Task:

```text
RAZ-AW-S3_RawHydrationToNormalizedEnrichedReadinessDesignScan
```

Scope:

```text
DESIGN SCAN ONLY
READBACK OF SANITIZED S2 REPORTS ONLY
NO RAW RAZ JSON MUTATION
NO RAW RAZ JSON COMMIT
NO FULL RAW TEXT IN REPORTS
NO NORMALIZED BUILD IMPLEMENTATION
NO ENRICHED BUILD IMPLEMENTATION
NO CONTENT AUTHORITY PROMOTION
NO TAG AUTHORITY PROMOTION
NO GRAMMAR / VOCABULARY / PATTERN AUTHORITY LINKAGE IMPLEMENTATION
NO READING / DIALOGUE / EXERCISE GENERATION
NO RUNTIME / API / SCHEDULER / DASHBOARD CHANGE
```

Repository:

```text
cobelinfuture-Kobel/English_Learning_DB
branch: main
```

Upstream closeout:

```text
RAZ-AW-S2G_FullAWHydrationReadbackCloseout: PASS
```

S2G result used by this scan:

```text
A-W raw JSON hydration/readback safety is closed as PASS.
The raw layer is safe for downstream normalized/enriched readiness design and QA.
The raw layer remains candidate_only and must not be treated as final content authority.
```

Files created by this task:

```text
docs/raz/RAZ_AW_S3_RAW_HYDRATION_TO_NORMALIZED_ENRICHED_READINESS_DESIGN_SCAN.md
reports/raz/raw_hydration_to_normalized_enriched_readiness_design_scan.json
```

Risk level:

```text
Low
```

Reason:

```text
This task defines contracts and sequencing only. It does not execute normalized/enriched builders and does not read raw payload text.
```

---

## 2. Current Source State

S2 closed the raw hydration/readback safety layer with the following effective facts:

```text
raw_level_file_count: 1959
levels_present: A-W
levels_missing: []
json_parse_status_counts: PASS=1959
level_json_mismatch_count: 0
book_id_mismatch_count: 0
generated_content_true_count: 0
ignored_json_file_count: 0
warnings: []
blockers: []
```

S2 aggregate source consistency:

```text
authority_status_counts:
  candidate_only: 1959

source_type_counts:
  raz_audio_timeline: 1959

extraction_method_counts:
  bookAudioContent: 1959

extractor_version_counts:
  raz_audio_timeline_to_content_authority_v3_story_filter: 1959
```

Interpretation:

```text
The raw layer is stable enough to become source evidence for normalized / enriched work.
It is not authoritative content yet.
```

---

## 3. S3 Objective

S3 must answer these questions before any builder implementation:

```text
1. Which raw fields are allowed to enter normalized output?
2. Which raw fields are evidence-only and must not become learner-facing content directly?
3. Which raw fields must be excluded or quarantined?
4. What normalized item shapes are required?
5. What enriched item shapes are required?
6. Which validators must block raw leakage, authority overreach, and schema drift?
7. Which later tasks can safely promote content or tags?
```

S3 is therefore a design/contract stage between:

```text
S2 raw hydration/readback safety
        ↓
S3 normalized/enriched readiness contracts
        ↓
S4+ normalized/enriched implementation and validation
```

---

## 4. Proposed Layer Separation

### 4.1 Raw Evidence Layer

Purpose:

```text
Preserve source-derived RAZ extraction objects externally or in uncommitted raw storage.
Serve as evidence for deterministic normalized builders.
```

Allowed status:

```text
authority_status: candidate_only
generated_content: false
raw_commit_allowed: false
```

Not allowed:

```text
Direct learner-facing output
Content authority approval
Tag authority approval
Grammar/vocabulary/pattern linkage approval
```

### 4.2 Normalized Layer

Purpose:

```text
Create stable, deterministic, schema-controlled records from raw evidence.
Represent sentence units, page units, reuse units, and source references in a queryable form.
```

Allowed status after implementation:

```text
normalized_status: candidate_normalized
content_authority_status: not_promoted
review_status: pending
```

Not allowed:

```text
Final content authority
Generated lessons
Generated exercises
Formal grammar / vocabulary / pattern authority linkage
```

### 4.3 Enriched Layer

Purpose:

```text
Add derived metadata, query facets, candidate tags, linkage candidates, and validation signals.
```

Allowed status after implementation:

```text
enrichment_status: candidate_enriched
candidate_tag_status: pending
authority_linkage_status: candidate_only
```

Not allowed:

```text
Automatic tag promotion
Automatic authority linkage promotion
Automatic learner-facing generation
```

---

## 5. Raw Field Classification

### 5.1 Allowed metadata fields

These may flow into normalized records if sanitized and schema-validated:

```text
source_type
extraction_method
extractor_version
book_metadata.level
book_metadata.book_id
book_metadata.title
book_metadata.story_page_start
book_metadata.story_page_end
book_metadata.story_page_count
book_metadata.allowed_text_types
book_metadata.min_story_page_number
clean_summary.authority_status
clean_summary.generated_content
clean_summary.raw_audio_fields_preserved
clean_summary.final_should_remove_audio_fields
```

Rationale:

```text
These fields identify source, extraction version, level/book identity, and provenance state.
They do not by themselves expose full raw text payloads.
```

### 5.2 Allowed derived counts

These may be used in reports and validators:

```text
sentence_candidate_count
page_unit_count
reuse_candidate_count
excluded_item_count
legacy_story_sentence_count
size_bytes
json_parse_status
```

Rationale:

```text
These are structural QA fields and do not expose raw content.
```

### 5.3 Candidate normalized content fields

These may enter normalized records only after explicit schema and leakage validation:

```text
normalized_sentence.text
normalized_sentence.unit_id
normalized_sentence.page_number
normalized_sentence.source_span_ref
normalized_page_unit.unit_id
normalized_page_unit.page_number
normalized_page_unit.sentence_ids
normalized_reuse_unit.unit_id
normalized_reuse_unit.page_range
normalized_reuse_unit.sentence_ids
```

Constraints:

```text
Text must be normalized text, not full raw extraction payload.
Each text item must be source-referenced.
Every learner-facing candidate must remain candidate_only until later authority review.
```

### 5.4 Evidence-only raw structures

These must not be copied wholesale into normalized or enriched GitHub reports:

```text
sentence_candidates
page_units
reuse_unit_candidates
legacy_story_sentences
excluded_items
word trace structures
audio trace structures
raw page image references
full raw audio timeline payloads
```

Allowed usage:

```text
Builder input only, from local/raw storage.
Small scalar metadata and deterministic counts may be emitted.
Full payloads must not be emitted to sanitized reports.
```

### 5.5 Forbidden final-output structures

These must not appear in final normalized/enriched public reports or learner-facing artifacts:

```text
raw audio traces
word-level timing traces
raw page image payloads
unfiltered text-layer artifacts
abnormal OCR/text-layer noise
internal debug dumps
full raw JSON objects
```

---

## 6. Proposed Normalized Schemas

### 6.1 `raz_normalized_books.json`

One record per RAZ book.

Minimum shape:

```json
{
  "book_uid": "raz_A_6",
  "source": "RAZ",
  "level": "A",
  "book_id": "6",
  "title": "I Can",
  "source_type": "raz_audio_timeline",
  "extraction_method": "bookAudioContent",
  "extractor_version": "raz_audio_timeline_to_content_authority_v3_story_filter",
  "story_page_start": 3,
  "story_page_end": 10,
  "story_page_count": 8,
  "authority_status": "candidate_only",
  "normalization_status": "candidate_normalized",
  "review_status": "pending"
}
```

### 6.2 `raz_normalized_sentences.json`

One record per normalized sentence candidate.

Minimum shape:

```json
{
  "sentence_uid": "raz_A_6_s0001",
  "book_uid": "raz_A_6",
  "level": "A",
  "book_id": "6",
  "page_number": 3,
  "sentence_index_in_book": 1,
  "text": "...",
  "source_ref": {
    "source_layer": "raw_sentence_candidate",
    "raw_file_relative_path": "raz_output_jsons/Level_A/raz_A_6_audio_timeline_extract.json",
    "raw_candidate_ref": "opaque_or_index_ref"
  },
  "authority_status": "candidate_only",
  "normalization_status": "candidate_normalized",
  "review_status": "pending"
}
```

### 6.3 `raz_normalized_page_units.json`

One record per page-level reading unit.

Minimum shape:

```json
{
  "page_unit_uid": "raz_A_6_p0003",
  "book_uid": "raz_A_6",
  "level": "A",
  "book_id": "6",
  "page_number": 3,
  "sentence_uids": [
    "raz_A_6_s0001"
  ],
  "source_ref": {
    "source_layer": "raw_page_unit",
    "raw_file_relative_path": "raz_output_jsons/Level_A/raz_A_6_audio_timeline_extract.json",
    "raw_page_ref": "opaque_or_index_ref"
  },
  "authority_status": "candidate_only",
  "normalization_status": "candidate_normalized",
  "review_status": "pending"
}
```

### 6.4 `raz_normalized_reuse_units.json`

One record per cross-page or reuse-capable reading unit.

Minimum shape:

```json
{
  "reuse_unit_uid": "raz_U_3975_r0001",
  "book_uid": "raz_U_3975",
  "level": "U",
  "book_id": "3975",
  "page_range": [4, 5],
  "sentence_uids": [
    "raz_U_3975_s0001",
    "raz_U_3975_s0002"
  ],
  "reuse_candidate_type": "reading_unit_candidate",
  "authority_status": "candidate_only",
  "normalization_status": "candidate_normalized",
  "review_status": "pending"
}
```

---

## 7. Proposed Enriched Schemas

### 7.1 `raz_enriched_books.json`

Adds query and curriculum-facing metadata to normalized books.

Candidate fields:

```text
book_uid
level
book_id
title
sentence_count
page_unit_count
reuse_unit_count
estimated_text_complexity_bucket
candidate_theme_tags
candidate_content_unit_tags
candidate_pedagogical_tags
authority_linkage_status
validation_status
```

### 7.2 `raz_enriched_sentences.json`

Adds query facets and candidate learning signals to normalized sentences.

Candidate fields:

```text
sentence_uid
book_uid
level
text
normalized_token_count
candidate_vocab_refs
candidate_grammar_refs
candidate_pattern_refs
sentence_length_bucket
punctuation_profile
dialogue_candidate_flag
reading_sentence_candidate_flag
review_status
```

Important constraint:

```text
candidate_vocab_refs / candidate_grammar_refs / candidate_pattern_refs must remain candidate_only until cross-source authority validators approve them.
```

### 7.3 `raz_enriched_units.json`

Adds reusable reading/dialogue unit metadata.

Candidate fields:

```text
unit_uid
unit_type
book_uid
level
sentence_uids
unit_sentence_count
unit_token_count
candidate_use_cases
candidate_reuse_tags
reading_usefulness_score_candidate
dialogue_usefulness_score_candidate
exercise_usefulness_score_candidate
review_status
```

---

## 8. Required Validators Before Implementation

### 8.1 Raw leakage validator

Blocks these keys from emitted reports and enriched public artifacts:

```text
sentence_candidates
page_units
reuse_unit_candidates
legacy_story_sentences
audio_trace
word_trace
raw_text
page_text
```

### 8.2 Stable ID validator

Validates deterministic IDs:

```text
book_uid pattern: raz_<LEVEL>_<BOOK_ID>
sentence_uid pattern: raz_<LEVEL>_<BOOK_ID>_sNNNN
page_unit_uid pattern: raz_<LEVEL>_<BOOK_ID>_pNNNN
reuse_unit_uid pattern: raz_<LEVEL>_<BOOK_ID>_rNNNN
```

### 8.3 Source ref validator

Every normalized content item must include:

```text
raw_file_relative_path
source_layer
raw_candidate_ref or deterministic index ref
```

### 8.4 Candidate-only validator

Blocks accidental promotion:

```text
content_authority_status must not be approved
tag_authority_status must not be approved
grammar/vocab/pattern authority linkage must not be approved
review_status must remain pending unless a later review gate updates it
```

### 8.5 Text normalization validator

Checks normalized text only:

```text
not empty
valid Unicode
no replacement character U+FFFD
no abnormal symbol density
no raw timing tokens
no raw markup artifacts
sentence boundary sanity
```

### 8.6 Count reconciliation validator

Compares normalized output to raw shallow counts:

```text
book count = 1959
level counts match S2F file_count_by_level
sentence counts reconcile to raw sentence_candidate_count unless explicitly excluded with reason
page unit counts reconcile to raw page_unit_count unless explicitly excluded with reason
reuse unit counts reconcile to raw reuse_candidate_count unless explicitly excluded with reason
```

---

## 9. Proposed S3+ Task Sequence

### S3A — Normalized / Enriched Schema Contract Design

Output:

```text
docs/raz/RAZ_AW_S3A_NORMALIZED_ENRICHED_SCHEMA_CONTRACT.md
schemas/raz/raz_normalized_books.schema.json
schemas/raz/raz_normalized_sentences.schema.json
schemas/raz/raz_normalized_page_units.schema.json
schemas/raz/raz_normalized_reuse_units.schema.json
schemas/raz/raz_enriched_books.schema.json
schemas/raz/raz_enriched_sentences.schema.json
schemas/raz/raz_enriched_units.schema.json
```

No builder yet.

### S3B — Normalized Builder Implementation

Output:

```text
tools/raz_aw_build_normalized_from_raw.py
reports/raz/raz_aw_normalized_build_summary.json
raz_output_jsons/derived/A-W/normalized or ulga/graph/raz_normalized/*.json depending final storage decision
```

Requires decision on derived storage surface before implementation.

### S3C — Normalized Validator QA

Output:

```text
tools/raz_aw_validate_normalized.py
reports/raz/raz_aw_normalized_validation_report.json
reports/raz/raz_aw_normalized_safety_report.json
```

### S3D — Enriched Builder Design / Implementation

Output:

```text
tools/raz_aw_build_enriched_from_normalized.py
reports/raz/raz_aw_enriched_build_summary.json
```

### S3E — Authority Linkage Candidate Layer

Output:

```text
candidate grammar/vocab/pattern linkage reports only
no promotion
```

### S3F — Normalized / Enriched Readback Closeout

Output:

```text
closeout stating whether normalized/enriched candidate layer is ready for later authority promotion scans
```

---

## 10. Storage Surface Decision Needed

Before S3B implementation, decide one of these:

### Option A — Keep derived under raw mirror

```text
raz_output_jsons/derived/Level_A/normalized/*.json
raz_output_jsons/derived/Level_A/enriched/*.json
```

Pros:

```text
Keeps derived artifacts close to raw evidence.
Avoids large GitHub data commits.
```

Cons:

```text
Harder to inspect in GitHub unless summarized reports are committed.
```

### Option B — Commit sanitized graph outputs to GitHub

```text
ulga/graph/raz_normalized_books.json
ulga/graph/raz_normalized_sentences.json
ulga/graph/raz_enriched_units.json
```

Pros:

```text
Queryable and versioned in GitHub.
Useful for downstream tooling.
```

Cons:

```text
Potentially large files.
Must prove no copyrighted/raw text overexposure policy issue before committing sentence text.
```

### Recommended for next implementation

```text
Use Option A for full derived text-bearing artifacts.
Commit only sanitized summaries, schemas, validators, and aggregate reports to GitHub.
```

Reason:

```text
Normalized sentence text is still content-bearing. It should not be broadly committed until content authority and copyright/scope policy are reviewed.
```

---

## 11. S3 Readiness Verdict

```text
RAZ-AW-S3_RawHydrationToNormalizedEnrichedReadinessDesignScan: PASS
```

Readiness decision:

```text
S3A normalized/enriched schema contract design: READY
S3B normalized builder implementation: NOT YET
S3C validator QA: NOT YET
S3D enriched builder: NOT YET
Authority promotion: NOT YET
Generation: NOT YET
Runtime/API integration: NOT YET
```

Next recommended task:

```text
RAZ-AW-S3A_NormalizedEnrichedSchemaContractDesign
```

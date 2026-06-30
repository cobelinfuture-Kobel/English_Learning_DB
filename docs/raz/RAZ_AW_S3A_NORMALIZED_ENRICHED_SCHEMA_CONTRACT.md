# RAZ-AW-S3A Normalized / Enriched Schema Contract

## 1. Preflight

Task:

```text
RAZ-AW-S3A_NormalizedEnrichedSchemaContractDesign
```

Scope:

```text
SCHEMA CONTRACT DESIGN ONLY
JSON SCHEMA ARTIFACTS ONLY
NO RAW RAZ JSON READ
NO RAW RAZ JSON MUTATION
NO RAW RAZ JSON COMMIT
NO FULL RAW TEXT IN REPORTS
NO NORMALIZED BUILD EXECUTION
NO ENRICHED BUILD EXECUTION
NO CONTENT AUTHORITY PROMOTION
NO TAG AUTHORITY PROMOTION
NO GRAMMAR / VOCABULARY / PATTERN AUTHORITY LINKAGE APPROVAL
NO READING / DIALOGUE / EXERCISE GENERATION
NO RUNTIME / API / SCHEDULER / DASHBOARD CHANGE
```

Repository:

```text
cobelinfuture-Kobel/English_Learning_DB
branch: main
```

Upstream dependency:

```text
RAZ-AW-S3_RawHydrationToNormalizedEnrichedReadinessDesignScan: PASS
```

Files created by this task:

```text
docs/raz/RAZ_AW_S3A_NORMALIZED_ENRICHED_SCHEMA_CONTRACT.md
schemas/raz/raz_normalized_books.schema.json
schemas/raz/raz_normalized_sentences.schema.json
schemas/raz/raz_normalized_page_units.schema.json
schemas/raz/raz_normalized_reuse_units.schema.json
schemas/raz/raz_enriched_books.schema.json
schemas/raz/raz_enriched_sentences.schema.json
schemas/raz/raz_enriched_units.schema.json
reports/raz/normalized_enriched_schema_contract_status.json
```

Risk level:

```text
Low
```

Reason:

```text
This task creates schemas and a contract document only. It does not build derived records and does not read raw payload text.
```

---

## 2. Contract Purpose

S3A converts the S3 readiness scan into concrete JSON Schema contracts for later builders and validators.

The schemas define two candidate layers:

```text
1. Normalized candidate layer
2. Enriched candidate layer
```

They deliberately do not approve:

```text
Content authority promotion
Tag authority promotion
Grammar / vocabulary / pattern authority linkage approval
Learner-facing generation
Runtime/API integration
```

---

## 3. Schema Inventory

### Normalized schemas

```text
schemas/raz/raz_normalized_books.schema.json
schemas/raz/raz_normalized_sentences.schema.json
schemas/raz/raz_normalized_page_units.schema.json
schemas/raz/raz_normalized_reuse_units.schema.json
```

Purpose:

```text
Represent deterministic source-derived book, sentence, page-unit, and reuse-unit records.
Every content-bearing candidate remains candidate_only / candidate_normalized / pending.
```

### Enriched schemas

```text
schemas/raz/raz_enriched_books.schema.json
schemas/raz/raz_enriched_sentences.schema.json
schemas/raz/raz_enriched_units.schema.json
```

Purpose:

```text
Represent query facets, candidate learning signals, candidate tags, and candidate linkage refs derived from normalized records.
Every linkage remains candidate_only until a later cross-source authority validator approves it.
```

---

## 4. Shared Status Contract

Allowed candidate statuses:

```text
authority_status: candidate_only
normalization_status: candidate_normalized
enrichment_status: candidate_enriched
review_status: pending | needs_review | rejected
content_authority_status: not_promoted
tag_authority_status: not_promoted
authority_linkage_status: candidate_only | not_evaluated
```

Blocked statuses in S3A/S3B/S3C/S3D:

```text
approved
promoted
final_authority
learner_facing_approved
```

Meaning:

```text
S3A schemas intentionally keep records usable for downstream QA and querying, but not usable as final content authority.
```

---

## 5. Required Source Reference Contract

Every normalized content-bearing record must include a `source_ref` object with:

```text
raw_file_relative_path
source_layer
raw_candidate_ref or deterministic_index_ref
```

Allowed `source_layer` examples:

```text
raw_book_metadata
raw_sentence_candidate
raw_page_unit
raw_reuse_unit_candidate
```

Purpose:

```text
A downstream validator must be able to trace every normalized item back to a raw evidence source without copying full raw payloads into GitHub reports.
```

---

## 6. Raw Leakage Boundary

The schemas do not allow wholesale raw structures such as:

```text
sentence_candidates
page_units
reuse_unit_candidates
legacy_story_sentences
audio_trace
word_trace
raw_text
page_text
full_raw_json
```

Later validators must also scan generated reports and derived artifacts for these keys.

---

## 7. Storage Boundary

Recommended storage policy for S3B/S3D implementation:

```text
Full text-bearing derived artifacts: keep under raw mirror / Drive derived surface.
GitHub: commit schemas, validators, sanitized summaries, and aggregate reports only.
```

Reason:

```text
Normalized sentence text is content-bearing. It should not be committed broadly before content authority and copyright/scope policy review.
```

---

## 8. Implementation Gate

S3A creates schema contracts only. Before S3B implementation, the next task must confirm:

```text
1. exact derived storage path
2. whether full normalized sentence text stays local/Drive-only
3. validator order
4. summary-only GitHub commit policy
5. count reconciliation source from S2F summaries
```

---

## 9. S3A Verdict

```text
RAZ-AW-S3A_NormalizedEnrichedSchemaContractDesign: PASS
```

Readiness decision:

```text
S3B normalized builder implementation: READY_WITH_STORAGE_DECISION_REQUIRED
S3C validator QA: NOT YET
S3D enriched builder: NOT YET
Authority promotion: NOT YET
Generation: NOT YET
Runtime/API integration: NOT YET
```

Recommended next task:

```text
RAZ-AW-S3B_NormalizedBuilderStorageDecisionAndImplementationPlan
```

# RAZ-AW-S3B Normalized Builder Storage Decision And Implementation Plan

## 1. Preflight

Task:

```text
RAZ-AW-S3B_NormalizedBuilderStorageDecisionAndImplementationPlan
```

Scope:

```text
STORAGE DECISION AND IMPLEMENTATION PLAN ONLY
NO RAW RAZ JSON READ
NO RAW RAZ JSON MUTATION
NO RAW RAZ JSON COMMIT
NO FULL RAW TEXT IN GITHUB REPORTS
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

Upstream dependencies:

```text
RAZ-AW-S2G_FullAWHydrationReadbackCloseout: PASS
RAZ-AW-S3_RawHydrationToNormalizedEnrichedReadinessDesignScan: PASS
RAZ-AW-S3A_NormalizedEnrichedSchemaContractDesign: PASS
```

Files created by this task:

```text
docs/raz/RAZ_AW_S3B_NORMALIZED_BUILDER_STORAGE_DECISION_AND_IMPLEMENTATION_PLAN.md
reports/raz/normalized_builder_storage_decision_and_implementation_plan.json
```

Risk level:

```text
Low
```

Reason:

```text
This task fixes storage and implementation contracts only. It does not run the builder and does not emit normalized sentence text.
```

---

## 2. Storage Decision

Decision:

```text
Full text-bearing normalized artifacts stay under the raw mirror / Drive-derived surface.
GitHub receives only schemas, validators, sanitized summaries, aggregate QA reports, and implementation docs.
```

Selected local/Drive-derived output root:

```text
G:\HomeWork\English_Learning_DB\raz_output_jsons\derived
```

Selected per-level normalized output pattern:

```text
raz_output_jsons/derived/Level_<LEVEL>/normalized/raz_<LEVEL>_normalized_books.json
raz_output_jsons/derived/Level_<LEVEL>/normalized/raz_<LEVEL>_normalized_sentences.json
raz_output_jsons/derived/Level_<LEVEL>/normalized/raz_<LEVEL>_normalized_page_units.json
raz_output_jsons/derived/Level_<LEVEL>/normalized/raz_<LEVEL>_normalized_reuse_units.json
```

Selected cross-level manifest / summaries under derived surface:

```text
raz_output_jsons/derived/reports/raz_aw_normalized_local_manifest.json
raz_output_jsons/derived/reports/raz_aw_normalized_count_reconciliation.json
```

GitHub-committed summaries only:

```text
reports/raz/raz_aw_normalized_build_summary.json
reports/raz/raz_aw_normalized_safety_report.json
reports/raz/raz_aw_normalized_count_reconciliation_summary.json
```

GitHub forbidden for S3B/S3C:

```text
Full normalized sentence corpus
Full normalized page-unit corpus with text-bearing payloads
Full normalized reuse-unit corpus with text-bearing payloads
Raw sentence_candidates / page_units / reuse_unit_candidates payloads
Raw audio or word trace payloads
```

---

## 3. Builder Input / Output Contract

Planned builder:

```text
tools/raz_aw_build_normalized_from_raw.py
```

Planned local command:

```powershell
cd G:\HomeWork\English_Learning_DB
python tools\raz_aw_build_normalized_from_raw.py --raw-root G:\HomeWork\English_Learning_DB\raz_output_jsons --derived-root G:\HomeWork\English_Learning_DB\raz_output_jsons\derived
```

Builder inputs:

```text
raz_output_jsons/Level_A ... Level_W/*.json
schemas/raz/raz_normalized_books.schema.json
schemas/raz/raz_normalized_sentences.schema.json
schemas/raz/raz_normalized_page_units.schema.json
schemas/raz/raz_normalized_reuse_units.schema.json
reports/raz/local_hydration_full_aw_qa_summary.json
```

Builder full derived outputs, not committed to GitHub:

```text
raz_output_jsons/derived/Level_A/normalized/*.json
...
raz_output_jsons/derived/Level_W/normalized/*.json
```

Builder sanitized GitHub outputs:

```text
reports/raz/raz_aw_normalized_build_summary.json
reports/raz/raz_aw_normalized_safety_report.json
reports/raz/raz_aw_normalized_count_reconciliation_summary.json
```

---

## 4. Normalized Record Generation Rules

### 4.1 Book records

Generate one normalized book record per raw RAZ file.

Required invariants:

```text
book_uid = raz_<LEVEL>_<BOOK_ID>
source = RAZ
authority_status = candidate_only
normalization_status = candidate_normalized
content_authority_status = not_promoted
review_status = pending
source_ref.source_layer = raw_book_metadata
```

Expected count:

```text
1959 normalized book records
```

### 4.2 Sentence records

Generate one normalized sentence record per accepted raw sentence candidate unless excluded by deterministic filter.

Required invariants:

```text
sentence_uid = raz_<LEVEL>_<BOOK_ID>_sNNNN
book_uid = raz_<LEVEL>_<BOOK_ID>
text = normalized text only
authority_status = candidate_only
normalization_status = candidate_normalized
content_authority_status = not_promoted
review_status = pending
source_ref.source_layer = raw_sentence_candidate
```

Allowed exclusions:

```text
empty text
abnormal text-layer artifact
replacement character U+FFFD
raw timing token leakage
raw markup artifact
non-story candidate if extractor marks it excluded
```

Each exclusion must be counted and summarized without emitting raw text.

### 4.3 Page-unit records

Generate one normalized page-unit record per accepted raw page unit.

Required invariants:

```text
page_unit_uid = raz_<LEVEL>_<BOOK_ID>_pNNNN
sentence_uids references must exist in normalized sentences
source_ref.source_layer = raw_page_unit
authority_status = candidate_only
normalization_status = candidate_normalized
content_authority_status = not_promoted
review_status = pending
```

### 4.4 Reuse-unit records

Generate one normalized reuse-unit record per accepted raw reuse candidate.

Required invariants:

```text
reuse_unit_uid = raz_<LEVEL>_<BOOK_ID>_rNNNN
sentence_uids references must exist in normalized sentences
source_ref.source_layer = raw_reuse_unit_candidate
authority_status = candidate_only
normalization_status = candidate_normalized
content_authority_status = not_promoted
review_status = pending
```

---

## 5. Validator Order For S3C

S3C validators must run in this order:

```text
1. schema validation
2. raw leakage validation
3. stable ID validation
4. source ref validation
5. candidate-only / no-promotion validation
6. text normalization validation
7. internal reference validation
8. count reconciliation validation
9. GitHub output safety validation
```

Required blocking checks:

```text
No raw payload keys in GitHub reports
No raw audio trace / word trace / full raw JSON emission
No approved/promoted/final_authority status
No learner_facing_approved status
Every normalized sentence has source_ref
Every page/reuse sentence_uid reference resolves
Counts reconcile to S2F summaries or have explicit exclusion reason counts
```

---

## 6. GitHub Commit Policy For S3B/S3C

Allowed to commit:

```text
tools/raz_aw_build_normalized_from_raw.py
tools/raz_aw_validate_normalized.py
reports/raz/raz_aw_normalized_build_summary.json
reports/raz/raz_aw_normalized_safety_report.json
reports/raz/raz_aw_normalized_count_reconciliation_summary.json
docs/raz/*normalized*implementation*.md
docs/raz/*normalized*qa*.md
```

Not allowed to commit:

```text
raz_output_jsons/derived/Level_*/normalized/*.json
raw RAZ files
full normalized sentence corpus
full text-bearing derived corpora
scratch data dumps
```

Required operator command pattern after local run:

```powershell
git add tools\raz_aw_build_normalized_from_raw.py `
        tools\raz_aw_validate_normalized.py `
        reports\raz\raz_aw_normalized_build_summary.json `
        reports\raz\raz_aw_normalized_safety_report.json `
        reports\raz\raz_aw_normalized_count_reconciliation_summary.json
```

Do not run:

```powershell
git add .
```

---

## 7. Implementation Plan

### S3C1 — Normalized Builder Implementation

Implement:

```text
tools/raz_aw_build_normalized_from_raw.py
```

Responsibilities:

```text
read local raw files from raz_output_jsons/Level_A ... Level_W
emit full normalized artifacts to raz_output_jsons/derived/Level_<LEVEL>/normalized
emit sanitized summaries to reports/raz
preserve candidate_only / not_promoted statuses
avoid raw leakage in GitHub reports
```

### S3C2 — Normalized Validator QA

Implement:

```text
tools/raz_aw_validate_normalized.py
```

Responsibilities:

```text
validate normalized derived files against schemas
validate raw leakage boundary
validate source refs
validate stable IDs
validate candidate-only statuses
validate count reconciliation
emit sanitized QA reports only
```

### S3C3 — Local Build Run And Report Commit

Run builder and validator locally.

Commit only:

```text
sanitized summaries
safety reports
validator reports
implementation / QA docs
```

### S3C4 — Normalized Candidate Layer Closeout

Close out whether normalized candidate layer is ready for enriched builder design.

---

## 8. Open Decisions Closed By S3B

```text
exact derived storage path: CLOSED
full normalized sentence text stays local/Drive-only: CLOSED
validator order: CLOSED
summary-only GitHub commit policy: CLOSED
count reconciliation source from S2F summaries: CLOSED
```

---

## 9. S3B Verdict

```text
RAZ-AW-S3B_NormalizedBuilderStorageDecisionAndImplementationPlan: PASS
```

Readiness decision:

```text
S3C1 normalized builder implementation: READY
S3C2 normalized validator QA: READY_AFTER_BUILDER
S3D enriched builder: NOT YET
Authority promotion: NOT YET
Generation: NOT YET
Runtime/API integration: NOT YET
```

Recommended next task:

```text
RAZ-AW-S3C1_NormalizedBuilderImplementation
```

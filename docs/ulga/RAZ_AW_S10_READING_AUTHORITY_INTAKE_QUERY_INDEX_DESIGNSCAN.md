# RAZ-AW-S10 Reading Authority Intake Query Index DesignScan

## 1. Task

`RAZ-AW-S10_ReadingAuthorityIntake_QueryIndexDesignScan`

## 2. Preflight

This DesignScan was produced as a GitHub evidence-based design task.

Local-only execution checks such as:

```powershell
git status -sb
pytest
validator execution
streaming reads of ulga/graph/raz_reading_authority_intake_candidates.json
```

are intentionally deferred to the next local/Codex implementation stage.

S10 does not require loading the full local candidate artifact. The S10 prompt explicitly defines this as a DesignScan-only task and forbids implementing a query-index builder, creating query-index JSON/JSONL output, creating `reading_authority.json`, performing promotion, expanding query-layer approved levels, or committing the 619 MB candidate artifact.

## 3. Files Inspected

GitHub evidence inspected:

```text
docs/ulga/RAZ_AW_S10_READING_AUTHORITY_INTAKE_QUERY_INDEX_DESIGNSCAN_PROMPT.md
docs/ulga/RAZ_AW_S9_READING_AUTHORITY_INTAKE_BUILDER_QA_ARTIFACT_EXTERNALIZATION_AND_WARNING_TAXONOMY.md
docs/ulga/RAZ_AW_S9_READING_AUTHORITY_INTAKE_BUILDER_QA_ARTIFACT_EXTERNALIZATION_AND_WARNING_TAXONOMY_PROMPT.md
```

S10 implementation should additionally inspect locally in the next task:

```text
docs/ulga/RAZ_AW_S8_READING_AUTHORITY_INTAKE_BUILDER_IMPLEMENTATION.md
ulga/schemas/raz_reading_authority_intake.schema.json
ulga/builders/build_raz_reading_authority_intake.py
ulga/validators/validate_raz_reading_authority_intake_schema.py
ulga/validators/validate_raz_reading_authority_intake_artifact_policy.py
ulga/reports/raz_reading_authority_intake_builder_summary.json
ulga/reports/raz_reading_authority_intake_builder_validation.json
ulga/reports/raz_reading_authority_intake_artifact_manifest.json
ulga/reports/raz_reading_authority_intake_warning_taxonomy.json
ulga/reports/raz_reading_authority_intake_builder_qa_summary.json
ulga/reports/raz_reading_authority_intake_builder_qa_validation.json
ulga/graph/raz_level_discovery_inventory.json
.gitignore
```

## 4. Current State Summary from S8/S9

S8 produced the candidate-intake layer:

```text
total_records = 243957
sentence = 201993
page_unit = 22632
reuse_unit = 19332
```

S9 formalized the artifact policy:

```text
artifact_status = LOCAL_ONLY
git_policy = do_not_commit
gitignore_status = PASS
artifact_committed_to_git = false
external_storage_status = PENDING_OPERATOR_UPLOAD
record_count = 243957
content_hash_sha256 = 96040b787816dd1ef193c680cefb4c350a08d6e78f8619759f8716a71a4e0fc6
```

S9 also reconciled warnings:

```text
source_warning_count = 1646931
semantic_warning_count = 1646921
unique_qa_warning_family_count = 10
recomputed_source_warning_count = 1646931
warning_count_reconciliation_status = PASS
blocking_warning_count = 0
promotion_blocking_status = PROMOTION_STILL_BLOCKED
```

Primary warning categories:

```text
MISSING_CEFR_ESTIMATE = 243957
SPARSE_PEDAGOGICAL_TAGS = 901201
LEGACY_TAG_COMPATIBILITY_MAPPED = 43959
UNSUPPORTED_LEGACY_REUSABILITY_TAG = 24055
QUERY_LAYER_NOT_READY_G_TO_W = 229535
S6B_PARITY_NOTE_INHERITED = 14572
MISSING_BOOK_TITLE = 215492
SENTENCE_COUNT_HEURISTIC_MISMATCH = 42164
SOURCE_UNKNOWN_THEME = 3484
SOURCE_UNKNOWN_PATTERN = 1289
SOURCE_UNKNOWN_GRAMMAR = 932
SOURCE_SECTION_HEADING_DETECTED = 486
```

Guardrails remain:

```text
promotion_allowed = false
authority_status = candidate_only
final_eligible = false
query-layer expansion = not performed
runtime mutation = not performed
learner-state mutation = not performed
planner mutation = not performed
API/dashboard/scheduler mutation = not performed
source RAZ derived artifact mutation = not performed
```

## 5. Query Index Purpose and Non-goals

### Purpose

The query index is a compact read model over RAZ Reading Authority Intake candidates.

It should answer metadata-level retrieval questions without requiring users, validators, or later planners to repeatedly open the 619 MB full candidate payload.

It should support future queries such as:

```text
Which Level A sentence candidates exist?
Which Level C page_unit candidates contain multiple sentences?
Which reuse_unit candidates have short-reading or exercise reuse potential?
Which records are query-layer approved under the current A-F policy?
Which G-W records are present but staged-only?
Which records have missing CEFR estimates but otherwise valid traceability?
Which records need metadata enrichment before promotion review?
```

### Non-goals

S10 and the future query index are not:

```text
Reading Authority promotion
final reading_authority.json
learner-facing generated content
runtime query API
planner integration
learner-state mutation
query-layer approved-level expansion
source artifact mutation
```

The query index only makes candidates easier to inspect, filter, and stage for future review.

## 6. Query Dimensions

The first query-index contract should support these dimensions.

### Identity and source

```text
reading_intake_id
source
source_level
normalized_level
unit_type
schema_version
```

### Book and traceability

```text
book_id
book_title
page_number
page_unit_id
source_sentence_candidate_ids
source_artifact_path
source_record_id
derived_from_original_text
generated_content
traceability_complete
```

### Text metadata

```text
sentence_count
word_count
text_language
text_role
text_preview
```

The compact query index should not duplicate full `clean_text` by default. A short `text_preview` may be acceptable for human review, but it should be truncated and clearly non-authoritative.

### Pedagogical tags

```text
cefr_estimate
theme_tags
vocabulary_tags
grammar_tags
pattern_tags
skill_area
reusability_tags
```

### Query policy

```text
query_layer_ready
query_layer_approved
query_status
query_block_reason
```

### Authority state

```text
authority_status
candidate_only
promotion_allowed
promotion_status
final_eligible
```

### Warning flags

```text
warning_families
warning_count
has_blocking_warning
metadata_enrichment_needed
```

### Artifact pointer

```text
source_artifact
source_hash_sha256
source_artifact_status
source_shard
record_offset
record_line_number
```

`record_offset` should be optional until the implementation proves a stable byte-offset strategy. For JSON arrays, line-number indexing is not naturally stable unless the full payload format is changed to JSONL. Therefore, the first implementation should prefer generated shard paths and `reading_intake_id` lookup rather than relying on byte offsets inside the large JSON array.

## 7. A-F / G-W Query-layer Policy

The current policy must remain:

```text
A-F = query-layer ready / approved under current policy
G-W = present as staged candidates only, not query-layer approved
```

The query index may include G-W records, but their query state must be explicit:

```text
A-F: query_status = approved_candidate
G-W: query_status = staged_candidate_not_query_approved
```

G-W records may be searchable for inventory and QA, but they must not be returned by default for learner-facing query use.

Recommended default filter behavior:

```text
default_query_scope = A-F approved candidates only
include_staged = false by default
include_staged=true required to include G-W
```

This preserves visibility without silently expanding approved levels.

## 8. Storage Strategy Comparison

### Option A: Single compact index manifest

Pros:

```text
simple
Git-friendly if metadata-only
human-readable summary
```

Cons:

```text
may still become too large
poor query locality
hard to inspect by level/unit_type
```

Verdict: useful for summary, not sufficient as the only index.

### Option B: Level-sharded JSONL indexes

Example:

```text
ulga/graph/raz_reading_authority_intake_query_index/A.jsonl
ulga/graph/raz_reading_authority_intake_query_index/B.jsonl
...
ulga/graph/raz_reading_authority_intake_query_index/W.jsonl
```

Pros:

```text
small enough per level in most cases
streaming-friendly
simple deterministic rebuild
human inspectable
```

Cons:

```text
unit_type queries still require scanning a level shard
large upper levels may still be non-trivial
```

Verdict: acceptable, but not optimal.

### Option C: Level + unit_type sharded JSONL indexes

Example:

```text
ulga/graph/raz_reading_authority_intake_query_index/A/sentence.jsonl
ulga/graph/raz_reading_authority_intake_query_index/A/page_unit.jsonl
ulga/graph/raz_reading_authority_intake_query_index/A/reuse_unit.jsonl
...
ulga/graph/raz_reading_authority_intake_query_index/W/reuse_unit.jsonl
```

Pros:

```text
best query locality for current data model
stable deterministic rebuild
human-review friendly
supports A-F / G-W policy cleanly
keeps sentence/page/reuse concerns separated
works with streaming build from local large artifact
```

Cons:

```text
more files
requires manifest reconciliation
may still need Git-size gate per shard
```

Verdict: recommended default.

### Option D: SQLite local query cache

Pros:

```text
fast local query
supports indexes naturally
compact binary representation
```

Cons:

```text
binary artifact is less reviewable
less Git-friendly
harder to diff
requires local rebuild and validation discipline
```

Verdict: useful later as local cache, not first authority artifact.

### Option E: External artifact pointer + lightweight repo manifest only

Pros:

```text
minimal Git footprint
avoids large generated files
works with Google Drive/local storage
```

Cons:

```text
poor repo-level reviewability
requires local artifact access for almost every query
weak developer experience
```

Verdict: already used for full candidate payload; not sufficient for query layer.

### Option F: Hybrid compact index + local/Drive full payload

Pros:

```text
keeps Git safe
keeps common queries fast
preserves full payload externally
supports review and promotion staging
```

Cons:

```text
requires manifest and hash discipline
requires clear stale-index detection
```

Verdict: recommended overall architecture.

## 9. Recommended Storage / Index Strategy

Recommended S11/S10A strategy:

```text
Hybrid:
1. Keep full candidate payload LOCAL_ONLY or externalized.
2. Build metadata-only level + unit_type JSONL shards.
3. Commit only shards that pass per-file size gate.
4. Commit a compact manifest and summary/validation reports.
5. If any shard exceeds Git safety threshold, externalize that shard and commit only its manifest pointer.
```

Default layout proposal:

```text
ulga/graph/raz_reading_authority_intake_query_index_manifest.json
ulga/graph/raz_reading_authority_intake_query_index/A/sentence.jsonl
ulga/graph/raz_reading_authority_intake_query_index/A/page_unit.jsonl
ulga/graph/raz_reading_authority_intake_query_index/A/reuse_unit.jsonl
...
ulga/graph/raz_reading_authority_intake_query_index/W/sentence.jsonl
ulga/graph/raz_reading_authority_intake_query_index/W/page_unit.jsonl
ulga/graph/raz_reading_authority_intake_query_index/W/reuse_unit.jsonl
```

Manifest should include:

```json
{
  "task": "RAZ-AW-S11_ReadingAuthorityIntake_QueryIndexSchemaImplementation",
  "source_artifact": "ulga/graph/raz_reading_authority_intake_candidates.json",
  "source_artifact_policy": "LOCAL_ONLY",
  "source_hash_sha256": "96040b787816dd1ef193c680cefb4c350a08d6e78f8619759f8716a71a4e0fc6",
  "total_records_indexed": 243957,
  "levels": ["A", "B", "...", "W"],
  "unit_types": ["sentence", "page_unit", "reuse_unit"],
  "approved_query_levels": ["A", "B", "C", "D", "E", "F"],
  "staged_only_levels": ["G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W"],
  "shards": []
}
```

The query index should be metadata-only. It should not duplicate full source text.

## 10. Warning-aware Query Design

Warnings should become filterable metadata, not blockers.

Recommended model:

```json
{
  "warnings": {
    "families": ["MISSING_CEFR_ESTIMATE", "SPARSE_PEDAGOGICAL_TAGS"],
    "count": 2,
    "blocking": false,
    "metadata_enrichment_needed": true
  }
}
```

Handling by family:

| Warning family | Query behavior |
|---|---|
| `MISSING_CEFR_ESTIMATE` | Expose as `cefr_estimate=null`; allow filtering; do not block candidate visibility. |
| `SPARSE_PEDAGOGICAL_TAGS` | Expose sparse tag flags; useful for enrichment queue. |
| `QUERY_LAYER_NOT_READY_G_TO_W` | Set `query_status=staged_candidate_not_query_approved`; exclude from default learner-facing query scope. |
| `MISSING_BOOK_TITLE` | Preserve `book_id`; set `book_title=null`; route to metadata enrichment. |
| `LEGACY_TAG_COMPATIBILITY_MAPPED` | Preserve mapped value; expose compatibility flag. |
| `UNSUPPORTED_LEGACY_REUSABILITY_TAG` | Expose unsupported tag family; do not drop record. |
| `S6B_PARITY_NOTE_INHERITED` | Preserve as inherited upstream QA note. |
| `SENTENCE_COUNT_HEURISTIC_MISMATCH` | Flag as review-needed for text metadata; do not block. |
| `SOURCE_UNKNOWN_THEME` | Empty/unknown theme remains filterable; route to enrichment. |
| `SOURCE_UNKNOWN_PATTERN` | Empty/unknown pattern remains filterable; route to enrichment. |
| `SOURCE_UNKNOWN_GRAMMAR` | Empty/unknown grammar remains filterable; route to enrichment. |
| `SOURCE_SECTION_HEADING_DETECTED` | Mark as possible non-body text; include only when explicitly requested or during review. |

The index should support queries like:

```text
warning_family=MISSING_CEFR_ESTIMATE
metadata_enrichment_needed=true
query_status=approved_candidate
unit_type=page_unit
normalized_level=C
```

This lets S10/S11 serve both review workflows and eventual query workflows without promoting any records.

## 11. Proposed Future Schema / Builder / Validator / Tests

S10 does not create these files. It defines them for the next stage.

Recommended next implementation outputs:

```text
ulga/schemas/raz_reading_authority_intake_query_index.schema.json
ulga/builders/build_raz_reading_authority_intake_query_index.py
ulga/validators/validate_raz_reading_authority_intake_query_index.py
ulga/graph/raz_reading_authority_intake_query_index_manifest.json
ulga/graph/raz_reading_authority_intake_query_index/{level}/{unit_type}.jsonl
ulga/reports/raz_reading_authority_intake_query_index_summary.json
ulga/reports/raz_reading_authority_intake_query_index_validation.json
tests/ulga/test_raz_reading_authority_intake_query_index.py
docs/ulga/RAZ_AW_S11_READING_AUTHORITY_INTAKE_QUERY_INDEX_SCHEMA_IMPLEMENTATION.md
```

### Proposed compact query-record shape

```json
{
  "reading_intake_id": "RAZ_A_1001_SENT_000001",
  "schema_version": "raz_reading_authority_intake_query_index.v1",
  "source": "RAZ",
  "source_level": "A",
  "normalized_level": "A",
  "unit_type": "sentence",
  "query_status": "approved_candidate",
  "query_layer_ready": true,
  "query_layer_approved": true,
  "book": {
    "book_id": "1001",
    "book_title": null,
    "page_number": 1,
    "page_unit_id": "RAZ_A_1001_P001"
  },
  "text_meta": {
    "sentence_count": 1,
    "word_count": 4,
    "text_language": "en",
    "text_role": "reading_source_text",
    "text_preview": "I see a cat."
  },
  "tags": {
    "cefr_estimate": null,
    "theme_tags": [],
    "vocabulary_tags": [],
    "grammar_tags": [],
    "pattern_tags": [],
    "skill_area": [],
    "reusability_tags": []
  },
  "warnings": {
    "families": ["MISSING_CEFR_ESTIMATE"],
    "count": 1,
    "blocking": false,
    "metadata_enrichment_needed": true
  },
  "artifact_pointer": {
    "source_artifact": "ulga/graph/raz_reading_authority_intake_candidates.json",
    "source_artifact_status": "LOCAL_ONLY",
    "source_hash_sha256": "96040b787816dd1ef193c680cefb4c350a08d6e78f8619759f8716a71a4e0fc6",
    "shard": "A/sentence.jsonl",
    "record_offset": null,
    "source_record_id": "RAZ_A_1001_SENT_000001"
  },
  "authority": {
    "authority_status": "candidate_only",
    "candidate_only": true,
    "promotion_allowed": false,
    "promotion_status": "not_promoted",
    "final_eligible": false
  }
}
```

The first implementation should validate:

```text
all query index rows preserve candidate_only
all query index rows preserve promotion_allowed=false
A-F rows may be approved_candidate
G-W rows must be staged_candidate_not_query_approved
no row is final_eligible=true
all rows retain a source artifact pointer
manifest total counts reconcile to S8/S9
warning family counts reconcile to S9 taxonomy
no shard exceeds Git safety threshold unless externalized
```

## 12. Artifact-size and Git Policy

The full candidate artifact must remain:

```text
ulga/graph/raz_reading_authority_intake_candidates.json = LOCAL_ONLY / do_not_commit
```

The query index should follow a two-level size policy:

```text
1. Full source payload: always externalized / local-only.
2. Compact query shards: Git-track only if each shard remains below size threshold.
```

Recommended thresholds:

```text
soft_warning_threshold = 25 MB per shard
hard_externalize_threshold = 50 MB per shard
never_commit_threshold = 100 MB per file
```

If a compact shard exceeds the threshold, split further by:

```text
level / unit_type / book_id range
```

or externalize the shard and commit only its manifest pointer.

## 13. Guardrails

S10 and the next implementation must preserve:

```text
no reading_authority.json
no Reading Authority promotion
no promotion_allowed=true
no final_eligible=true
no authority_status other than candidate_only
no generated learner-facing content
no dialogue/writing/exercise rewrite
no query-layer approved-level expansion beyond A-F
no runtime mutation
no learner-state mutation
no planner mutation
no API/dashboard/scheduler mutation
no source RAZ derived artifact mutation
no commit of ulga/graph/raz_reading_authority_intake_candidates.json
```

## 14. Risks and Deferred Work

### Risk 1: Index staleness

The compact index can become stale relative to the local 619 MB candidate artifact.

Mitigation:

```text
manifest must store source_hash_sha256
builder must compare current local artifact hash before rebuild or validation
validation must fail if source_hash mismatch is detected
```

### Risk 2: Metadata-only index may be insufficient for human review

Human reviewers may want to see text quickly.

Mitigation:

```text
include short text_preview only
keep full clean_text in local/external source artifact
add lookup tooling later if needed
```

### Risk 3: Warning flags may be misused as blockers

Warnings are not blockers.

Mitigation:

```text
schema separates warnings.blocking=false from query_status
promotion decisions stay forbidden until a promotion-specific stage
```

### Risk 4: G-W accidentally becomes query-approved

Mitigation:

```text
validator must assert G-W query_status != approved_candidate
approved levels must be loaded from current policy, not inferred from indexed records
```

### Deferred work

```text
actual query-index schema implementation
streaming builder implementation
query-index validator
per-shard size gates
local artifact hash verification
Drive/external artifact upload pointer update
promotion review design
Reading Authority final schema
runtime query API integration
```

## 15. Final Verdict

```text
RAZ-AW-S10_ReadingAuthorityIntake_QueryIndexDesignScan = PASS
```

This is a GitHub evidence-based DesignScan. It does not claim local execution, local artifact streaming, pytest, validator execution, or staged-file verification.

## 16. Recommended Next Task

Recommended next task:

```text
RAZ-AW-S10A_ReadingAuthorityIntake_QueryIndexContractImplementation
```

Reason:

```text
S10A should implement only the schema/contract, validator skeleton, manifest contract, and small fixtures before building full 243,957-record query shards.
```

After S10A passes, proceed to:

```text
RAZ-AW-S11_ReadingAuthorityIntake_QueryIndexBuilderImplementation
```

S11 should run locally/Codex because it needs streaming access to the 619 MB local artifact and must run validators/tests.

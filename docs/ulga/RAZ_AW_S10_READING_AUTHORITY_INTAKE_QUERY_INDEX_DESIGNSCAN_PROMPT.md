# RAZ-AW-S10 Reading Authority Intake Query Index DesignScan Prompt

Use this prompt in Codex/local repo execution.

## 1. Task

`RAZ-AW-S10_ReadingAuthorityIntake_QueryIndexDesignScan`

## 2. Objective

Design the query-index layer for RAZ A-W Reading Authority Intake candidates after S8/S9.

S10 must answer:

```text
How should the system query 243,957 RAZ reading intake candidates without committing or repeatedly loading the 619 MB full candidate payload?
```

This is a DesignScan task. It must produce a design document only. It must not implement the query index builder, schema, validators, runtime query API, or any Reading Authority promotion.

## 3. Required Predecessors

Required completed stages:

```text
RAZ-AW-S6B_FullDerivedArtifactInventorySyncQA = PASS_AW_READY_FOR_S7
RAZ-AW-S7_ReadingAuthorityIntake_SchemaImplementation = PASS
RAZ-AW-S8_ReadingAuthorityIntake_BuilderImplementation = PUSHED_WITH_LARGE_ARTIFACT_EXTERNALIZED
RAZ-AW-S9_ReadingAuthorityIntake_BuilderQA_ArtifactExternalizationAndWarningTaxonomy = PASS
```

Relevant S8/S9 evidence:

```text
total_records = 243957
sentence = 201993
page_unit = 22632
reuse_unit = 19332
candidate_artifact_path = ulga/graph/raz_reading_authority_intake_candidates.json
candidate_artifact_size_mb = 619.32
candidate_artifact_git_policy = do_not_commit
candidate_artifact_status = LOCAL_ONLY
candidate_artifact_sha256 = 96040b787816dd1ef193c680cefb4c350a08d6e78f8619759f8716a71a4e0fc6
source_warning_count = 1646931
semantic_warning_count = 1646921
blocking_warning_count = 0
promotion_blocking_status = PROMOTION_STILL_BLOCKED
query_layer_ready = A-F only
```

## 4. Strict Scope

Allowed:

```text
Design analysis
query-index contract proposal
future artifact layout proposal
future schema / builder / validator plan
query-dimension taxonomy
storage and sharding strategy
artifact-size and Git policy analysis
warning-aware query strategy
promotion guardrail analysis
next-task recommendation
```

Forbidden:

```text
implementing a query-index builder
creating query index JSON/JSONL output
creating final reading_authority.json
Reading Authority promotion
promotion_allowed=true
final_eligible=true
authority_status other than candidate_only
query-layer approved-level expansion
runtime query API changes
learner state changes
planner changes
API/dashboard/scheduler changes
mutation of source RAZ derived artifacts
committing ulga/graph/raz_reading_authority_intake_candidates.json
loading the entire 619 MB candidate artifact into memory unnecessarily
LLM-generated learner-facing content
rewritten dialogue/writing/exercise content
```

## 5. Required Preflight

Run:

```powershell
git status -sb
```

Confirm unrelated pre-existing changes, if still present, are not touched by S10:

```text
ulga/graph/static_candidate_ranking*.json
ulga/graph/corpus_source_inventory.json
ulga/reports/corpus_source_inventory_summary.json
ulga/reports/raz_downstream_discovery_drift_validation.json
docs/drive_manifest_guide.md
reports/raz/drive_manifest_hydration_plan.status.json
tests/test_drive_manifest_manager.py
tools/drive_manifest_manager.py
```

Confirm `.gitignore` contains:

```text
ulga/graph/raz_reading_authority_intake_candidates.json
```

Do not modify `.gitignore` unless it is missing the required candidate-artifact exclusion.

## 6. Files to Inspect

Inspect:

```text
docs/ulga/RAZ_AW_S9_READING_AUTHORITY_INTAKE_BUILDER_QA_ARTIFACT_EXTERNALIZATION_AND_WARNING_TAXONOMY_PROMPT.md
docs/ulga/RAZ_AW_S9_READING_AUTHORITY_INTAKE_BUILDER_QA_ARTIFACT_EXTERNALIZATION_AND_WARNING_TAXONOMY.md
docs/ulga/RAZ_AW_S8_READING_AUTHORITY_INTAKE_BUILDER_IMPLEMENTATION_PROMPT.md
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

Optionally inspect the local large artifact only through metadata or streaming-safe sampling. Do not require reading the whole file for S10 DesignScan.

## 7. Required Output

Create:

```text
docs/ulga/RAZ_AW_S10_READING_AUTHORITY_INTAKE_QUERY_INDEX_DESIGNSCAN.md
```

Do not create code, schemas, graph outputs, validators, tests, or generated query-index data in S10.

## 8. Design Questions S10 Must Answer

### 8.1 Query layer purpose

Define the query index as a candidate-intake read model, not as Reading Authority promotion.

It should support future questions such as:

```text
Which candidate reading units are available for Level A / unit_type=sentence?
Which page_unit candidates exist for Level C with sentence_count > 1?
Which reuse_unit candidates have short_reading_seed or exercise_seed potential?
Which candidates are query_layer_ready under current policy?
Which candidates are blocked from query-layer use because levels G-W are not approved?
Which candidates have missing CEFR estimates but otherwise valid traceability?
Which records need metadata enrichment before promotion review?
```

### 8.2 Query dimensions

Evaluate at least these dimensions:

```text
reading_intake_id
source_level
normalized_level
unit_type
book_id
book_title
page_number
page_unit_id
source_sentence_candidate_ids
sentence_count
word_count
text_role
query_layer_ready
query_layer_approved
candidate_only / promotion flags
cefr_estimate
theme_tags
vocabulary_tags
grammar_tags
pattern_tags
skill_area
reusability_tags
source_traceability completeness
warning_family flags
artifact shard / offset / pointer
```

### 8.3 A-F versus G-W policy

S10 must preserve the current policy:

```text
A-F = query_layer_ready / approved under current policy
G-W = staged candidates only, not query-layer approved
```

The design may allow G-W records to be indexed as disabled/staging records, but it must not expand approved levels.

### 8.4 Storage strategy

Compare possible future storage/index layouts:

```text
single compact index manifest
level-sharded JSONL indexes
level + unit_type sharded JSONL indexes
SQLite local query cache
external artifact pointer + lightweight repo manifest
hybrid: Git-tracked compact index + local/Drive full payload
```

Recommend one default strategy for S11 implementation.

The recommendation should explicitly address:

```text
Git file-size safety
stable deterministic rebuilds
streaming build from local 619 MB artifact
counts reconciliation against S8/S9
hash verification against S9 artifact manifest
query speed
human review usability
future promotion review compatibility
```

### 8.5 Warning-aware query behavior

Use the S9 warning taxonomy to design warning-aware filters.

At minimum, define handling for:

```text
MISSING_CEFR_ESTIMATE
SPARSE_PEDAGOGICAL_TAGS
QUERY_LAYER_NOT_READY_G_TO_W
MISSING_BOOK_TITLE
LEGACY_TAG_COMPATIBILITY_MAPPED
UNSUPPORTED_LEGACY_REUSABILITY_TAG
S6B_PARITY_NOTE_INHERITED
SENTENCE_COUNT_HEURISTIC_MISMATCH
SOURCE_UNKNOWN_THEME
SOURCE_UNKNOWN_PATTERN
SOURCE_UNKNOWN_GRAMMAR
SOURCE_SECTION_HEADING_DETECTED
```

Important: these are warnings, not blockers. The query index may expose them as filterable flags, but must not convert them into promotion or runtime decisions.

### 8.6 Future output contract proposal

Propose future S11/S10A implementation outputs, but do not create them now.

Likely future artifacts:

```text
ulga/schemas/raz_reading_authority_intake_query_index.schema.json
ulga/builders/build_raz_reading_authority_intake_query_index.py
ulga/validators/validate_raz_reading_authority_intake_query_index.py
ulga/graph/raz_reading_authority_intake_query_index_manifest.json
ulga/graph/raz_reading_authority_intake_query_index/{level}/{unit_type}.jsonl
ulga/reports/raz_reading_authority_intake_query_index_summary.json
ulga/reports/raz_reading_authority_intake_query_index_validation.json
tests/ulga/test_raz_reading_authority_intake_query_index.py
```

The design must explicitly say whether the sharded query-index files should be Git-tracked or externalized.

### 8.7 Minimal query record proposal

Propose a compact query-record shape.

The proposed shape should avoid duplicating full source text unless justified. Consider short previews or metadata-only indexing.

Candidate conceptual shape:

```json
{
  "reading_intake_id": "RAZ_A_1001_SENT_000001",
  "source_level": "A",
  "normalized_level": "A",
  "unit_type": "sentence",
  "query_status": "approved_candidate",
  "book_id": "1001",
  "book_title": "...",
  "page_number": 1,
  "sentence_count": 1,
  "word_count": 4,
  "tags": {
    "cefr_estimate": "Pre-A1",
    "theme_tags": [],
    "vocabulary_tags": [],
    "grammar_tags": [],
    "pattern_tags": [],
    "skill_area": [],
    "reusability_tags": []
  },
  "warnings": [],
  "artifact_pointer": {
    "source_artifact": "ulga/graph/raz_reading_authority_intake_candidates.json",
    "source_hash_sha256": "...",
    "shard": null,
    "record_offset": null
  },
  "authority": {
    "authority_status": "candidate_only",
    "promotion_allowed": false,
    "final_eligible": false
  }
}
```

The final DesignScan should refine this, not blindly adopt it.

## 9. Required DesignScan Structure

The created DesignScan document must include:

```text
1. Preflight
2. Files inspected
3. Current state summary from S8/S9
4. Query index purpose and non-goals
5. Query dimensions
6. A-F / G-W query-layer policy
7. Storage strategy comparison
8. Recommended storage/index strategy
9. Warning-aware query design
10. Proposed future schema / builder / validator / tests
11. Artifact-size and Git policy
12. Guardrails
13. Risks and deferred work
14. Final verdict
15. Recommended next task
```

## 10. Acceptance Criteria

S10 is PASS only if the DesignScan:

```text
confirms S9 PASS as prerequisite
preserves LOCAL_ONLY policy for the 619 MB full candidate artifact
preserves candidate_only / promotion blocked status
does not expand query-layer approved levels beyond A-F
defines a concrete query-index strategy
defines future output files but does not create them
addresses warning-aware filtering without treating warnings as blockers
addresses Git size and external artifact policy
recommends the next implementation task
```

## 11. Recommended Final Verdict Format

Use:

```text
RAZ-AW-S10_ReadingAuthorityIntake_QueryIndexDesignScan = PASS
```

If any prerequisite is missing, use:

```text
RAZ-AW-S10_ReadingAuthorityIntake_QueryIndexDesignScan = BLOCKED_<REASON>
```

## 12. Recommended Next Task

If S10 passes, recommend one of:

```text
RAZ-AW-S11_ReadingAuthorityIntake_QueryIndexSchemaImplementation
```

or, if the design concludes a smaller staged implementation is safer:

```text
RAZ-AW-S10A_ReadingAuthorityIntake_QueryIndexContractImplementation
```

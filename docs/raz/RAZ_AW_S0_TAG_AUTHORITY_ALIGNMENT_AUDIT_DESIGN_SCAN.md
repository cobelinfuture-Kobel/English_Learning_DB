# RAZ-AW-S0 Tag Authority Alignment Audit Design Scan

## 1. Preflight

Task:

```text
RAZ-AW-S0_TagAuthorityAlignmentAudit_DesignScan
```

Scope:

```text
DESIGN SCAN ONLY
READ ONLY
NO RAW RAZ JSON MUTATION
NO RAZ OUTPUT INGESTION
NO AUTHORITY PROMOTION
NO TAG REGISTRY PROMOTION
NO NORMALIZER IMPLEMENTATION
NO VALIDATOR / BUILDER / TEST MUTATION
NO GENERATED READING / DIALOGUE / EXERCISE CONTENT
NO RUNTIME / API / SCHEDULER / DASHBOARD CHANGE
```

Repository:

```text
cobelinfuture-Kobel/English_Learning_DB
branch: main
```

Files inspected or used as upstream contract:

```text
docs/ulga/ENGLISHDB_GH_S2_TAG_REGISTRY_BOOTSTRAP_DESIGN_SCAN.md
tag_registry/tag_registry.bootstrap_draft.json
tag_registry/content_unit_type_registry.bootstrap_draft.json
tag_registry/reusability_tags_registry.bootstrap_draft.json
tag_registry/tag_alias_candidates.bootstrap_draft.json
docs/raz/RAZ_S6_REUSABLE_CONTENT_SEED_QUERY_LAYER_DESIGN_SCAN.md
docs/raz/RAZ_S6C_SEED_QUERY_AUTHORITY_LINKAGE_DESIGN_SCAN.md
docs/ulga/ULGA_AUX_S0_CORPUS_ROADMAP_AND_SOURCE_INVENTORY_DESIGN_SCAN.md
docs/ulga/ULGA_AUX_S1_GLOBAL_SOURCE_INVENTORY_IMPLEMENTATION.md
ulga/reports/corpus_source_inventory_summary.json
.gitignore
```

Files created by this task:

```text
docs/raz/RAZ_AW_S0_TAG_AUTHORITY_ALIGNMENT_AUDIT_DESIGN_SCAN.md
```

Risk level:

```text
Low
```

Reason:

```text
This task only defines the audit contract. It does not scan raw A-W data, mutate RAZ outputs, create validators, or promote any tag/content authority.
```

---

## 2. Current Readiness State

### 2.1 Upstream tag registry state

S2 created bootstrap draft tag registry artifacts. These are usable as candidate alignment targets, but they are not formal authority.

Current status:

```text
tag_registry.bootstrap_draft: PRESENT
content_unit_type_registry.bootstrap_draft: PRESENT
reusability_tags_registry.bootstrap_draft: PRESENT
tag_alias_candidates.bootstrap_draft: PRESENT
formal_tag_registry: NOT YET
```

Critical boundary:

```text
bootstrap_draft != formal_authority
candidate_only != approved
matched_bootstrap_tag != authority_linked_tag
```

### 2.2 RAZ source data state

Current Git policy still excludes:

```text
raz_output_jsons/
input/
output/
scratch/
```

Therefore, this design scan cannot perform actual A-W raw traversal in GitHub.

Current raw-scan status:

```text
RAZ A-F enriched summary: historically available in docs/reports
RAZ A-W raw JSON mounted in repo: NO
RAZ A-W raw alignment implementation: BLOCKED_BY_RAW_NOT_MOUNTED
```

### 2.3 Authority linkage state

Known limitations remain:

```text
RAZ grammar tags are rule-based.
RAZ vocabulary tags are not EVP-linked.
RAZ grammar tags are not EGP-linked.
RAZ CEFR is not authority-linked.
RAZ theme tags are mapped but not linked to Theme Authority refs.
RAZ pattern tags are rule-based and not linked to Sentence Pattern Authority refs.
```

Therefore, audit output must distinguish tag-surface alignment from authority-ref alignment.

---

## 3. Audit Purpose

The RAZ-AW-S0 audit should answer:

```text
1. Which observed RAZ tag-like values already match bootstrap registry entries?
2. Which observed values only match by alias?
3. Which observed values should become candidate_new_tags?
4. Which observed fields should remain source/context metadata and not become tags?
5. Which tag domains have enough coverage to support later normalization/query work?
6. Which gaps block formal authority alignment?
```

It should not answer:

```text
1. Whether any RAZ content is approved Reading Authority.
2. Whether any generated exercise/dialogue/worksheet should be created.
3. Whether any RAZ grammar/vocabulary/pattern tag is formally EGP/EVP/Pattern-linked.
4. Whether any raw extraction field should be rewritten.
```

---

## 4. Required Input Contract

A future implementation may accept either local mounted raw data or Git-tracked sanitized samples.

### 4.1 Preferred local input layout

```text
raz_output_jsons/
  Level_A/
  Level_B/
  ...
  Level_W/
  derived/
    Level_A/
    ...
    Level_W/
```

Alternative accepted layout:

```text
work/raz/A/raw_extracts/
work/raz/B/raw_extracts/
...
work/raz/W/raw_extracts/
```

### 4.2 Registry inputs

```text
tag_registry/tag_registry.bootstrap_draft.json
tag_registry/content_unit_type_registry.bootstrap_draft.json
tag_registry/reusability_tags_registry.bootstrap_draft.json
tag_registry/tag_alias_candidates.bootstrap_draft.json
```

### 4.3 Optional authority inputs

```text
ulga/graph/grammar_nodes.json
ulga/graph/vocabulary_nodes.json
ulga/graph/theme_nodes.json
ulga/graph/sentence_patterns.json
ulga/graph/chunk_nodes.json
```

If these are unavailable or too large, audit implementation must still produce tag-surface alignment, while marking authority-ref alignment as `not_evaluated`.

---

## 5. Observed Value Extraction Contract

The audit should collect observed values from these families when present.

### 5.1 Source fields

```text
source_tags.source
source_tags.source_type
source_tags.extraction_method
source_tags.extractor_version
source_tags.raz_level
source_tags.book_id
source_tags.book_title
source_tags.page_number
source_tags.page_unit_id
source_tags.candidate_id
source_tags.raw_file_path
```

Audit classification:

```text
raw_extraction_field
no_tag_needed_context_only
```

These fields must not become formal tags.

### 5.2 Content-unit fields

```text
content_unit_tags.content_unit_type
content_unit_tags.sentence_authority_eligible
content_unit_tags.is_story_sentence
content_unit_tags.is_heading
content_unit_tags.is_direct_speech
content_unit_tags.is_question
content_unit_tags.is_imperative
content_unit_tags.sentence_count
content_unit_tags.has_multi_sentence_unit
content_unit_tags.has_direct_speech
content_unit_tags.has_sequence
content_unit_tags.has_heading
```

Audit classification targets:

```text
content_unit_type
content_feature_flag
normalization_required_flag
```

### 5.3 Theme fields

```text
theme_tags.primary_theme
theme_tags.mapped_theme
theme_tags.subthemes
theme_tags.theme_confidence
theme_tags.theme_source
```

Audit classification targets:

```text
theme_query_hint
theme_authority_link_candidate
mapped_but_unverified
```

Theme value matching must be reported separately from Theme Authority node linkage.

### 5.4 Linguistic fields

```text
linguistic_tags.raz_level
linguistic_tags.grammar_tags
linguistic_tags.sentence_pattern_tags
linguistic_tags.vocabulary_tags[].normalized_word
linguistic_tags.vocabulary_tags[].pos
linguistic_tags.vocabulary_tags[].lookup_status
linguistic_tags.chunk_tags
```

Audit classification targets:

```text
rule_based_unlinked
candidate_unlinked
authority_linkage_required
```

No grammar, vocabulary, pattern, or chunk tag may be reported as formal authority unless explicit authority refs exist.

### 5.5 Pedagogical fields

```text
pedagogical_tags.skill_area
pedagogical_tags.question_type_candidates
pedagogical_tags.exercise_seed
pedagogical_tags.assessment_seed
```

Audit classification targets:

```text
query_hint
reuse_hint
candidate_only
```

### 5.6 Reuse fields

```text
reuse_tags.is_reusable_unit
reuse_tags.reusability_tags
reuse_tags.derivation_potential.short_reading
reuse_tags.derivation_potential.writing_model
reuse_tags.derivation_potential.dialogue_rewrite
reuse_tags.derivation_potential.exercise_generation
reuse_tags.derivation_potential.listening_audio
```

Audit classification targets:

```text
reusability_tag
reuse_hint
not_generation_approval
```

---

## 6. Alignment Categories

The audit must emit exactly these primary categories.

```text
matched_existing_tag
matched_existing_tag_by_alias
candidate_new_tag
no_tag_needed_context_only
```

### 6.1 `matched_existing_tag`

Use when observed value exactly matches a canonical bootstrap registry value.

Required fields:

```json
{
  "observed_value": "sentence",
  "domain": "content_unit_type",
  "matched_tag_id": "CUT_SENTENCE",
  "matched_label": "sentence",
  "alignment_category": "matched_existing_tag",
  "authority_status": "candidate_only"
}
```

### 6.2 `matched_existing_tag_by_alias`

Use when observed value matches an alias candidate.

Required fields:

```json
{
  "observed_value": "title",
  "domain": "content_unit_type",
  "alias_matched": "title",
  "canonical_candidate": "heading",
  "alignment_category": "matched_existing_tag_by_alias",
  "auto_merge_allowed": false,
  "review_status": "pending"
}
```

### 6.3 `candidate_new_tag`

Use when observed value is tag-like, useful, but not in bootstrap registry or alias candidates.

Required fields:

```json
{
  "observed_value": "side_bar_note",
  "domain": "content_unit_type",
  "alignment_category": "candidate_new_tag",
  "authority_status": "candidate_only",
  "review_status": "pending",
  "example_refs": []
}
```

### 6.4 `no_tag_needed_context_only`

Use when observed field is source trace, count, id, page number, confidence score, or diagnostic metadata.

Required fields:

```json
{
  "observed_field": "source_tags.book_id",
  "observed_value": "883",
  "alignment_category": "no_tag_needed_context_only",
  "reason": "source_trace_identifier"
}
```

---

## 7. Required Output Artifacts For Future Implementation

A future implementation should write:

```text
reports/raz/tag_alignment_report.json
reports/raz/candidate_new_tags.json
reports/raz/observed_raw_tag_inventory.json
reports/raz/tag_alias_mapping_candidates.json
reports/raz/authority_linkage_gap_report.json
```

### 7.1 `observed_raw_tag_inventory.json`

Purpose:

```text
Inventory every observed tag-like field/value by level, source family, and count.
```

Required top-level shape:

```json
{
  "task_id": "RAZ-AW-S0_TagAuthorityAlignmentAudit",
  "levels_requested": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W"],
  "levels_scanned": [],
  "levels_missing": [],
  "observed_domains": {},
  "field_inventory": []
}
```

### 7.2 `tag_alignment_report.json`

Purpose:

```text
Classify observed tag-like values against bootstrap registry and alias candidates.
```

Required summary fields:

```json
{
  "alignment_status": "PASS | PASS_WITH_WARNINGS | BLOCKED",
  "registry_status_used": "bootstrap_draft",
  "raw_mutation": false,
  "authority_promotion": false,
  "counts_by_alignment_category": {},
  "counts_by_domain": {},
  "records": []
}
```

### 7.3 `candidate_new_tags.json`

Purpose:

```text
List proposed new tags only as pending candidates.
```

Required rule:

```text
Every record must carry review_status=pending and authority_status=candidate_only.
```

### 7.4 `authority_linkage_gap_report.json`

Purpose:

```text
Show where RAZ tag surfaces exist but formal authority refs are absent.
```

Required categories:

```text
missing_egp_grammar_ref
missing_evp_vocabulary_ref
missing_pattern_authority_ref
missing_theme_authority_ref
missing_chunk_authority_ref
not_applicable
not_evaluated
```

---

## 8. Validation Rules

A future validator for this audit must check:

```text
1. All output JSON files parse.
2. alignment_category is one of the four allowed categories.
3. No candidate_new_tag has review_status other than pending.
4. No RAZ-derived tag has authority_status=formal unless explicit authority refs exist.
5. raw_extraction_fields_not_formal_tags are never emitted as formal tags.
6. alias matches retain auto_merge_allowed=false unless manually reviewed.
7. counts_by_alignment_category match record counts.
8. levels_missing is non-empty when A-W is requested but not all levels are available.
9. authority_promotion is always false for S0.
10. raw_mutation is always false for S0.
```

---

## 9. Blockers / Warnings

### 9.1 Hard blocker for implementation scan

```text
RAZ A-W raw JSON is not currently mounted in GitHub.
```

Because `raz_output_jsons/` is intentionally ignored, full A-W scanning must wait until the operator either:

```text
1. provides a local Codex workspace with raw_A-W accessible, or
2. uploads a sanitized raw inventory/sample set, or
3. explicitly stages rights-safe raw JSON to a private repo path.
```

### 9.2 Warnings

```text
1. Bootstrap registry is candidate_only, not formal authority.
2. RAZ tag fields are useful query metadata, not authority evidence.
3. RAZ A-F docs prove candidate seed query readiness, not A-W raw coverage.
4. Higher-level RAZ content may introduce content unit types not yet present in bootstrap draft.
5. Alias matching must not rewrite tags automatically.
```

---

## 10. Design Verdict

```text
RAZ-AW-S0 DesignScan verdict: PASS_WITH_WARNINGS
```

Meaning:

```text
The audit contract is ready.
The bootstrap registry can be used as an alignment target.
The future implementation is blocked from full A-W scan until raw A-W is mounted or provided.
No authority promotion is allowed from this task.
```

---

## 11. Recommended Next Task

Recommended next task:

```text
RAZ-AW-S1_RawAWInventoryMountAndSafetyCheck
```

Purpose:

```text
Confirm which A-W raw files are available, count levels/books/files, detect large files, preserve copyright/source-role boundaries, and decide whether the raw inventory can be scanned locally without committing raw text to GitHub.
```

Alternative if the operator wants to avoid raw exposure in GitHub:

```text
RAZ-AW-S1_LocalRawInventoryReadOnlyAuditPrompt
```

This would instruct Codex to scan local `raz_output_jsons/` only and commit reports, not raw corpus files.

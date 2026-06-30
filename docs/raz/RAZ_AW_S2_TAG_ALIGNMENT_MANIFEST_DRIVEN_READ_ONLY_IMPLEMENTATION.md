# RAZ-AW-S2 Tag Alignment Manifest-Driven Read-Only Implementation

## 1. Preflight

Task:

```text
RAZ-AW-S2_TagAlignmentManifestDrivenReadOnlyImplementation
```

Scope:

```text
MANIFEST-DRIVEN TAG ALIGNMENT IMPLEMENTATION
READ ONLY AGAINST RAW CORPUS
SANITIZED REPORT OUTPUT ONLY
NO RAW RAZ JSON READ REQUIRED
NO RAW RAZ JSON MUTATION
NO RAW RAZ JSON COMMIT
NO FULL RAW TEXT IN REPORTS
NO AUTHORITY PROMOTION
NO TAG REGISTRY PROMOTION
NO NORMALIZER IMPLEMENTATION
NO GENERATED READING / DIALOGUE / EXERCISE CONTENT
NO RUNTIME / API / SCHEDULER / DASHBOARD CHANGE
```

Repository:

```text
cobelinfuture-Kobel/English_Learning_DB
branch: main
```

Upstream dependencies:

```text
EnglishDB-GH-S2_TagRegistryBootstrap_DesignScan
RAZ-AW-S1C_RawAWDriveManifestGeneration
```

Required inputs:

```text
reports/raz/raw_aw_drive_file_manifest.json
tag_registry/content_unit_type_registry.bootstrap_draft.json
tag_registry/tag_alias_candidates.bootstrap_draft.json
```

Files created by this task:

```text
docs/raz/RAZ_AW_S2_TAG_ALIGNMENT_MANIFEST_DRIVEN_READ_ONLY_IMPLEMENTATION.md
tools/raz_aw_tag_alignment_from_manifest.py
reports/raz/tag_alignment_manifest_driven.status.json
```

Files intentionally not created by this GitHub-side run:

```text
reports/raz/observed_raw_tag_inventory.json
reports/raz/tag_alignment_report.json
reports/raz/candidate_new_tags.json
reports/raz/tag_alias_mapping_candidates.json
reports/raz/authority_linkage_gap_report.json
reports/raz/tag_alignment_manifest_driven_safety_report.json
```

Reason:

```text
The implementation tool has been committed to GitHub. The report generation step should run in the operator's local repository after pulling this tool, because the manifest is large and local execution is safer and more deterministic.
```

Risk level:

```text
Low
```

---

## 2. S2 Input Readiness

S1C manifest state:

```text
manifest_status: GENERATED
sanitized: true
contains_raw_text: false
raw_mutation: false
raw_commit_allowed: false
levels_present: A-W
levels_missing: []
file_count_total: 1961
json_parse_status_counts: PASS=1960, FAIL=1
large_file_count_over_50mb: 0
large_file_count_over_100mb: 0
unexpected_file_count: 0
media_file_count: 0
archive_file_count: 0
```

S2 readiness:

```text
READY_WITH_ONE_PARSE_WARNING
```

Parse-fail rule:

```text
Any manifest record whose json_parse_status is not PASS must be skipped and reported in diagnostics. It must not block the whole S2 run.
```

---

## 3. Alignment Method

The S2 implementation is intentionally manifest-driven.

It reads only these safe manifest-level facts:

```text
level
filename
relative_path_hash
size_bytes / size_mb
json_parse_status
source_type
extraction_method
extractor_version
book_id
book_title
level_from_json
story_page_count
sentence_candidate_count
page_unit_count
reuse_candidate_count
excluded_item_count
legacy_story_sentence_count
authority_status
generated_content
raw_audio_fields_preserved
final_should_remove_audio_fields
top_level_keys
```

It does not read:

```text
raw JSON corpus files
sentence_candidates objects
page_units objects
reuse_unit_candidates objects
legacy_story_sentences text
word_trace
audio_trace
page text
sentence text
```

---

## 4. Alignment Categories

The implementation emits only the four S0-approved categories:

```text
matched_existing_tag
matched_existing_tag_by_alias
candidate_new_tag
no_tag_needed_context_only
```

### 4.1 Content-unit alignment

The tool infers safe content-unit evidence from manifest counts and top-level key names:

```text
sentence_candidate_count > 0 or top_level_keys contains sentence_candidates -> sentence
page_unit_count > 0 or top_level_keys contains page_units -> page_unit
reuse_candidate_count > 0 or top_level_keys contains reuse_unit_candidates -> reuse_unit
```

These are matched to bootstrap content-unit registry entries only as candidate-only registry matches.

### 4.2 Context-only classification

The tool classifies source trace fields, file fields, parse status, size fields, source_type, extraction_method, book_id, book_title, and level fields as:

```text
no_tag_needed_context_only
```

Reason:

```text
These are source/manifest metadata, not formal authority tags.
```

### 4.3 Authority linkage gap report

Because the manifest does not contain grammar, vocabulary, theme, pattern, or chunk authority refs, S2 emits:

```text
not_evaluated_manifest_only
```

for:

```text
missing_egp_grammar_ref
missing_evp_vocabulary_ref
missing_pattern_authority_ref
missing_theme_authority_ref
missing_chunk_authority_ref
```

---

## 5. Output Reports After Local Run

Run command:

```powershell
cd G:\HomeWork\English_Learning_DB
git pull
python tools\raz_aw_tag_alignment_from_manifest.py
```

Expected output files:

```text
reports/raz/observed_raw_tag_inventory.json
reports/raz/tag_alignment_report.json
reports/raz/candidate_new_tags.json
reports/raz/tag_alias_mapping_candidates.json
reports/raz/authority_linkage_gap_report.json
reports/raz/tag_alignment_manifest_driven_safety_report.json
```

Commit command:

```powershell
git add reports\raz\observed_raw_tag_inventory.json `
        reports\raz\tag_alignment_report.json `
        reports\raz\candidate_new_tags.json `
        reports\raz\tag_alias_mapping_candidates.json `
        reports\raz\authority_linkage_gap_report.json `
        reports\raz\tag_alignment_manifest_driven_safety_report.json

git commit -m "reports: add manifest-driven RAZ AW tag alignment"
git push
```

Do not run:

```powershell
git add .
```

---

## 6. Safety Guarantees

The implementation enforces:

```text
contains_raw_text: false
raw_mutation: false
authority_promotion: false
tag_registry_promotion: false
```

It also rejects report payloads that would emit forbidden raw-text-bearing keys such as:

```text
sentence_candidates
page_units
reuse_unit_candidates
legacy_story_sentences_text
word_trace
audio_trace
raw_text
page_text
```

---

## 7. Current S2 Verdict

```text
RAZ-AW-S2 GitHub-side implementation: PASS_WITH_WARNINGS
```

Meaning:

```text
The implementation tool exists.
The actual alignment reports have not yet been generated in this connector session.
The local run is required.
One manifest parse-fail record is expected to be skipped and reported.
```

After the local S2 reports are committed, run:

```text
RAZ-AW-S2A_TagAlignmentReportReadbackQA
```

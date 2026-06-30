# RAZ-AW-S1C Raw A-W Drive Manifest Generation

## 1. Preflight

Task:

```text
RAZ-AW-S1C_RawAWDriveManifestGeneration
```

Scope:

```text
MANIFEST GENERATION TOOLING
SANITIZED REPORT OUTPUT ONLY
NO RAW RAZ JSON MUTATION
NO RAW RAZ JSON COMMIT
NO FULL RAW TEXT IN REPORTS
NO TAG ALIGNMENT IMPLEMENTATION
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
RAZ-AW-S1A_GoogleDriveRawInventoryReadOnlyReportGeneration
RAZ-AW-S1B_DriveKnownFileFetchAndManifestStrategy
```

Files created by this task:

```text
docs/raz/RAZ_AW_S1C_RAW_AW_DRIVE_MANIFEST_GENERATION.md
tools/raz_aw_drive_manifest_from_local_mirror.py
tools/raz_aw_drive_manifest_apps_script.gs
reports/raz/raw_aw_drive_file_manifest.status.json
```

Files intentionally not created by this GitHub-side run:

```text
reports/raz/raw_aw_drive_file_manifest.json
reports/raz/raw_aw_manifest_generation_safety_report.json
```

Reason:

```text
The full manifest requires either local filesystem access to a synced/mirrored raz_output_jsons folder or a Google Apps Script/Drive API run with full folder enumeration. The current ChatGPT Drive connector can fetch known file URLs but cannot reliably enumerate all nested files in the shared folder.
```

Risk level:

```text
Low
```

---

## 2. Current Evidence

Known-file Drive fetch has been proven:

```text
file_id: 1p-wtd73dK9KrdIpTo8SfUecIkssFVXTK
title: raz_A_6_audio_timeline_extract.json
json_parse: PASS
level: A
book_id: 6
book_title: I Can
```

Therefore, the remaining blocker is not file access. The remaining blocker is complete and stable A-W file enumeration.

Current status:

```text
known_file_fetch: PASS
known_file_parse: PASS
folder_level_AW_discovery: PASS
complete_nested_file_enumeration: NOT_AVAILABLE_IN_CURRENT_CONNECTOR
full_manifest_generation: OPERATOR_OR_CODEX_LOCAL_RUN_REQUIRED
```

---

## 3. Implemented Manifest Generation Paths

This task adds two supported paths.

### 3.1 Local mirror generator

Tool:

```text
tools/raz_aw_drive_manifest_from_local_mirror.py
```

Use when `raz_output_jsons/` exists locally or through Google Drive desktop sync.

Example command from repo root:

```powershell
python tools\raz_aw_drive_manifest_from_local_mirror.py --raw-root G:\HomeWork\English_Learning_DB\raz_output_jsons
```

Output files:

```text
reports/raz/raw_aw_drive_file_manifest.json
reports/raz/raw_aw_manifest_generation_safety_report.json
reports/raz/raw_aw_large_file_report.json
```

### 3.2 Google Apps Script generator

Tool:

```text
tools/raz_aw_drive_manifest_apps_script.gs
```

Use when the Google Drive folder is the authoritative source and file IDs are required for every JSON file.

Default root folder id:

```text
15P1dahD12t9Hsht1cPKIEj8K0oPc6Noz
```

Output file name created in Drive:

```text
raw_aw_drive_file_manifest.json
```

The generated file should then be downloaded or copied into:

```text
reports/raz/raw_aw_drive_file_manifest.json
```

---

## 4. Manifest Safety Contract

The manifest may include:

```text
level
folder_title
filename
relative_path or drive_file_id
drive_url if available
size_bytes
mime_type
json_parse_status
source_type
extraction_method
extractor_version
book_id
book_title
sentence_candidate_count
page_unit_count
reuse_candidate_count
excluded_item_count
authority_status
```

The manifest must not include:

```text
sentence text
page text
legacy_story_sentences text
cleaned_candidate text
word trace
audio trace
full page_units
full sentence_candidates
full reuse_unit_candidates
image payloads
PDF/audio/media payloads
```

---

## 5. Current S1C Verdict

```text
RAZ-AW-S1C GitHub-side implementation: PASS_WITH_WARNINGS
```

Meaning:

```text
Manifest generation tooling exists.
The manifest has not been generated inside this ChatGPT connector session.
S2 tag alignment remains blocked until reports/raz/raw_aw_drive_file_manifest.json exists and is reviewed.
```

---

## 6. Operator Run Steps

### Option A: Local mirror run

```powershell
cd G:\HomeWork\English_Learning_DB
python tools\raz_aw_drive_manifest_from_local_mirror.py --raw-root G:\HomeWork\English_Learning_DB\raz_output_jsons
git status
```

Only stage report outputs, not raw corpus:

```powershell
git add reports\raz\raw_aw_drive_file_manifest.json reports\raz\raw_aw_manifest_generation_safety_report.json reports\raz\raw_aw_large_file_report.json
git commit -m "reports: add RAZ AW raw Drive manifest"
git push
```

### Option B: Google Apps Script run

```text
1. Open Google Apps Script.
2. Paste tools/raz_aw_drive_manifest_apps_script.gs.
3. Run generateRazAwDriveFileManifest().
4. Download or copy the generated raw_aw_drive_file_manifest.json.
5. Place it at reports/raz/raw_aw_drive_file_manifest.json.
6. Commit only that sanitized manifest/report.
```

---

## 7. Next Task Gate

Proceed to S2 only when this file exists:

```text
reports/raz/raw_aw_drive_file_manifest.json
```

Required S2 gate:

```text
manifest_status: GENERATED
contains_raw_text: false
raw_commit_allowed: false
levels_present includes expected available A-W levels
file_count_total > 0
json_parse_status_counts available
```

Next task after the manifest is generated:

```text
RAZ-AW-S2_TagAlignmentManifestDrivenReadOnlyImplementation
```

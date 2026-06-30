# RAZ-AW-S2C Drive Manifest Hydration Tooling

## 1. Preflight

Task:

```text
RAZ-AW-S2C_DriveManifestHydrationTooling
```

Scope:

```text
DRIVE MANIFEST HYDRATION TOOLING
SANITIZED SHALLOW QA OUTPUT ONLY
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

Upstream dependency:

```text
RAZ-AW-S2B_DriveFileIDManifestReadbackQA
```

Files created by this task:

```text
docs/raz/RAZ_AW_S2C_DRIVE_MANIFEST_HYDRATION_TOOLING.md
tools/raz_aw_drive_manifest_hydration_plan.py
tools/raz_aw_drive_manifest_hydration_apps_script.gs
reports/raz/drive_manifest_hydration_tooling_status.json
```

Risk level:

```text
Low
```

Reason:

```text
This task creates tooling and status metadata only. It does not hydrate all raw JSON files in this connector session and does not commit raw JSON.
```

---

## 2. S2B Readiness Recap

S2B established:

```text
manifest_fetch: PASS
manifest_parse: PASS
a_w_file_id_coverage: PASS
manifest_driven_per_file_fetch: PASS
folder_search_enumeration_required: false
```

Drive manifest:

```text
file_id: 1gNIiNgh8uyohMVhFl1wqJEPJpqrLkYkY
title: manifest.json
shape: relative_path -> drive_file_id
raw_level_json_file_count: 1959
levels_present: A-W
levels_missing: []
```

Therefore S2C does not need Google Drive folder search. It uses:

```text
manifest.json -> drive_file_id -> fetch JSON by file ID
```

---

## 3. Tooling Added

### 3.1 Local hydration planner

Tool:

```text
tools/raz_aw_drive_manifest_hydration_plan.py
```

Purpose:

```text
Read a locally downloaded Drive manifest.json and generate sanitized hydration planning reports.
It does not fetch Google Drive files.
```

Expected input path:

```text
scratch/raz/manifest.json
```

`scratch/` should stay uncommitted.

Command:

```powershell
cd G:\HomeWork\English_Learning_DB
python tools\raz_aw_drive_manifest_hydration_plan.py --manifest scratch\raz\manifest.json
```

Expected outputs:

```text
reports/raz/drive_manifest_hydration_plan.json
reports/raz/drive_manifest_hydration_sample_urls.json
```

These reports contain file IDs, URLs, relative paths, levels, and counts only. They do not contain raw sentence/page/audio text.

### 3.2 Google Apps Script hydration QA

Tool:

```text
tools/raz_aw_drive_manifest_hydration_apps_script.gs
```

Purpose:

```text
Run inside Google Apps Script with Drive access.
Fetch selected or full raw JSON files by file_id from the Drive manifest.
Emit shallow schema QA only.
```

Supported functions:

```text
hydrateRazAwManifestSample()
hydrateRazAwManifestLevel('A')
hydrateRazAwManifestFull()
```

Output files are written to the Drive folder and named:

```text
drive_manifest_hydration_sample_<timestamp>.json
drive_manifest_hydration_level_<LEVEL>_<timestamp>.json
drive_manifest_hydration_full_<timestamp>.json
```

---

## 4. Hydration Modes

### sample

```text
first / middle / last raw JSON per A-W level
```

Use this for quick QA.

### level

```text
all raw JSON files for one selected level
```

Use this before full hydration, for example:

```javascript
hydrateRazAwManifestLevel('A')
hydrateRazAwManifestLevel('W')
```

### full

```text
all 1959 raw level JSON files from manifest
```

Use only after sample and level runs pass.

---

## 5. Shallow Hydration Fields

Allowed emitted fields:

```text
relative_path
drive_file_id
level
book_id
book_title
size_bytes
mime_type
json_parse_status
source_type
extraction_method
extractor_version
story_page_start
story_page_end
story_page_count
sentence_candidate_count
page_unit_count
reuse_candidate_count
excluded_item_count
legacy_story_sentence_count
authority_status
generated_content
```

Forbidden emitted fields:

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

## 6. Commit Policy

Commit allowed:

```text
reports/raz/drive_manifest_hydration_plan.json
reports/raz/drive_manifest_hydration_sample_urls.json
sanitized Apps Script result reports after review
```

Commit forbidden:

```text
raw RAZ JSON files
full hydrated raw JSON payloads
sentence/page/audio trace text
Google Drive local cache folders
scratch/
```

Do not use:

```powershell
git add .
```

Only add explicit sanitized report files.

---

## 7. Current S2C Verdict

```text
RAZ-AW-S2C GitHub-side tooling: PASS_WITH_WARNINGS
```

Meaning:

```text
Hydration tooling exists.
The full Drive hydration run has not been executed in this connector session.
Use sample mode first, then level mode, then full mode if needed.
```

Recommended next task after running sample hydration:

```text
RAZ-AW-S2D_DriveManifestHydrationSampleQA
```

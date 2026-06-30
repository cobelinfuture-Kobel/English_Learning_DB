# RAZ-AW-S1B Drive Known File Fetch And Manifest Strategy

## 1. Preflight

Task:

```text
RAZ-AW-S1B_DriveKnownFileFetchAndManifestStrategy
```

Scope:

```text
GOOGLE DRIVE KNOWN-FILE FETCH PROBE
MANIFEST STRATEGY ONLY
SANITIZED REPORTS ONLY
NO RAW RAZ JSON MUTATION
NO RAW RAZ JSON COMMIT
NO FULL RAW TEXT IN REPORTS
NO FOLDER-WIDE TAG ALIGNMENT
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

Known file provided by operator:

```text
url: https://drive.google.com/file/d/1p-wtd73dK9KrdIpTo8SfUecIkssFVXTK/view?usp=drive_link
file_id: 1p-wtd73dK9KrdIpTo8SfUecIkssFVXTK
title: raz_A_6_audio_timeline_extract.json
```

Files created by this task:

```text
docs/raz/RAZ_AW_S1B_DRIVE_KNOWN_FILE_FETCH_AND_MANIFEST_STRATEGY.md
reports/raz/drive_known_file_fetch_probe_report.json
reports/raz/raw_aw_drive_manifest_strategy.json
reports/raz/raw_aw_manifest_seed.sample.json
```

Risk level:

```text
Low
```

Reason:

```text
The task proves known-file fetch viability and defines a manifest strategy. It does not enumerate the full raw corpus or commit raw text.
```

---

## 2. Known File Fetch Result

The known Google Drive JSON file was accessible by direct URL.

Observed metadata:

```text
file_id: 1p-wtd73dK9KrdIpTo8SfUecIkssFVXTK
title: raz_A_6_audio_timeline_extract.json
created_time: 2026-06-30T13:09:46.352Z
modified_time: 2026-06-24T15:00:26.000Z
```

Local shallow JSON probe result:

```text
json_parse: PASS
size_bytes: 32298
source_type: raz_audio_timeline
extraction_method: bookAudioContent
extractor_version: raz_audio_timeline_to_content_authority_v3_story_filter
level: A
book_id: 6
book_title: I Can
sentence_candidate_count: 8
page_unit_count: 8
reuse_candidate_count: 0
excluded_item_count: 3
legacy_story_sentence_count: 8
authority_status: candidate_only
generated_content: false
raw_audio_fields_preserved: true
final_should_remove_audio_fields: true
```

Critical interpretation:

```text
Google Drive known-file fetch: PASS
Google Drive known-file JSON parse: PASS
Folder-level enumeration: STILL UNRELIABLE
Full A-W inventory: NOT YET
```

---

## 3. Updated Understanding

Prior S1A showed:

```text
Drive root folder discovery: PASS
A-W level folder discovery: PASS
file-level enumeration by parent search: NOT VERIFIED
```

S1B adds:

```text
Known file URL fetch: PASS
Known file shallow parse: PASS
```

Therefore the remaining blocker is not file access. The remaining blocker is complete and stable file enumeration.

Correct blocker wording:

```text
file access is available when file IDs are known
folder enumeration through the current connector search surface is not reliable enough for A-W inventory
```

---

## 4. Manifest Strategy

To proceed safely, the system needs a manifest that maps every raw JSON file to a Drive file ID without containing raw sentence/page text.

Recommended manifest:

```text
reports/raz/raw_aw_drive_file_manifest.json
```

This manifest should be generated outside raw corpus commit paths and may be committed only if sanitized.

### 4.1 Required manifest fields

Each record should contain:

```json
{
  "level": "A",
  "folder_title": "Level_A",
  "filename": "raz_A_6_audio_timeline_extract.json",
  "drive_file_id": "1p-wtd73dK9KrdIpTo8SfUecIkssFVXTK",
  "drive_url": "https://drive.google.com/file/d/1p-wtd73dK9KrdIpTo8SfUecIkssFVXTK/view",
  "size_bytes": 32298,
  "mime_type": "application/json",
  "json_parse_status": "PASS",
  "raw_text_in_manifest": false
}
```

### 4.2 Optional shallow schema fields

The manifest may include shallow schema counts only:

```json
{
  "source_type": "raz_audio_timeline",
  "extraction_method": "bookAudioContent",
  "extractor_version": "raz_audio_timeline_to_content_authority_v3_story_filter",
  "book_id": "6",
  "book_title": "I Can",
  "sentence_candidate_count": 8,
  "page_unit_count": 8,
  "reuse_candidate_count": 0,
  "excluded_item_count": 3,
  "authority_status": "candidate_only"
}
```

### 4.3 Forbidden manifest fields

Do not include:

```text
sentence text
page text
legacy_story_sentences text
audio word traces
full page units
full sentence candidate objects
raw audio timelines
image payloads
PDF/audio/media files
```

---

## 5. Manifest Generation Options

### Option A: Operator-side local script

Use a local script against a Google Drive synced folder or local mirror.

Pros:

```text
fast
can enumerate all files
can calculate exact size_bytes
can parse shallow JSON schema
no Drive API pagination issue
```

Cons:

```text
requires local filesystem access
requires operator/Codex local run
```

### Option B: Google Drive export/listing by Apps Script

Use Google Apps Script or Drive API to generate a CSV/JSON manifest from the shared Drive folder.

Pros:

```text
works directly in Drive
can enumerate nested files reliably
can include Drive file IDs and sizes
```

Cons:

```text
requires a small Apps Script or Drive API step
must ensure no raw text is included
```

### Option C: Manual known-file seed expansion

Operator supplies known file URLs in batches.

Pros:

```text
works with current connector
no special script required
```

Cons:

```text
not scalable for A-W full inventory
high operator overhead
```

Recommended path:

```text
Option B if the Drive folder is authoritative source storage.
Option A if Google Drive is synced locally.
```

---

## 6. Pass / Warning / Block Criteria

### PASS

```text
known-file fetch works
manifest exists
manifest covers A-W
manifest has no raw text
all listed JSON files include file_id / filename / level / size_bytes
large-file categories are calculated
at least shallow JSON parse status is recorded
```

### PASS_WITH_WARNINGS

```text
known-file fetch works
manifest is partial
some levels have missing file counts
some JSON parse statuses are not evaluated
large-file scan is incomplete
```

### BLOCKED

```text
known-file fetch fails
manifest cannot be generated
manifest contains raw text
manifest lacks file IDs
manifest cannot distinguish levels
raw corpus files are staged for Git commit
```

---

## 7. Current S1B Verdict

```text
RAZ-AW-S1B verdict: PASS_WITH_WARNINGS
```

Meaning:

```text
Known-file fetch and shallow JSON parse are proven.
A manifest-based strategy is ready.
Full A-W file inventory remains blocked until a manifest is generated.
S2 tag alignment remains blocked until manifest coverage is available.
```

---

## 8. Recommended Next Task

Recommended next task:

```text
RAZ-AW-S1C_RawAWDriveManifestGeneration
```

Goal:

```text
Generate reports/raz/raw_aw_drive_file_manifest.json with A-W file IDs, filenames, level mapping, file sizes, parse status, and no raw text.
```

Alternative if using local synced Drive:

```text
RAZ-AW-S1C_LocalMirrorManifestGeneration
```

Only after S1C produces a complete manifest should the project proceed to:

```text
RAZ-AW-S2_TagAlignmentLocalOrManifestDrivenReadOnlyImplementation
```

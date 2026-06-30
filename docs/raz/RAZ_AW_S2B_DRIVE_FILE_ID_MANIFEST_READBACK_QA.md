# RAZ-AW-S2B Drive File ID Manifest Readback QA

## 1. Preflight

Task:

```text
RAZ-AW-S2B_DriveFileIDManifestReadbackQA
```

Scope:

```text
GOOGLE DRIVE FILE-ID MANIFEST READBACK QA
SANITIZED REPORT OUTPUT ONLY
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

Input manifest URL:

```text
https://drive.google.com/file/d/1gNIiNgh8uyohMVhFl1wqJEPJpqrLkYkY/view?usp=drive_link
```

Files created by this task:

```text
docs/raz/RAZ_AW_S2B_DRIVE_FILE_ID_MANIFEST_READBACK_QA.md
reports/raz/drive_file_id_manifest_readback_report.json
reports/raz/drive_file_id_manifest_sample_fetch_report.json
```

Risk level:

```text
Low
```

Reason:

```text
This task only reads a Drive manifest and samples file-id fetches. It records sanitized metadata and shallow counts only.
```

---

## 2. Manifest Fetch Result

Google Drive manifest fetch:

```text
file_id: 1gNIiNgh8uyohMVhFl1wqJEPJpqrLkYkY
title: manifest.json
created_time: 2026-06-30T16:46:17.324Z
modified_time: 2026-06-30T16:46:17.324Z
```

Manifest structure:

```json
{
  "last_updated": "...",
  "target_folder_id": "...",
  "files": {
    "raz_output_jsons/Level_A/xxx.json": "drive_file_id"
  }
}
```

Interpretation:

```text
The Drive-side manifest provides an explicit relative_path -> drive_file_id map.
This removes the need to rely on unstable nested folder enumeration by connector search.
```

---

## 3. Coverage Readback

Manifest-level counts:

```text
manifest_file_count_total: 2000
raw_level_json_file_count: 1959
derived_file_count: 39
special_file_count: 2
non_json_file_count: 0
duplicate_drive_file_id_count: 0
raw_filename_pattern_mismatch_count: 0
```

A-W level coverage:

```text
A: 100
B: 100
C: 100
D: 83
E: 93
F: 90
G: 92
H: 84
I: 88
J: 83
K: 83
L: 67
M: 73
N: 74
O: 77
P: 75
Q: 64
R: 67
S: 100
T: 90
U: 77
V: 99
W: 100
```

Missing levels:

```text
[]
```

Special files:

```text
raz_output_jsons/run_failed_items.json
raz_output_jsons/run_summary.json
```

---

## 4. Sample File-ID Fetch QA

Four manifest-driven file-id fetches were sampled across low/mid/high RAZ levels.

### Sample A

```text
manifest_path: raz_output_jsons/Level_A/raz_A_1067_audio_timeline_extract.json
drive_file_id: 1Yrf3hkV1DAncSDnFDatvztN7Ks1oRLEG
fetch_status: PASS
json_parse_status: PASS
level: A
book_id: 1067
book_title: Pond Animals
sentence_candidate_count: 8
page_unit_count: 8
reuse_candidate_count: 0
```

### Sample M

```text
manifest_path: raz_output_jsons/Level_M/raz_M_1016_audio_timeline_extract.json
drive_file_id: 1rJhAyDhJZOVDovzTKRz1lRdxK991vW9-
fetch_status: PASS
json_parse_status: PASS
level: M
book_id: 1016
book_title: Frogs and Toads
sentence_candidate_count: 94
page_unit_count: 12
reuse_candidate_count: 12
```

### Sample U

```text
manifest_path: raz_output_jsons/Level_U/raz_U_3975_audio_timeline_extract.json
drive_file_id: 1Qt5CzJY7FkdlBx1cgHyMZc50kYirRIE4
fetch_status: PASS
json_parse_status: PASS
level: U
book_id: 3975
book_title: The World's Biggest Library
sentence_candidate_count: 212
page_unit_count: 11
reuse_candidate_count: 11
```

### Sample W

```text
manifest_path: raz_output_jsons/Level_W/raz_W_1014_audio_timeline_extract.json
drive_file_id: 1huZ9k1AfKXcZ99ft7LGo2bAtjj447F9y
fetch_status: PASS
json_parse_status: PASS
level: W
book_id: 1014
book_title: Joe Kittinger: An Unsung Hero
sentence_candidate_count: 298
page_unit_count: 18
reuse_candidate_count: 18
```

Sample summary:

```text
samples_attempted: 4
samples_fetched: 4
samples_parsed: 4
failures: 0
```

---

## 5. Updated Route Assessment

Previous limitation:

```text
Google Drive folder search / nested enumeration was not reliable enough for full A-W inventory.
```

S2B updated route:

```text
Drive manifest -> drive_file_id -> fetch JSON
```

Result:

```text
known_file_fetch: PASS
manifest_fetch: PASS
manifest_parse: PASS
a_w_file_id_coverage: PASS
manifest_driven_per_file_fetch: PASS
folder_search_enumeration_required: false
```

This does not mean all 1959 raw JSON files were fully fetched in this QA run. It means the manifest provides complete file IDs, and sampled file-ID based fetches succeed.

---

## 6. Relationship To S2

S2 local manifest route:

```text
PASS_WITH_WARNINGS
```

Drive file-id manifest route:

```text
PASS
```

S2 source upgrade:

```text
AVAILABLE
```

Meaning:

```text
Future Drive-side hydration, spot checks, or raw JSON shallow probes should use the Drive manifest file IDs instead of connector folder search.
```

Remaining S2 warning:

```text
The local manifest route still recorded one parse failure for run_failed_items.json. This is a special file, not a blocker for A-W raw level coverage.
```

---

## 7. Current S2B Verdict

```text
RAZ-AW-S2B verdict: PASS
```

Next recommended task:

```text
RAZ-AW-S2C_DriveManifestHydrationTooling
```

Purpose:

```text
Create tooling that consumes manifest.json and can fetch selected or full Drive raw JSON files by file_id for shallow schema QA without relying on folder search.
```

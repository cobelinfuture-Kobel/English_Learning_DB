# RAZ-AW-S2E Local Hydration Level QA Operator Run

## 1. Preflight

Task:

```text
RAZ-AW-S2E_LocalHydrationLevelQA
```

Scope:

```text
LOCAL FULL-LEVEL HYDRATION QA
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
RAZ-AW-S2D_LocalHydrationSampleQA
```

S2D result:

```text
status: PASS
selected_record_count: 69
fetch_success_count: 69
json_parse_status_counts: PASS=69
levels_missing: []
warnings: []
blockers: []
```

Files created by this task:

```text
docs/raz/RAZ_AW_S2E_LOCAL_HYDRATION_LEVEL_QA_OPERATOR_RUN.md
tools/raz_aw_local_hydration_level_qa.py
reports/raz/local_hydration_level_qa.status.json
```

Risk level:

```text
Low
```

---

## 2. Purpose

S2D sampled first / middle / last files per A-W level.

S2E performs a fuller readback on selected complete levels, defaulting to:

```text
Level_A
Level_W
```

Reason:

```text
Level_A checks the earliest/simple raw format.
Level_W checks the latest/longest/highest raw format.
Together they provide low/high boundary QA before any full A-W hydration.
```

---

## 3. Local Tool

Tool:

```text
tools/raz_aw_local_hydration_level_qa.py
```

Default command:

```powershell
cd G:\HomeWork\English_Learning_DB
git pull
python tools\raz_aw_local_hydration_level_qa.py --raw-root G:\HomeWork\English_Learning_DB\raz_output_jsons --levels A W
```

Alternative command for a single level:

```powershell
python tools\raz_aw_local_hydration_level_qa.py --raw-root G:\HomeWork\English_Learning_DB\raz_output_jsons --levels A
```

Alternative command for more levels:

```powershell
python tools\raz_aw_local_hydration_level_qa.py --raw-root G:\HomeWork\English_Learning_DB\raz_output_jsons --levels A M W
```

Expected outputs:

```text
reports/raz/local_hydration_level_qa_report.json
reports/raz/local_hydration_level_qa_summary.json
```

Only commit these two files:

```powershell
git add reports\raz\local_hydration_level_qa_report.json `
        reports\raz\local_hydration_level_qa_summary.json

git commit -m "reports: add local RAZ AW hydration level QA"
git push
```

Do not run:

```powershell
git add .
```

---

## 4. Safety Contract

Allowed output:

```text
level
book_id
filename
relative_path
size_bytes
json_parse_status
source_type
extraction_method
extractor_version
story page counts
sentence_candidate_count
page_unit_count
reuse_candidate_count
excluded_item_count
legacy_story_sentence_count
authority_status
generated_content
raw_audio_fields_preserved
final_should_remove_audio_fields
```

Forbidden output:

```text
sentence text
page text
legacy_story_sentences text
sentence_candidates payload
page_units payload
reuse_unit_candidates payload
word trace
audio trace
raw text
image/media payloads
```

---

## 5. Expected Evaluation

For default `--levels A W`, expected approximate record count:

```text
Level_A: 100
Level_W: 100
Total: 200
```

Expected pass condition:

```text
status: PASS
selected_record_count > 0
fetch_success_count == selected_record_count
json_parse_status_counts: PASS only
levels_missing: []
warnings: []
blockers: []
```

Warnings are acceptable if documented, but any raw text emission or raw JSON commit remains a blocker.

---

## 6. Current Status

```text
S2E tooling: PASS
S2E report generation: WAITING_FOR_OPERATOR_RUN
S2F full A-W hydration: NOT READY UNTIL S2E REPORTS PASS
```

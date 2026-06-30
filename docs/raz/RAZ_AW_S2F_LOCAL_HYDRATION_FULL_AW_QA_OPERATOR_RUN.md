# RAZ-AW-S2F Local Hydration Full A-W QA Operator Run

## 1. Preflight

Task:

```text
RAZ-AW-S2F_LocalHydrationFullAWQA
```

Scope:

```text
LOCAL FULL A-W HYDRATION QA
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

Upstream dependencies:

```text
RAZ-AW-S2D_LocalHydrationSampleQA
RAZ-AW-S2E_LocalHydrationLevelQA
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

S2E result:

```text
status: PASS
requested_levels: A, W
selected_record_count: 200
fetch_success_count: 200
json_parse_status_counts: PASS=200
levels_missing: []
warnings: []
blockers: []
```

Files created by this task:

```text
docs/raz/RAZ_AW_S2F_LOCAL_HYDRATION_FULL_AW_QA_OPERATOR_RUN.md
tools/raz_aw_local_hydration_full_aw_qa.py
reports/raz/local_hydration_full_aw_qa.status.json
```

Risk level:

```text
Low
```

---

## 2. Purpose

S2F performs shallow QA over all raw A-W level JSON files from the local raw mirror.

Expected count from S2B:

```text
1959 raw level JSON files
```

S2F does not include special files such as:

```text
raz_output_jsons/run_failed_items.json
raz_output_jsons/run_summary.json
```

Those are not raw level book JSON files.

---

## 3. Local Tool

Tool:

```text
tools/raz_aw_local_hydration_full_aw_qa.py
```

Command:

```powershell
cd G:\HomeWork\English_Learning_DB
git pull
python tools\raz_aw_local_hydration_full_aw_qa.py --raw-root G:\HomeWork\English_Learning_DB\raz_output_jsons
```

Expected outputs:

```text
reports/raz/local_hydration_full_aw_qa_report.json
reports/raz/local_hydration_full_aw_qa_summary.json
```

Only commit these two files:

```powershell
git add reports\raz\local_hydration_full_aw_qa_report.json `
        reports\raz\local_hydration_full_aw_qa_summary.json

git commit -m "reports: add local RAZ AW full hydration QA"
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
aggregate source/extractor/status counts
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

Expected pass condition:

```text
status: PASS
selected_record_count: 1959
fetch_success_count: 1959
json_parse_status_counts: PASS only
levels_missing: []
level_json_mismatch_count: 0
book_id_mismatch_count: 0
generated_content_true_count: 0
warnings: []
blockers: []
```

Warnings are acceptable if documented, but any raw text emission or raw JSON commit remains a blocker.

---

## 6. Current Status

```text
S2F tooling: PASS
S2F report generation: WAITING_FOR_OPERATOR_RUN
S2G downstream transition: NOT READY UNTIL S2F REPORTS PASS
```

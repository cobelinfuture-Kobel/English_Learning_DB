# RAZ-AW-S2D Local Hydration Sample QA Operator Run

## 1. Preflight

Task:

```text
RAZ-AW-S2D_LocalHydrationSampleQA
```

Reason for route change:

```text
The Google Apps Script sample hydration path is operationally inconvenient for this stage. The task is switched to a local raw mirror sample QA path.
```

Scope:

```text
LOCAL SAMPLE HYDRATION QA
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

Files created by this route-change task:

```text
docs/raz/RAZ_AW_S2D_LOCAL_HYDRATION_SAMPLE_QA_OPERATOR_RUN.md
tools/raz_aw_local_hydration_sample_qa.py
```

Risk level:

```text
Low
```

---

## 2. Local Tool

Tool:

```text
tools/raz_aw_local_hydration_sample_qa.py
```

Purpose:

```text
Select first / middle / last raw JSON per A-W level from local raz_output_jsons.
Shallow-parse each selected JSON.
Emit sanitized QA reports only.
```

Expected sample count:

```text
23 levels × 3 sample files per level = 69 records
```

---

## 3. Operator Command

Run from repository root:

```powershell
cd G:\HomeWork\English_Learning_DB
git pull
python tools\raz_aw_local_hydration_sample_qa.py --raw-root G:\HomeWork\English_Learning_DB\raz_output_jsons
```

Expected outputs:

```text
reports/raz/local_hydration_sample_qa_report.json
reports/raz/local_hydration_sample_qa_summary.json
```

Only commit these two files:

```powershell
git add reports\raz\local_hydration_sample_qa_report.json `
        reports\raz\local_hydration_sample_qa_summary.json

git commit -m "reports: add local RAZ AW hydration sample QA"
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

## 5. Current Status

```text
Local S2D tooling: PASS
Local S2D report generation: WAITING_FOR_OPERATOR_RUN
Cloud Apps Script S2D path: DEFERRED
```

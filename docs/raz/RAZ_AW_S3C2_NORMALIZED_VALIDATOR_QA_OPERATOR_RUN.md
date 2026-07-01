# RAZ-AW-S3C2 Normalized Validator QA Operator Run

## 1. Task

```text
RAZ-AW-S3C2_NormalizedValidatorQA
```

Scope:

```text
NORMALIZED VALIDATOR QA TOOLING
LOCAL DERIVED INPUT
SANITIZED REPORT OUTPUT ONLY
NO RAW DATA MUTATION
NO RAW DATA COMMIT
NO TEXT-BEARING REPORTS
NO ENRICHED BUILD
NO AUTHORITY PROMOTION
NO GENERATION
NO RUNTIME/API CHANGE
```

Files created by this task:

```text
tools/raz_aw_validate_normalized.py
reports/raz/normalized_validator_qa_status.json
```

---

## 2. Validator Coverage

The validator checks:

```text
file presence for A-W
schema_version contracts
required fields and stable ID patterns
candidate_only / candidate_normalized / not_promoted boundaries
source_ref presence and source_layer correctness
sentence field existence without emitting values
page/reuse sentence_uid reference resolution
count reconciliation against build summary
dominant extraction path = $.cleaned_candidate
forbidden payload/status leakage
```

---

## 3. Local Run Command

```powershell
cd G:\HomeWork\English_Learning_DB
git pull
python tools\raz_aw_validate_normalized.py --derived-root G:\HomeWork\English_Learning_DB\raz_output_jsons\derived --build-summary reports\raz\raz_aw_normalized_build_summary.json
```

---

## 4. Expected Report Outputs

```text
reports/raz/raz_aw_normalized_validator_qa_report.json
reports/raz/raz_aw_normalized_schema_validation_summary.json
reports/raz/raz_aw_normalized_reference_validation_summary.json
reports/raz/raz_aw_normalized_validator_safety_report.json
```

---

## 5. Commit Policy

```powershell
git add reports\raz\raz_aw_normalized_validator_qa_report.json `
        reports\raz\raz_aw_normalized_schema_validation_summary.json `
        reports\raz\raz_aw_normalized_reference_validation_summary.json `
        reports\raz\raz_aw_normalized_validator_safety_report.json

git commit -m "reports: add RAZ AW normalized validator QA"
git push
```

Do not run:

```powershell
git add .
```

Do not commit:

```text
raz_output_jsons/derived/Level_*/normalized/*.json
raw RAZ files
full normalized sentence corpus
full text-bearing derived corpora
scratch dumps
```

---

## 6. Expected PASS Conditions

```text
status: PASS
actual_totals.book_count: 1959
actual_totals.sentence_count: 201993
actual_totals.page_unit_count: 22632
actual_totals.reuse_unit_count: 19332
issue_counts: {}
forbidden_key_counts: {}
forbidden_status_counts: {}
blockers: []
```

Next after successful report inspection:

```text
RAZ-AW-S3C3_NormalizedCandidateLayerCloseout
```

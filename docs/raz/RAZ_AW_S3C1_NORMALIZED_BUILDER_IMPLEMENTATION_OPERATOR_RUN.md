# RAZ-AW-S3C1 Normalized Builder Implementation Operator Run

## 1. Preflight

Task:

```text
RAZ-AW-S3C1_NormalizedBuilderImplementation
```

Scope:

```text
NORMALIZED BUILDER IMPLEMENTATION
LOCAL RAW MIRROR INPUT
LOCAL / DRIVE-DERIVED TEXT-BEARING OUTPUT ONLY
SANITIZED GITHUB SUMMARY OUTPUT ONLY
NO RAW RAZ JSON MUTATION
NO RAW RAZ JSON COMMIT
NO FULL RAW TEXT IN GITHUB REPORTS
NO ENRICHED BUILD EXECUTION
NO CONTENT AUTHORITY PROMOTION
NO TAG AUTHORITY PROMOTION
NO GRAMMAR / VOCABULARY / PATTERN AUTHORITY LINKAGE APPROVAL
NO READING / DIALOGUE / EXERCISE GENERATION
NO RUNTIME / API / SCHEDULER / DASHBOARD CHANGE
```

Upstream dependencies:

```text
RAZ-AW-S2G_FullAWHydrationReadbackCloseout: PASS
RAZ-AW-S3_RawHydrationToNormalizedEnrichedReadinessDesignScan: PASS
RAZ-AW-S3A_NormalizedEnrichedSchemaContractDesign: PASS
RAZ-AW-S3B_NormalizedBuilderStorageDecisionAndImplementationPlan: PASS
```

Files created by this task:

```text
tools/raz_aw_build_normalized_from_raw.py
docs/raz/RAZ_AW_S3C1_NORMALIZED_BUILDER_IMPLEMENTATION_OPERATOR_RUN.md
reports/raz/normalized_builder_implementation_status.json
```

Risk level:

```text
Medium-Low
```

Reason:

```text
The builder reads local raw JSON and writes text-bearing normalized derived artifacts locally, but GitHub commit policy remains summary-only.
```

---

## 2. Local Run Command

Run from repository root:

```powershell
cd G:\HomeWork\English_Learning_DB
git pull
python tools\raz_aw_build_normalized_from_raw.py --raw-root G:\HomeWork\English_Learning_DB\raz_output_jsons --derived-root G:\HomeWork\English_Learning_DB\raz_output_jsons\derived
```

---

## 3. Expected Local Derived Outputs

Text-bearing normalized artifacts are written under:

```text
G:\HomeWork\English_Learning_DB\raz_output_jsons\derived\Level_A\normalized
...
G:\HomeWork\English_Learning_DB\raz_output_jsons\derived\Level_W\normalized
```

Each level should contain:

```text
raz_<LEVEL>_normalized_books.json
raz_<LEVEL>_normalized_sentences.json
raz_<LEVEL>_normalized_page_units.json
raz_<LEVEL>_normalized_reuse_units.json
```

These files are not for GitHub commit.

---

## 4. Expected GitHub-Safe Outputs

The builder emits sanitized reports:

```text
reports/raz/raz_aw_normalized_build_summary.json
reports/raz/raz_aw_normalized_safety_report.json
reports/raz/raz_aw_normalized_count_reconciliation_summary.json
```

These reports must not contain full sentence text or raw payloads.

---

## 5. Commit Policy

After local run, commit only:

```powershell
git add reports\raz\raz_aw_normalized_build_summary.json `
        reports\raz\raz_aw_normalized_safety_report.json `
        reports\raz\raz_aw_normalized_count_reconciliation_summary.json

git commit -m "reports: add RAZ AW normalized build summaries"
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
scratch data dumps
```

---

## 6. Expected PASS Conditions

```text
status: PASS or PASS_WITH_WARNINGS
normalized_book_count: 1959
normalized_sentence_count > 0
raw_mutation: false
raw_commit_allowed: false
contains_raw_text: false in GitHub reports
content_authority_status: not_promoted
authority_status: candidate_only
review_status: pending
```

Warnings are acceptable if they are explicit exclusion counts. A `BLOCKED` status means the normalized candidate layer is not ready for validator QA.

---

## 7. Next Task

After reports are pushed and inspected:

```text
RAZ-AW-S3C2_NormalizedValidatorQA
```

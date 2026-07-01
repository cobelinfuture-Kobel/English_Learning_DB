# RAZ-AW-S3C1B Cleaned Candidate Text Mapping Fix

## 1. Preflight

Task:

```text
RAZ-AW-S3C1B_CleanedCandidateTextMappingFix
```

Trigger:

```text
S3C1A rerun produced normalized_sentence_count > 0, but sentence_extraction_path_counts showed $.text_type as the dominant source path.
```

Scope:

```text
PATCH SENTENCE TEXT SOURCE PRIORITY ONLY
NO RAW JSON MUTATION
NO RAW JSON COMMIT
NO TEXT-BEARING GITHUB REPORTS
NO ENRICHED BUILD
NO AUTHORITY PROMOTION
NO GENERATION
NO RUNTIME/API CHANGE
```

Files changed:

```text
tools/raz_aw_build_normalized_from_raw.py
reports/raz/cleaned_candidate_text_mapping_fix_status.json
```

---

## 2. Fix Summary

The builder now treats `cleaned_candidate` as the highest-priority sentence text field.

It also blocks classification/status/id fields from being selected as sentence text:

```text
text_type
source_type
authority_status
promotion_status
review_status
candidate_id
page_unit_id
book_page_id
book_id
level
title
```

The build summary now warns if the dominant extraction path is not:

```text
$.cleaned_candidate
```

---

## 3. Operator Rerun

Run from repository root:

```powershell
cd G:\HomeWork\English_Learning_DB
git pull
python tools\raz_aw_build_normalized_from_raw.py --raw-root G:\HomeWork\English_Learning_DB\raz_output_jsons --derived-root G:\HomeWork\English_Learning_DB\raz_output_jsons\derived
```

Expected result:

```text
status: PASS
normalized_book_count: 1959
normalized_sentence_count: 201996
blockers: []
sentence_extraction_path_counts dominant path: $.cleaned_candidate
```

---

## 4. Commit Policy

Commit only sanitized reports:

```powershell
git add reports\raz\raz_aw_normalized_build_summary.json `
        reports\raz\raz_aw_normalized_safety_report.json `
        reports\raz\raz_aw_normalized_count_reconciliation_summary.json

git commit -m "reports: refresh RAZ AW normalized build with cleaned candidate mapping"
git push
```

Do not commit:

```text
raz_output_jsons/derived/Level_*/normalized/*.json
raw RAZ files
full text-bearing derived corpora
scratch dumps
```

---

## 5. Next Gate

If rerun confirms `$.cleaned_candidate` and no blockers:

```text
RAZ-AW-S3C2_NormalizedValidatorQA
```

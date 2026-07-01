# RAZ-AW-S3C1A Normalized Sentence Extraction Mapping Fix

## 1. Preflight

Task:

```text
RAZ-AW-S3C1A_NormalizedSentenceExtractionMappingFix
```

Trigger:

```text
S3C1 returned BLOCKED.
normalized_book_count: 1959
normalized_sentence_count: 0
blocker: no_normalized_sentences_generated
main exclusion reason: text_missing_or_not_string
```

Scope:

```text
PATCH BUILDER MAPPING ONLY
LOCAL RAW MIRROR INPUT ONLY DURING OPERATOR RERUN
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
tools/raz_aw_probe_sentence_candidate_shape.py
reports/raz/normalized_sentence_extraction_mapping_fix_status.json
```

---

## 2. Fix Summary

The builder now uses guarded structural extraction instead of shallow field lookup only.

Changes:

```text
recursive candidate text extraction with depth guard
additional candidate text aliases
guarded string-list support for token-like lists
skip rules for audio / timing / trace / image structures
sanitized sentence_extraction_path_counts in build summary
```

The probe tool inspects key paths and value types only. It does not emit text values.

---

## 3. Operator Rerun

Optional probe:

```powershell
cd G:\HomeWork\English_Learning_DB
git pull
python tools\raz_aw_probe_sentence_candidate_shape.py --raw-root G:\HomeWork\English_Learning_DB\raz_output_jsons --sample-per-level 2
```

Rerun builder:

```powershell
python tools\raz_aw_build_normalized_from_raw.py --raw-root G:\HomeWork\English_Learning_DB\raz_output_jsons --derived-root G:\HomeWork\English_Learning_DB\raz_output_jsons\derived
```

---

## 4. Commit Policy

Commit only sanitized reports:

```powershell
git add reports\raz\raz_aw_normalized_build_summary.json `
        reports\raz\raz_aw_normalized_safety_report.json `
        reports\raz\raz_aw_normalized_count_reconciliation_summary.json
```

If probe report is needed:

```powershell
git add reports\raz\raz_aw_sentence_candidate_shape_probe.json
```

Then:

```powershell
git commit -m "reports: refresh RAZ AW normalized build after sentence mapping fix"
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

## 5. Expected Result

```text
status: PASS or PASS_WITH_WARNINGS
normalized_book_count: 1959
normalized_sentence_count > 0
blockers: []
contains_raw_text: false in GitHub reports
raw_commit_allowed: false
```

Next after successful rerun:

```text
RAZ-AW-S3C2_NormalizedValidatorQA
```

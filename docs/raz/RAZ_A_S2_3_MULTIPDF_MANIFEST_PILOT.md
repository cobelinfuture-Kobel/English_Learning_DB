# RAZ-A-S2.3 MultiPDF Manifest Pilot

## 1. Task Name

RAZ-A-S2.3_MultiPDFManifestPilot

## 2. Date/Time

- Run date: 2026-06-20
- Runtime command completed at: 2026-06-20 01:11:48

## 3. Files Modified

- `input/manifest/raz_a_books_manifest.xlsx`

## 4. Files Created

- `docs/raz/RAZ_A_S2_3_MULTIPDF_MANIFEST_PILOT.md`
- `output/json/reference_duplicate_groups.json`

## 5. Manifest Rows Used

| book_id | book_no | book_title | pdf_file |
|---|---:|---|---|
| RAZ_A_001 | 1 | Vegetables | `a/01_Vegetables_Password_Removed.pdf` |
| RAZ_A_002 | 2 | I Go | `a/02_I Go_Password_Removed.pdf` |
| RAZ_A_003 | 3 | Bird Goes Home | `a/03_Bird Goes Home_Password_Removed.pdf` |

All rows used:

- `raz_level = A`
- `audio_file = blank`
- `source_note = reference_only`

## 6. Runtime Command

```bash
python tools/raz/build_raz_a_reference_sentences.py
```

Result:

- Success
- Extractor used: `pdfplumber_v0.1`

## 7. Output Files Verified

- `output/excel/raz_a_reference_sentences.xlsx`
- `output/json/pages_raw.json`
- `output/json/sentences_v01.json`
- `output/json/reference_duplicate_groups.json`
- `output/json/extraction_report.json`
- `output/logs/extraction_log.txt`

## 8. Excel Sheets Verified

- `README`
- `books`
- `pages_raw`
- `sentences_v01`
- `sentence_qc`
- `reference_duplicate_groups`
- `book_summary`
- `extraction_report`
- `decision_rules`

## 9. Batch Extraction Summary

| Metric | Value |
|---|---:|
| total_books | 3 |
| processed_pdf_count | 3 |
| failed_pdf_count | 0 |
| total_pages | 36 |
| total_sentences | 222 |
| reference_sentence_count | 68 |
| excluded_sentence_count | 154 |
| unique_reference_sentence_count | 34 |
| duplicate_reference_sentence_count | 34 |
| reference_duplicate_group_count | 18 |
| max_reference_occurrence_count | 4 |
| sentence_qc rows | 154 |
| extraction_report.status | `completed_with_warnings` |

## 10. Per-Book Extraction Summary

| book_id | book_title | pages | sentence_count | reference_sentence_count | unique_reference_sentence_count | duplicate_reference_sentence_count | excluded_sentence_count | reference_duplicate_group_count | extraction_status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| RAZ_A_001 | Vegetables | 12 | 74 | 32 | 8 | 24 | 42 | 8 | `needs_review` |
| RAZ_A_002 | I Go | 12 | 74 | 18 | 13 | 5 | 56 | 5 | `needs_review` |
| RAZ_A_003 | Bird Goes Home | 12 | 74 | 18 | 13 | 5 | 56 | 5 | `needs_review` |

## 11. Multi-Book Integrity Checks

| Check | Result |
|---|---|
| `extraction_report.total_books == manifest row count` | PASS |
| `processed_pdf_count == successfully processed PDFs` | PASS |
| `book_summary` has one row per processed book | PASS |
| `sentence_id` values are unique | PASS |
| every sentence row has valid manifest `book_id` | PASS |
| non-empty `reference_group_id` starts with its own `book_id` | PASS |
| no cross-book duplicate merge in `reference_duplicate_groups` | PASS |
| per-book `reference_sentence_count = unique_reference_sentence_count + duplicate_reference_sentence_count` | PASS |
| batch `reference_sentence_count = unique_reference_sentence_count + duplicate_reference_sentence_count` | PASS |
| batch `total_sentences = reference_sentence_count + excluded_sentence_count` | PASS |

## 12. QC Routing Checks

| Check | Result |
|---|---|
| every `sentence_boundary_status != clean` row is in `sentence_qc` | PASS |
| every `include_in_reference == false` row is in `sentence_qc` | PASS |
| duplicate-only rows are not added to QC merely because they are duplicates | PASS |

## 13. Policy Confirmation

- OCR was not executed.
- Audio was not processed.
- No RAZ data was imported into Sentence Authority, Reading Authority, Dialogue Authority, Worksheet Authority, Assessment Authority, or ULGA.
- Extracted data remains `external_reference_only` / `reference_only`.

## 14. Issues Found

- Batch status remained `completed_with_warnings`, which is expected for RAZ booklet-style PDFs with cover matter, credits, URLs, layout artifacts, and repeated booklet text.
- All three pilot PDFs produced `needs_review` at book level because a substantial portion of extracted rows were excluded noise or non-clean segments.
- The current noise filter remains first-match based, so mixed-noise rows may be categorized by the earliest matching rule rather than the most semantically specific rule.
- No structural multi-book integrity issue was found in manifest handling, sentence IDs, reference group scoping, or duplicate grouping.

## 15. Recommendation

The system can proceed to `RAZ-A-S2.4_LargerASetPilot`.

Reason:

- Multi-book manifest processing worked correctly.
- Batch and per-book metrics were internally consistent.
- Duplicate reference groups stayed scoped to each book.
- QC routing remained correct and did not inflate from duplicate-only reference rows.

## S2.3.1 Mirrored Text Patch Follow-Up

### Why the patch was needed

S2.3 revealed mirrored / reversed / rotated booklet text in several PDFs. These rows were structurally extracted but were not valid forward reading content and some were still affecting reference metrics.

### What detection was added

- mirrored / reversed URL fragment detection
- mirrored benchmark / footer marker detection
- mirrored credit / author marker detection
- mirrored sentence-like publisher/footer detection
- explicit exclusion role: `mirrored_text_artifact`
- explicit exclusion reason: `mirrored_or_rotated_text`

### Before / After Batch Metrics

| Metric | S2.3 Before | S2.3.1 After |
|---|---:|---:|
| total_sentences | 222 | 222 |
| reference_sentence_count | 68 | 48 |
| excluded_sentence_count | 154 | 174 |
| unique_reference_sentence_count | 34 | 24 |
| duplicate_reference_sentence_count | 34 | 24 |
| reference_duplicate_group_count | 18 | 8 |
| sentence_qc rows | 154 | 174 |
| extraction_report.status | `completed_with_warnings` | `completed_with_warnings` |

### Follow-Up Verification

- Reversed rows were excluded from reference use.
- Reversed rows were routed to `sentence_qc`.
- Reversed markers no longer remained in `reference_duplicate_groups`.
- Forward body-text rows still remained included.
- S2.2 duplicate policy and S2.3 multi-book integrity checks still passed.

### Remaining Warnings

- Some mirrored rows are classified as `url_fragment` rather than `mirrored_text_artifact` when explicit URL markers are also present. This is acceptable under the current priority rules because they remain excluded.
- Batch status remains `completed_with_warnings`, which is expected for booklet-style RAZ PDFs with mixed cover matter, layout artifacts, and mirrored text in the text layer.

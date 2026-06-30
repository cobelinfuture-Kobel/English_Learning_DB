# RAZ-A-S2.4 Larger A-Set Pilot

## 1. Task Name

RAZ-A-S2.4_LargerASetPilot

## 2. Date/Time

- Run date: 2026-06-20
- Runtime command completed at: 2026-06-20 01:43:00

## 3. Files Modified

- `input/manifest/raz_a_books_manifest.xlsx`

## 4. Files Created

- `docs/raz/RAZ_A_S2_4_LARGER_A_SET_PILOT.md`

## 5. Selected PDF Count

- Selected PDF count: 10

## 6. Selected Filenames

- `01_Vegetables_Password_Removed.pdf`
- `02_I Go_Password_Removed.pdf`
- `03_Bird Goes Home_Password_Removed.pdf`
- `04_Fruit_Password_Removed.pdf`
- `05_My Room_Password_Removed.pdf`
- `06_He Runs_Password_Removed.pdf`
- `07_Baby Animals_Password_Removed.pdf`
- `08_In And Out_Password_Removed.pdf`
- `09_My Hair_Password_Removed.pdf`
- `10_I Can_Password_Removed.pdf`

## 7. Manifest Rows Used

| book_id | book_no | book_title | pdf_file |
|---|---:|---|---|
| RAZ_A_001 | 1 | Vegetables | `a/01_Vegetables_Password_Removed.pdf` |
| RAZ_A_002 | 2 | I Go | `a/02_I Go_Password_Removed.pdf` |
| RAZ_A_003 | 3 | Bird Goes Home | `a/03_Bird Goes Home_Password_Removed.pdf` |
| RAZ_A_004 | 4 | Fruit | `a/04_Fruit_Password_Removed.pdf` |
| RAZ_A_005 | 5 | My Room | `a/05_My Room_Password_Removed.pdf` |
| RAZ_A_006 | 6 | He Runs | `a/06_He Runs_Password_Removed.pdf` |
| RAZ_A_007 | 7 | Baby Animals | `a/07_Baby Animals_Password_Removed.pdf` |
| RAZ_A_008 | 8 | In And Out | `a/08_In And Out_Password_Removed.pdf` |
| RAZ_A_009 | 9 | My Hair | `a/09_My Hair_Password_Removed.pdf` |
| RAZ_A_010 | 10 | I Can | `a/10_I Can_Password_Removed.pdf` |

All rows used:

- `raz_level = A`
- `audio_file = blank`
- `source_note = reference_only`

## 8. Runtime Command

```bash
python tools/raz/build_raz_a_reference_sentences.py
```

Result:

- Success
- Extractor used: `pdfplumber_v0.1`

## 9. Output Files Verified

- `output/excel/raz_a_reference_sentences.xlsx`
- `output/json/pages_raw.json`
- `output/json/sentences_v01.json`
- `output/json/reference_duplicate_groups.json`
- `output/json/extraction_report.json`
- `output/logs/extraction_log.txt`

## 10. Excel Sheets Verified

- `README`
- `books`
- `pages_raw`
- `sentences_v01`
- `sentence_qc`
- `reference_duplicate_groups`
- `book_summary`
- `extraction_report`
- `decision_rules`

## 11. Batch Extraction Summary

| Metric | Value |
|---|---:|
| total_books | 10 |
| processed_pdf_count | 10 |
| failed_pdf_count | 0 |
| total_pages | 120 |
| total_sentences | 716 |
| reference_sentence_count | 262 |
| excluded_sentence_count | 454 |
| unique_reference_sentence_count | 90 |
| duplicate_reference_sentence_count | 172 |
| reference_duplicate_group_count | 60 |
| max_reference_occurrence_count | 4 |
| sentence_qc rows | 454 |
| extraction_report.status | `completed_with_warnings` |
| body_text rows | 262 |
| include_in_reference = true rows | 262 |
| include_in_unique_reference = true rows | 90 |

## 12. Per-Book Extraction Summary

| book_id | book_title | pages | sentence_count | reference_sentence_count | unique_reference_sentence_count | duplicate_reference_sentence_count | excluded_sentence_count | reference_duplicate_group_count | extraction_status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| RAZ_A_001 | Vegetables | 12 | 74 | 32 | 8 | 24 | 42 | 8 | `needs_review` |
| RAZ_A_002 | I Go | 12 | 74 | 8 | 8 | 0 | 66 | 0 | `needs_review` |
| RAZ_A_003 | Bird Goes Home | 12 | 74 | 8 | 8 | 0 | 66 | 0 | `needs_review` |
| RAZ_A_004 | Fruit | 12 | 70 | 32 | 8 | 24 | 38 | 8 | `needs_review` |
| RAZ_A_005 | My Room | 12 | 68 | 34 | 9 | 25 | 34 | 9 | `needs_review` |
| RAZ_A_006 | He Runs | 12 | 68 | 34 | 9 | 25 | 34 | 9 | `needs_review` |
| RAZ_A_007 | Baby Animals | 12 | 78 | 32 | 8 | 24 | 46 | 8 | `needs_review` |
| RAZ_A_008 | In And Out | 12 | 68 | 34 | 9 | 25 | 34 | 9 | `needs_review` |
| RAZ_A_009 | My Hair | 12 | 74 | 14 | 14 | 0 | 60 | 0 | `needs_review` |
| RAZ_A_010 | I Can | 12 | 68 | 34 | 9 | 25 | 34 | 9 | `needs_review` |

## 13. Integrity Checks

| Check | Result |
|---|---|
| `extraction_report.total_books == manifest row count` | PASS |
| `processed_pdf_count + failed_pdf_count = input_pdf_count` | PASS |
| `book_summary` has one row per processed book | PASS |
| all `sentence_id` values are unique | PASS |
| every sentence row has a valid manifest `book_id` | PASS |
| every non-empty `reference_group_id` starts with its own `book_id` | PASS |
| no `reference_duplicate_groups` row merges sentence IDs from different books | PASS |
| `reference_sentence_count = unique_reference_sentence_count + duplicate_reference_sentence_count` | PASS |
| `total_sentences = reference_sentence_count + excluded_sentence_count` | PASS |

## 14. Mirrored Text Regression Checks

| Check | Result |
|---|---|
| mirrored / reversed rows are not `body_text` + `include_in_reference = true` | PASS |
| mirrored / reversed rows remain excluded | PASS |
| no reversed marker remains in `reference_duplicate_groups.reference_text_key` | PASS |

## 15. QC Routing Checks

| Check | Result |
|---|---|
| all `sentence_boundary_status != clean` rows are in `sentence_qc` | PASS |
| all `include_in_reference == false` rows are in `sentence_qc` | PASS |
| duplicate-only rows are not added to QC merely because they are duplicate instances | PASS |

## 16. Policy Confirmation

- OCR was not executed.
- Audio was not processed.
- No RAZ data was imported into Sentence Authority, Reading Authority, Dialogue Authority, Worksheet Authority, Assessment Authority, or ULGA.
- Extracted data remains `external_reference_only` / `reference_only`.

## 17. Issues Found

- Batch status remained `completed_with_warnings`, which is expected for booklet-style RAZ PDFs with cover matter, credits, URLs, duplicate booklet text, and mirrored text in the PDF text layer.
- All 10 books are still flagged `needs_review` at book level because excluded/noisy rows remain a substantial share of extracted segments.
- Different books show materially different usable-reference yield. Some books retain strong repeated body-text patterns, while others lose many rows to mirrored/layout exclusion.
- The mirrored-text detector is heuristic. It performed correctly on this 10-book pilot, but a larger set may still reveal new reversed-token patterns or mixed-direction layout artifacts.

## 18. Recommendation

The system can proceed to `RAZ-A-S2.5_CrossLevelSmokePilot`.

Reason:

- Batch totals were internally consistent.
- `sentence_id` and `reference_group_id` scoping remained correct across 10 books.
- Mirrored / reversed text stayed excluded from usable reference rows and duplicate groups.
- Forward body-text rows remained preserved.
- QC routing remained stable and did not inflate from duplicate-only reference rows.

## S2.4.1 Front/Back Matter Title Contamination Patch Follow-Up

### Why the patch was needed

S2.4 revealed short title-like contamination rows on front/back matter pages. These rows looked sentence-like enough to pass the body-text filter and were contaminating reference rows and duplicate groups.

### What detection was added

- front/back matter page detection using page position
- page-context-aware front/back matter marker detection
- title-like contamination row detection on strong front/back matter pages
- front/back-only reference group suppression before duplicate grouping
- explicit exclusion role: `title_contamination_artifact`
- explicit exclusion reason: `front_back_matter_title_contamination`

### Before / After Batch Metrics

| Metric | S2.4 Before | S2.4.1 After |
|---|---:|---:|
| total_sentences | 716 | 716 |
| reference_sentence_count | 262 | 254 |
| excluded_sentence_count | 454 | 462 |
| unique_reference_sentence_count | 90 | 86 |
| duplicate_reference_sentence_count | 172 | 168 |
| reference_duplicate_group_count | 60 | 56 |
| sentence_qc rows | 454 | 462 |
| extraction_report.status | `completed_with_warnings` | `completed_with_warnings` |

### Follow-Up Verification

- Front/back matter title-contamination rows were excluded from reference use.
- Excluded contamination rows were routed to `sentence_qc`.
- Front/back-only duplicate groups were removed before reference grouping.
- No front/back matter body-text reference rows remained.
- Mirrored-text regression still passed.
- Core integrity checks still passed.

### Remaining Warnings

- Batch status remains `completed_with_warnings`, which is expected for booklet-style RAZ PDFs with front/back matter, mirrored text, URLs, and layout artifacts.
- Some body pages still contain mixed-direction text-layer anomalies in certain books. They did not break the current S2.4.1 checks, but they remain a data-quality risk worth monitoring in later pilots.

## S2.4.2 Directionality Reading-Order Layer Follow-Up

### Why the layer was needed

S2.4.1 removed front/back matter title contamination, but some body-page rows still contained PDF text-layer directionality anomalies. These rows mixed forward body text with reversed fragments or line-order interleaving and were still able to enter reference rows and duplicate groups.

### New fields added

- `text_direction_status`
- `directionality_confidence`
- `directionality_reason`

These fields were added to:

- `sentences_v01.json`
- Excel `sentences_v01`
- Excel `sentence_qc`

### Directionality statuses supported

- `forward_clean`
- `reversed_text`
- `mixed_direction`
- `rotated_or_mirrored`
- `reading_order_interleaved`
- `unknown_direction`
- `not_applicable`

### Before / After Batch Metrics

| Metric | S2.4.1 Before | S2.4.2 After |
|---|---:|---:|
| total_sentences | 716 | 716 |
| reference_sentence_count | 254 | 243 |
| excluded_sentence_count | 462 | 473 |
| unique_reference_sentence_count | 86 | 78 |
| duplicate_reference_sentence_count | 168 | 165 |
| reference_duplicate_group_count | 56 | 55 |
| sentence_qc rows | 462 | 473 |
| extraction_report.status | `completed_with_warnings` | `completed_with_warnings` |

### Verification

- All reference rows now require `text_direction_status = forward_clean`.
- Directionally unsafe rows are excluded from reference use and routed to `sentence_qc`.
- `reference_duplicate_groups.json` contains only rows whose source sentences remain `include_in_reference = true` and `text_direction_status = forward_clean`.
- Known mixed-direction false positives from `RAZ_A_009 / My Hair` were removed from reference use and duplicate grouping.
- Valid forward body-text rows from `RAZ_A_009 / My Hair` remain included.
- Mirrored/reversed publisher/footer exclusion still passed.
- Front/back matter title-contamination exclusion still passed.
- Sentence ID uniqueness, book scoping, duplicate metrics, and QC routing still passed.

### Remaining Warnings

- Batch status remains `completed_with_warnings`, which is expected for booklet-style PDFs with mirrored text, layout noise, and front/back matter.
- Directionality detection remains heuristic and score-based. This is intentional for a minimal patch, but a larger future batch may expose new reversed-token variants that need added markers.
- A small number of rows remain in conservative safety buckets such as `reading_order_interleaved` and `unknown_direction`. They are preserved for audit and QC, but excluded from reference use by design.

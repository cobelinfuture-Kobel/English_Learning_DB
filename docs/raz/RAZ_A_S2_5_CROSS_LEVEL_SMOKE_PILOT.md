# RAZ-A-S2.5 Cross-Level Smoke Pilot

## 1. Task Name

RAZ-A-S2.5_CrossLevelSmokePilot

## 2. Date/Time

- Run date: 2026-06-20
- Runtime command completed at: 2026-06-20 10:28:12

## 3. Files Modified

- `input/manifest/raz_a_books_manifest.xlsx`

## 4. Files Created

- `docs/raz/RAZ_A_S2_5_CROSS_LEVEL_SMOKE_PILOT.md`

## 5. Builder Naming Note

- This smoke test intentionally used the existing A-named builder: `tools/raz/build_raz_a_reference_sentences.py`
- The output workbook remains `output/excel/raz_a_reference_sentences.xlsx`
- This is a temporary smoke-test use of the A builder across A/B/C/D/E/F
- Generic RAZ builder naming is deferred to a later task

## 6. Selected Level Coverage

- Levels attempted: `A B C D E F`
- Levels found: `A B C D E F`
- Selection status: full planned 11-PDF smoke set achieved

| Level | Selected PDF Count | Notes |
|---|---:|---|
| A | 3 | Used requested regression baseline set |
| B | 2 | First two sorted `_Password_Removed.pdf` files |
| C | 2 | First two sorted `_Password_Removed.pdf` files |
| D | 2 | First two sorted `_Password_Removed.pdf` files |
| E | 1 | First sorted available PDF |
| F | 1 | First sorted available PDF |

## 7. Selected PDF Filenames

- A: `01_Vegetables_Password_Removed.pdf`, `02_I Go_Password_Removed.pdf`, `09_My Hair_Password_Removed.pdf`
- B: `01_Valentines All Around_Password_Removed.pdf`, `02_Near and Far Away_Password_Removed.pdf`
- C: `C001_How Things Move_Password_Removed.pdf`, `C002_I Can Help_Password_Removed.pdf`
- D: `01_What to Wear_Password_Removed.pdf`, `02_Do Not Eat That!_Password_Removed.pdf`
- E: `A Day of Firsts.pdf`
- F: `A Clown Face.pdf`

## 8. Manifest Rows Used

| book_id | raz_level | book_no | book_title | pdf_file |
|---|---|---:|---|---|
| RAZ_A_001 | A | 1 | Vegetables | `a/01_Vegetables_Password_Removed.pdf` |
| RAZ_A_002 | A | 2 | I Go | `a/02_I Go_Password_Removed.pdf` |
| RAZ_A_003 | A | 3 | My Hair | `a/09_My Hair_Password_Removed.pdf` |
| RAZ_B_001 | B | 1 | Valentines All Around | `b/01_Valentines All Around_Password_Removed.pdf` |
| RAZ_B_002 | B | 2 | Near and Far Away | `b/02_Near and Far Away_Password_Removed.pdf` |
| RAZ_C_001 | C | 1 | How Things Move | `c/C001_How Things Move_Password_Removed.pdf` |
| RAZ_C_002 | C | 2 | I Can Help | `c/C002_I Can Help_Password_Removed.pdf` |
| RAZ_D_001 | D | 1 | What to Wear | `d/01_What to Wear_Password_Removed.pdf` |
| RAZ_D_002 | D | 2 | Do Not Eat That! | `d/02_Do Not Eat That!_Password_Removed.pdf` |
| RAZ_E_001 | E | 1 | A Day of Firsts | `e/A Day of Firsts.pdf` |
| RAZ_F_001 | F | 1 | A Clown Face | `f/A Clown Face.pdf` |

All rows used:

- `audio_file = blank`
- `source_note = reference_only`

## 9. Runtime Command

```bash
python tools/raz/build_raz_a_reference_sentences.py
```

Result:

- Success
- Extractor used: `pdfplumber_v0.1`

## 10. Output Files Verified

- `output/excel/raz_a_reference_sentences.xlsx`
- `output/json/pages_raw.json`
- `output/json/sentences_v01.json`
- `output/json/reference_duplicate_groups.json`
- `output/json/extraction_report.json`
- `output/logs/extraction_log.txt`

## 11. Excel Sheets Verified

- `README`
- `books`
- `pages_raw`
- `sentences_v01`
- `sentence_qc`
- `reference_duplicate_groups`
- `book_summary`
- `extraction_report`
- `decision_rules`

Directionality columns verified in `sentences_v01` and `sentence_qc`:

- `text_direction_status`
- `directionality_confidence`
- `directionality_reason`

## 12. Batch Extraction Summary

| Metric | Value |
|---|---:|
| input_pdf_count | 11 |
| processed_pdf_count | 11 |
| failed_pdf_count | 0 |
| total_books | 11 |
| total_pages | 138 |
| total_sentences | 658 |
| reference_sentence_count | 101 |
| excluded_sentence_count | 557 |
| unique_reference_sentence_count | 40 |
| duplicate_reference_sentence_count | 61 |
| reference_duplicate_group_count | 21 |
| max_reference_occurrence_count | 4 |
| sentence_qc rows | 557 |
| extraction_report.status | `completed_with_warnings` |

Smoke-test interpretation:

- `PASS_WITH_WARNINGS`

## 13. Per-Level Summary

| Level | selected_pdf_count | total_sentences | reference_sentence_count | excluded_sentence_count | unique_reference_sentence_count | duplicate_reference_sentence_count | reference_duplicate_group_count | unsafe_direction_row_count | mixed_direction_row_count | rotated_or_mirrored_row_count | reading_order_interleaved_row_count | unknown_direction_row_count | needs_review_sentence_count |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 3 | 222 | 47 | 175 | 23 | 24 | 8 | 74 | 13 | 42 | 1 | 18 | 109 |
| B | 2 | 148 | 48 | 100 | 12 | 36 | 12 | 0 | 0 | 0 | 0 | 0 | 63 |
| C | 2 | 85 | 4 | 81 | 4 | 0 | 0 | 15 | 0 | 12 | 0 | 0 | 64 |
| D | 2 | 203 | 2 | 201 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 79 |
| E | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| F | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## 14. Per-Book Summary

| book_id | raz_level | book_title | pages | sentence_count | reference_sentence_count | unique_reference_sentence_count | duplicate_reference_sentence_count | excluded_sentence_count | reference_duplicate_group_count | extraction_status |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| RAZ_A_001 | A | Vegetables | 12 | 74 | 32 | 8 | 24 | 42 | 8 | `needs_review` |
| RAZ_A_002 | A | I Go | 12 | 74 | 8 | 8 | 0 | 66 | 0 | `needs_review` |
| RAZ_A_003 | A | My Hair | 12 | 74 | 7 | 7 | 0 | 67 | 0 | `needs_review` |
| RAZ_B_001 | B | Valentines All Around | 12 | 80 | 32 | 8 | 24 | 48 | 8 | `needs_review` |
| RAZ_B_002 | B | Near and Far Away | 12 | 68 | 16 | 4 | 12 | 52 | 4 | `needs_review` |
| RAZ_C_001 | C | How Things Move | 12 | 42 | 0 | 0 | 0 | 42 | 0 | `needs_review` |
| RAZ_C_002 | C | I Can Help | 12 | 43 | 4 | 4 | 0 | 39 | 0 | `needs_review` |
| RAZ_D_001 | D | What to Wear | 12 | 87 | 2 | 1 | 1 | 85 | 1 | `needs_review` |
| RAZ_D_002 | D | Do Not Eat That! | 16 | 116 | 0 | 0 | 0 | 116 | 0 | `needs_review` |
| RAZ_E_001 | E | A Day of Firsts | 13 | 0 | 0 | 0 | 0 | 0 | 0 | `image_pdf_needs_ocr` |
| RAZ_F_001 | F | A Clown Face | 13 | 0 | 0 | 0 | 0 | 0 | 0 | `image_pdf_needs_ocr` |

## 15. Directionality Gate Checks

| Check | Result |
|---|---|
| every reference row is `body_text` | PASS |
| every reference row is `forward_clean` | PASS |
| unsafe direction rows are excluded | PASS |
| unsafe direction rows have empty `reference_group_id` | PASS |
| unsafe direction rows have `duplicate_reference_status = non_reference` | PASS |
| reference groups contain only `body_text + forward_clean + include_in_reference = true` rows | PASS |
| known A-level regression rows remain safe | PASS |
| valid forward body-text rows still included | PASS |

## 16. Reference Group Cleanliness Checks

| Check | Result |
|---|---|
| every non-empty `reference_group_id` starts with its own `book_id` | PASS |
| no reference group merges sentence IDs from different books | PASS |
| no unsafe direction row appears in `reference_duplicate_groups.json` | PASS |
| no non-body reference row appears in `reference_duplicate_groups.json` | PASS |

## 17. Cross-Level Anomaly Search

Directionality / reversed markers:

- Markers such as `slairetam`, `z-agnidaer`, `moc`, `koob`, `kramhcneb`, `gnidaer`, `detartsulli`, `yb nettirw`, `riah ym`, and `og i` were found in excluded audit rows.
- All matched rows remained `include_in_reference = false`.
- No matched directionality-marker row entered `reference_duplicate_groups.json`.

Front/back matter markers:

- Markers such as `photo credits`, `front cover`, `back cover`, `title page`, `correlation`, `fountas`, `pinnell`, `reading recovery`, `all rights reserved`, `written by`, `illustrated by`, `word count`, `benchmark`, `leveled book`, `level a` through `level e`, `www`, `123rf`, and `istockphoto` were found in excluded rows.
- All matched rows remained excluded from reference use.

Higher-level structure markers:

- No matches were found for `contents`, `table of contents`, `glossary`, `index`, `quiz`, `questions`, `activity`, `worksheet`, `chapter`, `introduction`, `caption`, `labels`, `diagram`, `map`, or `chart` in this 11-book smoke set.

## 18. Level-Aware Policy Observations

No level-aware policy was implemented in this task. Observations only:

| Level | too_long | medium_review | body_text + forward_clean + include_in_reference | forward_clean but excluded | Main exclusion signal for forward_clean excluded rows |
|---|---:|---:|---:|---:|---|
| B | 16 | 7 | 48 | 2 | `unknown_noise` |
| C | 12 | 9 | 4 | 8 | `unknown_noise` |
| D | 13 | 23 | 2 | 9 | `unknown_noise` |
| E | 0 | 0 | 0 | 0 | image-PDF / no text layer |
| F | 0 | 0 | 0 | 0 | image-PDF / no text layer |

Observations:

- The current A-level body-text rule appears workable for B, but increasingly conservative for C and D.
- C and D show many forward-looking rows excluded while still being `forward_clean`, usually falling to `unknown_noise` because the current inclusion rule is tightly coupled to short early-reader sentence patterns.
- C and D also show more `medium_review` and `too_long` rows, indicating that the current fixed `<= 8 words clean` assumption is too restrictive beyond A/B.
- E and F selected samples behaved like image PDFs in this workspace and produced `image_pdf_needs_ocr`; OCR remains intentionally disabled, so those levels could not be meaningfully assessed here.
- This smoke test supports a follow-up design task: `RAZ-S2.6_LevelAwareReferencePolicy_DesignScan`.

## 19. QC Routing Checks

| Check | Result |
|---|---|
| `sentence_qc` includes all rows with `sentence_boundary_status != clean` | PASS |
| `sentence_qc` includes all rows with `include_in_reference = false` | PASS |
| duplicate-only rows are not added to QC merely because they are duplicate instances | PASS |

Sampling summary by selected book:

- Every book was sampled for up to 10 reference rows and up to 10 excluded forward-clean / `medium_review` / `too_long` rows.
- A-level excluded samples were dominated by expected URL / copyright / mixed-direction audit rows.
- B-level excluded samples showed a small number of forward-clean rows falling into `unknown_noise`.
- C-level and D-level excluded samples showed repeated `forward_clean + unknown_noise` patterns, indicating likely over-exclusion under A-level heuristics.
- E/F had no sentence rows to sample because the selected files behaved as image PDFs.

## 20. Policy Confirmation

- OCR was not executed.
- Audio was not processed.
- No RAZ data was imported into Sentence Authority, Reading Authority, Dialogue Authority, Worksheet Authority, Assessment Authority, or ULGA.
- Extracted data remains `external_reference_only` / `reference_only`.

## 21. Issues Found

- The builder remained structurally safe, but cross-level recall drops sharply above B.
- `RAZ_C_001` and `RAZ_D_002` produced zero usable reference rows despite having extracted text, which strongly suggests the A-level sentence heuristic is too strict for some higher-level layouts/text lengths.
- E/F selected PDFs behaved as `image_pdf_needs_ocr`, limiting cross-level text-layer coverage even though the level folders existed.
- The current inclusion rule still depends on short-sentence punctuation and early-reader pattern matching, so valid forward rows at higher levels can be pushed into `unknown_noise`.
- Batch status remains `completed_with_warnings`, which is expected for this smoke test and consistent with the high excluded-row share.

## 22. Recommendation

Proceed to `RAZ-S2.6_LevelAwareReferencePolicy_DesignScan`.

Reason:

- Safety gates passed.
- Directionally unsafe rows stayed out of reference rows and reference groups.
- Front/back matter contamination stayed excluded.
- Duplicate grouping remained book-scoped.
- The main next problem is not a safety failure; it is level-aware recall and policy design for C/D and beyond.

## S2.5.1 Artifact Sync Re-Export

### Why this task was needed

S2.5 JSON outputs and report were already correct, but the uploaded/output Excel artifact was suspected to be stale. S2.5.1 was used to verify whether the workbook still reflected an older 10-book A-level run or the correct 11-book cross-level smoke run.

### Excel artifact result

- Normal workbook path: `output/excel/raz_a_reference_sentences.xlsx`
- Run-stamped workbook path: `output/excel/raz_reference_sentences_S2_5_RUN_20260620_022807.xlsx`
- JSON run_id used: `RUN_20260620_022807`
- Excel `extraction_report.run_id`: `RUN_20260620_022807`

### Workbook verification

- Workbook sheet verification: PASS
- Sheet list verified:
  - `README`
  - `books`
  - `pages_raw`
  - `sentences_v01`
  - `sentence_qc`
  - `reference_duplicate_groups`
  - `book_summary`
  - `extraction_report`
  - `decision_rules`

### Workbook dimension verification

| Sheet | Data Rows | Rows Including Header |
|---|---:|---:|
| books | 11 | 12 |
| pages_raw | 138 | 139 |
| sentences_v01 | 658 | 659 |
| sentence_qc | 557 | 558 |
| reference_duplicate_groups | 40 | 41 |
| book_summary | 11 | 12 |
| extraction_report | 1 | 2 |

### Directionality column verification

- `sentences_v01.text_direction_status`: PASS
- `sentences_v01.directionality_confidence`: PASS
- `sentences_v01.directionality_reason`: PASS
- `sentence_qc.text_direction_status`: PASS
- `sentence_qc.directionality_confidence`: PASS
- `sentence_qc.directionality_reason`: PASS

### Excel / JSON sync result

- `run_id`: PASS
- `input_pdf_count`: PASS
- `processed_pdf_count`: PASS
- `failed_pdf_count`: PASS
- `total_books`: PASS
- `total_pages`: PASS
- `total_sentences`: PASS
- `reference_sentence_count`: PASS
- `excluded_sentence_count`: PASS
- `unique_reference_sentence_count`: PASS
- `duplicate_reference_sentence_count`: PASS
- `reference_duplicate_group_count`: PASS
- `max_reference_occurrence_count`: PASS
- `image_pdf_count`: PASS
- `status`: PASS

### Reference safety verification from Excel

- Every Excel reference row is `body_text`: PASS
- Every Excel reference row is `forward_clean`: PASS
- Unsafe direction rows are excluded: PASS
- Reference groups contain only safe `body_text + forward_clean` rows: PASS
- No cross-book reference group merge: PASS

### Final artifact status

- The workbook was not stale.
- The existing `output/excel/raz_a_reference_sentences.xlsx` already matched the S2.5 11-book JSON outputs.
- A run-stamped copy was created for safer artifact handoff.
- Final artifact status: `PASS_ARTIFACT_SYNC_COMPLETE`

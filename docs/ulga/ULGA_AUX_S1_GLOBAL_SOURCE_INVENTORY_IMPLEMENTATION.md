# ULGA-AUX-S1 Global Source Inventory Implementation

## 1. Preflight

Task:

- implement a machine-readable global source inventory
- preserve authority/reference boundaries
- remain static/offline only
- avoid corpus extraction, OCR, or authority import

Preflight result:

- scope is safe for a minimal-change implementation
- no runtime restart is required
- no existing authority graph, learner-state artifact, scheduler, API, or dashboard behavior needs modification

## 2. Files Inspected

- `docs/ulga/ULGA_AUX_S0_CORPUS_ROADMAP_AND_SOURCE_INVENTORY_DESIGN_SCAN.md`
- `docs/ulga/ulga_roadmap.md`
- `docs/SOURCE_IMPORT_DESIGN.md`
- `docs/raz/RAZ_A_S1_PDF_SENTENCE_EXTRACTION_SPEC.md`
- `docs/raz/RAZ_A_S2_5_CROSS_LEVEL_SMOKE_PILOT.md`
- `docs/ulga/ULGA_S11_READING_DIALOGUE_CONTENT_AUTHORITY_DESIGN_SCAN.md`
- `grammar_profile/source/English Grammar Profile Online.xlsx`
- `vocabulary/source/English Vocabulary Profile Online.xlsx`
- `vocabulary/source/NGSL+with+SFI+(31K).xlsx`
- `grammar_profile/json/grammar_profile.json`
- `vocabulary/json/vocabulary.json`
- `themes/theme_catalog.json`
- `themes/theme_mapping.json`
- `themes/theme_vocab_mapping.json`
- `input/manifest/raz_a_books_manifest.xlsx`
- `input/pdf/a/`
- `input/pdf/b/`
- `input/pdf/c/`
- `input/pdf/d/`
- `input/pdf/e/`
- `input/pdf/f/`
- `output/excel/*`
- `output/json/*`
- `output/logs/extraction_log.txt`
- `output/archive/S2_5_RUN_20260620_022807/`

## 3. Files Created

- `ulga/builders/build_corpus_source_inventory.py`
- `ulga/validators/validate_corpus_source_inventory.py`
- `ulga/graph/corpus_source_inventory.json`
- `ulga/reports/corpus_source_inventory_summary.json`
- `tests/ulga/test_corpus_source_inventory.py`
- `docs/ulga/ULGA_AUX_S1_GLOBAL_SOURCE_INVENTORY_IMPLEMENTATION.md`

## 4. Files Modified

- none

This task only added the required AUX-S1 files.

## 5. Builder Behavior

The builder performs a deterministic filesystem-based scan.

Behavior:

- checks path presence for known authority sources and normalized artifacts
- inspects RAZ PDF folders by folder existence and local `*.pdf` count only
- does not read PDF text
- does not OCR image PDFs
- does not parse Excel workbook cells
- emits stable `source_id` values
- sorts output by `source_family` then `source_id`
- writes canonical inventory JSON without a timestamp
- writes summary JSON with `generated_at`

Boundary-preserving rules enforced in builder output:

- RAZ manifest is recorded as manifest-only authority metadata, not content authority
- RAZ PDF folders are always `external_reference_corpus`
- RAZ pilot outputs are always `experimental_pilot_output`
- future candidate corpora remain non-promotable placeholders
- no record is marked learner-facing

## 6. Validator Behavior

The validator checks:

- required field presence
- `source_role` enum validity
- `status` enum validity
- `exists` value against actual filesystem state
- boundary rules for external reference corpora, pilot outputs, future candidates, and RAZ manifest
- RAZ B-F cannot be `present` when their folders contain zero PDFs
- notes and risk flags are string lists
- summary counts and rollups match canonical inventory records

## 7. Inventory Summary

Current generated summary:

- total sources: 33
- authority sources: 4
- normalized authority artifacts: 5
- external reference corpora: 6
- experimental pilot outputs: 12
- future candidate corpora: 6
- present: 22
- blocked: 5
- future candidate: 6
- missing: 0
- validation status in summary: `PASS_WITH_WARNINGS`

Present authority sources:

- `EGP_SOURCE_XLSX`
- `EVP_SOURCE_XLSX`
- `NGSL_SOURCE_XLSX`
- `RAZ_A_BOOKS_MANIFEST_XLSX`

Present external reference corpora:

- `RAZ_A_PDF_REFERENCE_CORPUS`

## 8. RAZ A/B-F Availability Result

Observed local result:

- `input/pdf/a`: present, 98 PDFs, status `present`
- `input/pdf/b`: folder exists, 0 PDFs, status `blocked`
- `input/pdf/c`: folder exists, 0 PDFs, status `blocked`
- `input/pdf/d`: folder exists, 0 PDFs, status `blocked`
- `input/pdf/e`: folder exists, 0 PDFs, status `blocked`
- `input/pdf/f`: folder exists, 0 PDFs, status `blocked`

Interpretation:

- only A is currently available as a local external reading reference corpus
- B-F must not be treated as available benchmark corpora in the current workspace

## 9. Boundary Rules Preserved

Preserved boundaries:

- no OCR executed
- no RAZ sentence text extracted
- no RAZ content imported into ULGA authority
- no external reference corpus promoted to authority
- no experimental pilot output promoted to authority
- no learner-facing content output created
- no runtime, scheduler, API, dashboard, or adaptive learner-state behavior changed

## 10. Commands Run

Executed commands:

```powershell
python ulga\builders\build_corpus_source_inventory.py
python ulga\validators\validate_corpus_source_inventory.py
python -m pytest tests\ulga\test_corpus_source_inventory.py -q
```

## 11. Test Results

Results:

- builder: `PASS_WITH_WARNINGS`
- validator: `PASS`
- focused pytest file: `12 passed`

Full `tests/ulga/` suite was not run in this task.

## 12. Next Recommended Task

Recommended next task:

```text
ULGA-AUX-S2_RAZCorpusRoleAndManifestHardening
```

Reason:

- the inventory now exists as a validated static artifact
- the next highest-risk issue is not discovery but policy hardening around RAZ manifest/corpus role boundaries and empty B-F folders

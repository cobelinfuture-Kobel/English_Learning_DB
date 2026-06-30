# RAZ-S6D_LevelExpansionDynamicDiscovery_Implementation

## 1. Task Name

- `RAZ-S6D_LevelExpansionDynamicDiscovery_Implementation`

## 2. Preflight Inspected Files

- `tools/raz_normalized_tagging_pipeline.py`
- `ulga/query/raz_reusable_content_seed_query_layer.py`
- `ulga/validators/validate_raz_reusable_content_seed_query_layer.py`
- `tests/ulga/test_raz_reusable_content_seed_query_layer.py`
- `ulga/builders/build_corpus_source_inventory.py`
- `docs/raz/RAZ_S6A_REUSABLE_CONTENT_SEED_QUERY_LAYER_IMPLEMENTATION.md`
- `docs/raz/RAZ_S6_REUSABLE_CONTENT_SEED_QUERY_LAYER_DESIGN_SCAN.md`
- `docs/raz/RAZ_A_S2_5_CROSS_LEVEL_SMOKE_PILOT.md`

## 3. Files Created

- `ulga/builders/build_raz_level_discovery.py`
- `ulga/validators/validate_raz_level_discovery.py`
- `tests/ulga/test_raz_level_discovery.py`
- `ulga/graph/raz_level_discovery_inventory.json`
- `ulga/reports/raz_level_discovery_summary.json`
- `ulga/reports/raz_level_discovery_validation.json`
- `docs/ulga/RAZ_S6D_LEVEL_EXPANSION_DYNAMIC_DISCOVERY_IMPLEMENTATION.md`

## 4. Files Modified

- `ulga/query/raz_reusable_content_seed_query_layer.py`
- `ulga/validators/validate_raz_reusable_content_seed_query_layer.py`

## 5. Discovery Contract

- Discovery is static and offline only.
- Discovery scans `raz_output_jsons/Level_*` and `raz_output_jsons/derived/Level_*`.
- Discovery does not mutate raw RAZ evidence or derived artifacts.
- Discovery does not generate new teaching content.
- Discovery does not promote any content into Reading, Writing, Dialogue, or Assessment Authority.
- Discovery keeps `authority_status = candidate_only` and `promotion_allowed = false` at the inventory layer.
- Discovery records malformed levels and malformed artifacts instead of silently skipping them.

## 6. Inventory Schema

Each level record contains:

- `level`
- `normalized_level`
- `detected`
- `status`
- `source_evidence`
- `available_artifacts`
- `missing_artifacts`
- `skip_reasons`
- `pipeline_capabilities`
- `authority_status`
- `promotion_allowed`
- `warnings`

`source_evidence` currently records:

- `source_pdf_count`
- `timeline_json_count`
- `sentence_candidate_count`
- `page_unit_count`
- `reuse_unit_count`
- `clean_summary_count`
- `clean_summary_exists`
- `normalized_sentence_count`
- `normalized_page_unit_count`
- `normalized_reuse_unit_count`
- `enriched_sentence_count`
- `enriched_page_unit_count`
- `enriched_reuse_unit_count`

## 7. Summary Schema

The summary report contains:

- `task`
- `total_detected_levels`
- `ready_level_count`
- `skipped_level_count`
- `partial_level_count`
- `invalid_level_count`
- `missing_required_input_count`
- `levels_by_status`
- `levels_ready_for_sentence_pipeline`
- `levels_ready_for_page_unit_pipeline`
- `levels_ready_for_reuse_unit_pipeline`
- `warnings`
- `next_recommended_task`

## 8. Validator Rules

`validate_raz_level_discovery.py` checks:

- every valid discovered level has a valid single-letter level code
- invalid level names are classified as `INVALID_FORMAT`
- every discovered record remains `authority_status = candidate_only`
- every discovered record keeps `promotion_allowed = false`
- every ready level has the required upstream evidence
- skipped, missing, and invalid levels provide at least one skip reason
- missing timeline input is reported, not treated as success
- summary counts add back to `total_detected_levels`
- the new discovery module does not contain `C/D/E/F`-only hardcoding
- existing enriched seed cards still remain `candidate_only`

`validate_raz_reusable_content_seed_query_layer.py` was also updated so S6 validation uses dynamically discovered queryable levels instead of fixed `A-F`.

## 9. Test Results

Executed:

- `python ulga/builders/build_raz_level_discovery.py`
- `python ulga/validators/validate_raz_level_discovery.py`
- `python ulga/validators/validate_raz_reusable_content_seed_query_layer.py`
- `python -m pytest tests/ulga/test_raz_level_discovery.py tests/ulga/test_raz_reusable_content_seed_query_layer.py -q`

Observed results:

- discovery builder: `PASS`
- discovery validator: `PASS`
- reusable seed query validator: `PASS`
- pytest: `13 passed`

## 10. Discovery Results

Current workspace result:

- detected levels: `6`
- ready for sentence pipeline: `A B C D E F`
- ready for page unit pipeline: `A B C D E F`
- ready for reuse unit pipeline: `A B C D E F`
- partial levels: none
- invalid levels: none
- skipped levels: none

Current inventory shows:

- `A`: `timeline_json_count=100`, `sentence_candidate_count=808`, `page_unit_count=804`, `reuse_unit_count=4`
- `B`: `timeline_json_count=100`, `sentence_candidate_count=829`, `page_unit_count=802`, `reuse_unit_count=27`
- `C`: `timeline_json_count=100`, `sentence_candidate_count=1064`, `page_unit_count=808`, `reuse_unit_count=248`
- `D`: `timeline_json_count=83`, `sentence_candidate_count=1180`, `page_unit_count=735`, `reuse_unit_count=389`
- `E`: `timeline_json_count=93`, `sentence_candidate_count=1670`, `page_unit_count=904`, `reuse_unit_count=619`
- `F`: `timeline_json_count=90`, `sentence_candidate_count=1936`, `page_unit_count=872`, `reuse_unit_count=723`

## 11. Known Limitations

- Discovery is based on local filesystem evidence only. It does not call external APIs.
- `source_pdf_count` is currently `0` for all discovered levels in this workspace because readiness is derived from raw timeline and derived artifact presence, not PDF folder availability.
- Query-layer default behavior such as picture-prompt bias toward lower levels remains unchanged. This task only removed fixed level loading assumptions, not product-level retrieval policy.
- If future repositories introduce multi-character level IDs, the current validator will intentionally classify them as invalid until naming policy is updated.

## 12. Explicit Authority Boundary Statement

This task does not promote any RAZ content into Reading Authority, Writing Authority, Dialogue Authority, or Assessment Authority.

All reused or derived RAZ content remains candidate-only, static, offline, and non-promoted in this implementation.

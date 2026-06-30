# RAZ-S6K1_G_DerivedBuildSmokePilot_WarningClusterQA

## 1. Task name

- `RAZ-S6K1_G_DerivedBuildSmokePilot_WarningClusterQA`

## 2. Objective

- Cluster `Level G` warnings from the `RAZ-S6K_G_DerivedBuildSmokePilot`.
- Decide whether warnings are review backlog or must-fix defects before `Level H` second smoke pilot.

## 3. Preflight

- Read `S6K` smoke-pilot reports and Level `G` normalized/enriched artifacts.
- Confirmed `new_warning_types = []`, schema validation `PASS`, seed query layer still matches the operator approval policy.
- Confirmed this QA task stays read-only for derived artifacts and does not rebuild `Level G`.

## 4. Files inspected

- `docs/ulga/RAZ_S6K_G_DERIVED_BUILD_SMOKE_PILOT.md`
- `ulga/reports/raz_g_derived_build_smoke_pilot.json`
- `raz_output_jsons/derived/Level_G/normalized/raz_G_sentence_normalized.jsonl`
- `raz_output_jsons/derived/Level_G/normalized/raz_G_page_unit_normalized.json`
- `raz_output_jsons/derived/Level_G/normalized/raz_G_reuse_unit_normalized.json`
- `raz_output_jsons/derived/Level_G/enriched/raz_G_sentence_enriched.jsonl`
- `raz_output_jsons/derived/Level_G/enriched/raz_G_page_unit_enriched.json`
- `raz_output_jsons/derived/Level_G/enriched/raz_G_reuse_unit_enriched.json`
- `raz_output_jsons/derived/reports/raz_tagging_summary.json`
- `raz_output_jsons/derived/reports/raz_tagging_warnings.json`
- `raz_output_jsons/derived/reports/raz_tagging_schema_validation.json`
- `ulga/policies/raz_seed_query_layer_policy.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_summary.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_validation.json`
- `ulga/reports/raz_level_discovery_validation.json`
- `ulga/reports/raz_downstream_discovery_drift_validation.json`
- `tools/raz_normalized_tagging_pipeline.py`

## 5. Files created

- `ulga/reports/raz_g_warning_cluster_qa.json`
- `docs/ulga/RAZ_S6K1_G_DERIVED_BUILD_SMOKE_PILOT_WARNING_CLUSTER_QA.md`
- `tools/raz_g_warning_cluster_qa.py`

## 6. Files modified

- `None`

## 7. Source S6K build integrity recap

- `normalized_sentence_count = 2336`
- `normalized_page_unit_count = 930`
- `normalized_reuse_unit_count = 801`
- `enriched_sentence_count = 2336`
- `enriched_page_unit_count = 930`
- `enriched_reuse_unit_count = 801`
- Count parity `PASS`
- Schema validation `PASS`
- Traceability `PASS`
- Duplicate ID check `PASS`
- Forbidden audio field check `PASS`

## 8. Warning distribution recap

- `unknown_theme = 837`
- `unknown_pattern = 0`
- `unknown_grammar = 145`
- `section_heading_detected = 101`
- `human_review_required = 897`
- `malformed_or_schema_warning = 0`
- `new_warning_types = []`

## 9. unknown_theme cluster analysis

- Total records: `837`
- By record type: `{'sentence': 611, 'page_unit': 128, 'reuse_unit': 98}`
- Top books: `[('2206 | Tens and Ones Together', 43), ('2465 | Amazing Mummies', 36), ('1547 | Rude Robot', 32), ('2737 | Miles the Nile Crocodile', 32), ('1573 | New Rule!', 29), ("2628 | A President's Day", 29), ('4171 | Doing the Right Thing', 28), ("837 | Monsters' Stormy Day", 28), ('1556 | Troll Bridge', 27), ('2187 | Mystery Valentine', 26)]`
- Probable themes inferred from raw text: `[('Animals', 99), ('Science', 43), ('Math', 22), ('Nature', 18), ('Transportation', 10), ('DailyRoutine', 9), ('School', 8), ('Health', 4)]`
- Assessment: warning volume is broad but concentrated in recurring topical books, pointing to taxonomy coverage gaps more than malformed data.
- Likelihood: taxonomy gap `HIGH`, pipeline defect `LOW`

## 10. human_review_required cluster analysis

- Total records: `897`
- Trigger combinations: `[('unknown_theme', 775), ('section_heading_detected + unknown_grammar', 40), ('unknown_theme + section_heading_detected + unknown_grammar', 25), ('unknown_theme + unknown_grammar', 21), ('section_heading_detected', 20), ('unknown_theme + section_heading_detected', 16)]`
- Overlap with `unknown_theme`: `837`
- Overlap with `section_heading_detected`: `101`
- Overlap with `unknown_grammar`: `86`
- Assessment: `human_review_required` is mostly redundant with `unknown_theme` plus section-heading gating, not a separate hidden defect family.

## 11. section_heading_detected cluster analysis

- Total records: `101`
- By record type: `{'sentence': 101}`
- Top titles: `[('How to Build a Guitar', 15), ('Grow Tomatoes in Six Steps', 7), ('All Kinds of Homes', 7), ('Fire Safety', 7), ('Tens and Ones Together', 7), ('Cockroaches', 7), ('Ough is Tough', 6), ('American Symbols', 5), ('Living Or Nonliving?', 5), ("A President's Day", 5)]`
- Likely true headings: `95`
- Ambiguous headings: `6`
- Assessment: most flagged records look like real nonfiction headings or short title fragments; they are entering enriched artifacts but remain `candidate_only` and review-blocked.
- Recommendation: keep as QA warning and continue excluding from future query-layer eligibility.

## 12. unknown_grammar cluster analysis

- Total records: `145`
- By record type: `{'sentence': 145}`
- Likely grammar categories: `[('other', 66), ('present_simple', 53), ('compound_sentence', 17), ('relative_clause', 3), ('future', 2), ('imperative', 2), ('complex_sentence', 1), ('comparative', 1)]`
- Sentence length buckets: `{'5-8': 38, '9-12': 10, '1-4': 97}`
- Assessment: many unknown-grammar sentences are still classifiable as question / present-simple / past-simple / compound forms, so this looks more like a rule-coverage gap than a data defect.

## 13. warning overlap matrix

- `unknown_theme` vs `human_review_required`: `837`
- `unknown_theme` vs `section_heading_detected`: `41`
- `unknown_theme` vs `unknown_grammar`: `46`
- `human_review_required` vs `section_heading_detected`: `101`
- `human_review_required` vs `unknown_grammar`: `86`
- `section_heading_detected` vs `unknown_grammar`: `65`

## 14. Top warning-contributing books/pages/units

- Top books: `[('2206 | Tens and Ones Together', 112), ('2465 | Amazing Mummies', 75), ("2628 | A President's Day", 74), ('1547 | Rude Robot', 70), ('2737 | Miles the Nile Crocodile', 68), ('2340 | Cockroaches', 66), ('1556 | Troll Bridge', 64), ('1573 | New Rule!', 64), ('1951 | American Symbols', 64), ('2187 | Mystery Valentine', 62)]`
- Top page units: `[('RAZ_G_837_P012', 16), ('RAZ_G_1573_P007', 15), ('RAZ_G_1573_P008', 14), ('RAZ_G_2187_P012', 14), ('RAZ_G_2515_P011', 14), ('RAZ_G_2628_P007', 14), ('RAZ_G_2835_P004', 14), ('RAZ_G_2340_P006', 13), ('RAZ_G_2340_P009', 13), ('RAZ_G_2628_P005', 13)]`

## 15. Representative samples

- unknown_theme: `[{'record_id': 'RAZ_G_1287_CAND_000001', 'record_type': 'sentence', 'book_id': '1287', 'title': 'Billy Gets Lost', 'page_unit_id': 'RAZ_G_1287_P003', 'text': 'Billy is a puppy.', 'warnings': ['unknown_theme'], 'review_status': 'human_review_required'}, {'record_id': 'RAZ_G_1287_CAND_000005', 'record_type': 'sentence', 'book_id': '1287', 'title': 'Billy Gets Lost', 'page_unit_id': 'RAZ_G_1287_P004', 'text': 'Billy chases it.', 'warnings': ['unknown_theme'], 'review_status': 'human_review_required'}, {'record_id': 'RAZ_G_1287_CAND_000015', 'record_type': 'sentence', 'book_id': '1287', 'title': 'Billy Gets Lost', 'page_unit_id': 'RAZ_G_1287_P006', 'text': '"Oh, no, I am lost," Billy says.', 'warnings': ['unknown_theme'], 'review_status': 'human_review_required'}]`
- human_review_required: `[{'record_id': 'RAZ_G_1287_CAND_000001', 'record_type': 'sentence', 'book_id': '1287', 'title': 'Billy Gets Lost', 'page_unit_id': 'RAZ_G_1287_P003', 'text': 'Billy is a puppy.', 'warnings': ['unknown_theme'], 'review_status': 'human_review_required'}, {'record_id': 'RAZ_G_1287_CAND_000005', 'record_type': 'sentence', 'book_id': '1287', 'title': 'Billy Gets Lost', 'page_unit_id': 'RAZ_G_1287_P004', 'text': 'Billy chases it.', 'warnings': ['unknown_theme'], 'review_status': 'human_review_required'}, {'record_id': 'RAZ_G_1287_CAND_000015', 'record_type': 'sentence', 'book_id': '1287', 'title': 'Billy Gets Lost', 'page_unit_id': 'RAZ_G_1287_P006', 'text': '"Oh, no, I am lost," Billy says.', 'warnings': ['unknown_theme'], 'review_status': 'human_review_required'}]`
- section_heading_detected: `[{'record_id': 'RAZ_G_1396_CAND_000001', 'record_type': 'sentence', 'book_id': '1396', 'title': 'Grow Tomatoes in Six Steps', 'page_unit_id': 'RAZ_G_1396_P004', 'text': 'Tasty Tomatoes', 'warnings': ['section_heading_detected', 'unknown_theme'], 'review_status': 'human_review_required'}, {'record_id': 'RAZ_G_1396_CAND_000005', 'record_type': 'sentence', 'book_id': '1396', 'title': 'Grow Tomatoes in Six Steps', 'page_unit_id': 'RAZ_G_1396_P005', 'text': 'Step 1: Plant the Seeds', 'warnings': ['section_heading_detected'], 'review_status': 'human_review_required'}, {'record_id': 'RAZ_G_1396_CAND_000010', 'record_type': 'sentence', 'book_id': '1396', 'title': 'Grow Tomatoes in Six Steps', 'page_unit_id': 'RAZ_G_1396_P006', 'text': 'Step 2: Water the Seeds', 'warnings': ['section_heading_detected'], 'review_status': 'human_review_required'}]`
- unknown_grammar: `[{'record_id': 'RAZ_G_1396_CAND_000006', 'record_type': 'sentence', 'book_id': '1396', 'title': 'Grow Tomatoes in Six Steps', 'page_unit_id': 'RAZ_G_1396_P005', 'text': 'Fill a small pot with soil.', 'warnings': ['unknown_grammar'], 'review_status': 'pending'}, {'record_id': 'RAZ_G_1396_CAND_000007', 'record_type': 'sentence', 'book_id': '1396', 'title': 'Grow Tomatoes in Six Steps', 'page_unit_id': 'RAZ_G_1396_P005', 'text': 'Use a pencil to poke a hole halfway down the soil.', 'warnings': ['unknown_grammar', 'unknown_pattern'], 'review_status': 'pending'}, {'record_id': 'RAZ_G_1396_CAND_000009', 'record_type': 'sentence', 'book_id': '1396', 'title': 'Grow Tomatoes in Six Steps', 'page_unit_id': 'RAZ_G_1396_P005', 'text': 'Fill the hole with soil.', 'warnings': ['unknown_grammar'], 'review_status': 'pending'}]`

## 16. Root-cause assessment

- taxonomy gap likelihood: `HIGH`
- pipeline defect likelihood: `LOW`
- section boundary defect likelihood: `LOW`
- grammar mapping gap likelihood: `MEDIUM`

## 17. Seed query layer boundary result

- Queryable levels: `['A', 'B', 'C', 'D', 'E', 'F']`
- Approved levels by policy: `['A', 'B', 'C', 'D', 'E', 'F']`
- `G exposed = False`
- Status: `PASS`

## 18. Authority boundary result

- `candidate_only = PASS`
- `promotion_allowed = PASS`

## 19. Validator results

- `validate_raz_level_discovery = PASS`
- `validate_raz_reusable_content_seed_query_layer = PASS`
- `validate_raz_downstream_discovery_drift = PASS_WITH_WARNINGS`
- `must_fix_count = 0`

## 20. Test results

- `29 passed, 8 subtests passed in 19.38s`

## 21. QA status

- `PASS_WITH_WARNINGS`

## 22. Decision for H second pilot

- `ALLOW_H_SECOND_PILOT`

## 23. Next recommended task

- `If H enters the second smoke pilot, keep the A-F query gate fixed and treat Level G unknown_theme / unknown_grammar follow-up as targeted QA backlog rather than promotion-ready cleanup.`

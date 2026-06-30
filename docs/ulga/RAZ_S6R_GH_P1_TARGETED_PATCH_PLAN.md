# RAZ-S6R_GH_P1_TargetedPatchPlan

## 1. Task name

`RAZ-S6R_GH_P1_TargetedPatchPlan`

## 2. Objective

Create a focused post-S6P / post-S6Q P1 patch plan for the remaining G/H backlog without implementing taxonomy, pattern, grammar, query, or promotion changes.

## 3. Scope guardrails

- G/H only.
- Planning only. No production tagging logic changes.
- No I-W processing.
- No seed query layer expansion.
- No promotion, CEFR, adaptive, or learner-state behavior.

## 4. Preflight

- S6Q status: `PASS`
- S6P status: `PASS`
- Current queryable levels: `['A', 'B', 'C', 'D', 'E', 'F']`
- Current S6F must_fix_count: `0`
- Planning only: `True`
- Production code modified: `False`

## 5. Files inspected

- `docs/ulga/RAZ_S6Q_GH_TAGGING_RERUN_DELTA_QA.md`
- `ulga/reports/raz_gh_tagging_rerun_delta_qa.json`
- `docs/ulga/RAZ_S6P_GH_TARGETED_TAXONOMY_AND_PATTERN_PATCH_IMPLEMENTATION.md`
- `ulga/reports/raz_gh_targeted_taxonomy_and_pattern_patch_implementation.json`
- `docs/ulga/RAZ_S6O_GH_TARGETED_TAXONOMY_AND_PATTERN_PATCH_PLAN.md`
- `ulga/reports/raz_gh_targeted_taxonomy_and_pattern_patch_plan.json`
- `docs/ulga/RAZ_S6N_WARNING_REPORT_COVERAGE_PATCH.md`
- `ulga/reports/raz_warning_report_coverage_patch.json`
- `docs/ulga/RAZ_S6M_H_WARNING_CLUSTER_AND_REPORT_COVERAGE_QA.md`
- `ulga/reports/raz_h_warning_cluster_and_report_coverage_qa.json`
- `raz_output_jsons/derived/reports/raz_tagging_summary.json`
- `raz_output_jsons/derived/reports/raz_tagging_warnings.json`
- `raz_output_jsons/derived/reports/raz_tagging_schema_validation.json`
- `ulga/policies/raz_seed_query_layer_policy.json`
- `ulga/query/raz_reusable_content_seed_query_layer.py`
- `ulga/validators/validate_raz_reusable_content_seed_query_layer.py`
- `ulga/builders/build_raz_level_discovery.py`
- `ulga/validators/validate_raz_level_discovery.py`
- `ulga/validators/validate_raz_downstream_discovery_drift.py`
- `ulga/reports/raz_level_discovery_summary.json`
- `ulga/reports/raz_level_discovery_validation.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_summary.json`
- `ulga/reports/raz_reusable_content_seed_query_layer_validation.json`
- `ulga/reports/raz_downstream_discovery_drift_validation.json`
- `tools/raz_normalized_tagging_pipeline.py`
- `tests/test_raz_normalized_tagging_pipeline.py`
- `raz_output_jsons/derived/Level_G/normalized/raz_G_sentence_normalized.jsonl`
- `raz_output_jsons/derived/Level_G/normalized/raz_G_page_unit_normalized.json`
- `raz_output_jsons/derived/Level_G/normalized/raz_G_reuse_unit_normalized.json`
- `raz_output_jsons/derived/Level_G/enriched/raz_G_sentence_enriched.jsonl`
- `raz_output_jsons/derived/Level_G/enriched/raz_G_page_unit_enriched.json`
- `raz_output_jsons/derived/Level_G/enriched/raz_G_reuse_unit_enriched.json`
- `raz_output_jsons/derived/Level_H/normalized/raz_H_sentence_normalized.jsonl`
- `raz_output_jsons/derived/Level_H/normalized/raz_H_page_unit_normalized.json`
- `raz_output_jsons/derived/Level_H/normalized/raz_H_reuse_unit_normalized.json`
- `raz_output_jsons/derived/Level_H/enriched/raz_H_sentence_enriched.jsonl`
- `raz_output_jsons/derived/Level_H/enriched/raz_H_page_unit_enriched.json`
- `raz_output_jsons/derived/Level_H/enriched/raz_H_reuse_unit_enriched.json`

## 6. Files created

- `tools/raz_gh_p1_targeted_patch_plan.py`
- `tests/ulga/test_raz_gh_p1_targeted_patch_plan.py`
- `docs/ulga/RAZ_S6R_GH_P1_TARGETED_PATCH_PLAN.md`
- `ulga/reports/raz_gh_p1_targeted_patch_plan.json`

## 7. Files modified

- None

## 8. Source status from S6Q

- `s6q_status = PASS`
- `s6p_patch_accepted = True`

## 9. Current G/H metrics

- `G`: enriched=4067, unknown_theme=616, unknown_pattern=242, unknown_grammar=145, section_heading=101, human_review=691, malformed=0, dialogue=0
- `H`: enriched=4548, unknown_theme=404, unknown_pattern=199, unknown_grammar=175, section_heading=167, human_review=545, malformed=0, dialogue=0

## 10. Residual warning summary

- `G`: unknown_theme=616 (15.15%), unknown_pattern=242 (5.95%), unknown_grammar=145 (3.57%), section_heading=101 (2.48%), human_review=691 (16.99%)
- `H`: unknown_theme=404 (8.88%), unknown_pattern=199 (4.38%), unknown_grammar=175 (3.85%), section_heading=167 (3.67%), human_review=545 (11.98%)

- `G top books`: [{'key': '2206 | Tens and Ones Together', 'count': 112}, {'key': '1547 | Rude Robot', 'count': 66}, {'key': '1573 | New Rule!', 'count': 64}, {'key': "837 | Monsters' Stormy Day", 'count': 62}, {'key': '4171 | Doing the Right Thing', 'count': 56}]
- `H top books`: [{'key': '262 | Club Monster', 'count': 62}, {'key': '1382 | Pip, the Monster Princess', 'count': 61}, {'key': '263 | Cool as a Cuke', 'count': 60}, {'key': '945 | Tag-Along Goat', 'count': 60}, {'key': "1148 | Nami's Gifts", 'count': 54}]
- `G top page units`: [{'key': 'RAZ_G_837_P012', 'count': 16}, {'key': 'RAZ_G_1573_P007', 'count': 15}, {'key': 'RAZ_G_1573_P008', 'count': 14}, {'key': 'RAZ_G_2187_P012', 'count': 14}, {'key': 'RAZ_G_2515_P011', 'count': 13}]
- `H top page units`: [{'key': 'RAZ_H_1523_P008', 'count': 12}, {'key': 'RAZ_H_3886_P015', 'count': 12}, {'key': 'RAZ_H_890_P006', 'count': 12}, {'key': 'RAZ_H_3595_P013', 'count': 11}, {'key': 'RAZ_H_3865_P003', 'count': 11}]
- `G repeated text patterns`: [{'key': 'how many toys are out <w> the room today', 'count': 10}, {'key': 'what <w> the missing numeral', 'count': 6}, {'key': 'what other ways can you show what you know', 'count': 5}, {'key': 'and she did', 'count': 4}, {'key': '<w> pig <w> <w> wig and <w> dog <w> <w> bog', 'count': 4}]
- `H repeated text patterns`: [{'key': 'poof', 'count': 6}, {'key': 'then she put <w> <w> <w> red box', 'count': 3}, {'key': 'what <w> beautiful kitty you are', 'count': 2}, {'key': 'sam drew the idea <w> his pad <w> paper', 'count': 2}, {'key': 'rapunzel', 'count': 2}]

## 11. Residual unknown_theme analysis

### Theme Categories
- `social_emotional_moral_choice`: evidence=220, levels=['G', 'H'], confidence=HIGH, risk=LOW, expected_reduction=165, priority=P1_IMPLEMENT
- `broad_narrative_ambiguous_residual`: evidence=239, levels=['G', 'H'], confidence=LOW, risk=HIGH, expected_reduction=0, priority=DEFER
- `fantasy_monsters_royalty`: evidence=127, levels=['G', 'H'], confidence=MEDIUM, risk=MEDIUM, expected_reduction=95, priority=P1_IMPLEMENT
- `other`: evidence=96, levels=['G', 'H'], confidence=LOW, risk=HIGH, expected_reduction=0, priority=DEFER
- `math_counting_measurement_leftover`: evidence=143, levels=['G', 'H'], confidence=HIGH, risk=LOW, expected_reduction=0, priority=P2_DEFER
- `culture_holiday_tradition`: evidence=141, levels=['G', 'H'], confidence=HIGH, risk=LOW, expected_reduction=106, priority=P1_IMPLEMENT
- `poetry_literary_misc_deferred`: evidence=54, levels=['G', 'H'], confidence=LOW, risk=HIGH, expected_reduction=0, priority=DEFER

## 12. Residual unknown_pattern analysis

### Pattern Categories
- `other`: evidence=52, levels=['G', 'H'], confidence=LOW, risk=MEDIUM, expected_reduction=0, priority=DEFER
- `quoted_expressive_sentence`: evidence=150, levels=['G', 'H'], confidence=MEDIUM, risk=MEDIUM, expected_reduction=0, priority=DEFER
- `prepositional_expansion`: evidence=55, levels=['G', 'H'], confidence=MEDIUM, risk=LOW, expected_reduction=19, priority=P1_NARROW_SCOPE
- `poetic_repetitive_line`: evidence=71, levels=['G', 'H'], confidence=LOW, risk=HIGH, expected_reduction=0, priority=DEFER
- `relative_or_temporal_clause_tail`: evidence=43, levels=['G', 'H'], confidence=MEDIUM, risk=MEDIUM, expected_reduction=19, priority=P1_NARROW_SCOPE
- `compound_predicate_or_clause_chain`: evidence=11, levels=['G', 'H'], confidence=MEDIUM, risk=MEDIUM, expected_reduction=6, priority=P1_NARROW_SCOPE
- `narrative_inversion`: evidence=10, levels=['G', 'H'], confidence=LOW, risk=HIGH, expected_reduction=0, priority=DEFER
- `question_like_residual`: evidence=45, levels=['G', 'H'], confidence=LOW, risk=MEDIUM, expected_reduction=0, priority=DEFER
- `pronunciation_artifact_residual`: evidence=3, levels=['H'], confidence=LOW, risk=HIGH, expected_reduction=0, priority=DEFER
- `imperative_procedural_residual`: evidence=1, levels=['H'], confidence=LOW, risk=MEDIUM, expected_reduction=0, priority=DEFER

## 13. Residual unknown_grammar analysis

### Grammar Categories
- `imperative_procedural`: evidence=18, levels=['G', 'H'], confidence=HIGH, risk=LOW, expected_reduction=14, priority=P1_NARROW_SCOPE
- `section_heading_driven_artifact`: evidence=148, levels=['G', 'H'], confidence=HIGH, risk=HIGH, expected_reduction=0, priority=DEFER
- `present_simple_linking_still_missed`: evidence=105, levels=['G', 'H'], confidence=LOW, risk=HIGH, expected_reduction=21, priority=DEFER
- `compound_relative_grammar_residual`: evidence=38, levels=['G', 'H'], confidence=MEDIUM, risk=MEDIUM, expected_reduction=10, priority=DEFER
- `other`: evidence=11, levels=['G', 'H'], confidence=LOW, risk=MEDIUM, expected_reduction=0, priority=DEFER

## 14. Candidate authorization table

| Candidate | Type | Decision | Evidence | Est. Reduction | Confidence | Risk |
|---|---|---|---:|---:|---|---|
| `THM_P1_SOCIAL_EMOTIONAL_MORAL_CHOICE` | `theme_taxonomy` | `AUTHORIZE_FOR_S6S` | 220 | 165 | `HIGH` | `LOW` |
| `THM_P1_CULTURE_HOLIDAY_TRADITION` | `theme_taxonomy` | `AUTHORIZE_FOR_S6S` | 141 | 106 | `HIGH` | `LOW` |
| `THM_P1_FANTASY_MONSTERS_ROYALTY` | `theme_taxonomy` | `AUTHORIZE_FOR_S6S` | 127 | 95 | `MEDIUM` | `MEDIUM` |
| `THM_P2_MATH_COUNTING_MEASUREMENT` | `no_change` | `REPLACE_WITH_I_SMOKE_PILOT` | 143 | 0 | `HIGH` | `LOW` |
| `THM_DEFER_POETRY_LITERARY_MISC` | `no_change` | `DEFER` | 54 | 0 | `LOW` | `HIGH` |
| `PAT_P1_QUOTED_EXPRESSIVE_SENTENCE` | `pattern_rule` | `DEFER` | 150 | 0 | `MEDIUM` | `MEDIUM` |
| `PAT_P1_PREPOSITIONAL_EXPANSION` | `pattern_rule` | `DEFER` | 55 | 19 | `MEDIUM` | `LOW` |
| `PAT_P1_COMPOUND_PREDICATE_OR_CLAUSE_CHAIN` | `pattern_rule` | `DEFER` | 11 | 6 | `MEDIUM` | `MEDIUM` |
| `PAT_P1_RELATIVE_OR_TEMPORAL_CLAUSE_TAIL` | `pattern_rule` | `DEFER` | 43 | 19 | `MEDIUM` | `MEDIUM` |
| `PAT_DEFER_POETIC_REPETITIVE_LINE` | `no_change` | `DEFER` | 71 | 0 | `LOW` | `HIGH` |
| `PAT_DEFER_NARRATIVE_INVERSION_AND_ARTIFACT` | `no_change` | `DEFER` | 10 | 0 | `LOW` | `HIGH` |
| `GRM_P1_PRESENT_SIMPLE_AND_LINKING_FOLLOWUP` | `grammar_rule` | `DEFER` | 105 | 21 | `LOW` | `HIGH` |
| `GRM_P1_IMPERATIVE_PROCEDURAL` | `grammar_rule` | `AUTHORIZE_NARROW_FOR_S6S` | 18 | 14 | `HIGH` | `LOW` |
| `GRM_DEFER_SECTION_HEADING_ARTIFACTS` | `no_change` | `DEFER` | 148 | 0 | `HIGH` | `HIGH` |

## 15. Recommended S6S scope

- Recommendation: `AUTHORIZE_S6S_P1_THEME_PLUS_IMPERATIVE_ONLY`
- Authorized candidates: `['THM_P1_SOCIAL_EMOTIONAL_MORAL_CHOICE', 'THM_P1_CULTURE_HOLIDAY_TRADITION', 'THM_P1_FANTASY_MONSTERS_ROYALTY', 'GRM_P1_IMPERATIVE_PROCEDURAL']`
- Not authorized candidates: `['THM_P2_MATH_COUNTING_MEASUREMENT', 'THM_DEFER_POETRY_LITERARY_MISC', 'PAT_P1_QUOTED_EXPRESSIVE_SENTENCE', 'PAT_P1_PREPOSITIONAL_EXPANSION', 'PAT_P1_COMPOUND_PREDICATE_OR_CLAUSE_CHAIN', 'PAT_P1_RELATIVE_OR_TEMPORAL_CLAUSE_TAIL', 'PAT_DEFER_POETIC_REPETITIVE_LINE', 'PAT_DEFER_NARRATIVE_INVERSION_AND_ARTIFACT', 'GRM_P1_PRESENT_SIMPLE_AND_LINKING_FOLLOWUP', 'GRM_DEFER_SECTION_HEADING_ARTIFACTS']`
- Reason: `Theme P1 families remain materially valuable and safely title-concentrated, while imperative grammar is the only clean grammar follow-up; pattern residuals are now mostly ambiguity-heavy.`

## 16. Candidates explicitly not authorized

- `THM_P2_MATH_COUNTING_MEASUREMENT`
- `THM_DEFER_POETRY_LITERARY_MISC`
- `PAT_P1_QUOTED_EXPRESSIVE_SENTENCE`
- `PAT_P1_PREPOSITIONAL_EXPANSION`
- `PAT_P1_COMPOUND_PREDICATE_OR_CLAUSE_CHAIN`
- `PAT_P1_RELATIVE_OR_TEMPORAL_CLAUSE_TAIL`
- `PAT_DEFER_POETIC_REPETITIVE_LINE`
- `PAT_DEFER_NARRATIVE_INVERSION_AND_ARTIFACT`
- `GRM_P1_PRESENT_SIMPLE_AND_LINKING_FOLLOWUP`
- `GRM_DEFER_SECTION_HEADING_ARTIFACTS`

## 17. Section heading policy

- `keep_warning_only = True`
- `keep_query_exclusion = True`
- `patch_needed = False`

## 18. Human review policy

- `treat_as_derived_gate = True`
- `patch_directly = False`

## 19. S6T delta QA plan

- Rerun levels: `['G', 'H']`
- Metrics: `['unknown_theme_delta', 'unknown_pattern_delta', 'unknown_grammar_delta', 'human_review_required_delta', 'section_heading_delta', 'malformed_or_schema_warning', 'dialogue_or_quotation_warning', 'count_parity', 'schema_validation', 'duplicate_warning_check', 'traceability', 'seed_query_boundary', 'authority_boundary', 'S6F must_fix_count']`
- Pass criteria: `{'unknown_theme_delta': 'Negative on both G and H for authorized theme families.', 'unknown_pattern_delta': 'Flat or incidental only; no pattern regression is acceptable because S6S should not touch pattern rules.', 'unknown_grammar_delta': 'Negative only for narrow imperative/procedural subset; broad present-simple bucket must remain stable.', 'human_review_required_delta': 'Negative only through indirect overlap reduction.', 'section_heading_delta': 'Stable within reviewable margin; no direct reduction target.', 'malformed_or_schema_warning': 'Must remain 0.', 'dialogue_or_quotation_warning': 'Must remain 0.', 'count_parity': 'PASS', 'schema_validation': 'PASS', 'duplicate_warning_check': '0', 'traceability': 'PASS', 'seed_query_boundary': 'G/H remain excluded.', 'authority_boundary': 'candidate_only=PASS and promotion_allowed=PASS.', 'S6F must_fix_count': '0'}`

## 20. Seed query layer boundary

- queryable_levels: `['A', 'B', 'C', 'D', 'E', 'F']`
- `g_exposed = False`
- `h_exposed = False`
- status: `PASS`

## 21. Authority boundary

- `candidate_only = PASS`
- `promotion_allowed = PASS`

## 22. Validator results

- `validate_raz_level_discovery = PASS`
- `validate_raz_reusable_content_seed_query_layer = PASS`
- `validate_raz_downstream_discovery_drift = PASS_WITH_WARNINGS`
- `must_fix_count = 0`

## 23. Plan status

`PASS_WITH_WARNINGS`

## 24. Risk level

`Low`

## 25. Decision for next stage

`RUN_S6S_P1_TARGETED_PATCH_IMPLEMENTATION`

## 26. Next recommended task

`RAZ-S6S_GH_P1_TARGETED_PATCH_IMPLEMENTATION`


# RAZ-S6O_GH_TargetedTaxonomyAndPatternPatchPlan

## 1. Task Name

`RAZ-S6O_GH_TargetedTaxonomyAndPatternPatchPlan`

## 2. Objective

Create a planning-only, ranked patch plan for Level G/H `unknown_theme`, `unknown_pattern`, and limited `unknown_grammar` coverage gaps now that the post-S6N flat warning report is trustworthy.

## 3. Scope Guardrails

- G/H only.
- Planning only. No taxonomy, pattern, grammar, query, authority, or learner-state implementation changes.
- `G exposed = false`, `H exposed = false`.
- `candidate_only` and `promotion_allowed=false` remain unchanged.

## 4. Preflight

- S6N source status: `PASS`; flat warning report is trustworthy.
- S6M source status: `PASS_WITH_WARNINGS`; H `unknown_pattern` root cause remains `PATTERN_TAXONOMY_GAP`.
- G baseline artifacts inspected: S6K + S6K1 reports.
- H baseline artifacts inspected: S6L + S6M reports.
- Current warning / summary / schema reports inspected.
- G/H enriched sentence, page-unit, and reuse-unit artifacts inspected read-only.
- Query-layer and validator code inspected to confirm A-F-only exposure boundary remains intact.

## 5. Files Inspected

- `docs/ulga/RAZ_S6N_WARNING_REPORT_COVERAGE_PATCH.md`
- `ulga/reports/raz_warning_report_coverage_patch.json`
- `docs/ulga/RAZ_S6M_H_WARNING_CLUSTER_AND_REPORT_COVERAGE_QA.md`
- `ulga/reports/raz_h_warning_cluster_and_report_coverage_qa.json`
- `docs/ulga/RAZ_S6K_G_DERIVED_BUILD_SMOKE_PILOT.md`
- `ulga/reports/raz_g_derived_build_smoke_pilot.json`
- `docs/ulga/RAZ_S6K1_G_DERIVED_BUILD_SMOKE_PILOT_WARNING_CLUSTER_QA.md`
- `ulga/reports/raz_g_warning_cluster_qa.json`
- `docs/ulga/RAZ_S6L_H_DERIVED_BUILD_SECOND_SMOKE_PILOT.md`
- `ulga/reports/raz_h_derived_build_second_smoke_pilot.json`
- `raz_output_jsons/derived/reports/raz_tagging_warnings.json`
- `raz_output_jsons/derived/reports/raz_tagging_summary.json`
- `raz_output_jsons/derived/reports/raz_tagging_schema_validation.json`
- `raz_output_jsons/derived/Level_G/enriched/*`
- `raz_output_jsons/derived/Level_H/enriched/*`
- `tools/raz_normalized_tagging_pipeline.py`
- `ulga/query/raz_reusable_content_seed_query_layer.py`
- `ulga/validators/validate_raz_reusable_content_seed_query_layer.py`
- `ulga/reports/raz_level_discovery_summary.json`
- `ulga/reports/raz_level_discovery_validation.json`
- `ulga/reports/raz_downstream_discovery_drift_validation.json`

## 6. Files Created

- `docs/ulga/RAZ_S6O_GH_TARGETED_TAXONOMY_AND_PATTERN_PATCH_PLAN.md`
- `ulga/reports/raz_gh_targeted_taxonomy_and_pattern_patch_plan.json`

## 7. Files Modified

- None outside the two new planning artifacts.

## 8. Source Status From S6N

- `unknown_pattern` and `human_review_required` now appear in `raz_tagging_warnings.json`.
- Coverage parity, duplicate warning check, and traceability check passed.
- `taxonomy_or_pattern_rule_changed = false`
- `grammar_rule_changed = false`
- Query layer still limited to A-F.

## 9. G/H Warning Comparison

| Level | Enriched records | unknown_theme | unknown_pattern | unknown_grammar | section_heading | human_review |
|---|---:|---:|---:|---:|---:|---:|
| G | 4067 | 837 (20.58%) | 643 (15.81%) | 145 (3.57%) | 101 (2.48%) | 897 (22.06%) |
| H | 4548 | 734 (16.14%) | 660 (14.51%) | 175 (3.85%) | 167 (3.67%) | 832 (18.29%) |

Other warning families:

- `malformed_or_schema_warning = 0` on G/H.
- `dialogue_or_quotation_warning = 0` on G/H.

Top warning-contributing books:

- G: `Tens and Ones Together`, `Amazing Mummies`, `A President's Day`, `Rude Robot`, `Miles the Nile Crocodile`
- H: `Abigail Adams`, `Rapunzel`, `Dr. King's Memorial`, `The Empty Pot`, `Our Five Senses`

Top repeated text patterns:

- G: `step <num>`, `what other ways can you show what you know`, `conclusion`, `what is the missing numeral`
- H: `introduction`, `conclusion`, `poof`, `the seed did not grow`

## 10. unknown_theme Analysis

Cross-level high-signal clusters:

- `science_nature_nonfiction` (`168`): `Amazing Mummies`, `My Bones`, `What Lives in This Hole?`, `Our Five Senses`
- `folktale_fairy_fable` (`152`): `Rapunzel`, `The Empty Pot`, `Troll Bridge`, `The Stonecutter`, `Cinderella`
- `history_biography_civics` (`127`): `Abigail Adams`, `A President's Day`, `Dr. King's Memorial`, `American Symbols`
- `animal_nonfiction` (`121`): `Miles the Nile Crocodile`, `Scorpions`, `Cockroaches`, `Flies`, `Elephants: Giant Mammals`
- `social_emotional_moral_choice` (`118`): `Rude Robot`, `New Rule!`, `Cool as a Cuke`, `Doing the Right Thing`

Planning conclusion:

- Theme expansion should start from title/book-anchored families, not broad body-text heuristics.
- The residual bucket is still heterogeneous and should not be force-mapped in a single patch.

## 11. unknown_pattern Analysis

Cross-level high-signal clusters:

- `simple_declarative_svo/svc` (`1067` combined): dominant G/H root cause and best P0 target.
- `quoted_expressive_sentence` (`113`): direct speech and exclamation frames, but needs tighter gating.
- `prepositional_phrase_expansion` (`21`): ordinary declaratives with heavier PP tails.
- `compound_predicate_or_clause_chain` (`20`): short coordinated clause chains.
- `relative_clause_or_temporal_tail` (`35` combined estimate): short subordinate tails attached to otherwise normal declaratives.

Deferred pattern families:

- poetic/repetitive lines
- narrative inversion
- pronunciation/artifact-style residuals

Planning conclusion:

- The first implementation patch should not chase exotic literary structure.
- It should cover the ordinary declarative backlog first, because that is the largest low-risk reduction path.

## 12. unknown_grammar Analysis

Observed pattern:

- A meaningful share is still broad `present_simple` / linking / declarative residue from S6K1/S6M.
- A smaller but clear subset is procedural imperative grammar.
- Another share is contaminated by section-heading records and should not drive grammar broadening.

Planning conclusion:

- Grammar follow-up should be staged after theme and pattern rerun deltas.
- The only clean early grammar candidate is narrow imperative/procedural coverage.

## 13. Section Heading Policy

- `keep_warning_only = true`
- `keep_query_exclusion = true`
- `patch_needed = false`

Reason:

- S6M already showed `MIXED_TRUE_AND_AMBIGUOUS` with `likely_false_positive_count = 0`.
- G shows the same structural behavior: headings like `Introduction`, `Conclusion`, `Step 1`, country subsection labels, and nonfiction headings.

## 14. human_review_required Policy

- Treat as a derived review gate, not a direct patch target.
- Do not implement direct suppression logic.
- Expected reduction should come indirectly from `unknown_theme` and `unknown_pattern` shrinkage.

## 15. Candidate Ranking

P0:

- `THM_P0_SCI_NATURE_NONFICTION`
- `THM_P0_FOLKTALE_FAIRY_FABLE`
- `THM_P0_HISTORY_BIOGRAPHY_CIVICS`
- `THM_P0_ANIMAL_NONFICTION`
- `PAT_P0_SIMPLE_DECLARATIVE_SVO_SVC`

P1:

- `THM_P1_SOCIAL_EMOTIONAL_MORAL_CHOICE`
- `THM_P1_CULTURE_HOLIDAY_TRADITION`
- `THM_P1_FANTASY_MONSTERS_ROYALTY`
- `PAT_P1_QUOTED_EXPRESSIVE_SENTENCE`
- `PAT_P1_PREPOSITIONAL_EXPANSION`
- `PAT_P1_COMPOUND_PREDICATE_OR_CLAUSE_CHAIN`
- `PAT_P1_RELATIVE_OR_TEMPORAL_CLAUSE_TAIL`
- `GRM_P1_PRESENT_SIMPLE_AND_LINKING_FOLLOWUP`
- `GRM_P1_IMPERATIVE_PROCEDURAL`

Deferred:

- Poetry / rhyme / literary residual theme bucket
- Poetic/repetitive line pattern family
- Narrative inversion and pronunciation/artifact pattern families
- Section-heading-driven grammar residuals

## 16. Recommended Patch Order

1. Theme P0 nonfiction/civics/animal families.
2. Theme P0 folktale/fairy-tale family.
3. Pattern P0 normal declarative coverage.
4. Pattern P1 PP / compound / relative-tail follow-ups.
5. Theme P1 social-emotional / culture / fantasy families.
6. Grammar P1 imperative/procedural follow-up.
7. Re-check present-simple/linking grammar only after rerun deltas.

## 17. Deferred Candidates

- `THM_DEFER_POETRY_LITERARY_MISC`
- `PAT_DEFER_POETIC_REPETITIVE_LINE`
- `PAT_DEFER_NARRATIVE_INVERSION_AND_ARTIFACT`
- `GRM_DEFER_SECTION_HEADING_ARTIFACTS`

These are deferred because they are high ambiguity, low volume, or high pollution risk.

## 18. Implementation Guardrails For Next Task

- Keep the next task as a minimal-change implementation.
- Prefer title/book-level theme rules before lexical free-form matching.
- Keep heading exclusion logic intact.
- Do not widen queryable levels.
- Do not promote any G/H content.
- Do not broaden grammar coverage until post-pattern rerun deltas are known.
- Preserve duplicate-warning parity and traceability parity.

## 19. Delta QA Plan

Required rerun scope:

- `G`
- `H`

Required delta metrics:

- `unknown_theme_delta`
- `unknown_pattern_delta`
- `unknown_grammar_delta`
- `human_review_required_delta`
- `section_heading_delta`
- schema validation
- count parity
- seed query boundary
- authority boundary

Pass criteria:

- Target warning families must decrease after their corresponding patch.
- Untouched warning families should not regress by more than a small reviewable margin.
- `section_heading_detected` can remain stable but should not spike materially.
- `G exposed` and `H exposed` must remain `false`.
- `candidate_only` and `promotion_allowed=false` must remain unchanged.

## 20. Seed Query Layer Boundary

- Queryable levels remain `A B C D E F`.
- `G exposed = false`
- `H exposed = false`
- Status: `PASS`

## 21. Authority Boundary

- `candidate_only = PASS`
- `promotion_allowed = PASS`

## 22. Validator Results

- `python ulga/validators/validate_raz_level_discovery.py` -> `PASS`
- `python ulga/validators/validate_raz_reusable_content_seed_query_layer.py` -> `PASS`
- `python ulga/validators/validate_raz_downstream_discovery_drift.py` -> `PASS_WITH_WARNINGS`
- `must_fix_count = 0`

## 23. Plan Status

`PASS_WITH_WARNINGS`

## 24. Risk Level

`Medium`

Reason:

- The patch plan is actionable, but several literary and residual buckets remain unsafe for broad automation.

## 25. Decision For Next Stage

`RUN_GH_TARGETED_TAXONOMY_AND_PATTERN_PATCH_IMPLEMENTATION`

## 26. Next Recommended Task

`RAZ-S6P_GH_TargetedTaxonomyAndPatternPatchImplementation`

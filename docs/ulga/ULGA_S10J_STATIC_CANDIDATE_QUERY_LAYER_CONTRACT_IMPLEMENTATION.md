# ULGA-S10J Static Candidate Query Layer Contract Implementation

## 1. Scope

Implemented the full static candidate query layer defined by S10I.

- No upstream ranking mutation
- No upstream view mutation
- No adaptive behavior
- Static-only request validation enforced

## 2. S10I Carryover

S10I warnings are preserved in the implementation through derived-field warnings, view warnings, and static-only guardrails.

- Grammar remains indirect rather than first-class
- Reinforcement provenance remains reference-only
- `source_artifact`, `bridge_reason`, `supporting_authority_layer`, and `node_type` remain derived response fields
- `theme_scoped_view`, `reading_bridge_view`, and `dialogue_bridge_view` warnings are surfaced, not suppressed
- `view_score` remains explicitly policy-adjusted
- raw ranking direct curriculum use remains blocked

## 3. Files Created

- `ulga/query/__init__.py`
- `ulga/query/static_candidate_query_layer.py`
- `ulga/validators/validate_static_candidate_query_layer.py`
- `tests/ulga/test_static_candidate_query_layer.py`
- `docs/ulga/ULGA_S10J_STATIC_CANDIDATE_QUERY_LAYER_CONTRACT_IMPLEMENTATION.md`
- `ulga/reports/static_candidate_query_layer_summary.json`
- `ulga/reports/static_candidate_query_layer_validation.json`

## 4. Files Modified

- none outside S10J-created files

## 5. Query Functions Implemented

- `query_static_candidates`
- `get_static_ranking_view`
- `get_top_candidates`
- `get_candidates_by_theme`
- `get_candidates_by_node_type`
- `get_candidate_explanation`
- `get_reading_bridge_candidates`
- `get_dialogue_bridge_candidates`
- `get_a1_safe_candidates`

## 6. Request Schema Implementation

Canonical request dispatcher implemented with `query_type`, `view_name`, `filters`, `limit`, `offset`, `include_explanation`, `include_score_breakdown`, and `static_only`.

## 7. Response Schema Implementation

Canonical success and error response envelopes implemented with deterministic `query_metadata`, canonical candidate fields, and structured errors.

## 8. Derived Field Implementation

- `node_type`: derived from `candidate_type`
- `source_artifact`: derived from static view source
- `bridge_reason`: derived from `view_name`
- `supporting_authority_layer`: derived from candidate family, themes, explain tokens, and raw score breakdown
- level fields: `cefr`, `level`, `internal_level`, `level_family`, `level_band`, `level_source`

## 9. Multi-Level Coverage Matrix

Generated into `ulga/reports/static_candidate_query_layer_summary.json`.

Coverage summary:

- `A1`: supported_by_cefr_only
- `A1+`: requires_internal_band_mapping
- `A2`: supported_by_cefr_only
- `A2+`: requires_internal_band_mapping
- `B1`: supported_by_cefr_only
- `B1+`: requires_internal_band_mapping
- `B2`: partial support concentrated in `theme_scoped_view`
- `B2+`: requires_internal_band_mapping with sparse upstream coverage
- `C1`: partial support concentrated in `theme_scoped_view`
- `C2`: missing in current downstream views

## 10. Warning Code Registry

Central warning registry implemented in `ulga/query/static_candidate_query_layer.py`.

- warning code count: `20`
- required warning codes missing: `[]`

## 11. Static-only Guardrails

Forbidden adaptive / learner-specific request fields are rejected.

- `learner_id` rejected
- `student_id` rejected
- `mastery` rejected
- `adaptive` rejected
- `static_only=false` rejected
- raw ranking curriculum use blocked through warning-bearing diagnostic path only

## 12. Score Policy

`raw_static_score` and `view_score` are returned separately.

- no ranking recomputation
- no reranking
- filtering preserves upstream order
- `view_score` is never presented as mastery or personalization

## 13. Candidate Explanation Implementation

Explanation schema is built only from static artifacts and never references learner-specific state.

- `why_this_candidate`
- `why_this_score`
- `which_authority_supports_it`
- `which_bridge_produced_it`
- `which_filters_can_retrieve_it`
- `score_breakdown_summary`
- `view_policy_summary`
- `known_limitations`

## 14. Validator Result

`python ulga\validators\validate_static_candidate_query_layer.py`

- result: `PASS`
- validation report: `ulga/reports/static_candidate_query_layer_validation.json`

## 15. Test Result

Targeted:

- `python -m pytest tests\ulga\test_static_candidate_query_layer.py -q`
- result: `25 passed`

Broader:

- `python -m pytest tests\ulga\ -q`
- result: timed out after `124` seconds

## 16. Known Warnings

- derived fields remain derived, not upstream source truth
- `theme_scoped_view` remains heuristic
- `reading_bridge_view` needs tuning
- `dialogue_bridge_view` needs tuning
- `view_score` is policy-adjusted

## 17. Blocked / Forbidden Features

- learner-specific joins
- mastery filters
- adaptive behavior
- raw ranking direct curriculum use

## 18. Decision

`S10J_RESULT = PASS_WITH_WARNINGS`

- `STATIC_ONLY_INTEGRITY = PASS`
- `ADAPTIVE_DEPENDENCY_COUNT = 0`
- `QUERY_FUNCTIONS_IMPLEMENTED = 9`
- `REQUIRED_QUERY_FUNCTIONS_MISSING = 0`
- `WARNING_REGISTRY_COMPLETE = true`

## 19. Recommended Next Task

`ULGA-S10K_StaticCandidateQueryLayer_QA`

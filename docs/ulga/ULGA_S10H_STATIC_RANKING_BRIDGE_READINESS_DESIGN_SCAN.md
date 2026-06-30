# ULGA-S10H Static Ranking Bridge Readiness Design Scan

## 1. Scope

READ-ONLY / DESIGN SCAN ONLY

- No ranking implementation
- No adaptive planner
- No learner_state dependency
- No graph/report mutation

## 2. Files Inspected

present_inputs:

- `ulga/graph/static_candidate_ranking.json`
- `ulga/reports/static_candidate_ranking_summary.json`
- `ulga/reports/static_candidate_ranking_quality_audit.json`
- `ulga/graph/static_candidate_ranking_views.json`
- `ulga/reports/static_candidate_ranking_views_summary.json`
- `ulga/graph/exposure_mapping_bridge.json`
- `ulga/reports/exposure_mapping_bridge_summary.json`
- `ulga/graph/learner_exposure_evidence.json`
- `ulga/reports/learner_exposure_evidence_summary.json`
- `ulga/graph/reinforcement_candidate_expansion.json`
- `ulga/reports/reinforcement_candidate_expansion_summary.json`

missing_inputs:

- none

optional_inputs:

- `docs/ulga/ULGA_S10E_STATIC_CANDIDATE_RANKING_BALANCING_CONTRACT_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S10F_STATIC_CANDIDATE_RANKING_VIEWS_IMPLEMENTATION.md`
- `docs/ulga/ULGA_S10G_STATIC_CANDIDATE_RANKING_VIEWS_QA_AUDIT.md`
- `ulga/reports/static_candidate_ranking_views_quality_audit.json`
- `ulga/builders/build_static_candidate_ranking.py`
- `ulga/builders/build_static_candidate_ranking_views.py`
- `ulga/validators/validate_static_candidate_ranking.py`
- `ulga/validators/validate_static_candidate_ranking_views.py`

## 3. Current Static Ranking Position

Current sequence:

`S10A~S10D ranking readiness and QA`
-> `S10E balancing contract`
-> `S10F ranking views implementation`
-> `S10G ranking views QA audit`
-> `S10H Bridge Readiness`
-> `S10I Static Candidate Query Layer`

Current position:

- S10C raw static ranking exists and is traceable.
- S10D marks raw ranking `PASS_WITH_WARNINGS` because raw top-N is chunk-heavy and duplicate-prone.
- S10F adds deterministic static views without mutating raw ranking.
- S10G confirms view-layer downstream readiness is viable but not warning-free.

## 4. Artifact Presence Result

- `artifact_presence = PASS`
- `missing_artifacts = []`
- `risk_level = LOW`

Rationale:

- All required core artifacts are present.
- Raw ranking contains `11997` active candidates and `8703` blocked candidates.
- Views payload exists with required named views and static/offline generation metadata.

## 5. Bridge Completeness Result

covered_authorities:

- `Vocabulary`
- `Chunk`
- `Theme`
- `Pattern`

partial_authorities:

- `Grammar`
- `Reinforcement`

missing_authorities:

- none

not_applicable_authorities:

- `Exposure`

bridge_gap_count:

- `2`

bridge_gaps:

- `Grammar` is only indirectly exposed through `dependency_readiness_score`, `grammar_refs`-derived explains, and chunk grammar metadata. It is not first-class in ranking/view rows.
- `Reinforcement` exists as a scored signal and as a separate expansion artifact, but ranking/view entries do not carry explicit reinforcement provenance fields beyond explain tokens.

Assessment notes:

- `Vocabulary`, `Chunk`, `Pattern`, and `Theme` are directly queryable from candidate/view rows via `candidate_type`, `theme_refs`, `label`, `level`, `source_explain`, and per-view membership.
- `Exposure` was inspected but remains learner-specific. Under static-only policy it should not be bridged into S10I query behavior, so it is `not_applicable`, not a static blocker.

bridge_completeness:

- `PASS_WITH_WARNINGS`

## 6. Signal Traceability Result

| Signal | Status | Source Artifact | Traceability Note | Risk |
| --- | --- | --- | --- | --- |
| frequency signal | traceable | `ulga/graph/static_candidate_ranking.json` | Present in `score_breakdown.frequency_score`; explain tokens distinguish vocabulary authority, chunk proxy, and inferred pattern frequency. | LOW |
| theme signal | traceable | `ulga/graph/static_candidate_ranking.json` | Present in `theme_refs` and `score_breakdown.theme_spiral_score`; explain tokens identify theme-spiral origin. | LOW |
| pattern signal | traceable | `ulga/graph/static_candidate_ranking.json` | Pattern candidates are explicit via `candidate_type=pattern_candidate` and pattern-specific explain tokens. | LOW |
| chunk signal | traceable | `ulga/graph/static_candidate_ranking.json` | Chunk candidates are explicit via `candidate_type=chunk_candidate` and chunk-specific explain tokens. | LOW |
| grammar signal | partially_traceable | `ulga/graph/static_candidate_ranking.json`, `ulga/builders/build_static_candidate_ranking.py` | Grammar contribution is represented indirectly through dependency readiness and `dependency_readiness_from_grammar_refs`; not exposed as a separate candidate field. | MEDIUM |
| reinforcement signal | partially_traceable | `ulga/graph/static_candidate_ranking.json`, `ulga/graph/reinforcement_candidate_expansion.json` | `reinforcement_score` is explicit, but per-candidate reinforcement provenance is mostly encoded in explain strings rather than structured bridge fields. | MEDIUM |
| exposure signal | not_applicable | `ulga/graph/learner_exposure_evidence.json` | Exposure is learner-bound and intentionally outside static-only ranking/query scope. | LOW |
| coverage signal | partially_traceable | `ulga/graph/static_candidate_ranking_views.json`, `ulga/reports/static_candidate_ranking_views_summary.json` | Coverage is enforced through view mix targets and theme-scoped protection rules, but not emitted as a named per-candidate score component. | MEDIUM |
| balancing signal | traceable | `ulga/graph/static_candidate_ranking_views.json` | `view_score`, `view_policy_applied`, and `balance_adjustments` make downstream balancing auditable. | LOW |

signal_traceability:

- `PASS_WITH_WARNINGS`

untraceable_signal_count:

- `0`

## 7. Static Independence Result

static_independence:

- `PASS`

adaptive_dependency_count:

- `0`

adaptive_dependency_findings:

- none

Inspection result by forbidden dependency:

- `learner_state`: not found in ranking/views payloads; explicitly forbidden by validators.
- `mastery`: not found.
- `adaptive planner`: not found.
- `runtime personalization`: not found.
- `student-specific score`: not found.
- `assessment feedback`: not found.
- `event-log feedback`: not found.

Supporting evidence:

- `static_candidate_ranking.json` has `adaptive_enabled = false`.
- `static_candidate_ranking_views.json` has `adaptive_enabled = false` and `generation_mode = static_offline_view_construction`.
- Ranking and view validators recursively scan for forbidden adaptive keywords including `learner_state`, `mastery`, `student_id`, `learner_id`, and personalized exposure markers.

## 8. Query Readiness Result

query_readiness:

- `PASS_WITH_WARNINGS`

query_ready:

- `true`

s10i_required_views:

- `balanced_global_view`
- `a1_safe_view`
- `theme_scoped_view`
- `reading_bridge_view`
- `dialogue_bridge_view`
- `pattern_first_view`
- `vocabulary_first_view`
- `chunk_safe_view`
- `deduplicated_view`

missing_views:

- none

Query capability assessment:

- `get_top_candidates(level, theme, limit)`: viable via `view_rank`, `level`, `theme_refs`, and named views.
- `get_candidates_by_node_type(node_type)`: viable, but current first-class field is `candidate_type`; S10I should normalize `node_type` to this contract.
- `get_candidates_by_theme(theme)`: viable through `theme_scoped_view` and `theme_refs`.
- `get_candidate_explanation(candidate_id)`: viable through `raw_candidate_id`, `source_explain`, `balance_adjustments`, `view_policy_applied`, `raw_static_score`, and `view_score`.
- `get_static_ranking_view(view_name)`: viable because view names are explicit and stable.

missing_query_capabilities:

- no first-class per-candidate `source_artifact` field
- no first-class per-candidate `bridge_reason` field
- no first-class per-candidate `supporting_authority_layer` field
- no first-class `node_type` alias separate from `candidate_type`

query_blockers:

- none

Readiness caveats:

- `reading_bridge_view` and `dialogue_bridge_view` are structurally queryable but S10G QA marked them `NEEDS_TUNING`.
- `theme_scoped_view` is queryable, but semantic relevance is still heuristic and sometimes noisy.

## 9. Explainability Readiness Result

explainability_readiness:

- `PASS_WITH_WARNINGS`

Explainability status:

- `why this candidate`: mostly answerable from `raw_rank`, `view_rank`, `candidate_type`, `theme_refs`, and view membership.
- `why this score`: answerable from `static_score` or `view_score` plus `score_breakdown` or `balance_adjustments`.
- `which authority supports it`: partly answerable from `candidate_type`, `source_explain`, and `theme_refs`, but not via a dedicated authority field.
- `which bridge produced it`: partly answerable at view level through `view_policy_applied`; not first-class for reinforcement or grammar bridge provenance.
- `which filters can retrieve it`: answerable from `level`, `candidate_type`, `theme_refs`, `view_name`, and `dedup_group_id`.

explainability_gaps:

- raw ranking candidate rows do not carry explicit `source_artifact` file paths per candidate
- supporting authority layer is inferred, not first-class
- grammar contribution is indirect rather than separately enumerated
- reinforcement provenance is tokenized in explain strings instead of structured bridge records on each ranking/view row
- theme-scoped semantic match reason is not emitted as a dedicated field

## 10. Risks

blocking_risks:

- none

non_blocking_warnings:

- Raw S10C ranking remains unsafe for direct top-N curriculum use because of chunk dominance and duplicate labels.
- `reading_bridge_view` is structurally ready but QA says it still lacks enough pattern support in top windows.
- `dialogue_bridge_view` remains chunk-heavy and has elevated opaque chunk ratio.
- Theme-scoped views are present but semantic relevance is heuristic; examples show false-positive theme matches.
- More than 80% of many view scores exceed raw scores, so S10I should treat `view_score` as downstream policy output, not source truth.

future_adaptive_risks:

- S10I must not directly join learner exposure or learner reinforcement artifacts into static query responses.
- Exposure-related artifacts contain `learner_id`; accidental reuse would break static-only integrity.

documentation_gaps:

- No explicit query contract yet defines canonical response shape for `get_candidate_explanation(candidate_id)`.
- No first-class field names yet exist for `source_artifact`, `bridge_reason`, or `supporting_authority_layer`.
- `node_type` versus `candidate_type` normalization should be fixed in S10I contract text.

## 11. Decision

S10H_RESULT = `PASS_WITH_WARNINGS`

STATIC_ONLY_INTEGRITY = `PASS`

ADAPTIVE_DEPENDENCY_COUNT = `0`

BRIDGE_GAP_COUNT = `2`

QUERY_READY = `true`

promotion_recommendation =

- `ALLOW_S10I_WITH_WARNINGS`

Decision rationale:

- All core artifacts are present.
- No adaptive dependency was found in the static route.
- Query path is viable using existing view structures.
- Remaining issues are explainability field-shape gaps and view-quality warnings, not hard blockers.

## 12. Recommended Next Task

`ULGA-S10I_StaticCandidateQueryLayer_DesignScan`

Recommended S10I focus:

- define a query contract that normalizes `candidate_type` as `node_type`
- expose `source_artifact`, `bridge_reason`, and `supporting_authority_layer` as derived query response fields without mutating upstream artifacts
- keep learner exposure and learner-specific reinforcement data explicitly out of static query behavior

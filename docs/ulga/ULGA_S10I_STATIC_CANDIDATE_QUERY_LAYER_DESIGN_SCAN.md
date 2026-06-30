# ULGA-S10I Static Candidate Query Layer Design Scan

## 1. Scope

READ-ONLY / DESIGN SCAN ONLY / QUERY CONTRACT DESIGN ONLY

- No query implementation
- No ranking mutation
- No adaptive behavior
- No learner_state dependency
- No graph/report mutation

## 2. S10H Carryover

- `S10H_RESULT = PASS_WITH_WARNINGS`
- `STATIC_ONLY_INTEGRITY = PASS`
- `ADAPTIVE_DEPENDENCY_COUNT = 0`
- `BRIDGE_GAP_COUNT = 2`
- `QUERY_READY = true`
- `PROMOTION_RECOMMENDATION = ALLOW_S10I_WITH_WARNINGS`

S10H warnings carried into S10I:

- Grammar not first-class
- Reinforcement provenance not first-class
- `source_artifact` missing
- `bridge_reason` missing
- `supporting_authority_layer` missing
- `node_type` not normalized separately from `candidate_type`
- `reading_bridge_view` / `dialogue_bridge_view` / `theme_scoped_view` still need tuning

## 3. Files Inspected

present_inputs:

- `ulga/graph/static_candidate_ranking.json`
- `ulga/reports/static_candidate_ranking_summary.json`
- `ulga/reports/static_candidate_ranking_quality_audit.json`
- `ulga/graph/static_candidate_ranking_views.json`
- `ulga/reports/static_candidate_ranking_views_summary.json`
- `ulga/reports/static_candidate_ranking_views_quality_audit.json`
- `docs/ulga/ULGA_S10E_STATIC_CANDIDATE_RANKING_BALANCING_CONTRACT_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S10F_STATIC_CANDIDATE_RANKING_VIEWS_IMPLEMENTATION.md`
- `docs/ulga/ULGA_S10G_STATIC_CANDIDATE_RANKING_VIEWS_QA_AUDIT.md`
- `docs/ulga/ULGA_S10H_STATIC_RANKING_BRIDGE_READINESS_DESIGN_SCAN.md`
- `ulga/graph/exposure_mapping_bridge.json`
- `ulga/reports/exposure_mapping_bridge_summary.json`
- `ulga/graph/learner_exposure_evidence.json`
- `ulga/reports/learner_exposure_evidence_summary.json`
- `ulga/graph/reinforcement_candidate_expansion.json`
- `ulga/reports/reinforcement_candidate_expansion_summary.json`

missing_inputs:

- none

optional_inputs:

- `ulga/builders/build_static_candidate_ranking.py`
- `ulga/builders/build_static_candidate_ranking_views.py`
- `ulga/validators/validate_static_candidate_ranking.py`
- `ulga/validators/validate_static_candidate_ranking_views.py`

## 4. Static Query Layer Position

Static query layer position:

`S10F Static Views`
-> `S10G View QA`
-> `S10H Bridge Readiness`
-> `S10I Query Layer Contract`
-> `S10J Query Layer Implementation or Response Schema QA`

Current position:

- S10F already materializes deterministic static views.
- S10G already proves downstream retrieval is viable but warning-bearing.
- S10H already proves the bridge path is static-only and query-ready.
- S10I should therefore define a query contract on top of existing views, not on top of raw ranking top-N.

## 5. Query Surface Contract

Supported query functions:

### `get_static_ranking_view(view_name, limit=None, offset=0)`

- purpose: fetch one named static view for deterministic downstream consumption
- default view: none; `view_name` required
- input parameters: `view_name`, `limit`, `offset`, `include_explanation`, `include_score_breakdown`
- allowed filters: none beyond pagination
- sorting behavior: preserve upstream `view_rank`
- response shape: `query_metadata` + ordered `candidates`
- static-only restrictions: `static_only=true` required; raw ranking direct view is diagnostic only
- warnings: `theme_scoped_view`, `reading_bridge_view`, and `dialogue_bridge_view` should return contract warnings

### `get_top_candidates(level=None, cefr=None, theme=None, node_type=None, candidate_type=None, view_name="balanced_global_view", limit=20)`

- purpose: default general retrieval entrypoint
- default view: `balanced_global_view`
- input parameters: `level`, `cefr`, `theme`, `node_type`, `candidate_type`, `view_name`, `limit`, `offset`
- allowed filters: `level`, `cefr`, `theme`, `node_type`, `candidate_type`
- sorting behavior: sort by `view_rank`; do not recompute score
- response shape: canonical response schema with derived fields
- static-only restrictions: reject learner/mastery/adaptive filters
- warnings: if `view_name` is omitted and caller asks for raw ranking top-N, return `NOT_ALLOWED_FOR_CURRICULUM_USE`

### `get_candidates_by_theme(theme, level=None, view_name="theme_scoped_view", limit=20)`

- purpose: theme-filtered retrieval
- default view: `theme_scoped_view`
- input parameters: `theme`, `level`, `view_name`, `limit`, `offset`
- allowed filters: `theme`, `level`
- sorting behavior: preserve `view_rank`
- response shape: canonical response schema
- static-only restrictions: no learner-specific theme preference allowed
- warnings: add `THEME_SCOPED_VIEW_HEURISTIC_RELEVANCE_WARNING`

### `get_candidates_by_node_type(node_type, level=None, theme=None, view_name=None, limit=20)`

- purpose: node-family retrieval using normalized type alias
- default view: `balanced_global_view` unless `theme` is present, then `theme_scoped_view`
- input parameters: `node_type`, `level`, `theme`, `view_name`, `limit`, `offset`
- allowed filters: `node_type`, `level`, `theme`
- sorting behavior: preserve selected view ordering
- response shape: canonical response schema
- static-only restrictions: `node_type` is derived from `candidate_type`; no adaptive routing
- warnings: if `node_type` maps to unsupported or unknown family, return empty result with warning

### `get_candidate_explanation(candidate_id, view_name=None)`

- purpose: expose candidate-level explanation without adaptive reasoning
- default view: search named view if provided; otherwise search known static views by `raw_candidate_id`
- input parameters: `candidate_id`, `view_name`, `include_score_breakdown`
- allowed filters: none
- sorting behavior: exact candidate lookup, not list ranking
- response shape: single-candidate response with full explanation object
- static-only restrictions: explanation may only use static artifacts
- warnings: return derived-field warnings when authority/bridge provenance is inferred

### `get_reading_bridge_candidates(level=None, theme=None, limit=20)`

- purpose: reading-support retrieval for future reading bridge consumers
- default view: `reading_bridge_view`
- input parameters: `level`, `theme`, `limit`, `offset`
- allowed filters: `level`, `theme`
- sorting behavior: preserve `view_rank`
- response shape: canonical response schema
- static-only restrictions: no reading-personalization logic
- warnings: add `READING_BRIDGE_VIEW_NEEDS_TUNING`

### `get_dialogue_bridge_candidates(level=None, theme=None, limit=20)`

- purpose: dialogue-support retrieval for future dialogue bridge consumers
- default view: `dialogue_bridge_view`
- input parameters: `level`, `theme`, `limit`, `offset`
- allowed filters: `level`, `theme`
- sorting behavior: preserve `view_rank`
- response shape: canonical response schema
- static-only restrictions: no learner-specific dialogue selection
- warnings: add `DIALOGUE_BRIDGE_VIEW_NEEDS_TUNING`

### `get_a1_safe_candidates(theme=None, node_type=None, limit=20)`

- purpose: safe early-level retrieval
- default view: `a1_safe_view`
- input parameters: `theme`, `node_type`, `limit`, `offset`
- allowed filters: `theme`, `node_type`
- sorting behavior: preserve `view_rank`
- response shape: canonical response schema
- static-only restrictions: no weak-skill or mastery remediation logic
- warnings: if theme is requested, add theme heuristic warning when resolved through theme-scoped filtering

## 6. View Selection Policy

- `balanced_global_view`: default general query view; preferred for mixed curriculum-safe retrieval.
- `a1_safe_view`: use for A1 / pre-A1 retrieval; never fallback to raw ranking for beginner use.
- `theme_scoped_view`: use when the caller’s main axis is theme; return semantic relevance warning because the current matching remains heuristic.
- `reading_bridge_view`: use for reading-support retrieval only; return tuning warning because top windows remain vocabulary-heavy.
- `dialogue_bridge_view`: use for dialogue-support retrieval only; return tuning warning because top windows remain chunk-heavy and opaque.
- `pattern_first_view`: use when sentence-frame usability is more important than mixed balance.
- `vocabulary_first_view`: use when vocabulary-first retrieval is explicitly desired.
- `chunk_safe_view`: use for chunk retrieval with dedup and opacity mitigation.
- `deduplicated_view`: use when duplicate label collision is the primary risk and exact candidate family mix is secondary.

Mandatory policy:

- Prefer view-based query over raw `static_candidate_ranking.json` top-N.
- Raw ranking direct curriculum use is `NOT_ALLOWED`.
- Raw ranking may be exposed only as a clearly labeled diagnostic/admin surface.

## 7. Request Schema

Canonical request schema:

```json
{
  "query_type": "get_top_candidates",
  "view_name": "balanced_global_view",
  "filters": {
    "level": "A1",
    "cefr": "A1",
    "theme": "Home",
    "node_type": "vocabulary",
    "candidate_type": null,
    "ranking_bucket": null
  },
  "limit": 20,
  "offset": 0,
  "include_explanation": true,
  "include_score_breakdown": true,
  "static_only": true
}
```

Required request fields:

- `query_type`
- `view_name`
- `filters`
- `limit`
- `offset`
- `include_explanation`
- `include_score_breakdown`
- `static_only`

Validation rules:

- `static_only` must equal `true`
- reject `learner_id`
- reject `student_id`
- reject `mastery`
- reject `learner_state`
- reject `adaptive`
- reject `personalized`
- reject `assessment_feedback`
- reject `event_log`
- reject `runtime_profile`
- reject negative `limit` or `offset`
- clamp `limit` to contract-safe maximum such as `100`
- if both `node_type` and `candidate_type` are supplied and conflict, reject request
- if `view_name` is omitted for node/theme queries, default deterministically rather than inferring from user profile

## 8. Response Schema

Canonical response schema:

```json
{
  "query_metadata": {
    "query_type": "get_top_candidates",
    "view_name": "balanced_global_view",
    "static_only": true,
    "adaptive_enabled": false,
    "source_artifact": "ulga/graph/static_candidate_ranking_views.json",
    "limit": 20,
    "offset": 0,
    "result_count": 20,
    "warnings": []
  },
  "candidates": [
    {
      "candidate_id": "chunk:go_out:safe_chunk_001519",
      "raw_candidate_id": "chunk:go_out:safe_chunk_001519",
      "label": "go out",
      "node_type": "chunk",
      "candidate_type": "chunk_candidate",
      "level": "A1",
      "cefr": "A1",
      "theme_refs": ["theme:a1_daily_life_and_routines"],
      "view_rank": 1,
      "raw_rank": 10,
      "raw_static_score": 0.914,
      "view_score": 0.934,
      "score_type": "view_policy_adjusted",
      "source_artifact": "ulga/graph/static_candidate_ranking_views.json",
      "bridge_reason": "chunk_safe_static_view_membership",
      "supporting_authority_layer": ["Chunk", "Theme", "Reinforcement"],
      "explanation": {},
      "warnings": []
    }
  ]
}
```

Required response fields:

- `query_metadata`
- `candidates`
- `candidate_id`
- `raw_candidate_id`
- `label`
- `node_type`
- `candidate_type`
- `level`
- `cefr`
- `theme_refs`
- `view_rank`
- `raw_rank`
- `raw_static_score`
- `view_score`
- `score_type`
- `source_artifact`
- `bridge_reason`
- `supporting_authority_layer`
- `explanation`
- `warnings`

Response behavior:

- `candidate_id` should equal `view_candidate_id` when a view row is returned.
- `cefr` is an alias of `level` unless a future normalized CEFR field differs.
- `query_metadata.source_artifact` should name the primary artifact used for the response, not every inspected artifact.
- `warnings` may exist at both metadata level and candidate level.

## 9. Derived Field Policy

### `node_type`

Derived from `candidate_type`:

- `vocabulary_candidate -> vocabulary`
- `chunk_candidate -> chunk`
- `pattern_candidate -> pattern`
- `grammar_candidate -> grammar`
- `theme_candidate -> theme`
- `sentence_candidate -> sentence`
- `dialogue_candidate -> dialogue`
- `reading_candidate -> reading`

Fallback:

- `node_type = "unknown"`
- warning: `NODE_TYPE_DERIVED_FROM_UNKNOWN_CANDIDATE_TYPE`

### `source_artifact`

Derivation policy:

- default response source: `ulga/graph/static_candidate_ranking_views.json`
- if raw score breakdown is included: also cite `ulga/graph/static_candidate_ranking.json` in explanation metadata
- if response mentions view QA warning: cite `ulga/reports/static_candidate_ranking_views_quality_audit.json`
- if response mentions reinforcement provenance: cite `ulga/graph/reinforcement_candidate_expansion.json` as reference-only context, not joined payload
- if learner exposure artifact is requested: do not join it; return warning only

### `bridge_reason`

Derived from:

- `view_name`
- `view_policy_applied`
- `balance_adjustments`
- `source_explain`
- `candidate_type`
- `theme_refs`

Allowed normalized values:

- `balanced_global_static_view_membership`
- `a1_safe_static_view_membership`
- `theme_scoped_static_view_membership`
- `reading_bridge_static_view_membership`
- `dialogue_bridge_static_view_membership`
- `pattern_first_static_view_membership`
- `vocabulary_first_static_view_membership`
- `chunk_safe_static_view_membership`
- `deduplicated_static_view_membership`

### `supporting_authority_layer`

Derived, not upstream source truth.

Derivation rules:

- `vocabulary_candidate` -> add `Vocabulary`
- `chunk_candidate` -> add `Chunk`
- `pattern_candidate` -> add `Pattern`
- `theme_refs` present -> add `Theme`
- `dependency_readiness_from_grammar_refs` in explain -> add `Grammar`
- `reinforcement_score > 0` in raw breakdown or reinforcement explain token present -> add `Reinforcement`

Important constraint:

- `supporting_authority_layer` is an interpretive derived field for query usability.
- It must not be presented as canonical upstream provenance.

## 10. Score Interpretation Policy

Definitions:

- `raw_static_score` = score from raw static candidate ranking
- `view_score` = downstream policy-adjusted score from static candidate ranking views
- `score_type` = `raw_static_score` / `view_policy_adjusted` / `derived_query_score`

Rules:

- Do not present `view_score` as raw authority score.
- Do not present `view_score` as learner mastery.
- Do not present `view_score` as personalized recommendation.
- Do not compare `view_score` across unrelated views unless explicitly documented.
- Do not use raw ranking top-N directly for curriculum selection.
- If both scores exist, show both.
- If only one score exists, add warning such as `MISSING_RAW_OR_VIEW_SCORE_PAIR`.

Recommended query interpretation:

- list ordering should follow upstream `view_rank`
- score fields are explanatory metadata, not query-time recomputation targets
- S10I should avoid inventing any new computed score beyond field normalization; `derived_query_score` should remain reserved for future explicit contract revisions

## 11. Candidate Explanation Schema

Canonical explanation schema:

```json
{
  "why_this_candidate": "",
  "why_this_score": "",
  "which_authority_supports_it": [],
  "which_bridge_produced_it": "",
  "which_filters_can_retrieve_it": [],
  "score_breakdown_summary": {},
  "view_policy_summary": {},
  "known_limitations": []
}
```

Explanation rules:

- generate only from static artifacts
- may use `source_explain`, `balance_adjustments`, `view_policy_applied`, `theme_refs`, `candidate_type`, `raw_rank`, `view_rank`, `raw_static_score`, and `view_score`
- may summarize raw score breakdown when `include_score_breakdown=true`
- must not reference learner mastery, student history, personal weakness, adaptive next-best-node logic, or runtime behavior

Recommended field population:

- `why_this_candidate`: summarize view membership + type + level/theme fit
- `why_this_score`: summarize raw score and downstream adjustments
- `which_authority_supports_it`: emit derived authority layers
- `which_bridge_produced_it`: emit normalized `bridge_reason`
- `which_filters_can_retrieve_it`: include `view_name`, `level`, `theme`, `node_type`, `candidate_type`
- `score_breakdown_summary`: raw ranking components when available
- `view_policy_summary`: `view_policy_applied` + `balance_adjustments`
- `known_limitations`: list derivation caveats and current view QA warnings

## 12. Static-only Guardrails

Reject request if it contains:

- `learner_id`
- `student_id`
- `mastery`
- `learner_state`
- `adaptive`
- `personalized`
- `assessment_feedback`
- `event_log`
- `runtime_profile`

Reject request if:

- `static_only != true`

Warning-only cases:

- query uses `reading_bridge_view`
- query uses `dialogue_bridge_view`
- query uses `theme_scoped_view`
- query requests raw ranking direct top-N
- query requests `source_artifact` for learner exposure artifact

Raw ranking direct top-N rule:

- return `NOT_ALLOWED_FOR_CURRICULUM_USE`
- may be exposed only as diagnostic/admin retrieval with clear labeling

Additional guardrails:

- do not join `learner_exposure_evidence.json` into candidate responses
- do not join `reinforcement_candidate_expansion.json` as result rows for static ranking queries
- allow those artifacts only as documentation references for warnings/explanation metadata

## 13. Query Readiness Matrix

| Query Function | Backing View | Status | Warning | Blocker |
| --- | --- | --- | --- | --- |
| `get_static_ranking_view` | named view | READY | view-specific warnings may propagate | none |
| `get_top_candidates` | `balanced_global_view` | READY | score and authority fields are partly derived | none |
| `get_candidates_by_theme` | `theme_scoped_view` | READY_WITH_WARNINGS | heuristic semantic relevance | none |
| `get_candidates_by_node_type` | `balanced_global_view` or `theme_scoped_view` | READY_WITH_WARNINGS | `node_type` is derived from `candidate_type` | none |
| `get_candidate_explanation` | all views + raw ranking | READY_WITH_WARNINGS | authority and bridge provenance are derived | none |
| `get_reading_bridge_candidates` | `reading_bridge_view` | READY_WITH_WARNINGS | needs pattern support tuning | none |
| `get_dialogue_bridge_candidates` | `dialogue_bridge_view` | READY_WITH_WARNINGS | chunk-heavy and opaque chunks in top windows | none |
| `get_a1_safe_candidates` | `a1_safe_view` | READY_WITH_WARNINGS | top-20 chunk suppression may over-correct | none |

## 14. Risks and Warnings

blocking_risks:

- none

non_blocking_warnings:

- `theme_scoped_view` remains heuristically relevant rather than semantically guaranteed.
- `reading_bridge_view` still under-delivers pattern support in top windows.
- `dialogue_bridge_view` still over-delivers opaque chunks in top windows.
- `source_artifact`, `bridge_reason`, `supporting_authority_layer`, and `node_type` are derived contract fields rather than first-class upstream fields.

future_adaptive_risks:

- exposure artifacts include `learner_id`; accidental joining would break static-only integrity
- reinforcement expansion artifacts are learner-bound and must not become static query result inputs

implementation_risks:

- inconsistent client use of `node_type` vs `candidate_type` could fragment API usage if not normalized centrally
- callers may incorrectly treat `view_score` as canonical raw ranking score
- clients may attempt to use diagnostic raw ranking endpoints as curriculum endpoints unless explicitly blocked

## 15. Decision

`S10I_RESULT = PASS_WITH_WARNINGS`

`IMPLEMENTATION_RECOMMENDATION = ALLOW_S10J_WITH_WARNINGS`

Decision basis:

- required artifacts exist
- S10H carryover is recorded
- query functions are definable on top of current view contract
- request schema, response schema, derived field policy, score policy, explanation schema, and static guardrails are all definable without adaptive dependency
- remaining concerns are QA/tuning warnings and derived-field caveats, not blockers

## 16. Recommended Next Task

`ULGA-S10J_StaticCandidateQueryLayer_ContractImplementation`

Implementation boundary for S10J:

- implement contract and response normalization only
- do not mutate ranking/view generation
- keep learner/exposure/reinforcement artifacts out of static query joins
- surface warnings from `reading_bridge_view`, `dialogue_bridge_view`, and `theme_scoped_view` as metadata rather than hiding them

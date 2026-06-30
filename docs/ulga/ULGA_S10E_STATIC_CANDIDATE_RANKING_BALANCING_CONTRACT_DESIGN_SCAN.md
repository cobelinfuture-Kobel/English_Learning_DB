# ULGA S10E Static Candidate Ranking Balancing Contract Design Scan

## 1. Task Summary

S10E defines the downstream balancing/query contract for consuming the S10C static candidate ranking baseline safely. This task is design-only. It does not rebuild ranking data, change scores, tune weights, or introduce adaptive logic.

## 2. Scope and Non-goals

Scope:

- define curriculum-usable ranking views derived from raw S10C output
- define balancing, level, theme, deduplication, and opacity policies
- define safe downstream-consumer contracts for future modules
- define what S10F should implement later

Non-goals:

- modify `static_score`
- modify S10C ranking order in-place
- generate a new balanced ranking graph now
- introduce learner personalization or adaptive planning
- consume `learner_state`, mastery, retention, assessment, attempt, review queue, planner, or personalized exposure data

## 3. S10C Baseline Recap

S10C produced a valid static ranking baseline:

- `candidate_count = 20700`
- `active_candidate_count = 11997`
- `blocked_candidate_count = 8703`
- `adaptive_leakage_detected = false`
- ranking mode remains static/offline

S10C is a candidate-pool ordering layer built from authority data only.

## 4. S10D QA Findings Recap

S10D returned `PASS_WITH_WARNINGS` and confirmed:

- `top_20 contains only one candidate_type`
- top-20 and top-50 windows are chunk-dominant
- pattern candidates are underrepresented in top-100
- some theme-scoped views have no pattern candidates
- some theme-scoped views have no vocabulary candidates
- duplicate normalized labels appear in top-ranked windows
- inferred or fallback signals are present
- adaptive leakage remains false

## 5. Problem Statement

The raw S10C ranking is valid as a static authority-derived ordering, but it is not safe to use directly as lesson order, bridge-input order, or child-facing curriculum order. Downstream modules need a balancing contract that preserves raw ranking evidence while reshaping query windows into curriculum-usable views.

## 6. Raw Ranking vs Curriculum Ranking

`raw static ranking != curriculum ranking`

The raw S10C ranking should be treated as:

- a global candidate pool
- a deterministic evidence order
- an input to downstream view construction

It should not be treated as:

- final lesson order
- final exercise order
- final reading seed order
- final planner order

S10E therefore designs downstream views, not mutations of the raw ranking.

## 7. Balancing Contract Goals

- preserve `raw_rank` and `raw_static_score`
- prevent chunk-only top windows from becoming curriculum truth
- protect pattern and vocabulary coverage
- provide A1-safe filtered windows
- provide theme-scoped windows with relevant coverage
- collapse duplicates and near-duplicates before display/use
- separate raw evidence from downstream balancing policy
- keep adaptive logic blocked

## 8. Proposed Ranking View Types

### `raw_global_view`

- purpose: debugging, auditing, and raw authority inspection
- allowed candidate types: all active candidate types
- level policy: none beyond source ranking
- theme policy: none
- candidate type mix: none
- deduplication policy: none
- chunk opacity policy: allow
- score handling: preserve `raw_rank` and `raw_static_score` only
- expected downstream consumer: auditors, diagnostics, developer tooling

### `balanced_global_view`

- purpose: general curriculum-safe mixed candidate feed
- allowed candidate types: pattern, vocabulary, chunk
- level policy: configurable `level_band` or `level_ceiling`
- theme policy: optional soft preference
- candidate type mix: enforce target mix contract
- deduplication policy: required
- chunk opacity policy: limit overrepresented opaque chunks
- score handling: preserve raw score, add future `view_rank` and design-only `view_score`
- expected downstream consumer: exercise generator, worksheet authority, general teaching flows

### `a1_safe_view`

- purpose: early-stage learner-safe ranking window
- allowed candidate types: primarily pattern and vocabulary, constrained chunks
- level policy: `level_ceiling = A1` by default
- theme policy: prefer concrete child-friendly themes
- candidate type mix: pattern/vocabulary protected, chunk capped
- deduplication policy: required
- chunk opacity policy: strict limit
- score handling: raw score preserved; opaque and inferred signals only affect future view policy
- expected downstream consumer: beginner lessons, children/Cambridge-aligned entry flows

### `theme_scoped_view`

- purpose: theme-contained ranking windows for domain teaching
- allowed candidate types: pattern, vocabulary, chunk
- level policy: same level, level ceiling, or narrow band
- theme policy: hard filter by theme refs or theme mapping
- candidate type mix: require coverage diversity when available
- deduplication policy: required inside window
- chunk opacity policy: exclude unrelated opaque chunks
- score handling: preserve raw score inside filtered pool
- expected downstream consumer: theme lessons, worksheets, thematic activities

### `reading_bridge_view`

- purpose: reading authority bridge seed selection
- allowed candidate types: pattern and vocabulary first, limited chunks
- level policy: strict or ceiling mode
- theme policy: aligned to reading topic
- candidate type mix: pattern + vocabulary dominant
- deduplication policy: required
- chunk opacity policy: strongly limited
- score handling: require future suitability flags
- expected downstream consumer: Reading Authority Bridge

### `dialogue_bridge_view`

- purpose: dialogue authority bridge seed selection
- allowed candidate types: all, with chunks allowed when conversationally useful
- level policy: strict, ceiling, or band
- theme policy: preferred when conversation topic exists
- candidate type mix: pattern support required even if chunks are included
- deduplication policy: required
- chunk opacity policy: moderate limit, conversational chunks allowed
- score handling: preserve raw score and annotate conversational suitability
- expected downstream consumer: Dialogue Authority Bridge

### `pattern_first_view`

- purpose: grammar-first teaching or assessment preparation
- allowed candidate types: pattern first, vocabulary second, chunks limited
- level policy: strict or band
- theme policy: optional
- candidate type mix: pattern floor required
- deduplication policy: required
- chunk opacity policy: strict
- score handling: future balancing may promote high-utility patterns without changing raw score
- expected downstream consumer: grammar-focused exercises, pattern assessment

### `vocabulary_first_view`

- purpose: lexical teaching or assessment preparation
- allowed candidate types: vocabulary first, pattern second, chunks limited
- level policy: strict or band
- theme policy: optional or theme-scoped
- candidate type mix: vocabulary floor required
- deduplication policy: required
- chunk opacity policy: strict
- score handling: preserve raw score, future view policy may raise concrete vocabulary visibility
- expected downstream consumer: vocabulary practice, lexical assessment, worksheets

### `chunk_safe_view`

- purpose: controlled chunk exposure without opaque overload
- allowed candidate types: chunks plus supporting pattern/vocabulary anchors
- level policy: ceiling or band
- theme policy: prefer themed or anchored chunks
- candidate type mix: chunk allowed but not dominant
- deduplication policy: required
- chunk opacity policy: explicit penalties and caps
- score handling: preserve raw score, future policy flags opacity and anchor coverage
- expected downstream consumer: phrase teaching, dialogue prep, chunk review design

### `deduplicated_view`

- purpose: display-safe or consumer-safe ranking with collapsed equivalents
- allowed candidate types: all active types
- level policy: inherited from parent view
- theme policy: inherited from parent view
- candidate type mix: inherited from parent view
- deduplication policy: canonical collapse required
- chunk opacity policy: inherited from parent view
- score handling: canonical entry preserves linked raw candidates
- expected downstream consumer: any UI or report that must avoid duplicate display rows

## 9. Candidate Type Mix Policy

Default target mix for balanced views:

```json
{
  "pattern_candidate": {
    "min_ratio": 0.25,
    "target_ratio": 0.35,
    "max_ratio": 0.50
  },
  "vocabulary_candidate": {
    "min_ratio": 0.30,
    "target_ratio": 0.40,
    "max_ratio": 0.55
  },
  "chunk_candidate": {
    "min_ratio": 0.10,
    "target_ratio": 0.25,
    "max_ratio": 0.35
  }
}
```

This is a view-construction contract target, not a scoring-formula change.

Recommended protection rules:

- top-20 `balanced_global_view` should include at least 4 pattern candidates when available
- top-20 `balanced_global_view` should include at least 6 vocabulary candidates when available
- top-20 `a1_safe_view` should include at least 5 concrete vocabulary candidates when available
- top-20 `a1_safe_view` should include at least 5 usable sentence patterns when available

## 10. Level-First Policy

Supported level-first modes:

- `strict_level`
- `level_band`
- `level_ceiling`
- `level_progressive`

Examples:

```json
{
  "strict_level": "A1",
  "level_ceiling": "A1",
  "level_band": ["A1", "A2"],
  "level_progressive": ["A1", "A1+", "A2"]
}
```

Policy guidance:

- `strict_level` is best for assessment slices or tightly bounded lessons
- `level_band` is best for mixed teaching windows that still need coherence
- `level_ceiling` is best for A1-safe or child-facing views
- `level_progressive` is best for curriculum sequences that introduce limited stretch items

## 11. A1-Safe Window Policy

Rules for `a1_safe_view`:

- level must be `A1` unless a view explicitly allows limited spillover
- prefer pattern + vocabulary pairings over standalone chunk-heavy windows
- limit opaque chunks
- avoid advanced-looking placeholders
- avoid conditional/perfect/modal-heavy labels
- avoid duplicate normalized labels
- prefer concrete child-friendly themes such as Home, Food, School, Personal, and Daily Life

Rule-based exclusion or penalty signals:

- label contains `would have`
- label contains `had known`
- label contains `conditional`
- label contains `perfect`
- label contains `sb/sth`
- label contains slash alternatives
- label is too long
- candidate type is `chunk_candidate` and the label is opaque
- level is greater than `A1`

Recommended defaults:

- chunk max ratio in A1 top-20: `0.25`
- opaque chunk max ratio in A1 top-20: `0.15`
- normalized-label uniqueness in A1 top-20: required

## 12. Theme-Scoped View Policy

Theme views should:

- filter by `theme_refs`, topic mapping, or theme hints
- prefer same parent theme
- prefer same level or a level ceiling
- require at least one pattern candidate when available
- require at least one vocabulary candidate when available
- deduplicate chunk variants
- exclude unrelated opaque chunks

Themes to support later:

- `Home`
- `Food`
- `School`
- `Travel`
- `Health`
- `Personal`
- `Daily Life`

Theme selection order:

1. direct `theme_refs`
2. same parent theme
3. mapped theme hints from authority metadata
4. label/topic heuristics only as fallback

## 13. Deduplication / Canonical Collapse Policy

Normalized-label deduplication should:

- lowercase
- replace underscores with spaces
- remove `safe_chunk` suffixes
- remove duplicated punctuation
- normalize `sb/sth` placeholder order
- trim whitespace

Policy:

- within top-20, no duplicate normalized labels
- within top-100, duplicate normalized-label ratio should be below `0.10`
- equivalent chunks should collapse into one display candidate
- canonical candidate should preserve `equivalent_ids` for validator-safe traceability

Canonical selection preference:

1. highest raw score
2. cleaner label form
3. lower CEFR level
4. stable candidate id ordering

## 14. Opaque Chunk Handling Policy

Opaque chunk signals:

- contains `sb/sth`
- contains slash alternatives
- contains bracket alternatives
- phrasal verb with movable object
- idiomatic expression
- label length above threshold
- no concrete theme anchor
- no vocabulary anchor
- no pattern bridge

Policy:

- opaque chunks are allowed in `raw_global_view`
- opaque chunks are limited in `a1_safe_view`
- opaque chunks are limited in `reading_bridge_view`
- opaque chunks may be allowed in `dialogue_bridge_view` if conversationally useful

Suggested future flags:

- `contains_sb_sth`
- `contains_slash_alternative`
- `contains_bracket_alternative`
- `movable_object_pattern`
- `idiomatic_or_low_transparency`
- `missing_theme_anchor`
- `missing_pattern_bridge`
- `missing_vocabulary_anchor`

## 15. Pattern / Vocabulary Protection Policy

Because S10D found suppression risk, downstream views should protect pattern and vocabulary visibility.

Recommended rules:

- `balanced_global_view` top-20 should include a pattern floor and vocabulary floor when available
- `theme_scoped_view` should require at least one pattern candidate when available
- `theme_scoped_view` should require at least one vocabulary candidate when available
- `reading_bridge_view` should prefer pattern + vocabulary over opaque chunks
- `pattern_first_view` and `vocabulary_first_view` should act as safety valves when mixed views under-deliver core coverage

## 16. Score Handling Policy

S10E does not change `static_score`.

Future S10F views may add:

- `view_rank`
- `view_score`
- `view_policy_applied`
- `raw_rank`
- `raw_static_score`
- `balance_adjustments`
- `dedup_group_id`
- `curriculum_suitability_flags`

Rules:

- `raw_rank` must always remain traceable
- `raw_static_score` must always remain preserved
- `view_score` is a downstream design field, not a replacement for `static_score`
- balancing policy should be explainable through explicit adjustments or flags

## 17. Inferred Signal Handling Policy

Future views should treat inferred or fallback signals explicitly, not silently.

Allowed policy options:

- `allow_with_warning`
- `penalize_in_view_score`
- `require_direct_signal_for_top_20`
- `separate_inferred_signal_count_in_report`

Recommendation:

- A1-safe and reading-oriented views should prefer direct or high-confidence signals in top-ranked windows
- inferred-heavy candidates may remain visible deeper in the pool
- view reports should expose inferred-signal counts and ratios

## 18. Downstream Consumer Contract

### Reading Authority Bridge

- use `reading_bridge_view`
- allowed candidate types: pattern, vocabulary, limited chunks
- level policy: strict level or ceiling
- theme policy: aligned to reading topic
- dedup policy: required
- required metadata: level, candidate type, theme refs, opacity flags, inferred-signal flags
- forbidden metadata: learner state, mastery, assessment history, personalized exposure

### Dialogue Authority Bridge

- use `dialogue_bridge_view`
- allowed candidate types: all, with conversational chunks allowed
- level policy: strict, ceiling, or band
- theme policy: topic-aligned when available
- dedup policy: required
- required metadata: level, candidate type, theme refs, pattern support, opacity flags
- forbidden metadata: learner state, mastery, assessment history, personalized exposure

### Exercise Generator

- use `balanced_global_view` or `theme_scoped_view`
- allowed candidate types: all active types
- level policy: band or ceiling
- theme policy: optional or hard-scoped
- dedup policy: required
- required metadata: raw rank, raw score, view policy, type mix status
- forbidden metadata: learner state, mastery, assessment history, personalized exposure

### Assessment Authority

- use `vocabulary_first_view` or `pattern_first_view` depending on target
- allowed candidate types: target-focused
- level policy: strict level
- theme policy: optional
- dedup policy: required
- required metadata: level alignment, type focus, raw traceability
- forbidden metadata: learner state, mastery, assessment history, personalized exposure

### Worksheet Authority

- use `balanced_global_view`, `theme_scoped_view`, or `a1_safe_view`
- allowed candidate types: all active types under view policy
- level policy: ceiling or band
- theme policy: often required
- dedup policy: required
- required metadata: display-safe label, theme relevance, opacity flags
- forbidden metadata: learner state, mastery, assessment history, personalized exposure

### Future Antigravity Planner

- must not use S10C raw ranking directly
- should consume balanced view outputs only after a future adaptive layer exists
- any learner-state combination remains blocked until post-S10F adaptive work

## 19. Proposed JSON Contract Shape

```json
{
  "schema_version": "ULGA_S10E_STATIC_CANDIDATE_RANKING_BALANCING_CONTRACT_V1",
  "contract_mode": "design_only",
  "source": {
    "raw_ranking": "ulga/graph/static_candidate_ranking.json",
    "quality_audit": "ulga/reports/static_candidate_ranking_quality_audit.json"
  },
  "principles": {
    "raw_static_ranking_is_not_curriculum_ranking": true,
    "do_not_modify_static_score": true,
    "adaptive_enabled": false
  },
  "views": {
    "balanced_global_view": {
      "level_policy": {
        "mode": "level_band",
        "levels": ["A1", "A2", "B1"]
      },
      "candidate_type_mix": {
        "pattern_candidate": {
          "min_ratio": 0.25,
          "target_ratio": 0.35,
          "max_ratio": 0.50
        },
        "vocabulary_candidate": {
          "min_ratio": 0.30,
          "target_ratio": 0.40,
          "max_ratio": 0.55
        },
        "chunk_candidate": {
          "min_ratio": 0.10,
          "target_ratio": 0.25,
          "max_ratio": 0.35
        }
      },
      "deduplication": {
        "normalized_label_unique_in_top_20": true,
        "collapse_equivalent_chunks": true
      },
      "opaque_chunk_policy": {
        "limit_enabled": true
      }
    },
    "a1_safe_view": {
      "level_policy": {
        "mode": "level_ceiling",
        "ceiling": "A1"
      },
      "candidate_type_mix": {
        "pattern_candidate": {
          "min_ratio": 0.25,
          "target_ratio": 0.35
        },
        "vocabulary_candidate": {
          "min_ratio": 0.35,
          "target_ratio": 0.45
        },
        "chunk_candidate": {
          "max_ratio": 0.25
        }
      },
      "deduplication": {
        "normalized_label_unique_in_top_20": true,
        "collapse_equivalent_chunks": true
      },
      "opaque_chunk_policy": {
        "max_ratio": 0.15,
        "penalty_flags": [
          "contains_sb_sth",
          "contains_slash_alternative",
          "advanced_modal_or_perfect"
        ]
      }
    }
  },
  "future_outputs": {
    "view_rank": true,
    "view_score": true,
    "raw_rank_preserved": true,
    "raw_static_score_preserved": true
  }
}
```

## 20. S10F Implementation Boundaries

S10F may create:

- `ulga/builders/build_static_candidate_ranking_views.py`
- `ulga/validators/validate_static_candidate_ranking_views.py`
- `ulga/graph/static_candidate_ranking_views.json`
- `ulga/reports/static_candidate_ranking_views_summary.json`
- `tests/ulga/test_static_candidate_ranking_views.py`

S10F should implement ranking views, not alter raw ranking.

S10F must remain:

- static/offline
- non-adaptive
- traceable back to S10C raw ranking

## 21. Acceptance Criteria for S10F

- raw S10C ranking remains untouched
- ranking views preserve `raw_rank` and `raw_static_score`
- balanced views enforce candidate-type floors and caps when candidates are available
- A1-safe view excludes or limits opaque advanced chunks
- theme-scoped views include pattern and vocabulary coverage when available
- deduplicated views remove normalized-label duplicates from top-20
- consumer-targeted views emit suitability flags and policy metadata
- adaptive leakage remains false
- validators can prove that view construction is deterministic

## 22. Risks and Open Questions

- fixed ratio targets may be too rigid for sparse themes or advanced bands
- some chunk families may need semantic grouping beyond label normalization
- theme metadata quality may be uneven across authority sources
- pattern availability may be genuinely sparse in some filtered windows
- inferred-signal handling needs explicit thresholds in S10F
- bridge consumers may need different opacity tolerances than mixed curriculum views

## 23. Final Recommendation

S10C raw ranking remains valid as a baseline.

S10D QA findings show raw ranking is not curriculum-balanced.

S10E defines the contract for transforming raw ranking into safe downstream ranking views.

S10F should implement ranking views based on this contract.

Adaptive planner remains blocked.

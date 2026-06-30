# ULGA-S7C Pattern Vocabulary Linkage Design Scan

## 1. Executive Summary

This design scan defines how the **Sentence Pattern Authority** should connect to the **Vocabulary Authority** without mutating existing mounted datasets and without prematurely expanding the graph into an impractical number of pattern-to-vocabulary edges.

Current state:

- Sentence patterns exist and pass validation: `1,482` nodes, `1,529` edges.
- Accepted generator-ready patterns: `1,344`
- Extracted slots: `2,016`
- Vocabulary nodes exist and pass validation: `15,696` nodes
- Vocabulary slot constraints coverage on sentence patterns: `0%`

Key design decision:

```text
S7C should establish a slot-constraint authority contract and a runtime/linkage index design.
S7C should not materialize a full pattern x vocabulary candidate edge graph.
```

Reason:

- `1,482 x 15,696 = 23,261,472` possible pattern-vocabulary pairings at pattern level.
- `2,016 x 15,696 = 31,643,136` possible slot-vocabulary pairings at slot level.
- Most of those pairs are invalid by POS, CEFR, theme, morphology, or semantics.
- Full materialization would increase build cost, validator cost, storage size, and downstream query complexity for little authority value.

Final verdict: `PASS`

S7C is ready as a design-contract stage. Recommended next implementation step is a constrained linkage layer under `S7D` that builds slot constraint metadata and a queryable candidate index, not a dense edge explosion.

## 2. Existing Assets Found

Files inspected:

- `ulga/graph/sentence_patterns.json`
- `ulga/graph/ulga_sentence_pattern_nodes.json`
- `ulga/graph/ulga_sentence_pattern_edges.json`
- `ulga/graph/vocabulary_nodes.json`
- `ulga/graph/vocabulary_theme_edges.refined.json`
- `vocabulary/json/vocabulary.json`
- `themes/theme_vocab_mapping.json`
- `themes/theme_catalog.json`
- `chunk_profile/json/chunks.json`
- `chunk_profile/json/chunks_generator_safe.json`
- `ulga/schema/ulga_node_schema.json`
- `ulga/schema/ulga_edge_schema.json`
- `docs/ulga/ULGA_S5B_VOCABULARY_NODE_MOUNTING_CLOSEOUT.md`
- `docs/ulga/ULGA_S5C_VOCABULARY_AUTHORITY_QA_AUDIT.md`
- `docs/ulga/ULGA_S5D_VOCABULARY_THEME_LAYER_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S7A_SENTENCE_PATTERN_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S7BI_SENTENCE_PATTERN_QA_AUDIT.md`
- `docs/ulga/ULGA_S7BII_SENTENCE_PATTERN_COMPILER_FIX_CLOSEOUT.md`

Confirmed mounted assets:

- Sentence patterns: `1,482`
- Sentence pattern accepted count: `1,344`
- Sentence pattern needs_review count: `138`
- Vocabulary nodes: `15,696`
- Vocabulary-theme edges: `19,557`
- Vocabulary nodes with at least one theme edge: `9,065`
- Chunk generator-safe records: `3,522`

Authority field reality check:

- `sentence_patterns.json` currently stores `vocabulary_slot_constraints: {}`
- `vocabulary_nodes.json` stores `part_of_speech`, `frequency_rank`, `frequency_score`, `theme_tags`
- Theme membership truth currently lives in `vocabulary_theme_edges.refined.json`, not in `theme_tags`
- Raw `vocabulary.json` stores `topic` and `frequency_band`, which are useful linkage signals but are not the sole runtime source of truth

Design implication:

```text
S7C must target mounted ULGA vocabulary nodes as the authority target.
Raw source fields may be used as enrichment inputs, but not as replacement authority.
```

## 3. Pattern Slot Inventory

Current sentence pattern inventory summary:

- Total patterns: `1,482`
- Manual A1 core patterns: `17`
- Chunk-derived patterns: `1,465`
- Total extracted slots: `2,016`
- Required slots: `100%`
- Multi-type slots: `3`

Slot type distribution:

| Slot Type | Count |
| --- | ---: |
| `noun_phrase` | 1,634 |
| `verb` | 206 |
| `verb_infinitive` | 103 |
| `verb_gerund` | 60 |
| `verb_stem` | 5 |
| `multi_type` | 3 |
| `proper_noun` | 1 |
| `noun_phrase_1` | 1 |
| `noun_phrase_2` | 1 |
| `time` | 1 |
| `adjective` | 1 |

Top slot labels:

| Slot Label | Count |
| --- | ---: |
| `sth` | 1,137 |
| `sb` | 491 |
| `verb` | 206 |
| `infinitive` | 103 |
| `gerund` | 60 |
| `noun_phrase` | 6 |
| `verb_stem` | 5 |
| `noun_phrase/gerund` | 2 |
| `adjective/noun_phrase` | 1 |

Key observations:

1. Slot semantics are still coarse.
2. `sb` and `sth` dominate the chunk-derived inventory.
3. Only `3` slots currently express explicit multi-type semantics.
4. Slot names do not yet encode enough information for direct high-precision lexical matching.

Design implication:

```text
S7C should standardize slot-constraint metadata around normalized compatibility classes,
not rely only on raw placeholder strings.
```

Recommended normalized compatibility classes:

- `person_noun_phrase`
- `thing_noun_phrase`
- `general_noun_phrase`
- `base_verb`
- `gerund_verb`
- `infinitive_verb`
- `adjective`
- `proper_name`
- `time_expression`
- `location_noun_phrase`
- `multi_type`

## 4. Vocabulary Inventory

Mounted vocabulary authority summary:

- Total vocabulary nodes: `15,696`
- CEFR fully populated: yes
- Frequency rank fully populated: yes
- Frequency score fully populated: yes
- Theme membership available through refined theme edges: partial but usable
- Sense preservation: yes

CEFR distribution:

| CEFR | Count |
| --- | ---: |
| `A1` | 784 |
| `A2` | 1,594 |
| `B1` | 2,937 |
| `B2` | 4,164 |
| `C1` | 2,410 |
| `C2` | 3,807 |

Source POS distribution from `vocabulary.json`:

| POS | Count |
| --- | ---: |
| `noun` | 5,171 |
| `phrase` | 3,656 |
| `adjective` | 2,422 |
| `verb` | 2,318 |
| `adverb` | 805 |
| `phrasal verb` | 728 |
| `preposition` | 244 |
| `determiner` | 124 |
| `pronoun` | 101 |
| `conjunction` | 50 |
| `modal verb` | 37 |

Frequency band distribution from `vocabulary.json`:

| Band | Count |
| --- | ---: |
| `tier_1` | 1,000 |
| `tier_2` | 2,000 |
| `tier_3` | 4,000 |
| `tier_4` | 4,500 |
| `tier_5` | 4,196 |

Theme readiness:

- Source-topic-backed vocabulary nodes: `9,065`
- Theme edges emitted: `19,557`
- Top A1 theme hubs already exist, including:
- `theme:a1_homes_and_neighborhoods`
- `theme:a1_shopping_and_basic_transactions`
- `theme:a1_interests_and_abilities`
- `theme:a1_food_and_dining`
- `theme:a1_health_and_medical`

Real data model caveats:

1. `vocabulary_nodes.json` uses `part_of_speech`, not `pos`.
2. Theme membership should be read from theme edges first, not from `theme_tags`.
3. Frequency band is available in raw source, while mounted nodes expose `frequency_rank` and `frequency_score`.
4. Sense-level polysemy is common and must be preserved.

Examples:

- `read` exists as A1 verb, A2 verb, and C2 noun.
- `happy` exists as A1 adjective and A2 adjective.
- `swim` exists as A1 verb and A2 noun.

Design implication:

```text
Linkage must target vocabulary node IDs, never bare lemmas.
```

## 5. Compatibility Matrices

### 5.1 Slot Type -> Vocabulary POS Matrix

Recommended compatibility matrix:

| Slot Class | Primary Allowed POS | Secondary Allowed POS | Notes |
| --- | --- | --- | --- |
| `general_noun_phrase` | `noun` | `phrase`, `pronoun` | Default for `sth`, `noun_phrase` |
| `person_noun_phrase` | `noun` | `pronoun`, `phrase` | Prefer person-related theme/topic evidence |
| `thing_noun_phrase` | `noun` | `phrase` | Exclude person-heavy senses where possible |
| `base_verb` | `verb` | `phrasal verb` | Must support bare infinitive / stem realization |
| `gerund_verb` | `verb` | `phrasal verb` | Must support `-ing` morphology or inflected lookup |
| `infinitive_verb` | `verb` | `phrasal verb` | Usually `to + base`; phrasal verbs allowed |
| `adjective` | `adjective` | none | Strict |
| `proper_name` | `noun` | none | Requires extra name-list policy or proper-name flag |
| `time_expression` | `noun`, `phrase`, `adverb` | none | Needs dedicated runtime whitelist |
| `location_noun_phrase` | `noun`, `phrase` | none | Must pass location theme/topic signal |
| `multi_type` | union of child classes | none | Determined by `allowed_slot_types` |

### 5.2 CEFR Compatibility Matrix

Recommended CEFR rule:

| Pattern Level | Allowed Vocabulary Levels | Gate Type |
| --- | --- | --- |
| `A1` | `A1` default, `A2` optional bridge | hard gate + optional bridge policy |
| `A2` | `A1-A2` default, `B1` optional bridge | hard gate + optional bridge policy |
| `B1` | `A1-B1` default, `B2` optional bridge | hard gate + optional bridge policy |
| `B2` | `A1-B2` default, `C1` optional bridge | hard gate + optional bridge policy |
| `C1` | `A1-C1` default, `C2` optional bridge | hard gate + optional bridge policy |
| `C2` | `A1-C2` | hard gate |

Design decision:

```text
CEFR should act as a hard ceiling by default.
Cross-level allowance should be explicit bridge policy, not silent leakage.
```

### 5.3 Theme Compatibility Matrix

Recommended theme policy:

| Signal | Role | Notes |
| --- | --- | --- |
| Pattern `theme_refs` | hard or soft filter | Manual A1 patterns can use this immediately |
| Vocabulary theme edges | primary thematic evidence | Mounted authority signal |
| Raw source topic | fallback evidence only | Use when theme edge absent |
| Theme mapping blocked topics | hard blocker | Must be applied before ranking |

Theme modes:

- `hard_filter`: vocabulary must match at least one allowed theme
- `soft_filter`: non-matching vocabulary allowed but penalized
- `weighted_filter`: match boosts ranking without blocking

Recommended default by source:

- Manual A1 patterns: `hard_filter`
- Accepted chunk-derived patterns: `soft_filter`
- Needs-review patterns: no theme linkage emitted

### 5.4 Frequency Compatibility Matrix

Recommended frequency policy:

| Pattern Level | Preferred Bands | Hard Gate? |
| --- | --- | --- |
| `A1` | `tier_1`, `tier_2` | no, unless exam-restricted mode |
| `A2` | `tier_1` to `tier_3` | no |
| `B1` | `tier_1` to `tier_4` | no |
| `B2+` | any | no |

Design decision:

```text
Frequency should be a ranking signal by default, not a hard blocker.
Only special exam-restricted or beginner-safe modes should gate by frequency band.
```

## 6. Proposed Linkage Contract

S7C should define `vocabulary_slot_constraints` as the pattern-owned authority contract.

Recommended metadata shape:

```json
{
  "SLOT_01": {
    "slot_label": "noun_phrase/gerund",
    "compatibility_class": "multi_type",
    "allowed_slot_types": ["noun_phrase", "verb_gerund"],
    "allowed_pos": ["noun", "verb", "phrasal verb"],
    "allowed_cefr_min": "A1",
    "allowed_cefr_max": "A1",
    "theme_mode": "hard_filter",
    "allowed_theme_ids": [
      "theme:a1_food_and_dining",
      "theme:a1_interests_and_abilities"
    ],
    "blocked_theme_ids": [],
    "preferred_frequency_bands": ["tier_1", "tier_2"],
    "requires_morphology": true,
    "requires_chunk_support": false,
    "person_only": false,
    "thing_only": false,
    "location_only": false,
    "source": "rule_based_linkage_design"
  }
}
```

Contract rules:

1. Constraint ownership belongs to the pattern slot, not the vocabulary node.
2. Vocabulary nodes remain unchanged.
3. Constraint fields must be explicit enough for gate checks.
4. Theme and frequency policy must distinguish hard constraints from ranking preferences.
5. Morphology-sensitive slots must declare that dependency explicitly.

Recommended minimal S7D implementation subset:

- `compatibility_class`
- `allowed_pos`
- `allowed_cefr_max`
- `theme_mode`
- `allowed_theme_ids`
- `preferred_frequency_bands`
- `requires_morphology`

## 7. Candidate Ranking Model

Candidate ranking should happen after hard filters.

### 7.1 Gate-Then-Rank Pipeline

1. Skip `needs_review` patterns.
2. Read slot constraints.
3. Filter vocabulary candidates by POS compatibility.
4. Apply CEFR hard ceiling.
5. Apply blocked theme rules.
6. Apply required morphology availability.
7. Rank surviving candidates.

### 7.2 Ranking Score

Recommended formula:

```text
ranking_score =
  0.30 * cefr_fit +
  0.25 * theme_fit +
  0.20 * frequency_fit +
  0.15 * learner_mastery_fit +
  0.10 * recency_fit
```

Signal definitions:

- `cefr_fit`: best when candidate CEFR is at or just below pattern ceiling
- `theme_fit`: best when candidate has direct matching theme edge
- `frequency_fit`: best for higher-frequency items at lower levels
- `learner_mastery_fit`: prefer not-yet-mastered but not impossible items
- `recency_fit`: discourage immediate repetition unless spaced review is intended

Design boundary:

```text
S7C defines the ranking model contract only.
It does not implement learner-state ranking or planner runtime.
```

## 8. Edge Contract

A full dense `PATTERN_CAN_FILL_WITH` edge layer is not recommended for S7D first pass.

### Option A: Full Materialized Pattern-Vocabulary Edges

Pros:

- Simple query shape
- Explicit graph trace

Cons:

- Upper bound exceeds `20M+` edges even before slot expansion
- Expensive rebuilds
- Expensive validator checks
- Repeated information better expressed as constraints

Verdict: reject for first implementation

### Option B: Constraint-Owned Patterns + Runtime Candidate Query

Pros:

- Small authority footprint
- Easier rebuild
- Better alignment with gates/ranking
- No dense edge explosion

Cons:

- Requires query-time filtering logic
- Less explicit than a precomputed edge graph

Verdict: recommended default

### Option C: Hybrid Sparse Edge Layer

Materialize only high-confidence, pattern-critical, low-cardinality links:

- fixed lexical anchors
- irregular morphology exceptions
- curated proper-name pools
- mandatory chunk-only fillers

Recommended logical edge:

```text
PATTERN_CAN_FILL_WITH
```

Recommended physical edge:

```text
edge_type = "uses"
```

Rationale:

- `ulga_edge_schema.json` already allows `uses`
- avoids schema changes in S7D
- metadata can carry `logical_edge_type: "PATTERN_CAN_FILL_WITH"`

Recommended sparse edge metadata:

```json
{
  "logical_edge_type": "PATTERN_CAN_FILL_WITH",
  "slot_id": "SLOT_01",
  "constraint_reason": "curated_exception",
  "hard_gate": false,
  "ranking_boost": 0.9
}
```

## 9. Runtime Query Design

Recommended query interface:

```json
{
  "pattern_id": "pattern:PATTERN_NODE_000004",
  "slot_id": "SLOT_01",
  "target_level": "A1",
  "target_theme_ids": ["theme:a1_food_and_dining"],
  "generator_mode": "beginner_safe",
  "limit": 20
}
```

Recommended runtime steps:

1. Load pattern node.
2. Read `vocabulary_slot_constraints[SLOT_n]`.
3. Pull candidate vocabulary IDs from the mounted vocabulary pool.
4. Join theme edges for thematic evidence.
5. Join morphology layer when slot requires inflection.
6. Apply gate checks.
7. Rank survivors.
8. Return candidate IDs with explanation trace.

Recommended response:

```json
{
  "pattern_id": "pattern:PATTERN_NODE_000004",
  "slot_id": "SLOT_01",
  "candidate_count": 20,
  "candidates": [
    {
      "vocabulary_id": "vocabulary:apple:v_418",
      "score": 0.94,
      "reasons": ["A1_cefr_match", "theme_match", "high_frequency"]
    }
  ],
  "blocked_count": 143,
  "blocked_reasons_summary": {
    "cefr_above_ceiling": 42,
    "theme_mismatch": 71,
    "pos_mismatch": 30
  }
}
```

## 10. Antigravity Integration

S7C should remain planner-compatible but not planner-dependent.

Recommended integration boundary:

1. Antigravity Planner chooses a pattern node.
2. Vocabulary Gate calls the slot-candidate query.
3. Gate trace explains blocked candidate families.
4. Recommendation stage ranks already-approved candidates.

Implication for future stages:

- S7D should implement the slot-constraint layer
- S7E/S8 can consume it for gate/runtime candidate filtering
- S9 can rank candidates using learner-state signals

Do not do in S7C:

- no learner-state persistence
- no recommendation engine
- no direct generator prompt integration
- no mass vocabulary edge generation

## 11. Risks

### Risk 1: Data Model Mismatch

The mounted vocabulary graph and the linkage inputs do not expose all needed signals in one place.

- mounted node fields: `part_of_speech`, `frequency_rank`, `frequency_score`
- mounted theme truth: `vocabulary_theme_edges.refined.json`
- raw source enrichment: `topic`, `frequency_band`
- pattern contract target: `vocabulary_slot_constraints`

Mitigation:

- define explicit field mapping in S7D
- never assume `theme_tags` contains authoritative membership

### Risk 2: Polysemy Contamination

Lemma-level linkage would join wrong senses.

Examples:

- `read` verb vs noun
- `swim` verb vs noun

Mitigation:

- link by vocabulary node ID only
- treat lemma indexes as lookup helpers only

### Risk 3: Slot Semantics Too Coarse

`sb`, `sth`, `verb`, `noun_phrase` are too broad for high-quality generation.

Mitigation:

- introduce normalized compatibility classes
- allow person/thing/location flags
- use theme and morphology as secondary filters

### Risk 4: Theme Overreach

Chunk-derived patterns currently have `0` explicit `theme_refs`.

Mitigation:

- manual A1 patterns may use hard pattern theme filters
- chunk-derived patterns should start with soft theme weighting
- promote to hard theme gate only after audited inheritance

### Risk 5: Dense Edge Explosion

Full candidate materialization would create `20M+` possible edges.

Mitigation:

- default to pattern-owned constraints
- allow only sparse curated exception edges

### Risk 6: Morphology Gaps

Gerund, infinitive, and verb-stem slots need reliable surface-form generation.

Mitigation:

- make morphology dependency explicit in slot constraints
- do not over-approve slots that require unavailable morphology support

## 12. Recommended S7D Scope

Recommended next task:

`ULGA-S7D_PatternVocabularyLinkage_Implementation`

Minimal implementation scope:

1. Add a slot-constraint builder that populates `vocabulary_slot_constraints` for accepted patterns only.
2. Normalize raw slot labels into compatibility classes.
3. Build a read-only candidate index or query helper, not a dense edge graph.
4. Reuse mounted vocabulary nodes plus refined theme edges.
5. Add validator rules for slot-constraint structure.
6. Add pytest coverage for:
- slot-to-pos compatibility
- CEFR ceiling enforcement
- theme-mode contract
- morphology-required flags
- no constraints on `needs_review` patterns unless explicitly allowed

Explicit non-goals for S7D:

- no full pattern-vocabulary dataset
- no planner runtime
- no recommendation runtime
- no mutation of vocabulary authority
- no mutation of theme authority

## 13. Final Verdict

`PASS`

Summary:

- Pattern and vocabulary authorities are structurally ready for linkage design.
- The main gap is not missing source data; it is missing slot-constraint contract and query design.
- The safest minimal-change path is pattern-owned constraints plus sparse optional exception edges.
- S7D should implement constrained linkage metadata and candidate-query infrastructure, not a dense graph expansion.

# ULGA-S7E Pattern Theme Linkage Design Scan

## 1. Executive Summary

This design scan evaluates how **Sentence Pattern Authority** should connect to **Theme Authority** without mutating any mounted datasets.

Current state:

- Sentence patterns: `1,482`
- Accepted patterns: `1,344`
- Needs review patterns: `138`
- Vocabulary nodes: `15,696`
- Themes: `25`
- Refined vocabulary-theme edges: `19,557`
- Vocabulary nodes with at least one theme edge: `9,065`
- Sentence patterns with explicit `theme_refs`: `17`

Key conclusion:

```text
Theme should not be modeled as a single hard classification directly attached to most patterns today.
The safer authority design is:

Pattern
-> primary_theme (optional, high-confidence only)
-> secondary_themes (optional)
-> slot theme policy
-> query-time vocabulary theme filtering / ranking
```

Why:

1. Explicit pattern theme coverage is extremely low.
2. Chunk-derived patterns do carry chunk references, but most chunk theme hints are only `General`.
3. Topic-to-theme mapping is highly many-to-many, so topic alone cannot support hard single-theme classification.
4. Vocabulary-theme edges are already the strongest mounted theme authority available in the graph.

Final verdict: `PASS`

S7E is ready as a design-contract stage. The recommended next implementation step is a **Pattern Theme Linkage Authority layer** that supports optional pattern-level theme authority, weighted inference, and query-time theme-aware vocabulary filtering without dense new edge generation.

## 2. Files Inspected

- `themes/theme_catalog.json`
- `themes/theme_vocab_mapping.json`
- `ulga/graph/sentence_patterns.json`
- `ulga/graph/ulga_sentence_pattern_nodes.json`
- `ulga/graph/pattern_vocabulary_constraints.json`
- `ulga/graph/vocabulary_theme_edges.refined.json`
- `vocabulary/json/vocabulary.json`
- `chunk_profile/json/chunks.json`
- `chunk_profile/json/chunks_generator_safe.json`
- `ulga/graph/chunk_nodes.json`
- `grammar_profile/json/grammar_profile.json`
- `ulga/graph/grammar_nodes.json`
- `ulga/schema/ulga_node_schema.json`
- `ulga/schema/ulga_edge_schema.json`
- `docs/ulga/ULGA_S7C_PATTERN_VOCABULARY_LINKAGE_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S7D_PATTERN_VOCABULARY_CONSTRAINT_IMPLEMENTATION_CLOSEOUT.md`

## 3. Existing Assets Found

Sentence Pattern Authority:

- `sentence_patterns.json` stores `theme_refs`, `chunk_refs`, `grammar_refs`, `slots`, and `vocabulary_slot_constraints`
- `ulga_sentence_pattern_nodes.json` confirms `1,482` mounted nodes and `1,529` mounted edges
- `pattern_vocabulary_constraints.json` confirms accepted-only active constraints: `1,344`

Theme Authority:

- `theme_catalog.json` stores 25 themes with `theme_id`, `theme_name`, `level`, `parent_theme`, and `active_vocabulary_count`
- `theme_vocab_mapping.json` stores topic-based mapping policy, CEFR policy, frequency hints, and `prev_theme_id` / `next_theme_id`

Vocabulary Authority:

- `vocabulary.json` contains `15,696` vocabulary records
- `vocabulary_theme_edges.refined.json` contains `19,557` refined theme edges over `9,065` vocabulary nodes

Chunk Authority:

- `chunks.json` contains `4,546` chunk records
- `chunks_generator_safe.json` contains `3,522` safe chunk records
- mounted `chunk_nodes.json` is joinable from pattern `chunk_refs`

Grammar Authority:

- `grammar_profile.json` contains `1,222` raw grammar records
- mounted `grammar_nodes.json` is joinable from pattern `grammar_refs`

## 4. Theme Inventory

### 4.1 Total Themes

- Total themes: `25`

### 4.2 Theme Level Distribution

| Level | Count |
| --- | ---: |
| `A1` | 9 |
| `A1_plus` | 1 |
| `A2` | 3 |
| `A2_plus` | 1 |
| `B1` | 3 |
| `B1_plus` | 1 |
| `B2` | 3 |
| `B2_plus` | 1 |
| `C1` | 3 |

### 4.3 Theme Hierarchy by Parent Theme

| Parent Theme | Count |
| --- | ---: |
| `Social Interaction` | 4 |
| `Personal Life` | 4 |
| `Daily Life` | 3 |
| `Transactions` | 3 |
| `Travel` | 2 |
| `Work` | 2 |
| `Education` | 1 |
| `Daily Life (Bridge)` | 1 |
| `Social Interaction (Bridge)` | 1 |
| `Critical Thinking (Bridge)` | 1 |
| `Academic Life` | 1 |
| `Academic Life (Bridge)` | 1 |
| `Critical Thinking` | 1 |

### 4.4 Theme Progression Chains

Theme dependency already exists in `theme_vocab_mapping.json` as `prev_theme_id` / `next_theme_id`, even though it is not yet mounted as graph edges.

Observed chains:

1. `a1_personal_information_and_greetings -> a2_socializing_and_discussion -> b1_personal_expression_and_socializing -> b2_native_speed_communication -> c1_precise_expression`
2. `a1_daily_life_and_routines -> a2_daily_transactions_and_local_environment -> b1_work_and_business_environment -> b2_professional_and_academic_situations -> c1_advanced_work_and_socializing`
3. `a1_homes_and_neighborhoods -> a2_daily_transactions_and_local_environment -> b1_work_and_business_environment -> b2_professional_and_academic_situations -> c1_advanced_work_and_socializing`
4. `a1_shopping_and_basic_transactions -> a2_travel_and_consumption -> b1_travel_and_living_abroad -> b2_in_depth_debates_and_meetings -> c1_precise_expression`
5. `a1_food_and_dining -> a2_travel_and_consumption -> b1_travel_and_living_abroad -> b2_in_depth_debates_and_meetings -> c1_precise_expression`
6. `a1_interests_and_abilities -> b1_personal_expression_and_socializing -> b2_native_speed_communication -> c1_precise_expression`
7. `a1_travel_and_weather -> a2_travel_and_consumption -> b1_travel_and_living_abroad -> b2_in_depth_debates_and_meetings -> c1_precise_expression`
8. `a1_health_and_medical -> b1_personal_expression_and_socializing -> b2_native_speed_communication -> c1_precise_expression`
9. `a1_school_and_classroom -> b2_professional_and_academic_situations -> c1_advanced_work_and_socializing`

Coverage:

- Themes with `prev_theme_id`: `16`
- Themes with `next_theme_id`: `22`

### 4.5 Vocabulary Count per Theme

From `theme_catalog.json`:

- Average active vocabulary per theme: `1459.88`

From `theme_vocab_mapping.json`:

- Average mapped vocabulary per theme: `1509.64`

Top 5 by active vocabulary count:

| Theme ID | Active Vocabulary Count |
| --- | ---: |
| `b2_native_speed_communication` | 4,086 |
| `c1_implicit_meanings_and_complex_texts` | 3,745 |
| `c1_precise_expression` | 3,736 |
| `b1_plus_critical_discussion` | 3,157 |
| `b2_plus_academic_bridge` | 2,912 |

## 5. Pattern Theme Coverage

### 5.1 Pattern Coverage

| Metric | Count |
| --- | ---: |
| Total patterns | 1,482 |
| Patterns with `theme_refs` | 17 |
| Patterns without `theme_refs` | 1,465 |
| Accepted patterns with `theme_refs` | 17 |
| Accepted patterns without `theme_refs` | 1,327 |

Coverage ratios:

- Patterns with explicit `theme_refs`: `1.15%`
- Accepted patterns with explicit `theme_refs`: `1.26%`

### 5.2 Theme Density by Pattern Count

Observed pattern-level theme distribution:

| Theme ID | Pattern Count |
| --- | ---: |
| `theme:a1_homes_and_neighborhoods` | 6 |
| `theme:a1_interests_and_abilities` | 4 |
| `theme:a1_personal_information_and_greetings` | 3 |
| `theme:a1_daily_life_and_routines` | 2 |
| `theme:a1_school_and_classroom` | 2 |

There are no pattern-level theme assignments outside this small A1 manual set.

### 5.3 Source Split

| Source | Count | With Theme Refs |
| --- | ---: | ---: |
| `MANUAL_A1_CORE_PATTERN` | 17 | 17 |
| `CHUNK_GRAMMAR_METADATA_DERIVED` | 1,465 | 0 |

This is the central S7E gap.

## 6. Vocabulary Theme Coverage

From refined mounted edges:

| Metric | Count |
| --- | ---: |
| Vocabulary nodes | 15,696 |
| Vocabulary nodes with themes | 9,065 |
| Vocabulary nodes without themes | 6,631 |
| Refined theme-vocabulary edges | 19,557 |

Coverage ratio:

- Vocabulary nodes with at least one refined theme edge: `57.75%`

Top 5 themes by refined edge count:

| Theme Node ID | Edge Count |
| --- | ---: |
| `theme:a1_homes_and_neighborhoods` | 2,109 |
| `theme:a1_shopping_and_basic_transactions` | 2,079 |
| `theme:a1_interests_and_abilities` | 1,942 |
| `theme:a1_food_and_dining` | 1,854 |
| `theme:a1_health_and_medical` | 1,769 |

Design implication:

```text
Vocabulary-theme linkage is already much stronger than pattern-theme linkage.
Theme authority is therefore more reliable on the vocabulary side than on the pattern side.
```

## 7. Theme Candidate Inference Analysis

This section evaluates whether pattern theme can be inferred from available signals.

### 7.1 Signal 1: Pattern Text

Naive lexical cue scan over canonical pattern text found obvious theme words in only `61 / 1482` patterns (`4.12%`).

Interpretation:

- Pattern text alone is weak for general coverage.
- It can support a small precision-first rule set.
- It is not sufficient as the primary authority source.

### 7.2 Signal 2: Slot Type

Current active slot distribution is dominated by coarse generic classes:

- `noun_phrase`: `1,552`
- `verb`: `206`
- `verb_infinitive`: `101`
- `verb_gerund`: `60`

Dominant slot labels:

- `sth`: `1,077`
- `sb`: `469`

Interpretation:

- Slot type is useful for candidate vocabulary filtering.
- Slot type is not discriminative enough to infer pattern theme.
- It should remain a structural gate, not a theme classifier.

### 7.3 Signal 3: Chunk Refs

Pattern chunk coverage:

| Metric | Count |
| --- | ---: |
| Patterns with chunk refs | 1,465 |
| Patterns with any chunk theme hint | 1,465 |
| Patterns with specific non-`General` chunk theme hint | 165 |
| Patterns with chunk topic | 547 |
| Patterns with `General`-only chunk hint | 1,300 |

Top chunk topics at pattern level:

| Topic | Pattern Count |
| --- | ---: |
| `people: actions` | 246 |
| `communication` | 109 |
| `people: personality` | 74 |
| `relationships` | 27 |
| `travel` | 15 |
| `body and health` | 14 |
| `describing things` | 13 |
| `work` | 10 |
| `money` | 9 |

Top chunk theme hints:

| Theme Hint | Pattern Count |
| --- | ---: |
| `General` | 1,300 |
| `Personal` | 105 |
| `Travel` | 22 |
| `Shopping` | 14 |
| `Health` | 14 |
| `Hobbies` | 9 |
| `Home` | 4 |
| `School` | 2 |
| `Food` | 2 |

Interpretation:

- Chunk refs are the strongest available inference signal for the chunk-derived population.
- But most hints are still too generic for hard authority.
- Chunk topic and chunk theme hint are good **weighted evidence**, not hard classification, unless they converge with other signals.

### 7.4 Signal 4: Grammar Refs

Grammar reference coverage:

| Metric | Count |
| --- | ---: |
| Total grammar refs on patterns | 43 |
| Joinable mounted grammar refs | 43 |

Top grammar families:

| Grammar Family | Ref Count |
| --- | ---: |
| `VERBS` | 19 |
| `FUTURE` | 10 |
| `MODALITY` | 8 |
| `NEGATION` | 2 |
| `DETERMINERS` | 2 |

Interpretation:

- Grammar refs are structurally clean.
- They are weak theme evidence because they mostly describe form, not topic.
- They should not be used as direct pattern-theme authority.

### 7.5 Signal 5: Vocabulary Constraints

From active pattern vocabulary constraints:

| Metric | Count |
| --- | ---: |
| Active slot constraints | 1,932 |
| `hard_filter` theme gates | 19 |
| `soft_filter` theme gates | 1,913 |
| Slot constraints with non-empty `allowed_theme_ids` | 19 |

Interpretation:

- Vocabulary constraints currently preserve only the 17 manual pattern theme refs.
- They are useful as downstream consumers of pattern theme authority.
- They are not currently an inference source for most patterns.

### 7.6 Inference Feasibility Conclusion

Inference feasibility by signal:

| Signal | Coverage | Precision Potential | Recommended Role |
| --- | --- | --- | --- |
| Pattern text | low | medium | supporting evidence |
| Slot type | high | low | structural filter only |
| Chunk refs | high | medium | primary inference evidence for chunk-derived patterns |
| Grammar refs | very low | low | no direct theme authority |
| Vocabulary constraints | very low | high where present | downstream consumer, not primary inference source |

Final inference conclusion:

```text
Pattern theme can be inferred, but not with a single hard source.
The best design is weighted multi-signal inference with confidence scores.
```

## 8. Topic-to-Theme Ambiguity

Using `theme_vocab_mapping.json`, topic-to-theme mapping is strongly many-to-many:

- Unique topics in mapping: `19`
- Topics that map to more than one theme: `16`

Examples:

- `communication` maps to `19` themes
- `describing things` maps to `20` themes
- `people: actions` maps to `9` themes
- `relationships` maps to `10` themes
- `work` maps to `9` themes

Pattern-level chunk-topic to candidate-theme distribution:

| Candidate Theme Count | Pattern Count |
| --- | ---: |
| `19` | 109 |
| `20` | 13 |
| `10` | 27 |
| `9` | 256 |
| `6` | 74 |
| `5` | 25 |
| `4` | 10 |
| `3` | 10 |
| `1` | 22 |
| `0` | 1 |

Interpretation:

- Topic alone is too ambiguous for hard single-theme assignment.
- Multi-theme support is structurally necessary.

## 9. Answers to the Core Questions

### 9.1 Should Theme Hang Directly on Pattern, or Pattern -> Slot -> Theme?

Recommended answer:

```text
Both, but with different semantics.

Pattern
-> pattern_theme_linkage (primary / secondary / confidence)
Slot
-> slot_theme_policy (gate mode, optional allowed/blocked themes)
```

Reasoning:

1. Pattern theme answers "what scenario is this pattern usually used in?"
2. Slot theme policy answers "how should vocabulary be filtered or ranked for this slot?"
3. These are related but not identical.
4. Manual A1 patterns already prove pattern-level theme is useful.
5. Slot-level theme policy is still required because vocabulary selection happens at slot level.

Recommended design boundary:

- Pattern owns thematic authority.
- Slot owns thematic filtering policy.

### 9.2 Should Theme Be Hard Classification or Weighted Classification?

Recommended answer:

```text
Weighted classification by default.
Hard classification only for high-confidence manually assigned or audited cases.
```

Reasoning:

1. Pattern-level explicit theme coverage is only `17 / 1482`.
2. Chunk-derived hints are mostly `General`.
3. Topic-to-theme mapping is highly ambiguous.

Recommended policy:

- `manual_asserted`: hard-capable
- `audited_inferred`: hard-capable if confidence is high enough
- `weak_inferred`: weighted only

### 9.3 Should Pattern Allow Multiple Themes?

Recommended answer: `Yes`.

Reasoning:

Examples such as `I like ___.` can naturally serve:

- `Food`
- `Animals`
- `Hobbies`

Multi-theme is also supported by the data:

- topic-to-theme mapping is many-to-many
- chunk-derived patterns often sit in broad usage domains
- one pattern can be scenario-general while the filler vocabulary determines the specific theme

Recommended contract:

- `primary_theme`: optional single best theme
- `secondary_themes`: optional array
- `theme_confidence`
- `theme_mode`

### 9.4 Should the Relationship Be Pattern -> Theme -> Vocabulary or Pattern -> Vocabulary -> Theme?

Recommended answer:

```text
Operationally:
Pattern -> Theme policy -> Vocabulary

Authority-wise:
Pattern -> Theme linkage
Vocabulary -> Theme linkage
Runtime joins both
```

Not recommended:

- `Pattern -> Vocabulary -> Theme` as the main thematic design

Reason:

- Theme should shape candidate filtering and ranking before final vocabulary choice.
- But vocabulary-theme edges remain the stronger authority anchor.

Best model:

```text
Pattern theme linkage is intent authority.
Vocabulary theme edges are membership authority.
Runtime candidate query joins them.
```

### 9.5 Should Theme Be Planner Signal or Graph Authority?

Recommended answer:

```text
Both, but with clear precedence:
1. Graph authority when explicitly asserted or high-confidence inferred
2. Planner signal when confidence is weak or absent
```

Reasoning:

- Theme should not remain planner-only, because pattern pedagogy needs persistent thematic metadata.
- But weak inference should not be frozen as hard graph truth.

Recommended split:

- `theme_source = manual_asserted | audited_inferred | planner_runtime`
- only `manual_asserted` and `audited_inferred` become mounted pattern theme authority
- `planner_runtime` stays ephemeral

### 9.6 Should Theme Dependency Be Built?

Recommended answer: `Yes`, but as progression / affinity, not as prerequisite grammar logic.

Reasoning:

1. Theme progression chains already exist in `theme_vocab_mapping.json`.
2. These chains are useful for syllabus planning and spiral sequencing.
3. Theme dependency is weaker than grammar prerequisite dependency.

Recommended semantics:

- `belongs_to` for parent-theme family
- `spiral_to` for progression chain
- avoid using `prerequisite`

Example:

```text
theme:a1_personal_information_and_greetings
spiral_to
theme:a2_socializing_and_discussion
```

## 10. Multi-Theme Analysis

Recommended pattern contract should allow:

- `primary_theme`
- `secondary_themes`

Why:

1. Many patterns are scenario-generic.
2. Topic evidence often resolves to several plausible themes.
3. Vocabulary choice frequently determines the final realized theme.

Recommended runtime interpretation:

- `primary_theme`: strongest ranking signal or hard filter candidate
- `secondary_themes`: softer ranking boosts

Recommended cap:

- maximum `1` primary theme
- maximum `3` secondary themes

## 11. Pattern Theme Linkage Authority Design

### 11.1 Recommended Contract

```json
{
  "pattern_id": "SP_000004",
  "pattern_node_id": "pattern:PATTERN_NODE_000004",
  "primary_theme": "theme:a1_interests_and_abilities",
  "secondary_themes": [
    "theme:a1_food_and_dining",
    "theme:a1_homes_and_neighborhoods"
  ],
  "theme_confidence": 0.91,
  "theme_mode": "weighted",
  "theme_source": "audited_inferred",
  "evidence": {
    "pattern_text_signal": 0.35,
    "chunk_theme_signal": 0.80,
    "chunk_topic_signal": 0.60,
    "grammar_signal": 0.05,
    "slot_signal": 0.10
  }
}
```

### 11.2 Contract Semantics

Field rules:

- `primary_theme`: optional, nullable
- `secondary_themes`: optional array, may be empty
- `theme_confidence`: `0.0 - 1.0`
- `theme_mode`: `hard | weighted | planner_only`
- `theme_source`: `manual_asserted | audited_inferred | planner_runtime`

Recommended governance:

- `manual_asserted` + confidence `1.0`: eligible for hard gating
- `audited_inferred` + confidence `>= 0.85`: eligible for hard gating after audit
- otherwise weighted only

### 11.3 Slot-Level Companion Policy

Pattern theme linkage should pair with slot theme policy, not replace it.

Recommended slot companion shape:

```json
{
  "slot_id": "SLOT_01",
  "theme_gate_mode": "weighted",
  "allowed_theme_ids": [],
  "blocked_theme_ids": [],
  "inherit_primary_theme": true,
  "inherit_secondary_themes": true
}
```

## 12. Recommended Graph Modeling

Recommended mounted objects:

1. Pattern-owned linkage record dataset
2. Optional sparse pattern-to-theme edges for high-confidence cases

Recommended edge semantics under existing schema:

- `edge_type = "belongs_to"` for strong pattern-theme classification
- `edge_type = "supports"` for weaker thematic affinity
- `edge_type = "spiral_to"` for theme progression dependency between theme nodes

Recommended authority boundary:

- do not create dense pattern-theme-vocabulary edges
- do not rewrite vocabulary-theme authority
- do not rewrite theme mapping dataset

## 13. Recommended Runtime Design

Recommended runtime flow:

1. Load pattern theme linkage, if present.
2. Load slot constraints from `pattern_vocabulary_constraints.json`.
3. Load vocabulary candidates by POS / CEFR / morphology.
4. Join vocabulary-theme edges.
5. Apply theme policy:
   - hard filter only when pattern theme is explicit or high-confidence
   - weighted ranking otherwise
6. Return candidates with explanation trace.

Recommended ranking priority:

1. explicit pattern theme match
2. chunk-derived thematic evidence
3. vocabulary theme match
4. frequency fit
5. learner-state fit

## 14. Risks

### Risk 1: Over-hardening Weak Inference

If chunk topic or lexical cue is treated as hard truth too early, many chunk-derived patterns will be misclassified.

Mitigation:

- weighted by default
- hard only for manual or audited high-confidence cases

### Risk 2: Topic Ambiguity

`communication`, `describing things`, and `people: actions` map to too many themes.

Mitigation:

- never hard-classify from topic alone
- require multi-signal agreement

### Risk 3: Vocabulary-Pattern Drift

If pattern theme and vocabulary theme are modeled independently without runtime join policy, ranking drift will occur.

Mitigation:

- treat pattern theme as intent authority
- treat vocabulary theme edges as membership authority
- define explicit join policy

### Risk 4: Manual-A1 Bias

All current pattern-level themes come from 17 manual A1 patterns.

Mitigation:

- do not generalize hard pattern-theme rules from A1-only evidence
- use chunk-derived inference in weighted mode first

### Risk 5: Schema Overreach

Adding too many new edge types or forcing dense edge layers would create unnecessary maintenance cost.

Mitigation:

- prefer pattern-owned linkage records
- reuse existing edge types where sparse edges are needed

## 15. Recommended Next Task

`ULGA-S7F_PatternThemeLinkage_ContractAndAuditPlan`

Recommended scope:

1. Define the pattern theme linkage dataset shape.
2. Define confidence thresholds for `manual_asserted`, `audited_inferred`, and `planner_runtime`.
3. Define slot inheritance rules from pattern theme linkage into candidate query policy.
4. Define validator and audit expectations before any builder is implemented.

Explicit non-goals:

- no JSON mutation
- no builder implementation
- no validator implementation
- no theme mapping rebuild
- no pattern-theme edge generation

## 16. Final Verdict

`PASS`

Summary:

- Theme authority is strong on the vocabulary side and weak on the pattern side.
- Pattern theme should exist, but as optional high-confidence authority plus weighted inference.
- Slot theme policy remains necessary because vocabulary selection is slot-local.
- Multi-theme support is required.
- Theme dependency should exist as progression / spiral structure, not as prerequisite logic.

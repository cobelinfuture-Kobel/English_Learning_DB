# ULGA-S5D Vocabulary Theme Layer Design Scan

## Scope

This is a design scan for the Vocabulary Theme Layer. It does not create theme edges, vocabulary edges, morphology edges, chunk edges, learner state, planner output, recommendation output, or runtime behavior.

The purpose is to define how Vocabulary Authority and Theme Authority should connect inside ULGA without mutating existing authority data.

## Files Inspected

- `ulga/graph/vocabulary_nodes.json`
- `ulga/graph/ulga_graph.vocabulary_nodes.json`
- `vocabulary/json/vocabulary.json`
- `themes/theme_catalog.json`
- `themes/theme_mapping.json`
- `themes/theme_vocab_mapping.json`
- `output/reports/theme_mapping_report.json`
- `chunk_profile/json/chunks.json`
- `chunk_profile/json/chunk_usage_class_mapping.json`
- `docs/ulga/ULGA_S5A_VOCABULARY_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S5C_VOCABULARY_AUTHORITY_QA_AUDIT.md`
- `docs/ulga/ulga_schema_contract.md`
- `docs/ulga/ulga_roadmap.md`

## Current Authority State

### Vocabulary Authority

- Vocabulary nodes: `15,696`
- Unique lemmas: `9,751` in current node/source scan
- Polysemous lemmas: `3,517`
- Mounted vocabulary edges: `0`
- Theme tags populated on mounted nodes: `0`
- Theme tags empty on mounted nodes: `15,696`

The S5B vocabulary node layer is structurally ready, but theme information has not been mounted into nodes. This is expected. Theme assignment should be a separate S5E graph layer, not a mutation of `vocabulary_nodes.json`.

### Source Topic Readiness

From `vocabulary/json/vocabulary.json`:

- Nodes with native/recovered source topic: `9,065`
- Nodes without topic: `6,631`
- Topic diversity: `24`

Top source topics available for theme mapping:

| Topic | Vocabulary count |
| --- | ---: |
| communication | 1,491 |
| describing things | 1,299 |
| people: actions | 1,298 |
| people: personality | 1,265 |
| body and health | 453 |
| natural world | 319 |
| arts and media | 310 |
| food and drink | 302 |
| travel | 291 |
| work | 266 |

Risk: source topic names contain minor variants such as `people-actions`, `people-personality`, and `animal`, which should be normalized during implementation rather than in this design scan.

### Theme Authority

- Total themes in `themes/theme_catalog.json`: `25`
- Theme levels: A1 `9`, A1_plus `1`, A2 `3`, A2_plus `1`, B1 `3`, B1_plus `1`, B2 `3`, B2_plus `1`, C1 `3`
- Parent themes: `13`
- Theme mapping levels: `9`
- Mapped levels: `5`
- Descriptive-only plus levels: `4`

Theme hierarchy depth is currently shallow:

1. Parent theme family, such as `Social Interaction` or `Daily Life`.
2. Concrete theme catalog node, such as `a1_food_and_dining`.
3. Progression links through `prev_theme_id` / `next_theme_id` or progression chains.

This is sufficient for S5E. It is not yet enough for fine-grained subtheme reasoning.

## Theme Ownership Decision

### Option A: Theme owns Vocabulary membership

Theme Authority stores mapping rules from themes to topics, frequency bands, allowed CEFR levels, and blocked topics. S5E uses those rules to generate membership edges.

Benefits:

- Centralized maintenance.
- Easier to audit overlap between themes.
- Better support for plus-level inheritance.
- Better support for future chunk integration.
- Avoids mutating 15,696 vocabulary nodes whenever theme policy changes.

Tradeoff:

- Querying a vocabulary node's themes requires graph traversal or an edge index.

### Option B: Vocabulary owns Theme tags

Each VocabularyNode stores `theme_tags` directly.

Benefits:

- Simple lookup.
- Useful for cached runtime query results.

Risks:

- Harder to maintain when theme taxonomy changes.
- Harder to represent weighted membership.
- More dangerous for polysemous lemmas because lemma-level tags can hide sense-level differences.
- Encourages mutation of `vocabulary_nodes.json`, which is not allowed in this stage.

### Design Decision

S5D recommends Option A as the authority model:

```text
Theme Authority owns the mapping policy.
Vocabulary Theme Layer emits graph edges.
VocabularyNode metadata may cache derived theme tags later, but it must not be the source of truth.
```

## Theme Authority Audit

### Structure Findings

- Theme catalog is present and usable.
- Theme mapping has explicit categories for A1, A2, B1, B2, and C1.
- Plus levels are descriptive-only and need inherited theme policy.
- `theme_vocab_mapping.json` already contains primary, secondary, blocked topics, frequency bands, allowed CEFR levels, exam alignment, and progression links.

### Risks

- Overlap risk: many themes share broad topics like `communication` and `describing things`.
- Ambiguity risk: topics such as `people: actions` can support many unrelated themes.
- Missing coverage risk: `6,631` vocabulary records have no topic and require fallback mapping or remain unthemed.
- Encoding risk: some older docs/reports show damaged Chinese text, but JSON IDs and structural fields remain usable.

## Vocabulary Theme Readiness

### Readiness Metrics

| Metric | Value |
| --- | ---: |
| Vocabulary nodes | 15,696 |
| Nodes with source topic | 9,065 |
| Nodes without source topic | 6,631 |
| Topic diversity | 24 |
| Mounted node theme tags populated | 0 |
| Mounted node theme tags empty | 15,696 |

### Projected Theme Coverage

`output/reports/theme_mapping_report.json` already estimates per-theme active vocabulary coverage. Examples:

| Theme | Active vocabulary count |
| --- | ---: |
| `b2_native_speed_communication` | 4,086 |
| `c1_implicit_meanings_and_complex_texts` | 3,745 |
| `c1_precise_expression` | 3,736 |
| `b1_plus_critical_discussion` | 3,157 |
| `b2_plus_academic_bridge` | 2,912 |
| `a1_food_and_dining` | 232 |
| `a1_homes_and_neighborhoods` | 234 |
| `a1_health_and_medical` | 247 |
| `a1_interests_and_abilities` | 263 |
| `a1_travel_and_weather` | 270 |

Interpretation: theme mapping has enough data for implementation, but coverage is uneven by design. Early A1 themes are narrow; upper-level bridge themes are broad.

## Polysemy Risk Analysis

Polysemy is the central safety issue for the Vocabulary Theme Layer.

Observed:

- Unique lemmas: `9,751`
- Polysemous lemmas: `3,517`

Examples from S5C include highly polysemous lemmas such as `on`, `take`, `in`, `for`, `right`, `over`, `cover`, `good`, `point`, `close`, `change`, `break`, `go`, and `leave`.

Design rule:

```text
Theme membership must attach to vocabulary sense nodes, not bare lemma strings.
```

Reason:

- `bank` as a finance noun belongs to money / transactions.
- `bank` as a river-side noun belongs to natural world / travel context.
- A lemma-level mapping would collapse distinct EVP senses and contaminate theme selection.

S5E should therefore use `source_vocabulary_id` / vocabulary node ID as the mapping target. Lemma-level indexes may be used only as lookup aids, never as the authority target.

## Theme Edge Design

Recommended edge:

```text
vocabulary_node --belongs_to--> theme_node
```

Rationale:

- `belongs_to` already exists in ULGA-S2 edge schema.
- It is clear, queryable, and non-prerequisite.
- It avoids overloading `supports` or inventing a new `theme_member` edge type.

Recommended metadata:

```json
{
  "mounting_stage": "ULGA-S5E",
  "theme_layer": "core | extended | advanced",
  "theme_membership_type": "primary_topic | secondary_topic | inferred_fallback",
  "weight": 1.0,
  "source_topic": "travel",
  "matched_theme_topic": "travel",
  "sense_specific": true,
  "rule_based": true,
  "blocked_topic_checked": true
}
```

Do not use this layer for vocabulary-to-vocabulary dependency, morphology, chunk, or planner ranking.

## Theme Layer Scope

### Layer A: Core Theme Layer

Examples:

- Home
- Family
- School
- Food
- Animals
- Clothes

Implementation priority:

- A1/A2 concrete themes.
- High confidence primary topic matches.
- Narrow themes with lower ambiguity.

### Layer B: Extended Theme Layer

Examples:

- Travel
- Technology
- Health
- Jobs
- Environment

Implementation priority:

- A2/B1/B2 practical contexts.
- Primary + secondary topic matching.
- Weighted membership allowed.

### Layer C: Advanced Theme Layer

Examples:

- Politics
- Economics
- Philosophy
- Law

Implementation priority:

- B2/C1 advanced themes.
- Conservative mapping only.
- Requires stronger ambiguity controls and possibly manual review.

## Theme Graph Strategy

S5E should support three membership modes:

1. `single-theme`: one vocabulary sense maps to one high-confidence theme.
2. `multi-theme`: one vocabulary sense maps to multiple themes with separate edges.
3. `weighted-theme`: multiple edges carry `weight` and `theme_membership_type`.

Recommended first implementation:

- Generate `belongs_to` edges only.
- Use primary topic matches with higher weight.
- Use secondary topic matches with lower weight.
- Block edges when a vocabulary topic is in the theme's `blocked_topics`.
- Preserve unmatched vocabulary nodes without failure.

Suggested weighting:

| Match type | Weight |
| --- | ---: |
| primary topic | 1.0 |
| secondary topic | 0.65 |
| fallback inferred | 0.35 |

Fallback inferred edges should not be created in S5E unless explicitly requested. They are better deferred to QA or a later implementation.

## Theme Coverage Projection

Expected S5E outputs, if implemented:

- Vocabulary nodes connected: at most the `9,065` nodes with source topics in the first pass.
- Vocabulary nodes isolated: at least `6,631` unless fallback mapping is added.
- Average themes per vocabulary node: likely greater than 1.0 because broad topics such as `communication` and `describing things` appear in many themes.
- Theme edge count: likely much larger than `9,065` if secondary topics are included.

Risk: broad secondary topics can create very dense edges. S5E should cap or report high-degree theme hubs.

## Chunk Integration Analysis

Two integration options exist:

### Option A: Chunk -> Vocabulary -> Theme

Chunks connect to vocabulary anchors, and vocabulary connects to themes.

Benefits:

- Cleaner authority boundaries.
- Avoids duplicating theme logic in chunk layer.
- Easier to update theme policy once.

Tradeoff:

- Chunk-level idioms that do not decompose well may need direct theme hints.

### Option B: Chunk -> Theme

Chunks map directly to themes.

Benefits:

- Useful for idioms and social expressions.
- Can use existing chunk theme hints.

Risks:

- Duplicates theme logic.
- Harder to maintain.
- Can conflict with vocabulary-derived themes.

### Recommendation

S5D recommends a hybrid hierarchy:

```text
Default: Chunk -> Vocabulary -> Theme
Exception: Chunk -> Theme only for idioms, social expressions, discourse markers, and non-compositional chunks.
```

Current chunk readiness:

- Chunks: `4,546`
- Usage class mappings: `4,546`
- Major classes include `general_phrase`, `phrasal_verb`, `prepositional_phrase`, `idiom`, `time_phrase`, and `place_phrase`.

## Authority Readiness Assessment

| Target | Status | Rationale |
| --- | --- | --- |
| Chunk Authority | PARTIAL | Usage classes and theme hints exist, but direct chunk-theme authority should wait until vocabulary-theme edges exist. |
| Morphology Layer | READY | Theme should precede morphology so morphology can inherit or compare theme membership from base/sense nodes. |
| Sentence Pattern Authority | PARTIAL | Theme edges will help select lexical slots, but sentence patterns need separate pattern source authority. |
| Antigravity Planner | PARTIAL | Planner should wait for theme edges and gate checks before ranking nodes. |
| Gate Engine | PARTIAL | Theme Gate design is clear, but no theme edge outputs exist yet. |

## Roadmap Recommendation

Recommended sequence:

1. `ULGA-S5E_VocabularyThemeLayer_Implementation_Fix`
2. `ULGA-S5F_VocabularyThemeLayer_QA_Audit`
3. `ULGA-S5G_VocabularyMorphologyLayer_DesignScan`

Reason:

Theme should precede morphology. Theme membership is sense/context based, while morphology is lemma-family based. Building morphology first would risk pulling theme assignment toward lemma-level grouping, which is unsafe for polysemy.

## S5E Implementation Guardrails

S5E should:

- Read `vocabulary_nodes.json`, `vocabulary/json/vocabulary.json`, `themes/theme_catalog.json`, and `themes/theme_vocab_mapping.json`.
- Generate edges in a new file only.
- Preserve all vocabulary nodes unchanged.
- Use vocabulary node IDs, not lemma strings, as membership targets.
- Use `belongs_to` as the edge type.
- Include `primary_topic` vs `secondary_topic` metadata.
- Report unmatched vocabulary nodes.
- Report high-degree themes and high-theme-count vocabulary nodes.

S5E should not:

- Mutate `vocabulary_nodes.json`.
- Mutate theme catalog or mapping files.
- Add morphology edges.
- Add chunk edges.
- Add planner/recommendation behavior.
- Add runtime validation behavior.

## Forbidden Actions Check

- Created Theme Edges? No.
- Created Vocabulary Edges? No.
- Created Morphology Edges? No.
- Created Chunk Edges? No.
- Modified `vocabulary_nodes.json`? No.
- Modified `theme_catalog.json`? No.
- Modified `theme_mapping.json`? No.
- Modified grammar graph? No.
- Modified runtime? No.
- Created learner_state? No.
- Created planner? No.
- Created recommendation? No.

## Final Verdict

PASS

Theme architecture, readiness analysis, polysemy risk, graph edge design, chunk integration strategy, and roadmap are complete. No runtime or data mutation was performed.


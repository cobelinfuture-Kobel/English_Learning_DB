# ULGA-S8A Dependency Authority Design Scan

## Executive Summary

S8A should define **Dependency Authority** as a cross-authority graph contract for prerequisite, expansion, reinforcement, and recommended ordering signals. It must not become a Learning Path layer. A Learning Path is a query result over dependency edges, learner state, gates, level policy, and planner ranking.

Current ULGA already has partial dependency material:

- Grammar dependency edges: `493` total (`84 prerequisite`, `362 supports`, `30 contrasts_with`, `17 reviews`).
- Vocabulary morphology edges: `9,122 supports`, but these are word-family/semantic formation relations, not automatically learning prerequisites.
- Vocabulary-theme edges: `19,557 belongs_to`, refined down from `88,423` to avoid theme overconnection.
- Chunk-vocabulary edges: `7,804 uses`, mostly low confidence (`6,032 polysemy_fallback`).
- Chunk grammar metadata: `3,522` records, but only `2` unique grammar prerequisites and `388` manual review records.
- Sentence patterns: `1,482` nodes, `1,529` edges (`1,508 uses`, `17 belongs_to`, `4 prerequisite`).
- Pattern vocabulary constraints: `1,344` accepted constraints with query-time candidate policy, not dense graph materialization.

Main conclusion: S8A should create a **new dependency graph contract** that can reuse existing grammar `prerequisite/supports/reviews` evidence, but must normalize dependency semantics into explicit S8A relation names: `REQUIRES`, `EXPANDS`, `REINFORCES`, and `PRECEDES`. Only `REQUIRES` should be gate-eligible by default. Other relations are recommendation or mastery evidence unless manually promoted.

Go recommendation: **GO for S8B/S8C design and builder planning, NO-GO for direct broad graph generation without manual review queues and validator rules.**

## Current ULGA State

### Evidence Inspected

- `ulga/schema/ulga_graph_schema.json`
- `ulga/schema/ulga_node_schema.json`
- `ulga/schema/ulga_edge_schema.json`
- `ulga/graph/grammar_nodes.json`
- `ulga/graph/vocabulary_nodes.json`
- `ulga/graph/chunk_nodes.json`
- `ulga/graph/theme_nodes.json`
- `ulga/graph/sentence_patterns.json`
- `ulga/graph/ulga_sentence_pattern_nodes.json`
- `ulga/graph/grammar_dependency_core_edges.json`
- `ulga/graph/grammar_dependency_extended_edges.json`
- `ulga/graph/grammar_dependency_all_edges.json`
- `ulga/graph/vocabulary_theme_edges.refined.json`
- `ulga/graph/vocabulary_morphology_edges.json`
- `ulga/graph/chunk_vocabulary_edges.json`
- `ulga/graph/chunk_grammar_metadata.json`
- `ulga/graph/pattern_vocabulary_constraints.json`
- `ulga/graph/ulga_sentence_pattern_edges.json`
- `ulga/reports/grammar_dependency_core_summary.json`
- `ulga/reports/grammar_dependency_core_qa_audit.json`
- `ulga/reports/grammar_dependency_extended_summary.json`
- `ulga/reports/grammar_dependency_extended_qa_audit.json`
- `ulga/reports/vocabulary_theme_refinement_summary.json`
- `ulga/reports/vocabulary_morphology_summary.json`
- `ulga/reports/chunk_vocabulary_linkage_summary.json`
- `ulga/reports/chunk_grammar_parsing_summary.json`
- `ulga/reports/chunk_grammar_metadata_qa_audit.json`
- `ulga/reports/sentence_pattern_mount_summary.json`
- `ulga/reports/ulga_sentence_pattern_qa_audit.json`
- `ulga/reports/pattern_vocabulary_constraint_summary.json`
- `ulga/reports/pattern_vocabulary_constraint_qa_audit.json`
- `docs/ulga/ULGA_S1_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S3_GRAMMAR_DEPENDENCY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S4D_EXTENDED_GRAMMAR_DEPENDENCY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S5A_VOCABULARY_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S5D_VOCABULARY_THEME_LAYER_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S5H_VOCABULARY_MORPHOLOGY_LAYER_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S6A_CHUNK_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S6C_CHUNK_VOCABULARY_LINKAGE_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S6G_CHUNK_GRAMMAR_METADATA_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S7A_SENTENCE_PATTERN_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S7C_PATTERN_VOCABULARY_LINKAGE_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S7E_PATTERN_THEME_LINKAGE_DESIGN_SCAN.md`
- `docs/ulga/ulga_roadmap.md`
- `chunk_profile/json/chunks_generator_safe.json`
- `chunk_profile/json/chunk_usage_class_mapping.json`
- `themes/theme_catalog.json`
- `themes/theme_vocab_mapping.json`
- `grammar_profile/json/grammar_profile.json`
- `vocabulary/json/vocabulary.json`

### Missing Evidence

The task listed several filenames without directory prefixes. These root-level paths were not found:

- `chunks_generator_safe.json`
- `chunk_usage_class_mapping.json`
- `theme_catalog.json`
- `theme_vocab_mapping.json`

Equivalent available files were found and inspected by path:

- `chunk_profile/json/chunks_generator_safe.json`
- `chunk_profile/json/chunk_usage_class_mapping.json`
- `themes/theme_catalog.json`
- `themes/theme_vocab_mapping.json`

### Mounted Node Counts

| Node type | Count | CEFR notes |
|---|---:|---|
| GrammarNode | 1,222 | A1-C2, no plus levels |
| VocabularyNode | 15,696 | A1-C2, no plus levels |
| ChunkNode | 3,522 | A1-C2, many B2-C2 chunks |
| ThemeNode | 25 | A1-C1 plus-level progression nodes present |
| SentencePatternNode | 1,482 | A1-C2, mostly chunk-derived |
| SkillNode | 0 mounted | Schema allows `skill`, but no mounted SkillNode evidence found |

### Existing Edge State

| Layer | Edge/record count | Existing relation |
|---|---:|---|
| Grammar dependency all | 493 | `prerequisite`, `supports`, `contrasts_with`, `reviews` |
| Vocabulary theme refined | 19,557 | `belongs_to` |
| Vocabulary morphology | 9,122 | `supports`, metadata relation includes `derived_from`, `compound_of`, `has_suffix`, `has_prefix`, `shares_root` |
| Chunk vocabulary | 7,804 | `uses` |
| Sentence pattern edges | 1,529 | `uses`, `belongs_to`, `prerequisite` |
| Pattern vocabulary constraints | 1,344 records | constraint records, not graph edges |
| Chunk grammar metadata | 3,522 records | metadata refs, not graph edges |

## Dependency Authority Definition

Dependency Authority is the ULGA authority that defines whether one learning node is structurally, pedagogically, or evidentially needed before, during, or after another node. It answers: **what must be known, what helps, what expands, and what should usually come earlier?**

It should own:

- canonical dependency relation semantics;
- edge eligibility for gates, recommendations, and mastery calculations;
- confidence and evidence requirements;
- acyclic hard-gate validation;
- manual review queues for weak or ambiguous dependency claims.

It should not own:

- CEFR level assignment;
- theme membership;
- learning path storage;
- recommendation ranking;
- runtime learner mastery state.

### Difference From CEFR Difficulty Authority

CEFR describes expected learner production or comprehension difficulty. It is not learning order. Existing S3/S4 reports explicitly warn that EGP/CEFR is a difficulty profile, not a dependency profile. A B1 item can require an A2 form, but an A2 item does not automatically require every A1 item.

Dependency Authority may use CEFR as a sanity constraint:

- target should usually not be below a hard prerequisite unless reviewed;
- target should not require a much higher CEFR node without override;
- CEFR can scope candidate rules, but cannot be the only evidence.

### Difference From Learning Path Authority

Learning Path is not an authority layer in current ULGA direction. It is a query result:

```text
learner_state + target + dependency graph + gates + planner policy -> next path
```

Dependency Authority provides the graph facts. The planner chooses a traversal and ranking. Storing hand-authored paths would duplicate and eventually conflict with graph authority.

### Difference From Theme Spiral Authority

Theme Spiral Authority models topical revisiting and increasing communicative scope across levels. It can say that `daily_life_a1` spirals to a broader or more complex theme later. That is not the same as prerequisite. A learner can discuss a B1 travel theme without mastering every A1 daily-life vocabulary node.

Theme spiral can feed recommendation and curriculum pacing. It should only become gate logic when a specific dependency edge is manually promoted with evidence.

## Node Participation Matrix

| Node type | Status | Reason |
|---|---|---|
| GrammarNode | allowed | Strongest existing dependency evidence. Grammar dependency layer already has rule-based hard and soft edges, acyclic hard DAG checks, and CEFR misuse audits. |
| VocabularyNode | limited | Lexical relations are often associative, semantic, morphological, or thematic. Hard dependencies are rare. Use mainly for high-confidence morphology/word-family expansion, numeracy sequences, closed lexical sets, or chunk anchors. |
| ChunkNode | limited | Chunks can require vocabulary anchors and grammar signals, but existing chunk-vocabulary edges are mostly low-confidence fallback and chunk grammar prerequisites are sparse. Gate only when evidence is high or manually reviewed. |
| SentencePatternNode | allowed | Patterns are production frames with explicit grammar refs, chunk refs, slot constraints, and a small existing prerequisite edge set. Pattern-to-pattern dependencies and pattern-to-grammar requirements are valid if controlled. |
| ThemeNode | limited | Themes can participate in spiral/progression and recommendation. They should not become prerequisite gates by default because theme relation is contextual and broad. |
| SkillNode | blocked for S8A/S8C first pass | Schema allows `skill`, but no mounted SkillNode dataset was found. Do not generate dependencies against absent node authority. Revisit after Skill Authority exists. |

## Edge Type Contract

S8A should define logical dependency relations independent of the older physical `edge_type` enum. If implemented before schema expansion, these can be stored either in a dedicated dependency graph file with `relation`, or as existing physical edge types plus `metadata.logical_relation`. The cleaner route is a dedicated `dependency_graph_schema.json`.

### REQUIRES

- Semantic meaning: source node is a necessary prerequisite for target node.
- Allowed source node types: `grammar`, `sentence_pattern`, limited `vocabulary`, limited `chunk`.
- Allowed target node types: `grammar`, `sentence_pattern`, `chunk`, limited `vocabulary`.
- Gate eligible: yes, default only when confidence is high and review status is accepted.
- Recommendation eligible: yes.
- Mastery calculation eligible: yes, source mastery can be required before target readiness.
- Notes: must be acyclic over gate-eligible edges. CEFR alone cannot create this edge.

### EXPANDS

- Semantic meaning: target broadens, specializes, transforms, or extends source knowledge.
- Allowed source node types: `grammar`, `vocabulary`, `chunk`, `sentence_pattern`, limited `theme`.
- Allowed target node types: same type family by default; cross-type only when evidence is explicit.
- Gate eligible: no by default.
- Recommendation eligible: yes.
- Mastery calculation eligible: partial; can contribute to coverage breadth but should not block.
- Notes: maps well to morphology, grammar bridge relations, pattern variants, and theme progression when not strict.

### REINFORCES

- Semantic meaning: source provides practice, review, contrast, or strengthening evidence for target.
- Allowed source node types: `chunk`, `sentence_pattern`, `theme`, `vocabulary`, `grammar`.
- Allowed target node types: `grammar`, `vocabulary`, `chunk`, `sentence_pattern`, `theme`.
- Gate eligible: no.
- Recommendation eligible: yes.
- Mastery calculation eligible: yes, as evidence signal only.
- Notes: useful for review, contrast, retrieval, and chunk/pattern practice. Should not imply order.

### PRECEDES

- Semantic meaning: source usually comes before target pedagogically, but is not a necessary prerequisite.
- Allowed source node types: `grammar`, `sentence_pattern`, `theme`, limited `vocabulary`, limited `chunk`.
- Allowed target node types: same as source type by default; cross-type only with design evidence.
- Gate eligible: no by default; manual override required.
- Recommendation eligible: yes.
- Mastery calculation eligible: limited; can influence readiness confidence but not block.
- Notes: replaces unsafe overuse of `prerequisite` for soft sequencing.

## Dependency And Existing ULGA Edge Relationship

| Existing edge or concept | Reuse decision | Dependency interpretation |
|---|---|---|
| `USES` | Reuse as evidence, not dependency | `chunk -> vocabulary` and `pattern -> chunk/grammar` show composition. Convert to `REQUIRES` only for high-confidence static ingredients with accepted review. Otherwise `REINFORCES`. |
| `CONTAINS` | Do not use for S8A first pass | Current mounted graphs inspected do not show a major `contains` layer. It is structural membership, not prerequisite. |
| `BELONGS_TO` | Reuse as theme/classification evidence only | `vocabulary -> theme` and `pattern -> theme` membership should not become dependency. Can support recommendation and theme leakage audits. |
| `THEME_RELATED` | Avoid as dependency edge | No mounted edge type found with this exact name. The semantic is too broad for gates. Use `REINFORCES` or `EXPANDS` only after S8B theme spiral design. |
| `VOCABULARY_CONSTRAINT` | Reuse as query constraint, not graph dependency | Pattern vocabulary constraints define candidate gating and ranking policy. They should remain constraints unless a specific slot requires prior lexical mastery. |
| `CHUNK_LINKAGE` | Reuse as evidence family | Chunk-vocabulary `uses` edges and chunk grammar metadata can seed dependency candidates, but low-confidence fallback edges must not become hard dependencies. |
| `PATTERN_LINKAGE` | Reuse as evidence family | Existing pattern `uses`, `belongs_to`, and `prerequisite` edges can seed pattern dependencies. Pattern variants need careful distinction between family membership and prerequisite. |
| `prerequisite` | Reuse selectively | Existing grammar hard prerequisites can map to `REQUIRES`. Existing soft or pattern prerequisites need review before gate eligibility. |
| `supports` | Reuse as `EXPANDS` or `REINFORCES` evidence | Existing grammar and morphology supports are not automatically gateable. |
| `reviews` | Reuse as `REINFORCES` | Review edges are mastery evidence/recommendation signals, not hard dependencies. |
| `contrasts_with` | Reuse as `REINFORCES` | Contrast pairs help practice and diagnostics, not order. |
| `spiral_to` | Reserve for Theme Spiral / `EXPANDS` or `PRECEDES` | Do not map to `REQUIRES` without manual review. |

## Seed Strategy

| Seed class | Strategy | Confidence | Notes |
|---|---|---|---|
| Grammar dependency seed | Map existing `grammar_dependency_all_edges.json`. `metadata.dependency_class = hard_prerequisite` becomes `REQUIRES`; `soft_prerequisite`, `unlock_relation`, `bridge_relation` become `EXPANDS` or `PRECEDES`; `spiral_review` and `reviews` become `REINFORCES`; `contrast_pair` becomes `REINFORCES`. | authoritative for existing accepted hard grammar edges; derived for soft edges | Existing QA: hard DAG acyclic, CEFR not used as order, but 815 grammar nodes remain isolated. |
| Vocabulary semantic expansion seed | Use `vocabulary_morphology_edges.json` metadata relation. `derived_from`, `has_prefix`, `has_suffix`, `compound_of`, `shares_root` become `EXPANDS` candidates, not `REQUIRES`. Numeracy or closed-set dependencies require separate explicit rules. | derived / heuristic | Vocabulary acquisition is associative. Morphology can help recommendation and mastery breadth, but most edges should not gate. |
| Chunk dependency seed | Use `chunk_vocabulary_edges.json` plus `chunk_grammar_metadata.json`. High-confidence `exact_unique_sense` anchors can seed `REINFORCES` or limited `REQUIRES`; low-confidence `polysemy_fallback` goes to manual review only. Grammar prerequisites from chunk metadata can seed candidate `REQUIRES`, but current unique prerequisite coverage is very low. | heuristic / manual_review_required | Existing chunk-vocabulary edges: 6,032 low-confidence fallback. Existing chunk grammar metadata has 388 manual review records. |
| Pattern dependency seed | Use `ulga_sentence_pattern_edges.json`, pattern metadata refs, and `pattern_vocabulary_constraints.json`. Existing 4 pattern prerequisites can seed `REQUIRES` after review. Pattern `uses` edges to grammar/chunk become evidence; slot constraints remain query-time gates, not dependency edges. | derived / manual_review_required | Avoid dense pattern-vocabulary edges. Existing S7C/S7D explicitly recommend query-time candidate pools. |
| Theme dependency seed | Use `themes/theme_vocab_mapping.json` progression fields and `theme_nodes.json`. Create `EXPANDS` or `PRECEDES` for theme progression only after S8B ThemeSpiralAuthority design. Never seed `REQUIRES` by default. | heuristic / manual_review_required | Theme progression is pacing and spiral, not prerequisite. |

## Graph Schema Proposal

Proposed file: `ulga/schema/dependency_graph_schema.json` in a future implementation task. S8A does not create it.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "ulga/schema/dependency_graph_schema.json",
  "title": "ULGA Dependency Graph Schema",
  "contract_version": "ULGA-S8A-proposal",
  "type": "object",
  "additionalProperties": false,
  "required": ["graph_metadata", "nodes", "edges"],
  "properties": {
    "graph_metadata": {
      "type": "object",
      "required": [
        "graph_id",
        "contract_version",
        "generated_at",
        "source_graphs",
        "dependency_policy",
        "cefr_is_not_dependency_order"
      ],
      "properties": {
        "graph_id": { "type": "string" },
        "contract_version": { "type": "string" },
        "generated_at": { "type": ["string", "null"] },
        "source_graphs": { "type": "array", "items": { "type": "string" } },
        "dependency_policy": { "type": "string" },
        "cefr_is_not_dependency_order": { "type": "boolean", "const": true }
      }
    },
    "nodes": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["node_id", "node_type", "cefr_level"],
        "properties": {
          "node_id": { "type": "string" },
          "node_type": {
            "type": "string",
            "enum": ["grammar", "vocabulary", "chunk", "sentence_pattern", "theme", "skill"]
          },
          "cefr_level": { "type": ["string", "null"] }
        }
      }
    },
    "edges": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "edge_id",
          "source_id",
          "target_id",
          "relation",
          "confidence",
          "source_authority",
          "evidence",
          "review_status",
          "gate_eligible",
          "planner_weight",
          "notes"
        ],
        "properties": {
          "edge_id": { "type": "string", "pattern": "^dependency_edge:[A-Za-z0-9_.:-]+$" },
          "source_id": { "type": "string" },
          "target_id": { "type": "string" },
          "relation": {
            "type": "string",
            "enum": ["REQUIRES", "EXPANDS", "REINFORCES", "PRECEDES"]
          },
          "confidence": {
            "type": "object",
            "required": ["value", "method"],
            "properties": {
              "value": { "type": "number", "minimum": 0, "maximum": 1 },
              "method": {
                "type": "string",
                "enum": ["authoritative", "derived", "heuristic", "manual_review_required"]
              }
            }
          },
          "source_authority": {
            "type": "object",
            "required": ["authority_name", "source_file", "derivation"],
            "properties": {
              "authority_name": { "type": "string" },
              "source_file": { "type": ["string", "null"] },
              "source_edge_id": { "type": ["string", "null"] },
              "source_record_id": { "type": ["string", "null"] },
              "derivation": { "type": "string" }
            }
          },
          "evidence": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["evidence_type", "value"],
              "properties": {
                "evidence_type": { "type": "string" },
                "value": {},
                "notes": { "type": "string" }
              }
            }
          },
          "review_status": {
            "type": "string",
            "enum": ["accepted", "needs_review", "blocked", "deprecated"]
          },
          "gate_eligible": { "type": "boolean" },
          "planner_weight": { "type": "number", "minimum": 0, "maximum": 1 },
          "notes": { "type": "array", "items": { "type": "string" } }
        }
      }
    }
  }
}
```

## Validation Plan

### Schema Validation

- Validate required top-level keys: `graph_metadata`, `nodes`, `edges`.
- Validate relation enum: `REQUIRES`, `EXPANDS`, `REINFORCES`, `PRECEDES`.
- Validate `gate_eligible` is boolean.
- Validate `planner_weight` between `0` and `1`.
- Validate `confidence.value` between `0` and `1`.
- Validate `confidence.method` in accepted confidence classes.

### Missing Node Validation

- Every `source_id` and `target_id` must resolve to a mounted ULGA node.
- Skill dependencies must fail until SkillNode authority is mounted.
- Root-level missing source files should be reported as Missing Evidence, not inferred.

### Circular Dependency Detection

- Run cycle detection only on `relation = REQUIRES` and `gate_eligible = true`.
- `EXPANDS`, `REINFORCES`, and `PRECEDES` can form pedagogical networks but should not block DAG validation.
- Self-loops are blocked for all relation types unless a future review edge explicitly allows self-review.

### Cross-Level Anomaly Detection

- Flag `REQUIRES` where target CEFR is lower than source CEFR.
- Flag gaps greater than one broad CEFR band unless explicit bridge evidence exists.
- Plus-level theme nodes must not be coerced into grammar/vocabulary CEFR order.

### Impossible Dependency Detection

- Block ThemeNode `REQUIRES` edges by default.
- Block VocabularyNode `REQUIRES` from theme membership alone.
- Block ChunkNode `REQUIRES` sourced only from low-confidence polysemy fallback.
- Block PatternNode `REQUIRES` when the only evidence is same family or variant membership.

### Low-Confidence Edge Audit

- Any edge with confidence below `0.75` must be `needs_review` unless relation is non-gating.
- Any `gate_eligible = true` edge with `confidence.method = heuristic` must fail validation.
- Existing chunk `polysemy_fallback` evidence should default to manual review.

### Theme Leakage Audit

- Ensure `belongs_to` theme evidence does not create `REQUIRES`.
- Audit theme-derived dependency edges for broad topics, secondary topics, and inferred low-confidence theme edges.
- Prevent pattern/theme/vocabulary chains from making dense implicit dependencies.

### CEFR Contradiction Audit

- Detect rules where CEFR is the only evidence.
- Detect dependency direction caused solely by lower-to-higher CEFR.
- Require evidence text, source edge, or rule id for every `REQUIRES`.

### Manual Review Queue

Queue edge candidates when:

- confidence method is `heuristic`;
- source authority is chunk fallback, theme progression, or semantic association;
- cross-type dependency is proposed;
- target level is lower than source level;
- relation is `REQUIRES` but evidence is not authoritative;
- pattern variant/family relationship is being promoted to prerequisite.

## Risk Register

| Risk | Severity | Analysis | Mitigation |
|---|---|---|---|
| CEFR misused as dependency | High | Existing docs repeatedly warn CEFR is difficulty, not order. Rule-only CEFR inference would overgate and create false prerequisites. | Validator must reject CEFR-only `REQUIRES`; store `cefr_is_not_dependency_order = true`. |
| Theme Spiral misused as prerequisite | High | Theme progression is topical revisit and curriculum pacing, not mandatory mastery. | Theme edges default to `EXPANDS` or `PRECEDES`, never `REQUIRES` without manual acceptance. |
| Vocabulary semantic relation misread as dependency | High | Vocabulary relations are associative. Morphology and theme co-membership help ranking but rarely block learning. | Vocabulary `REQUIRES` limited to explicit closed sets, numeracy, or manual review. |
| Pattern variant misread as prerequisite | Medium | Pattern family membership does not mean one variant must precede another. | Family/variant edges stay `EXPANDS`; `REQUIRES` requires explicit grammar or production evidence. |
| Over-gating makes planner too conservative | High | If every composition edge becomes prerequisite, planner will block too many valid learning options. | Only `REQUIRES` with accepted review gates. `EXPANDS`, `REINFORCES`, `PRECEDES` are recommendation signals. |
| Dense edge explosion | High | S7C estimated full pattern-vocabulary candidate materialization can exceed `20M+` edges. | Keep pattern-vocabulary constraints query-time; do not materialize dense dependency edges. |
| Chunk low-confidence anchors pollute gates | Medium | Chunk-vocabulary linkage has `6,032` low-confidence fallback edges. | Use fallback only for recommendation or manual review; no direct gate eligibility. |
| Cross-authority cycles | Medium | Cross-type dependencies can produce loops through grammar, pattern, chunk, and vocabulary references. | Cycle detection over gate-eligible `REQUIRES` across all allowed node types. |
| Schema conflict with ULGA-S2 edge enum | Medium | Existing schema has lowercase physical edge types; S8A proposes uppercase logical relations. | Use dedicated dependency graph schema or `metadata.logical_relation` until schema migration. |

## Recommended Roadmap

### ULGA-S8B ThemeSpiralAuthority_DesignScan

Define Theme Spiral separately before dependency builder work. Required outputs:

- Theme spiral edge contract (`SPIRAL_TO`, `EXPANDS`, `PRECEDES`, or equivalent).
- Theme progression validation.
- Rules preventing theme spiral from becoming prerequisite.
- Theme leakage audit design for vocabulary and pattern inference.

### ULGA-S8C DependencyEdgeBuilder

Implement only after S8B. Minimal builder scope:

- Read existing graph files.
- Emit a new dependency graph file only.
- Map existing accepted grammar hard prerequisites to `REQUIRES`.
- Map soft grammar and morphology edges to non-gating `EXPANDS` or `REINFORCES`.
- Put chunk fallback, theme, and pattern variant candidates into review queues.
- Do not modify existing graph/json/source files.

### ULGA-S8D DependencyAuthority_QA_Audit

Audit the generated dependency graph:

- schema pass/fail;
- missing node checks;
- hard dependency DAG;
- cross-level anomalies;
- CEFR-only evidence rejection;
- manual review counts;
- over-gating simulation summary.

### ULGA-S8E LearningSignalClassification

Classify graph signals into:

- gate signal;
- recommendation signal;
- mastery evidence signal;
- review/practice signal;
- theme/context signal;
- runtime learner-state signal.

This prevents future planner logic from treating all edges as blockers.

### ULGA-S9A LearnerStateAuthority_DesignScan

Design learner state only after dependency signals are classified:

- mastery evidence model;
- prerequisite satisfaction explanation;
- stale mastery and review decay;
- per-node and per-edge readiness;
- runtime status boundaries.

## Go / No-Go Recommendation

Recommendation: **GO with constraints**.

Proceed to S8B before S8C. Dependency Authority is feasible because grammar dependency already has validated seed material and existing graph layers provide usable evidence. However, broad cross-type dependency generation is not ready without Theme Spiral separation, manual review queues, and strict validators.

No-go conditions for S8C:

- generating dependencies from CEFR alone;
- converting all `uses` edges into `REQUIRES`;
- converting theme progression into prerequisites;
- materializing dense pattern-vocabulary candidate edges;
- making heuristic or low-confidence edges gate-eligible.

Minimal safe first implementation:

- grammar hard prerequisites -> accepted `REQUIRES`;
- grammar soft/bridge/review/contrast -> non-gating relations;
- vocabulary morphology -> `EXPANDS`;
- pattern prerequisites -> review before gate;
- chunk/theme candidates -> manual review queues.

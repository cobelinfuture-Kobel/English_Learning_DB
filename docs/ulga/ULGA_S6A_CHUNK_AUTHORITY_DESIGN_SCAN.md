# ULGA-S6A Chunk Authority Design Scan

This report designs the ULGA Chunk Authority Layer and defines how chunks, phrases, and collocations should connect to Vocabulary, Theme, Morphology, and Grammar layers.

Task scope: design scan only. No chunk nodes, chunk edges, graph JSON, runtime files, learner state, planner, recommendation engine, or source authority files were modified.

---

## 1. Files Created

- `docs/ulga/ULGA_S6A_CHUNK_AUTHORITY_DESIGN_SCAN.md`

## 2. Files Modified

- None.

## 3. Files Inspected

Chunk Authority:

- `chunk_profile/json/chunks.json`
- `chunk_profile/json/chunks_generator_safe.json`
- `chunk_profile/json/chunk_equivalence_groups.json`
- `chunk_profile/json/chunk_usage_class_mapping.json`

Existing ULGA layers:

- `ulga/graph/vocabulary_nodes.json`
- `ulga/graph/vocabulary_theme_edges.refined.json`
- `ulga/graph/vocabulary_morphology_edges.json`
- `ulga/graph/grammar_dependency_all_edges.json`
- `ulga/graph/theme_nodes.json`

Related design and QA documents:

- `docs/ulga/ULGA_S5J_VOCABULARY_MORPHOLOGY_LAYER_QA_AUDIT.md`
- `docs/ulga/ULGA_S5G_VOCABULARY_THEME_REFINEMENT_QA_AUDIT.md`
- `docs/ulga/ULGA_S5A_VOCABULARY_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ulga_schema_contract.md`
- `docs/ulga/ulga_roadmap.md`

---

## 4. Chunk Authority Assessment

### 4.1 Source Metrics

| Metric | Value |
| --- | ---: |
| Total raw chunks | 4,546 |
| Generator-safe chunks | 3,522 |
| Canonical safe chunks | 3,522 |
| Equivalent groups | 924 |
| Raw records represented by safe layer | 4,546 |
| Equivalent IDs covered by equivalence groups | 1,948 |
| Generator allowed count | 3,522 |
| Validator accepts equivalents count | 3,522 |

Interpretation:

- The safe layer is the correct mounting source for ULGA ChunkNode candidates, because it collapses raw duplicates into canonical safe records while preserving source trace through `canonical_chunk_id`, `equivalent_ids`, and `raw_count`.
- Raw `chunks.json` should remain an authority source, not a direct graph mounting source.
- `chunk_equivalence_groups.json` is mature enough for validator acceptance but should not become graph edges in S6B.

### 4.2 Usage Class Distribution

| usage_class | Safe chunks |
| --- | ---: |
| general_phrase | 1,770 |
| phrasal_verb | 709 |
| prepositional_phrase | 304 |
| idiom | 260 |
| time_phrase | 180 |
| compound_noun | 112 |
| place_phrase | 100 |
| quantity_phrase | 16 |
| discourse_marker | 14 |
| modal_expression | 10 |
| compound_adjective | 9 |
| social_expression | 9 |
| greeting | 7 |
| grammar_term | 5 |
| opinion_expression | 5 |
| emotion_expression | 5 |
| daily_routine | 4 |
| request_expression | 3 |

### 4.3 CEFR Distribution

| Level | Safe chunks |
| --- | ---: |
| A1 | 76 |
| A2 | 243 |
| B1 | 566 |
| B2 | 946 |
| C1 | 559 |
| C2 | 1,132 |

Risk note: the chunk pool is heavily advanced-level. S6B should not infer beginner learning priority from raw chunk count.

### 4.4 Chunk Type Distribution

| chunk_type | Safe chunks |
| --- | ---: |
| phrase | 2,634 |
| phrasal verb | 726 |
| multi_word_entry | 162 |

### 4.5 Theme Hint Distribution

| theme_hint | Count |
| --- | ---: |
| General | 3,077 |
| Personal | 194 |
| Travel | 78 |
| Hobbies | 54 |
| Shopping | 50 |
| Health | 42 |
| Home | 24 |
| Food | 20 |
| School | 11 |
| DailyRoutine | 2 |

Risk note: `theme_hint` is sparse and broad. It should be treated as a weak projection hint, not as a direct ThemeNode authority.

### 4.6 Priority Band Distribution

| priority_band | Safe chunks |
| --- | ---: |
| core | 342 |
| common | 687 |
| low | 1,436 |
| extended | 1,057 |

### 4.7 Frequency Proxy Score Distribution

| Score band | Safe chunks |
| --- | ---: |
| 0.00-0.249 | 1,178 |
| 0.25-0.499 | 944 |
| 0.50-0.749 | 1,058 |
| 0.75-1.00 | 342 |

Frequency proxy summary:

- Min: `0.0`
- Max: `1.0`
- Average: `0.4151`

---

## 5. ChunkNode Design

Recommended conceptual ChunkNode shape:

```json
{
  "id": "chunk:SAFE_CHUNK_000001",
  "node_type": "chunk",
  "label": "insofar as",
  "normalized_chunk": "insofar as",
  "canonical_chunk_id": "EVP_CHUNK_000001",
  "safe_id": "SAFE_CHUNK_000001",
  "cefr_level": "C2",
  "chunk_type": "multi_word_entry",
  "usage_class": "general_phrase",
  "theme_hint": ["General"],
  "priority_band": "low",
  "frequency_proxy_score": 0.22,
  "generator_allowed": true,
  "validator_accepts_equivalents": true,
  "authority_source": {
    "source_name": "EVP Chunk Safe Layer",
    "source_file": "chunk_profile/json/chunks_generator_safe.json",
    "source_record_id": "SAFE_CHUNK_000001",
    "derivation": "derived_safe_layer"
  },
  "confidence": {
    "value": 0.9,
    "method": "derived_safe_layer",
    "notes": ["Canonical safe chunk generated from source-backed EVP chunk records."]
  },
  "version": {
    "contract": "ULGA-S2",
    "source_version": "1.0.0",
    "generated_at": null
  },
  "metadata": {
    "source_chunk_id": "EVP_CHUNK_000001",
    "equivalent_ids": ["EVP_CHUNK_000001"],
    "raw_count": 1,
    "guideword": null,
    "topic": null,
    "source_file": "English Vocabulary Profile Online.xlsx",
    "mounting_stage": "ULGA-S6B",
    "is_canonical": true,
    "safe_layer_source": "EVP_DERIVED_SAFE_LAYER"
  }
}
```

Design constraints:

- Use `safe_id` as the deterministic node identity source.
- Preserve `canonical_chunk_id` and `equivalent_ids` as metadata, not separate graph nodes.
- Keep raw duplicate records out of generator-facing graph traversal.
- Keep `generated_at` null in design artifacts and populate only during S6B implementation.
- Normalize `level` from safe layer into `cefr_level` for consistency with existing ULGA vocabulary and theme nodes.

---

## 6. First-Class Node Decision

### Option A: Chunk only as Vocabulary metadata

Assessment: rejected.

This keeps graph size small, but it collapses phrase-level authority into vocabulary records. It cannot represent formulaic expressions, idioms, discourse markers, phrasal verbs, or generator-safe chunk reuse cleanly. It also makes equivalence handling difficult because equivalent chunks do not belong to only one vocabulary item.

### Option B: Chunk as formal ChunkNode

Assessment: recommended.

Chunk is already an approved ULGA node family in `ulga_schema_contract.md`. The existing safe layer provides canonical identity, duplicate handling, usage class, priority, generator permission, and validator equivalence behavior. A formal ChunkNode allows Antigravity to query phrases directly without mutating vocabulary authority.

### Option C: Chunk only in generator safe layer, outside ULGA

Assessment: rejected as long-term architecture.

This protects runtime safety in the short term, but it prevents the graph from explaining why a chunk is recommended, which vocabulary anchors it uses, which theme it supports, and whether it has grammar prerequisites.

Recommendation: choose Option B. Chunks should be ULGA first-class nodes, mounted from `chunks_generator_safe.json`, with raw source and equivalence data preserved as metadata.

---

## 7. Vocabulary Linkage Design

Recommended edge:

```text
chunk --uses--> vocabulary
```

Examples:

- `bus stop` uses `bus` and `stop`
- `play football` uses `play` and `football`
- `ice cream` uses `ice` and `cream`

### 7.1 Sense Node Requirement

Chunk anchors should target vocabulary sense nodes, not lemma-only placeholders. Existing vocabulary node IDs include source record identity, for example `vocabulary:play:v_6582`, which is already closer to sense-specific authority than a pure lemma node.

### 7.2 Polysemy Selection

When a chunk component maps to multiple vocabulary senses:

1. Prefer exact normalized lemma plus part-of-speech compatibility.
2. Prefer vocabulary nodes whose topic matches the chunk `topic`.
3. Prefer theme overlap when refined vocabulary theme edges provide a strong primary theme.
4. Prefer lower CEFR only when multiple candidates remain equally plausible and the chunk level does not contradict it.
5. If no candidate is reliable, do not create a hard edge.

### 7.3 Unresolved Disambiguation

If sense selection cannot be resolved, S6D should either:

- omit the `USES` edge and record a review candidate, or
- create a provisional anchor only if the edge carries `confidence.value < 0.8`, `metadata.low_confidence_anchor = true`, and `metadata.requires_manual_review = true`.

### 7.4 Low-Confidence Vocabulary Anchors

Low-confidence anchors are allowed only as non-gating, provisional signals. They must not unlock generator output, learning path prerequisites, or gate decisions until audited.

---

## 8. Theme / Grammar / Morphology Linkage Design

### 8.1 Theme Linkage

Default projection:

```text
chunk -> vocabulary -> theme
```

Direct `chunk -> theme` edges should be prohibited for compositional chunks because vocabulary anchors already carry refined theme membership.

Direct `chunk -> theme` may be allowed only for:

- idioms
- social expressions
- discourse markers
- non-compositional chunks
- formulaic expressions

Even in those cases, the direct projection should be a weak `ALIGNS_WITH` or equivalent non-gating relation in a later design, not a hard prerequisite.

Reason: S5G reduced vocabulary-theme overconnection from 88,423 original edges to 19,557 refined edges. Direct chunk-theme projection must not reintroduce theme leakage through broad `theme_hint` values such as `General`.

### 8.2 Grammar Linkage

Chunks that may need grammar metadata:

- `going to`
- `used to`
- `have to`
- `there is`
- `a lot of`
- `as soon as`

Recommendation:

- Do not create direct chunk-to-grammar graph edges in S6B.
- Store grammar references in `metadata.grammar_prerequisites`.
- Permit a direct grammar edge only if the chunk itself is a grammar pattern authority, not just a lexical phrase.

Reason: existing grammar dependency edges are grammar-to-grammar prerequisites. Mixing phrase evidence into grammar graph edges would contaminate the dependency layer and create unclear gate behavior.

### 8.3 Morphology Linkage

Recommendation:

- Do not create direct morphology-to-chunk or chunk-to-morphology edges.
- Let chunks inherit morphology signals through vocabulary anchors.

Reason: S5J established morphology as a signal rather than a hard prerequisite. Direct chunk morphology edges would create graph bloat and false prerequisite risk.

---

## 9. Chunk Dependency Strategy

Chunk-to-chunk dependencies should not be hard prerequisites in the initial layer.

Classification:

| Example | Classification | Handling |
| --- | --- | --- |
| `bus stop` -> `bus station` -> `train station` | theme progression / collocation family | `related_to` metadata only |
| `ice cream` -> `ice cream cone` | collocation expansion | `related_to` or `expands` metadata only |
| `look` -> `look after` | not a chunk dependency; vocabulary anchor plus phrase usage | use vocabulary anchors |
| `there is` -> `there are` | possible grammar pattern relation | grammar metadata only until grammar-pattern authority exists |

True dependency should be reserved for cases where chunk B cannot be understood without chunk A as a fixed expression. That condition is rare and should require manual review.

Initial policy:

- No hard chunk prerequisites.
- Use soft `supports`, `related_to`, or `expansion_of` metadata in later stages.
- Never let soft chunk relation block learning path progression.

---

## 10. Chunk Layering Strategy

Layer A: Chunk Node Mounting

- Mount one ChunkNode per safe chunk.
- Preserve canonical and equivalent source trace.
- No vocabulary edges yet.

Layer B: Chunk Vocabulary Anchor Layer

- Build `chunk --uses--> vocabulary` edges.
- Apply sense disambiguation and low-confidence review rules.

Layer C: Chunk Theme Projection Layer

- Derive theme through vocabulary anchors by default.
- Allow direct theme projection only for non-compositional usage classes.

Layer D: Chunk Grammar Metadata Layer

- Add `metadata.grammar_prerequisites` where chunk meaning is grammar-pattern-like.
- Avoid direct grammar graph edges except for formal grammar pattern nodes.

Layer E: Chunk Collocation / Expansion Layer

- Add soft relatedness or expansion metadata.
- Avoid hard chunk-to-chunk prerequisites.

Layer F: Chunk QA Audit

- Validate duplicate safety, source trace, generator permissions, validator equivalence, vocabulary anchors, theme leakage, grammar contamination, and graph endpoint integrity.

---

## 11. Chunk Antigravity Value

Chunk Layer improves Antigravity by enabling:

- collocation-safe generation: generator can prefer canonical safe chunks instead of raw duplicate phrases.
- phrase-based output: exercises can target natural phrase units rather than isolated vocabulary.
- formulaic language: social expressions, discourse markers, and idioms can be selected as teachable units.
- lexical chunk recycling: known vocabulary anchors can unlock controlled phrase reuse.
- theme-aware speaking practice: chunks can be projected into themes through vocabulary anchors.
- sentence pattern slot filling: grammar-like chunks can be referenced as metadata without polluting grammar dependencies.

Boundary: Antigravity should consume audited ChunkNodes only after S6B/S6E. This S6A file does not authorize runtime integration.

---

## 12. Risk Analysis

### Polysemy Anchor Risk

Risk: chunks such as `play football` and `play a role` use different senses of the same surface word.

Mitigation: target vocabulary sense nodes; use topic, part of speech, theme, and CEFR compatibility; mark unresolved anchors as low confidence or review-only.

### Over-Linking Risk

Risk: decomposing every token in a phrase may create noisy anchors for function words or accidental substrings.

Mitigation: ignore stopword-only anchors unless the chunk is grammar-pattern-like; require normalized token boundaries; do not split opaque idioms aggressively.

### Equivalent Group Duplication Risk

Risk: mounting raw records instead of safe canonical records would duplicate nodes and inflate generator choices.

Mitigation: mount from `chunks_generator_safe.json`; preserve raw IDs only in metadata.

### Theme Leakage Risk

Risk: broad `theme_hint` values, especially `General`, may create meaningless theme links.

Mitigation: use vocabulary-to-theme projection as default; direct chunk-theme edges only for restricted non-compositional classes.

### Grammar Contamination Risk

Risk: direct chunk-to-grammar edges could blur phrase evidence with grammar prerequisite authority.

Mitigation: use `metadata.grammar_prerequisites`; create direct graph edges only when a chunk becomes a formal grammar pattern authority.

### Generator Safe Layer Mismatch

Risk: ULGA may mount nodes that generator policy would not allow.

Mitigation: mount only safe records with `generator_allowed = true`; expose generator eligibility as a first-class field and audit it in S6E.

### Low Frequency Chunk Noise

Risk: advanced and low-priority chunks dominate the pool.

Mitigation: keep `priority_band` and `frequency_proxy_score`; planner should prefer `core` and `common` chunks unless target level or theme requires otherwise.

### CEFR Misuse Risk

Risk: chunk CEFR does not always equal the difficulty of every component word.

Mitigation: treat chunk CEFR as phrase-level authority. Do not downgrade or upgrade chunk level solely from vocabulary anchors.

### Repeated Execution Risk

Risk: S6B generator may produce duplicate nodes if identity is not deterministic.

Mitigation: derive node ID from `safe_id`; make output generation idempotent; validate duplicate node IDs.

### Process Restart / Runtime Risk

Risk: runtime components may accidentally read partial graph artifacts.

Mitigation: S6A creates no runtime files. S6B should write graph artifacts atomically and keep them out of runtime until QA accepted.

---

## 13. Authority Readiness Assessment

| Area | Status | Rationale |
| --- | --- | --- |
| Chunk Node Mounting | READY | Safe layer has canonical IDs, source trace, equivalence metadata, generator flags, and priority fields. |
| Chunk Vocabulary Linkage | PARTIAL | Vocabulary nodes exist, but sense anchoring rules and low-confidence review queues are not implemented. |
| Chunk Theme Projection | PARTIAL | Refined theme layer exists, but direct chunk-theme policy needs a separate design scan. |
| Chunk Grammar Metadata | PARTIAL | Grammar graph exists, but chunk grammar prerequisites need metadata policy and matching rules. |
| Sentence Pattern Authority | NOT READY | No formal sentence pattern authority source exists yet. |
| Antigravity Planner | NOT READY | Planner must wait for mounted ChunkNodes, anchor QA, and Gate Engine boundaries. |
| Gate Engine | NOT READY | Gate policy should not consume chunk authority before S6E QA. |

---

## 14. Roadmap Recommendation

Recommended next sequence:

1. `ULGA-S6B_ChunkNodeMounting_Fix`
2. `ULGA-S6C_ChunkVocabularyLinkage_DesignScan`
3. `ULGA-S6D_ChunkVocabularyLinkage_Implementation_Fix`
4. `ULGA-S6E_ChunkVocabularyLinkage_QA_Audit`
5. `ULGA-S6F_ChunkThemeProjection_DesignScan`
6. `ULGA-S6G_ChunkGrammarMetadata_DesignScan`

Chunk Node Mounting can start directly in S6B.

Conditions for S6B:

- Mount only from `chunks_generator_safe.json`.
- Do not create chunk edges.
- Do not modify chunk source JSON.
- Preserve `equivalent_ids`, `raw_count`, and `canonical_chunk_id`.
- Validate node count equals safe chunk count: `3,522`.
- Validate all mounted nodes have `generator_allowed = true`.
- Validate no raw duplicate chunk creates a separate ChunkNode.

---

## 15. Forbidden Actions Check

- Modified `chunks.json`? **No**
- Modified `chunks_generator_safe.json`? **No**
- Modified `chunk_equivalence_groups.json`? **No**
- Modified `chunk_usage_class_mapping.json`? **No**
- Created chunk nodes? **No**
- Created chunk edges? **No**
- Modified vocabulary / theme / morphology / grammar graph? **No**
- Created `learner_state`? **No**
- Implemented planner / recommendation / learning path? **No**
- Modified runtime? **No**

---

## 16. Final Verdict

**Final Verdict: WARNING_ACCEPTED**

S6A design requirements are complete:

- Chunk Authority Assessment completed.
- ChunkNode design completed.
- First-class node decision completed.
- Vocabulary, Theme, Grammar, and Morphology linkage designs completed.
- Layering strategy and roadmap completed.
- No protected data, graph, or runtime files were modified.

Warning reasons:

- `theme_hint` is too broad to serve as direct theme authority.
- Vocabulary anchoring will require careful sense disambiguation.
- Chunk metadata is sufficient for mounting but not sufficient for final planner or gate use.

Recommended next task:

- `ULGA-S6B_ChunkNodeMounting_Fix`

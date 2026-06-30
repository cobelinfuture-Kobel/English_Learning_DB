# ULGA-S7D Pattern Vocabulary Constraint Implementation Closeout

## 1. Files Created

- `ulga/builders/build_pattern_vocabulary_constraints.py`
- `ulga/validators/validate_pattern_vocabulary_constraints.py`
- `tests/ulga/test_pattern_vocabulary_constraints.py`
- `ulga/graph/pattern_vocabulary_constraints.json`
- `ulga/graph/pattern_vocabulary_candidate_query_contract.json`
- `ulga/reports/pattern_vocabulary_constraint_summary.json`
- `docs/ulga/ULGA_S7D_PATTERN_VOCABULARY_CONSTRAINT_IMPLEMENTATION_CLOSEOUT.md`

## 2. Files Modified

- None.

Existing sentence pattern, vocabulary, theme, chunk, grammar, and schema source files were not mutated.

## 3. Source Inputs Used

- `ulga/graph/sentence_patterns.json`
- `docs/ulga/ULGA_S7C_PATTERN_VOCABULARY_LINKAGE_DESIGN_SCAN.md`

Reference inputs inspected during implementation:

- `ulga/graph/vocabulary_nodes.json`
- `ulga/graph/vocabulary_theme_edges.refined.json`
- `vocabulary/json/vocabulary.json`
- `themes/theme_vocab_mapping.json`
- `themes/theme_catalog.json`
- `ulga/schema/ulga_node_schema.json`
- `ulga/schema/ulga_edge_schema.json`

## 4. Active Constraint Count

- Source sentence patterns: `1,482`
- Active pattern constraint records emitted: `1,344`
- Slot constraints emitted: `1,932`
- Active criteria: `review_status == accepted` and `generator_allowed == true`

## 5. Inactive / Skipped Pattern Count

- Inactive skipped patterns: `138`
- Skip reason: `inactive_review_status_or_generator_blocked`
- `needs_review` patterns were not emitted as active constraints.

## 6. Slot Type Coverage

| Slot Type | Count |
| --- | ---: |
| `noun_phrase` | 1,552 |
| `verb` | 206 |
| `verb_infinitive` | 101 |
| `verb_gerund` | 60 |
| `verb_stem` | 5 |
| `multi_type` | 3 |
| `proper_noun` | 1 |
| `noun_phrase_1` | 1 |
| `noun_phrase_2` | 1 |
| `time` | 1 |
| `adjective` | 1 |

## 7. Compatibility Class Distribution

| Compatibility Class | Count |
| --- | ---: |
| `common_noun_phrase` | 1,557 |
| `generic_object` | 1,557 |
| `action_verb` | 312 |
| `activity_gerund` | 62 |
| `descriptive_adjective` | 2 |
| `person_entity` | 1 |
| `time_expression` | 1 |

## 8. CEFR Gate Distribution

| Max CEFR | Slot Constraint Count |
| --- | ---: |
| `A1` | 32 |
| `A2` | 88 |
| `B1` | 307 |
| `B2` | 636 |
| `C1` | 293 |
| `C2` | 576 |

Rule summary:

- Manual A1 Core Pattern constraints use `max_cefr = A1`.
- Accepted chunk-derived constraints use the pattern CEFR level.
- Plus-one vocabulary allowance is disabled by default.

## 9. Theme Gate Distribution

| Theme Gate Mode | Slot Constraint Count |
| --- | ---: |
| `hard_filter` | 19 |
| `soft_filter` | 1,913 |

Rule summary:

- Manual A1 constraints use `hard_filter` when pattern `theme_refs` exist.
- Chunk-derived accepted constraints use `soft_filter`.
- Theme source authorities were not mutated.

## 10. Frequency Hint Distribution

| Frequency Hint Mode | Slot Constraint Count |
| --- | ---: |
| `ranking_signal` | 1,932 |

Rule summary:

- Frequency is never a hard blocker in S7D.
- Low-frequency vocabulary remains allowed.
- A1/A2 constraints prefer `core` and `common`.
- B1+ constraints prefer `core`, `common`, and `extended`.

## 11. Candidate Query Contract Summary

- Contract version: `S7D_v1`
- Required inputs: `pattern_id`, `slot_id`
- Optional inputs: `learner_id`, `theme_context`, `cefr_ceiling`, `limit`
- Gate order: `review_status`, `generator_allowed`, `slot_constraint`, `cefr_gate`, `pos_gate`, `morphology_gate`
- Ranking signals: `theme_match`, `frequency_band`, `learner_mastery_gap`, `recency`, `diversity`
- Default candidate limit: `50`
- Full pattern-vocabulary edge materialization: `false`

## 12. Validator Result

Command:

```text
python ulga/validators/validate_pattern_vocabulary_constraints.py
```

Result:

```text
Pattern Vocabulary Constraint validation: PASS
```

Validator coverage:

- Constraint JSON shape
- Candidate query contract shape
- Active constraints only for accepted generator-allowed patterns
- Pattern ID and pattern node ID consistency
- Slot constraint field presence
- `multi_type` allowed slot types
- Compatibility class and allowed POS enums
- CEFR gate mode and manual A1 max level
- Theme gate mode
- Frequency hint mode
- Candidate query limit cap
- No materialized pattern-vocabulary edge fields
- Summary count consistency

## 13. Pytest Result

Focused command:

```text
python -m pytest tests/ulga/test_pattern_vocabulary_constraints.py -q
```

Result:

```text
13 passed
```

Full ULGA command:

```text
python -m pytest tests/ulga/ -q
```

Result:

```text
115 passed
```

## 14. Known Deferred Items

- No pattern-to-vocabulary edge graph was generated.
- No 20M+ linkage dataset was generated.
- No runtime candidate selection engine was implemented.
- No learner-state ranking was implemented.
- No planner or recommendation runtime was implemented.
- No vocabulary, theme, chunk, grammar, or schema authority source was mutated.
- No morphology surface-form generation was implemented in this stage.

## 15. Risks / Warnings

- Slot semantics remain coarse for `sb`, `sth`, and generic `noun_phrase`.
- Theme gating for chunk-derived patterns is soft because chunk-derived patterns do not yet carry audited pattern theme refs.
- Gerund and verb-form constraints declare morphology requirements, but surface realization is deferred.
- Frequency bands use S7D contract labels (`core`, `common`, `extended`) and should be mapped explicitly to raw source frequency tiers in a future runtime.

## 16. Recommended Next Task

`ULGA-S7E_PatternThemeLinkage_DesignScan`

Recommended scope:

- Define how chunk-derived sentence patterns inherit or infer theme context without mutating theme authority.
- Decide when a pattern theme should be a hard gate versus a ranking signal.
- Keep vocabulary candidate selection query-based, not edge-dense.

## 17. Final Verdict

`PASS`

S7D implemented a pattern-owned vocabulary constraint layer with active constraints only for accepted generator-allowed patterns, a candidate query contract, validator coverage, and pytest coverage. No full pattern-vocabulary edge materialization was introduced.

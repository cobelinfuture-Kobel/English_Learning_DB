# ULGA-S5G Vocabulary Theme Refinement QA Audit

## 1. Files Created

- `ulga/audits/audit_ulga_vocabulary_theme_refinement.py`
- `ulga/reports/vocabulary_theme_refinement_qa_audit.json`
- `docs/ulga/ULGA_S5G_VOCABULARY_THEME_REFINEMENT_QA_AUDIT.md`

## 2. Files Modified

- None of the protected source, graph, edge, rule, or runtime files were modified.
- The audit is read-only against original and refined graph artifacts.

## 3. Existing Validation Results

- Refinement validator: `PASS`
- Validator summary: `ULGA vocabulary theme refinement validation: PASS`

## 4. Tests Executed

- `C:\Users\winnie\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/ulga/ -q`: `PASS`
- Pytest summary: `65 passed in 18.49s`

## 5. Basic Metrics

- Vocabulary node count: `15696`
- Theme node count: `25`
- Original theme edge count: `88423`
- Refined theme edge count: `19557`
- Removed theme edge count: `68866`
- Mapped vocabulary before / after: `9065` / `9065`
- Average edges per mapped before / after: `9.7543` / `2.1574`
- Max edges per vocabulary before / after: `20` / `3`

## 6. Coverage Preservation

- Mapped vocabulary count preserved: `True`
- Lost mapped vocabulary count: `0`
- Newly unmapped after refinement count: `0`
- Source-topic-ready nodes still mapped: `9065`
- Mapped ratio before / after: `57.75%` / `57.75%`

## 7. Overconnection Reduction

- Nodes >3 theme edges before / after: `7221` / `0`
- Nodes >5 theme edges before / after: `5849` / `0`
- Nodes >10 theme edges before / after: `2790` / `0`
- Average edge density reduction: `77.88%`
- Total edge reduction: `77.88%`

## 8. Membership Role Quality

- Primary edge count: `8841`
- Secondary edge count: `10492`
- Inferred low-confidence count: `224`
- Nodes with 0 primary theme: `224`
- Nodes with >1 primary theme: `0`
- Nodes with >2 secondary themes: `0`
- Primary coverage ratio: `97.53%`

## 9. Theme Hub Balance

- Theme Gini before / after: `0.1597` / `0.5504`
- Top and bottom refined themes are included in the JSON audit report.
- Themes collapsed too much: `14`
- Themes still overconnected: `0`

## 10. Mapping Source Quality

```json
{
  "mapping_source_breakdown_before": {
    "fallback_topic_normalization_rules": 448,
    "themes/theme_vocab_mapping.json": 87975
  },
  "mapping_source_breakdown_after": {
    "themes/theme_vocab_mapping.json": 19333,
    "fallback_topic_normalization_rules": 224
  },
  "fallback_retained_count": 224,
  "fallback_retained_ratio": 0.011453699442654805,
  "native_topic_retained_count": 0,
  "theme_vocab_mapping_retained_count": 19333,
  "inferred_rule_retained_count": 224,
  "retained_rank_distribution": {
    "1": 9065,
    "2": 5719,
    "3": 4773
  },
  "removed_edge_role_breakdown": {
    "primary": 24401,
    "secondary": 44241,
    "inferred": 224
  },
  "removed_edge_source_breakdown": {
    "themes/theme_vocab_mapping.json": 68642,
    "fallback_topic_normalization_rules": 224
  }
}
```

## 11. Polysemy / Sense-Specific Audit

- Sense-specific true count: `19557`
- Lemma-level assignment true count: `0`
- Polysemous lemmas retaining distinct theme sets: `679`
- Suspicious identical theme sets across many senses: `50`

## 12. CEFR / Theme Distribution

```json
{
  "refined_theme_edges_by_vocabulary_cefr": {
    "B1": 4677,
    "A1": 1447,
    "A2": 2842,
    "C2": 2669,
    "B2": 5981,
    "C1": 1941
  },
  "refined_theme_edges_by_theme_cefr": {
    "A1": 14551,
    "C1": 1382,
    "B1": 407,
    "A2": 2157,
    "A2_plus": 266,
    "B1_plus": 266,
    "A1_plus": 319,
    "B2": 126,
    "B2_plus": 83
  },
  "mapped_vocabulary_by_cefr": {
    "C2": 1345,
    "A1": 629,
    "B2": 2816,
    "C1": 921,
    "A2": 1242,
    "B1": 2112
  },
  "unmapped_vocabulary_by_cefr": {
    "C1": 1489,
    "B1": 825,
    "C2": 2462,
    "B2": 1348,
    "A1": 155,
    "A2": 352
  },
  "a1_a2_mapped_vocabulary_count_after_refinement": 1871,
  "advanced_level_theme_sparsity_warnings": [
    {
      "theme_id": "b2_professional_and_academic_situations",
      "level": "B2",
      "refined_edge_count": 0
    },
    {
      "theme_id": "b2_native_speed_communication",
      "level": "B2",
      "refined_edge_count": 0
    },
    {
      "theme_id": "b2_plus_academic_bridge",
      "level": "B2_plus",
      "refined_edge_count": 83
    },
    {
      "theme_id": "c1_advanced_work_and_socializing",
      "level": "C1",
      "refined_edge_count": 83
    },
    {
      "theme_id": "c1_implicit_meanings_and_complex_texts",
      "level": "C1",
      "refined_edge_count": 0
    }
  ]
}
```

## 13. Safety Audit

```json
{
  "all_edges_source_vocabulary_to_target_theme": true,
  "all_edge_type_belongs_to": true,
  "duplicate_refined_edge_tuple_count": 0,
  "self_loop_count": 0,
  "missing_source_target_count": 0,
  "no_morphology_edges": true,
  "no_chunk_edges": true,
  "no_vocabulary_dependency_edges": true,
  "no_grammar_edges": true,
  "original_full_layer_preserved": true,
  "original_edges_unchanged_by_audit": true,
  "refined_edges_unchanged_by_audit": true,
  "theme_mapping_rule_count": 120,
  "theme_catalog_count": 25,
  "theme_mapping_top_level_keys": [
    "A1",
    "A1_plus",
    "A2",
    "A2_plus",
    "B1",
    "B1_plus",
    "B2",
    "B2_plus",
    "C1"
  ],
  "theme_vocab_mapping_top_level_keys": [
    "themes"
  ],
  "previous_s5f_verdict": "WARNING_ACCEPTED",
  "refinement_summary_consistent": true
}
```

## 14. Risks / Warnings

- Some mapped nodes lack a retained primary theme, mostly fallback-only inferred nodes.
- Some broad themes collapsed below 10% retention after refinement.
- Some polysemous lemmas retain identical theme sets across many senses.

## 15. Authority Readiness Assessment

```json
{
  "Theme Spiral Authority": "READY",
  "Vocabulary Morphology Layer": "READY",
  "Vocabulary Chunk Linkage": "PARTIAL",
  "Sentence Pattern Authority": "PARTIAL",
  "Antigravity Planner": "PARTIAL",
  "Gate Engine": "PARTIAL"
}
```

## 16. Recommended Next Task

ULGA-S5H_VocabularyMorphologyLayer_DesignScan

## 17. Final Verdict

WARNING_ACCEPTED

# ULGA-S5F Vocabulary Theme Layer QA Audit

## 1. Files Created

- `ulga/audits/audit_ulga_vocabulary_theme_layer.py`
- `ulga/reports/vocabulary_theme_layer_qa_audit.json`
- `docs/ulga/ULGA_S5F_VOCABULARY_THEME_LAYER_QA_AUDIT.md`

## 2. Files Modified

- None of the protected source, graph, edge, rule, or runtime files were modified.

## 3. Existing Validation Results

- Validator: `PASS`
- Validator summary: `ULGA vocabulary theme layer validation: PASS`

## 4. Tests Executed

- `pytest tests/ulga/ -q`: `PASS`
- Pytest summary: `56 passed`

## 5. Basic Metrics

- Vocabulary node count: `15696`
- Theme node count: `25`
- Theme edge count: `88423`
- Mapped vocabulary count: `9065`
- Unmapped vocabulary count: `6631`
- Mapped ratio: `57.75%`
- Average edges per mapped vocabulary: `9.75`

## 6. Membership Breakdown

```json
{
  "primary_count": 33242,
  "secondary_count": 54733,
  "inferred_count": 448,
  "unknown_membership_type_count": 0,
  "average_primary_edges_per_mapped_node": 3.6670711527854385,
  "average_secondary_edges_per_mapped_node": 6.037837837837838,
  "average_inferred_edges_per_mapped_node": 0.04942084942084942
}
```

## 7. Weight / Confidence Audit

```json
{
  "weight_min": 0.35,
  "weight_max": 1.0,
  "weight_median": 0.65,
  "confidence_min": 0.5,
  "confidence_max": 0.9,
  "confidence_median": 0.75,
  "count_confidence_gt_1": 0,
  "count_weight_gt_1": 0,
  "count_weight_lte_0": 0,
  "confidence_method_breakdown": {
    "inferred_rule": 448,
    "source_topic_mapping": 87975
  }
}
```

## 8. Theme Hub Analysis

- Theme Gini coefficient: `0.1597`
- Top themes and bottom themes are included in the JSON report.

## 9. Vocabulary Overconnection Analysis

```json
{
  "max_themes_per_vocabulary_node": 20,
  "median_themes_per_mapped_vocabulary_node": 9,
  "count_gt_3": 7221,
  "count_gt_5": 5849,
  "count_gt_10": 2790
}
```

## 10. Polysemy / Sense-Specific Audit

```json
{
  "sense_specific_true_count": 88423,
  "lemma_level_assignment_true_count": 0,
  "polysemous_lemma_count": 3513,
  "polysemous_lemma_identical_theme_sets_count": 1509,
  "top_50_polysemous_lemmas_by_theme_diversity": [
    {
      "lemma": "on",
      "sense_count": 19,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "in",
      "sense_count": 15,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "for",
      "sense_count": 15,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "to",
      "sense_count": 13,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "right",
      "sense_count": 13,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "good",
      "sense_count": 12,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "off",
      "sense_count": 11,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "back",
      "sense_count": 9,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "can",
      "sense_count": 9,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "do",
      "sense_count": 8,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "down",
      "sense_count": 8,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "little",
      "sense_count": 8,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "at least",
      "sense_count": 8,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "OK",
      "sense_count": 7,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "will",
      "sense_count": 7,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "at",
      "sense_count": 7,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "as",
      "sense_count": 6,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "cool",
      "sense_count": 6,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "number",
      "sense_count": 6,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "out of",
      "sense_count": 6,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "ring",
      "sense_count": 5,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "straight",
      "sense_count": 5,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "badly",
      "sense_count": 4,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "great",
      "sense_count": 4,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "negative",
      "sense_count": 4,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "long",
      "sense_count": 4,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": false
    },
    {
      "lemma": "no",
      "sense_count": 4,
      "theme_diversity": 25,
      "identical_theme_sets_for_all_senses": fa
```

## 11. Source Topic Coverage

```json
{
  "source_topic_ready_count": 9065,
  "mapped_source_topic_ready_count": 9065,
  "unmapped_despite_source_topic_count": 0,
  "missing_topic_count": 6631,
  "mapped_despite_missing_source_topic_count": 0,
  "mapping_source_breakdown": {
    "fallback_topic_normalization_rules": 448,
    "themes/theme_vocab_mapping.json": 87975
  }
}
```

## 12. Rule Quality Audit

```json
{
  "total_rule_count": 120,
  "enabled_rule_count": 120,
  "rules_producing_0_edges": [],
  "rules_producing_gt_1000_edges": [
    {
      "rule_id": "VOCAB_THEME_RULE_0004",
      "source_topic": "communication",
      "target_theme_id": "a1_personal_information_and_greetings",
      "membership_type": "secondary",
      "mapping_source": "themes/theme_vocab_mapping.json",
      "edge_count": 1491
    },
    {
      "rule_id": "VOCAB_THEME_RULE_0011",
      "source_topic": "communication",
      "target_theme_id": "a1_school_and_classroom",
      "membership_type": "secondary",
      "mapping_source": "themes/theme_vocab_mapping.json",
      "edge_count": 1491
    },
    {
      "rule_id": "VOCAB_THEME_RULE_0019",
      "source_topic": "communication",
      "target_theme_id": "a1_shopping_and_basic_transactions",
      "membership_type": "secondary",
      "mapping_source": "themes/theme_vocab_mapping.json",
      "edge_count": 1491
    },
    {
      "rule_id": "VOCAB_THEME_RULE_0038",
      "source_topic": "communication",
      "target_theme_id": "a1_plus_spiral_expansion",
      "membership_type": "secondary",
      "mapping_source": "themes/theme_vocab_mapping.json",
      "edge_count": 1491
    },
    {
      "rule_id": "VOCAB_THEME_RULE_0045",
      "source_topic": "communication",
      "target_theme_id": "a2_daily_transactions_and_local_environment",
      "membership_type": "secondary",
      "mapping_source": "themes/theme_vocab_mapping.json",
      "edge_count": 1491
    },
    {
      "rule_id": "VOCAB_THEME_RULE_0050",
      "source_topic": "communication",
      "target_theme_id": "a2_travel_and_consumption",
      "membership_type": "secondary",
      "mapping_source": "themes/theme_vocab_mapping.json",
      "edge_count": 1491
    },
    {
      "rule_id": "VOCAB_THEME_RULE_0053",
      "source_topic": "communication",
      "target_theme_id": "a2_socializing_and_discussion",
      "membership_type": "primary",
      "mapping_source": "themes/theme_vocab_mapping.json",
      "edge_count": 1491
    },
    {
      "rule_id": "VOCAB_THEME_RULE_0057",
      "source_topic": "communication",
      "target_theme_id": "a2_plus_roleplay_and_skills",
      "membership_type": "primary",
      "mapping_source": "themes/theme_vocab_mapping.json",
      "edge_count": 1491
    },
    {
      "rule_id": "VOCAB_THEME_RULE_0064",
      "source_topic": "communication",
      "target_theme_id": "b1_travel_and_living_abroad",
      "membership_type": "secondary",
      "mapping_source": "themes/theme_vocab_mapping.json",
      "edge_count": 1491
    },
    {
      "rule_id": "VOCAB_THEME_RULE_0069",
      "source_topic": "communication",
      "target_theme_id": "b1_work_and_business_environment",
      "membership_type": "secondary",
      "mapping_source": "themes/theme_vocab_mapping.json",
      "edge_count": 1491
    },
    {
      "rule_id": "VOCAB_THEME_RULE_0074",
      "source_topic": "communication",
      "target_theme_id": "b1_personal_expression_and_socializing",
      "membership_type": "secondary",
      "mapping_source": "themes/theme_vocab_mapping.json",
      "edge_count": 1491
    },
    {
      "rule_id": "VOCAB_THEME_RULE_0076",
      "source_topic": "communication",
      "target_theme_id": "b1_plus_critical_discussion",
      "membership_type": "primary",
      "mapping_source": "themes/theme_vocab_mapping.json",
      "edge_count": 1491
    },
    {
      "rule_id": "VOCAB_THEME_RULE_0084",
      "source_topic": "communication",
      "target_theme_id": "b2_professional_and_academic_situations",
      "membership_type": "secondary",
      "mapping_source": "themes/theme_vocab_mapping.json",
      "edge_count": 1491
    },
    {
      "rule_id": "VOCAB_THEME_RULE_0089",
      "source_topic": "communication",
      "target_theme_id": "b2_in_depth_debates_and_meetings",
      "membership_type": "secondary",
      "mapping_source": "themes/theme_vocab_mapping.json",
      "edge_count": 1491
    },
    {
     
```

## 13. CEFR / Theme Distribution

```json
{
  "theme_edges_by_cefr_level": {
    "B1": 20686,
    "A1": 6962,
    "C2": 11731,
    "A2": 13314,
    "B2": 26942,
    "C1": 8788
  },
  "mapped_vocabulary_by_cefr_level": {
    "B2": 2816,
    "C1": 921,
    "A2": 1242,
    "C2": 1345,
    "B1": 2112,
    "A1": 629
  },
  "unmapped_vocabulary_by_cefr_level": {
    "A2": 352,
    "B2": 1348,
    "C1": 1489,
    "A1": 155,
    "C2": 2462,
    "B1": 825
  },
  "high_level_vocabulary_mapped_to_low_level_theme_count": 23987,
  "high_level_vocabulary_mapped_to_low_level_theme_examples": [
    {
      "edge_id": "edge:vocab_theme_VOCAB_THEME_RULE_0005_v_4_a1_personal_information_and_greetings",
      "vocabulary": {
        "id": "vocabulary:albeit:v_4",
        "lemma": "albeit",
        "cefr_level": "C2",
        "source_vocabulary_id": "v_4"
      },
      "theme": "a1_personal_information_and_greetings",
      "theme_level": "A1"
    },
    {
      "edge_id": "edge:vocab_theme_VOCAB_THEME_RULE_0009_v_4_a1_daily_life_and_routines",
      "vocabulary": {
        "id": "vocabulary:albeit:v_4",
        "lemma": "albeit",
        "cefr_level": "C2",
        "source_vocabulary_id": "v_4"
      },
      "theme": "a1_daily_life_and_routines",
      "theme_level": "A1"
    },
    {
      "edge_id": "edge:vocab_theme_VOCAB_THEME_RULE_0012_v_4_a1_school_and_classroom",
      "vocabulary": {
        "id": "vocabulary:albeit:v_4",
        "lemma": "albeit",
        "cefr_level": "C2",
        "source_vocabulary_id": "v_4"
      },
      "theme": "a1_school_and_classroom",
      "theme_level": "A1"
    },
    {
      "edge_id": "edge:vocab_theme_VOCAB_THEME_RULE_0016_v_4_a1_homes_and_neighborhoods",
      "vocabulary": {
        "id": "vocabulary:albeit:v_4",
        "lemma": "albeit",
        "cefr_level": "C2",
        "source_vocabulary_id": "v_4"
      },
      "theme": "a1_homes_and_neighborhoods",
      "theme_level": "A1"
    },
    {
      "edge_id": "edge:vocab_theme_VOCAB_THEME_RULE_0020_v_4_a1_shopping_and_basic_transactions",
      "vocabulary": {
        "id": "vocabulary:albeit:v_4",
        "lemma": "albeit",
        "cefr_level": "C2",
        "source_vocabulary_id": "v_4"
      },
      "theme": "a1_shopping_and_basic_transactions",
      "theme_level": "A1"
    },
    {
      "edge_id": "edge:vocab_theme_VOCAB_THEME_RULE_0023_v_4_a1_food_and_dining",
      "vocabulary": {
        "id": "vocabulary:albeit:v_4",
        "lemma": "albeit",
        "cefr_level": "C2",
        "source_vocabulary_id": "v_4"
      },
      "theme": "a1_food_and_dining",
      "theme_level": "A1"
    },
    {
      "edge_id": "edge:vocab_theme_VOCAB_THEME_RULE_0027_v_4_a1_interests_and_abilities",
      "vocabulary": {
        "id": "vocabulary:albeit:v_4",
        "lemma": "albeit",
        "cefr_level": "C2",
        "source_vocabulary_id": "v_4"
      },
      "theme": "a1_interests_and_abilities",
      "theme_level": "A1"
    },
    {
      "edge_id": "edge:vocab_theme_VOCAB_THEME_RULE_0030_v_4_a1_travel_and_weather",
      "vocabulary": {
        "id": "vocabulary:albeit:v_4",
        "lemma": "albeit",
        "cefr_level": "C2",
        "source_vocabulary_id": "v_4"
      },
      "theme": "a1_travel_and_weather",
      "theme_level": "A1"
    },
    {
      "edge_id": "edge:vocab_theme_VOCAB_THEME_RULE_0034_v_4_a1_health_and_medical",
      "vocabulary": {
        "id": "vocabulary:albeit:v_4",
        "lemma": "albeit",
        "cefr_level": "C2",
        "source_vocabulary_id": "v_4"
      },
      "theme": "a1_health_and_medical",
      "theme_level": "A1"
    },
    {
      "edge_id": "edge:vocab_theme_VOCAB_THEME_RULE_0039_v_4_a1_plus_spiral_expansion",
      "vocabulary": {
        "id": "vocabulary:albeit:v_4",
        "lemma": "albeit",
        "cefr_level": "C2",
        "source_vocabulary_id": "v_4"
      },
      "theme": "a1_plus_spiral_expansion",
      "theme_level": "A1_plus"
    },
    {
      "edge_id": "edge:vocab_theme_VOCAB_THEME_RULE_0055_v_4_a2_socializing_and_dis
```

## 14. Safety Audit

```json
{
  "no_chunk_edges": true,
  "no_morphology_edges": true,
  "no_vocabulary_dependency_edges": true,
  "no_grammar_edges": true,
  "morphology_layer_implemented": false,
  "chunk_layer_implemented": false,
  "forbidden_edge_type_count": 0
}
```

## 15. Risks / Warnings

- average_edges_per_mapped_vocabulary is greater than 5
- many vocabulary nodes have more than 10 theme edges
- theme hubs are broad and overconnected
- unmapped nodes remain due missing source topics

## 16. Authority Readiness Assessment

```json
{
  "Vocabulary Morphology Layer": "PARTIAL",
  "Vocabulary Chunk Linkage": "PARTIAL",
  "Theme Spiral Authority": "READY",
  "Sentence Pattern Authority": "PARTIAL",
  "Antigravity Planner": "PARTIAL",
  "Gate Engine": "PARTIAL"
}
```

## 17. Recommended Next Task

ULGA-S5E_VocabularyThemeLayer_Refinement_Fix

## 18. Final Verdict

WARNING_ACCEPTED

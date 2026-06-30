# ULGA-S7DI Pattern Vocabulary Constraint QA Audit

## 1. Executive Summary

The S7D Pattern Vocabulary Constraint layer contains **1344** active constraints over **1932** slot constraints from **1482** sentence patterns. Validator status is **PASS** and pytest status is **PASS**.

**Final Verdict**: **WARNING_ACCEPTED**

## 2. Files Created

- `ulga/audits/audit_pattern_vocabulary_constraints.py`
- `ulga/reports/pattern_vocabulary_constraint_qa_audit.json`
- `docs/ulga/ULGA_S7DI_PATTERN_VOCABULARY_CONSTRAINT_QA_AUDIT.md`

## 3. Files Modified

- `ulga/builders/build_pattern_vocabulary_constraints.py`
- `ulga/validators/validate_pattern_vocabulary_constraints.py`
- `tests/ulga/test_pattern_vocabulary_constraints.py`
- `ulga/audits/audit_pattern_vocabulary_constraints.py`
- `ulga/graph/pattern_vocabulary_candidate_query_contract.json`
- `ulga/reports/pattern_vocabulary_constraint_summary.json`
- `ulga/reports/pattern_vocabulary_constraint_qa_audit.json`
- `docs/ulga/ULGA_S7DI_PATTERN_VOCABULARY_CONSTRAINT_QA_AUDIT.md`

## 4. Files Inspected

- `ulga/graph/pattern_vocabulary_constraints.json`
- `ulga/graph/pattern_vocabulary_candidate_query_contract.json`
- `ulga/reports/pattern_vocabulary_constraint_summary.json`
- `ulga/graph/sentence_patterns.json`
- `ulga/graph/ulga_sentence_pattern_nodes.json`
- `vocabulary/json/vocabulary.json`
- `vocabulary/mapping/frequency_mapping.json`
- `themes/theme_vocab_mapping.json`
- `themes/theme_catalog.json`
- `ulga/validators/validate_pattern_vocabulary_constraints.py`
- `tests/ulga/test_pattern_vocabulary_constraints.py`
- `docs/ulga/ULGA_S7D_PATTERN_VOCABULARY_CONSTRAINT_IMPLEMENTATION_CLOSEOUT.md`

## 5. Basic Integrity Metrics

- Total patterns: `1482`
- Active constraints: `1344`
- Inactive / skipped patterns: `138`
- Total slot constraints: `1932`
- Accepted patterns: `1344`
- Needs review / inactive patterns: `138`
- Active constraint ratio: `90.69%`
- Inactive constraint ratio: `9.31%`

## 6. Slot Coverage Analysis

- Unique slot types in active constraints: `11`
- Empty slot count: `0`
- Unknown slot count: `0`
- Multi-type coverage count: `3`
- Multi-type coverage ratio: `0.16%`

### Top 20 Slot Labels

```json
[
  {
    "value": "sth",
    "count": 1077
  },
  {
    "value": "sb",
    "count": 469
  },
  {
    "value": "verb",
    "count": 206
  },
  {
    "value": "infinitive",
    "count": 101
  },
  {
    "value": "gerund",
    "count": 60
  },
  {
    "value": "noun_phrase",
    "count": 6
  },
  {
    "value": "verb_stem",
    "count": 5
  },
  {
    "value": "noun_phrase/gerund",
    "count": 2
  },
  {
    "value": "adjective/noun_phrase",
    "count": 1
  },
  {
    "value": "name",
    "count": 1
  },
  {
    "value": "noun_phrase_1",
    "count": 1
  },
  {
    "value": "noun_phrase_2",
    "count": 1
  },
  {
    "value": "time",
    "count": 1
  },
  {
    "value": "adjective",
    "count": 1
  }
]
```

### Slot Type Distribution

```json
{
  "multi_type": 3,
  "proper_noun": 1,
  "noun_phrase": 1552,
  "verb_stem": 5,
  "noun_phrase_1": 1,
  "noun_phrase_2": 1,
  "time": 1,
  "adjective": 1,
  "verb_gerund": 60,
  "verb_infinitive": 101,
  "verb": 206
}
```

## 7. Compatibility Class Analysis

- Empty compatibility_classes count: `0`
- Unknown compatibility_classes count: `0`
- Unique compatibility classes used: `7`

```json
{
  "common_noun_phrase": 1557,
  "descriptive_adjective": 2,
  "generic_object": 1557,
  "person_entity": 1,
  "activity_gerund": 62,
  "action_verb": 312,
  "time_expression": 1
}
```

## 8. Allowed POS Analysis

- Empty allowed_pos count: `0`
- Suspicious combinations count: `0`

```json
{
  "adjective": 2,
  "noun": 1559,
  "phrase": 1558,
  "pronoun": 1557,
  "phrasal verb": 374,
  "verb": 374,
  "adverb": 1
}
```

## 9. CEFR Gate Audit

- Null CEFR gate count: `0`
- Invalid CEFR gate count: `0`
- Manual A1 patterns with non-A1 gate: `0`
- Plus-one allowance enabled count: `0`

```json
{
  "A1": 32,
  "C2": 576,
  "C1": 293,
  "B2": 636,
  "B1": 307,
  "A2": 88
}
```

## 10. Theme Gate Audit

- Invalid theme mode count: `0`
- Manual A1 hard_filter compliance: `True`
- Chunk-derived soft_filter compliance: `True`

```json
{
  "hard_filter": 19,
  "soft_filter": 1913
}
```

## 11. Frequency Hint Audit

- Invalid frequency mode count: `0`
- Hard block count: `0`
- Low frequency allowed false count: `0`

```json
{
  "ranking_signal": 1932
}
```

## 12. Candidate Query Contract Audit

- Contract version: `S7D_v1`
- Gate order matches design: `True`
- Ranking signals count: `5`
- Output shape key count: `8`
- Contract-level limit_default present: `True`
- Contract-level limit_max present: `True`
- Contract-level limit_default valid: `True`
- Contract-level limit_max valid: `True`
- Contract-level limit_default <= limit_max: `True`
- Candidate limit > 200 count: `0`
- Slot limit > top-level limit_max count: `0`

```json
{
  "contract_version": "S7D_v1",
  "gate_order": [
    "review_status",
    "generator_allowed",
    "slot_constraint",
    "cefr_gate",
    "pos_gate",
    "morphology_gate"
  ],
  "gate_order_matches_expected": true,
  "ranking_signals": [
    "theme_match",
    "frequency_band",
    "learner_mastery_gap",
    "recency",
    "diversity"
  ],
  "ranking_signal_count": 5,
  "output_shape_keys": [
    "cefr_level",
    "frequency_band",
    "lemma",
    "pos",
    "reasons",
    "score",
    "theme_ids",
    "vocabulary_node_id"
  ],
  "output_shape_key_count": 8,
  "materialization_policy": {
    "full_pattern_vocabulary_edges": false,
    "candidate_pool_generated_at_query_time": true
  },
  "limit_default_present": true,
  "limit_default_value": 50,
  "limit_default_valid": true,
  "limit_max_present": true,
  "limit_max_value": 200,
  "limit_max_valid": true,
  "limit_default_le_limit_max": true,
  "candidate_limit_gt_200_count": 0,
  "slot_limit_gt_top_level_limit_max_count": 0,
  "slot_limit_gt_top_level_limit_max_examples": [],
  "malformed_candidate_query_count": 0,
  "malformed_candidate_query_examples": []
}
```

## 13. Risk Findings

- [WARNING] slot_type_coverage_gap: Active constraints do not yet exercise 14 design-scan slot types: activity, base_verb, gerund, location, noun, object, person, place, plural_noun, sb

## 14. S7E Readiness Assessment

```json
{
  "status": "WARNING_ACCEPTED",
  "criteria": {
    "active_constraints_present": true,
    "slot_coverage_valid": true,
    "cefr_gate_valid": true,
    "theme_mode_valid": true,
    "frequency_ranking_valid": true,
    "candidate_query_contract_valid": true,
    "validator_pass": true,
    "pytest_pass": true
  },
  "warnings": [
    "Active constraints do not yet exercise 14 design-scan slot types: activity, base_verb, gerund, location, noun, object, person, place, plural_noun, sb"
  ],
  "blocked_reasons": []
}
```

## 15. Validator Result

```text
Validating Pattern Vocabulary Constraint layer...
Pattern Vocabulary Constraint validation: PASS
```

## 16. Pytest Result

```text
........................................................................ [ 61%]
..............................................                           [100%]
118 passed in 21.43s
```

## 17. Known Warnings

- Coverage remains narrow for several design-scan slot types and compatibility classes; this is a corpus coverage issue, not a structural S7D break.
- Theme hard_filter coverage is limited to manual A1 patterns; chunk-derived patterns remain soft-filter only and depend on downstream theme linkage quality.

## 18. Recommended Next Task

ULGA-S7E_PatternThemeLinkage_DesignScan

## 19. Final Verdict

WARNING_ACCEPTED

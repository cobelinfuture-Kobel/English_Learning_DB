# ULGA-S4F Extended Grammar Dependency Authority QA Audit

## 1. Files Created

- `ulga/audits/audit_ulga_grammar_extended_dependencies.py`
- `ulga/reports/grammar_dependency_extended_qa_audit.json`
- `docs/ulga/ULGA_S4F_EXTENDED_GRAMMAR_DEPENDENCY_QA_AUDIT.md`

## 2. Files Modified

- None of the protected graph, rule, source, generator, or runtime files were modified.

## 3. Existing Validation Results

- Extended dependency validator: `PASS`
- Validator output: `ULGA extended grammar dependencies validation: PASS`

## 4. Tests Executed

- `pytest tests/ulga/ -q`: `PASS`

## 5. Basic Metrics

- Node count: `1222`
- Core edge count: `183`
- Extended edge count: `310`
- Total edge count: `493`
- Total edge per node ratio: `0.4034`
- Enabled core rule count: `170`
- Enabled extended rule count: `310`
- Skipped extended rule count: `0`

## 6. S4C To S4F Improvement Delta

- Edge count delta: `310`
- Edge per node ratio delta: `0.2537`
- Connected node count delta: `255`
- Isolated node count delta: `-255`
- Isolated ratio delta: `-0.2087`

## 7. Isolated Node Analysis

- Isolated nodes: `815` (`66.69%`)
- Connected nodes: `407` (`33.31%`)
- Zero in-degree: `830`
- Zero out-degree: `975`

## 8. Dependency Breakdown

```json
{
  "counts": {
    "hard_prerequisite": 84,
    "soft_prerequisite": 216,
    "spiral_review": 63,
    "contrast_pair": 30,
    "unlock_relation": 10,
    "bridge_relation": 90
  },
  "breakdown_by_layer": {
    "bridge": {
      "bridge_relation": 90
    },
    "core": {
      "hard_prerequisite": 84,
      "soft_prerequisite": 12,
      "spiral_review": 63,
      "contrast_pair": 14,
      "unlock_relation": 10
    },
    "extended_core": {
      "soft_prerequisite": 204,
      "contrast_pair": 16
    }
  }
}
```

## 9. Layer Breakdown

```json
{
  "core_edge_count": 183,
  "extended_core_edge_count": 220,
  "bridge_edge_count": 90,
  "advanced_layer_edge_count": 0,
  "advanced_layer_implemented": false
}
```

## 10. Progression Breakdown

```json
{
  "progression_band_breakdown": {
    "A1_CORE": 35,
    "A2_CORE": 92,
    "A2_EXPANDED": 3,
    "B1_CORE": 41,
    "A1_EXPANDED": 10,
    "B2_CORE": 2,
    "A1_EXTENDED_CORE": 90,
    "A2_EXTENDED_CORE": 100,
    "B1_EXTENDED_CORE": 30,
    "B2_BRIDGE": 90
  },
  "progression_stage_breakdown": {
    "A1_STAGE_02": 14,
    "A2_STAGE_01": 33,
    "A2_STAGE_02": 20,
    "A2_STAGE_03": 19,
    "A1_STAGE_03": 15,
    "B1_STAGE_02": 22,
    "A1_STAGE_04": 13,
    "B1_STAGE_01": 10,
    "A2_STAGE_04": 19,
    "A2_STAGE_05": 4,
    "B1_STAGE_03": 9,
    "A1_STAGE_01": 3,
    "B2_STAGE_01": 2,
    "A_EXT_001_A1": 1,
    "A_EXT_002_A1": 1,
    "A_EXT_003_A1": 1,
    "A_EXT_004_A1": 1,
    "A_EXT_005_A1": 1,
    "A_EXT_006_A1": 1,
    "A_EXT_007_A1": 1,
    "A_EXT_008_A1": 1,
    "A_EXT_009_A1": 1,
    "A_EXT_010_A1": 1,
    "A_EXT_011_A1": 1,
    "A_EXT_012_A1": 1,
    "A_EXT_013_A1": 1,
    "A_EXT_014_A1": 1,
    "A_EXT_015_A1": 1,
    "A_EXT_016_A2": 1,
    "A_EXT_017_A2": 1,
    "A_EXT_018_A2": 1,
    "A_EXT_019_A2": 1,
    "A_EXT_020_A2": 1,
    "A_EXT_021_A2": 1,
    "A_EXT_022_A2": 1,
    "A_EXT_023_A2": 1,
    "A_EXT_024_A2": 1,
    "A_EXT_025_A2": 1,
    "A_EXT_026_A1": 1,
    "A_EXT_027_A1": 1,
    "A_EXT_028_A2": 1,
    "A_EXT_029_A2": 1,
    "A_EXT_030_A2": 1,
    "A_EXT_031_A2": 1,
    "A_EXT_032_A2": 1,
    "A_EXT_033_A2": 1,
    "A_EXT_034_A2": 1,
    "A_EXT_035_B1": 1,
    "A_EXT_036_B1": 1,
    "A_EXT_037_B1": 1,
    "A_EXT_038_B1": 1,
    "A_EXT_039_B1": 1,
    "A_EXT_040_B1": 1,
    "A_EXT_041_B1": 1,
    "A_EXT_042_A1": 1,
    "A_EXT_043_A1": 1,
    "A_EXT_044_A1": 1,
    "A_EXT_045_A1": 1,
    "A_EXT_046_A1": 1,
    "A_EXT_047_A1": 1,
    "A_EXT_048_A1": 1,
    "A_EXT_049_A1": 1,
    "A_EXT_050_A1": 1,
    "A_EXT_051_A1": 1,
    "A_EXT_052_A1": 1,
    "A_EXT_053_A1": 1,
    "A_EXT_054_A2": 1,
    "A_EXT_055_A2": 1,
    "A_EXT_056_A2": 1,
    "A_EXT_057_A2": 1,
    "A_EXT_058_A2": 1,
    "A_EXT_059_A2": 1,
    "A_EXT_060_A2": 1,
    "A_EXT_061_A2": 1,
    "A_EXT_062_A2": 1,
    "A_EXT_063_A2": 1,
    "A_EXT_064_A2": 1,
    "A_EXT_065_A2": 1,
    "A_EXT_066_A2": 1,
    "A_EXT_067_A1": 1,
    "A_EXT_068_A1": 1,
    "A_EXT_069_A1": 1,
    "A_EXT_070_A1": 1,
    "A_EXT_071_A1": 1,
    "A_EXT_072_A1": 1,
    "A_EXT_073_A1": 1,
    "A_EXT_074_A1": 1,
    "A_EXT_075_A2": 1,
    "A_EXT_076_A2": 1,
    "A_EXT_077_A2": 1,
    "A_EXT_078_A2": 1,
    "A_EXT_079_A2": 1,
    "A_EXT_080_A2": 1,
    "A_EXT_081_A2": 1,
    "A_EXT_082_A2": 1,
    "A_EXT_083_A2": 1,
    "A_EXT_084_A2": 1,
    "A_EXT_085_A2": 1,
    "A_EXT_086_A2": 1,
    "A_EXT_087_A2": 1,
    "A_EXT_088_A2": 1,
    "A_EXT_089_A2": 1,
    "A_EXT_090_A2": 1,
    "A_EXT_091_A2": 1,
    "A_EXT_092_A1": 1,
    "A_EXT_093_A1": 1,
    "A_EXT_094_A1": 1,
    "A_EXT_095_A1": 1,
    "A_EXT_096_A1": 1,
    "A_EXT_097_A1": 1,
    "A_EXT_098_A1": 1,
    "A_EXT_099_A1": 1,
    "A_EXT_100_A1": 1,
    "A_EXT_101_A1": 1,
    "A_EXT_102_A1": 1,
    "A_EXT_103_A2": 1,
    "A_EXT_104_A2": 1,
    "A_EXT_105_A2": 1,
    "A_EXT_106_A2": 1,
    "A_EXT_107_A2": 1,
    "A_EXT_108_A2": 1,
    "A_EXT_109_A2": 1,
    "A_EXT_110_A2": 1,
    "A_EXT_111_A2": 1,
    "A_EXT_112_A2": 1,
    "A_EXT_113_A2": 1,
    "A_EXT_114_A2": 1,
    "A_EXT_115_A2": 1,
    "A_EXT_116_A2": 1,
    "A_EXT_117_A1": 1,
    "A_EXT_118_A1": 1,
    "A_EXT_119_A1": 1,
    "A_EXT_120_A1": 1,
    "A_EXT_121_A1": 1,
    "A_EXT_122_A1": 1,
    "A_EXT_123_A1": 1,
    "A_EXT_124_A1": 1,
    "A_EXT_125_A1": 1,
    "A_EXT_126_A1": 1,
    "A_EXT_127_A1": 1,
    "A_EXT_128_A1": 1,
    "A_EXT_129_A2": 1,
    "A_EXT_130_A2": 1,
    "A_EXT_131_A2": 1,
    "A_EXT_132_A2": 1,
    "A_EXT_133_A2": 1,
    "A_EXT_134_A2": 1,
    "A_EXT_135_A2": 1,
    "A_EXT_136_A2": 1,
    "A_EXT_137_A2": 1,
    "A_EXT_138_A2": 1,
    "A_EXT_139_A2": 1,
    "A_EXT_140_A2": 1,
    "A_EXT_141_A2": 1,
    "A_EXT_142_A2": 1,
    "A_EXT_143_A2": 1,
    "A_EXT_144_A2": 1,
    "A_EXT_145_A2": 1,
    "A_EXT_146_A2": 1,
    "A_EXT_147_A2": 1,
    "A_EXT_148_B1": 1,
    "A_EXT_149_B1": 1,
    "A_EXT_150_B1": 1,
    "A_EXT_151_B1": 1,
    "A_EXT_152_B1": 1,
    "A_EXT_153_B1": 1,
    "A_EXT_154_B1": 1,
    "A_EXT_155_B1": 1,
    "A_EXT_156_B1": 1,
    "A_EXT_157_A2": 1,
    "A_EXT_158_A2": 1,
    "A_EXT_159_A2": 1,
    "A_EXT_160_A2": 1,
    "A_EXT_161_A2": 1,
    "A_EXT_162_A2": 1,
    "A_EXT_163_A2": 1,
    "A_EXT_164_B1": 1,
    "A_EXT_165_B1": 1,
    "A_EXT_166_B1": 1,
    "A_EXT_167_B1": 1,
    "A_EXT_168_B1": 1,
    "A_EXT_169_B1": 1,
    "A_EXT_170_B1": 1,
    "A_EXT_171_A1": 1,
    "A_EXT_172_A1": 1,
    "A_EXT_173_A1": 1,
    "A_EXT_174_A1": 1,
    "A_EXT_175_A1": 1,
    "A_EXT_176_A1": 1,
    "A_EXT_177_A1": 1,
    "A_EXT_178_A2": 1,
    "A_EXT_179_A2": 1,
    "A_EXT_180_A2": 1,
    "A_EXT_181_A2": 1,
    "A_EXT_182_A2": 1,
    "A_EXT_183_A2": 1,
    "A_EXT_184_B1": 1,
    "A_EXT_185_B1": 1,
    "A_EXT_186_B1": 1,
    "A_EXT_187_B1": 1,
    "A_EXT_188_B1": 1,
    "A_EXT_189_B1": 1,
    "A_EXT_190_B1": 1,
    "A_EXT_191_A1": 1,
    "A_EXT_192_A1": 1,
    "A_EXT_193_A1": 1,
    "A_EXT_194_A1": 1,
    "A_EXT_195_A1": 1,
    "A_EXT_196_A1": 1,
    "A_EXT_197_A1": 1,
    "A_EXT_198_A1": 1,
    "A_EXT_199_A1": 1,
    "A_EXT_200_A1": 1,
    "A_EXT_201_A1": 1,
    "A_EXT_202_A1": 1,
    "A_EXT_203_A1": 1,
    "A_EXT_204_A1": 1,
    "A_EXT_205_A1": 1,
    "A_EXT_206_A1": 1,
    "A_EXT_207_A1": 1,
    "A_EXT_208_A1": 1,
    "A_EXT_209_A1": 1,
    "A_EXT_210_A1": 1,
    "A_EXT_211_A1": 1,
    "A_EXT_212_A1": 1,
    "A_EXT_213_A1": 1,
    "A_EXT_214_A2": 1,
    "A_EXT_215_A2": 1,
    "A_EXT_216_A2": 1,
    "A_EXT_217_A2": 1,
    "A_EXT_218_A2": 1,
    "A_EXT_219_A2": 1,
    "A_EXT_220_A2": 1,
    "B_BRIDGE_001_B2": 1,
    "B_BRIDGE_002_B2": 1,
    "B_BRIDGE_003_B2": 1,
    "B_BRIDGE_004_B2": 1,
    "B_BRIDGE_005_B2": 1,
    "B_BRIDGE_006_B2": 1,
    "B_BRIDGE_007_B2": 1,
    "B_BRIDGE_008_B2": 1,
    "B_BRIDGE_009_B2": 1,
    "B_BRIDGE_010_B2": 1,
    "B_BRIDGE_011_B2": 1,
    "B_BRIDGE_012_B2": 1,
    "B_BRIDGE_013_B2": 1,
    "B_BRIDGE_014_B2": 1,
    "B_BRIDGE_015_B2": 1,
    "B_BRIDGE_016_B2": 1,
    "B_BRIDGE_017_B2": 1,
    "B_BRIDGE_018_B2": 1,
    "B_BRIDGE_019_B2": 1,
    "B_BRIDGE_020_B2": 1,
    "B_BRIDGE_021_B2": 1,
    "B_BRIDGE_022_B2": 1,
    "B_BRIDGE_023_B2": 1,
    "B_BRIDGE_024_B2": 1,
    "B_BRIDGE_025_B2": 1,
    "B_BRIDGE_026_B2": 1,
    "B_BRIDGE_027_B2": 1,
    "B_BRIDGE_028_B2": 1,
    "B_BRIDGE_029_B2": 1,
    "B_BRIDGE_030_B2": 1,
    "B_BRIDGE_031_B2": 1,
    "B_BRIDGE_032_B2": 1,
    "B_BRIDGE_033_B2": 1,
    "B_BRIDGE_034_B2": 1,
    "B_BRIDGE_035_B2": 1,
    "B_BRIDGE_036_B2": 1,
    "B_BRIDGE_037_B2": 1,
    "B_BRIDGE_038_B2": 1,
    "B_BRIDGE_039_B2": 1,
    "B_BRIDGE_040_B2": 1,
    "B_BRIDGE_041_B2": 1,
    "B_BRIDGE_042_B2": 1,
    "B_BRIDGE_043_B2": 1,
    "B_BRIDGE_044_B2": 1,
    "B_BRIDGE_045_B2": 1,
    "B_BRIDGE_046_B2": 1,
    "B_BRIDGE_047_B2": 1,
    "B_BRIDGE_048_B2": 1,
    "B_BRIDGE_049_B2": 1,
    "B_BRIDGE_050_B2": 1,
    "B_BRIDGE_051_B2": 1,
    "B_BRIDGE_052_B2": 1,
    "B_BRIDGE_053_B2": 1,
    "B_BRIDGE_054_B2": 1,
    "B_BRIDGE_055_B2": 1,
    "B_BRIDGE_056_B2": 1,
    "B_BRIDGE_057_B2": 1,
    "B_BRIDGE_058_B2": 1,
    "B_BRIDGE_059_B2": 1,
    "B_BRIDGE_060_B2": 1,
    "B_BRIDGE_061_B2": 1,
    "B_BRIDGE_062_B2": 1,
    "B_BRIDGE_063_B2": 1,
    "B_BRIDGE_064_B2": 1,
    "B_BRIDGE_065_B2": 1,
    "B_BRIDGE_066_B2": 1,
    "B_BRIDGE_067_B2": 1,
    "B_BRIDGE_068_B2": 1,
    "B_BRIDGE_069_B2": 1,
    "B_BRIDGE_070_B2": 1,
    "B_BRIDGE_071_B2": 1,
    "B_BRIDGE_072_B2": 1,
    "B_BRIDGE_073_B2": 1,
    "B_BRIDGE_074_B2": 1,
    "B_BRIDGE_075_B2": 1,
    "B_BRIDGE_076_B2": 1,
    "B_BRIDGE_077_B2": 1,
    "B_BRIDGE_078_B2": 1,
    "B_BRIDGE_079_B2": 1,
    "B_BRIDGE_080_B2": 1,
    "B_BRIDGE_081_B2": 1,
    "B_BRIDGE_082_B2": 1,
    "B_BRIDGE_083_B2": 1,
    "B_BRIDGE_084_B2": 1,
    "B_BRIDGE_085_B2": 1,
    "B_BRIDGE_086_B2": 1,
    "B_BRIDGE_087_B2": 1,
    "B_BRIDGE_088_B2": 1,
    "B_BRIDGE_089_B2": 1,
    "B_BRIDGE_090_B2": 1
  },
  "progression_score_min": 5,
  "progression_score_max": 790,
  "progression_score_median": 464,
  "progression_inversion_cases": []
}
```

## 11. CEFR Coverage

```json
{
  "cefr_scope_breakdown": {
    "A1": 135,
    "A2": 195,
    "B1": 71,
    "B2": 92
  },
  "c1_c2_edge_count": 0,
  "plus_level_misuse_count": 0,
  "cefr_as_order_misuse_count": 0,
  "b2_bridge_edge_count": 92
}
```

## 12. Directionality Audit

- Self-loop count: `0`
- Duplicate edge tuple count: `0`
- Missing source/target count: `0`
- Suspicious backward prerequisites: `8`

## 13. DAG Audit

- Acyclic: `True`
- Longest chain length: `4`
- Root node count: `11`
- Leaf node count: `54`
- Disconnected hard DAG components: `7`

## 14. Rule Quality Audit

```json
{
  "rules_producing_0_edges": [],
  "rules_producing_gt_5_edges": [],
  "rules_using_only_cefr_level": [],
  "rules_with_confidence_gte_1": [],
  "weak_match_evidence_edges": [],
  "duplicate_rule_intent_examples": []
}
```

## 15. Authority Safety Audit

```json
{
  "cefr_not_used_as_prerequisite_order": true,
  "plus_levels_not_used_as_cefr": true,
  "all_edges_rule_based": true,
  "all_edges_cefr_is_not_order_true": true,
  "no_advanced_layer_true": true,
  "no_layer_c_forbidden_family_implemented": true,
  "no_vocabulary_chunk_theme_learner_state_nodes": true,
  "non_grammar_nodes": [],
  "layer_c_edge_ids": []
}
```

## 16. Risks / Warnings

- isolated_node_ratio remains high after S4E
- edge_per_node_ratio remains below 0.50
- family coverage remains uneven
- suspicious backward prerequisites exist but are inherited from accepted S4C CEFR quirks
- B2 bridge edges exist and are justified as transition hubs

## 17. Authority Readiness Assessment

```json
{
  "Vocabulary Authority Mounting": "READY",
  "Chunk Authority Mounting": "PARTIAL",
  "Theme Spiral Authority": "READY",
  "Sentence Pattern Authority": "PARTIAL",
  "Antigravity Planner": "PARTIAL",
  "Gate Engine": "PARTIAL"
}
```

## 18. Recommended Next Task

ULGA-S5A_VocabularyAuthority_DesignScan

## 19. Final Verdict

WARNING_ACCEPTED

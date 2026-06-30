# ULGA-S4C Core Grammar Dependency Layer QA Audit Report

## 1. Files Created
- `ulga/audits/audit_ulga_grammar_core_dependencies.py` (Read-only audit tool for core dependencies)
- `ulga/reports/grammar_dependency_core_qa_audit.json` (Structured JSON report containing all calculated audit metrics)
- `docs/ulga/ULGA_S4C_GRAMMAR_DEPENDENCY_CORE_LAYER_QA_AUDIT.md` (This QA Audit closeout report)

## 2. Files Modified
- None (This is a read-only QA audit task; no core database or configuration files were changed)

## 3. Existing Validation Results
The existing validator `ulga/validators/validate_ulga_grammar_core_dependencies.py` was executed and returned:
- **Result**: **PASS**
- **Output**:
  ```
  Validation: SUCCESS. Verified 183 edges and verified DAG status.
  ULGA core dependencies validation: PASS
  ```

## 4. Tests Executed
Pytest test suite `tests/ulga/` was run, passing all 30 tests successfully:
- **Result**: **PASS**
- **Output**:
  ```
  ..............................                                           [100%]
  30 passed in 0.48s
  ```

## 5. Basic Metrics
- **Node Count**: 1,222
- **Edge Count**: 183
- **Enabled Rule Count**: 170
- **Skipped Rule Count**: 0 (All rules successfully matched active source and target nodes)
- **Edge per Node Ratio**: 0.1498 (~0.15 edges per node)

## 6. Isolated Node Analysis
- **Isolated Node Count**: 1,070 nodes
- **Isolated Node Ratio**: 87.56%
- **Zero In-Degree Count**: 1,180 nodes (including isolated nodes)
- **Zero Out-Degree Count**: 1,112 nodes (including isolated nodes)
- **Connected Node Count**: 152 nodes
- **Connected Node Ratio**: 12.44%

> [!NOTE]
> The high isolated node ratio (87.56%) is expected and pedagogically correct at this stage. The Core Grammar Dependency Layer is designed to model high-confidence progression seeds and core grammar structures (A1/A2/B1) rather than attempting to fully cover all 1,222 grammar nodes. Full coverage is deferred to the Extended Dependency Layer.

## 7. Dependency Breakdown
- **Dependency Class Breakdown**:
  - `hard_prerequisite`: 84
  - `soft_prerequisite`: 12
  - `spiral_review`: 63
  - `contrast_pair`: 14
  - `unlock_relation`: 10
- **Edge Type Breakdown**:
  - `prerequisite`: 84
  - `supports`: 75
  - `unlocks`: 10
  - `reviews`: 0 (Currently deferred)
  - `contrasts_with`: 14

## 8. Progression Breakdown
- **Progression Band Breakdown**:
  - `A1_CORE`: 35 edges
  - `A1_EXPANDED`: 10 edges
  - `A2_CORE`: 92 edges
  - `A2_EXPANDED`: 3 edges
  - `B1_CORE`: 41 edges
  - `B2_CORE`: 2 edges
- **Progression Score Stats**:
  - **Min Score**: 5
  - **Max Score**: 312
  - **Median Score**: 118

## 9. CEFR Coverage
- **Edge Level Distribution (involved nodes)**:
  - `A1`: 45 edges
  - `A2`: 95 edges
  - `B1`: 41 edges
  - `B2`: 2 edges
  - `C1/C2`: 0 edges
- **CEFR Plus-Level Misuse**: **PASS** (Zero occurrences of plus CEFR levels like A1+ / A2+ / B1+ used as raw `cefr_level` or inside matches).

## 10. Directionality Heuristic Audit
- **Self-Loops Detected**: 0
- **Duplicate Edges Detected**: 0
- **Suspicious Backward Prerequisites**: 8 edges detected
  - `edge:grammar_dep_RULE_078_000453_000435` (`going to` A2 -> `will` A1)
  - `edge:grammar_dep_RULE_079_000454_000437` (`going to` negative B1 -> `will` negative A2)
  - `edge:grammar_dep_RULE_097_000975_001022` (present simple questions A2 -> wh-questions A1)
  - `edge:grammar_dep_RULE_097_000975_001026` (present simple questions A2 -> wh-questions A1)
  - `edge:grammar_dep_RULE_097_000981_001022` (indirect questions A2 -> wh-questions A1)
  - `edge:grammar_dep_RULE_097_000981_001026` (indirect questions A2 -> wh-questions A1)
  - `edge:grammar_dep_RULE_100_000975_001132` (present simple questions A2 -> yes/no questions A1)
  - `edge:grammar_dep_RULE_100_000981_001132` (indirect questions A2 -> yes/no questions A1)

> [!IMPORTANT]
> These backward prerequisites are expected due to EGP classification quirks. For example, EGP classifies simple affirmative `will` as A1 but `be going to` as A2, and wh-questions/yes-no questions as A1 but basic present simple questions as A2. When mapping logical progression (e.g. learning question structures in general), these level reversals are flagged but accepted as they reflect EGP corpus levels.

## 11. DAG Audit
- **Acyclic Check**: **PASS** (prerequisite / unlocks subgraph is strictly acyclic)
- **Longest Hard Chain**: 4 links
- **DAG Connected Root Nodes**: 42 nodes
- **DAG Connected Leaf Nodes**: 48 nodes

## 12. Rule Quality Audit
- **Rules producing 0 edges**: 19 rules (Filtered by the builder script due to duplicates generated after level-fixing in S4B, e.g. `RULE_058` merging with `RULE_057`)
- **Rules producing >5 edges**: 0 rules (All rules produce a focused, high-precision set of edges)
- **Rules only matching cefr_level**: 0 rules (All rules require at least one semantic match criterion)
- **Rules with confidence >= 1.0**: 0 rules (Confidence levels strictly set between 0.60 and 0.70)

## 13. Authority Safety Audit
- **CEFR not used as prerequisite order**: Verified.
- **A1+/A2+/B1+ not used as cefr_level**: Verified.
- **All edges derived as rule_based**: Verified.
- **All edges contain cefr_is_not_order = true**: Verified.

## 14. Risks / Warnings
- **High Isolated Node Ratio**: 87.56% of grammar nodes remain isolated. This is a warning condition but acceptable for the Core Layer.
- **Minor CEFR Progression Inversions**: 8 edges are backwards in terms of pure CEFR difficulty (e.g., A2 prerequisite for A1), caused by EGP level classification choices.
- **B2 Edge Leakage**: 2 edges connect to B2 possessives, which is acceptable since B2 is adjacent to B1 and the rule represents possessive pronoun continuity.

## 15. Recommended Next Task
- **Recommended Next Task**: `ULGA-S4D_ExtendedGrammarDependencyAuthority_DesignScan` (Design the strategy to expand dependency coverage to the remaining isolated nodes).

## 16. Final Verdict
**Final Verdict**: **WARNING_ACCEPTED** (All core validation checks pass, DAG checks pass, and warnings about isolated nodes and minor CEFR inversions are fully justified and expected).

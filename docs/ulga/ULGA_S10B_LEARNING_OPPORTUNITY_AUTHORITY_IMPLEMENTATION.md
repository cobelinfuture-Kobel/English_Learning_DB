# ULGA-S10B Learning Opportunity Authority Implementation

## 1. Scope

Implemented the ULGA-S10B Learning Opportunity Authority as a derived, read-only authority layer. It emits Learning Opportunity records that combine focus pattern, optional vocabulary candidates, grammar references, chunk references, theme references, dependency metadata, ranking feature placeholders, and policy flags.

## 2. Files Created

- `ulga/builders/build_learning_opportunities.py`
- `ulga/validators/validate_learning_opportunities.py`
- `ulga/graph/learning_opportunities.json`
- `ulga/reports/learning_opportunity_summary.json`
- `tests/ulga/test_learning_opportunities.py`
- `docs/ulga/ULGA_S10B_LEARNING_OPPORTUNITY_AUTHORITY_IMPLEMENTATION.md`

## 3. Files Modified

None. This implementation only creates the allowed S10B files and does not rewrite upstream graph, schema, validator, report, or test files.

## 4. Inputs Read

- `ulga/graph/sentence_patterns.json`
- `ulga/graph/pattern_vocabulary_constraints.json`
- `ulga/graph/pattern_vocabulary_candidate_query_contract.json`
- `ulga/graph/dependency_graph.json`
- `ulga/graph/theme_spiral_graph.json`
- `ulga/graph/theme_nodes.json`
- `ulga/graph/vocabulary_nodes.json`
- `ulga/schema/learning_signal_policy.json`
- `ulga/learner_state/learner_state.json`

## 5. Builder Behavior

The builder reads accepted, generator-ready sentence patterns and creates one Learning Opportunity per active pattern. Pattern vocabulary constraints are used to select a small deterministic set of compatible vocabulary focus nodes from vocabulary authority data without materializing full pattern-vocabulary edges. Pattern theme refs are preferred; slot theme gates are used as fallback; missing themes default to `General` and are reported as warnings. Dependency graph `REQUIRES` edges are represented as dependency metadata only and do not perform learner-specific blocking.

## 6. Validator Rules

The validator checks opportunity ID uniqueness, `candidate_type`, source pattern existence, level presence, focus node shape, at least one pattern or vocabulary focus, non-empty theme refs, dependency status enum, complete ranking feature keys, complete policy flag keys, and source authority value. Warnings are reported for non-breaking conditions such as `General` theme fallback or empty vocabulary focus.

## 7. Output Summary

The generated summary is written to `ulga/reports/learning_opportunity_summary.json` and includes total count, level distribution, theme distribution, dependency status counts, policy flag counts, missing optional inputs, and warnings.

Current generated counts:

- Total opportunities: 1344
- By level: A1 27, A2 57, B1 203, B2 412, C1 211, C2 434
- Dependency status: ready 1337, unknown 7
- Missing optional inputs: none
- Summary status: PASS_WITH_WARNINGS

## 8. Tests Executed

Executed commands:

```powershell
python ulga\builders\build_learning_opportunities.py
python ulga\validators\validate_learning_opportunities.py
python -m pytest tests\ulga\test_learning_opportunities.py -q
python -m pytest tests\ulga\ -q
```

Results:

- Builder: PASS_WITH_WARNINGS, 1344 opportunities, 1328 builder warnings
- Validator: PASS, 1327 non-failing validator warnings
- New S10B tests: 7 passed
- Existing `tests\ulga\` suite: 259 passed, 5 failed in `tests\ulga\test_learner_state_builder_qa_audit.py`

## 9. Known Warnings

1327 opportunities use the `General` theme fallback because many existing chunk-derived sentence patterns do not carry theme refs. Dependency readiness is metadata-only in S10B and does not use learner-specific mastery state for blocking. The full existing ULGA test suite currently has unrelated S9F learner-state QA audit failures: the audit reports `BLOCKER` instead of the expected `PASS_WITH_WARNINGS`.

## 10. Final Verdict

S10B_STATUS: PASS_WITH_WARNINGS

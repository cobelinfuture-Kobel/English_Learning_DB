# ULGA-S8C Dependency Edge Builder Closeout

## Files Created

- `ulga/builders/build_dependency_edges.py`
- `ulga/validators/validate_dependency_graph.py`
- `ulga/audits/audit_dependency_graph.py`
- `tests/ulga/test_dependency_graph.py`
- `ulga/graph/dependency_graph.json`
- `ulga/reports/dependency_graph_summary.json`
- `ulga/reports/dependency_graph_qa_audit.json`
- `docs/ulga/ULGA_S8C_DEPENDENCY_EDGE_BUILDER_CLOSEOUT.md`

## Files Modified

- None.

No Learning Signal contract/policy file, Theme Spiral artifact, prior design scan, existing graph/source dataset, Learner State artifact, or Learning Signal graph was modified.

## Dependency Statistics

| Metric | Count |
|---|---:|
| Source grammar dependency edges inspected | 493 |
| Dependency edges emitted | 84 |
| Skipped source edges | 409 |
| `REQUIRES` edges | 84 |
| `hard_prerequisite` edges | 84 |
| `soft_prerequisite` edges | 0 |
| `recommended_order` edges | 0 |
| `review_link` edges | 0 |
| Cross-authority edges | 0 |
| Theme dependency edges | 0 |

Only GrammarNode -> GrammarNode `REQUIRES` edges were generated.

## Gate Statistics

| Metric | Count |
|---|---:|
| Gate eligible edges | 84 |
| Accepted edges | 84 |
| Derived confidence edges | 84 |
| Authoritative confidence edges | 0 |
| Review required edges | 0 |
| Circular dependencies | 0 |
| Orphan edges | 0 |

Gate eligibility rule applied:

```text
relation = REQUIRES
dependency_class = hard_prerequisite
review_status = accepted
confidence.method = derived
```

## Validator Result

Command:

```text
python ulga/validators/validate_dependency_graph.py
```

Result:

```text
Validating ULGA Dependency Graph...
ULGA Dependency Graph validation: PASS
```

## Test Result

Command:

```text
python -m pytest tests/ulga/test_dependency_graph.py -q
```

Result:

```text
12 passed in 0.11s
```

The S8C audit also ran the same focused test file and reported `PASS`.

## QA Audit Result

Audit file:

- `ulga/reports/dependency_graph_qa_audit.json`

Result:

```text
final_verdict = PASS
blocked_findings = []
warning_findings = []
```

QA audit highlights:

- Total edges: `84`
- Gate eligible edges: `84`
- Circular dependency count: `0`
- Orphan node count: `0`
- Non-REQUIRES edges: `0`
- Soft gate edges: `0`
- Confidence gate misuse edges: `0`
- Theme misuse edges: `0`
- Cross-authority edges: `0`

## Learning Signal Compliance

S8C reads `ulga/schema/learning_signal_policy.json` and follows S8F/S8G gate policy.

Compliance decisions:

- `REQUIRES` is the only emitted relation.
- `GATE_SIGNAL` compatibility is represented only through accepted hard grammar prerequisites.
- `SPIRAL_TO` was not generated.
- `BELONGS_TO` was not generated.
- `USES` was not promoted.
- `supports` was not promoted.
- `reviews` was not promoted.
- Theme relation gates were not generated.
- CEFR-only dependencies were not generated.
- `learning_signal_graph.json` was not created.

## Known Limitations

- This builder intentionally emits only hard grammar prerequisite `REQUIRES` edges.
- It does not emit `EXPANDS`, `REINFORCES`, or `PRECEDES`.
- It does not emit Theme Spiral edges.
- It does not emit a Learning Signal graph.
- It does not create Vocabulary -> Grammar, Grammar -> Vocabulary, Theme -> Grammar, Theme -> Theme, Pattern -> Pattern, or Chunk -> Pattern dependencies.
- Confidence is normalized to `derived` because the source grammar edges are rule-based and S8F gate policy only allows `authoritative` or `derived` for gate eligibility.
- Existing non-hard grammar edges remain available in their original graph files but are intentionally skipped by S8C.

## Recommended Next Task

`ULGA-S8D_DependencyAuthority_QA_Audit`

Recommended audit focus:

- Inspect all `84` gate-eligible `REQUIRES` edges.
- Verify no CEFR-only dependency was introduced.
- Verify no cross-authority edge slipped into the dependency graph.
- Verify gate behavior remains aligned with `learning_signal_policy.json`.
- Review whether any edge should be downgraded before planner or learner-state integration.

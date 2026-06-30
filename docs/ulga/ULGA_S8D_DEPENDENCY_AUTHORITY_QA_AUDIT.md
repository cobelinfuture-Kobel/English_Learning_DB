# ULGA-S8D Dependency Authority QA Audit

## Executive Summary

Final Verdict: **PASS_WITH_WARNINGS**.

S8C DependencyEdgeBuilder output is structurally valid and Learning Signal compliant:

- `dependency_graph.json` exists and parses.
- `84` dependency edges were emitted.
- All emitted edges are `REQUIRES`.
- All emitted edges are `hard_prerequisite`.
- All emitted edges are `gate_eligible=true`.
- All source and target nodes resolve to mounted GrammarNodes.
- No Vocabulary, Chunk, Theme, Pattern, or Skill nodes appear in the dependency graph.
- No Theme Spiral, `BELONGS_TO`, `USES`, `supports`, `reviews`, or CEFR-only dependency edges were generated.
- Gate-eligible graph is acyclic.
- Existing validator, focused tests, audit script, and full `tests/ulga/` suite pass.

Warning:

- `8` edges have target CEFR lower than source CEFR. These are not automatic failures because evidence includes `hard_prerequisite` and `cefr_is_not_order`, and no large backward jump greater than one broad CEFR band was found. They should be manually reviewed in S8D/S9A readiness planning before planner or learner-state gate use.

## Files Audited

- `ulga/graph/dependency_graph.json`
- `ulga/reports/dependency_graph_summary.json`
- `ulga/reports/dependency_graph_qa_audit.json`
- `ulga/builders/build_dependency_edges.py`
- `ulga/validators/validate_dependency_graph.py`
- `ulga/audits/audit_dependency_graph.py`
- `tests/ulga/test_dependency_graph.py`
- `ulga/schema/learning_signal_policy.json`
- `ulga/schema/learning_signal_contract.schema.json`
- `docs/ulga/ULGA_S8C_DEPENDENCY_EDGE_BUILDER_CLOSEOUT.md`
- `docs/ulga/ULGA_S8A_DEPENDENCY_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S8F_LEARNING_SIGNAL_CONTRACT_CLOSEOUT.md`
- `docs/ulga/ULGA_S8G_LEARNING_SIGNAL_QA_AUDIT.md`

## Commands Executed

```text
python ulga/validators/validate_dependency_graph.py
```

Result:

```text
Validating ULGA Dependency Graph...
ULGA Dependency Graph validation: PASS
```

```text
python -m pytest tests/ulga/test_dependency_graph.py -q
```

Result:

```text
12 passed in 0.12s
```

```text
python ulga/audits/audit_dependency_graph.py
```

Result:

```text
ULGA Dependency Graph QA Audit: PASS
Total edges: 84
Gate eligible edges: 84
Validator: PASS
Pytest: PASS
```

```text
python -m pytest tests/ulga/ -q
```

Result:

```text
130 passed in 21.12s
```

## Artifact Integrity QA

| Check | Result | Notes |
|---|---|---|
| `dependency_graph.json` exists | PASS | File present and JSON parse passed. |
| `dependency_graph_summary.json` exists | PASS | File present and JSON parse passed. |
| `dependency_graph_qa_audit.json` exists | PASS | File present and JSON parse passed. |
| Builder exists | PASS | `ulga/builders/build_dependency_edges.py` present. |
| Validator exists | PASS | `ulga/validators/validate_dependency_graph.py` present. |
| Audit script exists | PASS | `ulga/audits/audit_dependency_graph.py` present. |
| Focused test exists | PASS | `tests/ulga/test_dependency_graph.py` present. |
| Summary matches graph edge count | PASS | Summary count `84` matches graph count `84`. |

Artifact Integrity QA result: **PASS**.

## Schema / Field QA

Required edge fields:

- `edge_id`
- `source_node_id`
- `target_node_id`
- `relation`
- `dependency_class`
- `confidence`
- `source_authority`
- `review_status`
- `gate_eligible`
- `evidence`
- `notes`

| Check | Result | Notes |
|---|---|---|
| Missing required fields | PASS | `0` edges missing required fields. |
| Relation | PASS | All `84` edges use `REQUIRES`. |
| Dependency class | PASS | All `84` edges use `hard_prerequisite`. |
| Confidence method | PASS | All `84` edges use `derived`. |
| Review status | PASS | All `84` edges use `accepted`. |
| Gate eligibility | PASS | All `84` edges have `gate_eligible=true`. |

Schema / Field QA result: **PASS**.

## Node Resolution QA

| Check | Result | Notes |
|---|---|---|
| Source nodes resolve | PASS | All source nodes exist in `grammar_nodes.json`. |
| Target nodes resolve | PASS | All target nodes exist in `grammar_nodes.json`. |
| Source node type | PASS | All source IDs use `grammar:` prefix. |
| Target node type | PASS | All target IDs use `grammar:` prefix. |
| VocabularyNode included | PASS | None found. |
| ChunkNode included | PASS | None found. |
| ThemeNode included | PASS | None found. |
| PatternNode included | PASS | None found. |
| SkillNode included | PASS | None found. |
| Dangling source/target | PASS | `0` dangling endpoints. |

Node Resolution QA result: **PASS**.

## Gate Safety QA

| Check | Result | Notes |
|---|---|---|
| Gate formula enforced | PASS | All gates are `REQUIRES + hard_prerequisite + accepted + derived`. |
| Soft prerequisite gate | PASS | `0` found. |
| Recommended order gate | PASS | `0` found. |
| Review link gate | PASS | `0` found. |
| Heuristic gate | PASS | `0` found. |
| Manual-review-required gate | PASS | `0` found. |
| Non-REQUIRES gate | PASS | `0` found. |

Gate Safety QA result: **PASS**.

## Learning Signal Compliance QA

S8F/S8G policy says only `REQUIRES` and accepted hard `prerequisite` can produce gate behavior. The dependency graph complies.

| Check | Result | Notes |
|---|---|---|
| Uses only gate-allowed relation | PASS | All graph relations are `REQUIRES`. |
| Contains `SPIRAL_TO` | PASS | `0` found. |
| Contains `BELONGS_TO` | PASS | `0` found. |
| Contains `USES` | PASS | `0` found. |
| Contains `supports` | PASS | `0` found. |
| Contains `reviews` | PASS | `0` found. |
| Contains Theme relation | PASS | `0` theme source/target edges found. |
| CEFR-only evidence | PASS | Evidence includes hard prerequisite source and `cefr_is_not_order`; no CEFR-only edge found. |
| `learning_signal_graph.json` created | PASS | Not present. |

Learning Signal Compliance QA result: **PASS**.

## Source Traceability QA

| Check | Result | Notes |
|---|---|---|
| Source grammar dependency edge exists | PASS | All `84` `source_edge_id` values resolve in `grammar_dependency_all_edges.json`. |
| Source edge is physical `prerequisite` | PASS | All source edges are `edge_type=prerequisite`. |
| Source edge is hard prerequisite | PASS | All source edges have `metadata.dependency_class=hard_prerequisite`. |
| Evidence includes source file / source edge | PASS | Evidence includes `source_edge` object. |
| Evidence includes dependency class | PASS | Evidence includes `original_dependency_class=hard_prerequisite`. |
| Evidence includes CEFR-not-order marker | PASS | Evidence preserves `cefr_is_not_order`. |
| Orphan source edge | PASS | `0` found. |

Source Traceability QA result: **PASS**.

## CEFR Misuse QA

| Check | Result | Notes |
|---|---|---|
| CEFR-only dependency | PASS | `0` found. |
| Evidence includes hard prerequisite | PASS | All edges include hard-prerequisite evidence. |
| Evidence includes `cefr_is_not_order` | PASS | All edges preserve CEFR-not-order evidence. |
| Target CEFR lower than source CEFR | WARNING | `8` edges found. |
| Large backward CEFR jump | PASS | `0` cases exceed one broad CEFR band. |
| Same-level edges | INFO | `38` edges. |
| Target CEFR same or higher than source CEFR | INFO | `76` edges. |

Backward CEFR examples:

| Edge | Source CEFR | Target CEFR |
|---|---|---|
| `dependency_edge:grammar_dep_RULE_078_000453_000435` | A2 | A1 |
| `dependency_edge:grammar_dep_RULE_079_000454_000437` | B1 | A2 |
| `dependency_edge:grammar_dep_RULE_097_000975_001022` | A2 | A1 |
| `dependency_edge:grammar_dep_RULE_097_000975_001026` | A2 | A1 |
| `dependency_edge:grammar_dep_RULE_097_000981_001022` | A2 | A1 |
| `dependency_edge:grammar_dep_RULE_097_000981_001026` | A2 | A1 |
| `dependency_edge:grammar_dep_RULE_100_000975_001132` | A2 | A1 |
| `dependency_edge:grammar_dep_RULE_100_000981_001132` | A2 | A1 |

CEFR Misuse QA result: **PASS_WITH_WARNINGS**.

These cases should be reviewed before learner-state readiness gates are used. They do not currently fail S8D because S8A explicitly states CEFR is not dependency order, and every edge has rule-based hard-prerequisite evidence.

## Cycle / DAG QA

| Check | Result | Notes |
|---|---|---|
| Gate-eligible `REQUIRES` graph acyclic | PASS | Validator and audit report `0` cycles. |
| Self-dependency count | PASS | `0`. |
| Duplicate edge IDs | PASS | `0`. |
| Duplicate dependency tuples | PASS | `0`. |

Cycle / DAG QA result: **PASS**.

## Over-Gating Risk Review

Risk level: **Medium, controlled**.

Why controlled:

- Only `84` hard grammar prerequisite edges were emitted from `493` source grammar dependency edges.
- No `supports`, `reviews`, `contrast`, soft prerequisite, theme, vocabulary, chunk, or pattern relation was promoted.
- All gates are traceable to accepted hard grammar prerequisite source edges.
- Full test suite passes.

Residual concerns:

- All `84` emitted edges are gate eligible, so a future planner or learner-state engine could be conservative if it treats grammar readiness too strictly.
- `8` backward CEFR cases require manual review before runtime learner gating.
- Confidence is `derived`, not `authoritative`, because source grammar edges are rule-based. This is allowed by S8F but should remain visible to planner/learner-state consumers.

Recommended downgrade candidates:

- Do not auto-downgrade in S8D due to read-only scope.
- Queue the `8` backward CEFR cases for manual review in S8D follow-up or S9A readiness design.

## Builder Readiness Assessment

### Dependency Authority v1

Status: **READY WITH WARNING**.

Ready:

- Graph artifact exists.
- Validator passes.
- QA audit passes.
- Focused and full tests pass.
- Graph is acyclic.
- Graph is Learning Signal compliant.

Warning:

- Backward CEFR cases should be reviewed before live learner gating.

### ThemeSpiralEdgeBuilder

Status: **READY TO PROCEED SEPARATELY**.

S8C does not generate Theme Spiral edges and does not contaminate dependency graph with theme relations. ThemeSpiralEdgeBuilder can proceed if it keeps `SPIRAL_TO` non-gating per S8B/S8F/S8G.

### S9A LearnerStateAuthority Design Scan

Status: **READY FOR DESIGN SCAN**.

S9A can consume:

- `REQUIRES` as readiness dependency,
- `gate_eligible` as gate candidate,
- `confidence.method=derived` as reduced certainty,
- CEFR warning list as manual review input.

S9A must not treat gate eligibility as learner failure; it must evaluate learner mastery evidence separately.

### Schema / Validator Evolution

Status: **PARTIAL**.

Current validator is adequate for S8C. Future validator should add:

- exact schema contract for `dependency_graph.json`,
- explicit CEFR anomaly severity policy,
- manual review queue output for backward CEFR gates,
- integration checks against future Learner State thresholds.

## Risk Register

| Risk | Severity | Status | Notes |
|---|---|---|---|
| Cross-authority edge contamination | High | Controlled | No non-grammar edges emitted. |
| Theme relation becomes dependency | High | Controlled | No theme edges emitted. |
| Soft/review/support edge becomes gate | High | Controlled | `0` cases. |
| CEFR-only dependency | High | Controlled | Evidence includes hard prerequisite and `cefr_is_not_order`. |
| Backward CEFR gate anomaly | Medium | Open warning | `8` cases should be manually reviewed. |
| Over-gating by grammar prerequisites | Medium | Controlled warning | Only 84 hard prerequisites emitted, but all are gate eligible. |
| Planner misuse of gates | Medium | Deferred | Future planner must apply S8F policy and learner-state thresholds. |
| Learner State premature readiness blocking | Medium | Deferred | S9A must define mastery evidence and thresholds. |

## Final Verdict

**PASS_WITH_WARNINGS**

The S8C dependency graph is valid, acyclic, traceable, and compliant with Learning Signal policy. No blocking issue was found. The only material warning is the presence of `8` backward CEFR cases, which should be reviewed before runtime learner-state gating.

## Recommended Next Task

`ULGA-S8H_ThemeSpiralEdgeBuilder`

Rationale:

- Dependency Authority v1 is stable enough for now.
- Theme Spiral remains separate and should be built next as non-gating progression/coverage/review edges.
- S9A LearnerStateAuthority should follow after Theme Spiral and after manual review handling for backward CEFR dependency gates is specified.

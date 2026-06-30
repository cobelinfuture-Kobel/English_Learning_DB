# ULGA-S8H Theme Spiral Edge Builder Closeout

## Files Created

- `ulga/builders/build_theme_spiral_edges.py`
- `ulga/validators/validate_theme_spiral_graph.py`
- `ulga/audits/audit_theme_spiral_graph.py`
- `tests/ulga/test_theme_spiral_graph.py`
- `ulga/graph/theme_spiral_graph.json`
- `ulga/reports/theme_spiral_graph_summary.json`
- `ulga/reports/theme_spiral_graph_qa_audit.json`
- `docs/ulga/ULGA_S8H_THEME_SPIRAL_EDGE_BUILDER_CLOSEOUT.md`

## Files Modified

- None.

S8H did not modify:

- `ulga/graph/dependency_graph.json`
- `ulga/schema/learning_signal_contract.schema.json`
- `ulga/schema/learning_signal_policy.json`
- Dependency Authority artifacts
- Learner State artifacts

## Theme Statistics

- Theme count: 9
- ThemeStageNode count: 21
- ThemeStageNode model: `theme:<theme_id>:<cefr_band>`
- Source files:
  - `themes/theme_catalog.json`
  - `themes/theme_vocab_mapping.json`
  - `ulga/schema/learning_signal_policy.json`

Theme stage counts:

| Theme | Stage Count |
|---|---:|
| academic_life | 2 |
| critical_thinking | 2 |
| daily_life | 3 |
| education | 1 |
| personal_life | 3 |
| social_interaction | 4 |
| transactions | 2 |
| travel | 2 |
| work | 2 |

## Stage Statistics

- Stage aggregation key: normalized `parent_theme` + `level`
- Bridge normalization: parent themes ending with `(Bridge)` are normalized back to their base theme.
- Multiple source theme records at the same normalized theme and CEFR band are aggregated into one ThemeStageNode.

Examples:

- `Daily Life` and `Daily Life (Bridge)` become `daily_life`.
- `Social Interaction` and `Social Interaction (Bridge)` become `social_interaction`.
- `theme:daily_life:A1` aggregates both `a1_daily_life_and_routines` and `a1_homes_and_neighborhoods`.

## Spiral Statistics

- Relation emitted: `SPIRAL_TO`
- SPIRAL_TO edge count: 12
- Gate eligible edge count: 0
- Cross-theme edge count: 0
- Backward edge count: 0
- Self edge count: 0
- Duplicate edge count: 0
- Cycle count: 0
- Edges with absent intermediate CEFR stage gaps: 8

Edge counts by theme:

| Theme | SPIRAL_TO Count |
|---|---:|
| academic_life | 1 |
| critical_thinking | 1 |
| daily_life | 2 |
| personal_life | 2 |
| social_interaction | 3 |
| transactions | 1 |
| travel | 1 |
| work | 1 |

## Validator Result

PASS.

Command:

```powershell
python ulga\validators\validate_theme_spiral_graph.py
```

Result:

```text
ULGA Theme Spiral Graph validation: PASS
```

Validated:

- Schema shape
- Theme existence
- Stage existence
- Invalid relation
- Gate misuse
- Cross-theme spiral
- Backward spiral
- Duplicate edge
- Self edge
- Cycle detection
- Learning Signal policy compliance for `SPIRAL_TO`

## Test Result

Focused S8H tests:

```powershell
python -m pytest tests\ulga\test_theme_spiral_graph.py -q
```

Result:

```text
13 passed
```

Full ULGA test suite:

```powershell
python -m pytest tests\ulga -q
```

Result:

```text
143 passed
```

## QA Audit Result

Result: `PASS_WITH_WARNINGS`

Audit file:

- `ulga/reports/theme_spiral_graph_qa_audit.json`

Blocked findings:

- None.

Warnings:

- 8 `SPIRAL_TO` edges skip absent intermediate CEFR stages. These are accepted as adjacent available stages in the current Theme Authority data, not as strict CEFR-step adjacency.

## Learning Signal Compliance

PASS.

S8H follows `ulga/schema/learning_signal_policy.json`:

- `SPIRAL_TO` has `gate_allowed=false`.
- No `GATE_SIGNAL` was generated.
- No Learning Signal Graph was generated.
- Every emitted Theme Spiral edge has `gate_eligible=false`.
- No Dependency Authority artifact was modified.

Allowed S8H uses:

- recommendation
- coverage
- review
- curriculum sequencing
- future mastery evidence context

Forbidden and not emitted:

- prerequisite gating
- Dependency graph edges
- Learning Signal Graph records
- Theme to Vocabulary edges
- Theme to Pattern edges
- Theme to Chunk edges
- Theme to Grammar edges

## Known Limitations

- S8H emits only `ThemeStageNode -> ThemeStageNode` `SPIRAL_TO`.
- S8H does not emit `INTRODUCES`, `BROADENS_TO`, `CONTRASTS_WITH`, or `REINFORCES`.
- S8H uses normalized `parent_theme` as the v1 base theme identity because the current Theme Authority data does not expose a separate canonical base-theme table.
- Some themes do not have every intermediate CEFR stage. The builder links adjacent available stages within the same normalized theme, which creates 8 non-blocking stage-gap warnings.
- S8H does not classify learner state, planner ranking, reading authority, dialogue authority, or assessment behavior.

## Recommended Next Task

Recommended next task:

- `ULGA-S8I_ThemeSpiralAuthority_QA_Audit`

Rationale:

- S8H introduced the first materialized Theme Spiral graph.
- Before expanding to `INTRODUCES`, `BROADENS_TO`, `CONTRASTS_WITH`, or Learning Signal materialization, the Theme Spiral graph should receive an independent QA audit focused on stage-gap policy, Bridge normalization, same-theme guarantees, and non-gating compliance.

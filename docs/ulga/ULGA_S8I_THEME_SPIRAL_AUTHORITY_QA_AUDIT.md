# ULGA-S8I Theme Spiral Authority QA Audit

## Executive Summary

Final Verdict: **FAIL**

The S8H Theme Spiral graph is structurally safe for non-gating use: all 12 emitted edges are `SPIRAL_TO`, all have `gate_eligible=false`, no `GATE_SIGNAL` or Learning Signal Graph was generated, and no cross-theme, backward, duplicate, self-edge, or cycle issue was detected.

The audit fails because S8I requires each `ThemeStageNode` to include `source_authority`, but all 21 ThemeStageNodes in `ulga/graph/theme_spiral_graph.json` are missing that field. This is a contract completeness issue, not a gating-safety issue. S8I is read-only, so no automatic fix was applied.

## Files Audited

- `ulga/graph/theme_spiral_graph.json`
- `ulga/reports/theme_spiral_graph_summary.json`
- `ulga/reports/theme_spiral_graph_qa_audit.json`
- `ulga/builders/build_theme_spiral_edges.py`
- `ulga/validators/validate_theme_spiral_graph.py`
- `ulga/audits/audit_theme_spiral_graph.py`
- `tests/ulga/test_theme_spiral_graph.py`
- `ulga/schema/learning_signal_policy.json`
- `ulga/schema/learning_signal_contract.schema.json`
- `docs/ulga/ULGA_S8H_THEME_SPIRAL_EDGE_BUILDER_CLOSEOUT.md`
- `docs/ulga/ULGA_S8B_THEME_SPIRAL_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S8F_LEARNING_SIGNAL_CONTRACT_CLOSEOUT.md`
- `docs/ulga/ULGA_S8G_LEARNING_SIGNAL_QA_AUDIT.md`
- `docs/ulga/ULGA_S8D_DEPENDENCY_AUTHORITY_QA_AUDIT.md`

## Commands Executed

Executed:

```powershell
python ulga\validators\validate_theme_spiral_graph.py
```

Result:

```text
ULGA Theme Spiral Graph validation: PASS
```

Executed:

```powershell
python -m pytest tests\ulga\test_theme_spiral_graph.py -q
```

Result:

```text
13 passed
```

Executed:

```powershell
python -m pytest tests\ulga\ -q
```

Result:

```text
143 passed
```

Not executed:

```powershell
python ulga\audits\audit_theme_spiral_graph.py
```

Reason: S8I is read-only and permits only a QA markdown output. The existing audit script writes `ulga/reports/theme_spiral_graph_qa_audit.json`, so rerunning it would modify an existing report artifact. The existing audit JSON was inspected instead.

## Artifact Integrity QA

Status: **PASS**

Findings:

- `theme_spiral_graph.json` exists and parses as JSON.
- `theme_spiral_graph_summary.json` exists and parses as JSON.
- `theme_spiral_graph_qa_audit.json` exists and parses as JSON.
- Builder, validator, audit script, and focused test file exist.
- Summary counts match graph counts:
  - Summary stage count: 21
  - Graph stage count: 21
  - Summary edge count: 12
  - Graph edge count: 12
- Existing S8H audit verdict: `PASS_WITH_WARNINGS`

## Schema / Field QA

Status: **FAIL**

ThemeStageNode required-field result:

| Field | Result |
|---|---|
| `stage_id` | PASS |
| `theme_id` | PASS |
| `cefr_band` | PASS |
| `source_theme_ids` | PASS |
| `source_authority` | FAIL: missing from 21/21 ThemeStageNodes |
| `confidence` | PASS |
| `review_status` | PASS |
| `notes` | PASS |

SPIRAL_TO edge required-field result:

| Field | Result |
|---|---|
| `edge_id` | PASS |
| `source_stage_id` | PASS |
| `target_stage_id` | PASS |
| `relation` | PASS |
| `theme_id` | PASS |
| `source_cefr` | PASS |
| `target_cefr` | PASS |
| `confidence` | PASS |
| `review_status` | PASS |
| `gate_eligible` | PASS |
| `evidence` | PASS |
| `notes` | PASS |

Enum checks:

- All edge `relation` values are `SPIRAL_TO`.
- All edge `gate_eligible` values are `false`.
- All confidence methods are `derived`, which is allowed.
- All review statuses are `accepted`, which is allowed.

Critical gap:

- The current validator does not require `ThemeStageNode.source_authority`, so the validator passes while S8I field QA fails. The validator contract should be updated in a future non-read-only task.

## Stage Resolution QA

Status: **PASS_WITH_WARNINGS**

Findings:

- Every `source_stage_id` resolves to an existing ThemeStageNode.
- Every `target_stage_id` resolves to an existing ThemeStageNode.
- Every source/target pair shares the same normalized `theme_id`.
- Cross-theme edge count: 0
- Dangling stage reference count: 0
- Isolated ThemeStageNode count: 1

Isolated stage:

- `theme:education:A1`

Interpretation:

- The isolated `education` stage is expected under the current source data because there is only one `Education` stage available. It is not a graph safety failure, but it should remain visible for chain completeness review.

## Non-Gating Safety QA

Status: **PASS**

Findings:

- `SPIRAL_TO` gate count: 0
- `gate_eligible=true` count: 0
- No `GATE_SIGNAL` artifact was generated.
- `ulga/graph/learning_signal_graph.json` was not generated.
- S8H graph metadata records `dependency_graph_modified=false`.
- No Dependency Authority artifact was modified during S8I.

## Learning Signal Compliance QA

Status: **PASS**

`learning_signal_policy.json` maps `SPIRAL_TO` to:

- `COVERAGE_SIGNAL`
- `REVIEW_SIGNAL`
- `RECOMMENDATION_SIGNAL`
- `CONTEXT_SIGNAL`

Policy confirms:

- `gate_allowed=false`
- `GATE_SIGNAL` is not an allowed `SPIRAL_TO` signal.

Graph confirms:

- All 12 edges are `SPIRAL_TO`.
- No `BELONGS_TO`, `INTRODUCES`, `BROADENS_TO`, `CONTRASTS_WITH`, or `REINFORCES` edges were emitted.
- No Theme Spiral edge was promoted into a Dependency Authority edge.

## Bridge Normalization QA

Status: **PASS**

Findings:

- `Daily Life` and `Daily Life (Bridge)` normalize to `daily_life`.
- `Social Interaction` and `Social Interaction (Bridge)` normalize to `social_interaction`.
- `Academic Life` and `Academic Life (Bridge)` normalize to `academic_life`.
- `Critical Thinking` and `Critical Thinking (Bridge)` normalize to `critical_thinking`.
- No harmful normalization collision was detected in the emitted graph.

Risk note:

- The current implementation derives base theme identity from normalized `parent_theme` text. This is acceptable for S8H v1, but a future canonical base-theme table would reduce string-normalization risk.

## CEFR Progression QA

Status: **PASS_WITH_WARNINGS**

Findings:

- Backward edge count: 0
- Same-level self-loop count: 0
- Stage-gap warning count: 8
- No edge uses CEFR as a gate.
- No edge contains `planner_weight`; planner scoring is not materialized in S8H.

Stage-gap warnings:

- 8 edges skip absent intermediate CEFR stages and are accepted only as adjacent available stages within the same normalized theme.
- These edges remain non-gating sequencing edges.
- They should be added to a manual review queue in a future non-read-only task before planner weighting is introduced.

Examples:

- `theme:personal_life:A1 -> theme:personal_life:B1`
- `theme:travel:A1 -> theme:travel:B1`
- `theme:work:B1 -> theme:work:C1`

## Cycle / Graph Shape QA

Status: **PASS_WITH_WARNINGS**

Findings:

- Acyclic: PASS
- Duplicate edge count: 0
- Self edge count: 0
- Cycle count: 0
- Isolated ThemeStageNode count: 1

Theme chain completeness:

- 8 themes have at least one `SPIRAL_TO` edge.
- `education` has only one stage and therefore no emitted edge.

## Dependency Separation QA

Status: **PASS**

Findings:

- Theme Spiral graph is separate from `dependency_graph.json`.
- No `REQUIRES` edge was emitted.
- No `hard_prerequisite` was emitted.
- No `gate_eligible` dependency was emitted.
- No CEFR-only evidence was converted into a gate.
- S8H did not emit Theme to Vocabulary, Theme to Pattern, Theme to Chunk, or Theme to Grammar edges.

## Learner State / Planner Readiness QA

Status: **NO-GO_WITH_REMEDIATION**

S8H is directionally useful for S9A as non-gating input:

- `SPIRAL_TO` can support coverage history.
- `SPIRAL_TO` can support review sequencing.
- `SPIRAL_TO` can support context continuity.

S8H is not ready to feed S9A directly without remediation:

- Missing `ThemeStageNode.source_authority` weakens provenance for Learner State ingestion.
- Stage-gap edges need a manual review queue or explicit gap policy before planner weighting.
- Coverage/context signals must not be interpreted as readiness or mastery proof.

## Risk Register

| Risk | Severity | Status | Notes |
|---|---|---|---|
| Missing `ThemeStageNode.source_authority` | High | Open | 21/21 stage nodes are missing S8I-required provenance field. |
| Theme Spiral misused as prerequisite | High | Controlled | All edges are non-gating; policy forbids `SPIRAL_TO` gate. |
| Bridge normalization string collision | Medium | Controlled | No harmful collision found, but canonical base-theme identity is preferable. |
| CEFR stage gap misread as planner jump | Medium | Open | 8 gap edges need manual review before planner weighting. |
| Coverage misread as mastery | Medium | Controlled | No mastery artifact generated; future S9A must preserve distinction. |
| Context misread as readiness | Medium | Controlled | No readiness gate generated. |
| Isolated ThemeStageNode chain incompleteness | Low | Open | `theme:education:A1` has no available next same-theme stage. |

## Final Verdict

**FAIL**

Rationale:

- Safety checks pass: no gate misuse, cross-theme edge, backward edge, cycle, duplicate edge, or Dependency Authority contamination.
- Contract completeness fails: all ThemeStageNodes are missing the S8I-required `source_authority` field.
- Existing S8H validator does not catch this gap, so validator coverage must be tightened in a follow-up implementation task.

## Recommended Next Task

Recommended next task:

- `ULGA-S8H.1_ThemeSpiralGraphContractPatch`

Scope:

- Add `source_authority` to each ThemeStageNode.
- Update `validate_theme_spiral_graph.py` to require `source_authority`.
- Add focused tests for ThemeStageNode provenance.
- Add a stage-gap review queue artifact or explicit gap-review report.
- Rebuild and rerun S8I QA.

After S8H.1 passes:

- Proceed to `ULGA-S9A_LearnerStateAuthority_DesignScan`.

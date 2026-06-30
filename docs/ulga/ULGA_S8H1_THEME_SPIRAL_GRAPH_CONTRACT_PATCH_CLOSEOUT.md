# ULGA-S8H.1 Theme Spiral Graph Contract Patch Closeout

## Files Created

- `ulga/reports/theme_spiral_stage_gap_review_queue.json`
- `docs/ulga/ULGA_S8H1_THEME_SPIRAL_GRAPH_CONTRACT_PATCH_CLOSEOUT.md`

## Files Modified

- `ulga/builders/build_theme_spiral_edges.py`
- `ulga/validators/validate_theme_spiral_graph.py`
- `ulga/audits/audit_theme_spiral_graph.py`
- `tests/ulga/test_theme_spiral_graph.py`
- `ulga/graph/theme_spiral_graph.json`
- `ulga/reports/theme_spiral_graph_summary.json`
- `ulga/reports/theme_spiral_graph_qa_audit.json`

Not modified:

- `ulga/graph/dependency_graph.json`
- `ulga/schema/learning_signal_policy.json`
- `ulga/schema/learning_signal_contract.schema.json`
- `docs/ulga/ULGA_S8I_THEME_SPIRAL_AUTHORITY_QA_AUDIT.md`
- Dependency Authority artifacts
- Learner State artifacts
- Planner artifacts

## Patch Summary

S8H.1 fixes the S8I contract-completeness failure without expanding Theme Spiral scope.

Patched:

- Added `source_authority` provenance to every ThemeStageNode.
- Updated validator checks for ThemeStageNode provenance.
- Added a stage-gap review queue for all `SPIRAL_TO` edges that skip absent intermediate CEFR stages.
- Updated audit metrics for provenance and review queue coverage.
- Updated focused tests for provenance and stage-gap queue behavior.

Still intentionally not built:

- Learning Signal Graph
- Learner State
- Planner
- Reading Authority
- Dialogue Authority
- Theme to Vocabulary/Pattern/Chunk/Grammar edges

## Source Authority Patch

Each ThemeStageNode now includes:

```json
"source_authority": {
  "authority_name": "ThemeAuthority",
  "source_files": [
    "themes/theme_catalog.json",
    "themes/theme_vocab_mapping.json"
  ],
  "source_theme_ids": [],
  "derivation": "normalized_parent_theme_plus_cefr_stage",
  "normalization_policy": "strip_bridge_suffix_and_slugify_parent_theme",
  "confidence_basis": "derived_from_existing_theme_records"
}
```

Validator now checks:

- `source_authority` exists.
- `source_authority.authority_name == "ThemeAuthority"`.
- `source_authority.source_theme_ids` exactly matches `ThemeStageNode.source_theme_ids`.
- `source_authority.source_files` includes both required theme source files.
- `derivation`, `normalization_policy`, and `confidence_basis` are non-empty.

Audit result:

- `stage_node_missing_source_authority_count`: 0
- `source_authority_mismatch_count`: 0

## Stage Gap Review Queue Summary

Review queue artifact:

- `ulga/reports/theme_spiral_stage_gap_review_queue.json`

Counts:

- Stage-gap edges: 8
- Review queue entries: 8
- Stage-gap edges without review queue: 0
- Gate-eligible review queue entries: 0

Each entry records:

- `edge_id`
- `theme_id`
- `source_stage_id`
- `target_stage_id`
- `source_cefr`
- `target_cefr`
- `missing_intermediate_cefr`
- `review_reason = "absent_intermediate_cefr_stage"`
- `review_status = "needs_review"`
- `planner_weight_policy = "cap_or_ignore_until_reviewed"`
- `gate_eligible = false`

## Validator Result

Command:

```powershell
python ulga\validators\validate_theme_spiral_graph.py
```

Result:

```text
ULGA Theme Spiral Graph validation: PASS
```

## Audit Result

Command:

```powershell
python ulga\audits\audit_theme_spiral_graph.py
```

Result:

```text
ULGA Theme Spiral Graph QA Audit: PASS_WITH_WARNINGS
```

Remaining warning:

- 8 `SPIRAL_TO` edges skip absent intermediate CEFR stages; all 8 are now tracked in the stage-gap review queue.

Blocked findings:

- None.

## Test Result

Command:

```powershell
python -m pytest tests\ulga\test_theme_spiral_graph.py -q
```

Result:

```text
15 passed
```

## Full Test Result

Command:

```powershell
python -m pytest tests\ulga\ -q
```

Result:

```text
145 passed
```

## Learning Signal Compliance

PASS.

- All `SPIRAL_TO` edges have `gate_eligible=false`.
- No `GATE_SIGNAL` was generated.
- No Learning Signal Graph was generated.
- Stage-gap review queue entries are non-gating.
- `learning_signal_policy.json` was not modified.
- `learning_signal_contract.schema.json` was not modified.
- `dependency_graph.json` was not modified.

## Remaining Warnings

- `PASS_WITH_WARNINGS` remains appropriate because 8 edges skip absent intermediate CEFR stages.
- The warning is now controlled by `theme_spiral_stage_gap_review_queue.json`.
- Planner should cap or ignore these 8 edges until manual review confirms intended stage jumps.

## Recommended Next Task

Recommended next task:

- `ULGA-S8I.1_ThemeSpiralAuthority_QA_ReAudit`

Rationale:

- S8H.1 directly addresses S8I's fail condition.
- A read-only re-audit should confirm that the missing `source_authority` issue is resolved and that stage-gap review queue coverage is accepted.

After S8I.1 passes:

- Proceed to `ULGA-S9A_LearnerStateAuthority_DesignScan`.

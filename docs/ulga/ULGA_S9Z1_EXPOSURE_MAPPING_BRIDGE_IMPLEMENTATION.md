# ULGA-S9Z1 Exposure Mapping Bridge Implementation

## 1. Scope

Implemented ULGA-S9Z1 Exposure Mapping Bridge Authority V1.

S9Z1 adds a bridge layer between learner-state nodes and opportunity-level exposure evidence:

```text
Learner State Node
-> Exposure Mapping Bridge
-> Learner Exposure Evidence
-> Candidate Expansion
```

S9Z1 does not mutate upstream learner state, learning opportunities, dependency graph, dependency readiness resolution, reinforcement signal, antigravity plan, or reading stub authority.

## 2. Files Created

- `ulga/builders/build_exposure_mapping_bridge.py`
- `ulga/validators/validate_exposure_mapping_bridge.py`
- `ulga/graph/exposure_mapping_bridge.json`
- `ulga/reports/exposure_mapping_bridge_summary.json`
- `tests/ulga/test_exposure_mapping_bridge.py`
- `docs/ulga/ULGA_S9Z1_EXPOSURE_MAPPING_BRIDGE_IMPLEMENTATION.md`

## 3. Files Modified

- `ulga/builders/build_learner_exposure_evidence.py`
- `ulga/validators/validate_learner_exposure_evidence.py`
- `ulga/graph/learner_exposure_evidence.json`
- `ulga/reports/learner_exposure_evidence_summary.json`
- `tests/ulga/test_learner_exposure_evidence.py`

Downstream artifacts were rebuilt by the full ULGA test run:

- `ulga/graph/reinforcement_candidate_expansion.json`
- `ulga/reports/reinforcement_candidate_expansion_summary.json`

## 4. Inputs Read

- `ulga/learner_state/learner_state.json`
- `ulga/graph/learning_opportunities.json`
- `ulga/graph/vocabulary_nodes.json`
- `ulga/graph/sentence_patterns.json`
- `ulga/graph/theme_nodes.json`
- `ulga/graph/dependency_graph.json`
- `ulga/graph/dependency_readiness_resolution.json`
- `ulga/graph/reading_stub_authority.json`
- `ulga/graph/learner_exposure_evidence.json`
- `ulga/reports/learner_exposure_evidence_summary.json`
- `docs/ulga/ULGA_S9Z_EXPOSURE_COVERAGE_EXPANSION_DESIGN_SCAN.md`

## 5. Bridge Types

Implemented V1 bridge types:

| Bridge type | Implemented | Confidence | Notes |
|---|---:|---:|---|
| `direct_focus_node_bridge` | Yes | `1.0` | Includes safe namespace normalization from `sentence_pattern:*` to opportunity `pattern:*`. |
| `grammar_bridge` | Yes | `0.9` | Supported for exact grammar focus matches. No current records matched. |
| `vocabulary_bridge` | Yes | `0.8` | Supported for exact vocabulary focus matches. No current records matched. |
| `theme_bridge` | Yes | `0.4` | Diagnostic only; never planner-safe. |
| `dependency_parent_bridge` | Yes | `0.85` | Supported for grammar nodes required by opportunity dependencies. No current records matched. |

Deferred:

- `chunk_bridge`
- `related_vocab_expansion`
- `semantic_similarity_bridge`

Current bridge distribution:

```json
{
  "direct_focus_node_bridge": 1,
  "theme_bridge": 2
}
```

## 6. Coverage Before

Before S9Z1:

```text
evidence_count = 2
opportunity_mapping_count = 2
coverage_rate = 0.001488
```

S10J1 before S9Z1:

```text
candidate_count = 2
planner_eligible_count = 0
```

## 7. Coverage After

Bridge output:

```json
{
  "status": "PASS",
  "bridge_count": 3,
  "bridge_distribution": {
    "direct_focus_node_bridge": 1,
    "theme_bridge": 2
  },
  "planner_safe_count": 1,
  "warnings": []
}
```

Rebuilt learner exposure evidence:

```json
{
  "status": "PASS",
  "evidence_count": 3,
  "opportunity_mapping_count": 3,
  "weak_count": 2,
  "medium_count": 0,
  "strong_count": 1,
  "coverage_rate": 0.002232,
  "evidence_source_distribution": {
    "direct_focus_node": 1,
    "theme": 2
  },
  "bridge_ref_count": 3,
  "warnings": []
}
```

Coverage improved:

```text
0.001488 -> 0.002232
```

New bridge-enabled mapping:

```text
sentence_pattern:PATTERN_NODE_000014
-> pattern:PATTERN_NODE_000014
-> LO_A1_000014
```

Safety status for the new mapping:

```text
dependency_status = ready
reading_ready = true
planner_safe = true
```

## 8. Validator Result

Validator commands:

```powershell
python ulga\validators\validate_exposure_mapping_bridge.py
python ulga\validators\validate_learner_exposure_evidence.py
```

Results:

```text
Exposure Mapping Bridge validation: PASS
Learner Exposure Evidence validation: PASS
```

Bridge validator checks:

- `bridge_id` unique
- opportunity exists
- source ref exists in learner state
- bridge type valid
- confidence range valid
- `planner_safe` is boolean
- theme bridge is not planner-safe
- dependency-blocked or reading-missing bridge is not planner-safe
- summary counts match bridge records

Learner exposure validator was extended to check:

- `bridge_refs` is present and valid
- bridge-derived mapping types are accepted
- bridge source distribution matches summary
- bridge ref count matches summary

## 9. Test Result

Focused commands:

```powershell
python -m pytest tests\ulga\test_exposure_mapping_bridge.py -q
python -m pytest tests\ulga\test_learner_exposure_evidence.py -q
```

Results:

```text
8 passed
9 passed
```

Full ULGA command:

```powershell
python -m pytest tests\ulga\ -q
```

Result:

```text
353 passed
```

## 10. Warnings

Current S9Z1 warnings:

```text
None
```

Known follow-up risk:

```text
S10J1 now sees one planner-eligible exposure candidate after downstream rebuild.
S10J2 should formally review candidate expansion output with bridge-aware evidence and target-ref handling.
```

Current downstream S10J1 summary after full test rebuild:

```json
{
  "status": "PASS",
  "candidate_count": 3,
  "planner_eligible_count": 1,
  "source_distribution": {
    "exposure_evidence": 3
  },
  "ineligible_reason_distribution": {
    "dependency_blocked": 2
  },
  "exposure_evidence_used_count": 3,
  "dependency_ready_count": 1,
  "reading_ready_count": 3,
  "warnings": []
}
```

## 11. Final Verdict

S9Z1 successfully creates an exposure mapping bridge layer and improves coverage while preserving dependency, reading, and theme-only safety rules.

```text
S9Z1_STATUS: PASS
```

Recommended next task:

```text
ULGA-S10J2_CandidateExpansion_Rebuild_WithBridgeLayer
```

Reason:

```text
coverage_rate improved and downstream planner_eligible_count is now greater than 0 after rebuild.
```

## Closeout Summary

Files Created:

- `ulga/builders/build_exposure_mapping_bridge.py`
- `ulga/validators/validate_exposure_mapping_bridge.py`
- `ulga/graph/exposure_mapping_bridge.json`
- `ulga/reports/exposure_mapping_bridge_summary.json`
- `tests/ulga/test_exposure_mapping_bridge.py`
- `docs/ulga/ULGA_S9Z1_EXPOSURE_MAPPING_BRIDGE_IMPLEMENTATION.md`

Files Modified:

- `ulga/builders/build_learner_exposure_evidence.py`
- `ulga/validators/validate_learner_exposure_evidence.py`
- `ulga/graph/learner_exposure_evidence.json`
- `ulga/reports/learner_exposure_evidence_summary.json`
- `tests/ulga/test_learner_exposure_evidence.py`
- `ulga/graph/reinforcement_candidate_expansion.json`
- `ulga/reports/reinforcement_candidate_expansion_summary.json`

Commands Executed:

```powershell
python ulga\builders\build_exposure_mapping_bridge.py
python ulga\builders\build_learner_exposure_evidence.py
python ulga\validators\validate_exposure_mapping_bridge.py
python ulga\validators\validate_learner_exposure_evidence.py
python -m pytest tests\ulga\test_exposure_mapping_bridge.py -q
python -m pytest tests\ulga\test_learner_exposure_evidence.py -q
python -m pytest tests\ulga\ -q
```

Bridge Count:

- `3`

Bridge Distribution:

- `direct_focus_node_bridge`: `1`
- `theme_bridge`: `2`

Coverage Before:

- `0.001488`

Coverage After:

- `0.002232`

Validator Result:

- `PASS`

Test Result:

- `8 passed`
- `9 passed`
- `353 passed`

Warnings:

- None

Final Verdict:

```text
S9Z1_STATUS: PASS
```

Recommended Next Task:

```text
ULGA-S10J2_CandidateExpansion_Rebuild_WithBridgeLayer
```

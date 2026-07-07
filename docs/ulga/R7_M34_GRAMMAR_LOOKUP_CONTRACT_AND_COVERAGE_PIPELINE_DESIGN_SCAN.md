# R7-M34 Grammar Lookup Contract and Coverage Pipeline Design Scan

## 1. Current State

### Task ID

```text
R7-M34_GrammarLookupContractAndCoveragePipeline_DesignScan
```

### Chinese Name

```text
Grammar Lookup Contract 與 EGP Coverage Pipeline 設計掃描
```

### Predecessor

```text
R7-M33_ReadingV1_GrammarGraph_Integration_Readiness_Scan
```

R7-M33 completed as `PASS_WITH_WARNINGS`. It confirmed that:

```text
READINGV1_GRAMMAR_READY = NO
CROSS_SKILL_GRAMMAR_GATE_READY = NO
EGP_ALIGNMENT_STATUS = MISSING_FOR_NODES
EGP_COVERAGE_GAP_RISK = CRITICAL
GRAMMAR_LOOKUP_CONTRACT_REQUIRED = YES
NO_LEARNER_STATE_WRITE_CONFIRMED = YES
```

R7-M33 also confirmed that the repo cannot yet support EGP-backed level-completion claims unless grammar_nodes, EGP mapping, coverage matrix, query index, and validator artifacts are implemented.

## 2. Purpose

R7-M34 defines the concrete implementation path for:

- `grammar_lookup_contract.json`
- grammar_node to EGP row mapping
- EGP coverage summary generation
- grammar coverage matrix generation
- cross-skill grammar gate matrix generation
- grammar query index generation
- validator pipeline and reports

This task is a DesignScan. It does not implement builders, validators, runtime lookup, PracticeBank generation, learner-facing HTML, or learner_state writes.

## 3. Scope Lock

### In Scope

- Define target artifact list.
- Define artifact dependency order.
- Define schema contracts at field level.
- Define builder sequence.
- Define validator sequence.
- Define CI/check strategy for future implementation.
- Define handoff tasks for implementation.

### Out of Scope

- Populating all A1-B2 grammar_nodes.
- Building the actual runtime lookup engine.
- Generating ReadingV1 PracticeBank.
- Generating Listening / Speaking / Writing content.
- Writing learner_state.
- Claiming A1/A2/B1/B2 grammar readiness.
- Promoting AI-generated mappings to authority without review policy.

## 4. Design Principle

R7-M34 treats EGP as external authority evidence and GrammarSkillTree as internal teaching order.

```text
EGP / CEFR = level evidence
GrammarSkillTree = learning order
Coverage Matrix = level and spiral visibility
Lookup Contract = stable query interface
Validator = final gatekeeper
```

The system must prevent false claims such as:

```text
A1 complete, but only 50% of EGP A1 grammar rules are covered.
```

## 5. Target Artifact Stack

### 5.1 Authority Input

```text
grammar_profile/json/grammar_profile.json
```

Role:

```text
Normalized EGP grammar authority artifact.
```

Required fields:

```text
id
super_category
sub_category
level
guideword
can_do_statement
example
source_sheet
source_row
import_warnings
```

### 5.2 Grammar Node Layer

Target path:

```text
ulga/graph/grammar_nodes.json
```

Role:

```text
Internal GrammarSkillTree node inventory.
```

Required minimum fields:

```json
{
  "grammar_id": "GRAMMAR_EXAMPLE_ID",
  "label": "human readable label",
  "description": "teaching-facing description",
  "node_type": "grammar_rule|grammar_family|grammar_micro_feature",
  "system_stage": "A1|A1+|A2|A2+|B1|B1+|B2",
  "status": "active|candidate|deprecated|review_required",
  "source_policy": "authority_mapped|system_required|review_required",
  "egp_refs": [],
  "created_by": "manual|builder|reviewed_ai_candidate",
  "review_status": "approved|pending|conflict_review_required"
}
```

### 5.3 EGP Alignment Layer

Target path:

```text
ulga/graph/cefr_egp_alignment_table.json
```

Role:

```text
Maps internal grammar_nodes to EGP row-level evidence.
```

Required minimum fields:

```json
{
  "grammar_id": "GRAMMAR_EXAMPLE_ID",
  "egp_refs": [
    {
      "egp_row_id": "EGP_ROW_ID",
      "egp_level": "A1|A2|B1|B2|C1|C2",
      "super_category": "...",
      "sub_category": "...",
      "guideword": "...",
      "can_do_statement_hash": "stable_hash_or_null"
    }
  ],
  "alignment_status": "MATCH|EARLY_BY_DESIGN|LATE_BY_DEPENDENCY|PREVIEW_ONLY|CONFLICT_REVIEW_REQUIRED|NOT_IN_AUTHORITY_SOURCE",
  "alignment_reason": "...",
  "review_status": "approved|pending|operator_required"
}
```

### 5.4 Dependency Edge Layer

Target path:

```text
ulga/graph/grammar_edges.json
```

Role:

```text
Represents prerequisite and dependency relations used to compute teaching order.
```

Required minimum fields:

```json
{
  "edge_id": "GRAMMAR_EDGE_000001",
  "source_grammar_id": "GRAMMAR_BE_VERB_BASIC",
  "target_grammar_id": "GRAMMAR_THERE_IS",
  "relation": "REQUIRES|SUPPORTS|REINFORCES|SPIRAL_TO",
  "strength": "required|recommended|weak",
  "evidence_type": "pedagogical_dependency|egp_sequence_hint|manual_review",
  "review_status": "approved|pending"
}
```

### 5.5 Grammar Order Table

Target path:

```text
ulga/graph/grammar_order_table.json
```

Role:

```text
System teaching order computed from nodes, edges, stage constraints, and policy.
```

Required minimum fields:

```json
{
  "order": 1,
  "stage": "A1",
  "grammar_id": "GRAMMAR_BE_VERB_BASIC",
  "role": "focus|recycle|preview|blocked|maintenance",
  "prerequisites": [],
  "unlock_condition": "start|prerequisites_met|operator_review_required",
  "egp_alignment_status": "MATCH|LATE_BY_DEPENDENCY|..."
}
```

### 5.6 Grammar Coverage Matrix

Target path:

```text
ulga/graph/grammar_coverage_matrix.json
```

Role:

```text
Shows focus / recycle / preview / blocked / maintenance role by level-stage.
```

Required level-stage columns:

```text
A1
A1+
A2
A2+
B1
B1+
B2
```

Required role values:

```text
focus
recycle
preview
blocked
maintenance
not_applicable
```

### 5.7 Cross-Skill Grammar Gate Matrix

Target path:

```text
ulga/graph/cross_skill_grammar_gate_matrix.json
```

Role:

```text
Defines how each grammar rule can be used by Reading, Listening, Speaking, and Writing.
```

Required minimum fields:

```json
{
  "grammar_id": "GRAMMAR_EXAMPLE_ID",
  "stage": "A1+",
  "global_role": "focus|recycle|preview|blocked|maintenance",
  "skill_scope": {
    "reading": {
      "role": "focus|recycle|preview|blocked|maintenance",
      "allowed_question_types": []
    },
    "listening": {
      "role": "recognition|focus|recycle|preview|blocked",
      "allowed_question_types": []
    },
    "speaking": {
      "role": "oral_prompt|controlled_production|free_production|blocked",
      "allowed_activity_types": []
    },
    "writing": {
      "role": "guided_writing|controlled_production|free_production|blocked",
      "allowed_activity_types": []
    }
  },
  "blocked_in": [],
  "receptive_preview_only": false,
  "productive_allowed": true
}
```

### 5.8 Grammar Query Index

Target path:

```text
ulga/graph/grammar_query_index.json
```

Role:

```text
Precomputed query index for ReadingV1 and future four-skill systems.
```

Required query families:

```text
level_stage -> allowed_grammar_ids
level_stage -> blocked_grammar_ids
level_stage + skill -> allowed_grammar_ids
level_stage + skill -> blocked_grammar_ids
grammar_id -> egp_refs
grammar_id -> prerequisites
grammar_id -> cross_skill_roles
egp_row_id -> grammar_ids
egp_level -> uncovered_egp_row_ids
```

### 5.9 Grammar Lookup Contract

Target path:

```text
ulga/contracts/grammar_lookup_contract.json
```

Role:

```text
Stable contract that downstream systems read instead of raw graph files.
```

Required capability flags:

```json
{
  "lookup_by_level": true,
  "lookup_by_skill": true,
  "lookup_by_grammar_id": true,
  "lookup_by_egp_row_id": true,
  "lookup_uncovered_egp_rules": true,
  "lookup_blocked_grammar_by_stage_skill": true,
  "lookup_cross_skill_roles": true,
  "lookup_receptive_preview_vs_productive_mastery": true,
  "no_learner_state_write": true
}
```

### 5.10 Reports

Target report paths:

```text
ulga/reports/grammar_cefr_egp_coverage_summary.json
ulga/reports/grammar_coverage_gap_report.json
ulga/reports/cross_skill_grammar_gate_summary.json
ulga/reports/grammar_lookup_contract_validation_report.json
ulga/reports/grammar_skill_tree_validator_report.json
```

## 6. Pipeline Order

R7-M34 proposes this implementation sequence:

```text
1. Normalize and count EGP rules by level.
2. Create / populate grammar_nodes.json.
3. Map grammar_nodes to EGP rows.
4. Generate cefr_egp_alignment_table.json.
5. Create / populate grammar_edges.json.
6. Generate grammar_order_table.json.
7. Generate grammar_coverage_matrix.json.
8. Generate cross_skill_grammar_gate_matrix.json.
9. Generate grammar_query_index.json.
10. Create grammar_lookup_contract.json.
11. Generate coverage reports.
12. Run validators and emit validator reports.
```

## 7. Builder Design

Suggested builder files:

```text
ulga/builders/build_grammar_egp_level_inventory.py
ulga/builders/build_grammar_node_egp_alignment.py
ulga/builders/build_grammar_order_table.py
ulga/builders/build_grammar_coverage_matrix.py
ulga/builders/build_cross_skill_grammar_gate_matrix.py
ulga/builders/build_grammar_query_index.py
ulga/builders/build_grammar_lookup_contract.py
```

Builder constraints:

- Builders must be deterministic.
- Builders must not write learner_state.
- Builders must not generate learner-facing content.
- Builders must not promote AI-generated mappings without review status.
- Builders must preserve EGP row IDs.
- Builders must emit reports even when coverage is incomplete.

## 8. Validator Design

Suggested validator files:

```text
ulga/validators/validate_grammar_artifact_presence.py
ulga/validators/validate_grammar_egp_alignment.py
ulga/validators/validate_grammar_dependency_graph.py
ulga/validators/validate_grammar_coverage_matrix.py
ulga/validators/validate_cross_skill_grammar_gate.py
ulga/validators/validate_grammar_lookup_contract.py
ulga/validators/validate_grammar_skill_tree_pipeline.py
```

Validator families:

1. Artifact presence validator.
2. EGP mapping validator.
3. Dependency validator.
4. Coverage matrix validator.
5. Cross-skill gate validator.
6. Blocked grammar validator.
7. Practice coverage validator, future-facing only.

## 9. CI / Test Design

Suggested test files:

```text
tests/ulga/test_grammar_egp_level_inventory.py
tests/ulga/test_grammar_node_egp_alignment.py
tests/ulga/test_grammar_coverage_matrix.py
tests/ulga/test_cross_skill_grammar_gate_matrix.py
tests/ulga/test_grammar_lookup_contract.py
tests/ulga/test_grammar_skill_tree_validator.py
```

Required CI expectations after implementation:

```text
- missing required artifact -> FAIL
- empty grammar_nodes -> FAIL
- unresolved egp_ref -> FAIL
- missing coverage matrix -> FAIL
- blocked grammar violation -> FAIL
- speaking/writing using receptive-preview-only grammar -> FAIL
- EGP coverage below configured threshold -> PASS_WITH_WARNINGS or FAIL depending on stage policy
```

## 10. Threshold Policy

Default threshold proposal:

| Status | EGP mapping coverage | Practice coverage | blocked violation |
|---|---:|---:|---:|
| PASS | >= 95% | >= 80% | 0 |
| PASS_WITH_WARNINGS | 85%-94% | 60%-79% | 0 |
| HIGH_GAP_RISK | 60%-84% | 30%-59% | 0 or minor |
| CRITICAL_GAP | < 60% | < 30% | major violation |

R7-M34 does not enforce thresholds. It only defines them for future validator implementation.

## 11. Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| EGP row maps to multiple grammar nodes | Medium | allow multi-row / many-to-many mapping with review status |
| grammar_node is system-required but not in EGP | Medium | require `NOT_IN_EGP_BUT_SYSTEM_REQUIRED` with reason |
| A1+ / A2+ / B1+ mistaken as EGP levels | High | enforce bridge-stage policy |
| receptive preview treated as productive mastery | High | cross-skill validator blocks speaking/writing misuse |
| AI mapping promoted without review | High | require `review_status` and source policy |
| coverage percentage misread as learner mastery | High | reports must state coverage is system readiness, not learner mastery |

## 12. Implementation Task Breakdown

R7-M34 should hand off to implementation in small milestones:

```text
R7-M35_GrammarEGPLevelInventoryBuilderImplementation
R7-M36_GrammarNodeEGPAlignmentPipelineImplementation
R7-M37_GrammarCoverageMatrixBuilderImplementation
R7-M38_CrossSkillGrammarGateMatrixBuilderImplementation
R7-M39_GrammarQueryIndexAndLookupContractImplementation
R7-M40_GrammarEGPCoverageValidatorImplementation
R7-M41_GrammarGraphCoverageCloseoutQA
```

## 13. Gate Checks

```text
R7_M34_DESIGN_SCAN_STATUS = PASS
NO_RUNTIME_IMPLEMENTATION = true
NO_PRACTICEBANK_GENERATION = true
NO_LEARNER_STATE_WRITE = true
GRAMMAR_LOOKUP_CONTRACT_DESIGNED = true
COVERAGE_PIPELINE_ORDER_DEFINED = true
VALIDATOR_PIPELINE_DEFINED = true
NEXT_IMPLEMENTATION_SEQUENCE_DEFINED = true
```

## 14. NEXT_SHORT_STEP

```text
NEXT_SHORT_STEP = R7-M35_GrammarEGPLevelInventoryBuilderImplementation
```

## 15. Closeout

```text
R7_M34_CLOSEOUT_STATUS = PASS
STOP_REASON = NEXT_STEP_REQUIRES_IMPLEMENTATION_APPROVAL
BLOCKER_TYPE = SCOPE_BOUNDARY
LAST_COMPLETED_STATUS = R7_M34_DESIGN_SCAN_PASS
REQUIRED_OPERATOR_ACTION = Approve R7-M35 implementation before builder code is written.
NEXT_RESUME_TASK = R7-M35_GrammarEGPLevelInventoryBuilderImplementation
```

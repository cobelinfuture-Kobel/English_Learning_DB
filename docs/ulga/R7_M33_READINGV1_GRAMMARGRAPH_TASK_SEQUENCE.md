# R7-M33 ReadingV1 GrammarGraph Integration Readiness Scan

## 0. Authority Status

This document is the task-order authority for `R7-M33 ReadingV1 GrammarGraph Integration Readiness Scan`.

All follow-up implementation, audit, validation, and readback tasks for this line must follow the order in this file unless a stop condition is triggered.

## 1. Epic Definition

### Epic ID

`R7-M33_ReadingV1_GrammarGraph_Integration_Readiness_Scan`

### Chinese Name

`ReadingV1 接入 GrammarGraph 前的 EGP 覆蓋與四技能 Grammar Gate 就緒度掃描`

### Purpose

This task does not implement ReadingV1 runtime and does not generate learner-facing practice items.

The purpose is to verify whether the existing GrammarSkillTree / GrammarGraph can support:

- A1, A1+, A2, A2+, B1, B1+, B2 level-stage grammar readiness.
- English Grammar Profile grammar-rule coverage measurement.
- EGP coverage gap identification.
- Reading / Listening / Speaking / Writing shared grammar gating.
- Validator-based detection of blocked grammar, missing EGP evidence, missing prerequisites, and cross-skill misuse.

The task must make it possible to answer:

- How much of EGP A1 grammar is covered?
- How much of EGP A2 grammar is covered?
- How much of EGP B1 grammar is covered?
- How much of EGP B2 grammar is covered?
- Which EGP rules have no grammar node?
- Which grammar nodes have no EGP evidence?
- Which rules are only available for receptive preview?
- Which rules are allowed for speaking / writing production?

## 2. Scope Lock

### In Scope

- Grammar artifact inventory.
- EGP source readiness scan.
- Grammar node to EGP mapping audit.
- Cross-skill EGP grammar coverage matrix readiness.
- Grammar lookup contract decision.
- Validator / gap report contract.
- Final readiness classification.

### Out of Scope

- ReadingV1 runtime implementation.
- PracticeBank generation.
- Learner-facing HTML generation.
- learner_state write.
- adaptive planner implementation.
- error-book implementation.
- listening runtime.
- speaking runtime.
- writing runtime.
- mass question generation.
- full A1-B2 remediation unless explicitly scheduled after this scan.

## 3. Auto-Progress Control

This project runs in auto-progress mode unless a stop condition is triggered.

### Non-stop Conditions

The following are not valid stopping points:

- `PASS_CI_SYNCED_AND_MERGED`
- successful file write
- PR merged
- closeout completed
- readback completed
- NEXT_SHORT_STEP generated

### Required Continuation Rule

After each milestone:

1. Produce a short readback.
2. Update status.
3. Validate the result against this task-order document.
4. Continue to the next `NEXT_SHORT_STEP` if `STOP_REASON = NONE`.

### Stop Conditions

Stop only when one of the following occurs:

- CI failure.
- GitHub tool error / safety blocker that cannot be bypassed by an approved alternate write path.
- PR merge blocked.
- Next step exceeds this approved scope.
- Next step would modify files explicitly forbidden by the current milestone.
- Human selection of source_ref / evidence is required.
- Transition from planning-only to implementation where policy requires separate approval.

### Required Stop Output

If stopped, output:

```text
STOP_REASON: <reason>
BLOCKER_TYPE: <type>
LAST_COMPLETED_STATUS: <status>
REQUIRED_OPERATOR_ACTION: <operator action>
NEXT_RESUME_TASK: <resume task>
```

## 4. Task Tree

```text
R7-M33 ReadingV1 GrammarGraph Integration Readiness Scan

├─ R7-M33A GrammarGraph Scope and Artifact Inventory Scan
│  ├─ M33A Scope / Source Preflight
│  ├─ M33B Grammar Artifact Inventory
│  └─ M33C EGP Source Readiness
│
├─ R7-M33B Grammar Node EGP Mapping Audit
│  └─ M33D Grammar Node ↔ EGP Mapping Audit
│
├─ R7-M33C Cross-Skill EGP Grammar Coverage Matrix Readiness
│  └─ M33E Cross-Skill EGP Grammar Coverage Matrix Readiness
│
├─ R7-M33D Grammar Lookup Contract and Validator Decision
│  ├─ M33F Grammar Lookup Contract Decision
│  └─ M33G Validator / Gap Report Design
│
└─ R7-M33E Final Readiness Classification
   └─ M33H Final Readiness Classification
```

## 5. Ordered Milestones

| Order | Task ID | Name | Purpose | Expected Output |
|---:|---|---|---|---|
| 1 | R7-M33A | GrammarGraph Scope and Artifact Inventory Scan | Lock scope and inspect existing artifacts | scope report, artifact inventory, EGP readiness report |
| 2 | R7-M33B | Grammar Node EGP Mapping Audit | Determine whether grammar_nodes are mapped to EGP rules | mapping audit, uncovered EGP rules list |
| 3 | R7-M33C | Cross-Skill EGP Grammar Coverage Matrix Readiness | Determine coverage and four-skill grammar gate readiness | coverage summary, cross-skill matrix, gap report |
| 4 | R7-M33D | Grammar Lookup Contract and Validator Decision | Decide whether lookup contract and validators are required | lookup contract decision, validator contract |
| 5 | R7-M33E | Final Readiness Classification | Classify readiness and define next task | final readiness report |

## 6. Milestone Details

### R7-M33A GrammarGraph Scope and Artifact Inventory Scan

#### M33A Scope / Source Preflight

Required checks:

- `NO_READING_RUNTIME = true`
- `NO_PRACTICEBANK_GENERATION = true`
- `NO_LEARNER_STATE_WRITE = true`
- `SCAN_ONLY = true`
- Confirm source set: EGP, grammar_nodes, grammar_edges, grammar_order_table, grammar_coverage_matrix, grammar_query_index, validator report.

Expected output:

- `docs/ulga/R7_M33A_SCOPE_PREFLIGHT.md`

#### M33B Grammar Artifact Inventory

Required checks:

- `grammar_nodes.json`
- `grammar_edges.json`
- `grammar_order_table.json`
- `grammar_coverage_matrix.json`
- `cefr_egp_alignment_table.json`
- `grammar_query_index.json`
- `grammar_skill_tree_validator_report.json`
- EGP normalized artifact, if present.

Status values:

- `PRESENT`
- `MISSING`
- `PARTIAL`
- `CONTRACT_ONLY`
- `STALE`

Expected output:

- `ulga/reports/r7_m33_grammar_artifact_inventory_report.json`

#### M33C EGP Source Readiness

Required checks:

- `English Grammar Profile Online.xlsx` source registration exists.
- Normalized `grammar_profile.json` or equivalent exists.
- EGP rows have stable IDs.
- EGP rows include level / category / guideword / can-do / example where available.
- A1 / A2 / B1 / B2 can be queried by level.

Expected output:

- `ulga/reports/r7_m33_egp_source_readiness_report.json`

Gate:

```text
R7_M33A_STATUS = PASS / PASS_WITH_WARNINGS / FAIL
```

### R7-M33B Grammar Node EGP Mapping Audit

#### M33D Grammar Node ↔ EGP Mapping Audit

Required checks:

- Each grammar_node has or lacks `egp_refs` explicitly recorded.
- Each `egp_ref` can be traced back to an EGP row.
- Each mapped node has `alignment_status`.
- Unmapped grammar_nodes are listed.
- EGP rules without grammar_node are listed.
- Multi-row / one-to-many mappings requiring review are listed.

Mapping status values:

- `EGP_MAPPED`
- `EGP_PARTIAL_MATCH`
- `EGP_MULTI_ROW_MATCH`
- `NOT_IN_EGP_BUT_SYSTEM_REQUIRED`
- `UNMAPPED`
- `CONFLICT_REVIEW_REQUIRED`

Expected outputs:

- `ulga/reports/r7_m33_grammar_node_egp_mapping_audit.json`
- `ulga/reports/r7_m33_uncovered_egp_rules.json`

Gate:

```text
R7_M33B_STATUS = PASS / PASS_WITH_WARNINGS / FAIL
```

### R7-M33C Cross-Skill EGP Grammar Coverage Matrix Readiness

#### M33E Cross-Skill EGP Grammar Coverage Matrix Readiness

Purpose:

Verify that the grammar coverage matrix is not ReadingV1-only. It must be capable of becoming a shared grammar gate for Reading, Listening, Speaking, and Writing.

Required checks:

- Each grammar rule has a level-stage role: `focus`, `recycle`, `preview`, `blocked`, or `maintenance`.
- A1+ / A2+ / B1+ are internal bridge stages, not official EGP levels.
- EGP required-rule coverage can be calculated per level.
- Uncovered EGP rules can be listed per level.
- Skill-specific roles exist or are explicitly missing for reading / listening / speaking / writing.
- Receptive preview is distinguishable from productive mastery.
- Blocked grammar violation detection is possible.

Required metrics:

- `EGP_RULE_MAPPING_COVERAGE`
- `SYSTEM_STAGE_COVERAGE`
- `CROSS_SKILL_COVERAGE`
- `PRACTICE_COVERAGE`
- `VALIDATOR_PASS_RATE`
- `UNCOVERED_EGP_RULES`
- `BLOCKED_GRAMMAR_VIOLATIONS`

Suggested risk thresholds:

| Status | EGP mapping coverage | Practice coverage | blocked violation |
|---|---:|---:|---:|
| PASS | >= 95% | >= 80% | 0 |
| PASS_WITH_WARNINGS | 85%-94% | 60%-79% | 0 |
| HIGH_GAP_RISK | 60%-84% | 30%-59% | 0 or minor |
| CRITICAL_GAP | < 60% | < 30% | major violation |

Expected outputs:

- `ulga/reports/r7_m33_grammar_cefr_egp_coverage_summary.json`
- `ulga/reports/r7_m33_cross_skill_grammar_gate_matrix.json`
- `ulga/reports/r7_m33_grammar_coverage_gap_report.json`

Gate:

```text
R7_M33C_STATUS = PASS / PASS_WITH_WARNINGS / FAIL
```

### R7-M33D Grammar Lookup Contract and Validator Decision

#### M33F Grammar Lookup Contract Decision

Decision options:

- `NEEDED`
- `NOT_NEEDED`
- `NEEDED_LATER`

Default expectation:

`grammar_lookup_contract.json` is likely needed if ReadingV1 or future four-skill systems cannot query allowed / blocked / uncovered grammar through a stable interface.

Required lookup capabilities:

- `lookup_by_level`
- `lookup_by_skill`
- `lookup_by_grammar_id`
- `lookup_by_egp_row_id`
- `lookup_uncovered_egp_rules`
- `lookup_blocked_grammar_by_stage_skill`
- `no_learner_state_write`

Expected output:

- `docs/ulga/R7_M33D_GRAMMAR_LOOKUP_CONTRACT_DECISION.md`

#### M33G Validator / Gap Report Design

Required validator checks:

- grammar_id exists.
- EGP refs exist or absence is explicitly justified.
- prerequisite exists.
- graph has no cycle.
- introduced_stage does not violate prerequisite constraints.
- blocked grammar is not used in prohibited stages or skills.
- recycle coverage is sufficient.
- productive-skill usage is not earlier than allowed.

Expected output:

- `docs/ulga/R7_M33D_GRAMMAR_EGP_COVERAGE_VALIDATOR_CONTRACT.md`

Gate:

```text
R7_M33D_STATUS = PASS / PASS_WITH_WARNINGS / FAIL
```

### R7-M33E Final Readiness Classification

#### M33H Final Readiness Classification

Required final fields:

```text
READINGV1_GRAMMAR_READY = YES / PARTIAL / NO
CROSS_SKILL_GRAMMAR_GATE_READY = YES / PARTIAL / NO
EGP_ALIGNMENT_STATUS = FULL / PARTIAL / CONTRACT_ONLY / MISSING
EGP_COVERAGE_GAP_RISK = LOW / MEDIUM / HIGH / CRITICAL
GRAMMAR_LOOKUP_CONTRACT_REQUIRED = YES / NO
NO_LEARNER_STATE_WRITE_CONFIRMED = YES / NO
NEXT_RESUME_TASK = <task id>
```

Expected output:

- `docs/ulga/R7_M33_READINGV1_GRAMMARGRAPH_READINESS_REPORT.md`

Gate:

```text
R7_M33E_STATUS = PASS / PASS_WITH_WARNINGS / FAIL
```

## 7. Final Success Criteria

R7-M33 is complete only when the final readiness report can answer:

- Whether ReadingV1 can safely use the current GrammarGraph.
- Whether the grammar gate can support future Listening / Speaking / Writing systems.
- Whether EGP rule coverage can be measured per level.
- Whether uncovered EGP rules can be listed.
- Whether missing EGP alignment can be detected.
- Whether blocked grammar use can be prevented.
- Whether a grammar lookup contract is required.

## 8. Current NEXT_SHORT_STEP

```text
NEXT_SHORT_STEP:
R7-M33A_GrammarGraphScopeAndArtifactInventoryScan
```

## 9. Current Control State

```text
R7_M33_TASK_SEQUENCE_STATUS = ACTIVE
STOP_REASON = NONE
NEXT_RESUME_TASK = R7-M33A_GrammarGraphScopeAndArtifactInventoryScan
```
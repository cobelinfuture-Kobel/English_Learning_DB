# R7-M33D Grammar EGP Coverage Validator Contract

## Task

`R7-M33D_GrammarLookupContractAndValidatorDecision`

## Purpose

Define the validator requirements needed to prevent false level completion claims such as:

```text
A1 completed, but only 50% of EGP A1 grammar rules are covered.
```

This file is a validator contract only. It does not implement validator runtime.

## Required Validator Families

### 1. Artifact Presence Validator

Checks:

- `grammar_nodes.json` exists and is non-empty.
- `grammar_edges.json` exists and is non-empty.
- `grammar_order_table.json` exists and is non-empty.
- `grammar_coverage_matrix.json` exists and is non-empty.
- `cefr_egp_alignment_table.json` exists and is non-empty.
- `grammar_query_index.json` exists and is non-empty.

### 2. EGP Mapping Validator

Checks:

- Every grammar_node has either:
  - at least one `egp_ref`, or
  - explicit `NOT_IN_EGP_BUT_SYSTEM_REQUIRED` status with review reason.
- Every `egp_ref` resolves to a normalized EGP row.
- Every mapped node has `alignment_status`.
- Every official EGP level can report mapped and unmapped rules.

Allowed `alignment_status` values:

```text
MATCH
EARLY_BY_DESIGN
LATE_BY_DEPENDENCY
PREVIEW_ONLY
CONFLICT_REVIEW_REQUIRED
NOT_IN_AUTHORITY_SOURCE
```

### 3. Dependency Validator

Checks:

- Every prerequisite grammar_id exists.
- Grammar dependency graph has no cycle.
- Introduced stage does not violate prerequisite constraints.
- Dependency edges are typed and traceable.

### 4. Coverage Matrix Validator

Checks:

- Each grammar rule has a level-stage role:
  - `focus`
  - `recycle`
  - `preview`
  - `blocked`
  - `maintenance`
- A1+ / A2+ / B1+ are treated as internal bridge stages, not official EGP levels.
- EGP required-rule coverage can be calculated for A1 / A2 / B1 / B2.
- Uncovered EGP rules can be listed.

### 5. Cross-Skill Gate Validator

Checks:

- Reading scope is present.
- Listening scope is present or explicitly unsupported.
- Speaking scope is present or explicitly unsupported.
- Writing scope is present or explicitly unsupported.
- Receptive preview is not treated as productive mastery.
- Speaking and writing cannot use grammar that is only marked as receptive preview.

### 6. Blocked Grammar Validator

Checks:

- No blocked grammar appears in generated or selected content for that stage.
- No productive-skill activity uses blocked grammar.
- No B1/B2 grammar is used in A1/A2 as production unless explicitly marked `preview_only` and limited to receptive skills.

### 7. Practice Coverage Validator

Checks after PracticeBank exists:

- Each focus grammar rule has sufficient practice items.
- Each recycle grammar rule has sufficient reinforcement exposure.
- Practice item `grammar_focus` resolves to grammar_node.
- Practice item `grammar_recycle` resolves to grammar_node.
- Practice item has no blocked grammar violation.

This validator is future-facing for ReadingV1 / four-skill PracticeBank. It is not executed in R7-M33 because PracticeBank generation is out of scope.

## Required Metrics

```text
EGP_RULE_MAPPING_COVERAGE
SYSTEM_STAGE_COVERAGE
CROSS_SKILL_COVERAGE
PRACTICE_COVERAGE
VALIDATOR_PASS_RATE
UNCOVERED_EGP_RULES
BLOCKED_GRAMMAR_VIOLATIONS
```

## Suggested Thresholds

| Status | EGP mapping coverage | Practice coverage | blocked violation |
|---|---:|---:|---:|
| PASS | >= 95% | >= 80% | 0 |
| PASS_WITH_WARNINGS | 85%-94% | 60%-79% | 0 |
| HIGH_GAP_RISK | 60%-84% | 30%-59% | 0 or minor |
| CRITICAL_GAP | < 60% | < 30% | major violation |

## Current R7-M33 Scan Result

```text
VALIDATOR_REQUIRED = YES
CURRENT_VALIDATOR_RUNTIME_FOUND = NO
CURRENT_EGP_COVERAGE_GAP_RISK = CRITICAL
```

## Status

```text
R7_M33D_VALIDATOR_CONTRACT_STATUS = PASS
STOP_REASON = NONE
NEXT_SHORT_STEP = R7-M33E_FinalReadinessClassification
```

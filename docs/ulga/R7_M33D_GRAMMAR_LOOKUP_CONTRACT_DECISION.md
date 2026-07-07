# R7-M33D Grammar Lookup Contract Decision

## Task

`R7-M33D_GrammarLookupContractAndValidatorDecision`

## Decision

```text
GRAMMAR_LOOKUP_CONTRACT_REQUIRED = YES
```

## Reason

ReadingV1 and future Listening / Speaking / Writing systems should not directly read raw grammar artifacts.

A stable lookup contract is required because the current scan found:

- `grammar_nodes.json` exists but appears empty.
- `grammar_edges.json` is missing at the standard path.
- `grammar_order_table.json` is missing at the standard path.
- `grammar_coverage_matrix.json` is missing at the standard path.
- `cefr_egp_alignment_table.json` is missing at the standard path.
- `grammar_query_index.json` is missing at the standard path.
- `grammar_skill_tree_validator_report.json` is missing at the standard path.

Without a lookup contract, ReadingV1 cannot safely answer:

- Which grammar rules are allowed at A1 / A1+ / A2 / A2+ / B1 / B1+ / B2?
- Which EGP rules are uncovered?
- Which grammar rules are blocked?
- Which grammar rules are receptive-only preview?
- Which grammar rules are allowed for productive speaking / writing?

## Required Contract Capabilities

A future `grammar_lookup_contract.json` should support:

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

## Required Lookup Inputs

```text
level_stage
skill
skill_role
grammar_id
egp_row_id
question_type
activity_type
```

## Required Lookup Outputs

```text
allowed_grammar_ids
blocked_grammar_ids
uncovered_egp_rules
covered_egp_rules
grammar_alignment_status
grammar_prerequisites
cross_skill_roles
validator_requirements
```

## Suggested Contract Location

```text
ulga/contracts/grammar_lookup_contract.json
```

## Implementation Boundary

This milestone only makes the contract decision. It does not implement the contract file or runtime lookup engine.

## Status

```text
R7_M33D_LOOKUP_CONTRACT_DECISION_STATUS = PASS
GRAMMAR_LOOKUP_CONTRACT_REQUIRED = YES
STOP_REASON = NONE
NEXT_SHORT_STEP = R7-M33E_FinalReadinessClassification
```

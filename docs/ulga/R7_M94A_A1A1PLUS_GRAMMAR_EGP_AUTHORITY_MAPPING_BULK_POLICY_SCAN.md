# R7-M94A A1/A1_PLUS Grammar EGP Authority Mapping Bulk Policy Scan

## Task

```text
R7-M94A_A1A1PLUSGrammarEGPAuthorityMappingBulkPolicyScan
```

## Reason for mode change

Batch 01 established the safe EGP / RAZ / canonical patch pipeline, but the 5-node handoff model is too slow for the remaining grammar-node coverage work.

The process is now switched to level-band bulk mapping.

## Scope

```text
level_band = A1 + A1_PLUS
source_nodes = ulga/grammar/grammar_nodes.json
source_egp = EGP source artifacts / workbook-derived rows
primary_target = grammar nodes without sufficient EGP evidence refs
```

## Bulk target selection rule

Include grammar nodes where:

```text
introduced_stage in [A1, A1_PLUS]
AND grammar_id not already completed with acceptable EGP authority evidence
```

Batch 01 already patched:

```text
GRAMMAR_ARTICLES_BASIC
GRAMMAR_CAN_STATEMENT
GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC
```

Batch 01 still unresolved and must be included in bulk refined mapping:

```text
GRAMMAR_BASIC_PREPOSITIONS_PLACE
GRAMMAR_BE_VERB_BASIC
```

## Required output categories

Each target must be classified into one of:

```text
AUTO_ACCEPTABLE_AUTHORITY_EVIDENCE
AUTO_ACCEPTABLE_FORM_ONLY_EVIDENCE
NEEDS_REFINED_CANDIDATE
NO_EGP_AUTHORITY_FOUND
ALREADY_PATCHED
```

## Required artifacts

The next implementation may create:

```text
ulga/builders/build_grammar_node_egp_a1_a1plus_bulk_authority_mapping.py
ulga/validators/validate_grammar_node_egp_a1_a1plus_bulk_authority_mapping.py
tests/ulga/test_grammar_node_egp_a1_a1plus_bulk_authority_mapping.py
ulga/reports/grammar_node_egp_a1_a1plus_bulk_authority_mapping.json
ulga/reports/grammar_node_egp_a1_a1plus_bulk_authority_mapping_summary.json
```

## Canonical write boundary

This bulk mapping step is still report-only.

It must not directly modify:

```text
ulga/grammar/grammar_nodes.json
```

It must not write:

```text
egp_evidence_refs
egp_form_evidence_refs
coverage promotion fields
PracticeBank
learner state
runtime files
```

## Efficiency constraint

Do not return to a 5-node handoff loop. The unit of work is now a whole level band.

## Acceptance criteria

```text
A1/A1_PLUS target inventory produced
classification summary produced
unresolved queue produced inside report
validator passes
tests pass
no canonical grammar write
```

## Status

```text
R7_M94A_STATUS = PASS
LAST_COMPLETED_STATUS = R7_M94A_BULK_POLICY_SCAN_PASS
NEXT_SHORT_STEP = R7-M95A_A1A1PLUSGrammarEGPAuthorityMappingBulkBuilder
STOP_REASON = NONE
```

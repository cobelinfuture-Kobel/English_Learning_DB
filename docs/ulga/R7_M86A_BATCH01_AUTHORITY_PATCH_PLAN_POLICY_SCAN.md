# R7-M86A Batch 01 Authority Patch Plan Policy Scan

## Task

```text
R7-M86A_Batch01AuthorityPatchPlanPolicyScan
```

## Input state

```text
R7_M85A_STATUS = PASS_CI_SYNCED
operator_decision_status = APPROVED_R7_M84A_COORDINATION_PACKET
```

## Purpose

Plan the next authority-facing patch without applying it.

This policy scan converts the approved coordination decisions into a guarded patch-plan scope.

## Non-negotiable boundary

This task is planning only.

It must not modify:

```text
ulga/grammar/grammar_nodes.json
any canonical grammar node authority file
any learner state file
any runtime file
```

It must not write:

```text
egp_evidence_refs
RAZ usage attachment fields
coverage promotion fields
PracticeBank output
```

## Approved Batch 01 coordination outcomes

```text
B01-01 GRAMMAR_ARTICLES_BASIC
EGP = accept row 1741163708789x105964971324936210 as authority evidence
RAZ = keep approved usage examples

B01-02 GRAMMAR_BASIC_PREPOSITIONS_PLACE
EGP = unresolved; request refined candidates
RAZ = keep approved usage examples

B01-03 GRAMMAR_BE_VERB_BASIC
EGP = unresolved; request refined candidates
RAZ = keep approved usage examples

B01-04 GRAMMAR_CAN_STATEMENT
EGP = accept row 1741163708329x931125497510935300 as form evidence only
RAZ = keep approved semantic usage examples

B01-05 GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC
EGP = accept row 1741163709005x427091401714639400 as authority evidence
RAZ = keep approved usage examples
```

## Patch-plan output contract

The next implementation artifact may create:

```text
ulga/reports/grammar_node_egp_batch01_authority_patch_plan.json
ulga/reports/grammar_node_egp_batch01_authority_patch_plan_summary.json
ulga/validators/validate_grammar_node_egp_batch01_authority_patch_plan.py
tests/ulga/test_grammar_node_egp_batch01_authority_patch_plan.py
```

## Patch-plan content requirements

Each plan record should include:

```text
grammar_id
planned_action
selected_egp_row_id
selected_egp_evidence_role
raz_usage_status
write_target_path
write_allowed = false
operator_review_required = true
```

## Planned actions

```text
PLAN_AUTHORITY_EGP_EVIDENCE_PATCH
PLAN_FORM_ONLY_EGP_EVIDENCE_PATCH
PLAN_REFINED_EGP_CANDIDATE_REQUEST
```

## Expected records

```text
GRAMMAR_ARTICLES_BASIC -> PLAN_AUTHORITY_EGP_EVIDENCE_PATCH
GRAMMAR_BASIC_PREPOSITIONS_PLACE -> PLAN_REFINED_EGP_CANDIDATE_REQUEST
GRAMMAR_BE_VERB_BASIC -> PLAN_REFINED_EGP_CANDIDATE_REQUEST
GRAMMAR_CAN_STATEMENT -> PLAN_FORM_ONLY_EGP_EVIDENCE_PATCH
GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC -> PLAN_AUTHORITY_EGP_EVIDENCE_PATCH
```

## Acceptance criteria

```text
patch plan artifact exists
patch plan summary exists
validator passes
pytest passes
no authority files modified
no egp_evidence_refs written
all write_allowed fields remain false
```

## Status

```text
R7_M86A_STATUS = PASS
LAST_COMPLETED_STATUS = R7_M86A_POLICY_SCAN_PASS
NEXT_SHORT_STEP = R7-M87A_Batch01AuthorityPatchPlanArtifactBuilder
STOP_REASON = PLANNING_TO_IMPLEMENTATION_APPROVAL_REQUIRED
```

# R7-M89A Batch 01 Canonical Grammar Authority Patch Preflight

## Task

```text
R7-M89A_Batch01CanonicalGrammarAuthorityPatchPreflight
```

## Input state

```text
R7_M88A_STATUS = PASS_WITH_OPERATOR_APPROVAL_REQUIRED
operator_approval_for_preflight = received
```

## Scope

This preflight inspects the canonical grammar source and confirms whether a future Batch 01 authority patch is structurally safe.

This task does not modify canonical grammar data.

## Canonical source inspected

```text
ulga/grammar/grammar_nodes.json
```

The file exists and is a compact JSON array of grammar-node records.

## Batch 01 target presence

All five Batch 01 grammar IDs are present in the canonical grammar source.

```text
GRAMMAR_ARTICLES_BASIC = present
authority_status = candidate
current egp_evidence_refs = absent

GRAMMAR_BASIC_PREPOSITIONS_PLACE = present
authority_status = candidate
current egp_evidence_refs = absent

GRAMMAR_BE_VERB_BASIC = present
authority_status = accepted
current egp_evidence_refs = absent

GRAMMAR_CAN_STATEMENT = present
authority_status = accepted
current egp_evidence_refs = absent

GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC = present
authority_status = candidate
current egp_evidence_refs = absent
```

## Future patch candidates from R7-M87A

```text
GRAMMAR_ARTICLES_BASIC
planned_action = PLAN_AUTHORITY_EGP_EVIDENCE_PATCH
selected_egp_row_id = 1741163708789x105964971324936210
selected_egp_evidence_role = EGP_AUTHORITY_EVIDENCE

GRAMMAR_BASIC_PREPOSITIONS_PLACE
planned_action = PLAN_REFINED_EGP_CANDIDATE_REQUEST
selected_egp_row_id = null

GRAMMAR_BE_VERB_BASIC
planned_action = PLAN_REFINED_EGP_CANDIDATE_REQUEST
selected_egp_row_id = null

GRAMMAR_CAN_STATEMENT
planned_action = PLAN_FORM_ONLY_EGP_EVIDENCE_PATCH
selected_egp_row_id = 1741163708329x931125497510935300
selected_egp_evidence_role = EGP_FORM_EVIDENCE

GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC
planned_action = PLAN_AUTHORITY_EGP_EVIDENCE_PATCH
selected_egp_row_id = 1741163709005x427091401714639400
selected_egp_evidence_role = EGP_AUTHORITY_EVIDENCE
```

## Preflight findings

```text
canonical_source_exists = true
batch01_targets_present = true
existing_batch01_egp_evidence_refs_absent = true
patch_target_count = 3
refined_request_count = 2
schema_risk = medium
```

The schema risk is medium because current A1 nodes are compact records, while later B1/B2 nodes already use `egp_evidence_refs` directly. A future patch must preserve compact node fields and add evidence fields without changing unrelated nodes.

## Required future patch constraints

A future patch must:

```text
modify only ulga/grammar/grammar_nodes.json
modify only these grammar IDs:
  GRAMMAR_ARTICLES_BASIC
  GRAMMAR_CAN_STATEMENT
  GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC
leave GRAMMAR_BASIC_PREPOSITIONS_PLACE unchanged
leave GRAMMAR_BE_VERB_BASIC unchanged
preserve all existing fields
not change runtime files
not generate PracticeBank
not write learner state
```

## Proposed future field model

For authority evidence rows:

```json
"egp_evidence_refs": [
  "EGP_SOURCE_XLSX::Data!A?:H?::id=<egp_row_id>"
]
```

For form-only evidence, do not mix semantic ability into the EGP authority field. Use a separate review-safe extension field only if the implementation policy approves it:

```json
"egp_form_evidence_refs": [
  "EGP_SOURCE_XLSX::Data!A?:H?::id=<egp_row_id>"
]
```

## Blocking issue before direct patch

The EGP row IDs are known, but exact source row coordinates for Batch 01 accepted rows must be resolved before writing canonical evidence refs.

Known row IDs:

```text
1741163708789x105964971324936210
1741163708329x931125497510935300
1741163709005x427091401714639400
```

Required format needs exact row coordinate:

```text
EGP_SOURCE_XLSX::Data!A?:H?::id=<egp_row_id>
```

Therefore, direct patching is blocked until row coordinates are resolved by an evidence-ref resolver or explicitly approved as id-only evidence references.

## Status

```text
R7_M89A_STATUS = PASS_WITH_BLOCKER
LAST_COMPLETED_STATUS = R7_M89A_PREFLIGHT_PASS_WITH_BLOCKER
STOP_REASON = NEED_HUMAN_SOURCE_REF_EVIDENCE_SELECTION
BLOCKER_TYPE = EGP_SOURCE_REF_COORDINATE_REQUIRED
REQUIRED_OPERATOR_ACTION = Approve an evidence-ref resolver step or provide exact EGP source row coordinates for the three selected row IDs.
NEXT_RESUME_TASK = R7-M90A_Batch01EGPSourceRefResolver
```

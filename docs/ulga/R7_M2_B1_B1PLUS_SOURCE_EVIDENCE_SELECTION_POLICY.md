# R7-M2 B1 / B1_PLUS Source-evidence Selection Policy

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M2 B1 / B1_PLUS source-evidence selection policy

Branch:
codex/r7-m2-b1-b1plus-source-evidence-policy

Status:
POLICY_ONLY
```

R7-M2 defines which sources can support the B1 / B1_PLUS planning proposals from R7-M1. This task does not modify `grammar_nodes.json`, `grammar_edges.json`, derived artifacts, validators, CI tests, learner-facing practice, or learner state.

## 2. Prior Gate From R7-M1

R7-M1 proposed a planning-only B1 / B1_PLUS surface:

```text
B1 proposed nodes = 6
B1_PLUS proposed nodes = 4
Total proposed planning surface = 10
```

R7-M1 explicitly kept these proposals out of `grammar_nodes.json` and `grammar_edges.json`.

## 3. Scope Lock

Allowed in R7-M2:

```text
- define allowed source roles for B1 / B1_PLUS evidence
- define source priority and minimum evidence requirements
- define proposal-level evidence requirements
- define blocked source usage
- define readiness gate for future implementation
- produce a resumable next task
```

Forbidden in R7-M2:

```text
- no grammar_nodes.json modification
- no grammar_edges.json modification
- no derived artifact rebuild
- no validation report refresh
- no CI test expectation change
- no learner-facing practice generation
- no learner state write
- no accepted authority promotion
- no B2 implementation
```

## 4. Current Baseline To Protect

Current static grammar artifact baseline remains unchanged:

```text
status = PASS
node_count = 22
edge_count = 22
order_row_count = 22
coverage_node_count = 22
query_node_count = 22
check_count = 22
fail_count = 0
```

Current authority split remains unchanged:

```text
accepted = 5
candidate = 17
```

## 5. Schema-compatible Source Roles

The current `grammar_node.schema.json` permits these source roles in `source_evidence`:

```text
authority_source
normalized_authority_artifact
candidate_evidence
learner_facing_source
```

R7-M2 policy use:

```text
authority_source:
  allowed for high-value direct external authority evidence.

normalized_authority_artifact:
  preferred when evidence has been normalized into project-controlled static artifacts.

candidate_evidence:
  allowed for planning and draft implementation only; cannot promote accepted authority.

learner_facing_source:
  disallowed as a primary authority source for B1 / B1_PLUS promotion; may only support later example-surface analysis with blocked learner_state_write / automatic_promotion.
```

## 6. Allowed Evidence Source Classes

Future B1 / B1_PLUS candidate records may be supported by these source classes:

```text
CLASS-A: External authority source
Role: authority_source
Use: CEFR / EGP level alignment and grammar construct reference.
Minimum requirement: stable source_id, non-empty source_ref, CEFR level, allowed_use includes level_alignment and grammar_construct_reference.

CLASS-B: Project-normalized authority artifact
Role: normalized_authority_artifact
Use: preferred source for implementation batches after source extraction / normalization.
Minimum requirement: normalized artifact path, row/key reference, CEFR level, allowed_use includes level_alignment and grammar_construct_reference.

CLASS-C: Operator planning document
Role: candidate_evidence
Use: planning-only support for proposed grammar surface before implementation.
Minimum requirement: task doc path and section reference, confidence = operator_review_required.

CLASS-D: Learner-facing source
Role: learner_facing_source
Use: example-surface and later practice-shape analysis only.
Minimum requirement: blocked_use must include learner_state_write and automatic_promotion.
Promotion use: forbidden.
```

## 7. Blocked Evidence Uses

```text
[BLOCKED] AI suggestion alone cannot promote a B1 / B1_PLUS record to accepted.
[BLOCKED] R7-M1 planning proposal alone cannot promote a B1 / B1_PLUS record to accepted.
[BLOCKED] Learner-facing examples alone cannot promote a B1 / B1_PLUS record to accepted.
[BLOCKED] Unreviewed generated examples cannot be authority evidence.
[BLOCKED] A B1 / B1_PLUS implementation batch cannot use missing or empty source_ref.
[BLOCKED] No evidence source may write learner state.
[BLOCKED] No evidence source may enable automatic promotion.
```

## 8. Allowed `allowed_use` Values

The node schema permits these `allowed_use` values:

```text
level_alignment
grammar_construct_reference
example_sentence_evidence
stage_reference
validation_reference
```

R7-M2 minimum for future B1 / B1_PLUS candidate node implementation:

```text
required allowed_use:
- level_alignment
- grammar_construct_reference

optional allowed_use:
- stage_reference
- validation_reference
- example_sentence_evidence
```

`example_sentence_evidence` cannot be the only evidence type for authority promotion.

## 9. Required `blocked_use` Values

Future B1 / B1_PLUS candidate records must include blocked-use protection:

```text
required blocked_use:
- learner_state_write
- automatic_promotion

recommended blocked_use:
- direct_teaching_order
- learner_facing_full_text
```

Reason:

```text
CEFR / EGP evidence can support construct existence and level alignment, but it must not directly control internal teaching order or learner-facing generation.
```

## 10. Evidence Requirements Per R7-M1 Proposal

The following table assigns required evidence class before future implementation. This is policy-only; it does not create source-artifact records.

| Proposed grammar_id | Tentative stage | Required minimum source class | Secondary source class | Implementation readiness |
|---|---:|---|---|---|
| `GRAMMAR_PRESENT_PERFECT_EXPERIENCE_BASIC` | B1 | CLASS-A or CLASS-B | CLASS-C | blocked until evidence attached |
| `GRAMMAR_PRESENT_PERFECT_RESULT_BASIC` | B1 | CLASS-A or CLASS-B | CLASS-C | blocked until evidence attached |
| `GRAMMAR_PAST_CONTINUOUS_BASIC` | B1 | CLASS-A or CLASS-B | CLASS-C | blocked until evidence attached |
| `GRAMMAR_FIRST_CONDITIONAL_BASIC` | B1 | CLASS-A or CLASS-B | CLASS-C | blocked until evidence attached |
| `GRAMMAR_RELATIVE_CLAUSES_BASIC` | B1 | CLASS-A or CLASS-B | CLASS-C | blocked until evidence attached |
| `GRAMMAR_PASSIVE_PRESENT_PAST_BASIC` | B1 | CLASS-A or CLASS-B | CLASS-C | blocked until evidence attached |
| `GRAMMAR_REPORTED_SPEECH_BASIC` | B1_PLUS | CLASS-A or CLASS-B | CLASS-C | blocked until evidence attached |
| `GRAMMAR_SECOND_CONDITIONAL_BASIC` | B1_PLUS | CLASS-A or CLASS-B | CLASS-C | blocked until evidence attached |
| `GRAMMAR_MODAL_DEDUCTION_BASIC` | B1_PLUS | CLASS-A or CLASS-B | CLASS-C | blocked until evidence attached |
| `GRAMMAR_PRESENT_PERFECT_CONTINUOUS_BASIC` | B1_PLUS | CLASS-A or CLASS-B | CLASS-C | blocked until evidence attached |

## 11. Future Implementation Readiness Gate

A future source-artifact implementation batch is allowed only after a separate readiness task confirms:

```text
[ ] Each proposed node has source_id.
[ ] Each proposed node has non-empty source_ref.
[ ] Each proposed node has CEFR level evidence.
[ ] Each proposed node has schema-compatible source_role.
[ ] Each proposed node has required allowed_use.
[ ] Each proposed node has required blocked_use.
[ ] Each proposed node keeps authority_status = candidate.
[ ] Each proposed node keeps confidence = operator_review_required unless normalized authority evidence is reviewed.
[ ] Each proposed node keeps traceability.generated_content=false.
[ ] Each proposed node keeps traceability.learner_state_write=false.
```

## 12. Promotion Boundary

R7-M2 does not permit accepted authority promotion.

```text
planning source policy -> allowed
candidate source-artifact implementation -> requires later approved implementation batch
accepted authority promotion -> requires later promotion audit
learner-facing practice use -> not allowed from this task
```

A later promotion audit must prove:

```text
- evidence source role is authority_source or normalized_authority_artifact
- source evidence is reviewed and non-empty
- schema validation passes
- dependency edges resolve
- derived artifacts rebuild cleanly
- validation report fail_count = 0
- CI-safe pytest passes
- no learner-facing practice used the record before promotion
```

## 13. Risk Register

```text
RISK-1: Source-role mismatch
Status: OPEN
Impact: Medium
Control: R7-M2 uses only schema-compatible source roles.

RISK-2: Evidence too weak for promotion
Status: OPEN
Impact: Medium / High
Control: candidate implementation and accepted promotion are separated.

RISK-3: Learner-facing leakage
Status: OPEN
Impact: High
Control: learner_facing_source cannot be primary authority evidence and learner_state_write remains blocked.

RISK-4: Scope creep into B2
Status: OPEN
Impact: Medium
Control: R7-M2 is B1 / B1_PLUS only; B2 remains outside this task.
```

## 14. Gate & Distance Update

```text
[PASS] R7-M2 remains policy-only.
[PASS] No grammar_nodes.json changes.
[PASS] No grammar_edges.json changes.
[PASS] No derived artifact rebuild.
[PASS] No validation report refresh.
[PASS] No CI test change.
[PASS] No learner-facing practice generated.
[PASS] No learner state write path introduced.
[PASS] Source roles are aligned to current grammar_node schema.
[PASS] Future implementation is blocked until evidence attachment and readiness gate.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

## 15. Next Shortest Step

```text
NEXT_SHORT_STEP:
R7-M3 B1 / B1_PLUS candidate implementation readiness checklist
```

R7-M3 must remain checklist-only. It should verify whether the R7-M1 proposals plus R7-M2 evidence policy are sufficient to permit a later capped candidate node implementation batch. It must not modify `grammar_nodes.json` or `grammar_edges.json`.

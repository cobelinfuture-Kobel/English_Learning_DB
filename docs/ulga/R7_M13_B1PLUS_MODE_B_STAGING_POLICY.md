# R7-M13 B1_PLUS Mode-B Staging Policy

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M13 B1_PLUS staging policy selection

Branch:
codex/r7-m13-b1plus-mode-b-policy

Status:
POLICY_ONLY
```

R7-M13 records the operator-selected B1_PLUS staging policy after R7-M12 stopped with `HUMAN_STAGE_POLICY_REQUIRED`.

## 2. Operator Selection

```text
SELECTED_MODE = MODE-B
B1_PLUS = bridge from B1 to B2 preview
```

B1_PLUS is not a direct repeat of B1 and not full B2 implementation. It is a controlled bridge layer that keeps B1 as the stable base while allowing limited B2-preview direction.

## 3. Policy Definition

B1_PLUS records must satisfy all of the following:

```text
- introduced_stage = B1_PLUS
- authority_status = candidate
- learner_state_write = false
- generated_content = false
- no accepted promotion
- no learner-facing practice generation
- source evidence must support either advanced B1 use or early B2-preview direction
```

B1_PLUS may include:

```text
- B1 constructs with increased clause complexity
- B1 constructs extended toward B2 form or use
- bridge nodes that prepare learners for B2 without claiming B2 mastery
```

B1_PLUS must not include:

```text
- plain B1 basics already closed in the corrected B1 graph
- A2-backed basic constructs relabeled upward
- full B2 authority implementation
- learner-facing generated items
- learner state writes
```

## 4. Next Planning Surface Rule

The next B1_PLUS planning surface must be candidate-only and must prefer bridge-style grammar constructs. Candidate proposals should use one of these bridge roles:

```text
BRIDGE_ROLE_ADVANCED_B1_CONTROL
BRIDGE_ROLE_B2_PREVIEW_FORM
BRIDGE_ROLE_B2_PREVIEW_USE
BRIDGE_ROLE_CLAUSE_COMPLEXITY_EXTENSION
```

Each future proposal must identify whether it extends an existing B1 node, previews a B2 direction, or does both.

## 5. Readiness Decision

```text
R7-M13_POLICY_DECISION = MODE_B_SELECTED
B1_PLUS_STAGING_POLICY = DEFINED_AS_B1_TO_B2_BRIDGE
B1_PLUS_IMPLEMENTATION_READINESS = NOT_READY_PLANNING_SURFACE_REQUIRED
```

Reason:

```text
The staging policy is now selected, but no new B1_PLUS candidate surface has been defined under this Mode-B policy yet.
```

## 6. Scope Confirmation

```text
No grammar_nodes.json modification.
No grammar_edges.json modification.
No derived artifact rebuild.
No validation report refresh.
No CI test change.
No learner-facing practice generation.
No learner state write.
No accepted authority promotion.
No B2 implementation.
```

## 7. Gate & Distance Update

```text
[PASS] R7-M13 records operator-selected Mode-B.
[PASS] B1_PLUS is defined as B1-to-B2 bridge.
[PASS] B1 graph remains closed as static-candidate-ready.
[PASS] B1_PLUS implementation remains blocked until a new candidate surface exists.
[PASS] No grammar source artifact modified.
[PASS] No derived artifact rebuilt.
[PASS] No CI expectation changed.
[PASS] No learner-facing practice generated.
[PASS] No learner state write path introduced.
[NOT_CHECKED] GitHub Actions CI readback was not available at file creation time.
```

```text
ENGLISH_GRAMMAR_STATUS = PASS_LOCAL_ONLY_CI_NOT_VERIFIED
```

## 8. Next Shortest Step

```text
NEXT_SHORT_STEP:
R7-M14 B1_PLUS Mode-B candidate planning surface definition
```

R7-M14 must remain planning-only. It should propose a capped B1_PLUS candidate surface under Mode-B and must not modify `grammar_nodes.json` or `grammar_edges.json`.

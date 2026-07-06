# R7-M13 B1_PLUS Mode-B Staging Policy

## 1. Current State

```text
Epic ID:
R7_B1_B2_CandidateOnly_Planning

Sub-task ID:
R7-M13 B1_PLUS staging policy selection

Selected mode:
MODE-B = B1_PLUS as bridge from B1 to B2 preview

Branch:
codex/r7-m13-b1plus-modeb-policy

Status:
STAGING_POLICY_ONLY
```

R7-M13 records the operator-approved B1_PLUS staging policy after R7-M12 stopped at `HUMAN_STAGE_POLICY_REQUIRED`.

## 2. Prior State

```text
R7_CORRECTED_B1_GRAPH_LINE = CLOSED_AS_STATIC_CANDIDATE_GRAPH_READY
B1_PLUS_IMPLEMENTATION_READINESS = NOT_READY
R7-M12_STOP_DECISION = HUMAN_STAGE_POLICY_REQUIRED
```

## 3. Policy Decision

```text
B1_PLUS_STAGING_POLICY = MODE_B_BRIDGE_FROM_B1_TO_B2_PREVIEW
```

Definition:

```text
B1_PLUS is a bridge layer. It must extend stable B1 control toward B2-like complexity without treating B2 preview items as accepted B2 mastery.
```

B1_PLUS is therefore not:

```text
- deeper B1 consolidation only
- direct B2 implementation
- B2-backed early-preview only
- a replacement for B2 planning
```

## 4. Allowed B1_PLUS Candidate Surface

A future B1_PLUS planning surface may include items that meet all of the following:

```text
[1] Builds on an existing B1 node or B1 dependency path.
[2] Adds one controlled complexity step toward B2 behavior.
[3] Has concrete EGP source_ref evidence at B1, B2, or a clearly justified bridge row.
[4] Keeps authority_status = candidate.
[5] Keeps confidence = operator_review_required unless separately reviewed.
[6] Does not write learner state.
[7] Does not generate learner-facing practice.
```

## 5. Disallowed B1_PLUS Surface

```text
- Reusing old R7-M1 B1_PLUS labels without source-ref recheck.
- Re-promoting basic B1 items as B1_PLUS.
- Re-promoting A2-backed basic items as B1_PLUS.
- Treating preview as mastery.
- Implementing B2 nodes under a B1_PLUS label.
- Accepted authority promotion.
```

## 6. Candidate Planning Direction

The next B1_PLUS task should be planning-only and should rebuild a new B1_PLUS candidate surface under Mode-B.

Recommended candidate families:

```text
- expanded reported speech beyond basic statements
- conditional complexity beyond basic first/second conditional
- passive expansion beyond present/past affirmative core
- relative clause expansion beyond place/time/object basics
- modal nuance beyond must-deduction basics
- perfect aspect contrast and discourse use beyond B1 anchors
```

These are not approved nodes. They are only surface families for the next planning scan.

## 7. Scope Confirmation

```text
No grammar_nodes.json modification.
No grammar_edges.json modification.
No derived artifact rebuild.
No validation report refresh.
No CI expectation change.
No learner-facing practice generation.
No learner state write.
No accepted authority promotion.
No B2 implementation.
```

## 8. Gate & Distance Update

```text
[PASS] Operator selected MODE-B.
[PASS] B1_PLUS now has a staging policy.
[PASS] Corrected B1 graph remains closed as static-candidate-ready.
[PASS] B1_PLUS remains planning-only.
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

## 9. Next Shortest Step

```text
NEXT_SHORT_STEP:
R7-M14 B1_PLUS Mode-B candidate surface planning scan
```

R7-M14 must remain planning-only. It may propose a capped B1_PLUS candidate surface under Mode-B, but it must not modify `grammar_nodes.json` or `grammar_edges.json`.

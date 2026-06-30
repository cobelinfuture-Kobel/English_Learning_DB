# ULGA-S8G Learning Signal QA Audit

## Executive Summary

QA result: **PASS WITH WARNINGS**.

The S8F Learning Signal Contract is structurally usable and aligned with S8E's core safety requirements:

- `Knowledge Edge != Learning Signal` is preserved.
- All required signal types are present.
- All known source relations are mapped.
- Gate eligibility is restricted to `REQUIRES` and conditional hard `prerequisite`.
- Theme Spiral relations cannot gate.
- `GATE_SIGNAL` is blocking-only and has numeric planner weight `0.0`.
- Confidence caps are present and prevent `heuristic` or `manual_review_required` from gating.

No critical findings were found. Two non-blocking warnings were identified:

1. `signal_record_schema` exists in the schema but is not top-level required.
2. The schema allows flexible `signal_weight_ranges` and `confidence_caps`; the policy is complete, but the schema itself does not require every expected key.

Final recommendation: **GO for S8C DependencyEdgeBuilder planning and Theme Spiral builder planning, with one recommended pre-builder hardening task to make the future validator enforce the two warning areas.**

## Files Audited

- `ulga/schema/learning_signal_contract.schema.json`
- `ulga/schema/learning_signal_policy.json`
- `docs/ulga/ULGA_S8F_LEARNING_SIGNAL_CONTRACT_CLOSEOUT.md`
- `docs/ulga/ULGA_S8A_DEPENDENCY_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S8B_THEME_SPIRAL_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S8E_LEARNING_SIGNAL_CLASSIFICATION_DESIGN_SCAN.md`

Validation performed:

- JSON parse for schema and policy.
- Required top-level key check.
- Signal enum and source relation enum coverage check.
- Mapping coverage and duplicate mapping check.
- Gate safety rule check.
- Confidence cap and blocked confidence method check.
- Planner blocking and weak-signal override check.
- Learner State safety notes check.
- Closeout consistency spot check.

No files were modified during this QA.

## Schema QA

| Check | Result | Notes |
|---|---|---|
| JSON parse: `learning_signal_contract.schema.json` | PASS | JSON parses successfully. |
| JSON parse: `learning_signal_policy.json` | PASS | JSON parses successfully. |
| Required top-level fields | PASS | `contract_metadata`, `signal_types`, `signal_mapping_rules`, `signal_weight_policy`, `validation_policy`, `consumer_policy` are required. |
| Signal type enum completeness | PASS | All 7 signal types are present. |
| Source relation enum completeness | PASS | All 14 known source relations are present. |
| Confidence enum coverage | PASS | `authoritative`, `derived`, `heuristic`, `manual_review_required` are present. |
| Review status enum coverage | PASS | `accepted`, `needs_review`, `blocked`, `deprecated` are present. |
| Signal record schema presence | WARNING | `signal_record_schema` exists as a schema property but is not top-level required. This is not blocking because S8F top-level requirements did not explicitly require it, but future QA/validator should enforce it if signal artifacts depend on it. |
| Weight/cap completeness enforcement | WARNING | Policy contains complete ranges and caps, but schema allows arbitrary `signal_weight_ranges` and `confidence_caps` keys. Future validator should require exact key coverage. |

Schema QA result: **PASS WITH WARNINGS**.

## Mapping QA

Known relation coverage:

| Relation | Mapping present | Duplicate | Conflict |
|---|---|---|---|
| `REQUIRES` | PASS | No | No |
| `EXPANDS` | PASS | No | No |
| `REINFORCES` | PASS | No | No |
| `PRECEDES` | PASS | No | No |
| `SPIRAL_TO` | PASS | No | No |
| `INTRODUCES` | PASS | No | No |
| `BROADENS_TO` | PASS | No | No |
| `CONTRASTS_WITH` | PASS | No | No |
| `USES` | PASS | No | No |
| `BELONGS_TO` | PASS | No | No |
| `supports` | PASS | No | No |
| `reviews` | PASS | No | No |
| `prerequisite` | PASS | No | No |
| `contrasts_with` | PASS | No | No |

Mapping QA result: **PASS**.

No missing mappings, duplicate mappings, or direct mapping conflicts were detected.

## Gate Safety QA

Gate policy checks:

| Check | Result | Notes |
|---|---|---|
| Only `REQUIRES` and `prerequisite` have `gate_allowed=true` | PASS | Policy restricts gate-allowed relations correctly. |
| `prerequisite` requires hard-prerequisite metadata or accepted equivalent | PASS | `requires_metadata` includes `metadata.dependency_class=hard_prerequisite or policy accepted equivalent`. |
| `SPIRAL_TO` cannot gate | PASS | `gate_allowed=false`; also blocked in validation policy. |
| `BELONGS_TO` cannot gate | PASS | `gate_allowed=false`; also blocked in theme gate misuse policy. |
| `USES` cannot gate by default | PASS | `gate_allowed=false`; manual review required for any future gate promotion. |
| `supports` cannot gate | PASS | `gate_allowed=false`. |
| `reviews` cannot gate | PASS | `gate_allowed=false`. |
| `INTRODUCES` cannot gate | PASS | `gate_allowed=false`; theme gate misuse policy blocks it. |
| `BROADENS_TO` cannot gate | PASS | `gate_allowed=false`; theme gate misuse policy blocks it. |
| `CONTRASTS_WITH` cannot gate | PASS | `gate_allowed=false`. |

Gate Safety QA result: **PASS**.

## Confidence Safety QA

Confidence caps:

| Confidence method | Required cap | Actual cap | Result |
|---|---:|---:|---|
| `authoritative` | `<= 1.00` | `1.00` | PASS |
| `derived` | `<= 0.75` | `0.75` | PASS |
| `heuristic` | `<= 0.35` | `0.35` | PASS |
| `manual_review_required` | `= 0.00` | `0.00` | PASS |

Gate confidence validation:

| Check | Result | Notes |
|---|---|---|
| `gate_eligible + heuristic` blocked | PASS | `heuristic` appears in `blocked_confidence_methods`. |
| `gate_eligible + manual_review_required` blocked | PASS | `manual_review_required` appears in `blocked_confidence_methods`. |
| Gate requires accepted review status | PASS | `required_review_status=accepted`. |
| Gate requires `GATE_SIGNAL` | PASS | `required_signal_type=GATE_SIGNAL`. |

Confidence Safety QA result: **PASS**.

## Planner Safety QA

Planner safety checks:

| Check | Result | Notes |
|---|---|---|
| `GATE_SIGNAL` is blocking-only | PASS | `mode=blocking`. |
| `GATE_SIGNAL` numeric planner range is zero | PASS | `min=0.0`, `max=0.0`. |
| Weak signals cannot override gate | PASS | `weak_signal_stack_cannot_override_gate=true`. |
| Manual review signals have zero weight | PASS | `manual_review_required_weight=0.0`. |
| Heuristic gate weight is zero | PASS | `heuristic_gate_weight=0.0`. |
| Antigravity Planner applies gates before ranking | PASS | Consumer policy includes "Apply gate exclusions before ranking." |

Planner Safety QA result: **PASS**.

Recommendation signals cannot override a gate under the current policy.

## Theme Spiral Safety QA

Theme Spiral safety checks:

| Relation | Gate allowed | Result |
|---|---:|---|
| `SPIRAL_TO` | false | PASS |
| `INTRODUCES` | false | PASS |
| `BROADENS_TO` | false | PASS |
| `BELONGS_TO` | false | PASS |

Additional checks:

- `theme_gate_misuse.blocked_relations` includes `SPIRAL_TO`, `INTRODUCES`, `BROADENS_TO`, and `BELONGS_TO`.
- S8B says Theme Spiral must not block learners.
- S8F policy preserves that isolation.
- Dependency Authority remains the only path to hard gate semantics through `REQUIRES` or accepted hard `prerequisite`.

Theme Spiral Safety QA result: **PASS**.

## Learner State Safety QA

Learner State safety checks:

| Check | Result | Notes |
|---|---|---|
| Coverage Signal is not Mastery | PASS | Learner State policy says coverage and context track exposure, not mastery. |
| Context Signal is not Readiness | PASS | Context is exposure/context tracking, not prerequisite readiness. |
| `REINFORCES` is not mastery proof | PASS | Policy says reinforcement requires learner performance evidence before increasing mastery strongly. |
| Assessment maps performance to mastery | PASS | Assessment policy says static signals alone are not performance evidence. |

Learner State Safety QA result: **PASS**.

## Consistency QA

Schema, policy, and closeout consistency:

| Area | Result | Notes |
|---|---|---|
| Files created list | PASS | Closeout matches actual S8F artifact names. |
| Signal type list | PASS | Schema and policy both contain the 7 S8E signal types. |
| Source relation list | PASS | Schema and policy cover all required S8E relations. |
| Gate policy | PASS | Schema/policy/closeout all agree that only `GATE_SIGNAL` can gate. |
| Non-gating relations | PASS | Policy and closeout both block Theme Spiral, membership, review, support, uses, and contrast relations from default gates. |
| Weight policy | PASS | Policy and closeout ranges match. |
| Confidence caps | PASS | Policy and closeout caps match. |
| Validation policy | PASS | Closeout lists the same future validator areas found in policy. |
| Consumer policy | WARNING | Policy is more specific than closeout. Closeout summarizes Reading and Dialogue consumers broadly; policy correctly distinguishes Dialogue as consuming `RECOMMENDATION_SIGNAL` and `DIAGNOSTIC_SIGNAL`, not `MASTERY_SIGNAL` or `COVERAGE_SIGNAL` directly. This is documentation precision only, not a contract blocker. |
| Schema strictness | WARNING | Schema validates shape but does not force exact completeness for weight/cap keys. Policy itself is complete. |

Consistency QA result: **PASS WITH WARNINGS**.

## Builder Readiness Assessment

### DependencyEdgeBuilder Readiness

Status: **READY WITH GUARDRAILS**.

Ready:

- Gate-eligible relations are defined.
- `REQUIRES` and hard `prerequisite` policy is explicit.
- `supports`, `reviews`, `USES`, `BELONGS_TO`, and contrast relations are protected from accidental gates.
- Confidence and review-status rules are defined.
- Circular gate chain detection is specified as future validation scope.

Still needed:

- A concrete builder must inspect source metadata, especially `metadata.dependency_class=hard_prerequisite`.
- Builder must not infer `GATE_SIGNAL` from CEFR alone.
- Builder must output review queues for any ambiguous `USES` or physical `prerequisite` edge.

### Theme Spiral Builder Readiness

Status: **READY WITH GUARDRAILS**.

Ready:

- `SPIRAL_TO`, `INTRODUCES`, `BROADENS_TO`, and `BELONGS_TO` are explicitly non-gating.
- Theme gate misuse rules are encoded.
- Planner, coverage, review, and context usage are available.

Still needed:

- Builder must keep Theme Spiral output separate from Dependency Authority.
- Builder must not create `GATE_SIGNAL` from Theme Spiral.
- Builder should report large CEFR jumps and cross-theme chain anomalies to a review queue.

### Learner State Readiness

Status: **PARTIAL**.

Ready:

- Signal taxonomy separates readiness, mastery, review, coverage, context, and diagnostics.
- Learner State consumer policy is defined.

Still needed:

- S9A must define learner performance evidence shape.
- Static `MASTERY_SIGNAL` cannot update mastery without assessment/activity evidence.

## Risk Register

| Risk | Severity | Status | Notes |
|---|---|---|---|
| Theme Spiral converted into hard gates | High | Controlled | Policy blocks `SPIRAL_TO`, `INTRODUCES`, `BROADENS_TO`, and `BELONGS_TO` from gating. |
| `USES` edge promoted to gate automatically | High | Controlled | `USES` is non-gating by default and requires manual review for future gate promotion. |
| Physical `prerequisite` edge overgates soft prerequisites | High | Controlled | Requires hard-prerequisite metadata or policy-accepted equivalent. |
| Heuristic/manual-review signals gate content | High | Controlled | Both methods are blocked for gate confidence. |
| Weak recommendation overrides a gate | High | Controlled | Aggregation policy blocks weak signal stacks from overriding gates. |
| Coverage treated as mastery | Medium | Controlled | Learner State notes separate exposure from mastery. |
| Context treated as readiness | Medium | Controlled | Context is not a gate or readiness signal. |
| Schema does not enforce exact weight/cap key completeness | Medium | Warning | Policy is complete; future validator should enforce exact keys. |
| Closeout consumer summary is broader than policy | Low | Warning | Documentation precision issue only. |

## Final Recommendation

QA result: **PASS WITH WARNINGS**.

Go / No-Go recommendation: **GO** for controlled builder planning.

Recommended next step:

`ULGA-S8C_DependencyEdgeBuilder`

Builder entry conditions:

- Use S8F policy as read-only contract input.
- Emit review queues for ambiguous gate candidates.
- Do not generate gates from Theme Spiral, CEFR-only evidence, `BELONGS_TO`, `supports`, `reviews`, or unreviewed `USES`.
- Apply gate exclusions before planner ranking in any future planner integration.

Recommended follow-up hardening before full runtime use:

- Future S8G/S8H validator should enforce exact weight/cap key completeness.
- Future closeout or docs update should make consumer summaries as precise as `learning_signal_policy.json`.

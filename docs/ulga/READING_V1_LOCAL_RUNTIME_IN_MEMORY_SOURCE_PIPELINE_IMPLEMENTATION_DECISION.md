# ReadingV1 Local Runtime In-Memory Source Pipeline Implementation Decision

Task:
ReadingV1_LocalRuntimeInMemorySourcePipeline_Implementation_Decision

Scope:
Decide whether the P1 design-only local source pipeline may proceed to a future implementation task.

Current P1 status:

```text
ReadingV1_P1_STATUS = PASS_WITH_WARNINGS_FOUNDATION_READY
ReadingV1_P1_LOCAL_STATUS = PASS_LOCAL_SYNCED
ReadingV1_P1_CI_STATUS = PASS_CI_SYNCED_BY_OPERATOR_SCREENSHOT
```

---

## 1. Decision

```text
DECISION = APPROVE_DESIGN_TO_IMPLEMENTATION_HANDOFF
```

Meaning:
The local runtime source pipeline may be planned as a future implementation task, but this task does not implement it.

---

## 2. Allowed Future Implementation Shape

A future implementation may:

```text
read already-authorized local candidate source units
resolve source_unit_id to private homework display payloads
keep processing in memory by default
feed PracticeBank / Overlay / OutputGate inputs
return structured in-memory objects for tests
```

A future implementation must not:

```text
persist copied source material
write learner HTML files by default
publish public output
promote authority status
connect learner state
start P2 assessment generation
```

---

## 3. Required Future Gate

Before implementation, create a separate task:

```text
ReadingV1_LocalRuntimeInMemorySourcePipeline_Implementation
```

That task must include:

```text
schema or typed contract
builder or resolver module
unit tests
readback document
no public export
no source text persistence unless separately approved
```

---

## 4. Risk Result

```text
risk_level = MEDIUM
reason = source resolution touches content persistence boundaries
```

Mitigation:

```text
in-memory only
private-homework only
reference display only
OutputGate remains final blocker
```

---

## 5. Status

```text
ReadingV1_LocalRuntimeInMemorySourcePipeline_Implementation_Decision -> COMPLETED_APPROVED_FOR_FUTURE_IMPLEMENTATION_PLANNING
```

Next approved task:

```text
ReadingV1_ReviewedDisplaySnippetPolicy_DesignScan
```

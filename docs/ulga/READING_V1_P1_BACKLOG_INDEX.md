# ReadingV1 P1 Backlog Index

Task:
ReadingV1_P1_Backlog_Index

Scope:
Record the remaining safe P1 cleanup backlog after final P1 foundation closeout.

Current status:

```text
ReadingV1_P1_STATUS = PASS_WITH_WARNINGS_FOUNDATION_READY
ReadingV1_P1_LOCAL_STATUS = PASS_LOCAL_SYNCED
ReadingV1_P1_CI_STATUS = PASS_CI_SYNCED_BY_OPERATOR_SCREENSHOT
```

Boundary:

```text
P1 cleanup only
no P2 start
no public export
no production deployment
no authority promotion
no learner-state integration
```

---

## 1. Safe P1 Cleanup Backlog

### B1 Operator Review Checklist

Status:
NOT_STARTED

Purpose:
Create a checklist for human review before any post-P1 work.

Recommended task:

```text
ReadingV1_P1_Operator_Review_Checklist
```

### B2 Local Runtime Resolver Implementation Decision

Status:
DEFERRED

Purpose:
Decide whether P1-M6 design-only resolver should become runtime code.

Requires operator approval:
yes

Recommended task:

```text
ReadingV1_LocalRuntimeInMemorySourcePipeline_Implementation_Decision
```

### B3 Reviewed Display Snippet Policy

Status:
DEFERRED

Purpose:
Decide if short reviewed display snippets may be persisted under private homework policy.

Requires operator approval:
yes

Recommended task:

```text
ReadingV1_ReviewedDisplaySnippetPolicy_DesignScan
```

### B4 P1 Documentation Consistency Sweep

Status:
OPTIONAL

Purpose:
Check whether P1 documents use consistent status names and boundaries.

Recommended task:

```text
ReadingV1_P1_Documentation_Consistency_Sweep
```

### B5 P2 Entry Gate

Status:
BLOCKED_UNTIL_APPROVED

Purpose:
Define what must be true before P2 assessment expansion begins.

Requires operator approval:
yes

Recommended task:

```text
ReadingV1_P2_Entry_Gate_DesignScan
```

---

## 2. Do Not Do Automatically

```text
Do not start P2.
Do not add assessment expansion.
Do not add public output.
Do not add production deployment.
Do not add learner-state integration.
Do not promote authority status.
```

---

## 3. Recommended Next Step

```text
ReadingV1_P1_Operator_Review_Checklist
```

Task status:

```text
ReadingV1_P1_Backlog_Index -> COMPLETED
```

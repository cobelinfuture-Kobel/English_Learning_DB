# ReadingV1 Reviewed Display Snippet Policy Design Scan

Task:
ReadingV1_ReviewedDisplaySnippetPolicy_DesignScan

Scope:
Define the policy boundary for small operator-reviewed display snippets in ReadingV1 private homework flow.

Current P1 status:

```text
ReadingV1_P1_STATUS = PASS_WITH_WARNINGS_FOUNDATION_READY
```

---

## 1. Policy Decision

```text
reviewed_display_snippet_policy_status = DESIGN_ACCEPTED_WITH_GUARDS
```

Meaning:
Reviewed display snippets may be designed as a future private-homework support layer, but they are not automatically persisted by P1.

---

## 2. Allowed Concept

A reviewed display snippet is:

```text
a short learner-facing display unit
operator-reviewed
private-homework only
used to support a question prompt or answer choice
not treated as source authority
not treated as public material
```

---

## 3. Required Guards

Future implementation must keep these guards:

```text
private_homework_only = true
public_ready = false
commercial_distribution_allowed = false
authority_status = candidate_only
promotion_status = not_promoted
```

The snippet must not expose:

```text
answer key
validator internals
source locator details
copyright-sensitive source payload
promotion metadata
```

---

## 4. Persistence Rule

Default:

```text
reviewed_display_snippet_persistence = blocked
```

Allowed only after separate approval:

```text
operator_reviewed_micro_display_payload
short display-only text
private homework package only
traceable review metadata
no public export
```

---

## 5. Relationship to Source Pipeline

The source pipeline may create display payloads in memory.
Persistence of reviewed snippets requires a separate policy implementation gate.

Recommended future task:

```text
ReadingV1_ReviewedDisplaySnippetPolicy_Implementation_Gate
```

---

## 6. Result

```text
ReadingV1_ReviewedDisplaySnippetPolicy_DesignScan -> COMPLETED_WITH_GUARDS
```

Next approved task:

```text
ReadingV1_P2_Entry_Gate_DesignScan
```

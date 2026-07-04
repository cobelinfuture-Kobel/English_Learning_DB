# RAZ Private Homework Use Policy Design Scan

## 1. Current State

```text
Project: English_Learning_DB / E4S Reading V1 follow-up
Task: RAZ_PrivateHomeworkUsePolicy_DesignScan
Deliverable: docs/ulga/RAZ_PRIVATE_HOMEWORK_USE_POLICY_DESIGN_SCAN.md
Task type: Policy DesignScan
```

This document defines a narrow private-homework policy lane for RAZ-related Reading V1 work. It is not a public display approval, not a commercial worksheet approval, not a GitHub Pages approval, not a bulk RAZ text database approval, and not a learner-facing output implementation.

This task does not copy RAZ source text, does not create HTML, does not create worksheet output, does not create public preview, does not create learner state, does not create adaptive recommendation, and does not promote source/content authority.

Current baseline before this task:

```text
RAZ source payload display = blocked
RAZ evidence text display = blocked
Reading V1 learner-facing output = blocked
manual review decisions = completed but all need revision
next_gate_eligible_count = 0
```

---

## 2. Operator Constraint

Operator-provided intended use:

```text
use_scope = homework_only
repository_visibility = private
public_site_expected = false
commercial_distribution_expected = false
```

Interpretation:

```text
Private homework use can be treated differently from public learner-facing output, but it still must be gated. Private repository visibility lowers distribution risk but does not automatically authorize bulk copying, public display, public preview, commercial worksheet use, or GitHub Pages deployment.
```

---

## 3. Policy Decision

The project now distinguishes three lanes:

```text
LANE_A_INTERNAL_METADATA_ONLY
LANE_B_PRIVATE_HOMEWORK_LIMITED_USE
LANE_C_PUBLIC_OR_COMMERCIAL_OUTPUT
```

Policy decision:

| Lane | Status | Meaning |
|---|---:|---|
| `LANE_A_INTERNAL_METADATA_ONLY` | allowed | Existing internal review / locator / metadata use remains allowed. |
| `LANE_B_PRIVATE_HOMEWORK_LIMITED_USE` | conditionally allowed | Private, household-only homework output may be considered under strict controls. |
| `LANE_C_PUBLIC_OR_COMMERCIAL_OUTPUT` | blocked | Public site, GitHub Pages, public preview, sharing, resale, TPT/Etsy, or broad distribution remain blocked. |

---

## 4. What Private Homework Limited Use Allows

Conditionally allowed only when all conditions are true:

```text
repository is private
output is generated for household homework only
output is not pushed to GitHub Pages
output is not distributed publicly
output is not sold or packaged commercially
output is not shared with other families/classes/teachers as a package
output is not used to replace a RAZ subscription or access right
source attribution/locator is preserved internally
operator has lawful access to the source for household use
storage is limited and task-scoped, not a bulk corpus dump
```

Allowed artifact classes under this lane:

| Artifact | Private homework lane status | Notes |
|---|---:|---|
| RAZ locator / book id / level / page ref | allowed | Preferred durable storage format. |
| RAZ metadata / source family / topic tag | allowed | Internal use only. |
| Human notes about a RAZ source | allowed | Must not reconstruct full source text. |
| Very small task-scoped excerpt | conditional | Only if operator confirms lawful access and scope is household homework. |
| Full RAZ passage text | blocked by default | Requires separate explicit confirmation and should not become bulk DB. |
| Bulk RAZ passage database | blocked | Not allowed in this project lane. |
| Private local print HTML | conditional future | Requires separate implementation gate. |
| Private worksheet export | conditional future | Requires separate implementation gate. |

---

## 5. What Remains Blocked

The following remain blocked even under private homework use:

```text
public GitHub repository
GitHub Pages or public site export
public preview link
commercial worksheet package
TPT/Etsy/productized sale
bulk RAZ passage extraction
bulk RAZ text database
unbounded source payload storage
source/content authority promotion
learner state mutation
adaptive recommendation
sharing generated RAZ-derived package outside household
```

Hard boundary:

```text
Private homework lane is not public learner-facing output and is not product output.
```

---

## 6. GitHub Storage Policy

Because the repo is private, the project may store limited private-homework metadata and task-scoped records, but durable storage should prefer locator-first design.

Allowed in private repo:

```text
RAZ source locator
RAZ book id / level / page reference
homework task id
question type
operator note
review status
private_homework_scope flag
source access attestation flag
```

Conditionally allowed in private repo:

```text
small excerpt used only for a specific homework item
operator-created paraphrase or replacement text
private local print artifact manifest
```

Blocked in private repo:

```text
full RAZ corpus text
bulk passage payloads
full book text extraction
large source payload JSON
public-ready RAZ-derived worksheet bundle
assets intended for GitHub Pages
```

---

## 7. Required Fields for Future Private Homework Artifacts

Any future artifact that relies on this lane must include:

```text
use_scope = private_homework_only
repo_visibility_required = private
public_distribution_allowed = false
commercial_use_allowed = false
github_pages_allowed = false
bulk_source_payload_storage_allowed = false
source_payload_scope = none | small_task_scoped_excerpt | locator_only
operator_source_access_confirmed = true | false
source_locator_required = true
attribution_or_source_ref_required = true
learner_facing_context = household_homework_only
```

If source text is included, the artifact must also include:

```text
source_text_storage_reason
excerpt_length_policy_ref
source_access_basis
retention_policy
not_for_public_export = true
not_for_commercial_distribution = true
```

---

## 8. Validation Rules for Future Tasks

Future validators should block any artifact if:

```text
repo_visibility_required != private
public_distribution_allowed != false
commercial_use_allowed != false
github_pages_allowed != false
bulk_source_payload_storage_allowed != false
source_payload_scope = full_passage
source_payload_scope = bulk_corpus
operator_source_access_confirmed != true when source text is stored
source_locator_required != true
not_for_public_export != true when source text is stored
```

Future validators should warn if:

```text
source_payload_scope = small_task_scoped_excerpt
retention_policy is missing
excerpt length is not recorded
operator note is missing
review status is not recorded
```

---

## 9. Impact on Existing Reading V1 Artifacts

This policy does not automatically change the status of existing artifacts.

Existing `E4S_P1_READING_V1_SOURCE_PAYLOAD_DISPLAY_POLICY.md` remains valid for public/general output:

```text
RAZ source payload display = blocked
RAZ evidence text display = blocked
public/learner-facing display = blocked
```

Existing manual review decision summary remains valid:

```text
completed_decision_count = 3
needs_revision_count = 3
passed_internal_review_count = 0
next_gate_eligible_count = 0
source_payload_display_allowed = false
evidence_text_display_allowed = false
learner_facing_allowed = false
```

This policy only introduces a future private-homework lane that may be used by a separate implementation task.

---

## 10. What This Enables Later

This design scan allows a future task to be scoped as:

```text
ReadingV1_PrivateHomeworkHTMLExport_DesignScan
```

or:

```text
ReadingV1_PrivateHomeworkHTMLExport_Implementation
```

But only under these restrictions:

```text
private repo only
local/private output only
no GitHub Pages
no public preview
no commercial worksheet
no bulk RAZ text database
source locator required
limited task-scoped payload only if operator confirms lawful access
```

It does not enable:

```text
P1-S16 public/site HTML export
P1-S17 general worksheet export
public learner-facing Reading output
source payload display for public preview
commercial product output
```

---

## 11. Recommended Next Step

Recommended next task if the operator wants printable private homework output:

```text
ReadingV1_PrivateHomeworkHTMLExport_DesignScan
```

Purpose:

```text
Design a local/private printable HTML export path that consumes locator-first Reading V1 records and private-homework policy fields without creating public output, GitHub Pages output, commercial worksheet output, or bulk RAZ source storage.
```

Alternative if the operator wants no further expansion:

```text
STOP_READING_V1_FOLLOWUP
```

---

## 12. Acceptance Gates

| Gate | Result | Evidence |
|---|---:|---|
| Existing public/general RAZ block respected | PASS | Sections 1, 9 |
| Private homework lane separated from public output | PASS | Sections 2, 3 |
| GitHub private repo storage limits defined | PASS | Section 6 |
| Bulk source payload storage blocked | PASS | Sections 4, 5, 6 |
| Public/GitHub Pages/commercial output blocked | PASS | Sections 5, 10 |
| Future artifact required fields defined | PASS | Section 7 |
| Future validator rules defined | PASS | Section 8 |
| No HTML created | PASS | Documentation only |
| No worksheet created | PASS | Documentation only |
| No RAZ source text copied | PASS | Documentation only |
| No learner state/adaptive output created | PASS | Documentation only |
| No source/content authority promotion | PASS | Documentation only |

Result:

```text
ACCEPTANCE_GATES = PASS_WITH_WARNINGS
```

---

## 13. Known Warnings

```text
warning_id: RAZ-PHU-WARN-001
severity: medium
classification: PRIVATE_HOMEWORK_SCOPE_REQUIRES_OPERATOR_ATTESTATION
message: Any future task storing source text must require explicit operator confirmation of lawful access and household-only scope.
blocks_current_task: no
```

```text
warning_id: RAZ-PHU-WARN-002
severity: medium
classification: NO_OUTPUT_IMPLEMENTED
message: This design scan does not create private homework HTML, worksheet export, or printable files.
blocks_current_task: no
```

```text
warning_id: RAZ-PHU-WARN-003
severity: medium
classification: NO_TEST_RUN
message: Documentation-only design scan; no local tests or GitHub Actions CI were run.
blocks_current_task: no
```

---

## 14. Handoff Block

```text
CURRENT_TASK = RAZ_PrivateHomeworkUsePolicy_DesignScan
FILES_CREATED_OR_MODIFIED = docs/ulga/RAZ_PRIVATE_HOMEWORK_USE_POLICY_DESIGN_SCAN.md
ACCEPTANCE_GATES = PASS_WITH_WARNINGS
PUBLIC_RAZ_PAYLOAD_DISPLAY = BLOCKED
PRIVATE_HOMEWORK_RAZ_USE = CONDITIONALLY_ALLOWED
PRIVATE_REPO_REQUIRED = true
GITHUB_PAGES_ALLOWED = false
PUBLIC_PREVIEW_ALLOWED = false
COMMERCIAL_USE_ALLOWED = false
BULK_RAZ_TEXT_DATABASE_ALLOWED = false
LOCAL_PRIVATE_PRINT_HTML = FUTURE_CONDITIONAL_TASK_ONLY
NEXT_RECOMMENDED_TASK = ReadingV1_PrivateHomeworkHTMLExport_DesignScan
DRIFT_RISK = low
DRIFT_REASON = Policy lane is separated from public output; no runtime/export/source-text changes were made.
```

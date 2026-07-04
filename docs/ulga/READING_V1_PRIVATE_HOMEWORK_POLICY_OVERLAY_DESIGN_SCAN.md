# Reading V1 Private Homework Policy Overlay Design Scan

## 1. Current State

```text
Project: English_Learning_DB / E4S Reading V1 follow-up
Task: ReadingV1_PrivateHomeworkPolicyOverlay_DesignScan
Deliverable: docs/ulga/READING_V1_PRIVATE_HOMEWORK_POLICY_OVERLAY_DESIGN_SCAN.md
Task type: Policy DesignScan
```

This DesignScan defines how a future task may overlay Reading V1 candidate fields when the RAZ private-homework policy is active. It is intentionally policy-only.

This task does not modify existing candidate queue records, does not persist RAZ source text, does not implement the in-memory runtime pipeline, does not create HTML, does not create worksheet output, does not create public preview, and does not alter learner state or adaptive behavior.

Current machine-readable policy input:

```text
ulga/policies/raz_private_homework_policy_overlay.json
```

Current baseline:

```text
public/general RAZ payload display = BLOCKED
private homework payload display = LOCAL_RUNTIME_CONDITIONALLY_ALLOWED
candidate queue modified by config task = false
html exporter modified by config task = false
```

---

## 2. Design Goal

The goal is to define a safe overlay path from locator-only candidate evidence to private-homework runtime evidence access.

The overlay must preserve this distinction:

```text
persistent repo state: locator / metadata / policy flags only
local runtime state: household-only print materialization after attestation
public/cloud/export state: blocked
```

The overlay is not a data migration. It is an activation rule for a future task.

---

## 3. Overlay Activation Preconditions

A future overlay task may activate only when all conditions are true:

```text
target_env = local_homework_print
repo_visibility = private
operator_source_access_confirmed = true
public_distribution_allowed = false
commercial_use_allowed = false
github_pages_allowed = false
bulk_storage_allowed = false
not_for_public_export = true
not_for_commercial_distribution = true
policy_id = RAZ_PrivateHomeworkUsePolicy_Overlay_V1
source_family = RAZ_READING_CORPUS_A_T_CANDIDATE
```

If any condition is missing or false, the candidate remains in its existing locator-only state.

---

## 4. Candidate Field Overlay Contract

The future overlay should be computed, not blindly written.

Existing durable state remains:

```text
evidence_model.evidence_type = source_locator_only
evidence_model.evidence_locator = metadata_locator:...
evidence_model.source_trace_ref = trace_seed:...
source_payload_copied = false
```

Future private-homework runtime overlay may expose these computed fields:

```text
runtime_overlay.policy_id = RAZ_PrivateHomeworkUsePolicy_Overlay_V1
runtime_overlay.overlay_scope = private_homework_only
runtime_overlay.target_env = local_homework_print
runtime_overlay.evidence_type = private_homework_payload_runtime_allowed
runtime_overlay.display_scope = private_homework_only
runtime_overlay.evidence_text_persistence_allowed = false
runtime_overlay.evidence_text_runtime_access = local_print_only_after_operator_attestation
runtime_overlay.max_excerpt_lines = 12
runtime_overlay.source_locator_required = true
runtime_overlay.not_for_public_export = true
runtime_overlay.not_for_commercial_distribution = true
```

The following must not be persisted into the candidate artifact:

```text
raw RAZ passage text
full RAZ page text
full book text
large payload JSON
public-ready worksheet bundle
cloud-synced source payload
```

---

## 5. Manual Review State Handling

The existing manual review decision artifacts currently mark all candidates as needing revision. This DesignScan does not override that history.

For future private-homework runtime use, manual review must be separated into two layers:

```text
source/content review status: existing Reading V1 review state
private-homework activation review: operator attestation + local-only environment check
```

A future task may mark a private-homework runtime overlay as usable only when:

```text
private-homework activation review = pass
operator_source_access_confirmed = true
output gate target = local_homework_print
persistent evidence text storage = false
```

This does not imply public learner-facing approval.

---

## 6. Safe Overlay Status Values

Allowed overlay status values:

```text
overlay_not_applicable
overlay_blocked_by_environment
overlay_blocked_by_missing_attestation
overlay_blocked_by_public_target
overlay_ready_for_local_runtime
overlay_used_for_local_print
```

Forbidden overlay status values:

```text
public_output_approved
github_pages_approved
commercial_export_approved
bulk_storage_approved
source_payload_persisted
```

---

## 7. Future Overlay Artifact Shape

A future artifact should be separate from the base candidate file.

Recommended future artifact path:

```text
ulga/reports/reading_v1_private_homework_candidate_overlay.json
```

Example shape:

```json
{
  "schema_version": "READING_V1_PRIVATE_HOMEWORK_CANDIDATE_OVERLAY_V1",
  "policy_ref": "ulga/policies/raz_private_homework_policy_overlay.json",
  "target_env": "local_homework_print",
  "repo_visibility": "private",
  "overlay_records": [
    {
      "candidate_id": "reading_v1_pilot_001",
      "source_family": "RAZ_READING_CORPUS_A_T_CANDIDATE",
      "base_evidence_type": "source_locator_only",
      "base_evidence_locator": "metadata_locator:...",
      "overlay_status": "overlay_ready_for_local_runtime",
      "overlay_evidence_type": "private_homework_payload_runtime_allowed",
      "display_scope": "private_homework_only",
      "evidence_text_persistence_allowed": false,
      "runtime_materialization_allowed": true,
      "runtime_target_env": "local_homework_print",
      "max_excerpt_lines": 12,
      "source_locator_required": true,
      "not_for_public_export": true,
      "not_for_commercial_distribution": true
    }
  ]
}
```

This artifact must not include source text.

---

## 8. Validator Rules for Future Overlay Task

A future validator must block overlay records if:

```text
target_env != local_homework_print
repo_visibility != private
operator_source_access_confirmed != true
public_distribution_allowed != false
commercial_use_allowed != false
github_pages_allowed != false
bulk_storage_allowed != false
not_for_public_export != true
not_for_commercial_distribution != true
evidence_text_persistence_allowed != false
source_locator_required != true
```

A future validator must also block if any serialized overlay artifact contains:

```text
raw_source_text
full_passage_text
full_book_text
large_payload_json
public_ready_worksheet_bundle
```

A future validator should warn if:

```text
max_excerpt_lines is missing
source_locator is missing
policy_ref is missing
overlay_status is not overlay_ready_for_local_runtime or overlay_used_for_local_print
```

---

## 9. Relationship to Candidate Queue

This DesignScan does not modify:

```text
ulga/reports/reading_v1_pilot_candidates.json
ulga/reports/reading_v1_manual_review_queue.json
ulga/reports/reading_v1_manual_review_decisions.json
```

A future implementation should prefer an external overlay artifact rather than destructive updates to the original candidate records.

Reason:

```text
The base candidate record should remain source-locator-safe. Private-homework behavior is environment-specific and should be computed from policy plus activation context.
```

---

## 10. Relationship to In-Memory Pipeline

This DesignScan prepares but does not implement the in-memory pipeline.

Future in-memory pipeline requirements:

```text
repo stores only locator / metadata / quiz metadata / policy flags
local runtime reads operator-provided local source file only after attestation
runtime combines local payload and quiz metadata in memory
local print HTML may be produced only under local_homework_print target
materialized source text must not be committed back to GitHub
materialized source text must not be uploaded to GitHub Pages or public preview
```

---

## 11. Relationship to HTML Output Gate

This DesignScan prepares but does not implement the HTML output gate.

Future output gate must block:

```text
github_pages
public_site
public_preview
commercial_worksheet
shared_package
bulk_text_database
```

Future output gate may allow only:

```text
local_homework_print
```

when all private-homework activation requirements pass.

---

## 12. Acceptance Gates

| Gate | Result | Evidence |
|---|---:|---|
| Existing public/general block preserved | PASS | Sections 1, 3, 11 |
| Existing candidate queue not modified | PASS | Sections 1, 9 |
| Overlay activation preconditions defined | PASS | Section 3 |
| Candidate field overlay contract defined | PASS | Section 4 |
| Persistence boundary defined | PASS | Section 4 |
| Manual review / activation split defined | PASS | Section 5 |
| Overlay status values defined | PASS | Section 6 |
| Future overlay artifact shape defined | PASS | Section 7 |
| Future validator rules defined | PASS | Section 8 |
| In-memory pipeline boundary defined | PASS | Section 10 |
| HTML output gate boundary defined | PASS | Section 11 |
| No RAZ source text copied | PASS | Documentation only |
| No HTML created | PASS | Documentation only |
| No worksheet created | PASS | Documentation only |
| No learner state/adaptive output created | PASS | Documentation only |

Result:

```text
ACCEPTANCE_GATES = PASS_WITH_WARNINGS
```

---

## 13. Known Warnings

```text
warning_id: RV1-PH-OVERLAY-WARN-001
severity: medium
classification: NO_CANDIDATE_QUEUE_UPDATE
message: This DesignScan defines overlay rules only. Existing candidate artifacts remain unchanged.
blocks_current_task: no
```

```text
warning_id: RV1-PH-OVERLAY-WARN-002
severity: medium
classification: NO_RUNTIME_PIPELINE_IMPLEMENTED
message: In-memory source materialization is not implemented by this task.
blocks_current_task: no
```

```text
warning_id: RV1-PH-OVERLAY-WARN-003
severity: medium
classification: NO_HTML_OUTPUT_GATE_IMPLEMENTED
message: HTML output gate logic is not implemented by this task.
blocks_current_task: no
```

```text
warning_id: RV1-PH-OVERLAY-WARN-004
severity: medium
classification: NO_TEST_RUN
message: Documentation-only DesignScan. No local unittest or GitHub Actions CI were run.
blocks_current_task: no
```

---

## 14. Handoff Block

```text
CURRENT_TASK = ReadingV1_PrivateHomeworkPolicyOverlay_DesignScan
FILES_CREATED_OR_MODIFIED = docs/ulga/READING_V1_PRIVATE_HOMEWORK_POLICY_OVERLAY_DESIGN_SCAN.md
ACCEPTANCE_GATES = PASS_WITH_WARNINGS
BASE_CANDIDATE_QUEUE_MODIFIED = false
PRIVATE_HOMEWORK_OVERLAY_DEFINED = true
PERSISTENT_EVIDENCE_TEXT_ALLOWED = false
RUNTIME_EVIDENCE_ACCESS_SCOPE = local_homework_print_only_after_attestation
PUBLIC_OUTPUT_ALLOWED = false
GITHUB_PAGES_ALLOWED = false
COMMERCIAL_OUTPUT_ALLOWED = false
BULK_STORAGE_ALLOWED = false
NEXT_RECOMMENDED_TASK = ReadingV1_PrivateHomeworkOverlayArtifact_Implementation
DRIFT_RISK = low
DRIFT_REASON = Overlay is defined as a separate future artifact; base candidates and output layers remain unchanged.
```

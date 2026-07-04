# E4S P1 Follow-up B Reading V1 Source Payload Display Policy Design Scan

## 1. Current State

```text
Epic: E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
Closed Phase: E4S-P1_ReadingV1SourceGroundedPractice
Follow-up Branch: E4S-P1-FU-B_SourcePayloadDisplayPolicy_DesignScan
Deliverable: docs/ulga/E4S_P1_READING_V1_SOURCE_PAYLOAD_DISPLAY_POLICY.md
```

This task defines a conservative source payload and display policy for Reading V1 after P1 closeout and after the ManualReviewQueueArtifact implementation. It is policy-only. It does not copy source payloads, does not create learner-facing HTML, does not create worksheet export, does not create public preview, does not mutate learner state, does not create adaptive recommendations, and does not upgrade source/content authority.

Policy decision for the current Reading V1 tiny pilot:

```text
CURRENT_TINY_PILOT_SOURCE_PAYLOAD_DISPLAY = BLOCKED
CURRENT_TINY_PILOT_PASSAGE_TEXT_DISPLAY = BLOCKED
CURRENT_TINY_PILOT_EVIDENCE_TEXT_DISPLAY = BLOCKED
CURRENT_TINY_PILOT_LEARNER_FACING_OUTPUT = BLOCKED
```

Reason:

```text
The current candidate artifact is metadata-only, source payload was not inspected, manual review decisions remain pending, and source restrictions still require locator-only evidence. The policy therefore permits internal metadata display only, not source text display.
```

---

## 2. Inputs Considered

Policy inputs:

```text
docs/ulga/E4S_P1_READING_V1_CLOSEOUT_READBACK_QA.md
docs/ulga/E4S_P1_READING_V1_LEARNER_FACING_OUTPUT_GATE.md
docs/ulga/E4S_P1_READING_V1_MANUAL_REVIEW_QUEUE.md
ulga/reports/reading_v1_manual_review_queue.json
ulga/reports/reading_v1_manual_review_queue_summary.json
ulga/reports/reading_v1_pilot_candidates.json
ulga/reports/reading_v1_validation_report.json
ulga/graph/e4s_source_manifest.json
```

Current state readback:

```text
candidate_count = 3
manual_review_queue_exists = true
pending_count = 3
passed_internal_review_count = 0
validation_status = PASS_WITH_WARNINGS
validation_issue_count = 0
validation_warning_count = 6
learner_facing_allowed = false
worksheet_allowed = false
public_preview_allowed = false
authority_upgrade_allowed = false
```

---

## 3. Policy Scope

This policy controls whether a Reading V1 artifact may display:

```text
source passage text
source passage excerpts
source evidence text
source title text
source level labels
metadata locators
review notes
operator-authored replacement text
source-derived transformed text
```

This policy does not control:

```text
HTML implementation
worksheet implementation
learner state creation
adaptive scheduling
public distribution packaging
authority promotion
large-scale generation
```

Those require separate gates.

---

## 4. Display Classes

Allowed display classes:

| Display Class | Meaning | Current Tiny Pilot Status |
|---|---|---:|
| `DISPLAY_METADATA_ONLY` | Show IDs, locators, source family, question type, validation status, review status. | allowed internally |
| `DISPLAY_OPERATOR_AUTHORED_TEXT` | Show text written by operator/project, not copied from restricted source. | future gated |
| `DISPLAY_REVIEWED_REWRITTEN_TEXT` | Show human-reviewed replacement text that is not a source excerpt. | future gated |
| `DISPLAY_SHORT_SOURCE_QUOTE` | Show a short source quote/excerpt. | blocked |
| `DISPLAY_FULL_SOURCE_PAYLOAD` | Show full passage/source text. | blocked |
| `DISPLAY_EVIDENCE_TEXT` | Show evidence text copied from source. | blocked |
| `DISPLAY_PUBLIC_PREVIEW` | Show learner-facing or public page. | blocked |

Current allowed display:

```text
DISPLAY_METADATA_ONLY for internal review only
```

Current blocked display:

```text
DISPLAY_SHORT_SOURCE_QUOTE
DISPLAY_FULL_SOURCE_PAYLOAD
DISPLAY_EVIDENCE_TEXT
DISPLAY_PUBLIC_PREVIEW
```

---

## 5. Source Class Display Policy

| Source / Source Class | Role | Metadata Display | Payload Display | Evidence Text Display | Learner-Facing Display |
|---|---|---:|---:|---:|---:|
| `RAZ_READING_CORPUS_A_T_CANDIDATE` | reading corpus candidate | internal only | blocked | blocked | blocked |
| `RAZ_WORDLIST_A_T_EVIDENCE` | evidence only | internal only | blocked | blocked | blocked |
| `EGP_SOURCE_ENGLISH_GRAMMAR_PROFILE_ONLINE` | reference only | internal only | blocked | blocked | blocked |
| `EVP_SOURCE_ENGLISH_VOCABULARY_PROFILE_ONLINE` | reference only | internal only | blocked | blocked | blocked |
| `NGSL_SOURCE_FREQUENCY_PROFILE` | reference only | internal only | blocked | blocked | blocked |
| `CHUNK_SAFE_LAYER_REFERENCE` | reference only | internal only | blocked | blocked | blocked |
| operator-authored reviewed text | future internal source class | allowed after review | allowed if authored/owned | allowed if authored/owned | requires output gate |
| human-reviewed rewritten replacement text | future derived source class | allowed after review | allowed if non-infringing | allowed if non-infringing | requires output gate |

Hard rule:

```text
RAZ source payloads remain locator-only until a separate source-permission or owned-text policy explicitly permits a narrower use.
```

---

## 6. Current Candidate Field Policy

For the current three Reading V1 pilot candidates:

| Candidate Field | Current Value/Role | Display Policy |
|---|---|---:|
| `reading_candidate_id` | internal candidate identity | internal display allowed |
| `source_trace.source_id` | source ID | internal display allowed |
| `reading_payload_ref.passage_ref` | metadata locator | internal display allowed |
| `question_model.question_type` | literal question type | internal display allowed |
| `question_model.question_text` | metadata-only smoke text | internal display only, not learner-facing |
| `answer_model.expected_answer` | manual review placeholder | internal display only |
| `evidence_model.evidence_locator` | locator-only evidence | internal display allowed |
| `evidence_model.evidence_text_allowed` | false | no evidence text display |
| `reading_payload_ref.passage_excerpt_allowed` | false | no passage excerpt display |
| `manual_review_state` | pending | internal display allowed |
| `blocked_output_state` | all false | internal QA display allowed |

Decision:

```text
Current candidates may be rendered only as internal review records, not as student Reading questions.
```

---

## 7. Future Allowance Conditions

A future task may allow display of non-source-copied text only if all of these are true:

```text
manual review decision is complete
review decision approves internal validated pool
text is operator-authored or human-reviewed rewritten replacement text
text is explicitly marked not copied from restricted source payload
validation report is rerun after text insertion
payload/display policy class is recorded per candidate
learner-facing output gate is reopened and approved
output path is explicitly scoped
```

A future task may allow source quote/excerpt display only if all of these are true:

```text
source license/permission allows the specific display use
excerpt length policy is defined
attribution policy is defined
public/private distribution boundary is defined
copyright risk review is recorded
validator enforces excerpt length and source permission
manual review explicitly approves the excerpt
operator explicitly approves the output gate
```

Until then:

```text
source_quote_display = blocked
source_excerpt_display = blocked
full_source_payload_display = blocked
evidence_text_display = blocked
```

---

## 8. Validator Impact

Future validator hardening should add checks for these fields if display-enabled candidates are introduced:

```text
display_policy_class
display_text_origin
display_text_review_status
display_text_copied_from_source
source_payload_display_allowed
source_excerpt_display_allowed
evidence_text_display_allowed
operator_authored_text_allowed
rewritten_replacement_text_allowed
public_preview_allowed
learner_facing_display_allowed
```

Blocking rules:

```text
display_text_copied_from_source = true -> BLOCK unless source permission policy permits it
source_payload_display_allowed = true -> BLOCK for current RAZ candidates
evidence_text_display_allowed = true -> BLOCK for current RAZ candidates
learner_facing_display_allowed = true -> BLOCK unless output gate is approved
public_preview_allowed = true -> BLOCK unless public preview policy exists
```

Current validator does not need to change in this policy-only task.

---

## 9. Manual Review Queue Impact

The existing manual review queue can continue to store metadata-only review records.

For current queue items:

```text
review_status = pending
decision = pending
payload_policy_review.status = pending
question_review.status = pending
evidence_review.status = pending
learner_facing_allowed = false
worksheet_allowed = false
public_preview_allowed = false
authority_upgrade_allowed = false
```

This policy does not change any queue item decision. It only gives reviewers the rule that source payload/evidence text display remains blocked.

If future review decisions are recorded, reviewers must mark one of these display outcomes:

```text
metadata_only_internal_review
operator_authored_text_needed
rewritten_replacement_text_needed
source_payload_display_blocked
source_permission_review_needed
reject_for_display
```

---

## 10. Output Gate Impact

This policy alone does not reopen learner-facing output.

Current output gate remains:

```text
LEARNER_FACING_OUTPUT_GATE = EXPLICITLY_REMAINS_BLOCKED
```

Option C may be considered only after this policy if the operator wants to reopen the output gate. However, under the current state, Option C should still block learner-facing output unless review decisions and display-ready text exist.

---

## 11. Acceptance Gates for Option B

| Gate | Result | Evidence |
|---|---:|---|
| Option A queue artifact inspected | PASS | Section 2 |
| Current output block respected | PASS | Section 10 |
| Source class display rules defined | PASS | Section 5 |
| Current candidate field display policy defined | PASS | Section 6 |
| Future allowance conditions defined | PASS | Section 7 |
| Validator impact defined | PASS | Section 8 |
| Manual review queue impact defined | PASS | Section 9 |
| HTML implementation avoided | PASS | Documentation only |
| Worksheet implementation avoided | PASS | Documentation only |
| Source payload copying avoided | PASS | Documentation only |
| Learner-facing output avoided | PASS | Documentation only |
| Learner state avoided | PASS | Documentation only |
| Adaptive output avoided | PASS | Documentation only |
| Authority upgrade avoided | PASS | Documentation only |

Result:

```text
ACCEPTANCE_GATES = PASS_WITH_WARNINGS
```

---

## 12. Known Warnings

```text
warning_id: E4S-P1-FU-B-WARN-001
severity: medium
classification: CURRENT_PAYLOAD_DISPLAY_BLOCKED
message: The current tiny pilot remains metadata-only. Source passage/evidence text display is blocked.
blocks_current_task: no
```

```text
warning_id: E4S-P1-FU-B-WARN-002
severity: medium
classification: OUTPUT_GATE_STILL_BLOCKED
message: This policy does not approve learner-facing output, HTML export, worksheet export, or public preview.
blocks_current_task: no
```

```text
warning_id: E4S-P1-FU-B-WARN-003
severity: medium
classification: REVIEW_DECISIONS_PENDING
message: Manual review queue exists, but candidate-level review decisions remain pending.
blocks_current_task: no
```

```text
warning_id: E4S-P1-FU-B-WARN-004
severity: medium
classification: NO_TEST_RUN
message: This DesignScan is documentation-only. No local unittest or GitHub Actions CI were run.
blocks_current_task: no
```

---

## 13. Handoff Block

```text
GOVERNANCE_MD_CHECK = PASS
CURRENT_FOLLOWUP_TASK = E4S-P1-FU-B_SourcePayloadDisplayPolicy_DesignScan
CURRENT_TASK_SCOPE_LOCK = PASS
FORBIDDEN_OUTPUT_CHECK = PASS
FILES_CREATED_OR_MODIFIED = docs/ulga/E4S_P1_READING_V1_SOURCE_PAYLOAD_DISPLAY_POLICY.md
ACCEPTANCE_GATES = PASS_WITH_WARNINGS
CURRENT_TINY_PILOT_SOURCE_PAYLOAD_DISPLAY = BLOCKED
CURRENT_TINY_PILOT_PASSAGE_TEXT_DISPLAY = BLOCKED
CURRENT_TINY_PILOT_EVIDENCE_TEXT_DISPLAY = BLOCKED
LEARNER_FACING_OUTPUT_GATE = EXPLICITLY_REMAINS_BLOCKED
NEXT_RECOMMENDED_TASK = LearnerFacingOutputGate_Reopen_DesignScan_OR_ManualReviewDecisionArtifact_Implementation
DRIFT_RISK = low
DRIFT_REASON = Source display rules are now explicit, but no learner-facing/runtime/export behavior was changed.
```

---

## 14. Next Step Recommendation

If the goal is still printable/student-facing Reading output, the next safest task is not direct HTML export.

Recommended next task:

```text
ManualReviewDecisionArtifact_Implementation
```

Reason:

```text
Option B defines display policy, but current review decisions remain pending. Option C can be opened next, but without completed review decisions and display-ready text it should still keep learner-facing output blocked.
```

Alternative if the operator wants to test the gate logic anyway:

```text
LearnerFacingOutputGate_Reopen_DesignScan
```

Expected result under current evidence:

```text
likely remains blocked
```

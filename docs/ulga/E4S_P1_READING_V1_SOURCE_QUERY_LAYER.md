# E4S P1 Reading V1 Source Query Layer Design Scan

## 1. Current State

```text
Epic: E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
Phase: E4S-P1_ReadingV1SourceGroundedPractice
Middle Task: E4S-P1-M2_QueryAndSourceRouting
Small Task: E4S-P1-S6_ReadingV1_SourceQueryLayer_DesignScan
Deliverable: docs/ulga/E4S_P1_READING_V1_SOURCE_QUERY_LAYER.md
```

This task defines deterministic metadata-only source query logic for Reading V1. It is documentation only. It does not implement `tools/query_e4s_reading_v1_sources.py`, does not generate Reading candidates, and does not expose learner-facing output.

---

## 2. Governance Readback

```text
GOVERNANCE_MD_CHECK = PASS
CURRENT_TASK_IN_CONTRACT = PASS
```

Predecessor state:

```text
E4S-P1-M0_ActivationAndScopeGate -> COMPLETED
E4S-P1-M1_ReadingSchemaAndCandidateContract -> COMPLETED
E4S-P1-S5_ReadingV1_ValidatorContract_DesignScan -> COMPLETED
```

Task queue authorization:

```text
E4S-P1-S6_ReadingV1_SourceQueryLayer_DesignScan
Type = DesignScan / QueryDesign
May Implement = no
```

---

## 3. Task Boundary

Allowed file:

```text
docs/ulga/E4S_P1_READING_V1_SOURCE_QUERY_LAYER.md
```

Explicitly not changed in this task:

```text
tools/query_e4s_reading_v1_sources.py
Reading candidate JSON
Reading question output
source text payloads
student HTML
worksheet export
runtime state
adaptive path files
authority upgrade artifacts
large generated artifacts
```

Runtime impact:

```text
NONE
```

---

## 4. Query Layer Purpose

The future query layer answers only metadata-routing questions:

```text
Which manifest records are eligible for Reading V1 routing?
Which records are primary Reading candidate inputs?
Which records are supporting evidence or reference constraints?
Which records are blocked from Reading V1 input?
What minimal source_trace seed can a future candidate carry?
What source_policy snapshot should a future candidate preserve?
```

It does not decide the actual Reading question, answer, learner assignment, score, review schedule, HTML, worksheet, or source authority status.

---

## 5. Future Query Inputs

| Input | Required | Meaning |
|---|---:|---|
| `manifest_path` | yes | `ulga/graph/e4s_source_manifest.json` |
| `eligibility_contract_path` | yes | `docs/ulga/E4S_P1_READING_V1_SOURCE_ELIGIBILITY_CONTRACT.md` |
| `schema_path` | yes | `ulga/schemas/reading_v1_candidate.schema.json` |
| `target_phase` | yes | `E4S-P1_ReadingV1SourceGroundedPractice` |
| `query_mode` | yes | deterministic query mode |
| `output_path` | optional | future metadata-only summary path |

Forbidden query inputs:

```text
full source text payload
learner history or state
student HTML
worksheet export
generated candidate pool as source input
```

---

## 6. Query Modes

| Query Mode | Purpose | Allowed Output |
|---|---|---|
| `eligible_reading_sources` | Return Reading V1 eligible records | metadata only |
| `primary_reading_candidates` | Return primary Reading source records | metadata only |
| `supporting_evidence_sources` | Return supporting evidence records | metadata only |
| `reference_constraint_sources` | Return grammar/vocabulary/frequency/chunk references | metadata only |
| `blocked_sources` | Return blocked records | metadata only |
| `source_policy_snapshot` | Return policy fields for future candidates | metadata only |
| `candidate_trace_seed` | Return minimal trace seed without payload | metadata only |

No query mode may return passage text, question text, answer text, evidence text, learner data, HTML, worksheet data, or candidate JSON.

---

## 7. Eligibility Filter Rules

| Query Class | Inclusion Rule | Treatment |
|---|---|---|
| `PRIMARY_READING_CANDIDATE_INPUT` | `RAZ_READING_CORPUS_A_T_CANDIDATE` with `reading_corpus_candidate` role | primary trace seed |
| `SUPPORTING_READING_EXPOSURE_EVIDENCE` | `RAZ_WORDLIST_A_T_EVIDENCE` with `evidence_only` role | evidence only |
| `SCHEMA_REFERENCE_ONLY_GRAMMAR` | grammar profile reference record | reference only |
| `SCHEMA_REFERENCE_ONLY_VOCABULARY` | vocabulary profile reference record | reference only |
| `SCHEMA_REFERENCE_ONLY_FREQUENCY` | frequency profile reference record | reference only |
| `SCHEMA_REFERENCE_ONLY_CHUNK` | chunk reference record | reference only |
| `STATUS_AUDIT_ONLY` | status artifact record | blocked from Reading input |
| `GENERATED_CANDIDATE_BLOCKED_FOR_P1_INPUT` | generated content candidate | blocked from source input |
| `OUT_OF_SCOPE_SKILL_CANDIDATE` | assessment, writing, parent-functional, dialogue records | blocked from Reading input |
| `GOVERNANCE_ONLY` | governance / roadmap records | control-plane only |

Hard filters:

```text
No empty allowed_use.
No allowed_use / blocked_use overlap.
No status artifact as Reading input.
No generated candidate as source authority.
No RAZ wordlist as vocabulary authority or direct question source.
No payload access, learner-facing access, or authority upgrade from query output.
```

---

## 8. Deterministic Sorting

Sort key:

```text
query_class_priority
source_family
source_id
path
```

Default priority:

```text
PRIMARY_READING_CANDIDATE_INPUT = 10
SUPPORTING_READING_EXPOSURE_EVIDENCE = 20
SCHEMA_REFERENCE_ONLY_GRAMMAR = 30
SCHEMA_REFERENCE_ONLY_VOCABULARY = 31
SCHEMA_REFERENCE_ONLY_FREQUENCY = 32
SCHEMA_REFERENCE_ONLY_CHUNK = 33
STATUS_AUDIT_ONLY = 80
GENERATED_CANDIDATE_BLOCKED_FOR_P1_INPUT = 90
OUT_OF_SCOPE_SKILL_CANDIDATE = 91
GOVERNANCE_ONLY = 99
UNKNOWN_OR_INVALID = 100
```

Sorting must not use filesystem order, timestamps, random order, or model-generated ranking.

---

## 9. Future Query Output Shape

Future output object:

```text
schema_version
phase_id
task_id
query_id
query_mode
input_manifest_path
status
records
summary
warnings
blocked_records
next_shortest_step
```

Each `records[]` item:

```text
source_id
source_family
authority_role
query_class
path
format
exists
license_status
review_status
allowed_use_snapshot
blocked_use_snapshot
promotion_rule
risk_flags
source_trace_required
payload_access_allowed
learner_facing_allowed
authority_upgrade_allowed
query_notes
```

Required default values:

```text
payload_access_allowed = false
learner_facing_allowed = false
authority_upgrade_allowed = false
```

---

## 10. Candidate Trace Seed

`candidate_trace_seed` output may include:

```text
candidate_trace_seed_id
source_path_ref
source_unit_ref_policy
source_payload_copied
source_policy_snapshot
constraint_ref_policy
```

Required values:

```text
source_payload_copied = false
source_unit_ref_policy = locator_only_until_payload_policy
constraint_ref_policy = reference_only_no_authority_upgrade
```

This seed is not a Reading candidate and must not contain passage, question, answer, evidence, learner-facing, or learner-event content.

---

## 11. Query Issue Codes

Blocking issue codes:

```text
READING_V1_QUERY_MANIFEST_MISSING
READING_V1_QUERY_MANIFEST_INVALID
READING_V1_QUERY_UNKNOWN_MODE
READING_V1_QUERY_NO_PRIMARY_SOURCE
READING_V1_QUERY_INELIGIBLE_SOURCE_INCLUDED
READING_V1_QUERY_STATUS_AS_READING_SOURCE
READING_V1_QUERY_GENERATED_AS_AUTHORITY
READING_V1_QUERY_RAZ_WORDLIST_AS_AUTHORITY
READING_V1_QUERY_PAYLOAD_ACCESS_ALLOWED
READING_V1_QUERY_LEARNER_FACING_ALLOWED
READING_V1_QUERY_AUTHORITY_UPGRADE_ALLOWED
READING_V1_QUERY_NON_DETERMINISTIC_ORDER
READING_V1_QUERY_SCHEMA_DRIFT
```

Warning codes:

```text
READING_V1_QUERY_REFERENCE_SOURCE_MISSING
READING_V1_QUERY_SOURCE_EXISTS_FALSE
READING_V1_QUERY_LICENSE_REVIEW_NEEDED
READING_V1_QUERY_REVIEW_STATUS_NOT_FINAL
READING_V1_QUERY_TRACE_SEED_LOCATOR_PENDING
```

Warnings do not authorize payload access, learner-facing output, source upgrade, or candidate generation.

---

## 12. Future CLI Contract

Future P1-S7 helper should expose:

```text
python tools/query_e4s_reading_v1_sources.py \
  --manifest-path ulga/graph/e4s_source_manifest.json \
  --query-mode eligible_reading_sources \
  --output-report ulga/reports/reading_v1_source_query_summary.json
```

Expected behavior:

```text
exit code 0 for PASS / PASS_WITH_WARNINGS
exit code 1 for FAIL / BLOCKED
write structured report when output path is provided
never mutate manifest input
never read source payloads
never create Reading candidates
never create learner-facing output
never create learner state
never upgrade source authority
```

---

## 13. Future Query Helper Tests

P1-S7 tests should cover:

```text
current manifest returns RAZ_READING_CORPUS_A_T_CANDIDATE as primary source
current manifest returns RAZ_WORDLIST_A_T_EVIDENCE as evidence-only support
status artifact is blocked from Reading source output
generated candidate is blocked from source output
out-of-scope skill candidates are blocked from Reading input
reference-only records remain reference-only
payload_access_allowed is always false
learner_facing_allowed is always false
authority_upgrade_allowed is always false
candidate_trace_seed contains no passage/question/answer/evidence text
output is deterministically sorted
unknown query mode fails
missing manifest fails
structured report includes next_shortest_step
```

---

## 14. P1-M2 Boundary

P1-M2 sequence:

```text
E4S-P1-S6_ReadingV1_SourceQueryLayer_DesignScan -> current task
E4S-P1-S7_ReadingV1_SourceQueryLayer_Implementation -> next implementation task
E4S-P1-S8_ReadingV1_SourceQueryLayer_ReadbackQA -> query helper QA
```

P1-S7 may implement only metadata query helper and tests. It may not implement candidate builder, question generation, source payload access, validator, HTML, worksheet, learner state, adaptive path, source upgrade, or large generated artifacts.

---

## 15. Acceptance Gates for P1-S6

| Gate | Result | Evidence |
|---|---:|---|
| Governance MD checked | PASS | Section 2 |
| Current task appears in task queue | PASS | Section 2 |
| P1-M1 completion checked | PASS | Section 2 |
| Allowed file scope locked | PASS | Section 3 |
| Forbidden outputs recorded | PASS | Section 3 |
| Query layer purpose defined | PASS | Section 4 |
| Query input contract defined | PASS | Section 5 |
| Query modes defined | PASS | Section 6 |
| Eligibility filter rules defined | PASS | Section 7 |
| Deterministic sorting rules defined | PASS | Section 8 |
| Query output shape defined | PASS | Section 9 |
| Candidate trace seed defined | PASS | Section 10 |
| Query issue codes defined | PASS | Section 11 |
| Future CLI contract defined | PASS | Section 12 |
| Future tests defined | PASS | Section 13 |
| P1-M2 boundary defined | PASS | Section 14 |
| Query implementation avoided | PASS | No query helper code |
| Pilot generation avoided | PASS | No candidate JSON |
| Source payload access avoided | PASS | No source text copied |
| Learner-facing output avoided | PASS | No HTML / worksheet output |
| Runtime state avoided | PASS | No runtime files |
| Source upgrade avoided | PASS | Design only |

---

## 16. Warning Register

```text
warning_id: E4S-P1-S6-WARN-001
severity: medium
classification: QUERY_HELPER_NOT_IMPLEMENTED
message: This task defines source query design only. Query helper implementation belongs to P1-S7.
blocks_current_task: no
```

```text
warning_id: E4S-P1-S6-WARN-002
severity: medium
classification: TRACE_SEED_LOCATOR_PENDING
message: Candidate trace seed may not include unit-level locator until future query/index policy exists.
blocks_current_task: no
```

```text
warning_id: E4S-P1-S6-WARN-003
severity: medium
classification: NO_TEST_RUN
message: This DesignScan is documentation-only. No local Python tests or GitHub Actions CI were run.
blocks_current_task: no
```

---

## 17. Deferred Issues Register

```text
issue_id: E4S-P1-S6-DEFER-001
severity: high
affected_file_or_artifact: tools/query_e4s_reading_v1_sources.py
classification: FUTURE_WORK
why_deferred: P1-S6 defines query design only. Query helper implementation is scheduled for P1-S7.
recommended_future_task: E4S-P1-S7_ReadingV1_SourceQueryLayer_Implementation
blocks_current_task: no
```

```text
issue_id: E4S-P1-S6-DEFER-002
severity: high
affected_file_or_artifact: Reading V1 pilot candidates
classification: FUTURE_WORK
why_deferred: Pilot generation is blocked until P1-M2 query implementation/readback and P1-M3 pilot policy exist.
recommended_future_task: E4S-P1-S10_ReadingV1_PilotCandidateBuilder_Implementation after required gates
blocks_current_task: no
```

---

## 18. Distance Vector

```text
E4S-P0_SourceAuthorityAndCorpusRoadmap -> CLOSED_AS_SOURCE_AUTHORITY_FOUNDATION
D_P0 = 0

E4S-P1_ReadingV1SourceGroundedPractice -> ACTIVE_QUERY_DESIGN_READY
E4S-P1-S6_ReadingV1_SourceQueryLayer_DesignScan -> COMPLETED

D_P1_M2 = 2 small tasks left
D_P1 = 12 small tasks left
```

Remaining P1-M2 tasks:

```text
E4S-P1-S7_ReadingV1_SourceQueryLayer_Implementation
E4S-P1-S8_ReadingV1_SourceQueryLayer_ReadbackQA
```

---

## 19. Mandatory Handoff Block

```text
GOVERNANCE_MD_CHECK = PASS
CURRENT_TASK_IN_CONTRACT = PASS
CURRENT_TASK_SCOPE_LOCK = PASS
FORBIDDEN_OUTPUT_CHECK = PASS
FILES_CREATED_OR_MODIFIED = docs/ulga/E4S_P1_READING_V1_SOURCE_QUERY_LAYER.md
ACCEPTANCE_GATES = PASS_WITH_WARNINGS
DISTANCE_VECTOR_UPDATE = D_P1_M2 = 2; D_P1 = 12
NEXT_TASK_IN_CONTRACT = PASS
NEXT_TASK_ID = E4S-P1-S7_ReadingV1_SourceQueryLayer_Implementation
DRIFT_RISK = low
DRIFT_REASON = Query layer is now designed, but implementation and pilot generation remain blocked until later gates.
REQUIRED_ACTION = continue with P1-S7 only
```

---

## 20. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P1-S7_ReadingV1_SourceQueryLayer_Implementation
```

Only next allowed action:

```text
Create tools/query_e4s_reading_v1_sources.py and tests for deterministic metadata-only source query logic. The helper may read the source manifest and emit metadata-only query summaries. It must not read source payloads, generate Reading candidates, create questions, create learner-facing output, create learner state, or upgrade source authority.
```

Stop here until the operator explicitly starts P1-S7.

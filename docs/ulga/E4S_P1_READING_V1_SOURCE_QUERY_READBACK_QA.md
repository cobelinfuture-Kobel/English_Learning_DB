# E4S P1 Reading V1 Source Query Layer Readback QA

## 1. Current State

```text
Epic: E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
Phase: E4S-P1_ReadingV1SourceGroundedPractice
Middle Task: E4S-P1-M2_QueryAndSourceRouting
Small Task: E4S-P1-S8_ReadingV1_SourceQueryLayer_ReadbackQA
Deliverable: docs/ulga/E4S_P1_READING_V1_SOURCE_QUERY_READBACK_QA.md
```

This task performs GitHub artifact readback QA for the P1-S7 metadata-only source query helper. It does not change helper code, generate Reading candidates, read source payloads, create learner-facing output, create learner state, or upgrade source authority.

---

## 2. Governance and Queue Readback

Task queue evidence:

```text
E4S-P1-S6_ReadingV1_SourceQueryLayer_DesignScan -> DesignScan / QueryDesign
E4S-P1-S7_ReadingV1_SourceQueryLayer_Implementation -> Implementation / MetadataQueryOnly
E4S-P1-S8_ReadingV1_SourceQueryLayer_ReadbackQA -> QA / Readback
```

P1-M2 exit gate:

```text
P1-M2 exits only when source selection is deterministic, traceable, and blocked from learner-facing output.
```

Readback result:

```text
GOVERNANCE_MD_CHECK = PASS
CURRENT_TASK_IN_CONTRACT = PASS
CURRENT_TASK_SCOPE_LOCK = PASS
```

---

## 3. Files Inspected

```text
docs/ulga/E4S_P1_READING_V1_TASK_QUEUE.md
docs/ulga/E4S_P1_READING_V1_SOURCE_QUERY_LAYER.md
tools/query_e4s_reading_v1_sources.py
tests/test_query_e4s_reading_v1_sources.py
ulga/graph/e4s_source_manifest.json
```

Files modified by this task:

```text
docs/ulga/E4S_P1_READING_V1_SOURCE_QUERY_READBACK_QA.md
```

Files not modified by this task:

```text
tools/query_e4s_reading_v1_sources.py
tests/test_query_e4s_reading_v1_sources.py
ulga/graph/e4s_source_manifest.json
source payloads
Reading candidate JSON
student HTML
worksheet output
learner state files
adaptive path files
```

---

## 4. P1-S6 Design Contract Readback

P1-S6 required the query helper to be metadata-only and not return passage text, question text, answer text, evidence text, learner data, HTML, worksheet data, or candidate JSON.

P1-S6 required query modes:

```text
eligible_reading_sources
primary_reading_candidates
supporting_evidence_sources
reference_constraint_sources
blocked_sources
source_policy_snapshot
candidate_trace_seed
```

P1-S6 required deterministic sorting by:

```text
query_class_priority
source_family
source_id
path
```

P1-S6 required default output safety flags:

```text
payload_access_allowed = false
learner_facing_allowed = false
authority_upgrade_allowed = false
```

Readback result:

```text
P1_S6_DESIGN_ALIGNMENT = PASS
```

---

## 5. P1-S7 Helper Readback

Helper path:

```text
tools/query_e4s_reading_v1_sources.py
```

Readback findings:

```text
- Helper states that it reads only the E4S source manifest.
- Helper states that it must not read source payloads.
- Helper states that it must not generate Reading candidates.
- Helper states that it must not create learner-facing output.
- Helper states that it must not mutate learner state.
- Helper states that it must not upgrade source authority.
```

Implemented query modes:

```text
eligible_reading_sources
primary_reading_candidates
supporting_evidence_sources
reference_constraint_sources
blocked_sources
source_policy_snapshot
candidate_trace_seed
```

Implemented source classification:

```text
RAZ_READING_CORPUS_A_T_CANDIDATE -> PRIMARY_READING_CANDIDATE_INPUT
RAZ_WORDLIST_A_T_EVIDENCE -> SUPPORTING_READING_EXPOSURE_EVIDENCE
EGP_SOURCE_ENGLISH_GRAMMAR_PROFILE_ONLINE -> SCHEMA_REFERENCE_ONLY_GRAMMAR
EVP_SOURCE_ENGLISH_VOCABULARY_PROFILE_ONLINE -> SCHEMA_REFERENCE_ONLY_VOCABULARY
NGSL_SOURCE_FREQUENCY_PROFILE -> SCHEMA_REFERENCE_ONLY_FREQUENCY
CHUNK_SAFE_LAYER_REFERENCE -> SCHEMA_REFERENCE_ONLY_CHUNK
status_artifact -> STATUS_AUDIT_ONLY
generated_content_candidate -> GENERATED_CANDIDATE_BLOCKED_FOR_P1_INPUT
assessment/writing/parent-functional/story-dialogue -> OUT_OF_SCOPE_SKILL_CANDIDATE
governance/roadmap -> GOVERNANCE_ONLY
```

Implemented output safety flags:

```text
payload_access_allowed = false
learner_facing_allowed = false
authority_upgrade_allowed = false
```

Candidate trace seed safety:

```text
source_payload_copied = false
source_unit_ref_policy = locator_only_until_payload_policy
constraint_ref_policy = reference_only_no_authority_upgrade
```

Readback result:

```text
HELPER_METADATA_ONLY_READBACK = PASS
HELPER_CLASSIFICATION_READBACK = PASS
HELPER_SAFETY_FLAGS_READBACK = PASS
HELPER_TRACE_SEED_READBACK = PASS
```

---

## 6. Structured Report and CLI Readback

Helper report shape includes:

```text
schema_version
phase_id
task_id
query_helper_id
query_helper_version
query_id
query_mode
input_manifest_path
status
records
summary
issues
warnings
blocked_records
next_shortest_step
```

Structured failure behavior:

```text
Unknown query mode -> READING_V1_QUERY_UNKNOWN_MODE
Missing manifest -> READING_V1_QUERY_MANIFEST_MISSING
Invalid manifest -> READING_V1_QUERY_MANIFEST_INVALID
```

CLI readback:

```text
--manifest-path
--query-mode
--output-report
```

Exit rule:

```text
exit code 0 for PASS / PASS_WITH_WARNINGS
exit code 1 for FAIL / BLOCKED
```

Readback result:

```text
STRUCTURED_REPORT_READBACK = PASS
CLI_CONTRACT_READBACK = PASS
```

---

## 7. Test Readback

Test path:

```text
tests/test_query_e4s_reading_v1_sources.py
```

Test coverage confirmed:

```text
RAZ_READING_CORPUS_A_T_CANDIDATE returns as primary Reading candidate source.
RAZ_WORDLIST_A_T_EVIDENCE returns as evidence-only support.
Reference sources remain reference-only.
Status artifact, generated candidate, and out-of-scope records are blocked.
Candidate trace seed contains no passage/question/answer/evidence text.
Output is deterministically sorted.
Unknown query mode returns structured failure report.
Missing manifest writes structured failure report.
Report summary remains metadata-only and unsafe access flags remain false.
```

Import/load note:

```text
Test loader inserts the helper module into sys.modules before exec_module so dataclass module loading works correctly.
```

Readback result:

```text
TEST_COVERAGE_READBACK = PASS
```

---

## 8. Known Warnings

```text
warning_id: E4S-P1-S8-WARN-001
severity: medium
classification: TESTS_NOT_EXECUTED_BY_THIS_TASK
message: This ReadbackQA inspected GitHub artifacts only. No local unittest or GitHub Actions CI run was executed by this task.
blocks_current_task: no
```

```text
warning_id: E4S-P1-S8-WARN-002
severity: medium
classification: QUERY_REPORT_NOT_GENERATED_BY_THIS_TASK
message: P1-S8 did not run the query helper and did not create a query summary JSON artifact.
blocks_current_task: no
```

---

## 9. Acceptance Gates for P1-S8

| Gate | Result | Evidence |
|---|---:|---|
| Governance/task queue checked | PASS | Section 2 |
| P1-S6 design contract inspected | PASS | Section 4 |
| P1-S7 helper inspected | PASS | Section 5 |
| P1-S7 tests inspected | PASS | Section 7 |
| Metadata-only boundary preserved | PASS | Sections 4-5 |
| Deterministic sorting present | PASS | Sections 4-5 |
| RAZ reading corpus classified as primary | PASS | Section 5 |
| RAZ wordlist classified as evidence-only | PASS | Section 5 |
| Status artifacts blocked | PASS | Section 5 |
| Generated candidates blocked | PASS | Section 5 |
| Out-of-scope skill sources blocked | PASS | Section 5 |
| Payload access blocked | PASS | Sections 5-7 |
| Learner-facing output blocked | PASS | Sections 5-7 |
| Authority upgrade blocked | PASS | Sections 5-7 |
| Structured report behavior present | PASS | Section 6 |
| Test coverage present | PASS | Section 7 |
| Helper code unchanged by P1-S8 | PASS | Section 3 |
| Candidate generation avoided | PASS | Section 3 |
| Source payload extraction avoided | PASS | Section 3 |
| Learner state avoided | PASS | Section 3 |
| Student-facing output avoided | PASS | Section 3 |

Result:

```text
ACCEPTANCE_GATES = PASS_WITH_WARNINGS
```

---

## 10. P1-M2 Close Result

P1-M2 exit gate:

```text
P1-M2 exits only when source selection is deterministic, traceable, and blocked from learner-facing output.
```

Readback:

```text
source selection deterministic = PASS
source trace seed metadata exists = PASS
learner-facing output blocked = PASS
payload access blocked = PASS
authority upgrade blocked = PASS
```

P1-M2 state after this task:

```text
E4S-P1-M2_QueryAndSourceRouting -> COMPLETED
D_P1_M2 = 0 small tasks left
```

---

## 11. Distance Vector

```text
E4S-P0_SourceAuthorityAndCorpusRoadmap -> CLOSED_AS_SOURCE_AUTHORITY_FOUNDATION
D_P0 = 0

E4S-P1_ReadingV1SourceGroundedPractice -> ACTIVE_PILOT_POLICY_GATE_READY
E4S-P1-S8_ReadingV1_SourceQueryLayer_ReadbackQA -> COMPLETED
E4S-P1-M2_QueryAndSourceRouting -> COMPLETED

D_P1_M2 = 0 small tasks left
D_P1 = 10 small tasks left
```

Next middle task:

```text
E4S-P1-M3_SmallPilotCandidateGeneration
```

Next small task:

```text
E4S-P1-S9_ReadingV1_PilotGenerationPolicy_DesignScan
```

---

## 12. Mandatory Handoff Block

```text
GOVERNANCE_MD_CHECK = PASS
CURRENT_TASK_IN_CONTRACT = PASS
CURRENT_TASK_SCOPE_LOCK = PASS
FORBIDDEN_OUTPUT_CHECK = PASS
FILES_CREATED_OR_MODIFIED = docs/ulga/E4S_P1_READING_V1_SOURCE_QUERY_READBACK_QA.md
ACCEPTANCE_GATES = PASS_WITH_WARNINGS
DISTANCE_VECTOR_UPDATE = D_P1_M2 = 0; D_P1 = 10
NEXT_TASK_IN_CONTRACT = PASS
NEXT_TASK_ID = E4S-P1-S9_ReadingV1_PilotGenerationPolicy_DesignScan
DRIFT_RISK = low
DRIFT_REASON = Query helper passed artifact readback, but tests were not executed in this task and pilot generation remains blocked until policy.
REQUIRED_ACTION = continue with P1-S9 only
```

---

## 13. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P1-S9_ReadingV1_PilotGenerationPolicy_DesignScan
```

Only next allowed action:

```text
Create docs/ulga/E4S_P1_READING_V1_PILOT_GENERATION_POLICY.md to define strict tiny-pilot size, candidate source trace use, allowed question types, report requirements, and blocked outputs before any pilot candidate builder can run.
```

Stop here until the operator explicitly starts P1-S9.

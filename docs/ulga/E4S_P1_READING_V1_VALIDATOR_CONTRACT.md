# E4S P1 Reading V1 Validator Contract Design Scan

## 1. Current State

Epic ID:

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

Current Phase:

```text
E4S-P1_ReadingV1SourceGroundedPractice
```

Current Middle Task:

```text
E4S-P1-M1_ReadingSchemaAndCandidateContract
```

Current Small Task:

```text
E4S-P1-S5_ReadingV1_ValidatorContract_DesignScan
```

Deliverable:

```text
docs/ulga/E4S_P1_READING_V1_VALIDATOR_CONTRACT.md
```

This task defines the validator contract for Reading V1 candidates. It specifies the future validator inputs, validation stages, required issue codes, blocking rules, report shape, CLI expectations, and acceptance gates. It does not implement the validator, generate Reading questions, create pilot candidates, extract source payloads, create learner-facing HTML, create worksheets, create learner events, create learner state, or promote source/content authority.

---

## 2. Mandatory Governance Readback

Governance source:

```text
docs/roadmap/E4S_PHASED_TASK_DECOMPOSITION_AND_HANDSHAKE_CONTRACT.md
```

Governance result:

```text
GOVERNANCE_MD_CHECK = PASS
CURRENT_TASK_IN_CONTRACT = PASS
```

Predecessor state:

```text
E4S-P1-M0_ActivationAndScopeGate -> COMPLETED
E4S-P1-S3_ReadingV1_ItemSchema_DesignScan -> COMPLETED
E4S-P1-S4_ReadingV1_PilotCandidateSchema_Implementation -> COMPLETED
```

P1 task queue authorizes the current task as:

```text
E4S-P1-S5_ReadingV1_ValidatorContract_DesignScan
Type = DesignScan / ValidatorContract
Deliverable = docs/ulga/E4S_P1_READING_V1_VALIDATOR_CONTRACT.md
May Implement = no
```

---

## 3. Task Boundary

Task type:

```text
DesignScan / ValidatorContract
```

Allowed file:

```text
docs/ulga/E4S_P1_READING_V1_VALIDATOR_CONTRACT.md
```

Required existing inputs:

```text
docs/ulga/E4S_P1_READING_V1_ITEM_SCHEMA.md
ulga/schemas/reading_v1_candidate.schema.json
tests/test_reading_v1_candidate_schema.py
```

Forbidden files and paths:

```text
tools/validate_reading_v1_candidates.py
tools/query_e4s_reading_v1_sources.py
tools/build_reading_v1_pilot_candidates.py
ulga/reports/reading_v1_pilot_summary.json
ulga/reports/reading_v1_validation_report.json
site HTML
student-facing Reading practice HTML
worksheet exports
large generated artifacts
source corpus payloads
learner event files
learner state files
learner profile files
adaptive scheduling files
dependency graph artifacts
promotion artifacts
```

Generated artifact policy:

```text
No validator code, generated Reading questions, Reading candidate JSON, pilot artifacts, learner-facing files, learner events, learner state, or large JSON artifacts are allowed in P1-S5.
```

Runtime impact:

```text
NONE
```

Promotion impact:

```text
NONE. P1-S5 performs no source/content authority promotion.
```

---

## 4. Validator Purpose

The future Reading V1 validator must answer:

```text
Is this candidate structurally valid?
Is this candidate source-traceable?
Is this candidate evidence-grounded?
Does this candidate preserve source policy and blocked output constraints?
Does this candidate avoid learner-facing, learner-state, adaptive, public distribution, and authority-promotion behavior?
Is this candidate safe to move to the next P1 gate?
```

The validator must not answer:

```text
Is the learner ready for this item?
Did the learner master this concept?
Should the learner advance?
Should the item be scheduled for review?
Should the source become content authority?
Should the candidate become learner-facing HTML?
```

---

## 5. Validator Inputs

Future validator input classes:

| Input | Required | Meaning |
|---|---:|---|
| `candidate_path` | yes | Path to Reading V1 candidate JSON or JSON list produced by a future approved task. |
| `schema_path` | yes | `ulga/schemas/reading_v1_candidate.schema.json`. |
| `manifest_path` | yes | `ulga/graph/e4s_source_manifest.json`. |
| `source_eligibility_contract_path` | yes | `docs/ulga/E4S_P1_READING_V1_SOURCE_ELIGIBILITY_CONTRACT.md`. |
| `item_schema_contract_path` | yes | `docs/ulga/E4S_P1_READING_V1_ITEM_SCHEMA.md`. |
| `output_report_path` | yes | Future validation report path. |

Forbidden validator inputs:

```text
learner profile
learner answer history
learner state
adaptive scheduler queue
student-facing HTML
worksheet export
source payload files unless a future task explicitly permits payload handling
```

---

## 6. Validation Stages

Future validator must run stages in this order:

| Stage | Stage ID | Purpose | Blocking? |
|---:|---|---|---:|
| 1 | `SCHEMA_STRUCTURE` | Validate candidate object against Reading V1 JSON schema. | yes |
| 2 | `SOURCE_ELIGIBILITY` | Confirm source_id is eligible for P1 Reading V1 and source_family / authority_role match contract. | yes |
| 3 | `SOURCE_POLICY` | Confirm allowed / blocked uses, promotion rule, license, and risk flags remain preserved. | yes |
| 4 | `PAYLOAD_POLICY` | Confirm source payload and excerpts are not copied unless explicitly allowed. | yes |
| 5 | `QUESTION_MODEL` | Confirm question type is allowed and evidence is required. | yes |
| 6 | `ANSWER_MODEL` | Confirm answer shape is valid and answer evidence ref exists. | yes |
| 7 | `EVIDENCE_MODEL` | Confirm evidence locator and source trace linkage exist. | yes |
| 8 | `LEVEL_SITUATION_SKILL` | Confirm level is routing metadata only and skill is Reading only. | yes |
| 9 | `BLOCKED_OUTPUT_STATE` | Confirm all blocked output fields remain false before their gates. | yes |
| 10 | `AUDIT_TRAIL` | Confirm required audit fields exist. | yes |
| 11 | `REPORT_SUMMARY` | Emit summary, issue codes, warning counts, and next step. | yes |

---

## 7. Blocking Issue Codes

The future validator must produce these blocking issue codes when violated:

| Code | Condition |
|---|---|
| `READING_V1_SCHEMA_INVALID` | Candidate does not conform to `reading_v1_candidate.schema.json`. |
| `READING_V1_UNKNOWN_SOURCE_ID` | `source_trace.source_id` is not known in source manifest. |
| `READING_V1_INELIGIBLE_SOURCE` | Source is not eligible for Reading V1 candidate input. |
| `READING_V1_SOURCE_FAMILY_MISMATCH` | Candidate `source_family` does not match manifest / contract. |
| `READING_V1_AUTHORITY_ROLE_MISMATCH` | Candidate `authority_role` does not match manifest / contract. |
| `READING_V1_SOURCE_TRACE_MISSING` | Required source trace fields are absent or empty. |
| `READING_V1_SOURCE_PAYLOAD_COPIED` | `source_payload_copied` is true or source payload appears copied without a later policy. |
| `READING_V1_PUBLIC_DISTRIBUTION_ALLOWED` | `public_distribution_allowed` is true for restricted or non-redistributable sources. |
| `READING_V1_LEARNER_FACING_ALLOWED` | `learner_facing_allowed` is true before output gate. |
| `READING_V1_AUTHORITY_PROMOTION_ALLOWED` | `authority_promotion_allowed` is true. |
| `READING_V1_DIRECT_READING_AUTHORITY` | Candidate treats reading corpus candidate as direct reading authority. |
| `READING_V1_RAZ_WORDLIST_AS_VOCAB_AUTHORITY` | RAZ wordlist is used as direct vocabulary authority. |
| `READING_V1_QUESTION_TYPE_BLOCKED` | Question type is not in initial allowed list. |
| `READING_V1_QUESTION_NOT_EVIDENCE_REQUIRED` | `requires_evidence` is false or missing. |
| `READING_V1_ANSWER_EVIDENCE_MISSING` | Answer has no evidence reference. |
| `READING_V1_EVIDENCE_TRACE_MISSING` | Evidence has no source trace reference or locator. |
| `READING_V1_MODEL_ASSERTION_AS_EVIDENCE` | Evidence is not traceable and appears to rely on model assertion. |
| `READING_V1_LEVEL_AS_LEARNER_PLACEMENT` | Level metadata is used as learner placement. |
| `READING_V1_MULTISKILL_EXPANSION` | Candidate expands beyond Reading skill in P1. |
| `READING_V1_LEARNER_EVENT_CREATED` | Candidate creates or implies learner event data. |
| `READING_V1_LEARNER_STATE_UPDATED` | Candidate creates or updates learner state. |
| `READING_V1_ADAPTIVE_RECOMMENDATION_CREATED` | Candidate creates adaptive recommendation. |
| `READING_V1_STUDENT_HTML_CREATED` | Candidate creates student-facing HTML before output gate. |
| `READING_V1_WORKSHEET_CREATED` | Candidate creates worksheet output before output gate. |
| `READING_V1_LARGE_SCALE_GENERATION` | Candidate set exceeds a future approved pilot policy. |
| `READING_V1_MISSING_AUDIT_TRAIL` | Required audit fields are missing. |

---

## 8. Warning Issue Codes

The future validator may produce these warning codes when non-blocking but review-relevant:

| Code | Condition |
|---|---|
| `READING_V1_MANUAL_REVIEW_PENDING` | Candidate structurally passes but still requires manual review. |
| `READING_V1_OPTIONAL_REFERENCE_MISSING` | Optional grammar / vocabulary / frequency / chunk references are absent. |
| `READING_V1_LEVEL_BAND_UNKNOWN` | `normalized_level_band` is absent or unknown. |
| `READING_V1_SITUATION_CONTEXT_MISSING` | Optional `situation_context` is absent. |
| `READING_V1_EXCERPT_POLICY_REVIEW_NEEDED` | Candidate asks to allow excerpts but policy status is uncertain. |
| `READING_V1_SOURCE_REVIEW_NOT_FINAL` | Source is metadata-reviewed but not final-reviewed. |

Warnings do not allow promotion, learner-facing output, or pilot expansion.

---

## 9. Source Eligibility Rules

The validator must accept only these P1 source roles:

| source_id / family | role | allowed validator treatment |
|---|---|---|
| `RAZ_READING_CORPUS_A_T_CANDIDATE` / `raz_reading_corpus` | `reading_corpus_candidate` | primary Reading candidate input, trace required |
| `RAZ_WORDLIST_A_T_EVIDENCE` / `raz_wordlist` | `evidence_only` | supporting exposure evidence only, never vocabulary authority |
| `EGP_SOURCE_ENGLISH_GRAMMAR_PROFILE_ONLINE` / `grammar_profile` | `reference_only` | reference constraint only |
| `EVP_SOURCE_ENGLISH_VOCABULARY_PROFILE_ONLINE` / `vocabulary_profile` | `reference_only` | reference constraint only |
| `NGSL_SOURCE_FREQUENCY_PROFILE` / `frequency_profile` | `reference_only` | reference constraint only |
| `CHUNK_SAFE_LAYER_REFERENCE` / `chunk_authority` | `reference_only` | reference constraint only |

The validator must reject:

```text
status_artifact
generated_content_candidate
assessment_pattern_corpus
writing_template_corpus
parent_functional_sentence_corpus
story_dialogue_corpus
unknown source family
```

---

## 10. Schema Validation Rules

Schema validation must enforce:

```text
schema_version = READING_V1_CANDIDATE_SCHEMA_V1
phase_id = E4S-P1_ReadingV1SourceGroundedPractice
additionalProperties = false
all top-level required fields exist
all nested required fields exist
source_payload_copied = false
public_distribution_allowed = false
learner_facing_allowed = false
authority_promotion_allowed = false
requires_evidence = true
learner_placement_allowed = false
multi_skill_expansion_allowed = false
all blocked_output_state fields = false
```

If JSON Schema validation fails, the validator must still return a structured report with `status = FAIL` and at least one issue code.

---

## 11. Evidence Validation Rules

Evidence validation must enforce:

```text
answer_model.answer_evidence_ref exists
evidence_model.evidence_id exists
evidence_model.source_trace_ref exists
evidence_model.evidence_locator exists
evidence_text_allowed = false implies evidence_text must be absent
passage_excerpt_allowed = false implies passage_excerpt must be absent
evidence must be traceable to the same source context as source_trace
```

The future validator does not need to verify actual passage text in P1-S12 unless a later payload policy explicitly permits source payload inspection. Until then, locator-only evidence is acceptable if source trace is preserved.

---

## 12. Blocked Output Validation Rules

The validator must fail if any of these fields are true:

```text
blocked_output_state.learner_facing_output_created
blocked_output_state.student_html_created
blocked_output_state.worksheet_created
blocked_output_state.learner_event_created
blocked_output_state.learner_state_updated
blocked_output_state.adaptive_recommendation_created
blocked_output_state.authority_promotion_performed
blocked_output_state.large_scale_generation_performed
```

The validator must also fail if candidate text or audit notes imply any blocked output even when the boolean field remains false.

---

## 13. Report Shape

Future validator report must be a JSON object with this shape:

```text
schema_version
phase_id
task_id
validator_id
validator_version
input_candidate_path
input_schema_path
input_manifest_path
status
summary
issues
warnings
candidate_count
pass_count
fail_count
warning_count
blocked_output_count
next_shortest_step
```

Allowed `status` values:

```text
PASS
PASS_WITH_WARNINGS
FAIL
BLOCKED
```

Issue object shape:

```text
code
severity
candidate_id
field_path
message
blocking
recommended_action
```

Report rule:

```text
Any blocking issue sets status to FAIL or BLOCKED.
Warnings only may produce PASS_WITH_WARNINGS.
No issues produces PASS.
```

---

## 14. Future CLI Contract

Future validator implementation should expose a CLI equivalent to:

```text
python tools/validate_reading_v1_candidates.py \
  --candidate-path <candidate_json_or_dir> \
  --schema-path ulga/schemas/reading_v1_candidate.schema.json \
  --manifest-path ulga/graph/e4s_source_manifest.json \
  --output-report ulga/reports/reading_v1_validation_report.json
```

Expected CLI behavior:

```text
exit code 0 for PASS / PASS_WITH_WARNINGS
exit code 1 for FAIL / BLOCKED
always write a structured report when possible
never mutate candidate input
never create learner-facing output
never create learner state
never promote source/content authority
```

---

## 15. Future Validator Test Requirements

Future P1-S12 validator implementation must include tests for at least:

```text
valid minimal candidate passes
missing top-level required field fails
unknown source_id fails
ineligible source family fails
RAZ wordlist as direct vocabulary authority fails
source_payload_copied true fails
learner_facing_allowed true fails
public_distribution_allowed true fails
authority_promotion_allowed true fails
requires_evidence false fails
missing answer_evidence_ref fails
missing evidence locator fails
learner_placement_allowed true fails
multi_skill_expansion_allowed true fails
student_html_created true fails
worksheet_created true fails
learner_state_updated true fails
adaptive_recommendation_created true fails
large_scale_generation_performed true fails
manual_review_pending returns warning or pass_with_warnings
structured report emitted for invalid JSON if possible
```

---

## 16. P1-M1 Exit Rule

P1-M1 exit gate requires:

```text
P1-S3 item schema design exists.
P1-S4 machine-readable schema exists.
P1-S4 schema contract tests exist.
P1-S5 validator contract exists.
```

After this task:

```text
E4S-P1-M1_ReadingSchemaAndCandidateContract -> COMPLETED
```

No validator implementation is created by this task. Validator implementation remains scheduled for P1-S12 after query, pilot policy, pilot builder, and pilot readback gates.

---

## 17. Acceptance Gates for P1-S5

| Gate | Result | Evidence |
|---|---:|---|
| Governance MD checked | PASS | Section 2 |
| Current task appears in task queue | PASS | Section 2 |
| P1-S3 completion checked | PASS | Section 2 |
| P1-S4 schema dependency checked | PASS | Section 2 |
| Allowed file scope locked | PASS | Section 3 |
| Forbidden files listed | PASS | Section 3 |
| Validator purpose defined | PASS | Section 4 |
| Validator inputs defined | PASS | Section 5 |
| Validation stages defined | PASS | Section 6 |
| Blocking issue codes defined | PASS | Section 7 |
| Warning issue codes defined | PASS | Section 8 |
| Source eligibility validation rules defined | PASS | Section 9 |
| Schema validation rules defined | PASS | Section 10 |
| Evidence validation rules defined | PASS | Section 11 |
| Blocked output validation rules defined | PASS | Section 12 |
| Report shape defined | PASS | Section 13 |
| Future CLI contract defined | PASS | Section 14 |
| Future validator test requirements defined | PASS | Section 15 |
| P1-M1 exit rule defined | PASS | Section 16 |
| Runtime impact avoided | PASS | Documentation only |
| Validator implementation avoided | PASS | No validator code |
| Query implementation avoided | PASS | No query helper |
| Pilot generation avoided | PASS | No candidate JSON |
| Source payload extraction avoided | PASS | No payload copied |
| Learner state avoided | PASS | No learner files |
| Student-facing output avoided | PASS | No HTML / worksheet output |
| Promotion avoided | PASS | Design only |

---

## 18. Warning Register

```text
warning_id: E4S-P1-S5-WARN-001
severity: medium
classification: VALIDATOR_NOT_IMPLEMENTED
message: This task defines validator contract only. Validator implementation belongs to P1-S12.
blocks_current_task: no
```

```text
warning_id: E4S-P1-S5-WARN-002
severity: medium
classification: JSON_SCHEMA_RUNTIME_NOT_TESTED
message: P1-S4 added schema contract tests, but this task did not run local Python tests or GitHub Actions CI.
blocks_current_task: no
```

```text
warning_id: E4S-P1-S5-WARN-003
severity: medium
classification: PAYLOAD_VALIDATION_DEFERRED
message: Source payload validation remains deferred until a future explicit payload policy permits inspection.
blocks_current_task: no
```

---

## 19. Deferred Issues Register

```text
issue_id: E4S-P1-S5-DEFER-001
severity: high
affected_file_or_artifact: tools/validate_reading_v1_candidates.py
classification: FUTURE_WORK
why_deferred: P1-S5 defines validator contract only. Validator implementation is scheduled for P1-S12.
recommended_future_task: E4S-P1-S12_ReadingV1_CandidateValidator_Implementation
blocks_current_task: no
```

```text
issue_id: E4S-P1-S5-DEFER-002
severity: high
affected_file_or_artifact: Reading V1 source query layer
classification: FUTURE_WORK
why_deferred: P1-M2 must define and implement deterministic metadata query before pilot generation.
recommended_future_task: E4S-P1-S6_ReadingV1_SourceQueryLayer_DesignScan
blocks_current_task: no
```

```text
issue_id: E4S-P1-S5-DEFER-003
severity: high
affected_file_or_artifact: Reading V1 pilot candidates
classification: FUTURE_WORK
why_deferred: Pilot generation remains blocked until query design/implementation, pilot policy, and explicit tiny-pilot approval.
recommended_future_task: E4S-P1-S10_ReadingV1_PilotCandidateBuilder_Implementation after required gates
blocks_current_task: no
```

---

## 20. Distance Vector

P0 state:

```text
E4S-P0_SourceAuthorityAndCorpusRoadmap -> CLOSED_AS_SOURCE_AUTHORITY_FOUNDATION
D_P0 = 0
```

P1 state after this task:

```text
E4S-P1_ReadingV1SourceGroundedPractice -> ACTIVE_QUERY_GATE_READY
```

Current task status:

```text
E4S-P1-S5_ReadingV1_ValidatorContract_DesignScan -> COMPLETED
```

P1-M1 state:

```text
E4S-P1-M1_ReadingSchemaAndCandidateContract -> COMPLETED
D_P1_M1 = 0 small tasks left
```

P1 remaining small-task distance:

```text
D_P1 = 13 small tasks left
```

Next middle task:

```text
E4S-P1-M2_QueryAndSourceRouting
```

Next small task:

```text
E4S-P1-S6_ReadingV1_SourceQueryLayer_DesignScan
```

---

## 21. Mandatory Handoff Block

```text
GOVERNANCE_MD_CHECK = PASS
CURRENT_TASK_IN_CONTRACT = PASS
CURRENT_TASK_SCOPE_LOCK = PASS
FORBIDDEN_OUTPUT_CHECK = PASS
FILES_CREATED_OR_MODIFIED = docs/ulga/E4S_P1_READING_V1_VALIDATOR_CONTRACT.md
ACCEPTANCE_GATES = PASS_WITH_WARNINGS
DISTANCE_VECTOR_UPDATE = D_P1_M1 = 0; D_P1 = 13
NEXT_TASK_IN_CONTRACT = PASS
NEXT_TASK_ID = E4S-P1-S6_ReadingV1_SourceQueryLayer_DesignScan
DRIFT_RISK = low
DRIFT_REASON = Validator contract is defined, but validator code and pilot generation remain blocked until later gates.
REQUIRED_ACTION = continue with P1-S6 only
```

---

## 22. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P1-S6_ReadingV1_SourceQueryLayer_DesignScan
```

Only next allowed action:

```text
Create docs/ulga/E4S_P1_READING_V1_SOURCE_QUERY_LAYER.md to define deterministic metadata-only source query logic over eligible Reading V1 sources. Do not implement the query helper, generate Reading candidates, extract source payloads, create learner-facing output, create learner state, or promote authority.
```

Stop here until the operator explicitly starts P1-S6.

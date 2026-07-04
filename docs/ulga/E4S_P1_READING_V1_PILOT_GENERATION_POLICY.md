# E4S P1 Reading V1 Pilot Generation Policy Design Scan

## 1. Current State

```text
Epic: E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
Phase: E4S-P1_ReadingV1SourceGroundedPractice
Middle Task: E4S-P1-M3_SmallPilotCandidateGeneration
Small Task: E4S-P1-S9_ReadingV1_PilotGenerationPolicy_DesignScan
Deliverable: docs/ulga/E4S_P1_READING_V1_PILOT_GENERATION_POLICY.md
```

This task defines the strict tiny-pilot policy that must exist before any Reading V1 pilot candidate builder can run. It is policy-only. It does not implement the builder, generate Reading candidates, create Reading questions, read source payloads, create learner-facing output, create learner state, or upgrade source authority.

---

## 2. Governance and Queue Readback

Task queue evidence:

```text
E4S-P1-S9_ReadingV1_PilotGenerationPolicy_DesignScan -> DesignScan / PilotPolicy
E4S-P1-S10_ReadingV1_PilotCandidateBuilder_Implementation -> Implementation / SmallPilotOnly
E4S-P1-S11_ReadingV1_PilotCandidateReadbackQA -> QA / Readback
```

P1-M3 exit gate:

```text
P1-M3 exits only when a small pilot exists, passes schema/trace checks, and is not student-facing.
```

Predecessor state required before P1-S9:

```text
E4S-P1-M0_ActivationAndScopeGate -> COMPLETED
E4S-P1-M1_ReadingSchemaAndCandidateContract -> COMPLETED
E4S-P1-M2_QueryAndSourceRouting -> COMPLETED
E4S-P1-S8_ReadingV1_SourceQueryLayer_ReadbackQA -> COMPLETED
```

Readback result:

```text
GOVERNANCE_MD_CHECK = PASS
CURRENT_TASK_IN_CONTRACT = PASS
CURRENT_TASK_SCOPE_LOCK = PASS
```

---

## 3. Task Boundary

Allowed file:

```text
docs/ulga/E4S_P1_READING_V1_PILOT_GENERATION_POLICY.md
```

Files explicitly not changed by this task:

```text
tools/build_reading_v1_pilot_candidates.py
tools/query_e4s_reading_v1_sources.py
tools/validate_reading_v1_candidates.py
ulga/reports/reading_v1_pilot_summary.json
Reading candidate JSON
source text payloads
student HTML
worksheet output
learner event files
learner state files
adaptive path files
authority upgrade artifacts
large generated artifacts
```

Runtime impact:

```text
NONE
```

---

## 4. Pilot Purpose

The future tiny pilot may test only whether the Reading V1 pipeline can create a very small, source-traceable, schema-shaped candidate set from eligible metadata routes.

The pilot may test:

```text
source_trace preservation
source_policy snapshot preservation
basic question_model shape
answer_model evidence linkage
evidence_model locator requirement
level / situation / skill metadata shape
blocked_output_state remains false
audit_trail presence
summary report generation
```

The pilot must not test:

```text
large-scale generation
student-facing Reading delivery
worksheet export
learner response collection
learner state mutation
mastery scoring
adaptive recommendation
spaced review scheduling
source/content authority upgrade
multi-skill expansion
```

---

## 5. Tiny Pilot Size Limit

Default pilot limit:

```text
max_candidate_count = 3
```

Hard cap:

```text
hard_max_candidate_count = 5
```

P1-S10 must fail or block if requested output exceeds the hard cap.

Pilot count rules:

```text
- Default run creates at most 3 candidate records.
- Operator may explicitly request up to 5 for smoke testing.
- More than 5 is not a pilot and must be rejected.
- Candidate count must be reported in reading_v1_pilot_summary.json.
```

---

## 6. Allowed Pilot Source Inputs

Primary source route:

```text
RAZ_READING_CORPUS_A_T_CANDIDATE
query_class = PRIMARY_READING_CANDIDATE_INPUT
role = reading_corpus_candidate
```

Supporting evidence route:

```text
RAZ_WORDLIST_A_T_EVIDENCE
query_class = SUPPORTING_READING_EXPOSURE_EVIDENCE
role = evidence_only
```

Reference-only routes:

```text
EGP_SOURCE_ENGLISH_GRAMMAR_PROFILE_ONLINE
EVP_SOURCE_ENGLISH_VOCABULARY_PROFILE_ONLINE
NGSL_SOURCE_FREQUENCY_PROFILE
CHUNK_SAFE_LAYER_REFERENCE
```

Blocked routes:

```text
status_artifact
generated_content_candidate
assessment_pattern_corpus
writing_template_corpus
parent_functional_sentence_corpus
story_dialogue_corpus
governance
roadmap
unknown or invalid source family
```

Hard source rule:

```text
Only metadata returned by tools/query_e4s_reading_v1_sources.py may be consumed by P1-S10. P1-S10 must not read source text payloads directly.
```

---

## 7. Pilot Payload Policy

P1-S10 must generate candidate records from metadata only.

Allowed candidate payload references:

```text
passage_ref = metadata locator or placeholder locator
source_path_ref = manifest path reference
source_unit_ref_policy = locator_only_until_payload_policy
content_hash = optional placeholder only if no source payload is read
```

Blocked payload handling:

```text
copying full passage text
copying passage excerpts
copying evidence text
reading source PDF/text payloads
embedding copyrighted or restricted text
creating learner-facing display text from source payload
```

Required default values:

```text
source_payload_copied = false
passage_excerpt_allowed = false
evidence_text_allowed = false
```

Until an explicit payload policy permits source text access, P1 pilot evidence must be locator-only or metadata-reference only.

---

## 8. Allowed Pilot Question Types

Initial pilot question types may use only the P1-S3/P1-S4 allowed list:

```text
literal_who
literal_what
literal_where
literal_when
literal_yes_no
literal_count
literal_color
literal_action
sequence_order
main_idea_simple
vocabulary_in_context_basic
```

Recommended tiny-pilot subset:

```text
literal_what
literal_where
literal_yes_no
```

Blocked question types:

```text
inference
cause_effect
compare_contrast
author_purpose
open_ended_explanation
multi_source_reasoning
```

Pilot question text rule:

```text
Question text may be template-based and source-trace-linked, but must not require copied source passage text in P1-S10.
```

---

## 9. Answer and Evidence Policy

Every pilot candidate must include:

```text
answer_model.answer_evidence_ref
evidence_model.evidence_id
evidence_model.source_trace_ref
evidence_model.evidence_locator
evidence_model.evidence_text_allowed = false
```

Allowed evidence forms:

```text
source_locator_only
metadata_reference
manual_review_note
```

Blocked evidence forms:

```text
model assertion without trace
unlocated answer key
copied source text without policy
learner answer history
```

If an item cannot provide locator-only evidence, it must be marked `manual_review_required = true` or blocked.

---

## 10. Required Candidate Defaults

P1-S10 generated pilot candidates must default to:

```text
schema_version = READING_V1_CANDIDATE_SCHEMA_V1
phase_id = E4S-P1_ReadingV1SourceGroundedPractice
candidate_status = candidate_generated
source_payload_copied = false
public_distribution_allowed = false
learner_facing_allowed = false
authority_promotion_allowed = false
question_language = en
requires_evidence = true
learner_placement_allowed = false
skill_fit = reading_candidate
target_phase = E4S-P1_ReadingV1SourceGroundedPractice
multi_skill_expansion_allowed = false
```

All `blocked_output_state` fields must remain false:

```text
learner_facing_output_created
student_html_created
worksheet_created
learner_event_created
learner_state_updated
adaptive_recommendation_created
authority_promotion_performed
large_scale_generation_performed
```

---

## 11. Pilot Builder Input Contract

Future P1-S10 builder may read:

```text
ulga/graph/e4s_source_manifest.json
ulga/schemas/reading_v1_candidate.schema.json
metadata-only query helper output or in-memory query result
docs/ulga/E4S_P1_READING_V1_SOURCE_ELIGIBILITY_CONTRACT.md
docs/ulga/E4S_P1_READING_V1_ITEM_SCHEMA.md
docs/ulga/E4S_P1_READING_V1_VALIDATOR_CONTRACT.md
docs/ulga/E4S_P1_READING_V1_SOURCE_QUERY_LAYER.md
docs/ulga/E4S_P1_READING_V1_PILOT_GENERATION_POLICY.md
```

Future P1-S10 builder must not read:

```text
source PDFs or source text payloads
learner profiles
learner states
learner answer histories
adaptive queues
student-facing HTML
worksheet exports
generated candidate pool as source authority
```

---

## 12. Pilot Builder Output Contract

P1-S10 may create only these artifacts:

```text
tools/build_reading_v1_pilot_candidates.py
ulga/reports/reading_v1_pilot_summary.json
tests for tiny-pilot generation policy
```

Optional candidate artifact policy:

```text
If P1-S10 needs to emit candidate records, it must emit a tiny pilot artifact under an approved reports or derived path and must list the path explicitly in its handoff. The artifact must contain at most hard_max_candidate_count records.
```

P1-S10 must not create:

```text
student HTML
worksheet export
public distribution package
learner event log
learner state
adaptive recommendation
source/content authority upgrade
large candidate dataset
```

---

## 13. Pilot Summary Report Requirements

`ulga/reports/reading_v1_pilot_summary.json` must include at least:

```text
schema_version
phase_id
task_id
pilot_policy_ref
candidate_count
hard_max_candidate_count
source_query_report_ref
source_ids_used
question_types_used
metadata_only
payload_access_allowed
learner_facing_allowed
authority_upgrade_allowed
blocked_output_state_summary
validation_readiness
warnings
issues
next_shortest_step
```

Required summary values:

```text
metadata_only = true
payload_access_allowed = false
learner_facing_allowed = false
authority_upgrade_allowed = false
candidate_count <= hard_max_candidate_count
next_shortest_step = E4S-P1-S11_ReadingV1_PilotCandidateReadbackQA
```

---

## 14. Pilot Failure Conditions

P1-S10 must fail or block if:

```text
candidate_count > hard_max_candidate_count
no primary Reading source is available
query helper report status is FAIL or BLOCKED
any candidate has source_payload_copied = true
any candidate has learner_facing_allowed = true
any candidate has authority_promotion_allowed = true
any blocked_output_state field is true
any blocked source class is used as candidate source input
RAZ wordlist is used as direct vocabulary authority
question_type is outside allowed list
answer_evidence_ref is missing
evidence_locator is missing
student HTML or worksheet output is attempted
learner state or adaptive output is attempted
source/content authority upgrade is attempted
```

---

## 15. P1-S10 Test Requirements

Future P1-S10 tests must cover at least:

```text
default pilot candidate count is <= 3
hard cap blocks more than 5 candidates
primary RAZ reading source is used only as trace seed
RAZ wordlist remains evidence-only
reference sources remain reference-only
blocked sources are not used as candidate source input
candidate records conform to reading_v1_candidate.schema.json
source_payload_copied remains false
passage_excerpt_allowed remains false
evidence_text_allowed remains false
payload_access_allowed remains false
learner_facing_allowed remains false
authority_upgrade_allowed remains false
all blocked_output_state fields remain false
pilot summary report includes candidate_count and next_shortest_step
no source payload file is opened by builder
```

---

## 16. Acceptance Gates for P1-S9

| Gate | Result | Evidence |
|---|---:|---|
| Governance/task queue checked | PASS | Section 2 |
| P1-M2 completion checked | PASS | Section 2 |
| Allowed file scope locked | PASS | Section 3 |
| Pilot purpose defined | PASS | Section 4 |
| Tiny pilot size limit defined | PASS | Section 5 |
| Allowed source inputs defined | PASS | Section 6 |
| Payload policy defined | PASS | Section 7 |
| Allowed question types defined | PASS | Section 8 |
| Answer/evidence policy defined | PASS | Section 9 |
| Candidate defaults defined | PASS | Section 10 |
| Builder input contract defined | PASS | Section 11 |
| Builder output contract defined | PASS | Section 12 |
| Summary report requirements defined | PASS | Section 13 |
| Failure conditions defined | PASS | Section 14 |
| Future tests defined | PASS | Section 15 |
| Builder implementation avoided | PASS | No builder code |
| Pilot candidate generation avoided | PASS | No candidate JSON |
| Source payload access avoided | PASS | No source text copied |
| Learner-facing output avoided | PASS | No HTML / worksheet output |
| Runtime state avoided | PASS | No runtime files |
| Source upgrade avoided | PASS | Design only |

Result:

```text
ACCEPTANCE_GATES = PASS_WITH_WARNINGS
```

---

## 17. Warning Register

```text
warning_id: E4S-P1-S9-WARN-001
severity: medium
classification: PILOT_BUILDER_NOT_IMPLEMENTED
message: This task defines pilot generation policy only. Tiny pilot builder implementation belongs to P1-S10.
blocks_current_task: no
```

```text
warning_id: E4S-P1-S9-WARN-002
severity: medium
classification: PAYLOAD_POLICY_RESTRICTIVE
message: P1-S9 keeps payload access blocked. Pilot items must use locator-only or metadata-reference evidence until a future payload policy exists.
blocks_current_task: no
```

```text
warning_id: E4S-P1-S9-WARN-003
severity: medium
classification: NO_TEST_RUN
message: This DesignScan is documentation-only. No local Python tests or GitHub Actions CI were run.
blocks_current_task: no
```

---

## 18. Deferred Issues Register

```text
issue_id: E4S-P1-S9-DEFER-001
severity: high
affected_file_or_artifact: tools/build_reading_v1_pilot_candidates.py
classification: FUTURE_WORK
why_deferred: P1-S9 defines policy only. Builder implementation is scheduled for P1-S10.
recommended_future_task: E4S-P1-S10_ReadingV1_PilotCandidateBuilder_Implementation
blocks_current_task: no
```

```text
issue_id: E4S-P1-S9-DEFER-002
severity: high
affected_file_or_artifact: Reading V1 pilot candidate artifact
classification: FUTURE_WORK
why_deferred: Candidate artifact creation is blocked until P1-S10.
recommended_future_task: E4S-P1-S10_ReadingV1_PilotCandidateBuilder_Implementation
blocks_current_task: no
```

```text
issue_id: E4S-P1-S9-DEFER-003
severity: high
affected_file_or_artifact: source payload policy
classification: FUTURE_WORK
why_deferred: Source payload access remains blocked until an explicit future policy task permits it.
recommended_future_task: future payload policy task, not P1-S9
blocks_current_task: no
```

---

## 19. Distance Vector

```text
E4S-P0_SourceAuthorityAndCorpusRoadmap -> CLOSED_AS_SOURCE_AUTHORITY_FOUNDATION
D_P0 = 0

E4S-P1_ReadingV1SourceGroundedPractice -> ACTIVE_TINY_PILOT_BUILDER_READY
E4S-P1-S9_ReadingV1_PilotGenerationPolicy_DesignScan -> COMPLETED

D_P1_M3 = 2 small tasks left
D_P1 = 9 small tasks left
```

Remaining P1-M3 tasks:

```text
E4S-P1-S10_ReadingV1_PilotCandidateBuilder_Implementation
E4S-P1-S11_ReadingV1_PilotCandidateReadbackQA
```

---

## 20. Mandatory Handoff Block

```text
GOVERNANCE_MD_CHECK = PASS
CURRENT_TASK_IN_CONTRACT = PASS
CURRENT_TASK_SCOPE_LOCK = PASS
FORBIDDEN_OUTPUT_CHECK = PASS
FILES_CREATED_OR_MODIFIED = docs/ulga/E4S_P1_READING_V1_PILOT_GENERATION_POLICY.md
ACCEPTANCE_GATES = PASS_WITH_WARNINGS
DISTANCE_VECTOR_UPDATE = D_P1_M3 = 2; D_P1 = 9
NEXT_TASK_IN_CONTRACT = PASS
NEXT_TASK_ID = E4S-P1-S10_ReadingV1_PilotCandidateBuilder_Implementation
DRIFT_RISK = low
DRIFT_REASON = Tiny-pilot policy is now defined, but builder and candidate artifact generation remain blocked until P1-S10.
REQUIRED_ACTION = continue with P1-S10 only
```

---

## 21. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P1-S10_ReadingV1_PilotCandidateBuilder_Implementation
```

Only next allowed action:

```text
Create tools/build_reading_v1_pilot_candidates.py, ulga/reports/reading_v1_pilot_summary.json, and tests for a metadata-only tiny pilot bounded by max_candidate_count = 3 and hard_max_candidate_count = 5. Do not read source payloads, create learner-facing output, create learner state, create adaptive recommendations, or upgrade source authority.
```

Stop here until the operator explicitly starts P1-S10.

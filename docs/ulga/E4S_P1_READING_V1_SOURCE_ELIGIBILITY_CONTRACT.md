# E4S P1 Reading V1 Source Eligibility and Input Contract Design Scan

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
E4S-P1-M0_ActivationAndScopeGate
```

Current Small Task:

```text
E4S-P1-S1_ReadingV1_SourceEligibilityAndInputContract_DesignScan
```

Deliverable:

```text
docs/ulga/E4S_P1_READING_V1_SOURCE_ELIGIBILITY_CONTRACT.md
```

This task defines the formal source eligibility and input boundary for Reading V1. It converts the preliminary P1-S0 source-lane scope into a concrete P1 input contract. It does not generate Reading questions, extract source payloads, build schemas, build validators, create learner-facing HTML, create worksheets, create learner state, or promote any source/content authority.

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

P1-S0 source:

```text
docs/ulga/E4S_P1_READING_V1_ACTIVATION_SCOPE_GATE.md
```

P1-S0 dependency result:

```text
E4S-P1-S0_ReadingV1SourceGroundedPractice_ActivationAndScopeGate -> COMPLETED
```

P1-S1 is a DesignScan / input-contract task only.

---

## 3. Task Boundary

Task type:

```text
DesignScan / SourceEligibilityContract
```

Allowed file:

```text
docs/ulga/E4S_P1_READING_V1_SOURCE_ELIGIBILITY_CONTRACT.md
```

Forbidden files and paths:

```text
tools/build_e4s_source_manifest.py
tools/validate_e4s_source_manifest.py
tools/query_e4s_reading_v1_sources.py
tools/build_reading_v1_pilot_candidates.py
tools/validate_reading_v1_candidates.py
ulga/graph/e4s_source_manifest.json
ulga/reports/e4s_source_manifest_summary.json
ulga/schemas/reading_v1_candidate.schema.json
site HTML
student-facing Reading practice HTML
worksheet exports
large generated artifacts
source corpus payloads
learner state files
learner profile files
adaptive scheduling files
dependency graph artifacts
promotion artifacts
```

Generated artifact policy:

```text
No generated Reading questions, candidate JSON, learner-facing files, learner events, or large JSON artifacts are allowed in P1-S1.
```

Runtime impact:

```text
NONE
```

Promotion impact:

```text
NONE. P1-S1 performs no source/content authority promotion.
```

---

## 4. Reading V1 Eligibility Principle

Reading V1 source eligibility is not the same as source authority.

Eligibility means:

```text
The source may be considered as metadata, trace, reference, evidence, or candidate input for future Reading V1 tasks, under its allowed_use / blocked_use / promotion_rule.
```

Eligibility does not mean:

```text
The source is learner-facing.
The source is content authority.
The source may be publicly distributed.
The source may generate questions directly.
The source may update learner state.
The source may be promoted without review.
```

All P1 source use must preserve:

```text
source_id
source_family
authority_role
path
license_status
review_status
allowed_use
blocked_use
promotion_rule
risk_flags
source trace
```

---

## 5. Formal P1 Reading V1 Source Eligibility Matrix

| Eligibility Class | Manifest Record / Selector | P1 Reading V1 Use | Required Constraints | Blocked Use |
|---|---|---|---|---|
| `PRIMARY_READING_CANDIDATE_INPUT` | `source_id = RAZ_READING_CORPUS_A_T_CANDIDATE` | reading candidate selection, future query index design, source trace only | must keep `source_trace_required`; must respect restricted license; no payload copied in P1-S1 | learner-facing output, public distribution, automatic promotion, final authority promotion, direct reading authority |
| `SUPPORTING_READING_EXPOSURE_EVIDENCE` | `source_id = RAZ_WORDLIST_A_T_EVIDENCE` | exposure evidence, rough source ordering support, reading candidate selection support | evidence-only; may not become vocabulary authority; must preserve source trace | direct vocabulary authority, direct question generation, learner-facing output, public distribution, promotion |
| `SCHEMA_REFERENCE_ONLY_GRAMMAR` | `source_id = EGP_SOURCE_ENGLISH_GRAMMAR_PROFILE_ONLINE` | future schema / validation reference only | reference metadata only; no payload extraction in P1-S1 | direct grammar authority, learner-facing output, public distribution, promotion |
| `SCHEMA_REFERENCE_ONLY_VOCABULARY` | `source_id = EVP_SOURCE_ENGLISH_VOCABULARY_PROFILE_ONLINE` | future vocabulary constraint reference only | reference metadata only; no payload extraction in P1-S1 | direct vocabulary authority, learner-facing output, public distribution, promotion |
| `SCHEMA_REFERENCE_ONLY_FREQUENCY` | `source_id = NGSL_SOURCE_FREQUENCY_PROFILE` | future readability / frequency reference only | reference metadata only; no payload extraction in P1-S1 | final vocabulary authority, learner-facing output, public distribution, promotion |
| `SCHEMA_REFERENCE_ONLY_CHUNK` | `source_id = CHUNK_SAFE_LAYER_REFERENCE` | future sentence/chunk constraint reference only | reference metadata only; no learner-facing use | automatic promotion, final authority promotion, learner-facing output |
| `STATUS_AUDIT_ONLY` | `source_id = STATUS_RAZ_AW_V1_SNAPSHOT` | audit/readback only | status artifact remains project progress only | Reading source, learner progress, learner-facing output, direct reading authority, app runtime use |
| `GENERATED_CANDIDATE_BLOCKED_FOR_P1_INPUT` | `source_id = GENERATED_CONTENT_CANDIDATE_POOL` | no P1 input use except blocked-example documentation | generated candidate remains review-only | authority, learner-facing output, direct reading authority, large-scale generation, promotion |
| `OUT_OF_SCOPE_SKILL_CANDIDATE` | `source_family in {assessment_pattern_corpus, writing_template_corpus, parent_functional_sentence_corpus, story_dialogue_corpus}` | none in P1-S1 except cross-phase boundary documentation | defer to owning phase | Reading V1 input, learner-facing output, direct authority, promotion |
| `GOVERNANCE_ONLY` | `source_family in {governance, roadmap}` | task control, audit, source-of-truth readback | not content | Reading source, generated practice, learner-facing output |

---

## 6. RAZ Reading Corpus Input Contract

Record:

```text
source_id = RAZ_READING_CORPUS_A_T_CANDIDATE
source_family = raz_reading_corpus
authority_role = reading_corpus_candidate
target_phase = E4S-P1_ReadingV1SourceGroundedPractice
```

Allowed P1 uses:

```text
source_trace_only
query_index_design
reading_candidate_selection
```

P1-S1 constraints:

```text
- Treat as candidate input only.
- Preserve source_id and source trace in every future derived artifact.
- Do not copy or redistribute source payload in P1-S1.
- Do not expose learner-facing content in P1-S1.
- Do not treat as direct reading authority.
- Do not use it for public distribution.
- Do not use it for learner placement or adaptive recommendation.
```

Future use requirement:

```text
Before any Reading V1 pilot candidate can use this source, P1 must define item schema, validator contract, pilot generation policy, source trace fields, and QA readback.
```

---

## 7. RAZ Wordlist Evidence Contract

Record:

```text
source_id = RAZ_WORDLIST_A_T_EVIDENCE
source_family = raz_wordlist
authority_role = evidence_only
target_phase = E4S-P1_ReadingV1SourceGroundedPractice
```

Allowed P1 uses:

```text
source_trace_only
reading_candidate_selection
exposure evidence
rough ordering support
```

Blocked P1 uses:

```text
direct_vocab_authority
direct question generation
learner-facing output
public distribution
automatic promotion
final authority promotion
```

Hard rule:

```text
RAZ wordlist may help select or order Reading candidates, but it must never become Vocabulary Authority and must never directly generate Reading questions.
```

---

## 8. Reference-Only Source Contract

The following sources are reference-only for P1-S1:

```text
EGP_SOURCE_ENGLISH_GRAMMAR_PROFILE_ONLINE
EVP_SOURCE_ENGLISH_VOCABULARY_PROFILE_ONLINE
NGSL_SOURCE_FREQUENCY_PROFILE
CHUNK_SAFE_LAYER_REFERENCE
```

Allowed P1-S1 use:

```text
metadata readback
future schema design reference
future validator-design reference
future constraint vocabulary / grammar / frequency / chunk discussion
```

Blocked P1-S1 use:

```text
source payload extraction
learner-facing output
public distribution
direct grammar authority
direct vocabulary authority
final authority promotion
automatic promotion
```

Reference-only sources must remain secondary to the Reading source trace. They cannot override the primary reading candidate record.

---

## 9. Explicitly Ineligible Sources for Reading V1 Input

These source classes are not eligible for Reading V1 input in P1-S1:

```text
status_artifact
generated_content_candidate
assessment_pattern_corpus
writing_template_corpus
parent_functional_sentence_corpus
story_dialogue_corpus
unknown
```

Reason:

```text
They either belong to another phase, are status/progress artifacts, are generated/review-only, or are not content authority for Reading V1.
```

They may appear in documentation only as boundary examples.

---

## 10. P1 Input Data Classes

P1-S1 defines these future input classes for later P1 tasks:

| Input Class | Meaning | May Be Machine-Readable Later? | P1-S1 Output? |
|---|---|---:|---:|
| `reading_source_trace` | trace to eligible reading source record and source location | yes, after schema gate | no |
| `reading_candidate_selector` | metadata selector over eligible source records | yes, after query design | no |
| `exposure_evidence_ref` | non-authority evidence from wordlist or source metadata | yes, after schema gate | no |
| `reference_constraint_ref` | grammar/vocab/frequency/chunk reference metadata | yes, after schema gate | no |
| `blocked_source_ref` | explicit blocked-source example for validation | yes, after validator contract | no |

No machine-readable input artifact is created by P1-S1.

---

## 11. Required Future Fields for Reading V1 Candidate Records

Future Reading V1 candidate records should include at least:

```text
reading_candidate_id
source_id
source_family
authority_role
source_trace
source_license_status
source_review_status
level_claim_status
situation_domain
skill_fit
question_type
answer_model
evidence_ref
blocked_output_status
validation_status
manual_review_status
```

This list is a design expectation only. P1-S1 does not create schemas or JSON artifacts.

---

## 12. Blocked Outputs in P1-S1

P1-S1 explicitly blocks:

```text
Reading V1 question generation
Reading candidate JSON generation
student-facing Reading HTML
worksheet generation
source payload extraction
large generated JSON artifacts
schema implementation
validator implementation
query helper implementation
learner event creation
learner state creation
learner placement
mastery scoring
adaptive recommendation
spaced review scheduling
source/content authority promotion
```

---

## 13. Acceptance Gates for P1-S1

| Gate | Result | Evidence |
|---|---:|---|
| Governance MD checked | PASS | Section 2 |
| Current task appears in governance contract | PASS | Section 2 |
| P1-S0 dependency checked | PASS | Section 2 |
| Allowed file scope locked | PASS | Section 3 |
| Forbidden files listed | PASS | Section 3 |
| Reading eligibility principle defined | PASS | Section 4 |
| Formal source eligibility matrix created | PASS | Section 5 |
| RAZ reading corpus input contract defined | PASS | Section 6 |
| RAZ wordlist evidence contract defined | PASS | Section 7 |
| Reference-only source contract defined | PASS | Section 8 |
| Ineligible source classes defined | PASS | Section 9 |
| Future input data classes defined | PASS | Section 10 |
| Future candidate fields listed | PASS | Section 11 |
| Blocked outputs recorded | PASS | Section 12 |
| Runtime impact avoided | PASS | Documentation only |
| Manifest modification avoided | PASS | No JSON change |
| Builder / validator modification avoided | PASS | No Python change |
| Source payload extraction avoided | PASS | No payload copied |
| Learner state avoided | PASS | No learner files |
| Student-facing output avoided | PASS | No HTML / worksheet output |
| Promotion avoided | PASS | Design only |

---

## 14. Warning Register

```text
warning_id: E4S-P1-S1-WARN-001
severity: medium
classification: SOURCE_PAYLOAD_NOT_INSPECTED
message: P1-S1 uses manifest metadata and source-contract rules only. It does not inspect or extract source payloads.
blocks_current_task: no
```

```text
warning_id: E4S-P1-S1-WARN-002
severity: medium
classification: ELIGIBILITY_NOT_SCHEMA
message: This contract defines eligible source inputs but does not define the Reading V1 item schema.
blocks_current_task: no
```

```text
warning_id: E4S-P1-S1-WARN-003
severity: medium
classification: NO_TEST_RUN
message: This DesignScan is documentation-only. No local Python tests or GitHub Actions CI were run.
blocks_current_task: no
```

---

## 15. Deferred Issues Register

```text
issue_id: E4S-P1-S1-DEFER-001
severity: high
affected_file_or_artifact: P1 Reading V1 task queue
classification: FUTURE_WORK
why_deferred: P1-S1 defines eligibility only. P1-S2 must define the phase task queue and distance vector.
recommended_future_task: E4S-P1-S2_ReadingV1_TaskQueueAndDistanceVector_DesignScan
blocks_current_task: no
```

```text
issue_id: E4S-P1-S1-DEFER-002
severity: high
affected_file_or_artifact: Reading V1 item schema
classification: FUTURE_WORK
why_deferred: Schema work belongs to P1-M1 after P1-M0 is complete.
recommended_future_task: E4S-P1-S3_ReadingV1_ItemSchema_DesignScan
blocks_current_task: no
```

```text
issue_id: E4S-P1-S1-DEFER-003
severity: high
affected_file_or_artifact: source query implementation
classification: FUTURE_WORK
why_deferred: Query helper implementation belongs to P1-M2 after query design.
recommended_future_task: E4S-P1-S7_ReadingV1_SourceQueryLayer_Implementation after P1-S6
blocks_current_task: no
```

---

## 16. Distance Vector

P0 state:

```text
E4S-P0_SourceAuthorityAndCorpusRoadmap -> CLOSED_AS_SOURCE_AUTHORITY_FOUNDATION
D_P0 = 0
```

P1 current state:

```text
E4S-P1_ReadingV1SourceGroundedPractice -> ACTIVE_SCOPE_GATE
```

Current task status:

```text
E4S-P1-S1_ReadingV1_SourceEligibilityAndInputContract_DesignScan -> COMPLETED
```

P1-M0 remaining tasks:

```text
D_P1_M0 = 1 small task left
```

P1 remaining small-task distance:

```text
D_P1 = 17 small tasks left
```

Remaining P1-M0 task:

```text
E4S-P1-S2_ReadingV1_TaskQueueAndDistanceVector_DesignScan
```

---

## 17. Mandatory Handoff Block

```text
GOVERNANCE_MD_CHECK = PASS
CURRENT_TASK_IN_CONTRACT = PASS
CURRENT_TASK_SCOPE_LOCK = PASS
FORBIDDEN_OUTPUT_CHECK = PASS
FILES_CREATED_OR_MODIFIED = docs/ulga/E4S_P1_READING_V1_SOURCE_ELIGIBILITY_CONTRACT.md
ACCEPTANCE_GATES = PASS_WITH_WARNINGS
DISTANCE_VECTOR_UPDATE = D_P1_M0 = 1; D_P1 = 17
NEXT_TASK_IN_CONTRACT = PASS
NEXT_TASK_ID = E4S-P1-S2_ReadingV1_TaskQueueAndDistanceVector_DesignScan
DRIFT_RISK = low
DRIFT_REASON = Source eligibility is now formalized, but no schema, query implementation, pilot generation, or learner-facing output was created.
REQUIRED_ACTION = continue with P1-S2 only
```

---

## 18. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P1-S2_ReadingV1_TaskQueueAndDistanceVector_DesignScan
```

Only next allowed action:

```text
Create docs/ulga/E4S_P1_READING_V1_TASK_QUEUE.md to define the P1 task queue, distance vector, next-task sequence, and mandatory handoff checks before P1 can move into schema design.
```

Stop here until the operator explicitly starts P1-S2.

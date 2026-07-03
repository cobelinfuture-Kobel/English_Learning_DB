# E4S Authority Mapping Matrix Design Scan

## 1. Current State

Epic ID:

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

Current Phase:

```text
E4S-P0_SourceAuthorityAndCorpusRoadmap
```

Current Sub-task:

```text
E4S-P0-S4_AuthorityMappingMatrix_DesignScan
```

Deliverable:

```text
docs/ulga/E4S_AUTHORITY_MAPPING_MATRIX.md
```

This task defines authority-lane routing for registered source families and authority roles. It does not modify the source manifest, builder, validator, summary artifact, runtime, generated content, Reading HTML, learner-facing output, or source promotion.

---

## 2. Task Boundary

Task:

```text
E4S-P0-S4_AuthorityMappingMatrix_DesignScan
```

Scope:

```text
Define how each E4S source_family and authority_role maps into an authority lane, what the source may support, what it must not support, and which future phase or review task owns escalation.
```

Allowed files:

```text
docs/ulga/E4S_AUTHORITY_MAPPING_MATRIX.md
```

Forbidden files:

```text
tools/build_e4s_source_manifest.py
tools/validate_e4s_source_manifest.py
ulga/graph/e4s_source_manifest.json
ulga/reports/e4s_source_manifest_summary.json
tests/test_build_e4s_source_manifest.py
tests/test_validate_e4s_source_manifest.py
runtime files
generators
validators
source adapters
site HTML
student-facing Reading practice HTML
large generated artifacts
source corpus payloads
learner state files
promotion artifacts
```

Current-task blockers:

```text
- No explicit source_family to authority-lane mapping document.
- No explicit authority_role to lane behavior document.
- No escalation matrix for evidence, candidate, template, status, governance, and generated sources.
```

Warning policy:

```text
Any mismatch discovered between actual source payload quality and intended lane is FUTURE_WORK unless it prevents this matrix from defining routing behavior.
```

Generated artifact policy:

```text
No generated artifacts are allowed in this task.
```

Runtime impact:

```text
NONE
```

Promotion impact:

```text
NONE. This matrix defines allowed promotion paths but performs no promotion.
```

Stop condition:

```text
Stop after source_family mapping, authority_role mapping, promotion/escalation behavior, invalid mappings, gates, distance vector, deferred issues, and next shortest step are documented.
```

---

## 3. Matrix Purpose

The Authority Mapping Matrix prevents sources from being flattened into a single content pool.

It answers:

```text
Which lane owns this source?
Can it be queried?
Can it support candidate generation?
Can it become learner-facing?
Can it ever become authority?
Which future task owns escalation?
```

This matrix is documentation-only. Enforcement belongs to the existing manifest validator and later authority-specific validators.

---

## 4. Authority Lane Definitions

| Lane ID | Lane Name | Function | Authority Status | P0 Behavior |
|---|---|---|---|---|
| `LANE_GOVERNANCE` | Governance Lane | Roadmaps, policies, task contracts | Not content authority | Register / guide only |
| `LANE_CORE_AUTHORITY_REFERENCE` | Core Authority Reference Lane | Grammar, vocabulary, frequency, chunk, morphology, theme, pattern references | Reference or existing authority only when separately proven | Metadata / reference only |
| `LANE_CAMBRIDGE_CANDIDATE` | Cambridge Candidate Lane | Cambridge vocabulary and assessment pattern sources | Candidate / review-needed | Register / design only |
| `LANE_RAZ_EVIDENCE` | RAZ Evidence Lane | RAZ word lists and exposure indicators | Evidence only | Exposure evidence only |
| `LANE_RAZ_READING_CANDIDATE` | RAZ Reading Candidate Lane | RAZ reading corpus candidates | Reading corpus candidate | Register / query design only |
| `LANE_WRITING_TEMPLATE` | Writing Template Lane | Writing templates and controlled writing structures | Template corpus | Template design only |
| `LANE_DIALOGUE_CANDIDATE` | Dialogue Candidate Lane | Parent functional sentences and story/dialogue corpora | Dialogue candidate / functional corpus | Register / candidate design only |
| `LANE_ASSESSMENT_PATTERN_CANDIDATE` | Assessment Pattern Lane | Assessment / worksheet / exam-pattern sources | Assessment pattern candidate | Pattern design only |
| `LANE_GENERATED_CANDIDATE_REVIEW` | Generated Candidate Review Lane | AI-generated or generated candidate content | Candidate only | Manual review only |
| `LANE_STATUS_ONLY` | Status Lane | Status snapshots, progress artifacts, readback pages | Not content | Progress tracking only |
| `LANE_UNKNOWN_PENDING_REVIEW` | Unknown Pending Review Lane | Unclassified sources | Blocked | Register metadata only |

---

## 5. Source Family to Authority Lane Matrix

| source_family | authority_role default | Authority Lane | Allowed P0 Use | Explicitly Blocked Use | Escalation Owner |
|---|---|---|---|---|---|
| `governance` | `governance_only` | `LANE_GOVERNANCE` | register, summarize, guide task scope | learner-facing output, content authority, promotion | none; governance only |
| `roadmap` | `governance_only` | `LANE_GOVERNANCE` | register, summarize, sequence tasks | learner-facing output, content authority, promotion | none; roadmap only |
| `grammar_profile` | `reference_only` | `LANE_CORE_AUTHORITY_REFERENCE` | metadata, internal reference, schema design | direct grammar authority without review, learner-facing output | future grammar authority review |
| `vocabulary_profile` | `reference_only` | `LANE_CORE_AUTHORITY_REFERENCE` | metadata, internal reference, schema design | direct vocabulary authority without review, learner-facing output | future vocabulary authority review |
| `frequency_profile` | `reference_only` | `LANE_CORE_AUTHORITY_REFERENCE` | metadata, frequency reference | final vocabulary authority, learner-facing output | future vocabulary/frequency review |
| `chunk_authority` | `reference_only` | `LANE_CORE_AUTHORITY_REFERENCE` | metadata, query-index design | automatic promotion, learner-facing output | future chunk authority review |
| `morphology_authority` | `reference_only` | `LANE_CORE_AUTHORITY_REFERENCE` | metadata, morphology reference | automatic promotion, learner-facing output | future morphology review |
| `theme_authority` | `reference_only` | `LANE_CORE_AUTHORITY_REFERENCE` | metadata, theme reference | automatic promotion, learner-facing output | future theme review |
| `pattern_authority` | `reference_only` | `LANE_CORE_AUTHORITY_REFERENCE` | metadata, pattern reference | automatic promotion, learner-facing output | future pattern review |
| `cambridge_vocabulary` | `candidate_only` | `LANE_CAMBRIDGE_CANDIDATE` | register, schema design, manual review | automatic promotion, public distribution, learner-facing output | P0-S4/P2 or later vocabulary review |
| `raz_wordlist` | `evidence_only` | `LANE_RAZ_EVIDENCE` | exposure evidence, reading candidate selection support | direct vocabulary authority, public distribution, learner-facing output | P1 Reading query design only |
| `raz_reading_corpus` | `reading_corpus_candidate` | `LANE_RAZ_READING_CANDIDATE` | source trace, query-index design, reading candidate selection | direct reading authority, learner-facing output during P0, public distribution | P1 Reading V1 validators |
| `writing_template_corpus` | `template_corpus` | `LANE_WRITING_TEMPLATE` | template design, writing candidate design | direct reading authority, learner-facing output during P0 | P3 Writing system |
| `parent_functional_sentence_corpus` | `functional_sentence_corpus` | `LANE_DIALOGUE_CANDIDATE` | dialogue/speaking candidate design | direct dialogue authority, learner-facing output during P0 | P4 Dialogue/Speaking review |
| `story_dialogue_corpus` | `dialogue_corpus_candidate` | `LANE_DIALOGUE_CANDIDATE` | dialogue candidate design | direct dialogue authority, learner-facing output during P0, public distribution if restricted | P4 Dialogue/Speaking review |
| `assessment_pattern_corpus` | `assessment_pattern_candidate` | `LANE_ASSESSMENT_PATTERN_CANDIDATE` | assessment pattern design | direct assessment authority, learner-facing output during P0 | P2 Assessment expansion |
| `generated_content_candidate` | `generated_candidate` | `LANE_GENERATED_CANDIDATE_REVIEW` | register, summarize, manual review only | final authority promotion, automatic promotion, learner-facing output, large-scale generation | future generated-content review + validator review |
| `status_artifact` | `status_only` | `LANE_STATUS_ONLY` | progress tracking, metadata summary | reading/content authority, learner-facing output, app runtime use | P0-S7 status reclassification |
| `google_drive_reference` | `reference_only` | `LANE_UNKNOWN_PENDING_REVIEW` | metadata placeholder only | promotion, learner-facing output | P0-S2/S4 source split refinement |
| `github_repository` | `reference_only` | `LANE_GOVERNANCE` | repo-level reference only | content promotion by repo implication | governance review |
| `unknown` | `unknown_pending_review` | `LANE_UNKNOWN_PENDING_REVIEW` | register metadata only | all candidate generation, learner-facing output, promotion | future intake review |

---

## 6. Authority Role to Behavior Matrix

| authority_role | Meaning | Query Allowed? | Candidate Generation Allowed? | Learner-facing Allowed? | Promotion Allowed? |
|---|---|---:|---:|---:|---:|
| `primary_authority` | Direct trusted authority for a specific layer after review | yes, if traceable | no by default | no in P0 | explicit promotion task only |
| `secondary_authority` | Supporting authority, not final judge | yes, if traceable | no by default | no in P0 | explicit promotion task only |
| `evidence_only` | Evidence of exposure or occurrence | yes, as evidence | no direct generation | no | never direct authority |
| `candidate_only` | Candidate material requiring review | metadata/query only | only after later task approval | no in P0 | review required |
| `template_corpus` | Template source for later writing/pattern derivation | yes, for design | no in P0 | no in P0 | derivation review required |
| `functional_sentence_corpus` | Functional sentence source for dialogue/speaking candidates | yes, for design | no in P0 | no in P0 | dialogue review required |
| `dialogue_corpus_candidate` | Dialogue candidate source | yes, for design | no in P0 | no in P0 | dialogue review required |
| `reading_corpus_candidate` | Reading source candidate | yes, for P1 design | no in P0 | no in P0 | P1 validators required |
| `assessment_pattern_candidate` | Assessment pattern source candidate | yes, for design | no in P0 | no in P0 | P2 review required |
| `generated_candidate` | Generated candidate content | metadata/manual review only | no in P0 | no | validator + manual review required |
| `status_only` | Progress/status artifact only | no content query | no | no | never content |
| `governance_only` | Governance or roadmap only | no content query | no | no | not content |
| `reference_only` | Reference context only | metadata/reference only | no | no | explicit review required |
| `unknown_pending_review` | Unclassified source | no | no | no | blocked |

---

## 7. Promotion and Escalation Rules

Promotion is never inferred from source existence, source family, source role, or manifest registration.

Required escalation rules:

```text
1. evidence_only -> cannot become authority directly.
2. status_only -> cannot become content authority.
3. governance_only -> cannot become content authority.
4. generated_candidate -> cannot become authority without manual review and validator review.
5. reading_corpus_candidate -> cannot become learner-facing until P1 Reading validators approve generated packages.
6. template_corpus -> cannot become writing practice output until P3 derives and validates exercises.
7. dialogue_corpus_candidate / functional_sentence_corpus -> cannot become speaking prompt authority until P4 review.
8. assessment_pattern_candidate -> cannot become assessment authority until P2 review.
9. unknown_pending_review -> cannot be queried for candidate generation.
```

---

## 8. Invalid Mapping Matrix

The following mappings are invalid and must stay blocked by future validators or review gates:

| Invalid Mapping | Reason | Required Handling |
|---|---|---|
| `raz_wordlist -> primary_authority` | RAZ word list is exposure evidence, not vocabulary authority | fail / block promotion |
| `raz_wordlist -> direct_vocab_authority` | Contract blocks direct vocabulary authority | fail |
| `status_artifact -> reading_corpus_candidate` | Status artifacts are progress evidence only | fail |
| `status_artifact -> learner_facing_output` | Status pages are not practice pages | fail |
| `generated_content_candidate -> primary_authority` | Generated content is not source authority | fail |
| `generated_content_candidate -> learner_facing_output` | Requires manual and validator review | fail |
| `writing_template_corpus -> direct_reading_authority` | Writing templates are not Reading authority | fail |
| `parent_functional_sentence_corpus -> direct_dialogue_authority` | Functional sentences are candidate material only | fail |
| `story_dialogue_corpus -> primary_authority before review` | Dialogue corpus remains candidate until reviewed | fail |
| `unknown -> candidate_generation` | Unknown source cannot drive generation | fail |

---

## 9. Current Manifest Coverage Snapshot

The current manifest summary registers 16 records across the active P0 lanes.

Current source families represented:

```text
assessment_pattern_corpus
cambridge_vocabulary
chunk_authority
frequency_profile
generated_content_candidate
governance
grammar_profile
parent_functional_sentence_corpus
raz_reading_corpus
raz_wordlist
roadmap
status_artifact
story_dialogue_corpus
vocabulary_profile
writing_template_corpus
```

Current authority roles represented:

```text
assessment_pattern_candidate
candidate_only
dialogue_corpus_candidate
evidence_only
functional_sentence_corpus
generated_candidate
governance_only
reading_corpus_candidate
reference_only
status_only
template_corpus
```

Coverage status:

```text
All currently represented manifest source families have a lane in this matrix.
All currently represented manifest authority roles have behavior rules in this matrix.
```

---

## 10. Acceptance Gates for P0-S4

| Gate | Result | Evidence |
|---|---:|---|
| Authority lane definitions created | PASS | Section 4 |
| source_family to lane matrix created | PASS | Section 5 |
| authority_role behavior matrix created | PASS | Section 6 |
| Promotion / escalation rules defined | PASS | Section 7 |
| Invalid mappings defined | PASS | Section 8 |
| Current manifest family coverage represented | PASS | Section 9 |
| Current manifest role coverage represented | PASS | Section 9 |
| Runtime impact avoided | PASS | Documentation only |
| Manifest modification avoided | PASS | No JSON change |
| Validator modification avoided | PASS | No Python change |
| Promotion avoided | PASS | Design only |

---

## 11. Distance Vector

Current Epic:

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

Current Phase:

```text
E4S-P0_SourceAuthorityAndCorpusRoadmap
```

Current Sub-task:

```text
E4S-P0-S4_AuthorityMappingMatrix_DesignScan
```

Sub-task Status:

```text
E4S-P0-S4_AuthorityMappingMatrix_DesignScan -> COMPLETED
```

P0 remaining distance after this sub-task:

```text
D_P0 = 3 sub-tasks left
```

Remaining P0 tasks:

```text
E4S-P0-S5_LevelSituationTaxonomy_DesignScan
E4S-P0-S6_LearningPathBoundaryContract_DesignScan
E4S-P0-S7_StatusArtifactReclassification_DocumentationPatch
```

---

## 12. Deferred Issues Register

```text
issue_id: E4S-P0-S4-DEFER-001
severity: medium
affected_file_or_artifact: tools/validate_e4s_source_manifest.py
classification: FUTURE_WORK
why_deferred: This task is design-only and does not update validator rules.
recommended_future_task: future validator matrix enforcement patch if needed
blocks_current_task: no
```

```text
issue_id: E4S-P0-S4-DEFER-002
severity: medium
affected_file_or_artifact: ulga/graph/e4s_source_manifest.json
classification: FUTURE_WORK
why_deferred: This task maps existing families and roles but does not add or edit source records.
recommended_future_task: future source manifest expansion or source split task
blocks_current_task: no
```

```text
issue_id: E4S-P0-S4-DEFER-003
severity: medium
affected_file_or_artifact: authority-specific promotion validators
classification: FUTURE_WORK
why_deferred: Promotion validators require later authority-specific implementation tasks.
recommended_future_task: post-P0 authority validation tasks
blocks_current_task: no
```

---

## 13. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P0-S5_LevelSituationTaxonomy_DesignScan
```

Only next allowed action:

```text
Create docs/ulga/E4S_LEVEL_SITUATION_TAXONOMY.md to define level and situation taxonomy boundaries for future Reading / Writing / Dialogue / Assessment source routing.
```

Stop here until the operator explicitly starts E4S-P0-S5.

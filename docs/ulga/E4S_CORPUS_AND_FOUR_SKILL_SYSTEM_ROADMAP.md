# E4S Corpus and Four-Skill Source-Grounded Practice System Roadmap

## 1. Current State

Epic ID:

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

Chinese Name:

```text
英語四技能來源可追蹤練習系統
```

Current Phase:

```text
E4S-P0_SourceAuthorityAndCorpusRoadmap
```

Current Sub-task:

```text
E4S-P0-S0_CorpusRoadmap_MasterDesignScan
```

Data Sources and Ordering Basis:

```text
1. 雲端智慧體開發交握公版 / 重點任務排程
2. RAZ-AW-V1 Status Snapshot
3. Project Task Expansion Control Policy
4. Existing English Learning DB authority architecture
```

External Storage Authorization:

```text
GitHub: AUTHORIZED_READ_WRITE
Google Drive: AUTHORIZED_READ_REFERENCE_ONLY
```

Deliverable for This Sub-task:

```text
docs/ulga/E4S_CORPUS_AND_FOUR_SKILL_SYSTEM_ROADMAP.md
```

This document defines the master roadmap for Phase 0 through Phase 8. It does not implement builders, validators, generated artifacts, Reading HTML, quiz packages, learner state, or adaptive learning.

---

## 2. Governance Boundary

Task:

```text
E4S-P0-S0_CorpusRoadmap_MasterDesignScan
```

Scope:

```text
Create the master roadmap and task ordering for Source / Authority Foundation.
```

Allowed files:

```text
docs/ulga/E4S_CORPUS_AND_FOUR_SKILL_SYSTEM_ROADMAP.md
```

Forbidden files:

```text
runtime files
generators
validators
source adapters
site HTML
student-facing Reading practice HTML
large generated JSON artifacts
source corpus files
learner state files
promotion artifacts
```

Current-task blockers:

```text
- Missing master E4S roadmap.
- Missing explicit Phase 0 task sequence.
- Missing active/deferred phase boundary.
```

Warning policy:

```text
Warnings found outside this roadmap are FUTURE_WORK unless they block P0-S0 acceptance.
```

Generated artifact policy:

```text
No generated artifacts are allowed in this sub-task.
```

Runtime impact:

```text
NONE
```

Promotion impact:

```text
NONE. This task does not promote any source, candidate, derived unit, or generated content into authority.
```

Stop condition:

```text
Stop after the master roadmap file exists and defines P0-P8, P0 sub-task order, forbidden scope, gates, distance vector, and next shortest step.
```

Deferred issues register:

```text
All implementation work is deferred to later P0 sub-tasks.
```

---

## 3. Epic Objective

The E4S epic exists to organize Vocabulary, Grammar, Theme, RAZ, Cambridge, Writing Template, Dialogue, Assessment, and generated candidate sources into a queryable, verifiable, level-aware, source-traceable practice system for English learning.

This is not a direct App project. The App, worksheet renderer, Reading practice HTML, assessment UI, audio, speaking, ASR, and adaptive recommendation layers must wait until the source and authority contracts are explicit.

Primary control rule:

```text
Source / Authority first.
Practice generation second.
Student-facing product later.
```

---

## 4. Phase Roadmap

| Phase | Phase ID | Main Goal | Current Status | Active Now |
|---|---|---|---:|---:|
| P0 | E4S-P0_SourceAuthorityAndCorpusRoadmap | Register, classify, and govern all source lines before implementation | IN_PROGRESS | YES |
| P1 | E4S-P1_ReadingV1SourceGroundedPractice | Produce source-grounded Reading V1 practice packages | NOT_STARTED | NEXT, AFTER P0 |
| P2 | E4S-P2_AssessmentPatternExpansion | Expand Reading item patterns toward Cambridge / worksheet structures | ROADMAP_ONLY | NO |
| P3 | E4S-P3_WritingPracticeSystem | Convert writing templates and source-grounded language into controlled writing practice | ROADMAP_ONLY | NO |
| P4 | E4S-P4_DialogueSpeakingPromptSystem | Convert functional sentences and dialogue sources into speaking prompts | ROADMAP_ONLY | NO |
| P5 | E4S-P5_ListeningPracticeSystem | Convert verified sentence/dialogue/passage units into listening practice | ROADMAP_ONLY | NO |
| P6 | E4S-P6_ErrorTaggingAndWeakPointDiagnosis | Convert learner answers into diagnostic error tags | ROADMAP_ONLY | NO |
| P7 | E4S-P7_AdaptiveLearningPathIntegration | Integrate practice, weakness, dependency, theme, and learner path | ROADMAP_ONLY | NO |
| P8 | E4S-P8_FourSkillBridgeAndProductLayer | Bridge Reading source into listening, speaking, writing, worksheet, and app packages | ROADMAP_ONLY | NO |

Active implementation approval:

```text
P0 only.
P1 is next after P0 gates pass.
P2-P8 are deferred roadmap placeholders.
```

---

## 5. Phase 0 Definition

Phase ID:

```text
E4S-P0_SourceAuthorityAndCorpusRoadmap
```

Goal:

```text
Classify all current and future source materials into the correct authority or candidate lane before they can be used by Reading V1 or other practice systems.
```

P0 must define:

```text
source manifest
source inventory contract
license_status
review_status
allowed_use
blocked_use
promotion_rule
authority role
target phase
target ULGA/content authority stage
```

P0 must prevent these errors:

```text
RAZ word list promoted as Vocabulary Authority
Parent functional sentence corpus promoted directly as Dialogue Authority
GPT-generated content promoted directly as Content Authority
Writing templates mixed into Reading Authority
Status HTML mistaken for student-facing Reading practice HTML
Reading Practice HTML started before source contract exists
```

---

## 6. AUX Source Lines

| AUX Stage | Source Line | Role | Authority Status |
|---|---|---|---|
| AUX-S0 | Source Inventory / Roadmap | Register all source materials and use policies | FOUNDATION |
| AUX-S1 | Cambridge Vocabulary Authority | Starters, Movers, Flyers, A2 Key, B1 Preliminary vocabulary | AUTHORITY_CANDIDATE |
| AUX-S2 | RAZ WordList Evidence | RAZ A-T word list exposure evidence | EVIDENCE_ONLY |
| AUX-S3 | Writing Sentence Template Corpus | Writing Framework 1-3 and sentence templates | TEMPLATE_CORPUS |
| AUX-S4 | Parent Functional Sentence Corpus | Daily parent-child functional English | FUNCTIONAL_SENTENCE_CORPUS |
| AUX-S5 | Story Dialogue Corpus | Story dialogue and script-like source material | DIALOGUE_CORPUS_CANDIDATE |
| AUX-S6 | RAZ Reading Corpus | RAZ sentence, page, and passage source material | READING_CORPUS_CANDIDATE |
| AUX-S7 | Generated Content Candidates | GPT or AI-generated dialogue/writing/reading candidates | CANDIDATE_ONLY |
| AUX-S8 | Assessment Pattern Corpus | Cambridge / worksheet / exam pattern structures | ASSESSMENT_PATTERN_CANDIDATE |
| AUX-S9 | Content Query Contract | Unified query contract for content authority candidates | QUERY_CONTRACT |

---

## 7. Phase 1 Boundary Preview

Phase 1 is not active until Phase 0 is complete.

Phase ID:

```text
E4S-P1_ReadingV1SourceGroundedPractice
```

Reading V1 goal:

```text
Generate source-grounded Reading practice packages from approved Reading source/query contracts.
```

Reading V1 first supported item types:

```text
literal_who
literal_what
literal_where
true_false
sentence_ordering
cloze_vocabulary
```

Reading V1 must include:

```text
source trace
evidence
answer model
validator-readable structure
candidate quiz/practice package
```

Reading V1 must not include:

```text
adaptive learning
learner state
error diagnosis
AI large-scale mixed generation
listening
speaking
writing
student account system
final promotion without review
```

---

## 8. Deferred Phase Boundaries

P2 Assessment Pattern Expansion:

```text
Deferred. No Cambridge item-pattern implementation during P0/P1 unless explicitly promoted.
```

P3 Writing Practice System:

```text
Deferred. Writing templates may be registered in P0 but not converted into writing exercises.
```

P4 Dialogue / Speaking Prompt System:

```text
Deferred. Functional and dialogue sources may be registered in P0 but not converted into speaking prompts.
```

P5 Listening Practice System:

```text
Deferred. No TTS, audio, timing, or playback work during P0.
```

P6 Error Tagging / Weak-point Diagnosis:

```text
Deferred. Wrong-answer diagnosis and error tags are not part of P0 or Reading V1 initial build.
```

P7 Adaptive Learning Path Integration:

```text
Deferred. CEFR, YLE path, theme spiral, frequency, and dependency boundaries may be documented, but no adaptive planner is implemented.
```

P8 Four-Skill Bridge / Product Layer:

```text
Deferred. No worksheet factory, workbook, app package, or multi-skill product output during P0.
```

---

## 9. P0 Sub-task Sequence

P0 must run in this order:

| Order | Task ID | Task Type | Deliverable | Gate Summary |
|---:|---|---|---|---|
| 0 | E4S-P0-S0_CorpusRoadmap_MasterDesignScan | DesignScan | docs/ulga/E4S_CORPUS_AND_FOUR_SKILL_SYSTEM_ROADMAP.md | P0-P8 and P0 sequence defined |
| 1 | E4S-P0-S1_SourceInventoryContract_DesignScan | DesignScan | docs/ulga/E4S_P0_SOURCE_INVENTORY_CONTRACT.md | Source record fields defined |
| 2 | E4S-P0-S2_SourceManifestBuilder_Implementation | Implementation | tools/build_e4s_source_manifest.py; ulga/graph/e4s_source_manifest.json; ulga/reports/e4s_source_manifest_summary.json; tests/test_build_e4s_source_manifest.py | Builder produces parseable manifest and summary |
| 3 | E4S-P0-S3_SourceManifestValidator_Implementation | Implementation | tools/validate_e4s_source_manifest.py; tests/test_validate_e4s_source_manifest.py | Invalid role/status/use combinations fail |
| 4 | E4S-P0-S4_AuthorityMappingMatrix_DesignScan | DesignScan | docs/ulga/E4S_AUTHORITY_MAPPING_MATRIX.md | Sources mapped to correct authority lanes |
| 5 | E4S-P0-S5_LevelSituationTaxonomy_DesignScan | DesignScan | docs/ulga/E4S_LEVEL_SITUATION_TAXONOMY.md | Level and situation taxonomy defined |
| 6 | E4S-P0-S6_LearningPathBoundaryContract_DesignScan | DesignScan | docs/ulga/E4S_LEARNING_PATH_BOUNDARY_CONTRACT.md | CEFR / YLE / dependency / adaptive boundaries separated |
| 7 | E4S-P0-S7_StatusArtifactReclassification_DocumentationPatch | DocumentationPatch | docs/status/RAZ_AW_STATUS_ARTIFACT_CLASSIFICATION.md | Status HTML separated from student-facing Reading HTML |

---

## 10. P0 Completion Criteria

Phase 0 may close only when all of the following exist and pass their gates:

```text
1. E4S master roadmap
2. Source inventory contract
3. Source manifest builder
4. Source manifest validator
5. Authority mapping matrix
6. Level / situation taxonomy
7. Learning path boundary contract
8. Status artifact reclassification
```

Phase 0 does not close if:

```text
- any source can still be promoted by implication
- generated content can be mistaken for authority
- RAZ word list is treated as vocabulary authority
- student-facing Reading HTML starts before source contract
- status dashboard is mistaken for practice artifact
```

---

## 11. Gate Metrics for P0-S0

| Gate | Result | Evidence |
|---|---:|---|
| Master roadmap file created | PASS | This file |
| P0-P8 phases defined | PASS | Section 4 |
| P0 scope defined | PASS | Section 5 |
| AUX source lines defined | PASS | Section 6 |
| P1 boundary preview defined without implementation | PASS | Section 7 |
| Deferred phases locked | PASS | Section 8 |
| P0 sub-task order defined | PASS | Section 9 |
| Runtime impact avoided | PASS | Documentation only |
| Generated artifact avoided | PASS | No generated artifacts |
| Promotion avoided | PASS | No source promotion |

---

## 12. Distance Vector

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
E4S-P0-S0_CorpusRoadmap_MasterDesignScan
```

Sub-task Status:

```text
E4S-P0-S0_CorpusRoadmap_MasterDesignScan -> COMPLETED
```

P0 remaining distance after this sub-task:

```text
D_P0 = 7 sub-tasks left
```

Remaining P0 tasks:

```text
E4S-P0-S1_SourceInventoryContract_DesignScan
E4S-P0-S2_SourceManifestBuilder_Implementation
E4S-P0-S3_SourceManifestValidator_Implementation
E4S-P0-S4_AuthorityMappingMatrix_DesignScan
E4S-P0-S5_LevelSituationTaxonomy_DesignScan
E4S-P0-S6_LearningPathBoundaryContract_DesignScan
E4S-P0-S7_StatusArtifactReclassification_DocumentationPatch
```

Total epic distance is intentionally not estimated here because P2-P8 remain roadmap-only and must not be converted into implementation scope during P0.

---

## 13. Deferred Issues Register

```text
issue_id: E4S-DEFER-001
severity: medium
affected_file_or_artifact: source manifest builder / validator
classification: FUTURE_WORK
why_deferred: P0-S0 is roadmap-only and may not implement code.
recommended_future_task: E4S-P0-S2_SourceManifestBuilder_Implementation and E4S-P0-S3_SourceManifestValidator_Implementation
blocks_current_task: no
```

```text
issue_id: E4S-DEFER-002
severity: medium
affected_file_or_artifact: Reading Practice HTML
classification: FUTURE_WORK
why_deferred: Reading Practice HTML belongs to P1 after P0 source contracts exist.
recommended_future_task: P1-S3 Reading Practice HTML Renderer
blocks_current_task: no
```

```text
issue_id: E4S-DEFER-003
severity: high
affected_file_or_artifact: generated content candidates
classification: FUTURE_WORK
why_deferred: Generated candidates need explicit candidate-only and promotion rules before use.
recommended_future_task: E4S-P0-S1_SourceInventoryContract_DesignScan
blocks_current_task: no
```

```text
issue_id: E4S-DEFER-004
severity: medium
affected_file_or_artifact: status snapshot HTML
classification: FUTURE_WORK
why_deferred: Reclassification is a later documentation patch, not part of P0-S0.
recommended_future_task: E4S-P0-S7_StatusArtifactReclassification_DocumentationPatch
blocks_current_task: no
```

---

## 14. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P0-S1_SourceInventoryContract_DesignScan
```

Only next allowed action:

```text
Create docs/ulga/E4S_P0_SOURCE_INVENTORY_CONTRACT.md to define source_id, source_family, source_type, authority_role, path, format, exists, license_status, review_status, allowed_use, blocked_use, promotion_rule, target_phase, target_ulga_stage, risk_flags, and notes.
```

Stop here until the operator explicitly starts E4S-P0-S1.

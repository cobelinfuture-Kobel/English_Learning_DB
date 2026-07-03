# E4S Level Situation Taxonomy Design Scan

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
E4S-P0-S5_LevelSituationTaxonomy_DesignScan
```

Deliverable:

```text
docs/ulga/E4S_LEVEL_SITUATION_TAXONOMY.md
```

This task defines level and situation taxonomy boundaries for future Reading, Writing, Dialogue/Speaking, Listening, and Assessment routing. It does not modify manifest records, builders, validators, generated artifacts, learner state, adaptive learning paths, Reading HTML, or source promotion.

---

## 2. Task Boundary

Task:

```text
E4S-P0-S5_LevelSituationTaxonomy_DesignScan
```

Scope:

```text
Define the level taxonomy, level-claim policy, situation taxonomy, skill routing constraints, and future validation expectations needed before any source can be routed into practice generation or learning-path decisions.
```

Allowed files:

```text
docs/ulga/E4S_LEVEL_SITUATION_TAXONOMY.md
```

Forbidden files:

```text
tools/build_e4s_source_manifest.py
tools/validate_e4s_source_manifest.py
ulga/graph/e4s_source_manifest.json
ulga/reports/e4s_source_manifest_summary.json
docs/ulga/E4S_AUTHORITY_MAPPING_MATRIX.md
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
learning path runtime files
```

Current-task blockers:

```text
- No normalized level taxonomy boundary for CEFR / Cambridge / RAZ / internal bands.
- No situation taxonomy boundary for school, home, story, dialogue, assessment, and functional contexts.
- No rule separating source level claims from learner placement decisions.
- No rule separating situation labels from final practice generation.
```

Warning policy:

```text
Any mismatch between a source's claimed level and actual pedagogical difficulty is FUTURE_WORK unless it prevents this taxonomy from defining the claim boundary.
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
NONE. This taxonomy defines routing labels and claim boundaries but performs no source or content promotion.
```

Stop condition:

```text
Stop after level taxonomy, level-claim statuses, situation taxonomy, skill routing rules, invalid uses, gates, distance vector, deferred issues, and next shortest step are documented.
```

---

## 3. Taxonomy Purpose

The Level / Situation Taxonomy prevents three common failures:

```text
1. Treating a source's publisher level as a verified learner level.
2. Treating a situation label as permission to generate learner-facing practice.
3. Mixing CEFR, Cambridge, RAZ, school grade, and internal difficulty bands without a claim status.
```

This taxonomy is a routing and claim-control layer. It is not a placement engine, adaptive scheduler, learner model, or final curriculum map.

---

## 4. Level Taxonomy Axes

Every future source or content candidate that carries level information must separate these axes:

| Axis | Field Name | Meaning | P0 Status |
|---|---|---|---|
| Level System | `level_system` | Origin of the level label | design only |
| Raw Level Code | `raw_level_code` | Original source label | design only |
| Normalized Band | `normalized_level_band` | Internal broad band for routing | design only |
| Claim Status | `level_claim_status` | Confidence and review state of the level label | design only |
| Skill Scope | `skill_scope` | Skill area affected by the label | design only |
| Evidence Role | `level_evidence_role` | Whether the level is authority, candidate, evidence, or metadata | design only |
| Review Owner | `level_review_owner` | Future task or phase that may validate the claim | design only |

---

## 5. Controlled Level Systems

Allowed `level_system` values:

```text
CEFR
CAMBRIDGE_PRE_A1_STARTERS
CAMBRIDGE_A1_MOVERS
CAMBRIDGE_A2_FLYERS
CAMBRIDGE_A2_KEY
RAZ
INTERNAL_E4S_BAND
SCHOOL_GRADE
SOURCE_NATIVE_LEVEL
UNKNOWN
```

Rules:

```text
CEFR labels are broad external reference labels, not automatic learner placement.
Cambridge labels are assessment-oriented labels, not automatic grammar/vocabulary authority.
RAZ labels are reading-source labels, not automatic CEFR conversion.
School grade labels are local or publisher context, not CEFR equivalence.
INTERNAL_E4S_BAND is a routing label only until validated by later tasks.
UNKNOWN must remain blocked from generation and learner-facing output.
```

---

## 6. Normalized Level Bands

Allowed `normalized_level_band` values:

```text
PRE_A1
A1_LOW
A1_MID
A1_HIGH
A2_LOW
A2_MID
A2_HIGH
B1_PLUS_REFERENCE_ONLY
UNKNOWN
```

P0 interpretation:

| normalized_level_band | Meaning | P0 Use | Blocked Use |
|---|---|---|---|
| `PRE_A1` | Very early learner band | routing metadata | placement, generation without review |
| `A1_LOW` | Early A1 band | routing metadata | placement, generation without review |
| `A1_MID` | Middle A1 band | routing metadata | placement, generation without review |
| `A1_HIGH` | Upper A1 band | routing metadata | placement, generation without review |
| `A2_LOW` | Early A2 band | routing metadata | placement, generation without review |
| `A2_MID` | Middle A2 band | routing metadata | placement, generation without review |
| `A2_HIGH` | Upper A2 band | routing metadata | placement, generation without review |
| `B1_PLUS_REFERENCE_ONLY` | Above initial E4S practice focus | reference only | P1/P0 learner-facing use |
| `UNKNOWN` | No reliable normalized band | inventory only | query generation, placement, learner-facing output |

---

## 7. RAZ Level Handling

Allowed RAZ raw labels:

```text
RAZ_A
RAZ_B
RAZ_C
RAZ_D
RAZ_E
RAZ_F
RAZ_G
RAZ_H
RAZ_I
RAZ_J
RAZ_K
RAZ_L
RAZ_M
RAZ_N
RAZ_O
RAZ_P
RAZ_Q
RAZ_R
RAZ_S
RAZ_T
RAZ_UNKNOWN
```

RAZ policy:

```text
RAZ level is a reading-source progression label.
RAZ level is not a CEFR equivalence by default.
RAZ level may support Reading V1 source ordering after P1 validators are active.
RAZ level may not decide learner placement during P0.
RAZ level may not promote RAZ word lists into Vocabulary Authority.
```

P0 routing preview:

| RAZ raw label range | P0 normalized routing band | Status |
|---|---|---|
| `RAZ_A` - `RAZ_C` | `PRE_A1` / `A1_LOW` candidate | unverified routing only |
| `RAZ_D` - `RAZ_F` | `A1_LOW` / `A1_MID` candidate | unverified routing only |
| `RAZ_G` - `RAZ_J` | `A1_MID` / `A1_HIGH` candidate | unverified routing only |
| `RAZ_K` - `RAZ_N` | `A2_LOW` candidate | unverified routing only |
| `RAZ_O` - `RAZ_T` | `A2_MID` / `A2_HIGH` candidate | unverified routing only |
| `RAZ_UNKNOWN` | `UNKNOWN` | blocked from generation |

The above routing preview is not an official equivalence table. It is a coarse P0 routing placeholder for later review.

---

## 8. Level Claim Status

Allowed `level_claim_status` values:

```text
source_claim_unverified
metadata_reviewed
sample_reviewed
cross_source_aligned
validator_reviewed
promotion_reviewed
rejected
unknown_blocked
```

Rules:

```text
source_claim_unverified can appear in inventory and summary only.
metadata_reviewed can support query design but not learner-facing output.
sample_reviewed can support candidate selection but not final placement.
cross_source_aligned can support stronger routing but not adaptive scheduling.
validator_reviewed is required before generated practice packages rely on the level label.
promotion_reviewed is required before a level label can become authority-level metadata.
unknown_blocked cannot support generation or learner-facing output.
```

---

## 9. Level Evidence Role

Allowed `level_evidence_role` values:

```text
publisher_claim
source_metadata
corpus_statistical_signal
cross_source_alignment
human_review
validator_output
unknown
```

Evidence role policy:

```text
publisher_claim is not enough for promotion.
source_metadata can support manifest summaries.
corpus_statistical_signal requires future builder/validator work.
cross_source_alignment requires future bridge tasks.
human_review and validator_output are stronger but still task-scoped.
unknown cannot support learner-facing routing.
```

---

## 10. Situation Taxonomy Axes

Every future source or content candidate with situation information must separate these axes:

| Axis | Field Name | Meaning | P0 Status |
|---|---|---|---|
| Situation Domain | `situation_domain` | Broad real-world or pedagogical domain | design only |
| Situation Context | `situation_context` | Concrete context or scene | design only |
| Communicative Function | `communicative_function` | Language function used in the situation | design only |
| Interaction Mode | `interaction_mode` | solo, dialogue, group, instruction, assessment | design only |
| Skill Fit | `skill_fit` | Which skill can use the situation | design only |
| Situation Claim Status | `situation_claim_status` | Review state of the situation label | design only |
| Sensitivity Flag | `situation_sensitivity_flag` | Whether the situation needs extra review | design only |

---

## 11. Situation Domains

Allowed `situation_domain` values:

```text
home
school
classroom
playground
library
food_and_meals
shopping
travel_and_transport
animals_and_nature
sports_and_hobbies
health_and_body
time_and_daily_routine
weather_and_seasons
family_and_friends
story_fantasy
story_adventure
functional_parent_child
assessment_exam
worksheet_instruction
reading_passage
unknown
```

Domain policy:

```text
situation_domain routes the context; it does not authorize generation.
reading_passage domain requires source trace before Reading V1 use.
assessment_exam domain requires assessment-pattern review before item generation.
functional_parent_child domain requires dialogue/speaking review before learner-facing prompts.
story_fantasy and story_adventure require content suitability review before learner-facing use.
unknown is blocked from generation.
```

---

## 12. Situation Contexts

Recommended `situation_context` values:

```text
home_bedroom
home_kitchen
home_living_room
school_classroom
school_library
school_playground
school_art_room
school_music_room
school_science_lab
park
zoo
farm
beach
city
shop
restaurant
bus_train_station
doctor_clinic
birthday_party
sports_field
camping
morning_routine
after_school_routine
picture_description
story_sequence
exam_instruction
worksheet_problem
unknown
```

Context policy:

```text
A context can support multiple skills only if skill_fit explicitly allows them.
A context does not imply level.
A context does not imply learner familiarity.
A context must remain candidate metadata until reviewed.
```

---

## 13. Communicative Functions

Allowed `communicative_function` values:

```text
identify_object
identify_person
describe_location
describe_action
describe_attribute
count_quantity
ask_answer_wh_question
ask_answer_yes_no
sequence_events
retell_story
express_preference
express_feeling
make_request
give_instruction
follow_instruction
compare_contrast
explain_reason
predict_next_event
assessment_response
unknown
```

Function policy:

```text
communicative_function helps route tasks to Reading, Writing, Dialogue/Speaking, Listening, or Assessment.
It does not authorize item generation by itself.
Functions requiring inference, prediction, explanation, or comparison need later pattern review before learner-facing use.
```

---

## 14. Interaction Modes

Allowed `interaction_mode` values:

```text
solo_reading
solo_writing
one_to_one_dialogue
group_discussion
teacher_instruction
parent_child_dialogue
listen_and_respond
exam_response
worksheet_response
unknown
```

Rules:

```text
solo_reading may support Reading V1 only after source trace and validator gates.
solo_writing belongs to P3 Writing.
one_to_one_dialogue and parent_child_dialogue belong to P4 Dialogue/Speaking.
listen_and_respond belongs to P5 Listening.
exam_response and worksheet_response belong to P2 Assessment.
unknown is blocked from generation.
```

---

## 15. Skill Fit Matrix

Allowed `skill_fit` values:

```text
reading_candidate
writing_candidate
dialogue_speaking_candidate
listening_candidate
assessment_candidate
grammar_reference
vocabulary_reference
multi_skill_reference_only
unknown_blocked
```

| skill_fit | Future Owner | P0 Allowed Use | P0 Blocked Use |
|---|---|---|---|
| `reading_candidate` | P1 Reading V1 | source trace / query design | learner-facing Reading HTML |
| `writing_candidate` | P3 Writing | template/situation design | writing worksheet generation |
| `dialogue_speaking_candidate` | P4 Dialogue/Speaking | prompt design | speaking prompt authority |
| `listening_candidate` | P5 Listening | design only | audio generation |
| `assessment_candidate` | P2 Assessment | pattern design | assessment item generation |
| `grammar_reference` | future grammar authority review | metadata reference | direct grammar authority |
| `vocabulary_reference` | future vocabulary authority review | metadata reference | direct vocabulary authority |
| `multi_skill_reference_only` | future bridge review | reference only | direct generation |
| `unknown_blocked` | intake review | inventory only | all generation |

---

## 16. Phase Routing Rules

| Phase | May Consume Level Labels? | May Consume Situation Labels? | P0 Status |
|---|---:|---:|---|
| `E4S-P0_SourceAuthorityAndCorpusRoadmap` | metadata only | metadata only | active |
| `E4S-P1_ReadingV1SourceGroundedPractice` | yes, after source trace / validator gates | yes, reading passage only | future |
| `E4S-P2_AssessmentPatternExpansion` | yes, after assessment review | yes, exam/worksheet contexts | deferred |
| `E4S-P3_WritingPracticeSystem` | yes, after template review | yes, writing contexts | deferred |
| `E4S-P4_DialogueSpeakingPromptSystem` | yes, after dialogue review | yes, dialogue contexts | deferred |
| `E4S-P5_ListeningPracticeSystem` | yes, after listening review | yes, listening contexts | deferred |
| `E4S-P6_ErrorTaggingAndWeakPointDiagnosis` | no direct source consumption | no direct source consumption | deferred |
| `E4S-P7_AdaptiveLearningPathIntegration` | only after learning-path boundary | only after learning-path boundary | deferred |
| `E4S-P8_FourSkillBridgeAndProductLayer` | bridge only after prior reviews | bridge only after prior reviews | deferred |

---

## 17. Invalid Uses

These uses are invalid in P0:

| Invalid Use | Reason | Required Handling |
|---|---|---|
| `source level claim -> learner placement` | Source level is not learner state | block / defer to P7 |
| `RAZ level -> CEFR equivalence` | RAZ labels are not CEFR by default | block / mark unverified |
| `Cambridge list -> automatic Vocabulary Authority` | Requires vocabulary authority review | block |
| `situation label -> learner-facing HTML` | Situation label is routing metadata only | block |
| `story context -> child-safe content` | Suitability requires review | block until reviewed |
| `assessment context -> item generation` | Requires P2 pattern review | block |
| `functional_parent_child -> speaking prompt authority` | Requires P4 dialogue review | block |
| `UNKNOWN level or situation -> generation` | Unknown labels cannot drive generation | fail / block |
| `multi_skill_reference_only -> direct generation` | Needs bridge review | block |

---

## 18. Required Future Record Fields

Future manifest expansion may add these optional fields, but this task does not modify the manifest:

```text
level_system
raw_level_code
normalized_level_band
level_claim_status
level_evidence_role
level_review_owner
situation_domain
situation_context
communicative_function
interaction_mode
skill_fit
situation_claim_status
situation_sensitivity_flag
```

These fields must remain optional until a later manifest expansion task explicitly updates the schema and validator.

---

## 19. Acceptance Gates for P0-S5

| Gate | Result | Evidence |
|---|---:|---|
| Level taxonomy axes defined | PASS | Section 4 |
| Controlled level systems defined | PASS | Section 5 |
| Normalized level bands defined | PASS | Section 6 |
| RAZ level handling boundary defined | PASS | Section 7 |
| Level claim status defined | PASS | Section 8 |
| Situation taxonomy axes defined | PASS | Section 10 |
| Situation domains defined | PASS | Section 11 |
| Situation contexts defined | PASS | Section 12 |
| Communicative functions defined | PASS | Section 13 |
| Interaction modes defined | PASS | Section 14 |
| Skill fit matrix defined | PASS | Section 15 |
| Phase routing rules defined | PASS | Section 16 |
| Invalid uses defined | PASS | Section 17 |
| Runtime impact avoided | PASS | Documentation only |
| Manifest modification avoided | PASS | No JSON change |
| Validator modification avoided | PASS | No Python change |
| Promotion avoided | PASS | Design only |

---

## 20. Distance Vector

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
E4S-P0-S5_LevelSituationTaxonomy_DesignScan
```

Sub-task Status:

```text
E4S-P0-S5_LevelSituationTaxonomy_DesignScan -> COMPLETED
```

P0 remaining distance after this sub-task:

```text
D_P0 = 2 sub-tasks left
```

Remaining P0 tasks:

```text
E4S-P0-S6_LearningPathBoundaryContract_DesignScan
E4S-P0-S7_StatusArtifactReclassification_DocumentationPatch
```

---

## 21. Deferred Issues Register

```text
issue_id: E4S-P0-S5-DEFER-001
severity: medium
affected_file_or_artifact: ulga/graph/e4s_source_manifest.json
classification: FUTURE_WORK
why_deferred: This task defines optional future taxonomy fields but does not add them to the manifest.
recommended_future_task: future source manifest taxonomy expansion task
blocks_current_task: no
```

```text
issue_id: E4S-P0-S5-DEFER-002
severity: medium
affected_file_or_artifact: tools/validate_e4s_source_manifest.py
classification: FUTURE_WORK
why_deferred: This task defines level/situation validation expectations but does not update validator code.
recommended_future_task: future taxonomy validator enforcement patch
blocks_current_task: no
```

```text
issue_id: E4S-P0-S5-DEFER-003
severity: high
affected_file_or_artifact: learner placement / adaptive learning path
classification: FUTURE_WORK
why_deferred: This task explicitly separates source level claims from learner placement decisions.
recommended_future_task: E4S-P0-S6_LearningPathBoundaryContract_DesignScan and later P7 tasks
blocks_current_task: no
```

```text
issue_id: E4S-P0-S5-DEFER-004
severity: medium
affected_file_or_artifact: RAZ to CEFR alignment
classification: FUTURE_WORK
why_deferred: This task defines only coarse routing placeholders, not official equivalence.
recommended_future_task: future cross-source level alignment task
blocks_current_task: no
```

---

## 22. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P0-S6_LearningPathBoundaryContract_DesignScan
```

Only next allowed action:

```text
Create docs/ulga/E4S_LEARNING_PATH_BOUNDARY_CONTRACT.md to define boundaries between source levels, practice routing, learner placement, dependency graph, adaptive scheduling, and future P7 learning-path integration.
```

Stop here until the operator explicitly starts E4S-P0-S6.

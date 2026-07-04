# E4S P5 I4 Listening Candidate Seed Expansion Planning

## Current State

```text
Current Phase = E4S-P5_ListeningPracticeSystem
Current Sub-task = E4S-P5-I4_ListeningCandidateSeedExpansionPlanning
```

Prerequisite state:

```text
I1 validator = local PASS
I2 builder = local PASS
I3 empty package = local PASS
local hygiene = clean
```

I4 is planning only. It does not add seed JSON and does not rebuild the candidate package.

## Source Boundary

Allowed source groups for the next seed batch:

| Source ID | Planned candidate type | Tier |
|---|---|---:|
| PARENT_FUNCTIONAL_SENTENCE_CORPUS_REFERENCE | sentence_listening_candidate | 1 |
| STORY_DIALOGUE_CORPUS_REFERENCE | dialogue_listening_candidate | 2 |
| RAZ_READING_CORPUS_A_T_CANDIDATE | passage_listening_candidate | 3 |

Do not use as seed content in the next batch:

```text
RAZ_WORDLIST_A_T_EVIDENCE
governance docs
roadmap docs
status artifacts
grammar profile
vocabulary profile
frequency profile
chunk reference layer
Cambridge vocabulary collection
writing template corpus
assessment pattern corpus
generated content candidate pool
unknown source families
```

Reason:

```text
The current P5 builder and validator only support traceable sentence, dialogue, and passage candidates from the approved P5 source families.
```

## Seed Batch 001 Plan

```text
seed_batch_id = p5_i5_seed_batch_001
recommended_size = 3 candidates
sentence_candidates = 1
dialogue_candidates = 1
passage_candidates = 1
```

Expansion order:

```text
1. sentence candidate from parent functional sentence source
2. dialogue candidate from story dialogue source
3. passage candidate from RAZ reading source
```

This first batch is intentionally small so all three supported candidate types can be tested before expanding.

## Required Seed Fields

Every seed candidate should include:

```text
source_id
source_unit_id
source_unit_ref
source_text
normalized_level_band
situation_domain
situation_context
communicative_function
interaction_mode
```

Additional fields by type:

```text
sentence candidate: sentence_context_ref
dialogue candidate: dialogue_turns
passage candidate: sentence_ids, sentence_order, paragraph_or_page_ref
```

A1 constraints:

```text
sentence seed = one short sentence
dialogue seed = two turns
passage seed = two short sentences
normalized_level_band = A1
situation_sensitivity_flag = none
```

## Proposed I5 Artifacts

I5 should create:

```text
ulga/listening/seeds/e4s_p5_seed_batch_001.json
```

I5 should then refresh and validate:

```text
ulga/listening/candidates/e4s_listening_candidate_package.json
ulga/listening/reports/e4s_listening_validator_report.json
```

Recommended local commands after I5 implementation:

```text
python tools/build_e4s_listening_candidate_package.py --seed-candidates ulga/listening/seeds/e4s_p5_seed_batch_001.json --output ulga/listening/candidates/e4s_listening_candidate_package.json
python tools/validate_e4s_listening_candidates.py --candidate-package ulga/listening/candidates/e4s_listening_candidate_package.json --source-manifest ulga/graph/e4s_source_manifest.json --report-output ulga/listening/reports/e4s_listening_validator_report.json
python -m unittest tests.test_build_e4s_listening_candidate_package
python -m unittest tests.test_validate_e4s_listening_candidates
git status
```

## Gate And Distance Update

| Gate | Result |
|---|---:|
| I4 approval recorded | PASS |
| I3 local hygiene clean | PASS |
| eligible source classes identified | PASS |
| excluded source classes listed | PASS |
| seed batch size defined | PASS |
| required seed fields defined | PASS |
| seed JSON created in I4 | NO |
| candidate package rebuilt in I4 | NO |

Distance vector:

```text
E4S-P5-I4_ListeningCandidateSeedExpansionPlanning -> COMPLETED
D_P5_SEED_EXPANSION_PLANNING = 0
D_P5_I5_OPERATOR_APPROVAL = 1
```

## Next Shortest Step

```text
E4S-P5-I5_ListeningCandidateSeedBatch001Implementation
```

Suggested approval phrase:

```text
核准執行 E4S-P5-I5_ListeningCandidateSeedBatch001Implementation
```

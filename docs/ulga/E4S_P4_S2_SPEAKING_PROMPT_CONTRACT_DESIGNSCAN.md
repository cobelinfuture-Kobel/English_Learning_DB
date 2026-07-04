# E4S-P4-S2 Speaking Prompt Contract DesignScan

## 1. Current State

Epic ID: `E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem`

Phase ID: `E4S-P4_DialogueSpeakingPromptSystem`

Sub-task ID: `E4S-P4-S2_SpeakingPromptContract_DesignScan`

Status: `COMPLETED`

## 2. Design Scope

This task defines the V1 contract for a source-grounded speaking prompt record.

This task does not implement:

- prompt generator
- role-play renderer
- ASR
- recording
- speech scoring
- audio pipeline
- student-facing UI
- learner-state integration
- final Dialogue Authority promotion

## 3. Source Basis

Phase 4 is Dialogue / Speaking Prompt System.

Approved P4 source families:

- `AUX-S4 Parent Functional Sentence Corpus`
- `AUX-S5 Story Dialogue Corpus`
- `AUX-S7 Generated Dialogue Candidates`

Boundary inherited from P4-S1:

- AUX-S4 is functional sentence / oral prompt source, not full dialogue authority.
- AUX-S5 is story/context dialogue source and may preserve role/order/context.
- AUX-S7 is generated candidate only.
- P4 V1 is prompt-only.

## 4. Speaking Prompt Contract V1

A valid speaking prompt record must be a single prompt unit that can be rendered for oral practice without requiring ASR or scoring.

### 4.1 Required fields

```json
{
  "prompt_id": "SPK_AUXS4_000001",
  "source_family": "AUX-S4",
  "source_id": "AUXS4_SOURCE_000001",
  "source_trace": {
    "source_type": "parent_functional_sentence",
    "source_path": "",
    "source_record_id": "",
    "source_text_hash": "",
    "evidence_text": ""
  },
  "prompt_type": "functional_response",
  "speaking_mode": "guided_response",
  "speaker_roles": [],
  "theme": "DailyRoutine",
  "level_estimate": "A1",
  "input_text": "Time to brush your teeth.",
  "prompt_text": "What should you do now?",
  "expected_response_shape": {
    "response_type": "short_sentence",
    "min_words": 2,
    "max_words": 8,
    "required_elements": [],
    "example_responses": []
  },
  "allowed_variation": {
    "allow_synonym": false,
    "allow_short_answer": true,
    "allow_full_sentence": true,
    "allow_role_paraphrase": false
  },
  "blocked_generation_behavior": [],
  "authority_status": "candidate_only",
  "review_status": "pending",
  "validator_requirements": []
}
```

### 4.2 Field definitions

| Field | Required | Purpose |
|---|---:|---|
| `prompt_id` | yes | Stable prompt identifier. |
| `source_family` | yes | One of `AUX-S4`, `AUX-S5`, `AUX-S7`. |
| `source_id` | yes | Stable source record id or source-manifest id. |
| `source_trace` | yes | Evidence pointer back to source material. |
| `prompt_type` | yes | What kind of oral prompt this is. |
| `speaking_mode` | yes | What oral action the learner performs. |
| `speaker_roles` | yes | Speaker/character roles when available. Empty list is allowed for AUX-S4. |
| `theme` | yes | Situation/theme label. |
| `level_estimate` | yes | Estimated level, not final CEFR authority. |
| `input_text` | yes | Source-grounded text used to build the prompt. |
| `prompt_text` | yes | Student-facing prompt instruction. |
| `expected_response_shape` | yes | Acceptable oral response structure. |
| `allowed_variation` | yes | Permitted answer variation. |
| `blocked_generation_behavior` | yes | Explicitly forbidden generation/promotion behavior. |
| `authority_status` | yes | `candidate_only`, `reviewed_candidate`, or future promoted state. |
| `review_status` | yes | `pending`, `reviewed`, `rejected`, or `needs_revision`. |
| `validator_requirements` | yes | Checks required before packaging. |

## 5. Controlled Enumerations

### 5.1 `source_family`

Allowed values:

```text
AUX-S4
AUX-S5
AUX-S7
```

### 5.2 `prompt_type`

Allowed V1 values:

```text
functional_response
substitution_prompt
role_response
role_play_turn
story_retell
context_question
oral_sentence_builder
```

Definitions:

| prompt_type | Intended source | Description |
|---|---|---|
| `functional_response` | AUX-S4 | Learner orally responds to a daily function / command / routine situation. |
| `substitution_prompt` | AUX-S4 / AUX-S7 | Learner changes one slot in a sentence frame. |
| `role_response` | AUX-S5 | Learner responds as a named character or role. |
| `role_play_turn` | AUX-S5 | Learner produces one turn in a role-play exchange. |
| `story_retell` | AUX-S5 | Learner retells a short story/dialogue context. |
| `context_question` | AUX-S5 | Learner answers an oral question grounded in dialogue/story context. |
| `oral_sentence_builder` | AUX-S4 / AUX-S7 | Learner builds a short sentence orally from a given cue. |

### 5.3 `speaking_mode`

Allowed V1 values:

```text
repeat_oral
read_aloud
guided_response
short_answer
substitution_drill
role_play
retell
sentence_building
```

V1 mode notes:

- `repeat_oral` and `read_aloud` do not imply recording.
- `guided_response` and `short_answer` do not imply scoring.
- `role_play` does not imply multi-turn renderer implementation.
- `retell` is prompt-only in V1.

### 5.4 `authority_status`

Allowed V1 values:

```text
candidate_only
reviewed_candidate
rejected
```

Blocked in V1:

```text
authority_promoted
learner_facing_final
production_ready
```

### 5.5 `review_status`

Allowed values:

```text
pending
reviewed
needs_revision
rejected
```

## 6. Source-Specific Contract Rules

### 6.1 AUX-S4 Parent Functional Sentence Corpus

AUX-S4 records are functional sentence sources.

Allowed prompt types:

- `functional_response`
- `substitution_prompt`
- `oral_sentence_builder`

Rules:

- `speaker_roles` may be empty.
- `source_trace.source_type` should be `parent_functional_sentence`.
- `prompt_text` may ask the learner what to say or do in a daily situation.
- Do not mark AUX-S4 prompts as full dialogue authority.
- Do not invent character turns unless `source_family` changes through a derived candidate process.

Required blocked behavior:

```json
[
  "do_not_treat_parent_functional_sentence_as_dialogue_authority",
  "do_not_infer_speaker_turns_without_derivation",
  "do_not_promote_without_review"
]
```

### 6.2 AUX-S5 Story Dialogue Corpus

AUX-S5 records may contain context, characters, turns, narration, and story order.

Allowed prompt types:

- `role_response`
- `role_play_turn`
- `story_retell`
- `context_question`

Rules:

- Preserve role, turn order, and context when present.
- `speaker_roles` should not be empty if source roles exist.
- `source_trace.source_type` should be `story_dialogue` or more specific.
- Do not flatten role/dialogue context into a sentence-only record.
- Do not create learner-facing packages before validator checks.

Required blocked behavior:

```json
[
  "do_not_flatten_story_dialogue_context",
  "do_not_drop_speaker_order_when_available",
  "do_not_promote_without_source_trace_and_review"
]
```

### 6.3 AUX-S7 Generated Dialogue Candidates

AUX-S7 records are generated candidate sources only.

Allowed prompt types:

- `substitution_prompt`
- `oral_sentence_builder`
- `role_response`
- `role_play_turn`
- `story_retell`
- `context_question`

Rules:

- `authority_status` must be `candidate_only` unless a later review task explicitly changes it.
- `review_status` must start as `pending`.
- `source_trace.source_type` must indicate generated/derived origin.
- Any prompt generated from AUX-S7 must carry `generated = true` inside source trace or metadata.
- Generated content cannot claim source-grounded authority without evidence.

Required blocked behavior:

```json
[
  "do_not_treat_generated_content_as_authority",
  "do_not_mark_generated_content_as_source_grounded_without_evidence",
  "do_not_make_generated_content_learner_facing_without_review"
]
```

## 7. Expected Response Shape Contract

`expected_response_shape` defines what form the learner response should take. It is not a scoring rubric.

Required subfields:

```json
{
  "response_type": "short_sentence",
  "min_words": 1,
  "max_words": 20,
  "required_elements": [],
  "optional_elements": [],
  "example_responses": [],
  "non_scoring_notes": []
}
```

Allowed `response_type` values:

```text
repeat_text
single_word
short_phrase
short_sentence
sentence_frame
role_turn
retell_2_3_sentences
open_oral_response
```

Rules:

- `example_responses` are examples, not exhaustive answer keys.
- If `response_type = retell_2_3_sentences`, V1 still does not score the retell.
- `required_elements` should be limited to visible source-grounded cues.
- Do not require hidden grammar tags as student-facing answer conditions.

## 8. Validator Requirements Draft

A future validator must fail a prompt record if:

1. `prompt_id` is missing.
2. `source_family` is not one of `AUX-S4`, `AUX-S5`, `AUX-S7`.
3. `source_trace` is missing.
4. `prompt_type` is not in the allowed V1 set.
5. `speaking_mode` is not in the allowed V1 set.
6. `authority_status` is outside the allowed V1 set.
7. `review_status` is missing.
8. AUX-S4 record uses `role_play_turn` without derived-candidate metadata.
9. AUX-S5 source roles exist but `speaker_roles` is empty.
10. AUX-S7 record is not `candidate_only`.
11. AUX-S7 record is missing generated/derived trace.
12. A record claims `learner_facing_final` in V1.
13. A record claims ASR, recording, pronunciation score, or speech score support.

Validator should warn if:

1. `theme` is `General` but source suggests a clearer daily situation.
2. `level_estimate` is missing confidence metadata.
3. `example_responses` are empty for open prompts.
4. `max_words` is too high for PreA1/A1 prompt.

## 9. Example Records

### 9.1 AUX-S4 functional response

```json
{
  "prompt_id": "SPK_AUXS4_000001",
  "source_family": "AUX-S4",
  "source_id": "AUXS4_PARENT_FUNC_000001",
  "source_trace": {
    "source_type": "parent_functional_sentence",
    "source_path": "TBD",
    "source_record_id": "TBD",
    "source_text_hash": "TBD",
    "evidence_text": "Time to brush your teeth."
  },
  "prompt_type": "functional_response",
  "speaking_mode": "guided_response",
  "speaker_roles": [],
  "theme": "DailyRoutine",
  "level_estimate": "A1",
  "input_text": "Time to brush your teeth.",
  "prompt_text": "What should you say or do now?",
  "expected_response_shape": {
    "response_type": "short_sentence",
    "min_words": 2,
    "max_words": 8,
    "required_elements": [],
    "optional_elements": ["brush", "teeth"],
    "example_responses": ["I brush my teeth.", "I will brush my teeth."],
    "non_scoring_notes": ["Examples are guidance only; V1 does not score speech."]
  },
  "allowed_variation": {
    "allow_synonym": false,
    "allow_short_answer": true,
    "allow_full_sentence": true,
    "allow_role_paraphrase": false
  },
  "blocked_generation_behavior": [
    "do_not_treat_parent_functional_sentence_as_dialogue_authority",
    "do_not_infer_speaker_turns_without_derivation",
    "do_not_promote_without_review"
  ],
  "authority_status": "candidate_only",
  "review_status": "pending",
  "validator_requirements": [
    "source_trace_required",
    "no_asr_claim",
    "no_speech_score_claim"
  ]
}
```

### 9.2 AUX-S5 role-play turn

```json
{
  "prompt_id": "SPK_AUXS5_000001",
  "source_family": "AUX-S5",
  "source_id": "AUXS5_STORY_DIALOGUE_000001",
  "source_trace": {
    "source_type": "story_dialogue",
    "source_path": "TBD",
    "source_record_id": "TBD",
    "source_text_hash": "TBD",
    "evidence_text": "TBD"
  },
  "prompt_type": "role_play_turn",
  "speaking_mode": "role_play",
  "speaker_roles": [
    {"role_id": "role_a", "display_name": "Character A"},
    {"role_id": "role_b", "display_name": "Character B"}
  ],
  "theme": "StoryDialogue",
  "level_estimate": "A1",
  "input_text": "TBD",
  "prompt_text": "You are Character B. Answer Character A.",
  "expected_response_shape": {
    "response_type": "role_turn",
    "min_words": 2,
    "max_words": 12,
    "required_elements": [],
    "optional_elements": [],
    "example_responses": [],
    "non_scoring_notes": ["V1 only renders the prompt; it does not score the answer."]
  },
  "allowed_variation": {
    "allow_synonym": true,
    "allow_short_answer": true,
    "allow_full_sentence": true,
    "allow_role_paraphrase": true
  },
  "blocked_generation_behavior": [
    "do_not_flatten_story_dialogue_context",
    "do_not_drop_speaker_order_when_available",
    "do_not_promote_without_source_trace_and_review"
  ],
  "authority_status": "candidate_only",
  "review_status": "pending",
  "validator_requirements": [
    "source_trace_required",
    "speaker_roles_required_when_source_roles_exist",
    "no_asr_claim",
    "no_speech_score_claim"
  ]
}
```

### 9.3 AUX-S7 generated candidate

```json
{
  "prompt_id": "SPK_AUXS7_000001",
  "source_family": "AUX-S7",
  "source_id": "AUXS7_GEN_DIALOGUE_CAND_000001",
  "source_trace": {
    "source_type": "generated_dialogue_candidate",
    "source_path": "TBD",
    "source_record_id": "TBD",
    "source_text_hash": "TBD",
    "evidence_text": "TBD",
    "generated": true,
    "generation_basis": "TBD"
  },
  "prompt_type": "oral_sentence_builder",
  "speaking_mode": "sentence_building",
  "speaker_roles": [],
  "theme": "General",
  "level_estimate": "A1",
  "input_text": "TBD",
  "prompt_text": "Make one sentence with the cue.",
  "expected_response_shape": {
    "response_type": "short_sentence",
    "min_words": 3,
    "max_words": 10,
    "required_elements": [],
    "optional_elements": [],
    "example_responses": [],
    "non_scoring_notes": ["Generated candidate only; not authority."]
  },
  "allowed_variation": {
    "allow_synonym": false,
    "allow_short_answer": false,
    "allow_full_sentence": true,
    "allow_role_paraphrase": false
  },
  "blocked_generation_behavior": [
    "do_not_treat_generated_content_as_authority",
    "do_not_mark_generated_content_as_source_grounded_without_evidence",
    "do_not_make_generated_content_learner_facing_without_review"
  ],
  "authority_status": "candidate_only",
  "review_status": "pending",
  "validator_requirements": [
    "generated_trace_required",
    "candidate_only_required",
    "review_pending_required",
    "no_asr_claim",
    "no_speech_score_claim"
  ]
}
```

## 10. Design Decision

P4-S2 should remain a contract-only design scan.

Implementation should wait until:

1. P4-S3 defines role-play prompt package contract.
2. P4-S4 defines candidate boundary and promotion rules.
3. P4-S5 produces a small reviewed sample package.
4. P4-S6 implements validator checks.

This prevents P4 from accidentally becoming a generator, ASR, scoring, or UI task.

## 11. Gate Metrics

- Speaking prompt contract defined: PASS
- Required fields defined: PASS
- Source-specific rules for AUX-S4/AUX-S5/AUX-S7 defined: PASS
- `candidate_only` guard for AUX-S7 defined: PASS
- Prompt-only V1 boundary preserved: PASS
- Validator requirements drafted: PASS
- Examples included: PASS
- No generator code written: PASS
- No runtime modified: PASS
- No UI implemented: PASS
- No ASR/scoring/audio implemented: PASS

## 12. Distance Vector

Current sub-task:

`E4S-P4-S2_SpeakingPromptContract_DesignScan -> COMPLETED`

Remaining P4 sub-tasks:

1. `E4S-P4-S3_RolePlayPromptPackageContract_DesignScan`
2. `E4S-P4-S4_DialogueCandidateBoundaryContract_DesignScan`
3. `E4S-P4-S5_SamplePromptPackage_Implementation`
4. `E4S-P4-S6_PromptValidator_Implementation`
5. `E4S-P4-S7_ReadbackQA`

Total Distance: `D_p4 = 5 sub-tasks left`

## 13. Next Shortest Step

NEXT_SHORT_STEP: `E4S-P4-S3_RolePlayPromptPackageContract_DesignScan`

Unique execution action:

Define the role-play prompt package contract only. Do not implement renderer, generator, ASR, audio, speech scoring, UI, or learner-state integration.

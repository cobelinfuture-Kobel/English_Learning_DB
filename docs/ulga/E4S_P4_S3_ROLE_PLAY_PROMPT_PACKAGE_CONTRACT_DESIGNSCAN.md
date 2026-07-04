# E4S-P4-S3 Role-Play Prompt Package Contract DesignScan

## 1. Current State

Epic ID: `E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem`

Phase ID: `E4S-P4_DialogueSpeakingPromptSystem`

Sub-task ID: `E4S-P4-S3_RolePlayPromptPackageContract_DesignScan`

Status: `COMPLETED`

## 2. Design Scope

This task defines the V1 contract for a role-play prompt package.

A role-play prompt package is a container that groups multiple source-grounded speaking prompt records into a structured role-play activity.

This task does not implement:

- role-play renderer
- prompt generator
- ASR
- recording
- speech scoring
- audio pipeline
- student-facing UI
- learner-state integration
- final Dialogue Authority promotion

## 3. Source Basis

This contract extends P4-S2 Speaking Prompt Contract.

P4-S2 defines a single source-grounded speaking prompt record and explicitly excludes prompt generator, role-play renderer, ASR, recording, speech scoring, audio pipeline, UI, learner-state integration, and final Dialogue Authority promotion.

P4-S2 approved source families:

- `AUX-S4 Parent Functional Sentence Corpus`
- `AUX-S5 Story Dialogue Corpus`
- `AUX-S7 Generated Dialogue Candidates`

P4-S2 source boundary:

- AUX-S4 is functional sentence / oral prompt source, not full dialogue authority.
- AUX-S5 is story/context dialogue source and may preserve role/order/context.
- AUX-S7 is generated candidate only.
- P4 V1 is prompt-only.

## 4. Role-Play Prompt Package Contract V1

A valid role-play prompt package must be a structured activity package containing scenario metadata, role definitions, turn sequence, linked speaking prompts, source traces, and validator requirements.

It must not depend on recording, ASR, scoring, audio, UI rendering, or learner-state logic.

### 4.1 Required fields

```json
{
  "package_id": "RPP_AUXS5_000001",
  "package_type": "role_play_package",
  "source_family": "AUX-S5",
  "source_ids": ["AUXS5_STORY_DIALOGUE_000001"],
  "source_trace": {
    "source_type": "story_dialogue",
    "source_path": "",
    "source_record_ids": [],
    "source_text_hashes": [],
    "evidence_texts": []
  },
  "scenario": {
    "title": "At the Shop",
    "theme": "Shopping",
    "setting": "shop",
    "situation_summary": "Two people talk in a shop.",
    "level_estimate": "A1"
  },
  "roles": [],
  "turn_sequence": [],
  "prompt_refs": [],
  "package_flow": {
    "student_role_options": [],
    "turn_count": 0,
    "practice_mode": "guided_role_play"
  },
  "constraints": {
    "prompt_only": true,
    "requires_recording": false,
    "requires_asr": false,
    "requires_scoring": false,
    "requires_audio": false,
    "requires_ui_renderer": false
  },
  "authority_status": "candidate_only",
  "review_status": "pending",
  "validator_requirements": []
}
```

### 4.2 Field definitions

| Field | Required | Purpose |
|---|---:|---|
| `package_id` | yes | Stable package identifier. |
| `package_type` | yes | Must identify this as a role-play package or related V1 package type. |
| `source_family` | yes | Dominant source family: `AUX-S4`, `AUX-S5`, or `AUX-S7`. |
| `source_ids` | yes | Source record ids used by the package. |
| `source_trace` | yes | Evidence pointers for all package source material. |
| `scenario` | yes | Role-play situation metadata. |
| `roles` | yes | Role definitions visible to the learner/teacher. |
| `turn_sequence` | yes | Ordered role-play turns. |
| `prompt_refs` | yes | Links to P4-S2 speaking prompt records or inline prompt candidates. |
| `package_flow` | yes | How the package is practiced, without renderer logic. |
| `constraints` | yes | Explicit no-ASR/no-scoring/no-UI constraints. |
| `authority_status` | yes | V1 authority state. |
| `review_status` | yes | Review state. |
| `validator_requirements` | yes | Validation requirements before sample packaging. |

## 5. Controlled Enumerations

### 5.1 `package_type`

Allowed V1 values:

```text
role_play_package
role_response_package
story_retell_package
context_question_package
substitution_role_play_package
```

Definitions:

| package_type | Intended source | Description |
|---|---|---|
| `role_play_package` | AUX-S5 | Multi-role package with ordered turns. |
| `role_response_package` | AUX-S5 / AUX-S7 | Learner answers as one role in a given situation. |
| `story_retell_package` | AUX-S5 | Learner retells a short story/dialogue context. |
| `context_question_package` | AUX-S5 | Group of oral questions grounded in a context. |
| `substitution_role_play_package` | AUX-S4 / AUX-S7 | Controlled sentence-substitution activity with role labels. |

### 5.2 `practice_mode`

Allowed V1 values:

```text
guided_role_play
one_role_response
teacher_student_role_play
parent_child_role_play
story_retell
context_qna
substitution_drill
```

Mode boundaries:

- `guided_role_play` does not imply renderer.
- `teacher_student_role_play` does not imply classroom app UI.
- `parent_child_role_play` does not turn AUX-S4 into Dialogue Authority.
- `story_retell` does not imply speech scoring.
- `context_qna` does not imply ASR answer checking.

### 5.3 `authority_status`

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

### 5.4 `review_status`

Allowed values:

```text
pending
reviewed
needs_revision
rejected
```

## 6. Scenario Contract

`scenario` describes the communicative context.

Required subfields:

```json
{
  "title": "At the Shop",
  "theme": "Shopping",
  "setting": "shop",
  "situation_summary": "Two people talk in a shop.",
  "level_estimate": "A1",
  "level_confidence": "low",
  "source_grounded": true
}
```

Rules:

- `title` must be short and learner-readable.
- `theme` should align with existing theme labels where possible.
- `setting` must not invent source context unless marked as derived.
- `situation_summary` must be grounded in source or explicitly marked as derived.
- `level_estimate` is not final CEFR authority.

## 7. Roles Contract

`roles` defines available speakers/participants.

Required subfields per role:

```json
{
  "role_id": "role_a",
  "display_name": "Shopkeeper",
  "role_type": "adult_or_worker",
  "source_role_name": "",
  "learner_playable": true,
  "role_notes": []
}
```

Allowed `role_type` values:

```text
child
parent
teacher
student
friend
adult_or_worker
character
narrator
unknown_role
```

Rules:

- AUX-S5 roles should preserve source role names when available.
- AUX-S4 may use generic roles only when package is explicitly derived as a role-play candidate.
- AUX-S7 roles must be marked as generated/derived through source trace.
- A package with `practice_mode = guided_role_play` must have at least two roles.
- A package with `practice_mode = story_retell` may use `narrator` as the learner role.

## 8. Turn Sequence Contract

`turn_sequence` defines ordered role-play turns.

Required subfields per turn:

```json
{
  "turn_id": "turn_001",
  "turn_index": 1,
  "speaker_role_id": "role_a",
  "turn_type": "source_line",
  "prompt_ref": "SPK_AUXS5_000001",
  "source_text": "",
  "student_action": "read_or_answer",
  "expected_response_shape_ref": "SPK_AUXS5_000001.expected_response_shape",
  "optional_support": []
}
```

Allowed `turn_type` values:

```text
source_line
student_prompt
teacher_prompt
narration
cue_only
derived_line
generated_candidate_line
```

Allowed `student_action` values:

```text
listen_or_read
read_aloud
repeat
answer
choose_role_response
retell
substitute
```

Rules:

- `turn_index` must be continuous and ordered.
- `speaker_role_id` must exist in `roles` unless `turn_type = narration`.
- `prompt_ref` must reference a P4-S2 speaking prompt record when the turn expects learner output.
- Source turn order must be preserved for AUX-S5 unless package explicitly marks a derived sequence.
- AUX-S7 generated turns must use `turn_type = generated_candidate_line` or `derived_line`.

## 9. Prompt Refs Contract

`prompt_refs` links package turns to P4-S2 prompt records.

Required subfields per prompt ref:

```json
{
  "prompt_ref": "SPK_AUXS5_000001",
  "prompt_role": "learner_output",
  "turn_ids": ["turn_002"],
  "prompt_type": "role_play_turn",
  "speaking_mode": "role_play"
}
```

Allowed `prompt_role` values:

```text
learner_output
teacher_cue
context_question
retell_prompt
substitution_prompt
support_prompt
```

Rules:

- A package must contain at least one `learner_output` prompt ref.
- Prompt refs must be compatible with the package's `practice_mode`.
- `role_play_package` must include at least one prompt with `prompt_type = role_play_turn` or `role_response`.
- `story_retell_package` must include at least one `retell_prompt` or `context_question` prompt.

## 10. Source-Specific Package Rules

### 10.1 AUX-S4 Parent Functional Sentence Corpus

AUX-S4 may produce package types:

- `substitution_role_play_package`
- `role_response_package`
- `context_question_package`

Rules:

- Package must state it is derived from functional sentence source.
- Generic roles are allowed only if marked as derived.
- Do not claim original dialogue context.
- Do not assign multi-turn source dialogue unless turn sequence is explicitly generated/derived and reviewed.

Required blocked behavior:

```json
[
  "do_not_treat_parent_functional_sentence_as_original_dialogue",
  "do_not_claim_source_speaker_turns_when_absent",
  "do_not_promote_derived_role_play_without_review"
]
```

### 10.2 AUX-S5 Story Dialogue Corpus

AUX-S5 may produce package types:

- `role_play_package`
- `role_response_package`
- `story_retell_package`
- `context_question_package`

Rules:

- Preserve speaker roles, turn order, and story context when present.
- If roles exist in source, `roles` must not be empty.
- If source turn order exists, `turn_sequence` must preserve order unless marked as derived.
- Do not flatten story context into isolated prompts only.

Required blocked behavior:

```json
[
  "do_not_flatten_story_dialogue_context",
  "do_not_drop_speaker_order_when_available",
  "do_not_promote_without_source_trace_and_review"
]
```

### 10.3 AUX-S7 Generated Dialogue Candidates

AUX-S7 may produce package types:

- `role_response_package`
- `substitution_role_play_package`
- `context_question_package`

Rules:

- `authority_status` must be `candidate_only`.
- `review_status` must start as `pending`.
- Source trace must include generated/derived metadata.
- Package cannot claim source-grounded authority unless there is explicit evidence.
- Package cannot be learner-facing final in V1.

Required blocked behavior:

```json
[
  "do_not_treat_generated_package_as_authority",
  "do_not_mark_generated_package_as_source_grounded_without_evidence",
  "do_not_make_generated_package_learner_facing_without_review"
]
```

## 11. Package Validator Requirements Draft

A future validator must fail a role-play package if:

1. `package_id` is missing.
2. `package_type` is outside the V1 allowed set.
3. `source_family` is not `AUX-S4`, `AUX-S5`, or `AUX-S7`.
4. `source_trace` is missing.
5. `scenario` is missing.
6. `roles` is missing.
7. `turn_sequence` is missing.
8. `prompt_refs` is missing.
9. `constraints.prompt_only` is not true.
10. Any constraint claims recording, ASR, scoring, audio, UI renderer, or learner-state dependency.
11. `authority_status` is outside the allowed V1 set.
12. `review_status` is missing.
13. `role_play_package` has fewer than two roles.
14. A learner-output turn lacks a `prompt_ref`.
15. A `prompt_ref` points to an unsupported prompt type.
16. AUX-S5 source roles exist but package roles are empty.
17. AUX-S5 source order exists but `turn_sequence` is unordered or discontinuous.
18. AUX-S7 package is not `candidate_only`.
19. AUX-S7 package lacks generated/derived source trace.
20. V1 package claims `learner_facing_final`, `production_ready`, ASR, recording, pronunciation scoring, or speech scoring.

Validator should warn if:

1. `scenario.theme` is `General` but source suggests a clearer theme.
2. `scenario.level_estimate` lacks confidence metadata.
3. A role has `unknown_role` but source likely has a role name.
4. A turn has no `optional_support` for PreA1/A1.
5. `turn_count` is too high for A1 practice.
6. Package mixes AUX-S4 and AUX-S7 without explicit derivation notes.

## 12. Example Package Records

### 12.1 AUX-S5 role-play package

```json
{
  "package_id": "RPP_AUXS5_000001",
  "package_type": "role_play_package",
  "source_family": "AUX-S5",
  "source_ids": ["AUXS5_STORY_DIALOGUE_000001"],
  "source_trace": {
    "source_type": "story_dialogue",
    "source_path": "TBD",
    "source_record_ids": ["TBD"],
    "source_text_hashes": ["TBD"],
    "evidence_texts": ["TBD"]
  },
  "scenario": {
    "title": "At the Shop",
    "theme": "Shopping",
    "setting": "shop",
    "situation_summary": "Two people talk in a shop.",
    "level_estimate": "A1",
    "level_confidence": "low",
    "source_grounded": true
  },
  "roles": [
    {
      "role_id": "role_a",
      "display_name": "Shopkeeper",
      "role_type": "adult_or_worker",
      "source_role_name": "TBD",
      "learner_playable": false,
      "role_notes": []
    },
    {
      "role_id": "role_b",
      "display_name": "Customer",
      "role_type": "character",
      "source_role_name": "TBD",
      "learner_playable": true,
      "role_notes": []
    }
  ],
  "turn_sequence": [
    {
      "turn_id": "turn_001",
      "turn_index": 1,
      "speaker_role_id": "role_a",
      "turn_type": "source_line",
      "prompt_ref": null,
      "source_text": "TBD",
      "student_action": "listen_or_read",
      "expected_response_shape_ref": null,
      "optional_support": []
    },
    {
      "turn_id": "turn_002",
      "turn_index": 2,
      "speaker_role_id": "role_b",
      "turn_type": "student_prompt",
      "prompt_ref": "SPK_AUXS5_000001",
      "source_text": "TBD",
      "student_action": "answer",
      "expected_response_shape_ref": "SPK_AUXS5_000001.expected_response_shape",
      "optional_support": ["Use a short sentence."]
    }
  ],
  "prompt_refs": [
    {
      "prompt_ref": "SPK_AUXS5_000001",
      "prompt_role": "learner_output",
      "turn_ids": ["turn_002"],
      "prompt_type": "role_play_turn",
      "speaking_mode": "role_play"
    }
  ],
  "package_flow": {
    "student_role_options": ["role_b"],
    "turn_count": 2,
    "practice_mode": "guided_role_play"
  },
  "constraints": {
    "prompt_only": true,
    "requires_recording": false,
    "requires_asr": false,
    "requires_scoring": false,
    "requires_audio": false,
    "requires_ui_renderer": false
  },
  "authority_status": "candidate_only",
  "review_status": "pending",
  "validator_requirements": [
    "source_trace_required",
    "roles_required",
    "turn_order_required",
    "prompt_refs_required",
    "no_asr_claim",
    "no_speech_score_claim"
  ]
}
```

### 12.2 AUX-S4 substitution role-play package

```json
{
  "package_id": "RPP_AUXS4_000001",
  "package_type": "substitution_role_play_package",
  "source_family": "AUX-S4",
  "source_ids": ["AUXS4_PARENT_FUNC_000001"],
  "source_trace": {
    "source_type": "parent_functional_sentence",
    "source_path": "TBD",
    "source_record_ids": ["TBD"],
    "source_text_hashes": ["TBD"],
    "evidence_texts": ["Time to brush your teeth."]
  },
  "scenario": {
    "title": "Morning Routine",
    "theme": "DailyRoutine",
    "setting": "home",
    "situation_summary": "A parent gives a routine prompt at home.",
    "level_estimate": "A1",
    "level_confidence": "low",
    "source_grounded": true
  },
  "roles": [
    {
      "role_id": "role_parent",
      "display_name": "Parent",
      "role_type": "parent",
      "source_role_name": "",
      "learner_playable": false,
      "role_notes": ["Derived generic role from functional sentence context."]
    },
    {
      "role_id": "role_child",
      "display_name": "Child",
      "role_type": "child",
      "source_role_name": "",
      "learner_playable": true,
      "role_notes": ["Derived generic role from functional sentence context."]
    }
  ],
  "turn_sequence": [
    {
      "turn_id": "turn_001",
      "turn_index": 1,
      "speaker_role_id": "role_parent",
      "turn_type": "derived_line",
      "prompt_ref": null,
      "source_text": "Time to brush your teeth.",
      "student_action": "listen_or_read",
      "expected_response_shape_ref": null,
      "optional_support": []
    },
    {
      "turn_id": "turn_002",
      "turn_index": 2,
      "speaker_role_id": "role_child",
      "turn_type": "student_prompt",
      "prompt_ref": "SPK_AUXS4_000001",
      "source_text": "",
      "student_action": "answer",
      "expected_response_shape_ref": "SPK_AUXS4_000001.expected_response_shape",
      "optional_support": ["Say what you will do."]
    }
  ],
  "prompt_refs": [
    {
      "prompt_ref": "SPK_AUXS4_000001",
      "prompt_role": "learner_output",
      "turn_ids": ["turn_002"],
      "prompt_type": "functional_response",
      "speaking_mode": "guided_response"
    }
  ],
  "package_flow": {
    "student_role_options": ["role_child"],
    "turn_count": 2,
    "practice_mode": "parent_child_role_play"
  },
  "constraints": {
    "prompt_only": true,
    "requires_recording": false,
    "requires_asr": false,
    "requires_scoring": false,
    "requires_audio": false,
    "requires_ui_renderer": false
  },
  "authority_status": "candidate_only",
  "review_status": "pending",
  "validator_requirements": [
    "source_trace_required",
    "derived_role_note_required",
    "no_original_dialogue_claim",
    "no_asr_claim",
    "no_speech_score_claim"
  ]
}
```

### 12.3 AUX-S7 generated role-response package

```json
{
  "package_id": "RPP_AUXS7_000001",
  "package_type": "role_response_package",
  "source_family": "AUX-S7",
  "source_ids": ["AUXS7_GEN_DIALOGUE_CAND_000001"],
  "source_trace": {
    "source_type": "generated_dialogue_candidate",
    "source_path": "TBD",
    "source_record_ids": ["TBD"],
    "source_text_hashes": ["TBD"],
    "evidence_texts": ["TBD"],
    "generated": true,
    "generation_basis": "TBD"
  },
  "scenario": {
    "title": "Practice Answer",
    "theme": "General",
    "setting": "derived",
    "situation_summary": "Generated candidate role-response practice.",
    "level_estimate": "A1",
    "level_confidence": "low",
    "source_grounded": false
  },
  "roles": [
    {
      "role_id": "role_a",
      "display_name": "Speaker A",
      "role_type": "unknown_role",
      "source_role_name": "",
      "learner_playable": false,
      "role_notes": ["Generated role."]
    },
    {
      "role_id": "role_b",
      "display_name": "Speaker B",
      "role_type": "unknown_role",
      "source_role_name": "",
      "learner_playable": true,
      "role_notes": ["Generated role."]
    }
  ],
  "turn_sequence": [
    {
      "turn_id": "turn_001",
      "turn_index": 1,
      "speaker_role_id": "role_b",
      "turn_type": "generated_candidate_line",
      "prompt_ref": "SPK_AUXS7_000001",
      "source_text": "TBD",
      "student_action": "answer",
      "expected_response_shape_ref": "SPK_AUXS7_000001.expected_response_shape",
      "optional_support": ["Generated candidate only; teacher review required."]
    }
  ],
  "prompt_refs": [
    {
      "prompt_ref": "SPK_AUXS7_000001",
      "prompt_role": "learner_output",
      "turn_ids": ["turn_001"],
      "prompt_type": "oral_sentence_builder",
      "speaking_mode": "sentence_building"
    }
  ],
  "package_flow": {
    "student_role_options": ["role_b"],
    "turn_count": 1,
    "practice_mode": "one_role_response"
  },
  "constraints": {
    "prompt_only": true,
    "requires_recording": false,
    "requires_asr": false,
    "requires_scoring": false,
    "requires_audio": false,
    "requires_ui_renderer": false
  },
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

## 13. Design Decision

P4-S3 defines only the package-level contract.

Implementation must wait until:

1. P4-S4 defines dialogue candidate boundary and promotion rules.
2. P4-S5 creates a small sample prompt package.
3. P4-S6 implements validator checks.
4. P4-S7 performs ReadbackQA.

This prevents role-play from expanding into renderer, generator, ASR, scoring, audio, UI, or learner-state work.

## 14. Gate Metrics

- Role-play prompt package contract defined: PASS
- Package-level required fields defined: PASS
- Scenario contract defined: PASS
- Roles contract defined: PASS
- Turn sequence contract defined: PASS
- Prompt refs contract defined: PASS
- Source-specific package rules for AUX-S4/AUX-S5/AUX-S7 defined: PASS
- AUX-S7 candidate-only guard preserved: PASS
- Prompt-only V1 boundary preserved: PASS
- Validator requirements drafted: PASS
- Example package records included: PASS
- No renderer implemented: PASS
- No generator code written: PASS
- No runtime modified: PASS
- No UI implemented: PASS
- No ASR/scoring/audio implemented: PASS

## 15. Distance Vector

Current sub-task:

`E4S-P4-S3_RolePlayPromptPackageContract_DesignScan -> COMPLETED`

Remaining P4 sub-tasks:

1. `E4S-P4-S4_DialogueCandidateBoundaryContract_DesignScan`
2. `E4S-P4-S5_SamplePromptPackage_Implementation`
3. `E4S-P4-S6_PromptValidator_Implementation`
4. `E4S-P4-S7_ReadbackQA`

Total Distance: `D_p4 = 4 sub-tasks left`

## 16. Next Shortest Step

NEXT_SHORT_STEP: `E4S-P4-S4_DialogueCandidateBoundaryContract_DesignScan`

Unique execution action:

Define candidate boundary and promotion rules for dialogue/speaking prompt records and packages. Do not implement sample packages, validators, renderer, generator, ASR, audio, speech scoring, UI, or learner-state integration.

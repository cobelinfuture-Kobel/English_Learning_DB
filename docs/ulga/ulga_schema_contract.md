# ULGA Schema Contract

## Contract Status

Version: `ULGA-S1`

This document defines the first graph contract only. It is not an implementation schema file and does not authorize generation of formal graph JSON in S1.

## Core Principles

- ULGA is the authority graph layer.
- Learning Path is a graph query result.
- Source authorities remain read-only inputs.
- Nodes and edges must preserve authority source and confidence.
- Planner output must be gate-checked.
- Generator and validator runtimes must not read inferred graph data unless a later implementation stage validates it.

## Node Schema

Conceptual schema:

```json
{
  "node_id": "grammar:1741163706316x198445876411383900",
  "node_type": "GrammarNode",
  "label": "FORM: COMBINING TWO ADJECTIVES WITH 'BUT'",
  "level": "A2",
  "authority_source": {
    "source_name": "English Grammar Profile",
    "source_file": "grammar_profile/json/grammar_profile.json",
    "source_record_id": "1741163706316x198445876411383900",
    "source_row": 2
  },
  "confidence": {
    "value": 1.0,
    "method": "source_direct"
  },
  "metadata": {},
  "version": {
    "contract": "ULGA-S1",
    "source_version": null,
    "generated_at": null
  }
}
```

### Required Node Fields

| Field | Type | Required | Rule |
| --- | --- | --- | --- |
| `node_id` | string | yes | Globally unique and prefixed by node family. |
| `node_type` | enum | yes | Must be one of the approved ULGA node types. |
| `label` | string | yes | Human-readable display label. |
| `level` | string or null | no | CEFR/plus level when applicable. |
| `authority_source` | object | yes | Must identify source file and record when available. |
| `confidence` | object | yes | Must include value and method. |
| `metadata` | object | yes | Node-type-specific fields. |
| `version` | object | yes | Contract and source version metadata. |

### Approved Node Types

- `GrammarNode`
- `VocabularyNode`
- `ChunkNode`
- `ThemeNode`
- `SentencePatternNode`
- `SkillNode`
- `LearnerNode`
- `AssessmentNode`
- `MediaNode`

### Node ID Prefixes

| Node type | Prefix |
| --- | --- |
| `GrammarNode` | `grammar:` |
| `VocabularyNode` | `vocab:` |
| `ChunkNode` | `chunk:` or `safe_chunk:` |
| `ThemeNode` | `theme:` |
| `SentencePatternNode` | `pattern:` |
| `SkillNode` | `skill:` |
| `LearnerNode` | `learner:` |
| `AssessmentNode` | `assessment:` |
| `MediaNode` | `media:` |

## Edge Schema

Conceptual schema:

```json
{
  "edge_id": "edge:grammar:past_simple:requires:vocab:yesterday",
  "edge_type": "REQUIRES",
  "from_node_id": "grammar:past_simple",
  "to_node_id": "vocab:yesterday",
  "direction": "from_requires_to",
  "authority_source": {
    "source_name": "ULGA Dependency Authority",
    "source_file": null,
    "source_record_id": null
  },
  "confidence": {
    "value": 0.7,
    "method": "rule_based_design"
  },
  "metadata": {
    "hard_gate": true,
    "reason": "Past simple exercise requires past-time vocabulary."
  },
  "version": {
    "contract": "ULGA-S1",
    "source_version": null,
    "generated_at": null
  }
}
```

### Required Edge Fields

| Field | Type | Required | Rule |
| --- | --- | --- | --- |
| `edge_id` | string | yes | Globally unique and deterministic where possible. |
| `edge_type` | enum | yes | Must be one of the approved ULGA edge types. |
| `from_node_id` | string | yes | Must reference an existing node. |
| `to_node_id` | string | yes | Must reference an existing node. |
| `direction` | string | yes | Must describe semantic direction. |
| `authority_source` | object | yes | Must identify source or rule authority. |
| `confidence` | object | yes | Must include value and method. |
| `metadata` | object | yes | Edge-type-specific details. |
| `version` | object | yes | Contract and source version metadata. |

### Approved Edge Types

- `REQUIRES`
- `CONTAINS`
- `USES`
- `SPIRAL_TO`
- `PRECEDES`
- `ALIGNS_WITH`
- `BLOCKS`
- `RECOMMENDS`
- `ASSESSES`
- `GENERATES`

## Authority Source Contract

`authority_source` must state whether the field is direct from a source, recovered, rule-based, or manually reviewed.

Recommended shape:

```json
{
  "source_name": "English Vocabulary Profile",
  "source_file": "vocabulary/json/vocabulary.json",
  "source_record_id": "v_2",
  "source_row": 2,
  "derivation": "source_direct"
}
```

Allowed derivation values:

- `source_direct`
- `source_recovered`
- `rule_based`
- `manual_review`
- `derived_safe_layer`
- `planner_runtime`
- `learner_runtime`

## Confidence Contract

Recommended shape:

```json
{
  "value": 0.95,
  "method": "source_direct",
  "notes": []
}
```

Confidence levels:

| Range | Meaning |
| --- | --- |
| `1.0` | Direct authoritative source with no recovery. |
| `0.8-0.99` | Source-backed with deterministic recovery or canonicalization. |
| `0.5-0.79` | Rule-based inference requiring later audit. |
| `<0.5` | Experimental or learner-runtime signal only. |

Validation rule: hard gates should not depend on confidence below `0.8` unless explicitly marked as provisional.

## Metadata Contract By Node Type

### GrammarNode Metadata

Required:

- `super_category`
- `sub_category`
- `guideword`
- `can_do_statement`
- `example`
- `lexical_range`

### VocabularyNode Metadata

Required:

- `word`
- `guideword`
- `part_of_speech`
- `topic`
- `frequency_band`
- `active`
- `duplicate_status`
- `recovery_confidence`

### ChunkNode Metadata

Required:

- `chunk`
- `normalized_chunk`
- `chunk_type`
- `guideword`
- `usage_class`
- `equivalent_ids`
- `validator_accepts_equivalents`
- `generator_allowed`

### ThemeNode Metadata

Required:

- `theme_name`
- `parent_theme`
- `progression_stage`
- `description`
- `active_vocabulary_count`

### SentencePatternNode Metadata

Required once source exists:

- `pattern_text`
- `slot_constraints`
- `grammar_refs`
- `example`

### SkillNode Metadata

Required:

- `skill_domain`
- `mode`
- `assessment_methods`

### LearnerNode Metadata

Required:

- `current_level`
- `target_level`
- `mastery_state_ref`
- `blocked_nodes`
- `recent_assessment_refs`

### AssessmentNode Metadata

Required:

- `assessment_type`
- `target_nodes`
- `skill_domain`
- `difficulty`
- `evidence_model`

### MediaNode Metadata

Required:

- `media_type`
- `complexity`
- `linked_theme`
- `generation_status`

## Versioning

Every node and edge must carry:

- `contract`: ULGA contract version, starting with `ULGA-S1`.
- `source_version`: source authority version or file timestamp when formal version is unavailable.
- `generated_at`: null for design, timestamp for generated graph artifacts in later stages.

Graph-level version metadata in ULGA-S2 should include:

- `graph_id`
- `contract_version`
- `source_manifest`
- `build_tool`
- `build_timestamp`
- `validation_status`

## Validation Rules

ULGA-S2 implementation should validate:

- Every node has required contract fields.
- Every node ID is unique.
- Every edge ID is unique.
- Every edge endpoint references an existing node.
- Every `node_type` and `edge_type` is in the approved enum.
- Every node and edge has `authority_source`.
- Every node and edge has `confidence.value` between `0` and `1`.
- Hard gate edges must have confidence >= `0.8` or `metadata.provisional = true`.
- `REQUIRES` and `BLOCKS` must not form unreviewed cycles.
- `SPIRAL_TO` should move forward in level/progression stage.
- `GENERATES` edges must not point directly to raw unsafe chunk records.
- `ChunkNode` generator use should prefer `chunks_generator_safe.json`.
- `VocabularyNode` generator use should prefer active canonical records.
- `LearnerNode` must not be persisted as static curriculum authority.

## Planner Contract

Planner input:

```json
{
  "graph_ref": "ULGA graph",
  "learner_mastery_state": {},
  "target_level": "A2",
  "target_theme": "a2_travel",
  "blocked_nodes": [],
  "available_question_types": ["multiple_choice", "short_answer"]
}
```

Planner output:

```json
{
  "next_best_nodes": [],
  "blocked_reason": [],
  "prerequisite_gap": [],
  "recommended_exercise_type": []
}
```

Planner output is advisory. Gate Engine approval is required before downstream generation.

## Gate Contract

Gate input:

```json
{
  "candidate_nodes": [],
  "target_level": "A2",
  "target_theme": "a2_travel",
  "learner_mastery_state": {},
  "blocked_nodes": []
}
```

Gate output:

```json
{
  "allowed_nodes": [],
  "blocked_nodes": [
    {
      "node_id": "chunk:EVP_CHUNK_000001",
      "gate": "Level Gate",
      "reason": "C2 chunk above A2 ceiling."
    }
  ],
  "gate_trace": []
}
```

Gate types:

- Dependency Gate
- Grammar Gate
- Vocabulary Gate
- Chunk Gate
- Theme Gate
- Level Gate


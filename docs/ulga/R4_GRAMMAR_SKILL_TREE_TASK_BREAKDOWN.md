# R4 GrammarSkillTree Task Breakdown

## Current State

Epic ID:

```text
R4_GrammarSkillTree_OrderAndAlignment
```

Chinese name:

```text
Grammar 技能樹、順序表與 CEFR/EGP 對齊設計
```

R4 is a design-and-contract milestone. It does not generate learner-facing question banks and does not write learner state.

## Why R4 Exists

Reading V1 can now read local RAZ text and render runnable practice output, but it does not yet know whether a sentence or question is aligned with a coherent grammar learning sequence.

R4 creates the grammar sequence authority needed before large-scale ReadingV1 question generation.

R4 must answer four questions:

```text
1. What is the system grammar teaching order?
2. Where does each grammar item focus / recycle / preview / block across A1-B2?
3. How does the system order align with CEFR / English Grammar Profile evidence?
4. For a learner, what grammar node is unlocked next?
```

## Scope Lock

R4 does:

```text
- define grammar_nodes
- define grammar_edges
- define A1-B2 stage map
- define focus / recycle / preview / blocked policy
- define grammar order table contract
- define CEFR / EGP alignment contract
- define grammar coverage matrix contract
- define learner mastery levels
- define next-step gate contract
- define AI grammar tagging role
- define validator contract
- define implementation-ready task sequence
```

R4 does not:

```text
- generate ReadingV1 question bank
- promote AI output to authority
- write learner state
- implement adaptive planner runtime
- implement public product UI
- implement Cambridge formal exam mapping
- generate commercial worksheets
- publish RAZ full text
```

## Data Source Principles

```text
CEFR / EGP = external authority evidence
GrammarSkillTree = internal teaching order
LearnerMastery = individual readiness
Validator = final gatekeeper
```

CEFR / EGP should not directly decide teaching order. The system order is computed from dependency edges, stage constraints, spiral policy, and alignment evidence.

For children, YLE can be used as a learning-path reference while CEFR remains a difficulty authority. This is especially relevant to James / Cyndi style paths such as PreA1 Starters -> A1 Movers -> A2 Flyers -> KET.

---

# Middle Task Overview

```text
R4-M0  Scope and Governance Lock
R4-M1  Authority Source Inventory and Evidence Contract
R4-M2  Grammar Node Schema Design
R4-M3  Grammar Dependency Edge Schema Design
R4-M4  A1-B2 Stage Map Design
R4-M5  Focus / Recycle / Preview / Blocked Policy Design
R4-M6  Grammar Order Table Contract
R4-M7  CEFR / EGP Alignment Table Contract
R4-M8  Grammar Coverage Matrix Contract
R4-M9  Sentence Pattern / Chunk / Vocabulary / Theme Linkage Contract
R4-M10 AI Grammar Tagging Candidate Contract
R4-M11 Grammar Validator Contract
R4-M12 Learner Mastery and Next-Step Gate Contract
R4-M13 R4 QA / Readback / Closeout Contract
R4-M14 R5 Implementation Handoff Plan
```

---

# R4-M0 Scope and Governance Lock

## Purpose

Lock R4 as GrammarSkillTree design, not question generation or adaptive runtime.

## Small Tasks

```text
R4-M0-S1 Define R4 epic ID and objective
R4-M0-S2 Define allowed scope
R4-M0-S3 Define forbidden scope
R4-M0-S4 Define relation to ReadingV1 and future adaptive planner
R4-M0-S5 Define R4 completion gates
```

## Artifacts

```text
docs/ulga/R4_GRAMMAR_SKILL_TREE_TASK_BREAKDOWN.md
```

## Gate PASS

```text
R4 scope is explicit.
R4 is not allowed to generate question banks.
R4 is not allowed to write learner state.
R4 has a clear next implementation handoff.
```

---

# R4-M1 Authority Source Inventory and Evidence Contract

## Purpose

Define which sources can support grammar order and which sources cannot directly determine order.

## Small Tasks

```text
R4-M1-S1 Register EGP / English Grammar Profile as grammar authority evidence
R4-M1-S2 Register CEFR as difficulty / proficiency evidence
R4-M1-S3 Register YLE / Cambridge children path as learning-path reference where applicable
R4-M1-S4 Register existing ReadingV1 / RAZ text as source sentence evidence only
R4-M1-S5 Define source roles: authority_source, normalized_authority_artifact, candidate_evidence, learner_facing_source
R4-M1-S6 Define evidence confidence levels
```

## Expected Fields

```json
{
  "source_id": "EGP_SOURCE_XLSX",
  "source_family": "grammar_authority",
  "source_role": "authority_source",
  "allowed_use": ["level_alignment", "grammar_construct_reference"],
  "blocked_use": ["direct_teaching_order", "learner_state_write"],
  "learner_facing_allowed": false
}
```

## Gate PASS

```text
Each source has allowed_use and blocked_use.
EGP / CEFR are evidence layers, not direct order generators.
RAZ is source sentence evidence, not grammar authority.
```

---

# R4-M2 Grammar Node Schema Design

## Purpose

Define the canonical grammar node structure.

## Small Tasks

```text
R4-M2-S1 Define grammar_id convention
R4-M2-S2 Define grammar category taxonomy
R4-M2-S3 Define canonical label / description / examples
R4-M2-S4 Define CEFR / EGP evidence fields
R4-M2-S5 Define introduced_stage / recycle_stages / blocked_before fields
R4-M2-S6 Define relation to sentence patterns, chunks, vocabulary, themes
```

## Expected Artifact Later

```text
ulga/grammar/grammar_nodes.json
ulga/schemas/grammar_node.schema.json
```

## Example Node

```json
{
  "grammar_id": "GRAMMAR_THERE_IS",
  "label": "there is / there are",
  "category": "existential_structure",
  "cefr_band": ["A1"],
  "egp_evidence_refs": [],
  "introduced_stage": "A1_PLUS",
  "recycle_stages": ["A2", "A2_PLUS", "B1"],
  "blocked_before": ["A1"],
  "example_patterns": [
    "There is a ___.",
    "There are ___ in the ___."
  ]
}
```

## Gate PASS

```text
Grammar nodes are stable, unique, traceable, and linkable.
Nodes can support order table, coverage matrix, and validation.
```

---

# R4-M3 Grammar Dependency Edge Schema Design

## Purpose

Define prerequisite edges so the order table can be computed instead of hand-listed.

## Small Tasks

```text
R4-M3-S1 Define edge_id convention
R4-M3-S2 Define REQUIRES edge
R4-M3-S3 Define PRECEDES edge
R4-M3-S4 Define REINFORCES edge
R4-M3-S5 Define CONTRASTS_WITH / CONFUSABLE_WITH edge
R4-M3-S6 Define source_evidence and confidence fields
R4-M3-S7 Define AI-suggested edge candidate policy
```

## Expected Artifact Later

```text
ulga/grammar/grammar_edges.json
ulga/schemas/grammar_edge.schema.json
```

## Example Edge

```json
{
  "edge_id": "GEDGE_000001",
  "source": "GRAMMAR_BE_VERB_BASIC",
  "target": "GRAMMAR_PRESENT_CONTINUOUS",
  "relation": "REQUIRES",
  "reason": "Present continuous requires be verb control plus action verb -ing form.",
  "evidence_type": "expert_rule",
  "confidence": 0.95,
  "review_status": "approved"
}
```

## Gate PASS

```text
Each edge points to existing grammar nodes.
Dependency graph can be checked for cycles.
AI-generated edges remain candidate_only until reviewed.
```

---

# R4-M4 A1-B2 Stage Map Design

## Purpose

Define the internal stages used by ReadingV1 / GrammarSkillTree.

## Stage Set

```text
A1
A1_PLUS
A2
A2_PLUS
B1
B1_PLUS
B2
```

## Small Tasks

```text
R4-M4-S1 Define stage_id and display_name
R4-M4-S2 Define CEFR band relation
R4-M4-S3 Define optional YLE / Cambridge relation
R4-M4-S4 Define sentence length expectation
R4-M4-S5 Define allowed source evidence level
R4-M4-S6 Define stage transition rule
```

## Expected Artifact Later

```text
ulga/grammar/grammar_stage_map.json
ulga/schemas/grammar_stage_map.schema.json
```

## Gate PASS

```text
Each stage has a stable role.
A1+ / A2+ / B1+ are internal milestones, not fake CEFR official levels.
```

---

# R4-M5 Focus / Recycle / Preview / Blocked Policy Design

## Purpose

Define spiral grammar roles across levels.

## Role Definitions

```text
focus      = newly taught and assessed
recycle    = previously taught and practiced again
preview    = may appear in reading input but not assessed for production
blocked    = should not appear in generated practice for this stage
maintenance = old grammar kept active with low-weight review
expand     = known grammar expanded to a more complex form
```

## Small Tasks

```text
R4-M5-S1 Define role enum
R4-M5-S2 Define allowed transitions between roles
R4-M5-S3 Define default spiral ratio
R4-M5-S4 Define blocked grammar enforcement
R4-M5-S5 Define preview-only policy
R4-M5-S6 Define maintenance policy
```

## Default Spiral Ratio

```text
70% recycled / maintenance grammar
20% focus grammar
10% preview grammar
```

## Gate PASS

```text
A grammar item cannot be focus before prerequisites.
Blocked grammar cannot appear in generated learner-facing items.
Preview grammar cannot be assessed as required knowledge.
```

---

# R4-M6 Grammar Order Table Contract

## Purpose

Define the computed order table that answers: grammar 教學順序是什麼？

## Small Tasks

```text
R4-M6-S1 Define grammar_order_table fields
R4-M6-S2 Define topological sort requirements
R4-M6-S3 Define tie-breakers when multiple nodes are available
R4-M6-S4 Define stage constraint filter
R4-M6-S5 Define unlock condition format
R4-M6-S6 Define order conflict handling
```

## Expected Artifact Later

```text
ulga/grammar/grammar_order_table.json
```

## Required Fields

```json
{
  "order": 5,
  "stage": "A1_PLUS",
  "grammar_id": "GRAMMAR_THERE_IS",
  "role": "focus",
  "prerequisites": ["GRAMMAR_BE_VERB_BASIC", "GRAMMAR_SINGULAR_PLURAL_NOUN"],
  "unlock_condition": "all_prerequisites_at_or_above_M3",
  "alignment_status": "MATCH_WITH_DEPENDENCY_DELAY"
}
```

## Gate PASS

```text
Order table is derived from graph + constraints, not hand-only sequence.
Every row explains why it is placed there.
```

---

# R4-M7 CEFR / EGP Alignment Table Contract

## Purpose

Check whether the internal teaching order aligns with external grammar authority evidence.

## Small Tasks

```text
R4-M7-S1 Define alignment_status enum
R4-M7-S2 Define EGP evidence mapping fields
R4-M7-S3 Define CEFR band comparison rule
R4-M7-S4 Define early/late-by-design policy
R4-M7-S5 Define conflict review policy
R4-M7-S6 Define one-to-many / many-to-one mapping policy
```

## Alignment Status Enum

```text
MATCH
EARLY_BY_DESIGN
LATE_BY_DEPENDENCY
PREVIEW_ONLY
CONFLICT_REVIEW_REQUIRED
NOT_IN_AUTHORITY_SOURCE
```

## Expected Artifact Later

```text
ulga/grammar/grammar_cefr_egp_alignment.json
```

## Gate PASS

```text
Every grammar_order_table row has an alignment_status.
Deviation from CEFR/EGP must explain dependency, child path, or review need.
```

---

# R4-M8 Grammar Coverage Matrix Contract

## Purpose

Show where each grammar item appears across A1-B2.

## Small Tasks

```text
R4-M8-S1 Define matrix rows = grammar_id
R4-M8-S2 Define matrix columns = stage_id
R4-M8-S3 Define cell values = focus/recycle/preview/blocked/maintenance/expand
R4-M8-S4 Define gap detection
R4-M8-S5 Define too-early exposure detection
R4-M8-S6 Define recycle coverage minimum
```

## Expected Artifact Later

```text
ulga/grammar/grammar_coverage_matrix.json
ulga/reports/grammar_coverage_matrix_summary.json
```

## Gate PASS

```text
Each grammar item has visible first focus stage.
Each core grammar item has later recycle or maintenance coverage.
Blocked policy is visible and testable.
```

---

# R4-M9 Sentence Pattern / Chunk / Vocabulary / Theme Linkage Contract

## Purpose

Connect grammar nodes to actual usable language material.

## Small Tasks

```text
R4-M9-S1 Define GrammarNode -> SentencePatternNode edge
R4-M9-S2 Define GrammarNode -> ChunkNode edge
R4-M9-S3 Define GrammarNode -> VocabularyNode requirement hints
R4-M9-S4 Define GrammarNode -> ThemeNode recommended contexts
R4-M9-S5 Define ReadingSource sentence tagging linkage
R4-M9-S6 Define source evidence trace
```

## Example

```json
{
  "grammar_id": "GRAMMAR_THERE_IS",
  "pattern_ids": ["SP_THERE_IS_001"],
  "chunk_ids": ["CHUNK_IN_THE", "CHUNK_ON_THE"],
  "theme_ids": ["THEME_HOME", "THEME_SCHOOL", "THEME_TRAVEL"],
  "vocabulary_policy": {
    "allowed_cefr": ["PreA1", "A1"],
    "max_unknown_words": 1
  }
}
```

## Gate PASS

```text
Grammar is not an abstract label only.
Every focus grammar can be practiced through patterns, chunks, vocabulary, and theme.
```

---

# R4-M10 AI Grammar Tagging Candidate Contract

## Purpose

Define how AI can assist without becoming authority.

## Small Tasks

```text
R4-M10-S1 Define AI tagging input payload
R4-M10-S2 Define AI tagging output schema
R4-M10-S3 Define candidate_only status
R4-M10-S4 Define confidence and rationale requirements
R4-M10-S5 Define human / validator review boundary
R4-M10-S6 Define prohibited AI actions
```

## AI May Do

```text
- suggest grammar tags for source sentences
- suggest candidate dependency edges
- suggest sentence pattern match
- flag possible sequence violation
```

## AI Must Not Do

```text
- directly approve authority nodes
- directly unlock learner next step
- write learner state
- promote generated content to question bank
```

## Gate PASS

```text
AI output is candidate_only.
Validator or reviewer is required before promotion.
```

---

# R4-M11 Grammar Validator Contract

## Purpose

Define validation rules before grammar maps can be used by generators.

## Small Tasks

```text
R4-M11-S1 Validate grammar_id uniqueness
R4-M11-S2 Validate all edge endpoints exist
R4-M11-S3 Validate dependency graph has no cycle
R4-M11-S4 Validate introduced_stage is not earlier than prerequisites
R4-M11-S5 Validate blocked grammar does not appear in generated item policy
R4-M11-S6 Validate recycle coverage minimum
R4-M11-S7 Validate CEFR / EGP alignment status exists
R4-M11-S8 Validate next-step gate exists for focus grammar
```

## Expected Artifact Later

```text
ulga/validators/validate_grammar_skill_tree.py
ulga/reports/grammar_skill_tree_validation_report.json
```

## Gate PASS

```text
No orphan nodes.
No orphan edges.
No graph cycle.
No missing alignment status.
No missing next-step gate for focus grammar.
```

---

# R4-M12 Learner Mastery and Next-Step Gate Contract

## Purpose

Define how the system decides whether a learner can move to the next grammar node.

## Mastery Levels

```text
M0 unseen
M1 exposed
M2 recognized
M3 controlled
M4 productive
M5 transferable
```

## Small Tasks

```text
R4-M12-S1 Define mastery level enum
R4-M12-S2 Define evidence required per level
R4-M12-S3 Define minimum attempts / accuracy
R4-M12-S4 Define context coverage requirement
R4-M12-S5 Define question type coverage requirement
R4-M12-S6 Define retention / review window
R4-M12-S7 Define next-step unlock result schema
```

## Example Gate

```json
{
  "target_grammar_id": "GRAMMAR_PRESENT_CONTINUOUS",
  "requires": [
    {"grammar_id": "GRAMMAR_BE_VERB_BASIC", "min_mastery": "M3"},
    {"grammar_id": "GRAMMAR_ACTION_VERBS", "min_mastery": "M2"}
  ],
  "min_recent_accuracy": 0.8,
  "min_contexts": 2,
  "min_question_types": 2
}
```

## Gate PASS

```text
Next-step decision can return UNLOCKED, BLOCKED, or REVIEW.
Blocked decisions explain missing prerequisites.
```

---

# R4-M13 R4 QA / Readback / Closeout Contract

## Purpose

Define how R4 itself is accepted.

## Small Tasks

```text
R4-M13-S1 Verify all R4 docs exist
R4-M13-S2 Verify all expected schemas/contracts are specified
R4-M13-S3 Verify no learner-facing generation was added
R4-M13-S4 Verify no learner state write path exists
R4-M13-S5 Verify next implementation task is unambiguous
```

## R4 Closeout PASS Conditions

```text
R4-M0 PASS
R4-M1 PASS
R4-M2 PASS
R4-M3 PASS
R4-M4 PASS
R4-M5 PASS
R4-M6 PASS
R4-M7 PASS
R4-M8 PASS
R4-M9 PASS
R4-M10 PASS
R4-M11 PASS
R4-M12 PASS
R4-M13 PASS
```

---

# R4-M14 R5 Implementation Handoff Plan

## Purpose

Define the next shortest implementation sequence after R4 design is approved.

## Proposed R5 Sequence

```text
R5-M1 create grammar_node.schema.json
R5-M2 create grammar_edge.schema.json
R5-M3 seed grammar_nodes.json small pilot
R5-M4 seed grammar_edges.json small pilot
R5-M5 build grammar_order_table generator
R5-M6 build grammar_coverage_matrix generator
R5-M7 build CEFR/EGP alignment skeleton
R5-M8 build grammar_skill_tree validator
R5-M9 run pilot QA
R5-M10 close R5 pilot and expand
```

## R5 Does Not Yet Do

```text
- full A1-B2 grammar import
- learner adaptive planner
- ReadingV1 mass question generation
```

---

# Distance Vector

```text
R4 total middle tasks = 15
R4 completed middle tasks after this file = R4-M0 partial, task tree defined
R4 remaining middle tasks = 14 design/contract tasks
```

# Next Shortest Step

```text
NEXT_SHORT_STEP:
R4-M1_AuthoritySourceInventoryAndEvidenceContract_DesignScan
```

Operator trigger:

```text
R4-M1 開始
```

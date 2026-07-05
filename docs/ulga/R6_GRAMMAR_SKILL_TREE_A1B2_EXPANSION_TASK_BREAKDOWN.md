# R6 GrammarSkillTree A1-B2 Expansion Task Breakdown

## Current State

Epic ID:

```text
R6_GrammarSkillTree_A1B2Expansion
```

Chinese name:

```text
GrammarSkillTree A1-B2 擴展完整化
```

R6 is the expansion milestone after R5 pilot closeout. It turns the validated pilot GrammarSkillTree into an A1-B2 usable grammar authority layer.

## Dependency

R6 must start only after:

```text
R4_GrammarSkillTree_OrderAndAlignment = ACCEPTED
R5_GrammarSkillTree_PilotImplementation = CLOSED_PILOT_PASS
```

R6 uses R5 outputs as implementation foundations:

```text
grammar_node.schema.json
grammar_edge.schema.json
grammar_nodes.json pilot
grammar_edges.json pilot
grammar_order_table generator
grammar_coverage_matrix generator
grammar_cefr_egp_alignment skeleton
grammar_skill_tree validator
pilot QA report
```

## Why R6 Exists

R5 proves the GrammarSkillTree pipeline can work on a small pilot. R6 expands the pilot to A1-B2 so Reading, Listening, Speaking, Writing, Assessment, and future adaptive systems can query a stable grammar gate.

R6 must answer:

```text
1. Does the GrammarSkillTree cover the required A1-B2 grammar nodes?
2. Does every focus grammar have prerequisite edges?
3. Does every grammar item have a stage role across A1-B2?
4. Does every grammar item have CEFR / EGP alignment or an explicit review status?
5. Can validators reject missing, cyclic, too-early, or under-recycled grammar entries?
6. Can downstream four-skill systems query grammar policy by stage?
```

## Scope Lock

R6 does:

```text
- expand grammar_nodes from pilot to A1-B2 coverage
- expand grammar_edges from pilot to A1-B2 dependency coverage
- produce complete A1-B2 grammar_order_table
- produce complete A1-B2 grammar_coverage_matrix
- produce CEFR / EGP alignment status for each grammar node
- produce node-to-pattern/chunk/vocabulary/theme linkage readiness fields
- harden grammar_skill_tree validator
- produce expansion QA report
- define downstream query contract for four-skill systems
```

R6 does not:

```text
- generate learner-facing question banks
- write learner mastery state
- run adaptive planner runtime
- promote AI output without validator/review
- implement ReadingV1 mass generation
- implement Listening audio generation
- implement Speaking recording / ASR / scoring
- implement Writing scoring
- implement Cambridge formal exam mapping
- publish RAZ full text
- generate commercial worksheet output
```

## Definition of R6 Complete Version

R6 complete version means:

```text
GrammarSkillTree A1-B2 expansion is structurally usable and validator-checked.
```

It does not mean:

```text
English four-skill platform is complete.
ReadingV1 full question bank is complete.
Adaptive learner planner is complete.
Cambridge exam mode is complete.
```

---

# Middle Task Overview

```text
R6-M0  R5 Pilot Closeout Readiness Gate
R6-M1  A1-B2 Grammar Coverage Target Definition
R6-M2  Grammar Node Expansion Batch Plan
R6-M3  Grammar Edge Expansion Batch Plan
R6-M4  Stage Role Expansion Matrix
R6-M5  Grammar Order Table Full Expansion
R6-M6  CEFR / EGP Alignment Full Pass
R6-M7  Pattern / Chunk / Vocabulary / Theme Linkage Readiness Pass
R6-M8  Validator Hardening for A1-B2 Scale
R6-M9  Expansion QA Report
R6-M10 Downstream Four-Skill Query Contract
R6-M11 R6 Closeout and Handoff to Reading / Listening / Speaking / Writing
```

---

# R6-M0 R5 Pilot Closeout Readiness Gate

## Purpose

Confirm R5 is actually closed before expanding to A1-B2.

## Small Tasks

```text
R6-M0-S1 Confirm R5-M1 grammar_node.schema.json exists and passes schema QA
R6-M0-S2 Confirm R5-M2 grammar_edge.schema.json exists and passes schema QA
R6-M0-S3 Confirm R5-M3 pilot grammar_nodes.json exists
R6-M0-S4 Confirm R5-M4 pilot grammar_edges.json exists
R6-M0-S5 Confirm R5-M5 grammar_order_table generator exists
R6-M0-S6 Confirm R5-M6 grammar_coverage_matrix generator exists
R6-M0-S7 Confirm R5-M7 CEFR/EGP alignment skeleton exists
R6-M0-S8 Confirm R5-M8 grammar_skill_tree validator exists
R6-M0-S9 Confirm R5-M9 pilot QA PASS
R6-M0-S10 Confirm R5-M10 closed with expansion allowed
```

## Gate PASS

```text
R5 pilot is closed.
No R6 expansion starts from missing pilot artifacts.
```

---

# R6-M1 A1-B2 Grammar Coverage Target Definition

## Purpose

Define the target coverage boundary for A1-B2 expansion.

## Small Tasks

```text
R6-M1-S1 Define required stage set: A1, A1_PLUS, A2, A2_PLUS, B1, B1_PLUS, B2
R6-M1-S2 Define grammar category taxonomy for A1-B2
R6-M1-S3 Define minimum node coverage per category
R6-M1-S4 Define required CEFR/EGP evidence fields
R6-M1-S5 Define optional YLE / Cambridge children-path reference fields
R6-M1-S6 Define exclusion policy for C1/C2 grammar
R6-M1-S7 Define review queue for ambiguous or cross-level grammar
```

## Expected Artifact Later

```text
ulga/grammar/grammar_a1b2_coverage_targets.json
ulga/reports/grammar_a1b2_coverage_target_summary.json
```

## Gate PASS

```text
A1-B2 coverage target is explicit.
C1/C2 entries are not accidentally imported.
Ambiguous grammar has review status, not silent promotion.
```

---

# R6-M2 Grammar Node Expansion Batch Plan

## Purpose

Expand grammar_nodes in controlled batches, not one uncontrolled import.

## Batch Plan

```text
Batch 1: A1 / A1_PLUS core grammar
Batch 2: A2 / A2_PLUS grammar
Batch 3: B1 / B1_PLUS grammar
Batch 4: B2 grammar
Batch 5: cross-level cleanup and ambiguous review
```

## Small Tasks

```text
R6-M2-S1 Expand A1/A1_PLUS grammar nodes
R6-M2-S2 Expand A2/A2_PLUS grammar nodes
R6-M2-S3 Expand B1/B1_PLUS grammar nodes
R6-M2-S4 Expand B2 grammar nodes
R6-M2-S5 Add canonical labels and normalized ids
R6-M2-S6 Add CEFR / EGP evidence refs
R6-M2-S7 Add introduced_stage and expected recycle_stages
R6-M2-S8 Add blocked_before and blocked_after where needed
R6-M2-S9 Add example patterns placeholder refs
R6-M2-S10 Generate node expansion summary
```

## Expected Artifact Later

```text
ulga/grammar/grammar_nodes.json
ulga/reports/grammar_node_expansion_summary.json
```

## Gate PASS

```text
All grammar nodes use schema-compliant ids.
Every node has stage, category, evidence status, and review status.
No AI-only node is promoted as authority without review.
```

---

# R6-M3 Grammar Edge Expansion Batch Plan

## Purpose

Expand dependency edges for A1-B2 grammar nodes.

## Edge Types

```text
REQUIRES
PRECEDES
REINFORCES
CONTRASTS_WITH
CONFUSABLE_WITH
EXPANDS_TO
```

## Small Tasks

```text
R6-M3-S1 Add A1/A1_PLUS prerequisite edges
R6-M3-S2 Add A2/A2_PLUS prerequisite edges
R6-M3-S3 Add B1/B1_PLUS prerequisite edges
R6-M3-S4 Add B2 prerequisite edges
R6-M3-S5 Add PRECEDES edges for recommended order
R6-M3-S6 Add REINFORCES edges for spiral review
R6-M3-S7 Add CONTRASTS_WITH / CONFUSABLE_WITH edges for error diagnosis readiness
R6-M3-S8 Add edge evidence and confidence
R6-M3-S9 Add candidate_only edges for unresolved AI suggestions
R6-M3-S10 Generate edge expansion summary
```

## Expected Artifact Later

```text
ulga/grammar/grammar_edges.json
ulga/reports/grammar_edge_expansion_summary.json
```

## Gate PASS

```text
Every focus grammar has prerequisite coverage or explicit no_prerequisite justification.
No edge endpoint is missing.
No graph cycle is introduced.
```

---

# R6-M4 Stage Role Expansion Matrix

## Purpose

Assign each grammar node a role across A1-B2.

## Stage Role Values

```text
focus
recycle
preview
blocked
maintenance
expand
not_applicable
review
```

## Small Tasks

```text
R6-M4-S1 Generate initial role matrix from node stages and edges
R6-M4-S2 Mark focus stage for each grammar node
R6-M4-S3 Mark recycle stages for core grammar
R6-M4-S4 Mark preview-only stages where reading exposure is allowed
R6-M4-S5 Mark blocked stages before prerequisite readiness
R6-M4-S6 Mark maintenance stages for high-frequency old grammar
R6-M4-S7 Mark expand stages for advanced variants
R6-M4-S8 Generate gap / too-early / under-recycle report
```

## Expected Artifact Later

```text
ulga/grammar/grammar_coverage_matrix.json
ulga/reports/grammar_coverage_matrix_summary.json
```

## Gate PASS

```text
Every grammar node has a stage role across A1-B2.
No focus appears before required prerequisites.
Core grammar has recycle or maintenance coverage after focus.
```

---

# R6-M5 Grammar Order Table Full Expansion

## Purpose

Produce the full A1-B2 grammar order table from nodes, edges, and stage roles.

## Small Tasks

```text
R6-M5-S1 Run order generator over expanded nodes and edges
R6-M5-S2 Apply stage constraint filter
R6-M5-S3 Apply prerequisite topological sort
R6-M5-S4 Apply tie-breakers: CEFR band, frequency, child path, source evidence
R6-M5-S5 Add unlock_condition to each focus grammar row
R6-M5-S6 Add alignment_status to each row
R6-M5-S7 Add downstream_allowed flag for four-skill use
R6-M5-S8 Generate order conflict report
```

## Expected Artifact Later

```text
ulga/grammar/grammar_order_table.json
ulga/reports/grammar_order_table_summary.json
```

## Gate PASS

```text
Grammar order table is generated, not hand-only.
Every row explains prerequisites and unlock condition.
Conflicts are visible in report.
```

---

# R6-M6 CEFR / EGP Alignment Full Pass

## Purpose

Check every A1-B2 grammar node against CEFR / EGP evidence.

## Alignment Status

```text
MATCH
EARLY_BY_DESIGN
LATE_BY_DEPENDENCY
PREVIEW_ONLY
CONFLICT_REVIEW_REQUIRED
NOT_IN_AUTHORITY_SOURCE
```

## Small Tasks

```text
R6-M6-S1 Attach EGP evidence refs where available
R6-M6-S2 Attach CEFR band evidence where available
R6-M6-S3 Compare system_stage with authority level
R6-M6-S4 Mark MATCH cases
R6-M6-S5 Mark LATE_BY_DEPENDENCY cases
R6-M6-S6 Mark EARLY_BY_DESIGN cases only with explicit rationale
R6-M6-S7 Mark PREVIEW_ONLY cases
R6-M6-S8 Send conflicts to review queue
R6-M6-S9 Generate alignment summary by stage and status
```

## Expected Artifact Later

```text
ulga/grammar/grammar_cefr_egp_alignment.json
ulga/reports/grammar_cefr_egp_alignment_summary.json
```

## Gate PASS

```text
Every grammar node has alignment_status.
No silent mismatch with CEFR / EGP.
Every deviation has rationale or review requirement.
```

---

# R6-M7 Pattern / Chunk / Vocabulary / Theme Linkage Readiness Pass

## Purpose

Prepare grammar nodes for downstream four-skill generation by adding linkage readiness.

## Small Tasks

```text
R6-M7-S1 Check each focus grammar has at least one sentence pattern link or placeholder
R6-M7-S2 Check chunk policy readiness for common grammar nodes
R6-M7-S3 Check vocabulary policy readiness by CEFR band
R6-M7-S4 Check theme context readiness for early stages
R6-M7-S5 Mark missing links as BLOCKED_FOR_GENERATION but allowed in authority graph
R6-M7-S6 Generate linkage readiness report
```

## Expected Artifact Later

```text
ulga/reports/grammar_linkage_readiness_report.json
```

## Gate PASS

```text
Grammar authority can exist without full linkage.
But downstream generators cannot use grammar nodes missing required linkage.
Missing links are explicit, not silent.
```

---

# R6-M8 Validator Hardening for A1-B2 Scale

## Purpose

Harden validator rules for full A1-B2 use.

## Small Tasks

```text
R6-M8-S1 Validate grammar_id uniqueness at scale
R6-M8-S2 Validate edge endpoint existence
R6-M8-S3 Validate no dependency cycle
R6-M8-S4 Validate every focus grammar has next-step gate
R6-M8-S5 Validate no focus before prerequisite stage
R6-M8-S6 Validate no blocked grammar in generation-allowed policy
R6-M8-S7 Validate CEFR/EGP alignment completeness
R6-M8-S8 Validate coverage matrix completeness
R6-M8-S9 Validate order table completeness
R6-M8-S10 Validate linkage readiness flags
R6-M8-S11 Validate AI candidate entries remain candidate_only
```

## Expected Artifact Later

```text
ulga/validators/validate_grammar_skill_tree.py
ulga/reports/grammar_skill_tree_validation_report.json
```

## Gate PASS

```text
Validator catches structural, stage, alignment, and downstream-readiness errors.
Validation report can block generator use.
```

---

# R6-M9 Expansion QA Report

## Purpose

Create the official QA evidence for A1-B2 expansion.

## Small Tasks

```text
R6-M9-S1 Run grammar node validation
R6-M9-S2 Run grammar edge validation
R6-M9-S3 Run coverage matrix validation
R6-M9-S4 Run order table validation
R6-M9-S5 Run alignment validation
R6-M9-S6 Run linkage readiness validation
R6-M9-S7 Produce warning list and must-fix list
R6-M9-S8 Produce stage-level completeness summary
R6-M9-S9 Produce downstream-readiness summary
```

## Expected Artifact Later

```text
ulga/reports/grammar_skill_tree_a1b2_expansion_qa.json
docs/ulga/R6_GRAMMAR_SKILL_TREE_A1B2_EXPANSION_QA.md
```

## Gate PASS

```text
must_fix_count = 0
warnings are documented
stage coverage is measurable
next handoff is explicit
```

---

# R6-M10 Downstream Four-Skill Query Contract

## Purpose

Define how Reading / Listening / Speaking / Writing can use GrammarSkillTree safely.

## Query Types

```text
get_allowed_grammar_for_stage(stage)
get_blocked_grammar_for_stage(stage)
get_focus_grammar_for_stage(stage)
get_recycle_grammar_for_stage(stage)
get_preview_grammar_for_stage(stage)
get_prerequisites(grammar_id)
get_next_unlock_candidates(learner_mastery_snapshot)
validate_item_grammar_policy(item)
```

## Small Tasks

```text
R6-M10-S1 Define Reading query contract
R6-M10-S2 Define Listening query contract
R6-M10-S3 Define Speaking prompt query contract
R6-M10-S4 Define Writing prompt/query contract
R6-M10-S5 Define Assessment item query contract
R6-M10-S6 Define Error Tagging linkage contract
R6-M10-S7 Define no-learner-state-write rule for query contract
R6-M10-S8 Define generator block behavior when grammar policy fails
```

## Expected Artifact Later

```text
docs/ulga/R6_GRAMMAR_SKILL_TREE_FOUR_SKILL_QUERY_CONTRACT.md
ulga/contracts/grammar_skill_tree_query_contract.json
```

## Gate PASS

```text
Four-skill systems can query grammar policy.
Query contract is read-only.
No learner state is written by GrammarSkillTree queries.
```

---

# R6-M11 R6 Closeout and Handoff to Reading / Listening / Speaking / Writing

## Purpose

Close R6 and define the next safe system milestones.

## Small Tasks

```text
R6-M11-S1 Confirm all R6 artifacts exist
R6-M11-S2 Confirm validator PASS or PASS_WITH_WARNINGS with must_fix_count=0
R6-M11-S3 Confirm GrammarSkillTree is marked A1B2_USABLE_FOR_QUERY
R6-M11-S4 Confirm mass generation remains blocked until downstream generators have validators
R6-M11-S5 Define Reading handoff
R6-M11-S6 Define Listening handoff
R6-M11-S7 Define Speaking handoff
R6-M11-S8 Define Writing handoff
R6-M11-S9 Define Assessment / Error Tagging handoff
R6-M11-S10 Define next shortest task
```

## Closeout Status Values

```text
NOT_STARTED
IN_PROGRESS
PASS_WITH_WARNINGS
A1B2_USABLE_FOR_QUERY
BLOCKED_BY_MUST_FIX
```

## Gate PASS

```text
R6 closes only when GrammarSkillTree can be used as a read-only query/gate layer.
R6 does not authorize automatic learner progression or mass question generation by itself.
```

---

# R6 Distance Vector

```text
R6 total middle tasks = 12
R6 total small tasks = 108
R6 can start only after R5-M10 = CLOSED_PILOT_PASS
```

# R6 Output Definition

R6 complete output:

```text
GrammarSkillTree_A1B2_USABLE_FOR_QUERY
```

Meaning:

```text
- A1-B2 grammar policy can be queried by downstream systems
- grammar sequence is graph-derived and validator-checked
- CEFR / EGP alignment is explicit
- focus/recycle/preview/blocked coverage is explicit
- downstream generators can be blocked by grammar policy
```

Not meaning:

```text
- four-skill platform complete
- adaptive planner complete
- learner mastery state auto-write enabled
- Reading / Listening / Speaking / Writing generators complete
```

# Next Shortest Step After R6 Breakdown

Current upstream task remains:

```text
R4-M1_AuthoritySourceInventoryAndEvidenceContract_DesignScan
```

R6 trigger is not allowed until:

```text
R5-M10 close R5 pilot and expand = PASS
```

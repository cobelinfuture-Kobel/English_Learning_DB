# E4S-P6 Error Tagging Startup

## 1. Current State

Current Epic:

```text
E4S-ROOT_EnglishFourSkillSourceGroundedPracticeSystem
```

Current Phase:

```text
E4S-P6_ErrorTaggingAndWeakPointDiagnosis
```

Current Sub-task:

```text
E4S-P6-S0_ErrorTaggingPhaseStartup_PreflightAndBoundaryContract
```

Data Sources:

```text
- 重點任務排程.txt
- RAZ-AW-V1 Status Snapshot.txt
- 標籤化錯題分析.txt
```

External Permission:

```text
GitHub: APPROVED - read/write project files by API
Google Drive: APPROVED - read reference files/specs/datasets
```

Deliverable:

```text
docs/ulga/E4S_P6_ERROR_TAGGING_STARTUP.md
```

---

## 2. Core Execution

Phase 6 is started as the current E4S phase:

```text
E4S-P6_ErrorTaggingAndWeakPointDiagnosis
```

This supersedes the older ULGA/LPA meaning of Phase 6 as Recommendation Engine.

Phase 6 goal:

```text
Convert learner answer results into structured learning-error tags and weak-point records for later review and remediation.
```

Allowed in Phase 6:

```text
- question tagging
- answer record contract
- error tag contract
- weak-point summary contract
- remediation tag linkage
- source evidence trace
```

Blocked in P6-S0:

```text
- runtime implementation
- validator implementation
- UI / HTML
- adaptive learning path
- recommendation engine
- learner mastery scoring
- generated exercise promotion
```

P6-S0 only creates the startup and boundary contract.

Initial diagnostic chain:

```text
Question -> Question Tags -> Answer Record -> Error Tags -> Weak-point Summary -> Remediation Tags
```

First schema direction:

```text
question_id
source_type
level
question_type
skill_area
concept_tags
cognitive_skill
correct_answer
learner_answer
is_correct
error_type
error_detail
remediation_tag
source_evidence_ref
```

---

## 3. Gate and Distance Update

Gate Metrics:

```text
PASS - Phase 6 definition resolved to E4S-P6_ErrorTaggingAndWeakPointDiagnosis
PASS - Single sub-task scope locked
PASS - Runtime/code untouched
PASS - Recommendation Engine explicitly out of scope
PASS - Next step defined
```

Distance Vector:

```text
D_P6 = 8 sub-tasks left after P6-S0
E4S-P6-S0_ErrorTaggingPhaseStartup_PreflightAndBoundaryContract -> COMPLETED
E4S-P6 -> STARTED_IN_CONTRACT_MODE
ERROR_TAGGING_RUNTIME -> NOT_STARTED
WEAK_POINT_ENGINE -> NOT_STARTED
```

---

## 4. Next Shortest Step

NEXT_SHORT_STEP:

```text
E4S-P6-S1_ErrorTaggingTaxonomyContract_DesignScan
```

Unique next action:

```text
Create docs/ulga/E4S_P6_ERROR_TAGGING_TAXONOMY_CONTRACT.md
```

P6-S1 must define controlled values for:

```text
question_type
skill_area
concept_tags
cognitive_skill
error_type
error_detail
remediation_tag
```

P6-S1 must not implement runtime code, validators, generated data, UI, or adaptive logic.

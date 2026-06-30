# ULGA-S11 Reading / Dialogue Content Authority Design Scan

## 1. Preflight

Scope for this scan:

- design only
- no builder implementation
- no schema implementation
- no runtime mutation
- no graph, report, validator, test, or scheduler mutation
- no adaptive learner-state dependency

Files inspected before writing:

- `docs/ulga/ULGA_S10I_STATIC_CANDIDATE_QUERY_LAYER_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S10D_ANTIGRAVITY_PLANNER_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S10B_LEARNING_OPPORTUNITY_AUTHORITY_IMPLEMENTATION.md`
- `docs/ulga/ULGA_S11A_READING_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S11B_READING_STUB_AUTHORITY_IMPLEMENTATION.md`
- `docs/ulga/ULGA_S9X_LEARNER_EXPOSURE_EVIDENCE_DESIGN_SCAN.md`
- `ulga/graph/learning_opportunities.json`
- `ulga/graph/reading_stub_authority.json`
- `ulga/validators/validate_reading_stub_authority.py`

Preflight conclusions:

- S10 already has a static/offline query path and planner boundary.
- `learning_opportunities.json` is the current bridge concept between authority layers and future delivery.
- S11A and S11B already establish Reading as a content-facing layer, but only for Reading and only with stub coverage.
- Current learner-state and exposure evidence are not mature enough to be a required dependency for Content Authority selection.
- Minimal-change direction is to define a shared Content Authority contract for Reading and Dialogue without changing current runtime behavior.

## 2. Current Upstream State

Current authority stack relevant to S11:

```text
Vocabulary / Grammar / Chunk / Theme / Pattern Authority
-> Learning Opportunity Authority
-> Opportunity Ranking
-> Static Candidate Query Layer
-> Antigravity Planner boundary
-> Future Content Authority
```

Current grounded facts from inspected artifacts:

- Learning Opportunities already exist as first-class authority records.
- Static query is explicitly view-based and static-only.
- Planner is explicitly downstream of Opportunity Authority and must not become a content generator.
- Reading stub authority exists, but it is metadata-only and uses a temporary `1:1` opportunity-to-stub mapping.
- Dialogue authority does not yet exist as a first-class content authority artifact.

## 3. Problem Statement

ULGA currently knows how to identify teachable opportunities, but it does not yet have a first-class authority layer that says:

```text
Which concrete reading or dialogue asset can safely deliver this opportunity,
using authority-linked metadata,
without depending on adaptive runtime behavior?
```

Without this layer, content remains closer to plain text storage than queryable authority. That creates four practical risks:

- query results cannot distinguish approved content from raw text
- planner-facing delivery cannot explain why a reading or dialogue matches an opportunity
- generated content could bypass proper validation and enter downstream flows too early
- future Reading, Dialogue, Exercise, and Assessment layers would diverge in contract shape

## 4. Scope / Non-Scope

In scope for S11:

- define `Content Authority` as a future layer
- define `LearningOpportunity` as a bridge concept
- define Reading Authority contract
- define Dialogue Authority contract
- define shared content-item abstraction
- define future ULGA linkage edges
- define static query contract
- define validation contract
- define generation intake contract
- define static vs adaptive boundary

Out of scope for S11:

- implementing builders
- writing production reading passages
- writing production dialogue packs
- modifying existing graph JSON
- modifying existing reports, validators, tests, schemas, runtime files, API routes, scheduler jobs, or orchestrator behavior
- promoting adaptive runtime behavior
- making learner state a required input
- defining Assessment or Worksheet authority beyond future references

## 5. Content Authority Model

Content Authority is the layer that connects:

```text
ULGA / Candidate Query / Antigravity
-> Learning Opportunity
-> Reading / Dialogue / Exercise / Assessment
```

S11 focuses only on:

```text
Reading Authority
Dialogue Authority
```

Recommended authority position:

```text
Authority refs and opportunity metadata
-> Content Authority records
-> Static content query
-> Future planner delivery selection
```

Responsibilities:

- make content items queryable by level, theme, focus nodes, reinforcement nodes, grammar, pattern, and chunk metadata
- separate approved authority content from candidate, blocked, deprecated, and generated-but-unapproved content
- make content-to-opportunity matching explicit and explainable
- preserve static/offline safety

Non-responsibilities:

- deciding the next best opportunity
- mutating learner state
- performing adaptive personalization
- approving generated content automatically
- turning sequence order into prerequisite truth

## 6. Learning Opportunity Linkage

`LearningOpportunity` should remain the bridge concept between upstream authority refs and downstream content assets.

Design-level role:

- upstream layers define what should be taught
- `LearningOpportunity` packages that need into a content-addressable target
- Content Authority records define how that need can be delivered by Reading or Dialogue

Example future shape:

```json
{
  "id": "LO_A1_HOME_0001",
  "level": "A1",
  "theme": "Home",
  "focus_nodes": ["VN_kitchen", "GN_there_is", "SP_there_is_blank"],
  "reinforcement_nodes": ["VN_house", "VN_room"],
  "content_modes": ["reading", "dialogue"],
  "status": "candidate"
}
```

This is not a schema implementation. It is the future contract direction.

Recommended linkage rules:

- one opportunity may link to many content items
- one content item may support many opportunities
- first implementation can still allow a single primary `linked_opportunity` field for minimal change
- future expansion can add `linked_opportunities` or a separate match index when `1:N` becomes insufficient

## 7. Content Item Base Contract

Reading and Dialogue should share a base `content_item` abstraction.

Reason:

- both are content delivery objects downstream of the same authority stack
- both need common lifecycle, provenance, validation, and linkage metadata
- shared base fields reduce repeated logic and naming drift across builders, validators, query code, and dashboard summaries

Recommended shared base fields:

```json
{
  "content_id": "string",
  "content_type": "reading | dialogue",
  "title": "string",
  "level": "A1",
  "theme_refs": [],
  "linked_opportunity": "LO_A1_HOME_0001",
  "focus_vocabulary_refs": [],
  "reinforcement_vocabulary_refs": [],
  "grammar_refs": [],
  "pattern_refs": [],
  "chunk_refs": [],
  "dependency_refs": [],
  "source_type": "generated_validated | imported | manual_curated",
  "validation_status": "candidate | approved | blocked | deprecated",
  "validator_notes": []
}
```

Content-type-specific fields should remain separate:

- Reading adds text-length and reading-question metadata.
- Dialogue adds turn structure, function tags, and role-play support metadata.

## 8. Reading Authority Schema

Future `reading_authority.json` record:

```json
{
  "reading_id": "RA_A1_HOME_001",
  "title": "My House",
  "level": "A1",
  "theme_refs": ["THEME_HOME"],
  "linked_opportunity": "LO_A1_HOME_0001",
  "text": "...",
  "word_count": 50,
  "sentence_count": 6,
  "focus_vocabulary_refs": [],
  "reinforcement_vocabulary_refs": [],
  "grammar_refs": [],
  "pattern_refs": [],
  "chunk_refs": [],
  "dependency_refs": [],
  "question_type_support": [],
  "source_type": "generated_validated | imported | manual_curated",
  "validation_status": "candidate | approved | blocked | deprecated",
  "validator_notes": []
}
```

Recommended S11/S12 mandatory fields:

- `reading_id`
- `title`
- `level`
- `theme_refs`
- `linked_opportunity`
- `text`
- `word_count`
- `sentence_count`
- `focus_vocabulary_refs`
- `grammar_refs`
- `pattern_refs`
- `source_type`
- `validation_status`

Recommended future-but-not-required-in-S11 fields:

- `reinforcement_vocabulary_refs`
- `chunk_refs`
- `dependency_refs`
- `question_type_support`
- richer provenance fields such as generator version, import source, reviewer id, and approval timestamp

Design notes:

- `text` is required for real Reading Authority, but stub records may continue to exist outside this contract as planner-validation artifacts.
- `validation_status` must remain content-lifecycle metadata, not planner readiness.
- `dependency_refs` should refer to prerequisite concepts or readiness overlays, not content ordering.

## 9. Dialogue Authority Schema

Future `dialogue_authority.json` record:

```json
{
  "dialogue_id": "DA_A1_FOOD_001",
  "title": "At a Restaurant",
  "level": "A1",
  "theme_refs": ["THEME_FOOD"],
  "linked_opportunity": "LO_A1_FOOD_0001",
  "turns": [
    {
      "speaker": "A",
      "text": "What would you like?"
    },
    {
      "speaker": "B",
      "text": "I would like rice."
    }
  ],
  "turn_count": 2,
  "focus_vocabulary_refs": [],
  "reinforcement_vocabulary_refs": [],
  "grammar_refs": [],
  "pattern_refs": [],
  "chunk_refs": [],
  "function_tags": ["request", "answer"],
  "speaking_role_support": true,
  "source_type": "generated_validated | imported | manual_curated",
  "validation_status": "candidate | approved | blocked | deprecated",
  "validator_notes": []
}
```

Recommended S11/S12 mandatory fields:

- `dialogue_id`
- `title`
- `level`
- `theme_refs`
- `linked_opportunity`
- `turns`
- `turn_count`
- `focus_vocabulary_refs`
- `grammar_refs`
- `pattern_refs`
- `function_tags`
- `speaking_role_support`
- `source_type`
- `validation_status`

Recommended future-but-not-required-in-S11 fields:

- `reinforcement_vocabulary_refs`
- `chunk_refs`
- speaker persona metadata
- role constraints such as `teacher_student`, `peer_peer`, `service_customer`
- timing and audio performance metadata

Dialogue-specific design notes:

- `turn_count` should be materialized, not recomputed at query time, for deterministic audits and summaries.
- `function_tags` are authority metadata, not free-form runtime labels.
- `speaking_role_support` must not imply speaking evaluation is already implemented.

## 10. ULGA Node / Edge Contract

Future edge concepts:

```text
CONTENT_TARGETS_NODE
CONTENT_REINFORCES_NODE
CONTENT_USES_PATTERN
CONTENT_USES_GRAMMAR
CONTENT_USES_CHUNK
CONTENT_BELONGS_TO_THEME
CONTENT_SUPPORTS_OPPORTUNITY
CONTENT_PRECEDES_CONTENT
```

Recommended meanings:

- `CONTENT_TARGETS_NODE`: content explicitly teaches a focus node
- `CONTENT_REINFORCES_NODE`: content revisits a previously introduced node
- `CONTENT_USES_PATTERN`: content materially uses a sentence pattern
- `CONTENT_USES_GRAMMAR`: content materially uses a grammar point
- `CONTENT_USES_CHUNK`: content materially uses a chunk
- `CONTENT_BELONGS_TO_THEME`: content belongs to a theme authority scope
- `CONTENT_SUPPORTS_OPPORTUNITY`: content can deliver a specific opportunity
- `CONTENT_PRECEDES_CONTENT`: content is usually presented earlier in a curriculum sequence

Critical clarification:

```text
CONTENT_PRECEDES_CONTENT != REQUIRES
```

`CONTENT_PRECEDES_CONTENT` is sequencing guidance. It must not be treated as prerequisite truth. Otherwise the system would incorrectly convert recommended order into hard dependency gating.

## 11. Query Contract

Future static query example:

```json
{
  "level": "A1",
  "theme": "Home",
  "focus_nodes": ["VN_kitchen"],
  "required_patterns": ["SP_there_is_blank"],
  "content_mode": "reading",
  "limit": 5
}
```

Expected result:

```json
{
  "query_status": "ok",
  "content_candidates": [
    {
      "content_id": "RA_A1_HOME_001",
      "content_type": "reading",
      "match_score": 0.91,
      "matched_focus_nodes": [],
      "matched_reinforcement_nodes": [],
      "warnings": []
    }
  ]
}
```

Static query contract rules:

- query must operate on approved or explicitly allowed candidate content records, not raw generated text
- query must preserve static/offline behavior
- query must not require learner-specific mastery, exposure, or live dashboard state
- query must allow empty results without fallback mutation
- query must surface warnings instead of silently widening constraints

Recommended request fields:

- `level`
- `theme`
- `focus_nodes`
- `reinforcement_nodes`
- `required_patterns`
- `required_grammar`
- `content_mode`
- `limit`

Recommended response fields:

- `query_status`
- `content_candidates`
- `warnings`
- `query_metadata`

Recommended scoring dimensions:

- level match
- theme match
- focus-node overlap
- reinforcement-node overlap
- pattern match
- grammar match
- content-status eligibility

Out-of-scope query behavior:

- adaptive personalization
- live difficulty retuning from learner state
- automatic generation when no static match exists

If no match exists, the safe response is:

```text
empty candidate list + warning
```

not:

```text
generate content immediately
```

## 12. Validation Contract

Reading validators needed later:

- schema validator
- level validator
- vocabulary validator
- grammar validator
- pattern validator
- theme validator
- sentence length validator
- word count validator
- content safety validator
- duplication validator

Dialogue validators needed later:

- schema validator
- turn structure validator
- speaker alternation validator
- level validator
- vocabulary validator
- grammar validator
- pattern validator
- function tag validator
- dialogue naturalness validator
- content safety validator

Recommended validator behavior:

- fail closed on malformed schema
- fail closed on unresolved authority refs for `approved` items
- allow `candidate` items to carry non-fatal notes only when the record remains non-approved
- keep duplicate detection idempotent so repeated intake does not create duplicate approved items
- report partial validation outcomes explicitly instead of silently coercing status

## 13. Generation Intake Contract

Required intake pipeline:

```text
Generator Output
-> Schema Check
-> Authority Reference Resolution
-> Level / Grammar / Vocabulary / Pattern Validation
-> Theme Validation
-> Duplicate Check
-> Candidate Status
-> Manual or QA Approval
-> Approved Authority Item
```

Mandatory rules:

- generated content must never go directly to `approved`
- intake must be idempotent for repeated submissions of the same artifact
- timeout, API failure, or exchange-like malformed upstream response must leave the item unapproved
- partial validator failure must move the item to `blocked` or keep it in `candidate`, not silently downgrade checks
- imported and manual-curated content should use the same approval gate, even if they skip generator provenance

Minimal-change recommendation:

- keep a single `source_type` field now
- add richer provenance and retry metadata later only when implementation starts

## 14. Static vs Adaptive Boundary

S11 boundary statement:

- S11 supports static/offline content authority design.
- S11 must not depend on live adaptive learner state.
- Learner State and Antigravity can consume this layer later.
- Current output must remain safe for static candidate query workflows.

Operational implication:

- Content Authority may be queried by static filters and authority refs now.
- Adaptive selection may consume this layer later, but adaptive state must stay outside the authority truth of the content record itself.

## 15. Risks

Primary risks:

- content difficulty drift
- weak metadata
- generated text passing schema but failing pedagogy
- dialogue unnaturalness
- overfitting to CEFR only
- missing dependency graph
- treating content order as dependency
- no assessment feedback loop yet

Real-environment risks to preserve for later implementation:

- generator API failure could leave partially written intake records unless writes are transactional
- validator timeout could block approval queues or produce stale candidate status
- empty query results could trigger accidental fallback generation if the contract is not explicit
- repeated intake execution could create duplicate candidate records without stable fingerprints
- process restart during intake or approval could leave orphaned candidate states without resumable checkpoints
- malformed upstream content responses could pass schema shape but still contain unusable pedagogy

Integration risks with existing system:

- config drift if future content status enums diverge from dashboard or report expectations
- runtime-status ambiguity if planner-ready stub content is confused with approved learner-facing content
- scheduler/orchestrator conflicts if future content builders auto-run before validator or approval gates
- query/API divergence if Reading and Dialogue implement different filter names for the same authority concept

## 16. Recommended Roadmap

Recommended next tasks:

```text
ULGA-S11A_ReadingDialogueContentAuthority_SchemaImplementation
ULGA-S11B_ReadingAuthority_SeedSetDesign
ULGA-S11C_DialogueAuthority_SeedSetDesign
ULGA-S11D_ContentAuthority_QueryContract
ULGA-S11E_ContentAuthority_ValidationPlan
```

Execution order recommendation:

1. schema implementation
2. reading seed-set design
3. dialogue seed-set design
4. query contract implementation
5. validation plan and validator implementation

Do not start these tasks in S11.

## 17. Acceptance Criteria

This design scan is complete when it:

- clearly defines Reading Authority and Dialogue Authority
- defines Learning Opportunity as a bridge concept
- separates content storage from content authority
- defines future schemas without implementing them
- defines ULGA linkage edges
- defines query contract
- defines validation contract
- preserves static/offline safety
- does not modify runtime behavior
- does not generate production content
- ends with a clear recommended next task

Recommended next task:

```text
ULGA-S11A_ReadingDialogueContentAuthority_SchemaImplementation
```

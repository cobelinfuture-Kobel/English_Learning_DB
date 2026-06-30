# ULGA-S11A Reading Authority Design Scan

## 1. Scope

S11A defines the design boundary for a future **Reading Authority** as a content authority layer for ULGA.

This scan is design-only. It does not implement builders, validators, schemas, graph outputs, reports, tests, or planner behavior.

S11A scope:

- position Reading Authority inside the ULGA content-authority stack
- define the relationship between Learning Opportunities and Reading Assets
- draft `reading_authority.json` and `reading_query_contract.json`
- define reading difficulty, matching, lifecycle, stub strategy, and QA/audit metrics
- identify integration risks with Antigravity Planner, Dialogue Authority, Assessment Authority, and Learner State

S11A out of scope:

- generating reading passages
- writing `reading_authority.json`
- writing `reading_stub_authority.json`
- modifying `learning_opportunities.json` or `ranked_learning_opportunities.json`
- implementing planner selection
- mutating learner state
- changing existing graph, schema, builders, validators, reports, or tests

Minimal-change position:

- treat Reading Authority as a separate read-only content catalog derived from existing authority refs
- use `learning_opportunities.json` and future planner/session outputs as demand signals
- do not make Reading the source of truth for Opportunity, Ranking, Planner, Dialogue, or Assessment
- allow stub readings only as explicit planner-validation placeholders, not approved content

## 2. Current Inputs Reviewed

Design and implementation documents reviewed:

- `docs/ulga/ULGA_S10A_CANDIDATE_RANKING_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S10B_LEARNING_OPPORTUNITY_AUTHORITY_IMPLEMENTATION.md`
- `docs/ulga/ULGA_S10B1_LEARNING_OPPORTUNITY_THEME_SPECIFICITY_FIX.md`
- `docs/ulga/ULGA_S10C_OPPORTUNITY_RANKING_ENGINE_IMPLEMENTATION.md`
- `docs/ulga/ULGA_S10D_ANTIGRAVITY_PLANNER_DESIGN_SCAN.md`

Runtime and authority artifacts reviewed:

- `ulga/graph/learning_opportunities.json`
- `ulga/graph/ranked_learning_opportunities.json`
- `ulga/graph/dependency_graph.json`
- `ulga/graph/theme_spiral_graph.json`
- `ulga/graph/sentence_patterns.json`
- `ulga/graph/vocabulary_nodes.json`
- `ulga/graph/theme_nodes.json`

Report artifacts reviewed:

- `ulga/reports/learning_opportunity_summary.json`
- `ulga/reports/opportunity_ranking_summary.json`
- `ulga/reports/theme_spiral_graph_summary.json`
- `ulga/reports/learner_state_guardrail_summary.json`

Key facts from current inputs:

- S10B currently emits 1344 learning opportunities and passes validation.
- All 1344 opportunities now have specific theme refs after S10B1.
- Theme source is concentrated: 17 opportunities use `pattern_theme_ref`, 1327 use `vocabulary_theme`.
- Dependency status is mostly ready: 1337 `ready`, 7 `unknown`.
- S10C ranks all 1344 opportunities and passes validation.
- S10C top-ranked examples have `reinforcement_score: 0.0`, so Reading Authority must not infer reinforcement coverage from rank alone.
- Theme Spiral is non-gating: 12 `SPIRAL_TO` edges, 0 gate-eligible edges, and 8 stage-gap review cases.
- Learner State guardrails are active, but the learner-state sample is small: 9 evaluated records and 7 guardrail-modified records.

## 3. Reading Authority Position

Reading Authority is a **Content Authority Layer**.

Recommended authority position:

```text
Learning Opportunity Authority
+ Opportunity Ranking Engine
+ Antigravity Planner
+ Reading Authority
+ Future Dialogue Authority
+ Future Assessment Authority
```

Reading Authority answers:

```text
Which approved or draft reading assets can safely deliver this planned learning opportunity?
```

Reading Authority does not answer:

```text
Which opportunity should the learner study next?
```

That decision belongs to Opportunity Ranking and Antigravity Planner.

Responsibilities:

- catalog reading assets
- expose level, theme, grammar, pattern, vocabulary, dependency, and difficulty metadata
- make reading-to-opportunity matching explainable
- separate approved content from generated/draft/stub content
- report coverage gaps and orphaned records

Non-responsibilities:

- ranking learning opportunities
- creating learner-specific plans
- mutating learner state
- generating dialogue or assessment
- promoting Theme Spiral edges into gates
- silently approving generated content

## 4. Reading-Opportunity Relationship

Recommended model: `N:N` with explicit match records or link metadata.

Why not `1:1`:

- one opportunity may need multiple readings at different lengths, tones, or difficulty profiles
- a single passage may reinforce several vocabulary, grammar, pattern, or theme targets

Why not strict `1:N` or `N:1`:

- fixed direction would make either Reading or Opportunity the owner of the relationship
- current ULGA already separates teachable opportunity from delivery format

Recommended semantics:

- `Opportunity` is the teachable need.
- `Reading Asset` is a content delivery object.
- A reading may support multiple opportunities.
- An opportunity may match multiple readings.
- Match quality should be computed from shared authority refs, not from title or free text.

Draft relation shape:

```json
{
  "reading_id": "RA_A1_HOME_001",
  "opportunity_id": "LO_A1_000001",
  "match_score": 0.86,
  "match_reasons": [
    "level_match",
    "theme_match",
    "pattern_match",
    "vocabulary_overlap"
  ],
  "match_status": "candidate|approved|rejected",
  "source": "ReadingAuthority"
}
```

Minimal-change recommendation:

- In S11B, store direct `linked_opportunities` inside reading records first.
- Add a separate match index only if the link list becomes too large or needs independent audit history.

## 5. Reading Schema Draft

Future `reading_authority.json` draft:

```json
{
  "reading_id": "RA_A1_HOME_001",
  "title": "",
  "level": "A1",
  "theme_refs": [],
  "linked_opportunities": [],
  "focus_vocabulary": [],
  "focus_grammar": [],
  "focus_patterns": [],
  "dependency_refs": [],
  "estimated_word_count": 80,
  "difficulty_profile": {
    "cefr": "A1",
    "vocabulary_load": 0.0,
    "grammar_load": 0.0,
    "pattern_load": 0.0,
    "word_count_band": "short",
    "theme_complexity": 0.0
  },
  "content_status": "stub|draft|reviewed|approved|retired",
  "source": "ReadingAuthority"
}
```

Required fields in V1:

- `reading_id`
- `title`
- `level`
- `theme_refs`
- `linked_opportunities`
- `focus_vocabulary`
- `focus_grammar`
- `focus_patterns`
- `estimated_word_count`
- `difficulty_profile`
- `content_status`
- `source`

Validation expectations:

- `reading_id` is unique and stable.
- `level` uses the existing CEFR bands.
- `theme_refs`, `focus_vocabulary`, `focus_grammar`, and `focus_patterns` must resolve to mounted authority refs when non-empty.
- `linked_opportunities` must resolve to `learning_opportunities.json` when non-empty.
- `approved` readings must not contain unresolved authority refs.
- `stub` readings may contain partial fields but must be excluded from learner-facing delivery unless planner policy explicitly allows stubs for dry-run validation.

## 6. Difficulty Model

Reading Difficulty Authority should be internal to Reading Authority in V1, not a separate graph authority.

Recommended difficulty dimensions:

- `CEFR`
- `Vocabulary`
- `Grammar`
- `Pattern`
- `Word Count`
- `Theme Complexity`

Important rule:

- CEFR is not enough.

Reason:

- two A1 readings may differ sharply if one uses many low-frequency words, multiple grammar targets, long sentences, or unfamiliar themes
- S10C already shows high-level ranking is global; Reading must provide local content difficulty to avoid planner/content mismatch

Draft scoring:

```json
{
  "cefr": "A1",
  "vocabulary_load": 0.25,
  "grammar_load": 0.20,
  "pattern_load": 0.30,
  "word_count_band": "short",
  "theme_complexity": 0.15,
  "difficulty_score": 0.24
}
```

V1 guidance:

- A1: usually 40-120 words
- A2: usually 80-180 words
- B1: usually 150-350 words
- B2+: longer ranges require stronger review and assessment support

These ranges are policy hints, not schema gates.

## 7. Query Contract

Future `reading_query_contract.json` draft:

```json
{
  "level": "A1",
  "theme": "Home",
  "grammar": [
    "there_is"
  ],
  "pattern": [
    "There is ___."
  ]
}
```

Recommended normalized request shape:

```json
{
  "level": "A1",
  "theme_refs": [
    "theme:a1_homes_and_neighborhoods"
  ],
  "grammar_refs": [
    "grammar:GRAMMAR_NODE_001211"
  ],
  "pattern_refs": [
    "pattern:PATTERN_NODE_000014"
  ],
  "vocabulary_refs": [],
  "opportunity_id": "LO_A1_000001",
  "content_status_allowed": [
    "approved",
    "reviewed"
  ],
  "limit": 10
}
```

Expected response shape:

```json
{
  "query_status": "PASS|PASS_WITH_WARNINGS|BLOCKED",
  "matched_readings": [
    {
      "reading_id": "RA_A1_HOME_001",
      "match_score": 0.86,
      "match_reasons": [
        "level_match",
        "theme_match",
        "grammar_match",
        "pattern_match"
      ]
    }
  ],
  "warnings": []
}
```

Query safety rules:

- empty result is valid and must not trigger generated content silently
- invalid authority refs should return `BLOCKED`
- stubs should be excluded unless `content_status_allowed` explicitly includes `stub`
- results must be deterministic for the same inputs and same reading catalog

## 8. Match Strategy

Opportunity-to-Reading match signals:

- `theme_match`
- `grammar_match`
- `pattern_match`
- `vocabulary_overlap`
- `difficulty_match`

Recommended V1 formula:

```text
reading_match_score =
0.25 * theme_match
+ 0.20 * grammar_match
+ 0.20 * pattern_match
+ 0.20 * vocabulary_overlap
+ 0.15 * difficulty_match
```

Signal rules:

- `theme_match`: exact theme ref match preferred; Theme Spiral may provide weak continuity but never a gate
- `grammar_match`: direct focus grammar match or required grammar coverage
- `pattern_match`: direct focus pattern match
- `vocabulary_overlap`: overlap between reading focus vocabulary and opportunity focus vocabulary
- `difficulty_match`: reading level and difficulty profile fit planner/session constraints

Tie-break order:

1. higher `content_status` quality: `approved`, `reviewed`, `draft`, `stub`
2. higher `reading_match_score`
3. closer difficulty score
4. lower unresolved-ref count
5. deterministic `reading_id`

Hard blocks:

- missing required authority refs
- reading level above planner ceiling
- `content_status = retired`
- unresolved linked opportunity when matching by opportunity id
- dependency refs not ready when planner policy disallows unknown dependency
- reading has no usable text in learner-facing mode

## 9. Lifecycle Model

Recommended lifecycle:

```text
stub -> draft -> reviewed -> approved -> retired
```

Status semantics:

- `stub`: placeholder for coverage planning and contract validation only
- `draft`: generated or authored content that has not passed review
- `reviewed`: content passed structural review but may not be final authority-approved
- `approved`: learner-facing content
- `retired`: preserved for audit but excluded from matching

Recommended flow:

```text
Generator -> Human Review -> Authority
```

Rules:

- generator output may create `draft` but not `approved`
- human review may promote `draft` to `reviewed`
- authority validation may promote `reviewed` to `approved`
- `retired` readings must remain queryable by audit tools but excluded from learner-facing selection

## 10. Stub Authority Analysis

Future `reading_stub_authority.json` is useful, but only if it is clearly separated from approved readings.

Recommended position:

```text
Planner Validation Layer
```

Use cases:

- verify planner can request Reading Authority fields before real content exists
- measure opportunity coverage gaps
- validate query contract behavior
- support dry-run Antigravity Planner sessions

Risks:

- stubs may leak into learner-facing sessions
- downstream Dialogue or Assessment may treat placeholders as real content
- coverage metrics may look healthy even when no approved reading exists

Decision:

- S11B may implement Reading Stub Authority before full Reading content if S10E Planner needs a content-contract target.
- Stub records must use `content_status: "stub"` and must be excluded by default from learner-facing query results.
- QA must report `stub_ratio` separately from `approved_ratio`.

## 11. Antigravity Integration

Planner should call Reading Authority after it selects opportunities or session blocks.

Recommended flow:

```text
Session -> Opportunity -> Reading
```

Planner responsibilities:

- select opportunity ids
- pass level, theme, grammar, pattern, vocabulary, and block role hints
- decide whether empty reading matches block the session or produce a partial plan

Reading Authority responsibilities:

- return matching readings and match explanations
- report no-match cases explicitly
- never generate unapproved content silently

Important boundary:

```text
Session -> LLM direct generation
```

This path should be blocked for learner-facing delivery unless future policy explicitly allows generated drafts and review.

Integration risks:

- planner may expect content for every selected opportunity while Reading Authority has sparse coverage
- top-ranked opportunities may cluster around themes without available readings
- 7 current opportunities have unknown dependency and should not receive approved reading delivery when policy disallows unknown dependency

## 12. Dialogue Integration

Reading and Dialogue should share:

- `theme`
- `grammar`
- `pattern`
- `vocabulary`

Recommended relationship:

```text
Reading -> Dialogue
```

Meaning:

- a reading can seed dialogue practice
- a dialogue can reinforce the same opportunity refs
- both should reference the same authority ids, not copy free-text labels

Risks:

- Dialogue may drift from the reading focus if it uses theme only
- Dialogue may introduce new grammar or vocabulary that Reading did not prepare
- Reading text may be too static for spoken interaction

Mitigations:

- require shared focus refs for generated dialogue
- audit reading-dialogue overlap
- keep Dialogue Authority independent so it can reject a reading as unsuitable for dialogue

## 13. Assessment Integration

Recommended relationship:

```text
Reading -> Assessment
```

Assessment should check learner state through evidence events, not through Reading Authority directly.

Integration boundary:

- Reading provides content and focus refs.
- Assessment generates checks aligned to those refs.
- Learner State consumes assessment evidence later.
- Reading must not write learner-state updates.

Recommended assessment hooks:

- comprehension question refs
- target vocabulary checks
- grammar/pattern recognition checks
- short production prompt

Risks:

- assessment may test material not present in the reading
- learner-state evidence may over-credit passive exposure
- generated questions may use vocabulary above the reading level

Mitigations:

- require assessment-to-reading focus overlap
- use learner-state guardrails for passive exposure
- validate assessment vocabulary/grammar against Reading difficulty profile

## 14. QA / Audit Plan

Required Reading Authority metrics:

- `reading_count`
- `reading_level_distribution`
- `theme_distribution`
- `opportunity_coverage`
- `reading_match_rate`
- `planner_delivery_rate`
- `approved_ratio`
- `stub_ratio`
- `orphan_reading_count`
- `orphan_opportunity_count`

Additional recommended metrics:

- `unresolved_authority_ref_count`
- `retired_reading_count`
- `difficulty_distribution`
- `word_count_distribution`
- `duplicate_reading_count`
- `theme_source_distribution`
- `match_score_distribution`
- `empty_query_result_count`
- `stub_leakage_count`

Audit expectations:

- approved readings must have complete authority refs
- orphan readings are allowed only with explicit reason
- orphan opportunities must be visible as content coverage gaps
- repeated query execution must produce stable ordering
- process restart must not change match results for unchanged artifacts
- empty reading database must return controlled `PASS_WITH_WARNINGS` or `BLOCKED`, not generated filler

## 15. Risks and Mitigations

### Reading becomes static database

Risk:

- readings exist as isolated passages and do not help planner/session delivery.

Mitigation:

- require linked opportunities and authority refs
- audit `opportunity_coverage` and orphan counts

### Reading not linked to opportunities

Risk:

- planner cannot map selected opportunities to usable content.

Mitigation:

- make `linked_opportunities` required, or allow explicit no-link status only for draft/stub records

### Reading difficulty drift

Risk:

- CEFR label says A1 but vocabulary, grammar, sentence length, or theme complexity behaves like a higher level.

Mitigation:

- use multi-factor difficulty profile and audit word count, vocabulary load, grammar load, and pattern load

### Reading duplicates

Risk:

- generated or manually added readings may repeat the same text or same authority coverage.

Mitigation:

- add duplicate detection by title, normalized text hash, focus refs, and opportunity refs in S11B/S11C

### Planner cannot find content

Risk:

- Antigravity Planner selects valid opportunities but Reading Authority has no approved reading.

Mitigation:

- return explicit no-match reports
- separate `stub_ratio` from `approved_ratio`
- let planner emit partial plans or content-gap warnings

### Reading authority too dependent on generator

Risk:

- generated drafts become treated as approved content.

Mitigation:

- lifecycle gate: generator may create `draft` only
- approved status requires validation and review

### Reading authority too dependent on human review

Risk:

- content coverage stalls because every coverage placeholder waits for manual authoring.

Mitigation:

- allow stubs and drafts for planning/audit, but block learner-facing delivery until reviewed/approved

### Real environment risks

`API failure / timeout`

- future content generation or review APIs may fail.
- mitigation: Reading Authority V1 should use local artifacts; future API calls need timeouts, retry policy, and fail-closed status.

`empty data`

- no readings may exist for early S11B.
- mitigation: return empty catalog metrics and controlled blocked/warning status.

`duplicate execution`

- repeated builders must not duplicate reading ids or links.
- mitigation: stable IDs and deterministic generation from source refs.

`process restart`

- restarted runtime must not change matching order.
- mitigation: deterministic tie-breaks and no hidden in-memory counters.

`abnormal authority response`

- malformed opportunity refs, missing theme ids, null difficulty fields, or unknown dependencies can corrupt matching.
- mitigation: validator hard blocks approved records with unresolved required refs and reports all no-match causes.

## 16. Recommended Next Tasks

1. `S11B_ReadingStubAuthority_Implementation`

   Minimal first pass:

   - create stub reading records from a small selected subset of opportunities
   - write explicit `content_status: "stub"`
   - include level, theme refs, focus vocabulary, focus grammar, focus pattern, estimated word count, and linked opportunity ids
   - add validator and QA report
   - ensure default learner-facing query excludes stubs

2. `S11C_ReadingAuthority_QA_Audit`

   Validate unresolved refs, duplicate readings, orphan opportunities, match determinism, stub leakage, difficulty profile completeness, and approved/stub ratio.

3. Alternative next track: `S10E_AntigravityPlanner_Implementation`

   Use this first if the priority is planner selection mechanics before content-authority implementation. Planner can initially emit content-authority hints and record Reading gaps without requiring real readings.

Recommended next task:

```text
S11B_ReadingStubAuthority_Implementation
```

Reason:

- S10D already defines planner boundaries, and Reading Authority now has a clear stub-safe contract target.
- Stub Authority gives S10E a concrete content-contract surface without pretending approved reading content exists.

## 17. Final Verdict

S11A is ready to proceed.

Reasons:

- S10B/S10C provide stable opportunity and ranking inputs for Reading matching.
- S10D already defines the planner boundary and identifies Reading as a future content authority.
- Reading can be added as a read-only content authority without mutating existing graph truth.
- A stub-first implementation can validate planner/content contracts while avoiding unreviewed learner-facing content.

Controlled warnings:

- no approved reading catalog exists yet
- theme source quality is concentrated in vocabulary-derived themes
- reinforcement evidence is sparse in current ranked examples
- 7 opportunities have unknown dependency
- learner-state coverage remains small, so Reading should not claim learner-specific mastery effects

```text
S11A_STATUS: DESIGN_READY
```

## Closeout Summary

Files Created:

- `docs/ulga/ULGA_S11A_READING_AUTHORITY_DESIGN_SCAN.md`

Files Modified:

- None

Inputs Reviewed:

- `docs/ulga/ULGA_S10A_CANDIDATE_RANKING_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S10B_LEARNING_OPPORTUNITY_AUTHORITY_IMPLEMENTATION.md`
- `docs/ulga/ULGA_S10B1_LEARNING_OPPORTUNITY_THEME_SPECIFICITY_FIX.md`
- `docs/ulga/ULGA_S10C_OPPORTUNITY_RANKING_ENGINE_IMPLEMENTATION.md`
- `docs/ulga/ULGA_S10D_ANTIGRAVITY_PLANNER_DESIGN_SCAN.md`
- `ulga/graph/learning_opportunities.json`
- `ulga/graph/ranked_learning_opportunities.json`
- `ulga/graph/dependency_graph.json`
- `ulga/graph/theme_spiral_graph.json`
- `ulga/graph/sentence_patterns.json`
- `ulga/graph/vocabulary_nodes.json`
- `ulga/graph/theme_nodes.json`
- `ulga/reports/learning_opportunity_summary.json`
- `ulga/reports/opportunity_ranking_summary.json`
- `ulga/reports/theme_spiral_graph_summary.json`
- `ulga/reports/learner_state_guardrail_summary.json`

Key Design Decisions:

- Reading Authority is a content authority, not a ranking or planner authority.
- Reading-to-Opportunity should be `N:N`.
- Stub readings are useful only when excluded from learner-facing delivery by default.
- CEFR alone is insufficient for reading difficulty.
- Query and match behavior must be deterministic and audit-friendly.

Reading-Opportunity Mapping Decision:

- Use `N:N` with `linked_opportunities` in V1.
- Add separate match records later only if link audit history or scale requires it.

Stub Authority Decision:

- Implementing `reading_stub_authority.json` is acceptable as a planner-validation layer.
- Stubs must use `content_status: "stub"` and count separately from approved readings.

Risks Found:

- no approved reading database currently exists
- planner may select opportunities with no reading coverage
- generated drafts could leak into learner-facing content
- reading difficulty may drift beyond CEFR labels
- current opportunity themes are specific but mostly vocabulary-derived
- unknown dependency opportunities need hard-block handling in strict delivery mode

Final Verdict:

```text
S11A_STATUS: DESIGN_READY
```

Recommended Next Task:

```text
S11B_ReadingStubAuthority_Implementation
```

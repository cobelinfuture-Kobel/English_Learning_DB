# ULGA-S8B Theme Spiral Authority Design Scan

## Executive Summary

Theme Spiral Authority should define how a topic is revisited across CEFR bands with broader vocabulary, richer grammar, more complex chunks, and more demanding sentence patterns. It is a curriculum sequencing and coverage authority, not a prerequisite authority.

Current ULGA already has usable spiral evidence:

- `themes/theme_catalog.json`: `25` mounted theme concepts.
- `themes/theme_vocab_mapping.json`: `25` theme mapping records with `prev_theme_id`, `next_theme_id`, topic scope, allowed CEFR levels, frequency bands, and active vocabulary counts.
- `ulga/graph/theme_nodes.json`: `25` mounted ThemeNodes.
- `ulga/graph/vocabulary_theme_edges.refined.json`: `19,557` refined `belongs_to` edges over `9,065` vocabulary nodes.
- `ulga/graph/sentence_patterns.json`: `1,482` SentencePatternNodes, but only `17` have explicit theme refs.
- `chunk_profile/json/chunks_generator_safe.json`: `3,522` safe chunks, but `3,077` carry only `General` theme hints.

Main design conclusion:

```text
SPIRAL_TO is not REQUIRES.
Theme Spiral can guide recommendation, curriculum sequencing, coverage planning, and review selection.
It must not block a learner unless a separate Dependency Authority REQUIRES edge exists.
```

Recommendation: **GO for Theme Spiral contract work, NO-GO for hard gating or dense cross-authority edge generation.**

## Current ULGA State

### Evidence Inspected

- `docs/ulga/ULGA_S8A_DEPENDENCY_AUTHORITY_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S7E_PATTERN_THEME_LINKAGE_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S7C_PATTERN_VOCABULARY_LINKAGE_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S5D_VOCABULARY_THEME_LAYER_DESIGN_SCAN.md`
- `docs/ulga/ULGA_S5F_VOCABULARY_THEME_LAYER_QA_AUDIT.md`
- `docs/ulga/ulga_roadmap.md`
- `ulga/schema/ulga_node_schema.json`
- `ulga/schema/ulga_edge_schema.json`
- `ulga/graph/theme_nodes.json`
- `ulga/graph/vocabulary_theme_edges.refined.json`
- `ulga/graph/sentence_patterns.json`
- `ulga/graph/ulga_sentence_pattern_edges.json`
- `ulga/graph/pattern_vocabulary_constraints.json`
- `ulga/graph/chunk_nodes.json`
- `ulga/graph/chunk_grammar_metadata.json`
- `ulga/reports/vocabulary_theme_refinement_summary.json`
- `ulga/reports/sentence_pattern_mount_summary.json`
- `ulga/reports/ulga_sentence_pattern_qa_audit.json`
- `ulga/reports/pattern_vocabulary_constraint_summary.json`
- `ulga/reports/pattern_vocabulary_constraint_qa_audit.json`
- `themes/theme_catalog.json`
- `themes/theme_vocab_mapping.json`
- `vocabulary/json/vocabulary.json`
- `grammar_profile/json/grammar_profile.json`
- `chunk_profile/json/chunks_generator_safe.json`
- `chunk_profile/json/chunk_usage_class_mapping.json`

### Missing Evidence

The attached task referenced pattern-related graph/reports/docs generally, and those were available through the S7 graph and report files listed above.

Root-level files were not expected for S8B. The usable theme and chunk files are present under:

- `themes/theme_catalog.json`
- `themes/theme_vocab_mapping.json`
- `chunk_profile/json/chunks_generator_safe.json`
- `chunk_profile/json/chunk_usage_class_mapping.json`

### Theme Inventory

| Metric | Count |
|---|---:|
| Theme mapping records | 25 |
| Mounted ThemeNodes | 25 |
| Themes with `prev_theme_id` | 16 |
| Themes with `next_theme_id` | 22 |
| Missing `prev_theme_id` refs | 0 |
| Missing `next_theme_id` refs | 0 |

Level distribution:

| Level | Count |
|---|---:|
| A1 | 9 |
| A1_plus | 1 |
| A2 | 3 |
| A2_plus | 1 |
| B1 | 3 |
| B1_plus | 1 |
| B2 | 3 |
| B2_plus | 1 |
| C1 | 3 |

Observed progression roots:

- `a1_personal_information_and_greetings`
- `a1_daily_life_and_routines`
- `a1_school_and_classroom`
- `a1_homes_and_neighborhoods`
- `a1_shopping_and_basic_transactions`
- `a1_food_and_dining`
- `a1_interests_and_abilities`
- `a1_travel_and_weather`
- `a1_health_and_medical`

Observed progression chains:

1. `a1_personal_information_and_greetings -> a2_socializing_and_discussion -> b1_personal_expression_and_socializing -> b2_native_speed_communication -> c1_precise_expression`
2. `a1_daily_life_and_routines -> a2_daily_transactions_and_local_environment -> b1_work_and_business_environment -> b2_professional_and_academic_situations -> c1_advanced_work_and_socializing`
3. `a1_school_and_classroom -> b2_professional_and_academic_situations -> c1_advanced_work_and_socializing`
4. `a1_homes_and_neighborhoods -> a2_daily_transactions_and_local_environment -> b1_work_and_business_environment -> b2_professional_and_academic_situations -> c1_advanced_work_and_socializing`
5. `a1_shopping_and_basic_transactions -> a2_travel_and_consumption -> b1_travel_and_living_abroad -> b2_in_depth_debates_and_meetings -> c1_precise_expression`
6. `a1_food_and_dining -> a2_travel_and_consumption -> b1_travel_and_living_abroad -> b2_in_depth_debates_and_meetings -> c1_precise_expression`
7. `a1_interests_and_abilities -> b1_personal_expression_and_socializing -> b2_native_speed_communication -> c1_precise_expression`
8. `a1_travel_and_weather -> a2_travel_and_consumption -> b1_travel_and_living_abroad -> b2_in_depth_debates_and_meetings -> c1_precise_expression`
9. `a1_health_and_medical -> b1_personal_expression_and_socializing -> b2_native_speed_communication -> c1_precise_expression`

### Cross-Authority Readiness

| Authority | Current state for Theme Spiral |
|---|---|
| Vocabulary | Strongest usable scope source. Refined theme edges exist and overconnection has already been reduced. |
| Grammar | Usable only by CEFR and broad production function. Grammar is structural, not theme-specific. |
| Chunk | Limited. Safe chunks exist, but most theme hints are `General`; topic coverage is partial. |
| Pattern | Limited. Only 17 patterns have explicit theme refs; S7E recommends weighted inference, not hard classification. |
| Dependency | S8A says Theme Spiral must not become `REQUIRES`. |

## Theme Spiral Authority Definition

Theme Spiral Authority is the ULGA layer that defines staged revisiting of communicative domains across CEFR bands. It answers:

- what topic is being revisited;
- what lexical scope expands at each stage;
- what grammar and patterns are appropriate for the stage;
- what chunks and output types are expected;
- what earlier material should be reinforced;
- what new communicative load is introduced.

It differs from Theme Authority:

- Theme Authority owns theme identity, topic mapping, vocabulary membership, and blocked topics.
- Theme Spiral Authority owns staged progression between theme stages.

It differs from Dependency Authority:

- Dependency Authority owns `REQUIRES` and gate-eligible prerequisite logic.
- Theme Spiral Authority owns `SPIRAL_TO`, `INTRODUCES`, `REINFORCES`, `BROADENS_TO`, and `CONTRASTS_WITH` as non-gating sequencing and coverage signals.

It differs from Learning Path / Antigravity Planner:

- Theme Spiral is persistent authority metadata.
- Planner uses it to rank and sequence next activities.
- Learning Path is a runtime query result, not stored theme truth.

Core rule:

```text
SPIRAL_TO may influence order.
SPIRAL_TO must not block access.
Only Dependency Authority can create hard gating through accepted REQUIRES edges.
```

## Theme Stage Model

S8B should model a ThemeStage as a stage-specific view of a theme family. Existing data has theme records that already combine theme identity and stage identity. A future implementation can either keep using ThemeNodes as stage nodes or introduce explicit ThemeStageNodes.

Recommended stage bands:

- `Theme-A1`
- `Theme-A1_plus`
- `Theme-A2`
- `Theme-A2_plus`
- `Theme-B1`
- `Theme-B1_plus`
- `Theme-B2`
- `Theme-B2_plus`
- `Theme-C1`

Recommended fields per stage:

| Field | Meaning | Seed source |
|---|---|---|
| `theme_id` | Stable theme or stage identifier | `theme_catalog.json`, `theme_vocab_mapping.json` |
| `cefr_band` | Stage difficulty band | `level`, `progression_stage` |
| `stage_id` | Unique stage id, recommended format `theme_stage:{theme_id}:{cefr_band}` | Derived |
| `vocabulary_scope` | Topics, allowed CEFR levels, frequency bands, refined vocabulary edges | Theme mapping + vocabulary-theme edges |
| `grammar_scope` | Grammar level envelope and likely production functions | grammar nodes by CEFR + pattern refs |
| `chunk_scope` | Safe chunks matching theme hints/topics | `chunks_generator_safe.json` |
| `pattern_scope` | Explicit theme refs or inferred weighted pattern candidates | sentence pattern metadata + S7E policy |
| `expected_output_type` | Dialogue, short description, transaction, roleplay, discussion, report | Derived from CEFR and parent theme |
| `cognitive_load` | Low, medium, high, advanced | Derived from CEFR, output type, vocabulary breadth |
| `recommended_age_or_learner_profile` | Child, teen, adult, exam, general, professional | Exam alignment + theme domain |
| `planner_weight` | Planner ranking strength, not gate strength | Derived from confidence, coverage, learner target |

Recommended stage semantics:

| Stage | Scope |
|---|---|
| A1 | Concrete personal, home, food, school, health, weather, routine statements and short exchanges. |
| A1_plus | A1 review plus slightly broader local context, more slots, and controlled A2 vocabulary. |
| A2 | Local transactions, roleplay, simple past/future, preferences, routines, travel and social tasks. |
| A2_plus | Roleplay and skill bridge into B1; more flexible discourse markers and multi-turn exchanges. |
| B1 | Personal expression, work/travel problem solving, opinions, reasons, short narratives. |
| B1_plus | Critical discussion bridge, polysemy tolerance, more abstract topics. |
| B2 | Professional, academic, debate, meetings, native-speed communication support. |
| B2_plus | Academic bridge into C1 with dense vocabulary and complex discourse. |
| C1 | Precise expression, implicit meaning, complex texts, professional/social nuance. |

## Node and Edge Contract

### ThemeNode vs ThemeStageNode

Current mounted `theme` nodes already behave like staged themes because IDs include level and domain, for example `a1_food_and_dining` and `b2_native_speed_communication`. For minimal change:

- keep existing ThemeNodes unchanged;
- treat current ThemeNodes as stage-bearing theme nodes in S8F;
- optionally introduce ThemeStageNode later only if a single base theme needs multiple independent stage records.

Recommended minimal model:

```text
ThemeNode(stage-bearing) -> ThemeSpiralEdge -> ThemeNode(stage-bearing)
```

Recommended future model if needed:

```text
ThemeFamilyNode -> contains -> ThemeStageNode
ThemeStageNode -> spiral edge -> ThemeStageNode
```

### Should ThemeStageNode connect directly to Vocabulary / Grammar / Chunk / Pattern?

Recommended policy:

- Vocabulary: yes, but reuse existing `vocabulary -> belongs_to -> theme` edges as membership evidence. Avoid duplicating dense stage-vocabulary edges.
- Grammar: no direct dense stage-grammar edges. Store grammar scope as stage policy or query by CEFR and output type.
- Chunk: limited. Use chunk theme hints and topics as weighted scope evidence; do not hard attach most chunks because `General` dominates.
- Pattern: limited. Use explicit pattern-theme refs where present; use weighted inference for chunk-derived patterns.

### Separate Catalog vs Graph

Recommended future artifacts:

- `theme_stage_catalog.json`: stage records and scope policy.
- `theme_spiral_graph.json`: edges between stages.

For S8B, no JSON artifact is created.

## Edge Type Contract

| Relation | Semantic meaning | Allowed source | Allowed target | Gating | Recommendation | Mastery calculation | Curriculum sequencing |
|---|---|---|---|---|---|---|---|
| `SPIRAL_TO` | Source stage is revisited as a broader or more complex target stage. | `theme` or future `theme_stage` | `theme` or future `theme_stage` | No | Yes | Yes, as review/coverage evidence | Yes |
| `INTRODUCES` | Stage newly introduces a topic, output function, lexical set, grammar envelope, chunk family, or pattern family. | `theme_stage`; optionally `theme` | `vocabulary`, `chunk`, `sentence_pattern`, `grammar` scope refs or policy refs | No by default | Yes | Yes, as first-exposure evidence | Yes |
| `REINFORCES` | Stage reviews or strengthens earlier material without implying new prerequisite order. | `theme_stage`, `theme`, `chunk`, `sentence_pattern` | `theme_stage`, `theme`, `vocabulary`, `grammar`, `chunk`, `sentence_pattern` | No | Yes | Yes | Yes |
| `BROADENS_TO` | Source domain expands into adjacent, more abstract, or more complex domain. | `theme` or `theme_stage` | `theme` or `theme_stage` | No | Yes | Partial, coverage breadth only | Yes |
| `CONTRASTS_WITH` | Stages or domains are intentionally contrasted for discrimination, register, or topic boundary awareness. | `theme` or `theme_stage` | `theme` or `theme_stage` | No | Yes | Yes, diagnostic evidence | Optional |

Gate rule:

```text
All Theme Spiral relations default to gate_eligible = false.
Any hard gate must be represented separately by Dependency Authority as REQUIRES.
```

## Seed Strategy

| Seed source | Strategy | Confidence |
|---|---|---|
| `theme_catalog.json` | Seed stage identity, level, parent theme, active vocabulary count. | authoritative for mounted theme inventory |
| `theme_vocab_mapping.json` | Seed progression via `prev_theme_id` and `next_theme_id`; seed vocabulary scope from topics, blocked topics, allowed CEFR, frequency bands. | authoritative for declared mapping fields; derived for progression semantics |
| Pattern-theme linkage | Use existing 17 explicit pattern theme refs as high-confidence pattern scope. Use S7E weighted inference for the remaining patterns only as candidate scope. | authoritative for manual A1 refs; heuristic/manual_review_required for inferred refs |
| Chunk theme hints | Use non-`General` hints and topics as weighted chunk scope. Treat `General` as non-evidence. | derived for specific hints; heuristic for topic-only; manual_review_required for ambiguous topics |
| Grammar level profile | Use grammar CEFR and pattern grammar refs to define grammar envelope. Do not infer theme from grammar. | derived |
| CEFR band | Seed stage progression and cognitive load. CEFR is stage difficulty, not readiness. | authoritative for labels; derived for progression |
| Manual early-stage ordering | Use explicit ordering only for A1/A1_plus/A2 bridge design after review. | manual_review_required |

## Theme Progression Examples

These examples are design examples, not generated graph data. They use existing theme IDs where available and propose missing intermediate stage concepts where the current catalog does not yet have exact Home/Food/School/Travel/Health stage nodes at every band.

### Home

| Stage | Scope |
|---|---|
| A1 | Vocabulary: room, house, bed, door. Grammar: `there is/are`, prepositions of place. Patterns: "There is a ___", "I live in ___". Output: short home description. Reinforces concrete nouns and location. Introduces home objects. |
| A1_plus | Vocabulary: neighborhood, near, next to, floor. Grammar: place phrases and simple adjectives. Output: describe a room and nearby places. Reinforces A1 location. Introduces expanded local context. |
| A2 | Vocabulary: rent, address, building, repair. Grammar: past/simple future for local problems. Output: ask about a home problem. Reinforces home/location. Introduces transactions. |
| A2_plus | Vocabulary: move, appointment, landlord. Grammar: requests and roleplay. Output: housing roleplay. Reinforces local problem solving. Introduces multi-turn interaction. |
| B1 | Vocabulary: accommodation, neighborhood, commute. Grammar: reasons, comparison, short narrative. Output: explain living preferences. Reinforces home description. Introduces opinion and tradeoff. |
| B2 optional | Vocabulary: housing policy, affordability, urban planning. Grammar: argumentation and hedging. Output: discuss housing issues. Reinforces B1 preferences. Introduces abstract civic discussion. |

Existing seed chain: `a1_homes_and_neighborhoods -> a2_daily_transactions_and_local_environment -> b1_work_and_business_environment -> b2_professional_and_academic_situations -> c1_advanced_work_and_socializing`.

### Food

| Stage | Scope |
|---|---|
| A1 | Vocabulary: food, drink, water, rice. Grammar: likes, countable/uncountable basics. Patterns: "I like ___", "Can I have ___?" Output: simple order. Reinforces preferences. Introduces dining nouns. |
| A1_plus | Vocabulary: menu, price, breakfast, lunch. Grammar: polite requests. Output: cafe exchange. Reinforces A1 food words. Introduces transaction language. |
| A2 | Vocabulary: restaurant, bill, order, cheap. Grammar: past experience and future plan. Output: order and describe a meal. Reinforces requests. Introduces service interaction. |
| A2_plus | Vocabulary: reservation, recommendation, ingredient. Grammar: roleplay, clarification, preference reasons. Output: restaurant roleplay. Reinforces transaction skills. Introduces constraints. |
| B1 | Vocabulary: diet, health, habit, cuisine. Grammar: giving reasons, advice, comparison. Output: discuss eating habits. Reinforces food transactions. Introduces lifestyle explanation. |
| B2 optional | Vocabulary: nutrition, sustainability, food waste. Grammar: debate and concession. Output: discuss food systems. Reinforces B1 opinions. Introduces abstract social issues. |

Existing seed chain: `a1_food_and_dining -> a2_travel_and_consumption -> b1_travel_and_living_abroad -> b2_in_depth_debates_and_meetings -> c1_precise_expression`.

### School

| Stage | Scope |
|---|---|
| A1 | Vocabulary: teacher, class, book, pencil. Grammar: imperatives, can, simple classroom requests. Patterns: "Can I ___?", "This is my ___". Output: classroom exchange. Reinforces identity and objects. Introduces school nouns. |
| A1_plus | Vocabulary: subject, homework, test. Grammar: daily routine and ability. Output: talk about school day. Reinforces classroom nouns. Introduces study routine. |
| A2 | Vocabulary: schedule, lesson, project. Grammar: past simple and future plan. Output: describe a school event. Reinforces routine. Introduces planning. |
| A2_plus | Vocabulary: presentation, group work, feedback. Grammar: requests, suggestions, reasons. Output: group project roleplay. Reinforces school tasks. Introduces collaboration. |
| B1 | Vocabulary: exam, progress, goal, challenge. Grammar: explaining opinions and experiences. Output: discuss learning goals. Reinforces study routine. Introduces reflection. |
| B2 optional | Vocabulary: academic, research, argument, source. Grammar: reporting and hedging. Output: academic discussion. Reinforces B1 reflection. Introduces academic discourse. |

Existing seed chain: `a1_school_and_classroom -> b2_professional_and_academic_situations -> c1_advanced_work_and_socializing`. This chain skips A2/B1 in the current catalog and should be queued for manual review or intermediate stage design.

### Travel

| Stage | Scope |
|---|---|
| A1 | Vocabulary: bus, train, hotel, weather. Grammar: place and simple future intent. Patterns: "I go to ___", "It is ___". Output: simple travel/weather exchange. Reinforces place nouns. Introduces travel basics. |
| A1_plus | Vocabulary: ticket, station, map, near. Grammar: directions and requests. Output: ask for directions. Reinforces location. Introduces service interaction. |
| A2 | Vocabulary: trip, airport, reservation, cost. Grammar: past trip and future plan. Output: travel planning dialogue. Reinforces transactions. Introduces itinerary. |
| A2_plus | Vocabulary: delay, problem, change, help. Grammar: roleplay, complaint, clarification. Output: solve travel problem. Reinforces A2 planning. Introduces repair strategies. |
| B1 | Vocabulary: abroad, culture, accommodation, experience. Grammar: narrative, comparison, reasons. Output: describe living/travel abroad. Reinforces planning. Introduces cultural explanation. |
| B2 optional | Vocabulary: tourism, policy, environment, debate. Grammar: concession and argument. Output: debate travel impacts. Reinforces B1 experience. Introduces abstract impact. |

Existing seed chain: `a1_travel_and_weather -> a2_travel_and_consumption -> b1_travel_and_living_abroad -> b2_in_depth_debates_and_meetings -> c1_precise_expression`.

### Health

| Stage | Scope |
|---|---|
| A1 | Vocabulary: body, head, doctor, hurt. Grammar: have/has, simple present. Patterns: "I have a ___", "My ___ hurts". Output: state a symptom. Reinforces body vocabulary. Introduces health basics. |
| A1_plus | Vocabulary: medicine, rest, appointment. Grammar: advice with simple modals. Output: ask for help. Reinforces symptom statements. Introduces basic care. |
| A2 | Vocabulary: pharmacy, illness, fever, better. Grammar: past symptoms and should. Output: pharmacy/clinic roleplay. Reinforces care requests. Introduces advice. |
| A2_plus | Vocabulary: appointment, prescription, allergy. Grammar: clarification and constraints. Output: medical roleplay. Reinforces A2 health vocabulary. Introduces precise constraints. |
| B1 | Vocabulary: lifestyle, habit, stress, exercise. Grammar: reasons, advice, comparison. Output: discuss healthy habits. Reinforces symptoms/advice. Introduces lifestyle explanation. |
| B2 optional | Vocabulary: healthcare, mental health, policy, prevention. Grammar: argument and evaluation. Output: discuss health systems. Reinforces B1 advice. Introduces social analysis. |

Existing seed chain: `a1_health_and_medical -> b1_personal_expression_and_socializing -> b2_native_speed_communication -> c1_precise_expression`. This chain jumps from A1 to B1 and should be manually reviewed before builder output.

## Relationship with Dependency Authority

Theme Spiral and Dependency Authority must remain separate:

- `SPIRAL_TO` means "revisit and broaden this communicative domain later."
- `REQUIRES` means "the source must be mastered before target access."
- Theme Spiral can recommend a next theme.
- Theme Spiral can shape curriculum coverage.
- Theme Spiral can select review material.
- Theme Spiral cannot block a learner.
- Dependency Authority alone owns hard gating.

When Theme Spiral seems to imply prerequisite, the safe rule is:

```text
Create or review a separate Dependency Authority candidate.
Do not reinterpret SPIRAL_TO as REQUIRES.
```

Examples:

- Food A1 before Food A2 is useful sequencing, not hard prerequisite.
- Travel A1 before Travel B1 is sensible review, not a gate.
- School A1 jumping to B2 professional/academic situations is a catalog progression anomaly, not a dependency.

## Graph Schema Proposal

Proposed future file: `ulga/schema/theme_spiral_graph_schema.json`. S8B does not create it.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "ulga/schema/theme_spiral_graph_schema.json",
  "title": "ULGA Theme Spiral Graph Schema",
  "contract_version": "ULGA-S8B-proposal",
  "type": "object",
  "additionalProperties": false,
  "required": ["graph_metadata", "theme_stage_nodes", "spiral_edges"],
  "properties": {
    "graph_metadata": {
      "type": "object",
      "required": [
        "graph_id",
        "contract_version",
        "generated_at",
        "source_files",
        "spiral_policy",
        "spiral_is_not_prerequisite"
      ],
      "properties": {
        "graph_id": { "type": "string" },
        "contract_version": { "type": "string" },
        "generated_at": { "type": ["string", "null"] },
        "source_files": { "type": "array", "items": { "type": "string" } },
        "spiral_policy": { "type": "string" },
        "spiral_is_not_prerequisite": { "type": "boolean", "const": true }
      }
    },
    "theme_stage_nodes": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "stage_id",
          "theme_id",
          "cefr_band",
          "vocabulary_scope",
          "grammar_scope",
          "chunk_scope",
          "pattern_scope",
          "expected_output_type",
          "cognitive_load",
          "recommended_age_or_learner_profile",
          "planner_weight",
          "confidence",
          "source_authority",
          "review_status",
          "notes"
        ],
        "properties": {
          "stage_id": { "type": "string", "pattern": "^theme_stage:[A-Za-z0-9_.:-]+$" },
          "theme_id": { "type": "string" },
          "cefr_band": {
            "type": "string",
            "enum": ["A1", "A1_plus", "A2", "A2_plus", "B1", "B1_plus", "B2", "B2_plus", "C1"]
          },
          "vocabulary_scope": { "type": "object" },
          "grammar_scope": { "type": "object" },
          "chunk_scope": { "type": "object" },
          "pattern_scope": { "type": "object" },
          "expected_output_type": { "type": "array", "items": { "type": "string" } },
          "cognitive_load": { "type": "string" },
          "recommended_age_or_learner_profile": { "type": "array", "items": { "type": "string" } },
          "planner_weight": { "type": "number", "minimum": 0, "maximum": 1 },
          "confidence": {
            "type": "object",
            "required": ["value", "method"],
            "properties": {
              "value": { "type": "number", "minimum": 0, "maximum": 1 },
              "method": {
                "type": "string",
                "enum": ["authoritative", "derived", "heuristic", "manual_review_required"]
              }
            }
          },
          "source_authority": { "type": "object" },
          "review_status": {
            "type": "string",
            "enum": ["accepted", "needs_review", "blocked", "deprecated"]
          },
          "notes": { "type": "array", "items": { "type": "string" } }
        }
      }
    },
    "spiral_edges": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "edge_id",
          "source_stage_id",
          "target_stage_id",
          "relation",
          "confidence",
          "source_authority",
          "evidence",
          "review_status",
          "recommendation_weight",
          "gate_eligible",
          "notes"
        ],
        "properties": {
          "edge_id": { "type": "string", "pattern": "^theme_spiral_edge:[A-Za-z0-9_.:-]+$" },
          "source_stage_id": { "type": "string" },
          "target_stage_id": { "type": "string" },
          "relation": {
            "type": "string",
            "enum": ["SPIRAL_TO", "INTRODUCES", "REINFORCES", "BROADENS_TO", "CONTRASTS_WITH"]
          },
          "confidence": {
            "type": "object",
            "required": ["value", "method"],
            "properties": {
              "value": { "type": "number", "minimum": 0, "maximum": 1 },
              "method": {
                "type": "string",
                "enum": ["authoritative", "derived", "heuristic", "manual_review_required"]
              }
            }
          },
          "source_authority": { "type": "object" },
          "evidence": { "type": "array", "items": { "type": "object" } },
          "review_status": {
            "type": "string",
            "enum": ["accepted", "needs_review", "blocked", "deprecated"]
          },
          "recommendation_weight": { "type": "number", "minimum": 0, "maximum": 1 },
          "gate_eligible": { "type": "boolean", "const": false },
          "notes": { "type": "array", "items": { "type": "string" } }
        }
      }
    }
  }
}
```

## Validation Plan

### Schema Validation

- Validate required `graph_metadata`, `theme_stage_nodes`, and `spiral_edges`.
- Validate relation enum.
- Validate `gate_eligible` is always `false`.
- Validate `recommendation_weight` and confidence values are in range.

### Missing Theme Validation

- Every `theme_id` must resolve to `theme_nodes.json` or an accepted future stage catalog record.
- Every `prev_theme_id` and `next_theme_id` seed must resolve to an existing theme.

### Missing Stage Validation

- Every `source_stage_id` and `target_stage_id` must resolve to a stage node.
- Each stage must have a valid `cefr_band`.

### Invalid CEFR Transition Validation

- Flag backward transitions such as B2 to A2 unless relation is `REINFORCES` and explicitly reviewed.
- Flag large jumps such as A1 to B2 as `needs_review`.
- Do not fail plus-level bridge transitions if they are explicit and reviewed.

### Circular Spiral Detection

- Detect cycles in `SPIRAL_TO` and `BROADENS_TO`.
- Cycles in `REINFORCES` may be allowed if the relation is explicitly review-oriented, but should be reported.

### Stage Scope Coverage Audit

- Check each stage for non-empty vocabulary scope.
- Check grammar scope is policy-based and not false theme inference.
- Check chunk and pattern scope confidence.

### Vocabulary Leakage Audit

- Ensure blocked topics do not enter vocabulary scope.
- Use refined vocabulary-theme edges before raw topics.
- Flag high-degree broad themes and secondary-topic overreach.

### Grammar Leakage Audit

- Ensure grammar is not treated as theme evidence.
- Ensure grammar CEFR scope does not become learner readiness.

### Pattern Leakage Audit

- Explicit pattern theme refs are accepted.
- Chunk-derived inferred pattern scope must remain weighted unless audited.
- Do not create dense pattern-theme-vocabulary edge layers.

### Chunk Leakage Audit

- Treat `General` chunk theme hints as no theme evidence.
- Require manual review for topic-only chunk scope in broad topics like `communication` and `describing things`.

### Dependency Misuse Audit

- Reject `REQUIRES` in theme spiral graph.
- Reject `gate_eligible = true`.
- Report any code or graph layer trying to use `SPIRAL_TO` as a prerequisite.

### Manual Review Queue

Queue records when:

- CEFR jump is more than one broad band;
- source or target stage is inferred;
- scope depends only on topic;
- chunk hint is `General`;
- pattern scope is inferred from weak signals;
- theme chain crosses parent-theme domains unexpectedly.

## Risk Register

| Risk | Severity | Analysis | Mitigation |
|---|---|---|---|
| Theme Spiral misread as prerequisite | High | A stage chain can look like order, but it should not block access. | Enforce `gate_eligible = false`; use Dependency Authority for hard gates. |
| CEFR stage misread as learning readiness | High | A learner can work on a B1 theme with support even if the A2 theme stage was not mastered. | Treat CEFR as difficulty and scope, not readiness. |
| Over-broad parent theme expansion | Medium | Chains sometimes move from school/home/food to work/academic/debate domains. | Cross-parent transitions need manual review and explanation. |
| Theme vocabulary scope too broad | High | S5 refinement reduced overconnection, but broad topics still risk leakage. | Prefer refined edges and primary topics; audit blocked topics and secondary-topic expansion. |
| A1/A1_plus stage ambiguity | Medium | Current catalog has many A1 roots but only one A1_plus bridge. | Do not infer per-domain A1_plus stages unless explicitly generated by a later design. |
| Pattern/chunk scope too weak | Medium | Pattern theme refs cover only 17 patterns; chunks are mostly `General`. | Use weighted scope and review queues, not hard edges. |
| Planner over-follows theme progression | Medium | Planner may keep learners in one chain and reduce variety. | Use spiral as one ranking signal with coverage balancing. |
| Dense graph growth | High | Direct stage-to-vocabulary/chunk/pattern edges could grow quickly and duplicate existing membership authority. | Use scope policy and runtime joins; materialize only sparse audited edges. |
| Existing schema conflict | Medium | ULGA-S2 edge enum has lowercase `spiral_to`, while S8B proposes uppercase logical relations. | Use dedicated `theme_spiral_graph_schema.json` or metadata logical relation mapping. |

## Recommended Roadmap

### ULGA-S8C DependencyEdgeBuilder

Build dependency edges from accepted sources only. Theme Spiral output must not become dependency input except as non-gating evidence.

### ULGA-S8D DependencyAuthority_QA_Audit

Confirm `SPIRAL_TO` is not converted to `REQUIRES`, and detect any gate misuse.

### ULGA-S8E LearningSignalClassification

Classify signals into gate, recommendation, mastery evidence, review, coverage, and runtime planner signals. Theme Spiral should classify as recommendation/coverage/review.

### ULGA-S8F ThemeSpiralEdgeBuilder

Build only `theme_spiral_graph.json` and optional review queues. Minimal first pass:

- stage nodes from existing ThemeNodes;
- `SPIRAL_TO` edges from `next_theme_id`;
- review queue for A1 to B2 jumps and cross-parent transitions;
- no dense cross-authority edges.

### ULGA-S8G ThemeSpiralAuthority_QA_Audit

Audit schema, missing stages, CEFR jumps, cycles, vocabulary leakage, pattern/chunk leakage, and dependency misuse.

### ULGA-S9A LearnerStateAuthority_DesignScan

Design learner state after signal classification so mastery can use spiral evidence without treating it as a hard gate.

## Go / No-Go Recommendation

Recommendation: **GO with strict non-gating constraints**.

S8B has enough evidence to define Theme Spiral Authority. `theme_vocab_mapping.json` already contains valid progression references with no missing IDs, and the mounted ThemeNode layer matches the mapping count.

No-go conditions for S8F:

- creating `REQUIRES` from theme progression;
- setting `gate_eligible = true` on any theme spiral edge;
- materializing dense stage-to-vocabulary, stage-to-chunk, or stage-to-pattern edges;
- treating `General` chunk hints as theme evidence;
- treating topic-only pattern inference as hard classification;
- silently accepting large CEFR jumps such as A1 to B2 without review.

Minimal safe implementation path:

- keep existing ThemeNodes unchanged;
- produce separate stage/spiral artifacts only in the builder task;
- seed `SPIRAL_TO` from `next_theme_id`;
- mark all edges non-gating;
- use refined vocabulary-theme edges as scope evidence;
- put ambiguous chunk/pattern/large-jump cases into manual review.

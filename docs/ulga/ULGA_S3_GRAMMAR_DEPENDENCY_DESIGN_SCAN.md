# ULGA-S3 Grammar Dependency Authority Design Scan

## 1. Preflight

This document represents the Design Scan for the **Grammar Dependency Authority** step of the Universal Learning Graph Authority (ULGA) layer. 

### Core Restrictions Verified:
- **No data mutation**: No changes are made to `grammar_profile.json`, `chunks.json`, `vocabulary.json`, or level profiles.
- **No data generation**: No formal graph nodes or edges are generated. Graph empty scaffold remains in place.
- **No code changes**: No implementation code, generator/validator runtime edits, recommendation plans, or learning paths are written.
- **Read-only audit**: All authority sources remain strictly read-only.

---

## 2. Files Inspected

The following repository artifacts were inspected as part of this scan:

1. **ULGA Design & Schema Docs**:
   - [docs/ulga/ULGA_S1_DESIGN_SCAN.md](file:///G:/HomeWork/English_Learning_DB/docs/ulga/ULGA_S1_DESIGN_SCAN.md)
   - [docs/ulga/ulga_schema_contract.md](file:///G:/HomeWork/English_Learning_DB/docs/ulga/ulga_schema_contract.md)
   - [docs/ulga/ulga_roadmap.md](file:///G:/HomeWork/English_Learning_DB/docs/ulga/ulga_roadmap.md)
   - [docs/ulga/ULGA_S2_CLOSEOUT.md](file:///G:/HomeWork/English_Learning_DB/docs/ulga/ULGA_S2_CLOSEOUT.md)
2. **ULGA Implemented Schemas (S2)**:
   - [ulga/schema/ulga_node_schema.json](file:///G:/HomeWork/English_Learning_DB/ulga/schema/ulga_node_schema.json)
   - [ulga/schema/ulga_edge_schema.json](file:///G:/HomeWork/English_Learning_DB/ulga/schema/ulga_edge_schema.json)
   - [ulga/schema/ulga_graph_schema.json](file:///G:/HomeWork/English_Learning_DB/ulga/schema/ulga_graph_schema.json)
   - [ulga/graph/ulga_graph.empty.json](file:///G:/HomeWork/English_Learning_DB/ulga/graph/ulga_graph.empty.json)
   - [ulga/validators/validate_ulga_schema.py](file:///G:/HomeWork/English_Learning_DB/ulga/validators/validate_ulga_schema.py)
3. **Source Grammar Authority**:
   - [grammar_profile/json/grammar_profile.json](file:///G:/HomeWork/English_Learning_DB/grammar_profile/json/grammar_profile.json)
   - [grammar_profile/mapping/level_mapping.json](file:///G:/HomeWork/English_Learning_DB/grammar_profile/mapping/level_mapping.json)

---

## 3. Current Grammar Authority Assessment

The EGP source database ([grammar_profile.json](file:///G:/HomeWork/English_Learning_DB/grammar_profile/json/grammar_profile.json)) contains **1,222 records** representing structured English Grammar Profile statements. 

Our assessment indicates the database supports the following ULGA features:

- **Grammar Node creation**: Every record possesses a unique, stable string `id` (e.g., `1741163706316x198445876411383900`) which translates directly to a `GrammarNode` identifier.
- **CEFR difficulty authority**: Active candidate levels (A1-C1) are explicitly mapped via `level` fields. Exclusion of B2+/C-level records for specific tracks is manageable using [level_mapping.json](file:///G:/HomeWork/English_Learning_DB/grammar_profile/mapping/level_mapping.json).
- **Grammar categories**: The fields `super_category` (e.g. `MODALITY`, `CLAUSES`, `PRONOUNS`, `PAST`, `VERBS`) and `sub_category` (e.g. `present simple`, `there is/are`, `countable/uncountable`) are structured and clean.
- **Grammar descriptors**: `guideword` and `can_do_statement` fields contain rich semantic labels and statements for labeling and planner context.
- **Prerequisite edge inference**: EGP records do **not** natively contain dependency links. Edge relations are derived pedagogical assumptions that must be modeled using mapping rules.
- **Confidence tagging**: Direct EGP attributes receive a confidence of `1.0` (direct match). Inferred edges receive a confidence of `0.7` (rule-based).
- **Versioning**: Data format carries version contract `ULGA-S2`.

---

## 4. Grammar Node Model

Each mounted `GrammarNode` object in the graph must conform to [ulga_node_schema.json](file:///G:/HomeWork/English_Learning_DB/ulga/schema/ulga_node_schema.json):

```json
{
  "id": "grammar:1741163715607x526138276437947400",
  "node_type": "grammar",
  "label": "FORM: 'THERE IS'",
  "authority_source": {
    "source_name": "English Grammar Profile",
    "source_file": "grammar_profile/json/grammar_profile.json",
    "source_record_id": "1741163715607x526138276437947400",
    "source_row": 1210,
    "derivation": "source_direct"
  },
  "cefr_level": "A1",
  "confidence": {
    "value": 1.0,
    "method": "source_direct"
  },
  "version": {
    "contract": "ULGA-S2",
    "source_version": "20260615",
    "generated_at": null
  },
  "metadata": {
    "super_category": "VERBS",
    "sub_category": "there is/are",
    "can_do_statement": "Can use 'there is'...",
    "canonical_grammar_key": "egp_verbs_there_is_are_there_is"
  }
}
```

---

## 5. Grammar Edge Model

Prerequisite relationships must conform to [ulga_edge_schema.json](file:///G:/HomeWork/English_Learning_DB/ulga/schema/ulga_edge_schema.json):

```json
{
  "id": "edge:grammar:linking_be:prerequisite:grammar:there_is",
  "source_node_id": "grammar:1741163715288x539616242661052000",
  "target_node_id": "grammar:1741163715607x526138276437947400",
  "edge_type": "prerequisite",
  "authority_source": {
    "source_name": "ULGA Grammar Dependency Rules",
    "source_file": null,
    "source_record_id": null,
    "derivation": "rule_based"
  },
  "confidence": {
    "value": 0.70,
    "method": "rule_based_design",
    "notes": ["Inferred from copula be to empty subject there is."]
  },
  "version": {
    "contract": "ULGA-S2",
    "source_version": "20260615",
    "generated_at": null
  },
  "metadata": {
    "hard_gate": true,
    "classification": "hard_prerequisite",
    "reason": "Copula be verb must precede there is/are empty subjects."
  }
}
```

---

## 6. Dependency Classification

To manage and traverse the curriculum graph, dependencies are classified into five operational categories in edge metadata:

1. **`hard_prerequisite`**: A structural grammar prerequisite. Mastery of the source node is mandatory before introducing the target node. (Edge type: `prerequisite`, `metadata.hard_gate = true`).
2. **`soft_prerequisite`**: Recommended pedagogical order. No strict gate blocking. (Edge type: `prerequisite`, `metadata.hard_gate = false` or `edge_type = supports`).
3. **`spiral_review`**: Same topic/category, visited at a higher level with greater lexical complexity. (Edge type: `spiral_to` / `reviews`).
4. **`contrast_pair`**: Opposing structures commonly confused that are best taught alongside each other (e.g. *present simple* vs. *present continuous*). (Edge type: `contrasts_with`).
5. **`unlock_relation`**: Mastery of a core concept (e.g., base verbs) which unlocks a wide array of sub-concepts. (Edge type: `unlocks`).

---

## 7. Proposed Rule Set

The following mapping rules link EGP nodes into dependencies:

### 1. `be` verb $\rightarrow$ `there is / there are`
- **Source Node**: `1741163715288x539616242661052000` (linking verb *be*, A1)
- **Target Nodes**: `1741163715607x526138276437947400` (*there is*, A1) and `1741163715607x671128268905876200` (*there are*, A1)
- **Classification**: `hard_prerequisite`

### 2. `be` verb + `verb-ing` $\rightarrow$ `present continuous`
- **Source Node**: `1741163715288x262148040901666750` (auxiliary verb *be*, A1)
- **Target Nodes**: `PRESENT` $\rightarrow$ `present continuous` nodes
- **Classification**: `hard_prerequisite`

### 3. subject pronoun $\rightarrow$ subject-verb agreement
- **Source Node**: `1741163713868x463659211645272000` (subject pronouns, A1)
- **Target Nodes**: `CONCORD` / Subject-Verb agreement rules (e.g. singular/plural third-person verb forms)
- **Classification**: `hard_prerequisite`

### 4. singular/plural noun $\rightarrow$ articles / countable nouns
- **Source Node**: `NOUNS` singular/plural noun phrases (A1)
- **Target Nodes**: `DETERMINERS` $\rightarrow$ `articles` (e.g., `1741163708789x105964971324936210`, A1 articles *the, a, an*)
- **Classification**: `hard_prerequisite`

### 5. present simple $\rightarrow$ adverbs of frequency
- **Source Node**: `PRESENT` $\rightarrow$ `present simple` base statements (A1)
- **Target Nodes**: `ADVERBS` $\rightarrow$ frequency adverbs (e.g., `1741163706722x604132732561016200`, A1 frequency *always, sometimes*)
- **Classification**: `soft_prerequisite` / `unlock_relation`

### 6. past simple regular $\rightarrow$ past time expressions
- **Source Node**: `PAST` $\rightarrow$ `past simple` verbs (A1/A2)
- **Target Nodes**: `ADVERBS` / time expressions (e.g. *yesterday, last night*)
- **Classification**: `soft_prerequisite`

### 7. `can` $\rightarrow$ `can question / can negative`
- **Source Node**: `MODALITY` $\rightarrow$ `can` (ability, A1)
- **Target Nodes**: `MODALITY` $\rightarrow$ `can` negatives/questions
- **Classification**: `hard_prerequisite`

### 8. wh-word $\rightarrow$ wh-question patterns
- **Source Node**: `QUESTIONS` wh-words (A1)
- **Target Nodes**: `CLAUSES` $\rightarrow$ `interrogatives` wh-questions (e.g., `1741163708342x469176927335390700`, A2)
- **Classification**: `hard_prerequisite`

### 9. adjective $\rightarrow$ comparatives / superlatives
- **Source Node**: `ADJECTIVES` attributive/position forms (e.g., `1741163706530x479020650602328450`, A1)
- **Target Nodes**: `ADJECTIVES` comparatives and superlatives (A2/B1)
- **Classification**: `hard_prerequisite`

### 10. sentence connector $\rightarrow$ because / so / but
- **Source Node**: `CONJUNCTIONS` coordinating conjunctions (e.g. `1741163708775x236006169337418240`, A1)
- **Target Nodes**: `CLAUSES` subordinating *because* clauses (e.g., `1741163708567x184494536538858620`, A1)
- **Classification**: `soft_prerequisite` / `unlock_relation`

---

## 8. ULGA Integration Plan

In the upcoming implementation phase (**ULGA-S4**), we will introduce `build_ulga_grammar.py` inside `ulga/tools/` which will:
1. **Node Mounting**: Parse EGP records from `grammar_profile.json` and generate conformant Node records under the family prefix `grammar:`.
2. **Rule Resolution**: Apply deterministic rule matching on records matching the prerequisite criteria (matching super/sub categories and keyword combinations).
3. **Graph Assembly**: Populate `ulga_nodes.json` and `ulga_edges.json`, modifying `ulga_graph.json` status to `"formal_data_mounted": true`.

---

## 9. Validation Strategy

The validation execution script in S4 will extend `validate_ulga_schema.py` to assert:
- **No Cycles**: Cycle detection (DFS) runs over `prerequisite` edges with `hard_gate=true` to guarantee no circular dependencies.
- **Node Presence**: Every edge source and target resolves to an existing mounted node.
- **Level Constraints**: Checks that no child node CEFR level is lower than its hard prerequisite CEFR level, except where an explicit spiral/pedagogical override is documented.

---

## 10. Risks / Warnings

> [!WARNING]
> EGP is a **difficulty profile**, not a **dependency profile**. EGP CEFR levels represent student error-free production boundaries, not instruction ordering. Dependencies are pedagogical rules of thumb; their confidence is bounded at `0.70` (rule-based) and must be tested via path gates in later stages.

---

## 11. Recommended Next Task

- **Recommended Task Name**: `ULGA-S4_GrammarDependencyAuthority_Implementation_Fix`

---

## 12. Final Verdict

**Verdict**: **PASS**
The design scan is complete, categories are mapped to implemented schemas, and the repository is ready for grammar node and edge implementation.

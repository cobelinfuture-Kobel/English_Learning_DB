# ULGA-S6G Chunk Grammar Metadata Design Scan

This report defines the design scan and architecture specifications for the **Chunk Grammar Metadata Layer** and **Chunk Parsing Authority** under `ULGA-S6G`. It details how `ChunkNode` records are annotated with grammatical signals, prerequisites, slot patterns, and formulaic semantics to support the future Sentence Pattern Authority and Antigravity Planner.

This task is a **Design Scan** only. No nodes, edges, or source files have been modified.

---

## 1. Document & Process Trace

### 1.1 Files Created
- [ULGA_S6G_CHUNK_GRAMMAR_METADATA_DESIGN_SCAN.md](file:///G:/HomeWork/English_Learning_DB/docs/ulga/ULGA_S6G_CHUNK_GRAMMAR_METADATA_DESIGN_SCAN.md) (This file)

### 1.2 Files Modified
- **None** (Strictly prohibited).

### 1.3 Files Inspected
- **Design & QA Documents**:
  - [ULGA_S6A_CHUNK_AUTHORITY_DESIGN_SCAN.md](file:///G:/HomeWork/English_Learning_DB/docs/ulga/ULGA_S6A_CHUNK_AUTHORITY_DESIGN_SCAN.md)
  - [ULGA_S6C_CHUNK_VOCABULARY_LINKAGE_DESIGN_SCAN.md](file:///G:/HomeWork/English_Learning_DB/docs/ulga/ULGA_S6C_CHUNK_VOCABULARY_LINKAGE_DESIGN_SCAN.md)
  - [ULGA_S6D_CHUNK_VOCABULARY_LINKAGE_IMPLEMENTATION_CLOSEOUT.md](file:///G:/HomeWork/English_Learning_DB/docs/ulga/ULGA_S6D_CHUNK_VOCABULARY_LINKAGE_IMPLEMENTATION_CLOSEOUT.md)
  - [ULGA_S6E_CHUNK_VOCABULARY_LINKAGE_QA_AUDIT.md](file:///G:/HomeWork/English_Learning_DB/docs/ulga/ULGA_S6E_CHUNK_VOCABULARY_LINKAGE_QA_AUDIT.md)
  - [ULGA_S4F_EXTENDED_GRAMMAR_DEPENDENCY_QA_AUDIT.md](file:///G:/HomeWork/English_Learning_DB/docs/ulga/ULGA_S4F_EXTENDED_GRAMMAR_DEPENDENCY_QA_AUDIT.md)
  - [ulga_schema_contract.md](file:///G:/HomeWork/English_Learning_DB/docs/ulga/ulga_schema_contract.md)
  - [ulga_roadmap.md](file:///G:/HomeWork/English_Learning_DB/docs/ulga/ulga_roadmap.md)
- **Graph & Edge Datasets**:
  - [chunk_nodes.json](file:///G:/HomeWork/English_Learning_DB/ulga/graph/chunk_nodes.json)
  - [chunk_vocabulary_edges.json](file:///G:/HomeWork/English_Learning_DB/ulga/graph/chunk_vocabulary_edges.json)
  - [grammar_nodes.json](file:///G:/HomeWork/English_Learning_DB/ulga/graph/grammar_nodes.json)
  - [grammar_dependency_all_edges.json](file:///G:/HomeWork/English_Learning_DB/ulga/graph/grammar_dependency_all_edges.json)
  - [vocabulary_nodes.json](file:///G:/HomeWork/English_Learning_DB/ulga/graph/vocabulary_nodes.json)
  - [vocabulary_theme_edges.refined.json](file:///G:/HomeWork/English_Learning_DB/ulga/graph/vocabulary_theme_edges.refined.json)
  - [vocabulary_morphology_edges.json](file:///G:/HomeWork/English_Learning_DB/ulga/graph/vocabulary_morphology_edges.json)
- **Source Config files**:
  - [chunks.json](file:///G:/HomeWork/English_Learning_DB/chunk_profile/json/chunks.json)
  - [chunks_generator_safe.json](file:///G:/HomeWork/English_Learning_DB/chunk_profile/json/chunks_generator_safe.json)
  - [chunk_usage_class_mapping.json](file:///G:/HomeWork/English_Learning_DB/chunk_profile/json/chunk_usage_class_mapping.json)

---

## 2. Chunk Grammar Metadata Assessment

We conducted a statistical scan on the 3,522 mounted `ChunkNode` records to evaluate grammar-specific metadata distribution:

- **Total Chunk Nodes**: 3,522

### 2.1 Usage Class Distribution
- `general_phrase`: 1,770 (50.26%)
- `phrasal_verb`: 709 (20.13%)
- `prepositional_phrase`: 304 (8.63%)
- `idiom`: 260 (7.38%)
- `time_phrase`: 180 (5.11%)
- `compound_noun`: 112 (3.18%)
- `place_phrase`: 100 (2.84%)
- `quantity_phrase`: 16 (0.45%)
- `discourse_marker`: 14 (0.40%)
- `modal_expression`: 10 (0.28%)
- `compound_adjective`: 9 (0.26%)
- `social_expression`: 9 (0.26%)
- `greeting`: 7 (0.20%)
- `grammar_term`: 5 (0.14%)
- `opinion_expression`: 5 (0.14%)
- `emotion_expression`: 5 (0.14%)
- `daily_routine`: 4 (0.11%)
- `request_expression`: 3 (0.09%)

### 2.2 Core Syntactic Categories
- **`grammar_term` count**: 5 (e.g. `count noun`, `definite article`, `phrasal verb`).
- **`general_phrase` count**: 1,770
- **`phrasal_verb` count**: 709
- **`prepositional_phrase` count**: 304
- **`opinion_expression` count**: 5
- **`time_phrase` count**: 180
- **`formulaic candidate` count**: **284** (derived from the sum of `idiom`, `social_expression`, `greeting`, `emotion_expression`, `request_expression`).
- **`placeholder pattern` count**: **1,565** (chunks containing grammatical placeholders: `sb's`, `sth's`, `sb`, `sth`, `etc.`).
- **`grammar-like chunk candidate` count**: **21** (includes `grammar_term` nodes, plus chunks containing modals/aspects/prepositions like `going to`, `used to`, `have to`, `as soon as`, `would rather`, `had better`, `be able to`).
- **`pattern seed candidate` count**: **1,259** (chunks containing slot variables `sb`, `sth`, `sb's`, `sth's` that can directly seed a structural sentence pattern).

---

## 3. Core Architectural Decisions

We compared three options for modeling Chunk-to-Grammar relations in ULGA:

- **Option A**: Direct `chunk --requires--> grammar` graph edges.
- **Option B**: Simple `metadata` references inside the `ChunkNode`.
- **Option C**: An independent **`ChunkParsingAuthority`** derived metadata layer.

### 3.1 Architectural Matrix

| Metric | Option A: Direct Edges | Option B: Metadata Refs | Option C: Parsing Authority |
| :--- | :--- | :--- | :--- |
| **Graph Purity** | **FAIL**: Mixes syntax and lexical realization. | **PASS**: Separation of node layers. | **PASS**: Complete isolation of graphs. |
| **Maintainability** | **FAIL**: High edge maintenance overhead. | **PARTIAL**: Node bloat; hard to bulk edit. | **PASS**: Central rule engine; derived compilation. |
| **Planner Value** | **PARTIAL**: Simple path, but prone to loops. | **PASS**: Direct node query. | **PASS**: Dynamic contextual constraints. |
| **Gate Value** | **FAIL**: Graph traversal bottlenecks. | **PASS**: Fast JSON lookup. | **PASS**: Separation of gates and graph. |
| **Sentence Pattern Compatibility** | **FAIL**: Cannot model slots. | **PARTIAL**: Limited schema variables. | **PASS**: Full slot parsing blueprint. |

### 3.2 Recommendation: Option C + Option B
We recommend **Option C (Independent ChunkParsingAuthority)** as the compiler/mapping authority, which will generate static **Option B (Metadata References)** inside the `metadata` of the mounted `ChunkNode` records. 

> [!IMPORTANT]
> Chunks must **never** connect to GrammarNodes via direct graph edges. Mixing lexical chunks into the acyclic grammar dependency DAG would corrupt CEFR level gates, cause path loops, and prevent slot-based sentence expansion.

---

## 4. Chunk Grammar Metadata Schema

We define the derived metadata schema for each `ChunkNode`:

```json
{
  "grammar_signals": ["to-infinitive", "gerund"],
  "grammar_prerequisites": [
    "grammar:1741163706316x198445876411383900"
  ],
  "slot_pattern": "{verb} sb to do sth",
  "slot_count": 3,
  "slot_types": [
    "verb_stem",
    "pronoun_object",
    "verb_infinitive"
  ],
  "chunk_semantics": "persuasion",
  "pattern_seed": true,
  "formulaic_type": "collocation",
  "parsing_confidence": 0.95,
  "parsing_method": "regex_placeholder_parse"
}
```

### 4.1 Field Specifications

- **`grammar_signals`** (List of Strings): Grammatical structures found in the chunk.
  - *Candidates*: `to-infinitive`, `gerund`, `passive-voice`, `modal-auxiliary`, `comparative`, `superlative`, `plural-noun`, `possessive-s`.
- **`grammar_prerequisites`** (List of Strings): References to `GrammarNode` IDs that represent dependencies (e.g. learning `advise sb to do sth` requires the infinitive rule).
- **`slot_pattern`** (String or Null): The chunk's normalized surface rewritten with variable slot syntax.
  - *Examples*: `"{verb} sb to do sth"`, `"{verb} sth up"`, `"by the way"`.
- **`slot_count`** (Integer): Number of syntax variables in the chunk.
- **`slot_types`** (List of Strings): Syntactic categories of the variables.
  - *Candidates*: `verb_stem`, `pronoun_object`, `noun_phrase`, `adjective`.
- **`chunk_semantics`** (String or Null): Semantic function.
  - *Candidates*: `time_duration`, `place_direction`, `logical_connector`, `opinion_hedge`.
- **`pattern_seed`** (Boolean): True if the chunk contains syntactic slots (`sb`, `sth`) enabling sentence generation.
- **`formulaic_type`** (String or Null): Type of formulaic classification.
  - *Candidates*: `idiom`, `collocation`, `discourse_marker`, `social_formula`.
- **`parsing_confidence`** (Float): The parser's confidence score (0.0 to 1.0).
- **`parsing_method`** (String): Heuristic class used for generation.

---

## 5. Chunk Parsing Authority Rules

The **`ChunkParsingAuthority`** will compile metadata using three rule classes:

### Rule Class 1: Regex Slot Parsing (For 1,259 Pattern Seeds)
Extracts slots and counts variables based on placeholder substrings:
- `"sb's" / "sth's"` $\rightarrow$ Slot: `"{sb_possessive}"` / `"{sth_possessive}"`.
- `"sb" / "sth"` $\rightarrow$ Slot: `"{sb}"` / `"{sth}"`.
- `"doing sth"` $\rightarrow$ Slot: `"{gerund}"`.
- `"do sth"` $\rightarrow$ Slot: `"{infinitive}"`.

### Rule Class 2: POS-Pattern Mapping (For Phrasal Verbs)
Using vocabulary linkage POS metadata to identify syntactic categories:
- `[verb] + [particle]` $\rightarrow$ `"{verb} {particle}"` (e.g. `give up` $\rightarrow$ `"{verb} up"`).

### Rule Class 3: Grammatical Guideword Matching
Cross-referencing the chunk's guideword/source notes with the Grammar Profile's `guideword` or `can_do_statement` to map `grammar_prerequisites`.

---

## 6. Theme & Morphology Integration

Grammar metadata interacts with existing layers:
- **CEFR Verification**: A chunk's grammar prerequisite must not have a CEFR difficulty greater than the chunk's own `cefr_level` (e.g., A2 chunk must not require C1 grammar).
- **Morphological Slot Expansion**: If a slot requires a verb (`{verb}`), the morphology layer provides inflected forms (e.g. `drives`, `driving`, `driven`) to check grammar-slot agreement.

---

## 7. Roadmap Recommendation

The following progression is recommended:

1. **`ULGA-S6H_ChunkGrammarMetadata_Implementation_Fix`**
   - *Scope*: Implement the rule parser and write the compilation metadata into `chunk_nodes.json`.
2. **`ULGA-S6I_SentencePatternAuthority_DesignScan`**
   - *Scope*: Design the sentence patterns authority based on compiled pattern seeds.

---

## 8. Forbidden Actions Check

- **Modified chunk_nodes.json?** **No**
- **Modified chunk_vocabulary_edges.json?** **No**
- **Modified chunks source / safe layer?** **No**
- **Created chunk-grammar edges?** **No**
- **Created chunk-theme edges?** **No**
- **Created chunk-morphology edges?** **No**
- **Created chunk-chunk edges?** **No**
- **Modified grammar graph?** **No**
- **Modified theme / morphology / vocabulary graph?** **No**
- **Created learner_state?** **No**
- **Implemented planner / recommendation / learning path?** **No**
- **Modified runtime?** **No**

---

## 9. Final Verdict

**Final Verdict: PASS**

All design goals met. The grammar metadata architecture, assessment counts, and schema boundaries have been successfully defined. No files were modified.

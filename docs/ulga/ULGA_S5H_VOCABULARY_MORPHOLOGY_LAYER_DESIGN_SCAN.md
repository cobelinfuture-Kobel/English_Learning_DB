# ULGA-S5H Vocabulary Morphology Layer Design Scan Report

This report presents the architectural scan and graph schema design for the **Vocabulary Morphology Layer** in the Universal Learning Graph Architecture (ULGA).

---

## 1. Core Architectural Decision: Vocabulary Subsystem vs. Independent Authority

We analyze whether the Morphology Layer should be built as a **Vocabulary Subsystem** (a dependent feature inside the Vocabulary Layer) or as an **Independent Authority** (a separate graph sub-layer with its own rules and metadata engine).

### 1.1 Comparative Analysis

| Dimension | A. Vocabulary Subsystem | B. Independent Authority (Recommended) |
| :--- | :--- | :--- |
| **Ownership** | Owned by the Vocabulary Layer; morphology properties are stored directly on Vocabulary Nodes (e.g. metadata tags). | Owned by a standalone Morphology Authority that defines roots, affixes, and derivation rules. |
| **Scalability** | **Low.** Every time vocabulary sets are expanded or new corpora are imported, the morphology tagger must be run again on all nodes. | **High.** The Morphology Authority operates on general lexical rules. New vocab lists simply anchor to existing roots. |
| **Maintenance** | **Difficult.** Changing a morphological rule (e.g. affix definition) requires mutating 15,696 vocabulary nodes. | **Easy.** Morphological rules and stem dictionaries are maintained in one place. Only the relationship resolver updates. |
| **Planner Value** | **Limited.** The planner can only query defined vocabulary attributes. It cannot easily reason about lexical gaps. | **Extremely High.** The planner can calculate cognitive relations, generalize affix rules, and estimate learning loads of unmapped words. |

### 1.2 Recommendation

We strongly recommend **B. 獨立 Authority (Independent Authority)**. 

Morphology represents linguistic rules (invariants) that apply universally to lexemes, whereas vocabulary lists are pedagogically structured and level-dependent. Keeping the **Morphology Authority** independent ensures that:
1. **Clean Separation of Concerns**: Vocabulary represents semantic senses; Morphology represents lexical structures and word-formation rules.
2. **Cross-Layer Support**: The same Morphology Authority can resolve word families for vocabulary nodes, words contained in chunks, and vocabulary items found in grammar example sentences.
3. **Immutability Protection**: We avoid mutating the 15,696 vocabulary nodes whenever morphology logic is refined.

---

## 2. Morphology Taxonomy Design

We analyze which morphological categories should be represented in the ULGA graph and how they should be integrated.

### 2.1 Inflection (屈折變化)
* **Example**: *play* $\rightarrow$ *plays, playing, played*
* **Analysis**: Standard inflections represent grammatical variation without changing the lemma or the part of speech. 
* **ULGA Integration**: Standard inflections **should NOT** enter the Vocabulary Layer as separate nodes to avoid bloating the graph (which would add ~50,000+ redundant nodes). Instead, standard inflections are handled by the **Grammar Layer** (e.g. past tense rules, noun plurals). However, if an inflected form undergoes category conversion (e.g., *moving* B2 adjective, *painting* A2 noun), it **must** be mounted as a distinct vocabulary node and linked via morphology edges to the base lemma.

### 2.2 Derivation (派生變化)
* **Example**: *play* $\rightarrow$ *player* (noun), *playful* (adjective)
* **Analysis**: Derivations create new lemmas, often changing the part of speech and shifting the meaning and CEFR level.
* **ULGA Integration**: **Must enter ULGA**. They must be represented as separate vocabulary nodes and connected via directed morphological edges (e.g. `player --derived_from--> play`).

### 2.3 Prefix (前綴)
* **Example**: *happy* $\rightarrow$ *unhappy*; *possible* $\rightarrow$ *impossible*
* **Analysis**: Prefixes modify meaning (e.g. negation, repetition) and are critical signals of word difficulty shift.
* **ULGA Integration**: **Must enter ULGA**. The derived word (e.g. *impossible*) exists as a node and is linked to the base (*possible*). The prefix (e.g. `im-`) is stored as metadata on the relationship.

### 2.4 Suffix (後綴)
* **Example**: *teach* $\rightarrow$ *teacher*; *act* $\rightarrow$ *action*; *beauty* $\rightarrow$ *beautiful*
* **Analysis**: Suffixes typically change the grammatical class (POS) and are highly productive in academic vocabulary.
* **ULGA Integration**: **Must enter ULGA**. The suffix relation (e.g. `-er`, `-tion`) is mounted as metadata on the directed edge.

### 2.5 Compound (複合詞)
* **Example**: *classroom*, *football*, *birthday*
* **Analysis**: Compounds combine two free morphemes (*class* + *room*). If a learner knows both constituent words, the learning load of the compound is minimized.
* **ULGA Integration**: **Must enter ULGA**. The compound word is represented as a vocabulary node, and it points to both constituents using `compound_of` relationships.

---

## 3. Morphology Node Strategy: MorphologyNode vs. Direct Edges

We evaluate two graph modeling structures to represent word families.

### 3.1 Structural Comparison

* **Option A: MorphologyNode (Hub-and-Spoke)**
  * Create a dedicated node type `morphology` (e.g. `word_family:play`).
  * All family members connect to this hub: `vocab:play --belongs_to--> word_family:play`, `vocab:player --belongs_to--> word_family:play`.
* **Option B: Direct Vocabulary $\leftrightarrow$ Vocabulary (Directed Tree/DAG)**
  * Connect vocabulary nodes directly to their immediate parent: `vocab:player --derived_from--> vocab:play`, `vocab:playful --derived_from--> vocab:play`.

### 3.2 Tradeoff Matrix

| Metric | Option A: MorphologyNode Hub | Option B: Direct Vocab Edges |
| :--- | :--- | :--- |
| **Graph Complexity** | **Low.** $O(N)$ edges. Easy to group and query. | **Medium.** $O(N)$ tree edges. Requires traversing path recursively. |
| **Scalability** | **High.** Adding new nodes requires linking to one hub. | **Medium.** Requires identifying the exact parent lemma. |
| **Planner Usefulness** | **Excellent.** Can track mastery metrics directly on the family hub node. | **Excellent.** Represents the precise pedagogical progression path. |

### 3.3 Recommendation

We recommend a **Hybrid Model**:
1. **MorphologyNode Hubs** (`node_type: morphology`): Used to define the boundary of a **Word Family**. All vocabulary nodes belonging to the family point to this hub using `belongs_to` edges. This allows the planner to query all family members in a single step and aggregate family mastery.
2. **Direct Vocabulary $\rightarrow$ Vocabulary Edges**: Use `derived_from` (implemented via the `supports` edge type under the S2 contract) to specify the step-by-step progression (e.g. *act* $\rightarrow$ *active* $\rightarrow$ *activity* $\rightarrow$ *activate* $\rightarrow$ *activation*).

---

## 4. Morphology Edge Design

Under the strict constraints of the **ULGA-S2 Schema Contract**, the permitted `edge_type` values are:
`prerequisite`, `supports`, `belongs_to`, `unlocks`, `reviews`, `contrasts_with`, `uses`, `contains`, `spiral_to`, `assesses`.

To represent morphological relationships without violating the schema, we design the following mapping strategy:

### 4.1 Formal Graph Edges (ULGA-S2 Compliant)

1. **Word Family Grouping (`belongs_to`)**
   * **Source**: `vocabulary:play:v_7545` $\rightarrow$ **Target**: `morphology:play` (Hub)
   * **Role**: Groups all senses and derivations into a single cognitive family unit.
2. **Derivational Progression (`supports`)**
   * **Source**: `vocabulary:player:v_6483` $\rightarrow$ **Target**: `vocabulary:play:v_7545`
   * **Role**: Indicates that mastering the base verb *play* supports the acquisition of the noun *player*.
3. **Compound Membership (`contains`)**
   * **Source**: `vocabulary:classroom` $\rightarrow$ **Target**: `vocabulary:class` & `vocabulary:room`
   * **Role**: Indicates structural composition.

### 4.2 Edge Metadata Payload Design

The relationship details are stored in the edge's `metadata` block to enable granular planner reasoning:

```json
{
  "id": "edge:vocab_morph_supports_v_6483_v_7545",
  "source_node_id": "vocabulary:player:v_6483",
  "target_node_id": "vocabulary:play:v_7545",
  "edge_type": "supports",
  "authority_source": {
    "source_name": "Vocabulary Morphology Authority",
    "derivation": "rule_based"
  },
  "confidence": {
    "value": 1.0,
    "method": "rule_based"
  },
  "version": {
    "contract": "ULGA-S2"
  },
  "metadata": {
    "relationship_type": "derived_from",
    "affix_type": "suffix",
    "affix_form": "-er",
    "morphological_category": "agent_noun",
    "spelling_shift": false,
    "semantic_drift_score": 0.05
  }
}
```

---

## 5. Word Family Analysis & Statistics

A read-only statistical analysis was conducted on the 15,696 mounted vocabulary nodes.

### 5.1 Basic Metrics Summary
* **Total Mounted Vocabulary Nodes**: 15,696
* **Unique Lemmas**: 9,751
* **Polysemous Lemmas**: 3,517 (lemmas with multiple senses/entries)
* **Average Family Size (Target Sample)**: 13.62 nodes per family
* **Estimated Total Word Families**: ~2,800 families

### 5.2 Target Word Families Detailed Scan

The following table displays the actual nodes, parts of speech, CEFR levels, and NGSL frequency ranks for our target candidate families:

| Base Lemma | Total Nodes | Family Members (CEFR Progression) | Key Insights |
| :--- | :---: | :--- | :--- |
| **play** | 12 | `play` (verb, A1, rank 213)<br>`player` (noun, A1, rank 418)<br>`play` (noun, A2, rank 1003)<br>`playground` (noun, A2, rank 1951)<br>`play` (verb, B1, rank 2611)<br>`play` (noun, B2, rank 5469) | Solid high-frequency core. Illustrates category conversion (verb $\leftrightarrow$ noun) and compounding (*playground*). |
| **teach** | 5 | `teacher` (noun, A1, rank 367)<br>`teach` (verb, A1, rank 378)<br>`teach` (verb, A2, rank 1276)<br>`teach` (verb, B1, rank 2980)<br>`teaching` (noun, B1, rank 2981) | *Teacher* (A1) is actually ranked slightly higher in frequency than the base verb *teach* (A1), showing the value of independent POS nodes. |
| **happy** | 9 | `happy` (adj, A1, rank 374)<br>`happy` (adj, A2, rank 1262)<br>`unhappy` (adj, A2, rank 1859)<br>`happiness` (noun, B1, rank 4104)<br>`happily` (adv, B1, rank 4275)<br>`unhappiness` (noun, B2, rank 8303)<br>`happily` (adv, C1, rank 10419) | Perfect example of prefix negation (`un-`) and suffix adverbial/nominal derivation (`-ly`, `-ness`, `-ness` negation). |
| **act** | 32 | `actually` (adv, A2, rank 1113)<br>`activity` (noun, A2, rank 1220)<br>`actor` (noun, A2, rank 1587)<br>`action` (noun, B1, rank 2920)<br>`act` (verb, B1, rank 2961)<br>`active` (adj, B1, rank 3551)<br>`actual` (adj, B2, rank 6417)<br>`reaction` (noun, B2, rank 6345)<br>`interact` (verb, B2, rank 7494)<br>`interaction` (noun, C1, rank 9970)<br>`transaction` (noun, C1, rank 10032)<br>`action` (noun, C2, rank 12073) | The largest candidate family. Demonstrates extensive prefixation (`re-`, `inter-`, `trans-`) and multi-stage suffix derivations. |
| **possible** | 12 | `possible` (adj, A1, rank 291)<br>`possibly` (adv, A2, rank 1580)<br>`possible` (adj, B1, rank 2739)<br>`possibility` (noun, B1, rank 3301)<br>`impossible` (adj, B1, rank 3549)<br>`impossible` (adj, C2, rank 12284)<br>`impossibility` (noun, C2, rank 13826) | Clearly illustrates how negative prefixation shifts CEFR difficulty levels (possible A1 $\rightarrow$ impossible B1 $\rightarrow$ impossibility C2). |
| **help** | 10 | `help` (verb, A1, rank 191)<br>`help` (noun, A2, rank 981)<br>`helpful` (adj, B1, rank 3715)<br>`helper` (noun, B2, rank 8207)<br>`unhelpful` (adj, B2, rank 8349)<br>`helpless` (adj, C1, rank 10827)<br>`unhelpful` (adj, C1, rank 11065) | Highlights adjectival suffixes (`-ful`, `-less`) and prefix modifications (*unhelpful*). |
| **move** | 13 | `move` (verb, A2, rank 1043)<br>`move` (verb, B1, rank 2650)<br>`remove` (verb, B1, rank 3382)<br>`moving` (adj, B2, rank 5937)<br>`movement` (noun, B2, rank 5984)<br>`remove` (verb, B2, rank 6204)<br>`move` (noun, C1, rank 9542) | Demonstrates prefixation (*remove*) and suffix derivation (*movement*, *moving*). |
| **use** | 16 | `use` (verb, A1, rank 125)<br>`use` (noun, A2, rank 898)<br>`useful` (adj, A2, rank 1432)<br>`use` (verb, B1, rank 2481)<br>`user` (noun, B1, rank 3424)<br>`useless` (adj, B1, rank 4327)<br>`usage` (noun, C1, rank 10388)<br>`misuse` (noun/verb, C1, rank 10882)<br>`usefulness` (noun, C1, rank 10928)<br>`useless` (adj, C2, rank 12993) | Includes prefixation (*misuse*), multiple suffixes (*usefulness*, *uselessness*), and category conversion. |

### 5.3 Word Family Value to Learning Pathways
Word families reduce the cognitive load of vocabulary acquisition. Once a learner understands a base root (e.g. *help*) and standard morphological affixes (e.g. `-ful`, `un-`), the cost of acquiring related terms (e.g. *helpful*, *unhelpful*) is drastically reduced. The planner can leverage this to group vocabulary reviews, recycle stems in reading exercises, and offer a "cognitive discount" for family members.

---

## 6. CEFR Alignment vs. Morphology Progression

### 6.1 CEFR Morphology Progression Example
Morphological derivation creates a natural ladder of CEFR levels:
$$\text{play (A1)} \xrightarrow{\text{agentive -er}} \text{player (A2)} \xrightarrow{\text{adjectival -ful}} \text{playful (B1)} \xrightarrow{\text{nominal -ness}} \text{playfulness (C1)}$$

### 6.2 Learning Path Signal vs. Prerequisite
* **Decision**: Morphology should be treated as a **Learning Path Signal** (a soft scheduling boost) rather than a **Prerequisite** (a hard block).
* **Rationale**: A learner does not strictly need to master the verb *teach* before using the noun *teacher* (e.g., they can easily learn *teacher* at A1 in a school context). However, once *teach* is mastered, the learning curve of *teacher* is near zero. If we enforce morphology as a hard prerequisite, we break natural thematic mapping and situational learning. 
* **Planner Rule**: If a base lemma is mastered, apply a **50% cognitive weight reduction** (faster learning speed estimation) to its derived family members.

---

## 7. Theme Layer Integration

### 7.1 The Theme Contamination Risk
Different members of the same word family belong to completely different semantic categories:
* *play* (verb) $\rightarrow$ **Sports / Entertainment**
* *playground* (noun) $\rightarrow$ **School / Daily Life**
* *playwright* (noun) $\rightarrow$ **Arts / Literature**

If theme nodes are connected directly to word family hubs, or if theme edges are inherited down the family tree, themes will contaminate each other (e.g. labeling *playground* under *Entertainment*).

### 7.2 Coexistence Model
To avoid theme contamination:
1. **Sense-Level Anchoring**: Theme membership edges (`belongs_to`) must point directly to specific **Vocabulary Node IDs** (representing distinct senses/POS), never to Morphology Nodes or base lemmas.
2. **Layer Separation**: The Morphology Layer only connects vocabulary nodes to each other (`supports`) and to Morphology Hubs (`belongs_to`). The Theme Layer connects vocabulary nodes to Theme Catalog Nodes. There are **zero** direct edges between Theme Nodes and Morphology Nodes.

```
                  [Theme: Sports]          [Theme: Education]
                         │                         │
                     belongs_to                belongs_to
                         │                         │
                         ▼                         ▼
  [Morphology Hub] ◄── belongs_to ── [vocab:play]   [vocab:playground] ── belongs_to ──► [Morphology Hub]
                                           │                 │
                                           └──── supports ───┘
```

---

## 8. Chunk Layer Integration

Collocations and multi-word expressions in the Chunk Layer can be systematically mapped and reinforced using the Morphology Layer.

### 8.1 Chunk Scaffolding
Consider the chunks:
* *play football* (verb phrase) $\rightarrow$ uses base verb *play*
* *football player* (noun phrase) $\rightarrow$ uses derived noun *player*
* *professional player* (noun phrase) $\rightarrow$ uses derived noun *player*

### 8.2 Enhancing the Chunk Graph
1. **Lexical Recycling**: When the learner masters *play football* and is subsequently introduced to the derivation *player*, the planner can schedule the chunk *football player* immediately after, showing the syntactic transformation.
2. **Structural Bridging**: Chunks connect to vocabulary nodes via `uses` edges. The morphology layer connects vocabulary nodes via `supports` edges. By combining these layers, the system can automatically suggest sentence pattern transformations (e.g. *"They play football"* $\rightarrow$ *"They are football players"*).

---

## 9. Antigravity Value Analysis

Integrating a formal Morphology Layer empowers the Antigravity Planner with four core capabilities:

1. **Vocabulary Expansion (詞彙擴展)**: Systematically recommends derived words to learners who have mastered a base form. If a learner masters *possible* (A1), the system prioritizes *impossible* (B1) and *possibility* (B1) over unrelated words of the same level.
2. **Lexical Recycling (詞彙循環)**: During reviews, the system creates exercises that contrast word family members (e.g., matching *happy*, *unhappy*, *happily*, *happiness* into correct grammatical slots).
3. **Review Planning (複習規劃)**: Memory decays slower for family members. If a user practices *player*, the memory strength of *play* receives a passive boost. The planner can extend the spaced repetition interval of the base word, reducing review fatigue.
4. **Family-Based Learning (家族式學習)**: Groups learning sessions by family roots, allowing high-aptitude learners to acquire up to 10 vocabulary items in a single root-based module.

---

## 10. Layering Strategy

To manage implementation complexity and minimize noise, the Morphology Layer is divided into three logical phases:

### 10.1 Layer A: Core Morphology (核心詞族)
* **Scope**: Highly regular, high-frequency affixes covering A1–B1. Low ambiguity and zero spelling changes.
* **Affixes**: `-er` (agent), `-ness` (state), `-ly` (adverb), `un-`/`im-` (negation), `-ful` (adjective).
* **Examples**: *teacher, player, happiness, happily, unhappy, impossible, useful*.
* **Size**: ~1,800 edges.
* **Risk**: **Very Low.** High pedagogical consensus.

### 10.2 Layer B: Extended Morphology (擴展詞族)
* **Scope**: Intermediate derivations (B1-B2) with spelling shifts or minor semantic adjustments.
* **Affixes**: `-tion`/`-sion` (action), `-ity` (quality), `-ive` (adjective), `-ment` (state), `re-` (repetition), `dis-` (reversal).
* **Examples**: *activity, reaction, movement, possibility, disagree, reusable*.
* **Size**: ~3,000 edges.
* **Risk**: **Medium.** Requires spelling normalization during matching (e.g., *happy* $\rightarrow$ *happily*, *act* $\rightarrow$ *activity*).

### 10.3 Layer C: Advanced Morphology (進階學術詞族)
* **Scope**: Advanced/Academic (C1-C2) vocabulary, multi-stage derivations, and classical Greek/Latin roots.
* **Affixes**: `-ize`/`-ise`, `-ify`, `trans-`, `pro-`, `co-`, `-al`, `-ism`.
* **Examples**: *activation, transaction, institutional, productivity, incomprehensible*.
* **Size**: ~2,500 edges.
* **Risk**: **High.** Higher semantic drift (e.g. *department* vs. *depart*). Needs strict lexical validation rules to avoid incorrect relationships.

---

## 11. Authority Readiness Assessment

We evaluate the readiness of the various ULGA sub-components for the morphology layer:

| Sub-component | Status | Rationale |
| :--- | :---: | :--- |
| **Morphology Layer** | **READY** | Vocabulary sense nodes are mounted, and the family taxonomy and mapping rules are fully designed. |
| **Chunk Authority** | **PARTIAL** | Chunk lists and POS classes exist, but they lack formal integration mapping with vocabulary morphology anchors. |
| **Sentence Pattern Authority** | **NOT READY** | Sentence pattern templates are not yet structured or loaded. |
| **Antigravity Planner** | **PARTIAL** | The planner can consume vocabulary levels and ranks, but cannot process word family groupings or cognitive discounts until edges are generated. |
| **Gate Engine** | **PARTIAL** | The gate architecture is clear, but validation rules require morphology edge files to execute. |

---

## 12. Roadmap Recommendation

We propose the following roadmap for the upcoming sprints:

```mermaid
gantt
    title ULGA Vocabulary Morphology Layer & Integration Roadmap
    dateFormat  YYYY-MM-DD
    section Morphology Layer
    S5I: Implementation Fix          :active, s5i, 2026-06-16, 7d
    S5J: QA Audit                     :s5j, after s5i, 5d
    section Next Authority
    Chunk Layer Implementation        :s6a, after s5j, 10d
    Sentence Pattern Implementation   :s7a, after s6a, 12d
```

### 12.1 Recommended Next Sprints
* **ULGA-S5I_VocabularyMorphologyLayer_Implementation_Fix**: Write the rules engine to extract word families and generate S2-compliant `belongs_to` and `supports` edges.
* **ULGA-S5J_VocabularyMorphologyLayer_QA_Audit**: Verify graph structure, test family boundaries, and ensure no theme contamination or cycle loops exist.

### 12.2 Next Integration Priority: Chunk vs. Sentence Pattern
We strongly recommend implementing the **Chunk Layer** next.
* **Pedagogical Rationale**: Language acquisition progresses from **Words (Vocabulary)** $\rightarrow$ **Phrases (Chunks)** $\rightarrow$ **Sentences (Sentence Patterns)**. Chunks directly anchor to vocabulary lemmas. By building the Chunk Layer, we complete the lexical block of the graph before moving on to syntax. 
* **Technical Rationale**: Sentence patterns require slot-filling variables that reference both vocabulary parts-of-speech and chunk types. Implementing chunks first provides the necessary inputs for sentence patterns.

---

## 13. Forbidden Actions Check

We confirm that this scan was strictly read-only and did not violate any project boundaries:
1. **Modified `vocabulary.json`?** $\rightarrow$ **No.**
2. **Modified `vocabulary_nodes.json`?** $\rightarrow$ **No.**
3. **Modified `theme_nodes.json`?** $\rightarrow$ **No.**
4. **Modified `vocabulary_theme_edges.refined.json`?** $\rightarrow$ **No.**
5. **Modified grammar graph files?** $\rightarrow$ **No.**
6. **Modified chunk files?** $\rightarrow$ **No.**
7. **Created `learner_state` or planner models?** $\rightarrow$ **No.**
8. **Created real morphology edges in the graph?** $\rightarrow$ **No.**

---

## 14. Final Verdict

**Final Verdict**: **PASS**

All 14 design points, taxonomy analyses, word family scans, edge schemas, and roadmap suggestions have been successfully evaluated. The system is fully ready for S5I implementation.

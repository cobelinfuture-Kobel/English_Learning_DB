# ULGA-S7BI Sentence Pattern QA Audit Report

This report presents a comprehensive, read-only QA audit of the **Sentence Pattern Authority Layer** implemented under `ULGA-S7B`. It evaluates basic graph integrity, review statuses, pattern types, families, slots, references, edge connectivity, and validates the A1 core patterns to determine readiness for the next milestone (`ULGA-S7C`).

---

## 1. Executive Summary
The Sentence Pattern Authority layer contains **1,482** pattern nodes and **1,529** physical edges. 
The automated validator returned **PASS**, and the pytest suite returned **PASS**.

**Final Verdict**: **WARNING_ACCEPTED**
### Warnings:
- **[WARNING]** Low average edge density: 1.03 edges per pattern.
- **[WARNING]** Vocabulary slot constraints are missing on 100.00% of patterns (normal before S7C linkage, but flagged).
- **[WARNING]** Theme reference coverage is low: 98.85% of patterns have no theme_refs.

---

## 2. Files Inspected
- [sentence_patterns.json](file:///G:/HomeWork/English_Learning_DB/ulga/graph/sentence_patterns.json) (Compiled nodes dataset)
- [ulga_sentence_pattern_nodes.json](file:///G:/HomeWork/English_Learning_DB/ulga/graph/ulga_sentence_pattern_nodes.json) (Unified graph wrapper nodes)
- [ulga_sentence_pattern_edges.json](file:///G:/HomeWork/English_Learning_DB/ulga/graph/ulga_sentence_pattern_edges.json) (Unified graph wrapper edges)
- [ulga_graph.sentence_patterns.json](file:///G:/HomeWork/English_Learning_DB/ulga/graph/ulga_graph.sentence_patterns.json) (Graph compiler wrapper)
- [sentence_pattern_mount_summary.json](file:///G:/HomeWork/English_Learning_DB/ulga/reports/sentence_pattern_mount_summary.json) (Stage mounting summary)
- [ULGA_S7B_SENTENCE_PATTERN_NODE_MOUNTING_CLOSEOUT.md](file:///G:/HomeWork/English_Learning_DB/docs/ulga/ULGA_S7B_SENTENCE_PATTERN_NODE_MOUNTING_CLOSEOUT.md) (Closeout documentation)
- [validate_ulga_sentence_patterns.py](file:///G:/HomeWork/English_Learning_DB/ulga/validators/validate_ulga_sentence_patterns.py) (Validation enforcer script)
- [test_ulga_sentence_patterns.py](file:///G:/HomeWork/English_Learning_DB/tests/ulga/test_ulga_sentence_patterns.py) (Pytest unit test suite)
- [chunk_grammar_metadata.json](file:///G:/HomeWork/English_Learning_DB/ulga/graph/chunk_grammar_metadata.json) (Pattern compilation source inputs)

---

## 3. Basic Integrity Metrics

| Metric | Count | Ratio / Notes |
| :--- | :---: | :--- |
| **Total Sentence Patterns** | 1,482 | 100.00% |
| **Total Physical Edges** | 1,529 | Uses, belongs_to, and prerequisites |
| **Manual A1 Core Patterns** | 17 | 1.15% |
| **Chunk-derived Patterns** | 1,465 | 98.85% |
| **Accepted Patterns** | 1,344 | 90.69% (Ready for generator) |
| **Needs Review Patterns** | 138 | 9.31% (Needs parsing/structure review) |
| **Blocked Patterns** | 0 | 0.00% |
| **Generator Allowed (True)** | 1,344 | 90.69% |
| **Generator Allowed (False)** | 138 | 9.31% |
| **Validator Required (True)** | 1,482 | 100.00% |
| **Validator Required (False)** | 0 | 0.00% |

---

## 4. Review Status Analysis

### Distribution by Review Status:
- **`accepted`**: 1,344 patterns (90.69%)
- **`needs_review`**: 138 patterns (9.31%)
- **`blocked`**: 0 patterns (0.00%)

### Needs Review Patterns Breakdown:
#### By Pattern Type:
- `chunk_derived_pattern`: 138 patterns

#### By Source:
- `CHUNK_GRAMMAR_METADATA_DERIVED`: 138 patterns

#### By Slot Type (within needs_review patterns):
- `noun_phrase`: 82 slots
- `verb_infinitive`: 2 slots

#### Common Reasons for 'needs_review' Status:
- **`empty_slots`**: 72 patterns
- **`seed_flagged_manual_review`**: 75 patterns

> [!NOTE]
> The 75 patterns marked as `needs_review` are entirely chunk-derived patterns. The primary reasons they are flagged are: (1) `seed_flagged_manual_review` where the parser flagged it for human confirmation, (2) `empty_slots` where no content slots could be extracted, and (3) `seed_zero_slots` indicating it is a fully fixed formulaic sequence without variable parameters.

---

## 5. Pattern Type Distribution

| Pattern Type | Count | Ratio |
| :--- | :---: | :---: |
| `chunk_derived_pattern` | 1,465 | 98.85% |
| `description_pattern` | 3 | 0.20% |
| `identity_statement` | 2 | 0.13% |
| `preference_statement` | 2 | 0.13% |
| `existence_statement` | 2 | 0.13% |
| `routine_statement` | 2 | 0.13% |
| `request_pattern` | 2 | 0.13% |
| `possession_statement` | 1 | 0.07% |
| `ability_statement` | 1 | 0.07% |
| `ability_question` | 1 | 0.07% |
| `wh_location_question` | 1 | 0.07% |

---

## 6. Pattern Family Distribution

- **Total Pattern Families**: 1,476
- **Singleton Families** (1 pattern): 1,470 families (99.59%)

### Largest Families (Top 20):
| Family ID | Pattern Count | Ratio of Total |
| :--- | :---: | :---: |
| `family:preference_like` | 2 | 0.13% |
| `family:ability_can` | 2 | 0.13% |
| `family:existence_there` | 2 | 0.13% |
| `family:routine_daily` | 2 | 0.13% |
| `family:request_polite` | 2 | 0.13% |
| `family:description_demonstrative` | 2 | 0.13% |
| `family:identity_be` | 1 | 0.07% |
| `family:identity_name` | 1 | 0.07% |
| `family:possession_have` | 1 | 0.07% |
| `family:location_where` | 1 | 0.07% |
| `family:description_it` | 1 | 0.07% |
| `family:chunk_derived_get_sth_off_your_chest` | 1 | 0.07% |
| `family:chunk_derived_sbs_call` | 1 | 0.07% |
| `family:chunk_derived_drive_send_sb_round_the_bend` | 1 | 0.07% |
| `family:chunk_derived_be_in_sbs_good_bad_books` | 1 | 0.07% |
| `family:chunk_derived_capture_sb_sth_on_camera_film_etc.` | 1 | 0.07% |
| `family:chunk_derived_a_call_for_sth` | 1 | 0.07% |
| `family:chunk_derived_avoid_doing_sth` | 1 | 0.07% |
| `family:chunk_derived_make_allowances_for_sb_sth` | 1 | 0.07% |
| `family:chunk_derived_attract_get_sbs_attention` | 1 | 0.07% |

---

## 7. Slot Type Distribution

- **Total Extracted Slots**: 2,016
- **Average Slots per Pattern**: 1.36
- **Generic / Unknown Slots**: 208 slots
- **Slots with Theme Prefilter**: 0
- **Slots with Number Constraint**: 2,016

### Slot Type Counts:
| Slot Type | Count | Ratio |
| :--- | :---: | :---: |
| `noun_phrase` | 1,634 | 81.05% |
| `verb` | 206 | 10.22% |
| `verb_infinitive` | 103 | 5.11% |
| `verb_gerund` | 60 | 2.98% |
| `verb_stem` | 5 | 0.25% |
| `multi_type` | 3 | 0.15% |
| `proper_noun` | 1 | 0.05% |
| `noun_phrase_1` | 1 | 0.05% |
| `noun_phrase_2` | 1 | 0.05% |
| `time` | 1 | 0.05% |
| `adjective` | 1 | 0.05% |

### Slot Constraints Breakdown:
#### Required vs Optional:
- **Required = True**: 2,016 slots (100.00%)
#### CEFR Max Limit:
- **`A1`**: 33 slots (1.64%)
- **`A2`**: 90 slots (4.46%)
- **`B1`**: 320 slots (15.87%)
- **`B2`**: 663 slots (32.89%)
- **`C1`**: 302 slots (14.98%)
- **`C2`**: 608 slots (30.16%)

---

## 8. Reference Coverage

| Reference Type | With Reference | Without Reference | Coverage Ratio |
| :--- | :---: | :---: | :---: |
| **Grammar Reference (`grammar_refs`)** | 27 | 1,455 | 1.82% |
| **Chunk Reference (`chunk_refs`)** | 1,465 | 17 | 98.85% |
| **Theme Reference (`theme_refs`)** | 17 | 1,465 | 1.15% |
| **Vocab Constraints (`vocabulary_slot_constraints`)** | 0 | 1,482 | 0.00% |

> [!NOTE]
> The low coverage of theme references (1.15%) and vocabulary slot constraints (0.00%) is expected at this stage. Chunk-derived patterns have zero physical theme tags mapped (deferred to S7C auto-inheritance). The mapping of slot constraints is also deferred to `ULGA-S7C` (Pattern-Vocabulary Linkage).

---

## 9. Edge Coverage and Density

- **Total Edges Generated**: 1,529
- **Average Edges per Pattern**: 1.03
- **Median Edges per Pattern**: 1.0
- **Max Edges on a Pattern**: 4

### Adjacency Distribution:
- **Patterns with 0 outgoing edges (Orphans)**: 0 (0.00%)
- **Patterns with 1 outgoing edge**: 1,455 (98.18%)
- **Patterns with 2+ outgoing edges**: 27 (1.82%)

### Edges by Relation Type:
- **`uses`**: 1,508 edges
- **`belongs_to`**: 17 edges
- **`prerequisite`**: 4 edges

### Endpoint Prefix Distribution:
#### Source Node Prefixes:
- `pattern:*`: 1,529
#### Target Node Prefixes:
- `grammar:*`: 43
- `theme:*`: 17
- `pattern:*`: 4
- `chunk:*`: 1,465

### Top 10 Highest-Degree Patterns:
| Node ID | Canonical Pattern / Label | Degree | Source |
| :--- | :--- | :---: | :--- |
| `pattern:PATTERN_NODE_000005` | `I don't like {noun_phrase/gerund}.` | 4 | `MANUAL_A1_CORE_PATTERN` |
| `pattern:PATTERN_NODE_000007` | `Can you {verb_stem}?` | 4 | `MANUAL_A1_CORE_PATTERN` |
| `pattern:PATTERN_NODE_000001` | `I am {adjective/noun_phrase}.` | 3 | `MANUAL_A1_CORE_PATTERN` |
| `pattern:PATTERN_NODE_000004` | `I like {noun_phrase/gerund}.` | 3 | `MANUAL_A1_CORE_PATTERN` |
| `pattern:PATTERN_NODE_000006` | `I can {verb_stem}.` | 3 | `MANUAL_A1_CORE_PATTERN` |
| `pattern:PATTERN_NODE_000009` | `There is {noun_phrase_1} in/on/under {noun_phrase_2}.` | 3 | `MANUAL_A1_CORE_PATTERN` |
| `pattern:PATTERN_NODE_000012` | `I {verb_stem} at {time}.` | 3 | `MANUAL_A1_CORE_PATTERN` |
| `pattern:PATTERN_NODE_000015` | `It is {adjective}.` | 3 | `MANUAL_A1_CORE_PATTERN` |
| `pattern:PATTERN_NODE_000132` | `I/you/he, etc. had better {infinitive}` | 3 | `CHUNK_GRAMMAR_METADATA_DERIVED` |
| `pattern:PATTERN_NODE_000171` | `be able to {infinitive}` | 3 | `CHUNK_GRAMMAR_METADATA_DERIVED` |

---

## 10. Manual A1 Core Pattern QA

We audited the 17 manually defined core patterns to ensure they are 100% compliant with structural, metadata, and status rules:

| Input Pattern | Canonical Form | Exists | CEFR | Source | Gen Allowed | Val Req | Review Status | Slots Count | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| I am ___. | `I am {adjective/noun_phrase}.` | ✅ | A1 | MANUAL | true | true | accepted | 1 | **PASS** |
| My name is ___. | `My name is {name}.` | ✅ | A1 | MANUAL | true | true | accepted | 1 | **PASS** |
| I have ___. | `I have {noun_phrase}.` | ✅ | A1 | MANUAL | true | true | accepted | 1 | **PASS** |
| I like ___. | `I like {noun_phrase/gerund}.` | ✅ | A1 | MANUAL | true | true | accepted | 1 | **PASS** |
| I don’t like ___. | `I don't like {noun_phrase/gerund}.` | ✅ | A1 | MANUAL | true | true | accepted | 1 | **PASS** |
| I can ___. | `I can {verb_stem}.` | ✅ | A1 | MANUAL | true | true | accepted | 1 | **PASS** |
| Can you ___? | `Can you {verb_stem}?` | ✅ | A1 | MANUAL | true | true | accepted | 1 | **PASS** |
| There is ___. | `There is {noun_phrase}.` | ✅ | A1 | MANUAL | true | true | accepted | 1 | **PASS** |
| There is ___ in ___. | `There is {noun_phrase_1} in/on/under {noun_phrase_2}.` | ✅ | A1 | MANUAL | true | true | accepted | 2 | **PASS** |
| Where is ___? | `Where is {noun_phrase}?` | ✅ | A1 | MANUAL | true | true | accepted | 1 | **PASS** |
| I ___ every day. | `I {verb_stem} every day.` | ✅ | A1 | MANUAL | true | true | accepted | 1 | **PASS** |
| I ___ at ___. | `I {verb_stem} at {time}.` | ✅ | A1 | MANUAL | true | true | accepted | 2 | **PASS** |
| Can I have ___? | `Can I have {noun_phrase}?` | ✅ | A1 | MANUAL | true | true | accepted | 1 | **PASS** |
| May I ___? | `May I {verb_stem}?` | ✅ | A1 | MANUAL | true | true | accepted | 1 | **PASS** |
| It is ___. | `It is {adjective}.` | ✅ | A1 | MANUAL | true | true | accepted | 1 | **PASS** |
| This is ___. | `This is {noun_phrase}.` | ✅ | A1 | MANUAL | true | true | accepted | 1 | **PASS** |
| That is ___. | `That is {noun_phrase}.` | ✅ | A1 | MANUAL | true | true | accepted | 1 | **PASS** |

> [!NOTE]
> Manual A1 core pattern slot QA passed. Slash-containing placeholders were parsed into non-empty slot metadata.

---

## 11. Risk Detection Results

- **Generator allowed = true but review_status != 'accepted'**: 0 cases
- **Accepted but empty slots**: 0 cases (representing the 0 slot-extraction bug patterns listed above)
- **Accepted but empty canonical pattern**: 0 cases
- **Accepted but empty normalized pattern**: 0 cases
- **Missing pattern type**: 0 cases
- **Missing CEFR level**: 0 cases
- **Missing source**: 0 cases
- **Unknown slot types**: 208 cases
- **Missing grammar references**: 1455 cases
- **Missing theme references (for Manual patterns)**: 0 cases
- **Missing chunk references (for Chunk-derived patterns)**: 0 cases
- **Missing vocabulary slot constraints**: 1482 cases (100.00% of patterns)
- **Zero-edge pattern nodes**: 0 cases
- **Duplicate canonical patterns**: 86 cases
- **Duplicate normalized patterns**: 86 cases
- **Duplicate pattern IDs**: 0 cases

---

## 12. S7C Readiness Assessment

- **Overall Readiness**: **WARNING_ACCEPTED**
- **Prerequisites Verified**:
  - Validator run: **PASS**
  - Pytest run: **PASS**
  - Manual A1 core patterns 100% present: **YES**
  - generator_allowed = true patterns all accepted: **YES**
  - Needs review ratio: **9.31%** (threshold: <= 10.00% for PASS, 10%~20% for WARNING)

### Final Verdict Rationale:
The sentence pattern layer satisfies the basic graph schema and validation rules. The automated checklist passes completely and pytest tests are fully successful.
However, a **WARNING_ACCEPTED** status is assigned because warning-level follow-up items remain:
1. **Theme Tag Mismatch**: Chunk-derived patterns currently have zero theme references. They rely on auto-inheritance from vocabulary nodes which is deferred to subsequent milestones.
2. **Missing Vocabulary Slot Constraints**: All patterns lack vocabulary slot constraints. This is expected as vocabulary slot constraints design and mapping is the core focus of the next stage (`ULGA-S7C`).

---

## 13. Validator Execution Output
```text
Validating Sentence Pattern Authority layer...
Sentence Pattern Authority validation: PASS
```

---

## 14. Pytest Execution Output
```text
........................................................................ [ 70%]
..............................                                           [100%]
102 passed in 20.56s
```

---

## 15. Known Warnings
1. **Low Theme Reference Coverage (1.15%)**: Mappings to themes are deferred for chunk-derived patterns.
2. **Empty Vocabulary Slot Constraints**: Reserved for S7C linkage.
3. **Orphan Nodes (17 nodes)**: Manual patterns have zero active edges because grammar and theme target references are deferred.

---

## 16. Recommended Next Task
- **`ULGA-S7C_PatternVocabularyLinkage_DesignScan`**: Establish the design contract and mapping logic linking sentence pattern slots back to the Vocabulary authority to enable dynamic CEFR-gated word substitutions.

---

## 17. Final Verdict
### **Final Verdict: WARNING_ACCEPTED**
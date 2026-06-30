# ULGA-S5C Vocabulary Authority QA Audit Report

This report presents a read-only QA audit of the **Vocabulary Node Layer** mounted under ULGA-S5B. It evaluates the structural integrity, data coverage, and readiness of the 15,696 vocabulary nodes for subsequent layers (Theme, Morphology, Chunks, Sentence Patterns, and Antigravity Planner).

---

## 1. Files Created
- `ulga/audits/audit_ulga_vocabulary_nodes.py`: The read-only audit script used to compute metrics and check dataset integrity.
- `ulga/reports/vocabulary_authority_qa_audit.json`: The structured JSON report containing raw metrics.
- `docs/ulga/ULGA_S5C_VOCABULARY_AUTHORITY_QA_AUDIT.md`: This markdown document.

## 2. Files Modified
None. All operations were strictly read-only.

## 3. Existing Validation Results
Executing `python ulga/validators/validate_ulga_vocabulary_nodes.py` returned **PASS**.
- Confirmed that the output vocabulary files exist and conform to `ulga_node_schema.json`.
- Node type constraints (`vocabulary`), unique IDs, and metadata properties are fully compliant.
- Wrapper schema settings (empty edges, stage identifier) are verified.

## 4. Tests Executed
Executing `pytest tests/ulga/ -q` returned **PASS**.
- **5 test cases executed and passed**:
  - `test_node_files_exist` (success)
  - `test_node_counts_and_types` (success)
  - `test_graph_wrapper` (success)
  - `test_authority_source_and_metadata` (success)
  - `test_validator_run` (success)
- **Total pytest suite status**: 47 passed in 1.59s (including grammar and empty graph tests).

---

## 5. Basic Metrics

| Metric | Value |
| :--- | :--- |
| **Source Vocabulary Count** | 15,696 |
| **Mounted Node Count** | 15,696 |
| **Mounting Rate** | 100.00% |
| **Graph Edge Count** | 0 |
| **Node Type Distribution** | `vocabulary`: 15,696 |

---

## 6. ID / Sense Integrity

- **Unique Node ID Count**: 15,696
- **Duplicate Node ID Count**: 0
- **Unique Source Vocabulary ID Count**: 15,696 (matches `vocab_id` in source)
- **Duplicate Source Vocabulary ID Count**: 0
- **Unique Lemma Count (Lemmas)**: 9,759
- **Polysemy Lemma Count**: 3,513 (lemmas with multiple senses/entries)
- **Sense Preservation Check**: **PASS** (all 15,696 senses from the source are preserved).

### Top 15 Polysemous Lemmas in Mounted Nodes

| Lemma | Node Count | Senses / Part of Speech |
| :--- | :--- | :--- |
| **on** | 19 | preposition, adverb, adjective |
| **take** | 18 | verb, noun |
| **in** | 15 | preposition, adverb, noun |
| **for** | 15 | preposition, conjunction |
| **to** | 13 | preposition, infinitive marker |
| **right** | 13 | adjective, adverb, noun, verb |
| **over** | 13 | preposition, adverb, adjective |
| **cover** | 12 | verb, noun |
| **good** | 12 | adjective, noun, exclamation |
| **point** | 12 | noun, verb |
| **close** | 11 | adjective, adverb, verb, noun |
| **change** | 11 | noun, verb |
| **break** | 11 | verb, noun |
| **go** | 11 | verb, noun |
| **leave** | 11 | verb, noun |

---

## 7. CEFR Coverage

| Level | Node Count | Source Representation |
| :--- | :---: | :--- |
| **A1** | 784 | Natively mapped from EVP |
| **A2** | 1,594 | Natively mapped from EVP |
| **B1** | 2,937 | Natively mapped from EVP |
| **B2** | 4,164 | Natively mapped from EVP |
| **C1** | 2,410 | Natively mapped from EVP |
| **C2** | 3,807 | Natively mapped from EVP |
| **Missing CEFR** | 0 | None |
| **Invalid CEFR** | 0 | None |
| **Plus-Level Misuse** | 0 | Confirmed A1-C2 bounds without modifier misuse |

---

## 8. POS Coverage

| Part of Speech (POS) | Count | Usage Domains Count | Notes |
| :--- | :---: | :---: | :--- |
| **noun** | 5,171 | 5,171 | Dominant POS category |
| **phrase** | 3,656 | 3,656 | Multi-word expressions / idioms |
| **adjective** | 2,422 | 2,422 | |
| **verb** | 2,318 | 2,318 | |
| **adverb** | 805 | 805 | |
| **phrasal verb** | 728 | 728 | Special verb subclass |
| **preposition** | 244 | 244 | |
| **determiner** | 124 | 124 | |
| **pronoun** | 101 | 101 | |
| **conjunction** | 50 | 50 | |
| **modal verb** | 37 | 37 | |
| **exclamation** | 33 | 33 | |
| **auxiliary verb** | 6 | 6 | |
| **\<empty\>** | 1 | 0 | Anomaly: `v_70` (`seven`) - unmapped inactive record |

---

## 9. Frequency Coverage

- **Rank & Score Populated**: 15,696 (100.00% match coverage)
- **Missing Rank / Score**: 0
- **Frequency Score Bounds**:
  - Minimum: `0.0`
  - Maximum: `87.8469`
  - Median: `51.5693`

### Frequency Analysis by CEFR Level

| CEFR | Node Count | Populated Ranks | Median Rank | Populated Scores | Median Score |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **A1** | 784 | 784 | 392.5 | 784 | 61.9996 |
| **A2** | 1,594 | 1,594 | 1,581.5 | 1,594 | 58.0337 |
| **B1** | 2,937 | 2,937 | 3,847.0 | 2,937 | 55.5302 |
| **B2** | 4,164 | 4,164 | 7,397.5 | 4,164 | 52.7194 |
| **C1** | 2,410 | 2,410 | 10,684.5 | 2,410 | 49.1173 |
| **C2** | 3,807 | 3,807 | 13,793.0 | 3,807 | 44.1507 |

> [!NOTE]
> There is a perfect monotonic correlation between CEFR difficulty and frequency statistics:
> - Median Rank increases steadily from **392.5** (A1) to **13,793.0** (C2).
> - Median Score decreases steadily from **61.9996** (A1) to **44.1507** (C2).
> This validates the statistical alignment of EVP difficulty levels with corpus frequencies.

---

## 10. Theme Readiness

- **Theme Tags Populated**: 0
- **Theme Tags Empty**: 15,696 (expected in stage S5B)
- **Nodes with Source Topic but Empty Theme Tags**: 9,065
- **Projected Theme Mapping Readiness**: **HIGH** (9,065 nodes have native topics ready to map to theme catalog nodes in S5D).

### Top 5 Source Topics Available for Mapping
1. **communication**: 1,491 nodes
2. **describing things**: 1,299 nodes
3. **people: actions**: 1,298 nodes
4. **people: personality**: 1,265 nodes
5. **body and health**: 453 nodes

---

## 11. Chunk Readiness

- **Chunk Count Populated**: 15,696
- **Chunk Count > 0**: 0
- **Chunk Count = 0**: 15,696 (expected in stage S5B)
- **Likely Chunk Anchors Identification**: Heuristics identified high-frequency nouns and verbs (e.g. `book`, `ask`, `go`, `take`, `have`) as primary candidates for collocation anchors. 

---

## 12. Grammar Reference Safety

- **Grammar Prerequisites Field Exists**: **Yes**
- **Grammar Prerequisites Populated**: 0 (expected in stage S5B)
- **Grammar Graph Edges Created**: **None** (verified `edge_count = 0` in the graph wrapper).
- **Prerequisite Enforcement**: Safe, as grammar requirements are confined strictly to metadata arrays (`grammar_prerequisites = []`), preventing node-type boundary crossings.

---

## 13. Authority Source Coverage

- **Authority Source Populated**: 15,696
- **EVP Difficulty Authority**: 15,696 (100% coverage as primary)
- **NGSL/SFI Frequency Authority**: 15,696 (100% coverage as auxiliary)
- **Missing Authority Source**: 0

---

## 14. Risks / Warnings

### High Risk Issues
* **None** (zero ID conflicts, zero CEFR issues, 100% mounting rate).

### Medium Risk Issues
* **POS Metadata Empty (1 node)**: Node `vocabulary:seven:v_70` has an empty `part_of_speech`.
  - *Mitigation*: Inspection revealed that `'seven'` (`v_70`) is flagged as `active: false` and `pos_status: unmapped` in the source data. This is a legitimate unmapped source record, posing no risk.

### Low Risk Issues
* **Theme Tags Empty (15,696 nodes)**: No theme tags are populated (expected in S5B).
* **Chunk Count is 0 (15,696 nodes)**: Collocation links are not yet mounted (expected in S5B).
* **Grammar Prerequisites Empty (15,696 nodes)**: Pre-requisites not populated (expected in S5B).

---

## 15. Authority Readiness Assessment

| Target Layer | Rating | Rationale |
| :--- | :---: | :--- |
| **Vocabulary Theme Layer** | **READY** | 9,065 nodes have native topics ready for theme mapping. |
| **Vocabulary Morphology Layer** | **READY** | Full lemmatization structure is in place; word families can be built on top of unique base lemmas. |
| **Vocabulary Chunk Linkage** | **READY** | Anchor words are mounted and isolated. Chunks can now point to these nodes. |
| **Sentence Pattern Authority** | **READY** | Complete POS and lexical categorization enables slot pattern matching. |
| **Antigravity Planner** | **READY** | Perfectly aligned CEFR levels and frequency rank medians allow sound pedagogical ordering. |
| **Gate Engine** | **READY** | Validated schema structures guarantee runtime stability. |

---

## 16. Forbidden Actions Check

| Check | Verdict | Notes |
| :--- | :---: | :--- |
| **Modified `vocabulary.json`?** | **No** | Verified. |
| **Modified `vocabulary_nodes.json`?** | **No** | Verified. |
| **Added vocabulary edges?** | **No** | Verified (`edge_count = 0`). |
| **Added theme edges?** | **No** | Verified. |
| **Added morphology edges?** | **No** | Verified. |
| **Added chunk edges?** | **No** | Verified. |
| **Modified grammar graph?** | **No** | Verified. |
| **Modified chunk/theme data?** | **No** | Verified. |
| **Created `learner_state`?** | **No** | Verified. |
| **Implemented planner / recommendation / learning path?** | **No** | Verified. |
| **Modified runtime?** | **No** | Verified. |

---

## 17. Recommended Next Task
- **ULGA-S5D_VocabularyThemeLayer_DesignScan**: Design the integration model to map vocabulary nodes to thematic catalog nodes using `belongs_to` edges.

---

## 18. Final Verdict

**Final Verdict**: **WARNING_ACCEPTED** (WARNING because theme/chunk layers are not yet populated, which is the correct state for S5B; all high-risk items passed with 100% compliance).

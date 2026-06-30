# ULGA-S6B Chunk Node Mounting Closeout

This closeout documents the S6B implementation fix that mounts Chunk Authority into ULGA as first-class ChunkNode records.

Scope boundary: this task creates ChunkNodes only. It does not create chunk edges, planner logic, recommendation logic, learner state, learning path code, or runtime integration.

---

## 1. Files Created

- `ulga/build_ulga_chunk_nodes.py`
- `ulga/validators/validate_ulga_chunk_nodes.py`
- `tests/ulga/test_ulga_chunk_nodes.py`
- `ulga/graph/chunk_nodes.json`
- `ulga/graph/ulga_graph.chunk_nodes.json`
- `ulga/reports/chunk_node_mount_summary.json`
- `ulga/reports/chunk_node_duplicates.json`
- `docs/ulga/ULGA_S6B_CHUNK_NODE_MOUNTING_CLOSEOUT.md`

## 2. Files Modified

- None of the protected source authority files, existing ULGA graph layers, runtime files, planner files, recommendation files, or learner-state files were modified.

## 3. Source Chunk Count

- Raw source chunks from `chunk_profile/json/chunks.json`: `4,546`
- Generator-safe chunks from `chunk_profile/json/chunks_generator_safe.json`: `3,522`

## 4. Canonical Chunk Count

- Canonical mounted chunk count: `3,522`
- Equivalence-merged node count: `924`
- Non-merged safe canonical node count: `2,598`

## 5. Equivalence Groups Count

- Equivalence groups from `chunk_profile/json/chunk_equivalence_groups.json`: `924`
- All equivalence groups are represented through mounted canonical ChunkNode metadata.

## 6. Mounted Chunk Node Count

- Mounted ChunkNode count: `3,522`
- Graph wrapper `chunk_node_count`: `3,522`
- Graph wrapper `edge_count`: `0`

## 7. Duplicate Reduction Stats

Raw-to-mounted reduction:

- Raw chunks: `4,546`
- Mounted ChunkNodes: `3,522`
- Reduction count: `1,024`
- Reduction ratio: `22.5253%`

Duplicate normalized chunk finding:

- Duplicate normalized chunk surfaces: `192`
- Safe records involved in duplicate normalized surfaces: `477`

Policy:

- Exact duplicate/equivalence groups are canonicalized through the safe layer.
- Repeated normalized chunks with different EVP sense, guideword, level, topic, or usage class are preserved as separate ChunkNodes.
- For colliding normalized slugs, the generated `canonical_chunk` appends the stable `safe_chunk_id` to avoid merging distinct source senses.

Example:

- `chunk:insofar_as` for a unique canonical surface.
- `chunk:all_right:safe_chunk_000024` style IDs for repeated surfaces with distinct safe records.

## 8. Validation Results

Command executed:

```text
python ulga/validators/validate_ulga_chunk_nodes.py
```

Result:

```text
ULGA chunk nodes validation: PASS
```

Validator checks confirmed:

- `chunk_nodes.json` exists.
- `ulga_graph.chunk_nodes.json` exists.
- All node types are `chunk`.
- All node IDs are unique.
- `metadata.canonical_chunk` values are unique.
- `edge_count = 0`.
- Graph wrapper `edges = []`.
- No vocabulary, grammar, theme, morphology, or learner-state nodes exist in the chunk graph wrapper.
- All confidence values are `<= 1.0`.
- All confidence methods are `authority_mount`.

## 9. Tests Executed

Command executed:

```text
pytest tests/ulga/ -q
```

Result:

```text
77 passed in 25.63s
```

Builder command executed:

```text
python ulga/build_ulga_chunk_nodes.py
```

Builder result:

- Wrote `3,522` chunk nodes.
- Wrote graph wrapper with `0` edges.
- Wrote mount summary report.
- Wrote duplicate normalized chunk report.

## 10. Forbidden Actions Check

- Modified `chunks.json`? **No**
- Modified `chunks_generator_safe.json`? **No**
- Modified `chunk_equivalence_groups.json`? **No**
- Modified `chunk_usage_class_mapping.json`? **No**
- Created chunk edges? **No**
- Modified vocabulary graph? **No**
- Modified theme graph? **No**
- Modified morphology graph? **No**
- Modified grammar graph? **No**
- Created `learner_state`? **No**
- Implemented planner? **No**
- Implemented recommendation? **No**
- Implemented learning path? **No**
- Modified runtime? **No**

## 11. Known Limitations

- No Chunk-to-Vocabulary, Chunk-to-Theme, Chunk-to-Grammar, Chunk-to-Morphology, or Chunk-to-Chunk edges exist yet.
- `theme_hint` remains metadata only and must not be treated as ThemeNode authority.
- Repeated normalized chunk surfaces are not merged if they represent distinct EVP safe records or senses.
- Grammar-like chunks are not connected to grammar nodes in S6B.
- Runtime, planner, recommendation, and learning path components do not consume this layer yet.

## 12. Recommended Next Task

- `ULGA-S6C_ChunkVocabularyLinkage_DesignScan`

## 13. Final Verdict

**Final Verdict: PASS**

PASS conditions met:

- Chunk nodes created.
- Node count is greater than zero.
- Canonicalization through the safe layer is successful.
- Graph wrapper contains zero edges.
- Validator passed.
- Full ULGA pytest suite passed.
- No forbidden actions were performed.

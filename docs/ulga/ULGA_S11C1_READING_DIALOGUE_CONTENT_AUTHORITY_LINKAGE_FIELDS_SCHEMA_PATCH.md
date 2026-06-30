# ULGA-S11C1 Reading / Dialogue Content Authority Linkage Fields Schema Patch

## Preflight

- Baseline validator: `PASS`
- Baseline pytest: `PASS`
- Commands run:
  - `python ulga\validators\validate_reading_dialogue_content_authority_schema.py`
  - `python -m pytest tests\ulga\test_reading_dialogue_content_authority_schema.py -q`

## Files Inspected

- `docs/ulga/ULGA_S11C_READING_DIALOGUE_CONTENT_AUTHORITY_SCHEMA_IMPLEMENTATION.md`
- `docs/raz/RAZ_S6C_SEED_QUERY_AUTHORITY_LINKAGE_DESIGN_SCAN.md`
- `ulga/schemas/reading_content_authority_schema.json`
- `ulga/schemas/dialogue_content_authority_schema.json`
- `ulga/schemas/sample_reading_content_authority.json`
- `ulga/schemas/sample_dialogue_content_authority.json`
- `ulga/validators/validate_reading_dialogue_content_authority_schema.py`
- `tests/ulga/test_reading_dialogue_content_authority_schema.py`

## Files Modified

- `ulga/schemas/reading_content_authority_schema.json`
- `ulga/schemas/dialogue_content_authority_schema.json`
- `ulga/schemas/sample_reading_content_authority.json`
- `ulga/schemas/sample_dialogue_content_authority.json`
- `ulga/validators/validate_reading_dialogue_content_authority_schema.py`
- `tests/ulga/test_reading_dialogue_content_authority_schema.py`

## Files Intentionally Not Modified

- `reading_stub_authority`
- `ulga/query/**`
- `ulga/graph/**`
- `scheduler`
- `orchestrator`
- `runtime`
- `API routes`
- `RAZ_BookID.py`
- `BookID_prompt.txt`
- `tools/raz_normalized_tagging_pipeline.py`
- `raz_output_jsons/**`

## Schema Changes

- Added required top-level linkage fields for reading and dialogue:
  - `source_seed_refs`
  - `authority_refs`
  - `unresolved_authority_refs`
  - `authority_linkage_status`
  - `authority_linkage_policy_version`
  - `authority_linkage_warnings`
  - `authority_status`
  - `promotion_status`
  - `review_status`
  - `final_eligible`
- Added `$defs.source_seed_ref` with open string `source_level` support so future RAZ `G/H/I` values remain valid.
- Added nested `authority_refs` object while preserving existing flat refs for backward compatibility.
- Added `unresolved_authority_refs` structural placeholders and lifecycle enums without changing `content_type`, CEFR enum, required legacy fields, or `additionalProperties: false`.

## Sample Changes

- Reading sample now carries empty `source_seed_refs`, mirrored nested `authority_refs`, empty unresolved placeholders, and candidate-only linkage lifecycle fields.
- Dialogue sample now carries the same linkage structure with nested vocabulary/theme/grammar/pattern/chunk refs mirrored from existing flat fields.

## Validator Changes

- Preserved JSON Schema validation flow.
- Added shared linkage field checks, candidate boundary checks, fully-linked unresolved-ref guard, and nested-flat ref consistency checks.
- Tightened reading semantic validation to require non-empty stripped text plus exact simple word and sentence counts.
- Preserved dialogue turn semantics and added an explicit `turn_count >= 2` semantic check.
- Added a fixture-style validator check that `source_seed_refs[].source_level = "G"` is accepted.

## Test Changes

- Preserved existing coverage and added linkage field presence, missing-required-field failure, lifecycle failure, unresolved-ref consistency, future RAZ level `G`, additional-properties rejection, and dialogue turn-count checks.

## Validation Results

- Post-patch validator: `PASS`
- Post-patch pytest: `PASS`
- Optional compile check: `PASS`

## Known Limitations

1. S11C1 only reserves linkage fields; it does not implement actual seed-authority linkage.
2. `authority_refs` currently mirror provided refs; they are not newly resolved in this patch.
3. `source_seed_refs` supports G/H/I but does not enable G/H/I query discovery.
4. `unresolved_authority_refs` are structural placeholders until S6F linkage implementation.
5. No content generation, intake, or promotion path is enabled.

## Recommended Next Tasks

- `RAZ-S6D_LevelExpansionDynamicDiscovery_Implementation`
- `RAZ-S6F_SeedAuthorityLinkage_Implementation`

## Closeout Marker

`ULGA-S11C1_ReadingDialogueContentAuthority_LinkageFieldsSchemaPatch_PASS`

# ULGA-S11C Reading / Dialogue Content Authority Schema Implementation

## Scope

This task implements schema-only contracts for first-class Reading and Dialogue Content Authority records.

Boundaries preserved:

- no builder implementation
- no query-layer mutation
- no scheduler, orchestrator, dashboard, API, or runtime-status mutation
- no modification to `reading_stub_authority.json`
- no promotion of sample content into approved runtime graph artifacts

## Files Created

- `ulga/schemas/reading_content_authority_schema.json`
- `ulga/schemas/dialogue_content_authority_schema.json`
- `ulga/schemas/sample_reading_content_authority.json`
- `ulga/schemas/sample_dialogue_content_authority.json`
- `ulga/validators/validate_reading_dialogue_content_authority_schema.py`
- `tests/ulga/test_reading_dialogue_content_authority_schema.py`
- `docs/ulga/ULGA_S11C_READING_DIALOGUE_CONTENT_AUTHORITY_SCHEMA_IMPLEMENTATION.md`

## Files Modified

- None

## Commands Executed

- `python ulga/validators/validate_reading_dialogue_content_authority_schema.py`
- `python -m pytest tests/ulga/test_reading_dialogue_content_authority_schema.py -q`

## Contract Decisions

1. Reading and Dialogue are implemented as separate schema files to avoid premature coupling to future storage layout decisions while still preserving a shared field shape.
2. `additionalProperties: false` is applied to both contracts to reduce integration drift between future builders, validators, query code, and reporting layers.
3. Required fields follow the S11 design scan mandatory set, while future-facing fields such as reinforcement refs, chunk refs, dependency refs, and question support remain optional.
4. `content_type` is locked per schema with `const` so a Reading record cannot silently enter a Dialogue flow and vice versa.
5. Dialogue keeps `turn_count` materialized, and the Python validator cross-checks it against `len(turns)` to catch stale derived metadata after repeated edits or partial process restarts.

## Risk Review

- Risk level: Low
- Live trading impact: None
- Restart required: No

Real-environment risks intentionally documented but not solved by schema-only work:

- generated or imported content can still be empty pedagogically even when schema-valid
- repeated intake execution still needs stable duplicate fingerprints
- process restart during approval still needs resumable write checkpoints
- malformed upstream content can still require a quarantine validator beyond schema shape
- timeout and API failure handling remain future intake-pipeline concerns

## Validation Coverage

The validator and tests cover:

1. Draft 2020-12 schema validity
2. valid sample Reading record
3. valid sample Dialogue record
4. missing Reading text
5. wrong content type routed into Reading schema
6. additional-property rejection for runtime drift fields
7. invalid Dialogue source type enum
8. Dialogue with too few turns
9. `turn_count` mismatch semantic failure
10. Reading `word_count` smaller than `sentence_count` semantic failure

## Integration Notes

- No existing ULGA graph artifact was modified.
- No current planner bridge or static candidate query behavior was changed.
- The new schemas are safe to consume later from builder, approval-gate, or import-validator work without forcing current S11B stub records to migrate immediately.
- `reading_stub_authority.json` remains a planner-facing dry-run artifact and is intentionally outside this new learner-facing content schema contract.

## Final Status

Overall status: `PASS`

## Recommended Next Task

- `ULGA-S11D_ContentAuthority_QueryContract`

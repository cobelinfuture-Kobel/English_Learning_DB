# RAZ-AW-S5B Reading Authority Bridge QA

## Task

`RAZ-AW-S5B_ReadingAuthorityBridge_QA`

Status:

`IMPLEMENTED_PENDING_LOCAL_RUN`

## File Added

`tools/validate_raz_reading_authority_bridge.py`

## Local Run

```powershell
python tools/validate_raz_reading_authority_bridge.py `
  --bridge-root raz_output_jsons/bridge/reading_authority `
  --reports-dir reports/raz `
  --summary reports/raz/raz_reading_authority_bridge_summary.json
```

Expected console status:

`READING_AUTHORITY_BRIDGE_QA_PASS`

Expected QA report:

`reports/raz/raz_reading_authority_bridge_qa.json`

## Expected Count

S5A emitted 22632 bridge candidates, so S5B should scan 22632 bridge candidates if all local bridge files exist.

## QA Scope

The validator checks aggregate structure and safety fields for local bridge artifacts. It expects:

- schema version `raz_reading_authority_bridge_contract.v1`
- `bridge_type=ReadingAuthorityBridge`
- `unit_type=page_unit`
- `canonical_source_kind=normalized_page_units`
- `bridge_status=bridge_candidate`
- `authority_status=candidate_only`
- `promotion_status=promotion_blocked`
- `review_status=pending`
- no issue counts, warnings, or blockers

## Commit Policy

Do not commit generated bridge artifacts under `raz_output_jsons/bridge/**`.

After local run, commit only the sanitized QA report if status and safety flags pass:

`reports/raz/raz_reading_authority_bridge_qa.json`

## Interpretation

S5B QA pass does not create final ReadingAuthority records. It only validates the S5A bridge candidate layer.

## Next Task

After S5B QA report is pushed, the next stage should be a separate ReadingAuthority intake design task, not direct promotion.

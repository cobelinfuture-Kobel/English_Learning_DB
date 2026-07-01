# RAZ-AW-S5A Reading Authority Bridge Implementation

## Task

`RAZ-AW-S5A_ReadingAuthorityBridge_Implementation`

Status:

`IMPLEMENTED_PENDING_LOCAL_RUN`

## File Added

`tools/build_raz_reading_authority_bridge_candidates.py`

## Local Run

```powershell
python tools/build_raz_reading_authority_bridge_candidates.py `
  --review-root raz_output_jsons/review `
  --bridge-root raz_output_jsons/bridge/reading_authority `
  --reports-dir reports/raz
```

Expected console status:

`READING_AUTHORITY_BRIDGE_PRECHECK_PASS`

Expected local output:

`raz_output_jsons/bridge/reading_authority/Level_*/raz_*_reading_authority_bridge_candidates.json`

Expected summary:

`reports/raz/raz_reading_authority_bridge_summary.json`

## Expected Count

S4B validated 22632 canonical page-unit review candidates, so S5A should emit 22632 bridge candidates if all checks pass.

## Commit Policy

Do not commit generated bridge artifacts under `raz_output_jsons/bridge/**`.

After local run, commit only the sanitized summary report if safety flags and status pass.

## Next Task

`RAZ-AW-S5B_ReadingAuthorityBridge_QA`

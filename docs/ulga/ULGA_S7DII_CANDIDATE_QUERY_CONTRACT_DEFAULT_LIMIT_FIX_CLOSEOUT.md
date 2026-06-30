# ULGA-S7DII Candidate Query Contract Default Limit Fix Closeout

## 1. Files Created

- `docs/ulga/ULGA_S7DII_CANDIDATE_QUERY_CONTRACT_DEFAULT_LIMIT_FIX_CLOSEOUT.md`

## 2. Files Modified

- `ulga/builders/build_pattern_vocabulary_constraints.py`
- `ulga/validators/validate_pattern_vocabulary_constraints.py`
- `tests/ulga/test_pattern_vocabulary_constraints.py`
- `ulga/audits/audit_pattern_vocabulary_constraints.py`
- `ulga/graph/pattern_vocabulary_candidate_query_contract.json`
- `ulga/reports/pattern_vocabulary_constraint_summary.json`
- `ulga/reports/pattern_vocabulary_constraint_qa_audit.json`
- `docs/ulga/ULGA_S7DI_PATTERN_VOCABULARY_CONSTRAINT_QA_AUDIT.md`

## 3. Root Cause

The S7D builder published `limit_default=50` only inside each slot-level `candidate_query` payload. The top-level candidate query contract did not declare a global `limit_default` or `limit_max`, so any runtime component reading only the top-level contract could drift from the slot-level default contract.

## 4. Contract Before / After

- Before:
  - Top-level contract had no `limit_default`
  - Top-level contract had no `limit_max`
  - Slot-level `candidate_query.limit_default` existed with value `50`
- After:
  - Top-level contract declares `limit_default: 50`
  - Top-level contract declares `limit_max: 200`
  - Slot-level `candidate_query.limit_default=50` remains unchanged
  - Validator rejects missing, invalid, inverted, or out-of-range top-level limit contracts

## 5. Dataset Counts After Rebuild

- Active constraints: `1344`
- Inactive / skipped patterns: `138`
- Slot constraints: `1932`
- Full pattern-vocabulary edges generated: `false`

## 6. Validator Enhancements

- Require top-level `limit_default`
- Require top-level `limit_max`
- Enforce both as positive integers
- Enforce `limit_default <= limit_max`
- Enforce `limit_max <= 200`
- Enforce slot-level `candidate_query.limit_default <= top-level limit_max`

## 7. Pytest Enhancements

- Added top-level `limit_default` presence coverage
- Added top-level `limit_max` presence coverage
- Added positive integer coverage for `limit_default`
- Added `limit_max <= 200` coverage
- Added slot-level `limit_default <= top-level limit_max` coverage
- Preserved no full pattern-vocabulary materialized edge coverage

## 8. Audit Regression Result

The top-level candidate query contract limit warning is removed. Any remaining warning is limited to incomplete design-scan slot type coverage in active constraints.

## 9. Validator Result

`PASS`

## 10. Pytest Result

- `python -m pytest tests/ulga/test_pattern_vocabulary_constraints.py -q`: `16 passed`
- `python -m pytest tests/ulga/ -q`: `118 passed`

## 11. Remaining Warnings

- Expected remaining warning scope is limited to incomplete design-scan slot type coverage in active constraints.

## 12. Recommended Next Task

`ULGA-S7E_PatternThemeLinkage_DesignScan`

## 13. Final Verdict

`WARNING_ACCEPTED`

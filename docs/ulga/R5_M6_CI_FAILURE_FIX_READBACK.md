# R5-M6 CI Failure Fix Readback

## 1. Current State

```text
Task:
R5-M6 CI failure fix

Cause:
Initial PR #11 branch was behind latest main and failed English DB CI Readback at pytest.

Fix:
Refresh/replay R5-M6 changes on top of the newer main lineage and create a replacement PR if the original PR is closed.
```

## 2. Evidence

```text
Original failing workflow:
English DB CI Readback
failed job: validate
failed step: Run pytest when tests directory exists

Passing workflow from same original head:
ReadingV1 P1 Tests = success
```

## 3. Files preserved for R5-M6

```text
ulga/builders/build_static_grammar_coverage_matrix.py
ulga/grammar/grammar_coverage_matrix.json
docs/ulga/R5_M6_STATIC_GRAMMAR_COVERAGE_MATRIX_GENERATOR.md
```

## 4. Next Check

```text
Open replacement PR from current branch.
Wait for both workflows.
Merge only if all required CI reports success.
```

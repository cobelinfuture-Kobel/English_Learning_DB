# ULGA-S11B Reading Stub Authority Implementation

## 1. Scope

Implemented the ULGA-S11B Reading Stub Authority as a derived content-authority skeleton.

S11B creates one potential Reading Asset stub for each existing Learning Opportunity. These records are metadata-only and are intended to validate the future planner delivery chain:

```text
Learning Opportunity -> Reading Asset -> Future Planner Delivery
```

S11B does not generate learner-facing reading text, does not approve content, does not mutate learner state, and does not modify upstream opportunity, ranking, dependency, theme, vocabulary, or pattern artifacts.

## 2. Files Created

- `ulga/builders/build_reading_stub_authority.py`
- `ulga/validators/validate_reading_stub_authority.py`
- `ulga/graph/reading_stub_authority.json`
- `ulga/reports/reading_stub_summary.json`
- `tests/ulga/test_reading_stub_authority.py`
- `docs/ulga/ULGA_S11B_READING_STUB_AUTHORITY_IMPLEMENTATION.md`

## 3. Files Modified

None outside the S11B files listed above.

## 4. Inputs Read

- `ulga/graph/learning_opportunities.json`
- `ulga/graph/ranked_learning_opportunities.json`
- `ulga/graph/theme_nodes.json`
- `ulga/graph/vocabulary_nodes.json`
- `ulga/graph/sentence_patterns.json`
- `docs/ulga/ULGA_S11A_READING_AUTHORITY_DESIGN_SCAN.md`

## 5. Mapping Strategy

V1 mapping is intentionally simple:

```text
1 Learning Opportunity -> 1 Reading Stub
```

Each stub copies safe metadata from its source opportunity:

- `level`
- `theme_refs`
- `focus_nodes.vocabulary` into `focus_vocabulary`
- `focus_nodes.grammar` into `focus_grammar`
- `focus_nodes.pattern` into `focus_patterns`
- source `opportunity_id` into `linked_opportunities`

The design still preserves the S11A `N:N` future direction by using `linked_opportunities` as an array.

## 6. Output Counts

Current generated counts are expected to be:

- Total readings: 1344
- Linked opportunities: 1344
- Coverage ratio: 1.0
- Content status distribution: `stub` = 1344

## 7. Coverage Metrics

The summary report includes:

```json
{
  "planner_readiness": {
    "opportunity_count": 1344,
    "reading_count": 1344,
    "coverage_ratio": 1.0,
    "delivery_ready_ratio": 1.0
  }
}
```

`delivery_ready` means planner-contract ready for dry-run delivery, not approved learner-facing content.

## 8. Validator Result

Validator checks:

- `reading_id` uniqueness
- linked opportunity exists
- all opportunities are covered exactly once
- `theme_refs` exists and resolves to Theme Authority when available
- `level` exists
- `content_status == "stub"`
- `delivery_ready` exists and is true
- `source == "READING_STUB_AUTHORITY"`
- summary metrics match the generated readings

Executed command:

```powershell
python ulga\validators\validate_reading_stub_authority.py
```

Result: PASS.

## 9. Test Result

Focused tests cover:

- builder runs
- validator passes
- reading count is greater than zero
- coverage ratio equals 1.0
- reading ids are unique
- all linked opportunities exist exactly once
- deterministic output
- summary exists
- upstream input files are not modified

Executed commands:

```powershell
python ulga\builders\build_reading_stub_authority.py
python ulga\validators\validate_reading_stub_authority.py
python -m pytest tests\ulga\test_reading_stub_authority.py -q
python -m pytest tests\ulga\ -q
```

Results:

- Builder: PASS, 1344 readings, coverage ratio 1.0, 0 warnings
- Validator: PASS
- S11B focused tests: 10 passed
- Existing `tests\ulga\` suite: 278 passed, 5 failed

The 5 full-suite failures are existing S9F learner-state builder QA audit expectations in `tests\ulga\test_learner_state_builder_qa_audit.py`: the audit currently reports `BLOCKER` with 4 blockers instead of the test-expected `PASS_WITH_WARNINGS`.

## 10. Planner Readiness

S11B provides a concrete content-authority target for S10E Antigravity Planner implementation.

Planner can now validate this chain without relying on generated reading text:

```text
Opportunity -> Reading Stub -> Delivery Chain
```

Important limitation:

- Stubs are not approved readings.
- Future learner-facing delivery must filter by content policy and must not treat `content_status: "stub"` as reviewed or approved material.

## 11. Warnings

Known controlled warnings:

- Stub records contain metadata only and no final reading text.
- `delivery_ready` indicates planner dry-run readiness only.
- Current theme quality inherits S10B/S10B1 opportunity theme concentration, where most theme refs come from vocabulary theme authority.
- Unknown dependencies from source opportunities remain a planner/content-delivery policy concern.
- The full ULGA test suite still has unrelated S9F learner-state QA audit failures.

## 12. Final Verdict

S11B is ready for planner integration after builder, validator, and focused tests pass.

```text
S11B_STATUS: PASS
```

Recommended next task:

```text
ULGA-S10E_AntigravityPlanner_Implementation
```

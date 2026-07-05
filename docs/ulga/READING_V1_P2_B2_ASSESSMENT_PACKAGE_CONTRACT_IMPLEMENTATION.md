# ReadingV1 P2 B2 Assessment Package Contract Implementation

Task:
ReadingV1_P2_B2_AssessmentPackageContract_Implementation

Scope:
Implement the P2-B2 assessment package contract as schema, validator, and unit test scaffold.

Files created:

```text
ulga/schemas/reading_v1_p2_assessment_package.schema.json
ulga/validators/validate_reading_v1_p2_assessment_package.py
tests/ulga/test_reading_v1_p2_assessment_package.py
```

Implemented contract:

```text
schema_version = reading_v1_p2_assessment_package.v1
non-empty items list
child item validation through B1 validator
private homework only
local practice only
candidate_only
not_promoted
no public-ready package
no learner-state write
```

Validator entrypoint:

```text
validate_package(package)
```

Test command:

```text
python -m unittest tests.ulga.test_reading_v1_p2_assessment_package
```

Recommended combined command:

```text
python -m unittest tests.ulga.test_reading_v1_p2_assessment_item tests.ulga.test_reading_v1_p2_assessment_package
```

Current validation status:

```text
ReadingV1_P2_B2_LOCAL_TEST_STATUS = AWAITING_OPERATOR_LOCAL_TEST
```

Stop rule:

```text
Do not continue to P2-B3 until B2 local test output is read back.
```

Next task:

```text
ReadingV1_P2_B2_Local_Test_Readback
```

Task status:

```text
ReadingV1_P2_B2_AssessmentPackageContract_Implementation -> IMPLEMENTED_AWAITING_LOCAL_TEST
```

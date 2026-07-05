# ReadingV1 P2 B1 Assessment Item Contract Implementation

Task:
ReadingV1_P2_B1_AssessmentItemContract_Implementation

Scope:
Implement the P2-B1 assessment item contract as schema, validator, and unit test scaffold.

Files created:

```text
ulga/schemas/reading_v1_p2_assessment_item.schema.json
ulga/validators/validate_reading_v1_p2_assessment_item.py
tests/ulga/test_reading_v1_p2_assessment_item.py
```

Implemented contract:

```text
schema_version = reading_v1_p2_assessment_item.v1
private homework only
local practice only
candidate_only
not_promoted
no public-ready item
no learner-state write
no source payload persistence
```

Validator entrypoint:

```text
validate_item(item)
```

Test command:

```text
python -m unittest tests.ulga.test_reading_v1_p2_assessment_item
```

Current validation status:

```text
ReadingV1_P2_B1_LOCAL_TEST_STATUS = AWAITING_OPERATOR_LOCAL_TEST
```

Reason:
The GitHub connector wrote files but cannot execute repository unittest in this session.

Stop rule:

```text
Do not continue to P2-B2 until B1 local test output is read back.
```

Next task:

```text
ReadingV1_P2_B1_Local_Test_Readback
```

Task status:

```text
ReadingV1_P2_B1_AssessmentItemContract_Implementation -> IMPLEMENTED_AWAITING_LOCAL_TEST
```

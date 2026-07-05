# ReadingV1 P2 B4 Review Tag Contract Implementation

Task:
ReadingV1_P2_B4_ReviewTagContract_Implementation

Scope:
Implement the P2-B4 local review tag contract as schema, validator, and unit test scaffold.

Files created:

```text
ulga/schemas/reading_v1_p2_review_tag.schema.json
ulga/validators/validate_reading_v1_p2_review_tag.py
tests/ulga/test_reading_v1_p2_review_tag.py
```

Implemented contract:

```text
schema_version = reading_v1_p2_review_tag.v1
review_tag limited to local private review tags
review_boundary = local_private_review_only
learner_state_write = false
private_homework_only
candidate_only
not_promoted
not public-ready
```

Validator entrypoint:

```text
validate_review_tag(record)
```

Test command:

```text
python -m unittest tests.ulga.test_reading_v1_p2_review_tag
```

Recommended combined command:

```text
python -m unittest tests.ulga.test_reading_v1_p2_assessment_item tests.ulga.test_reading_v1_p2_assessment_package tests.ulga.test_reading_v1_p2_local_feedback tests.ulga.test_reading_v1_p2_review_tag
```

Current validation status:

```text
ReadingV1_P2_B4_LOCAL_TEST_STATUS = AWAITING_OPERATOR_LOCAL_TEST
```

Stop rule:

```text
Do not continue to P2-B5 until B4 local test output is read back.
```

Next task:

```text
ReadingV1_P2_B4_Local_Test_Readback
```

Task status:

```text
ReadingV1_P2_B4_ReviewTagContract_Implementation -> IMPLEMENTED_AWAITING_LOCAL_TEST
```

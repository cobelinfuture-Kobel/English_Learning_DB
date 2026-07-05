# ReadingV1 P2 B5 Package Builder Contract Implementation

Task:
ReadingV1_P2_B5_PackageBuilderContract_Implementation

Scope:
Implement the P2-B5 in-memory package builder contract and unit test scaffold.

Files created:

```text
ulga/builders/build_reading_v1_p2_assessment_package.py
tests/ulga/test_build_reading_v1_p2_assessment_package.py
```

Implemented contract:

```text
build_assessment_package(package_id, items)
build_synthetic_assessment_item(item_id)
build_synthetic_assessment_package()
in-memory dictionary output only
uses P2 package validator for tests
private_homework_only
candidate_only
not_promoted
not public-ready
no learner-state write
```

Test command:

```text
python -m unittest tests.ulga.test_build_reading_v1_p2_assessment_package
```

Recommended combined command:

```text
python -m unittest tests.ulga.test_reading_v1_p2_assessment_item tests.ulga.test_reading_v1_p2_assessment_package tests.ulga.test_reading_v1_p2_local_feedback tests.ulga.test_reading_v1_p2_review_tag tests.ulga.test_build_reading_v1_p2_assessment_package
```

Current validation status:

```text
ReadingV1_P2_B5_LOCAL_TEST_STATUS = AWAITING_OPERATOR_LOCAL_TEST
```

Stop rule:

```text
Do not continue to P2-B6 until B5 local test output is read back.
```

Next task:

```text
ReadingV1_P2_B5_Local_Test_Readback
```

Task status:

```text
ReadingV1_P2_B5_PackageBuilderContract_Implementation -> IMPLEMENTED_AWAITING_LOCAL_TEST
```

# ReadingV1 P2 B5 Local Test Readback

Task:
ReadingV1_P2_B5_Local_Test_Readback

Operator local commands:

```text
python -m unittest tests.ulga.test_build_reading_v1_p2_assessment_package
python -m unittest tests.ulga.test_reading_v1_p2_assessment_item tests.ulga.test_reading_v1_p2_assessment_package tests.ulga.test_reading_v1_p2_local_feedback tests.ulga.test_reading_v1_p2_review_tag tests.ulga.test_build_reading_v1_p2_assessment_package
```

Observed output:

```text
Ran 5 tests in 0.001s
OK
Ran 25 tests in 0.002s
OK
```

Result:

```text
ReadingV1_P2_B5_LOCAL_TEST_STATUS = PASS_LOCAL_SYNCED
ReadingV1_P2_B5_STATUS = COMPLETED
```

Next task:

```text
ReadingV1_P2_B6_Local_Test_And_Readback
```

Task status:

```text
ReadingV1_P2_B5_Local_Test_Readback -> COMPLETED
```

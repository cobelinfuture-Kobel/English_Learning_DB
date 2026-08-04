from ulga.builders import build_a1fs_v1_u01qb15_actual_real62_fresh474_r2_private_acceptance_runner as runner


def test_real62_identity_gate_uses_canonical_artifact_sha() -> None:
    assert runner.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert runner.A1FS_CONTENT_POLICY_EXEMPTION
    assert runner.EXPECTED_REAL62_ARTIFACT_SHA256 == "5b8564788cb645d8d3dd784316be5b05f950260da173a2bee7cfcbe1a7d9ab46"

from __future__ import annotations

from ulga.builders import _a1fs_online_v1_s16_canonical_learning_core as core
from ulga.builders import build_a1fs_online_v1_s16_canonical_mastery_remediation_reassessment_review_integration as builder
from ulga.validators import validate_a1fs_online_v1_s16_canonical_mastery_remediation_reassessment_review_integration as validator


def test_s16_builder_and_validator_declare_non_content_producer_policy() -> None:
    for module in (core, builder, validator):
        assert module.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
        assert module.A1FS_CONTENT_POLICY_EXEMPTION

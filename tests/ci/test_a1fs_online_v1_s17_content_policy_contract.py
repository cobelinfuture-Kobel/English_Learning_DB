from __future__ import annotations

from ulga.builders import build_a1fs_online_v1_s17_learner_parent_teacher_dashboard_human_review as builder
from ulga.validators import validate_a1fs_online_v1_s17_learner_parent_teacher_dashboard_human_review as validator


def test_s17_builder_and_validator_declare_non_content_producer_policy() -> None:
    for module in (builder, validator):
        assert module.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
        assert module.A1FS_CONTENT_POLICY_EXEMPTION

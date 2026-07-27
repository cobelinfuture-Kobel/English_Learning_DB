from __future__ import annotations

from ulga.builders import _a1fs_online_v1_s15_scored_journey_acceptance as acceptance
from ulga.builders import _a1fs_online_v1_s15_scored_journey_core as core
from ulga.builders import _a1fs_online_v1_s15_scored_journey_static as static
from ulga.builders import build_a1fs_online_v1_s15_reading_writing_scored_journey_completion_gate as builder
from ulga.validators import validate_a1fs_online_v1_s15_reading_writing_scored_journey_completion_gate as validator


def test_s15_builder_and_validator_declare_non_content_producer_policy() -> None:
    for module in (core, static, acceptance, builder, validator):
        assert module.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
        assert module.A1FS_CONTENT_POLICY_EXEMPTION

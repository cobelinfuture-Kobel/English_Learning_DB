from __future__ import annotations

from ulga.builders import build_a1fs_online_v1_s18_nonaudio_learner_product_e2e_release_acceptance_recovery as builder
from ulga.validators import validate_a1fs_online_v1_s18_nonaudio_learner_product_e2e_release_acceptance_recovery as validator


def test_s18_builder_and_validator_declare_non_content_producer_policy() -> None:
    for module in (builder, validator):
        assert module.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
        assert module.A1FS_CONTENT_POLICY_EXEMPTION

from __future__ import annotations

from product.a1fs_v1_2_1 import u04ms03_m2_capability_learner_facing_consumer_integration as compat
from product.a1fs_v1_2_1 import u04neb01_natural_episode_authority_cutover_108 as neb01


def test_pr579_legacy_entrypoint_now_delegates_to_neb01_without_rule_composition() -> None:
    report = compat.build_unit04_m2_capability_learner_facing_consumer_integration()
    assert report["task_id"] == neb01.TASK_ID
    assert report["status"] == neb01.STATUS
    assert report["revision"] == neb01.REVISION
    assert report["summary"]["episode_count"] == 108
    assert report["summary"]["micro_scene_count"] == 36
    assert report["authorship_contract"]["python_sentence_composer_used"] is False
    assert report["q10_infrastructure_proof"]["source_form_count"] == 20
    assert report["q10_infrastructure_proof"]["source_activity_count"] == 800

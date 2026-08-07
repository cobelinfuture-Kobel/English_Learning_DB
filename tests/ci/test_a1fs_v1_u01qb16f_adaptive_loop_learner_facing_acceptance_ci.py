from __future__ import annotations

import json
from pathlib import Path

from product.a1fs_v1_2_1 import u01qb15_runtime_server_e2e as product_runtime
from ulga.builders import _u01qb16e_different_item_reassessment_consumer_adapter as u16e


TASK_ID = "A1FS-V1-U01QB16F_Unit01AdaptiveLoopLearnerFacingAcceptanceAndPedagogicalQualityCloseout"
PASS_STATUS = "PASS_A1FS_V1_U01QB16F_ADAPTIVE_LOOP_LEARNER_FACING_ACCEPTANCE_AND_PEDAGOGICAL_QUALITY_CLOSEOUT"
NEXT_SHORT_STEP = "A1FS-V1-U01QB17_Unit01QuestionBankProductionQualityAndProgressionExpansion"


def _manifest() -> dict[str, object]:
    return json.loads(
        (Path(product_runtime.__file__).with_name("product_manifest.json")).read_text(encoding="utf-8")
    )


def _learner_adapter() -> str:
    return (
        Path(product_runtime.__file__)
        .with_name("runtime")
        .joinpath("secure_static", "u01qb15.js")
        .read_text(encoding="utf-8")
    )


def test_u01qb16f_closes_the_existing_single_runtime_adaptive_loop() -> None:
    manifest = _manifest()
    source = _learner_adapter()

    assert manifest["serve_module"] == "product.a1fs_v1_2_1.u01qb15_runtime_server_e2e"
    assert manifest["unit01_questionbank_runtime_item_count"] == 474
    assert manifest["unit01_questionbank_same_item_retry_allowed"] is False
    assert manifest["unit01_questionbank_reassessment_mode"] == "DIFFERENT_EXISTING_ITEM_AFTER_M7_DIAGNOSIS"
    assert u16e.installed() is True

    # Learner-visible closure: ordinary form completion surfaces canonical M7
    # pending work before another form may start, then renders targeted
    # remediation and one different existing-bank reassessment item.
    assert "await u01qb16eMaybeRenderPending()" in source
    assert "錯題補救" in source
    assert "完成補救，開始換題重評" in source
    assert "換題重新評量" in source
    assert "原錯題不重播" in source
    assert "/api/u01qb16e/reassessment/pending" in source
    assert "/api/u01qb16e/reassessment/start" in source
    assert "/api/u01qb16e/reassessment/response" in source

    # After reassessment the UI reloads canonical progress and re-enters the
    # pending/progression decision rather than creating a parallel learner path.
    assert "await loadProgress();" in source
    assert "setTimeout(()=>{u01qb16eMaybeRenderPending()" in source
    assert "if(await u01qb16eMaybeRenderPending())return;" in source


def test_u01qb16f_pedagogical_quality_invariants_are_learner_visible() -> None:
    source = _learner_adapter()

    # One-shot evidence prevents drill-until-correct from contaminating the
    # diagnosis signal.
    assert "每題只作答一次" in source
    assert "button.disabled=card.dataset.u01qb16eAttempted==='true'" in source

    # The learner is explicitly told that remediation uses a new item, while
    # support fillers remain runtime-only and invisible.
    assert "不會直接重做剛才的錯題" in source
    assert "support fillers 不呈現給學習者" in source
    assert "Different-item reassessment" in source

    # Existing task-angle/support metadata remains visible during ordinary and
    # reassessment work so the adaptive loop does not collapse into opaque
    # article-only retry behavior.
    assert "${item.task_angle}｜${item.support_level}" in source
    assert "${item.task_angle}｜${item.support_level}｜Different-item reassessment" in source


def test_u01qb16f_frozen_product_boundaries_remain_intact() -> None:
    manifest = _manifest()

    assert manifest["unit01_questionbank_runtime_item_count"] == 474
    assert manifest.get("speaking_scoring_enabled", False) is False
    assert manifest.get("audio_population_complete", False) is False
    assert manifest.get("a2_unlocked", False) is False

    assert u16e.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert u16e.A1FS_CONTENT_POLICY_EXEMPTION
    assert u16e.NEXT_SHORT_STEP == TASK_ID


def test_u01qb16f_closeout_identity_is_stable() -> None:
    assert TASK_ID.endswith("PedagogicalQualityCloseout")
    assert PASS_STATUS.startswith("PASS_A1FS_V1_U01QB16F_")
    assert NEXT_SHORT_STEP.startswith("A1FS-V1-U01QB17_")

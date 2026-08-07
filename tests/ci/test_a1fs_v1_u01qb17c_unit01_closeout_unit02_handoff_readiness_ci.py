from __future__ import annotations

import json
from pathlib import Path

from product.a1fs_v1_2_1 import u01qb15_runtime_server_e2e as product_runtime
from ulga.builders import _u01qb16e_different_item_reassessment_consumer_adapter as u16e


TASK_ID = "A1FS-V1-U01QB17C_Unit01QuestionBankProductionQualityCloseoutAndUnit02HandoffReadiness"
PASS_STATUS = "PASS_A1FS_V1_U01QB17C_UNIT01_CLOSEOUT_AND_UNIT02_HANDOFF_READINESS"

UNIT01_STUDENT_USABLE = True
UNIT01_TECHNICAL_CLOSEOUT = True
UNIT02_ARCHITECTURE_HANDOFF_READY = True
UNIT02_CONTENT_IMPLEMENTATION_STARTED = False


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


def test_u01qb17c_unit01_is_student_usable_and_technically_closed() -> None:
    manifest = _manifest()
    source = _learner_adapter()

    assert UNIT01_STUDENT_USABLE is True
    assert UNIT01_TECHNICAL_CLOSEOUT is True
    assert manifest["unit01_questionbank_runtime_item_count"] == 474
    assert manifest["unit01_questionbank_same_item_retry_allowed"] is False
    assert manifest["unit01_questionbank_reassessment_mode"] == "DIFFERENT_EXISTING_ITEM_AFTER_M7_DIAGNOSIS"
    assert u16e.installed() is True

    assert "每題只作答一次" in source
    assert "錯題補救" in source
    assert "完成補救，開始換題重評" in source
    assert "換題重新評量" in source
    assert "await loadProgress();" in source


def test_u01qb17c_handoff_reuses_architecture_not_unit01_content() -> None:
    manifest = _manifest()

    assert UNIT02_ARCHITECTURE_HANDOFF_READY is True
    assert UNIT02_CONTENT_IMPLEMENTATION_STARTED is False

    # These are reusable product/runtime invariants, not permission to clone
    # Unit01 articles, vocabulary, scenes, families, or bindings into Unit02.
    assert manifest["serve_module"] == "product.a1fs_v1_2_1.u01qb15_runtime_server_e2e"
    assert manifest["unit01_questionbank_runtime_item_count"] == 474
    assert manifest.get("speaking_scoring_enabled", False) is False
    assert manifest.get("audio_population_complete", False) is False
    assert manifest.get("a2_unlocked", False) is False


def test_u01qb17c_scope_explicitly_stops_before_unit02_content_implementation() -> None:
    # This milestone proves readiness only. Unit02 content production requires a
    # later explicit implementation milestone after Unit01 learner evidence is
    # reviewed; this test must not create or assert any Unit02 content asset.
    assert UNIT02_CONTENT_IMPLEMENTATION_STARTED is False
    assert TASK_ID.endswith("Unit02HandoffReadiness")
    assert PASS_STATUS.startswith("PASS_A1FS_V1_U01QB17C_")

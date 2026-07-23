from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


_IMPL_PATH = Path(__file__).with_name("cp07d_private_four_skill_delivery_consumer_test_impl.py")
_SPEC = importlib.util.spec_from_file_location("cp07d_private_four_skill_delivery_consumer_test_impl", _IMPL_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cp07d_test_impl_loader_unavailable")
_impl = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _impl
_SPEC.loader.exec_module(_impl)

_ORIGINAL_INITIALIZE_RUNTIME = _impl._initialize_runtime


def _initialize_runtime_with_directory(tmp_path: Path, skill: str):
    tmp_path.mkdir(parents=True, exist_ok=True)
    return _ORIGINAL_INITIALIZE_RUNTIME(tmp_path, skill)


_impl._initialize_runtime = _initialize_runtime_with_directory

# Preserve the already-reviewed four-skill runtime canaries and fail-closed tests.
test_policy_bound_projection_consumer_validates_for_each_skill = (
    _impl.test_policy_bound_projection_consumer_validates_for_each_skill
)
test_existing_m3_m5_m6_runtime_captures_projected_attempt = (
    _impl.test_existing_m3_m5_m6_runtime_captures_projected_attempt
)
test_listening_audio_and_speaking_recording_are_m10_compatible = (
    _impl.test_listening_audio_and_speaking_recording_are_m10_compatible
)
test_unresolved_cp05_lineage_and_a2_are_rejected = (
    _impl.test_unresolved_cp05_lineage_and_a2_are_rejected
)


def test_projected_asset_level_follows_selected_lesson_not_global_approved_scope() -> None:
    consumer = _impl._m2("READING")
    template = _impl._approved("READING")
    candidate = _impl.policy.build_candidate(
        payload=template["payload"],
        producer_id=_impl.cp05.PRODUCER_ID,
        level_scope=["A1", "A1+"],
        source_bindings={"fixture": "READING_A1_A1_PLUS_SCOPE"},
    )
    approved = _impl.policy.admit_candidate(
        candidate,
        validation_receipts=[
            {
                "validator_id": "cp07d_level_binding_fixture",
                "status": "PASS",
                "receipt_sha256": "4" * 64,
            }
        ],
        decision_ref="CP07D_LEVEL_BINDING_FIXTURE",
        producer_id=_impl.cp05.PRODUCER_ID,
    )
    plan = _impl._plan("READING", consumer)
    artifact = _impl.builder.build_private_delivery_consumer(consumer, approved, plan)
    projected = [
        row
        for row in artifact["asset_records"]
        if row["asset_key"] in artifact["cp07d_delivery_contract"]["projected_asset_keys"]
    ]
    assert projected
    assert {row["level"] for row in projected} == {"A1"}
    report = _impl.validator.validate_artifact(
        artifact,
        m2_consumer=consumer,
        cp05_approved=approved,
        cp07c_plan=plan,
    )
    assert report["validation_status"] == _impl.builder.PASS_STATUS, report["errors"]

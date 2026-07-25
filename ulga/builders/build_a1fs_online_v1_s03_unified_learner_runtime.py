#!/usr/bin/env python3
"""Governed S03 entrypoint that keeps private scoring out of M5 learner bundles."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Mapping, Sequence

from ulga.builders import build_a1fs_online_v1_s03_unified_learner_runtime_integration as _impl

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Renames the existing private scoring envelope to the M5-blocked answer_contract key while "
    "preserving the exact M6 scoring payload; no learner content or scoring authority is authored."
)

_ORIGINAL_LEARNER_PAYLOAD = _impl._learner_payload


def _m5_safe_learner_payload(item: Mapping[str, Any], *, capture_enabled: bool) -> dict[str, Any]:
    payload = _ORIGINAL_LEARNER_PAYLOAD(item, capture_enabled=capture_enabled)
    scoring = payload.pop("private_scoring_contract", None)
    if not isinstance(scoring, Mapping):
        raise _impl.RuntimeIntegrationError(
            f"private_scoring_contract_missing:{item.get('shared_item_id')}"
        )
    if "answer_contract" in payload:
        raise _impl.RuntimeIntegrationError(
            f"answer_contract_collision:{item.get('shared_item_id')}"
        )
    payload["answer_contract"] = dict(scoring)
    return payload


@contextmanager
def _patched() -> Iterator[None]:
    original = _impl._learner_payload
    _impl._learner_payload = _m5_safe_learner_payload
    try:
        yield
    finally:
        _impl._learner_payload = original


def build_runtime_consumer(
    s02_artifact: Mapping[str, Any],
    m03_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    with _patched():
        return _impl.build_runtime_consumer(s02_artifact, m03_artifact)


def materialize_runtime(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    with _patched():
        return _impl.materialize_runtime(*args, **kwargs)


def main(argv: Sequence[str] | None = None) -> int:
    with _patched():
        return _impl.main(argv)


def __getattr__(name: str) -> Any:
    return getattr(_impl, name)


if __name__ == "__main__":
    raise SystemExit(main())

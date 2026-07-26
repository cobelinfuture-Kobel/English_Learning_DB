#!/usr/bin/env python3
"""Compatibility adapter over the frozen S09 24-unit population core."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from typing import Any, Iterator, Mapping

from ulga.builders import _a1fs_online_v1_s09_twentyfour_unit_production_population_core as _core

for _name, _value in vars(_core).items():
    if not _name.startswith("__"):
        globals()[_name] = _value

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Adapts the frozen S09 population core to the existing S07 consumer summary contract and resolves "
    "CP01 grammar-unit prerequisite references to their existing canonical learning-unit identities. "
    "It creates no curriculum, learner content, answer key, audio, mastery, or public delivery."
)

_original_verify_cp01 = _core.s02._verify_cp01
_original_build_full_admission = _core.build_full_admission


def _verify_cp01_with_resolved_prerequisites(
    artifact: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    """Resolve CP01 prerequisite refs without changing the CP01 authority artifact.

    CP01 stores prerequisite refs in the grammar-unit namespace, while the S07/S09
    closure contracts operate in the learning-unit namespace. Both canonical forms
    are accepted as input, but every edge is normalized to a learning-unit identity
    before existence, order, and closure checks run.
    """

    raw_units = _original_verify_cp01(artifact)
    grammar_to_learning = {
        str(grammar_id): str(unit.get("learning_unit_id") or "")
        for grammar_id, unit in raw_units.items()
    }
    sequence_by_learning = {
        str(unit.get("learning_unit_id") or ""): int(unit.get("sequence_index") or 0)
        for unit in raw_units.values()
    }
    if (
        len(grammar_to_learning) != 24
        or len(sequence_by_learning) != 24
        or "" in grammar_to_learning.values()
        or "" in sequence_by_learning
    ):
        raise PopulationError("cp01_prerequisite_identity_index_invalid")

    resolved_units: dict[str, Mapping[str, Any]] = {}
    for grammar_id, raw_unit in raw_units.items():
        unit = deepcopy(dict(raw_unit))
        learning_id = str(unit.get("learning_unit_id") or "")
        sequence_index = int(unit.get("sequence_index") or 0)
        raw_prerequisites = unit.get("prerequisite_unit_ids")
        if not isinstance(raw_prerequisites, list) or len(raw_prerequisites) != len(
            set(str(value) for value in raw_prerequisites)
        ):
            raise PopulationError(f"prerequisite_contract_invalid:{grammar_id}")

        normalized: list[str] = []
        seen_learning_ids: set[str] = set()
        for raw_value in raw_prerequisites:
            source_ref = str(raw_value or "").strip()
            if not source_ref:
                raise PopulationError(f"prerequisite_reference_empty:{grammar_id}")
            if source_ref in grammar_to_learning:
                target_learning_id = grammar_to_learning[source_ref]
            elif source_ref in sequence_by_learning:
                target_learning_id = source_ref
            else:
                raise PopulationError(
                    f"prerequisite_reference_unknown:{grammar_id}:{source_ref}"
                )
            if target_learning_id in seen_learning_ids:
                raise PopulationError(
                    f"prerequisite_semantic_duplicate:{grammar_id}:{target_learning_id}"
                )
            target_sequence = sequence_by_learning[target_learning_id]
            if target_learning_id == learning_id or target_sequence >= sequence_index:
                raise PopulationError(
                    f"canonical_prerequisite_order_invalid:{grammar_id}"
                )
            seen_learning_ids.add(target_learning_id)
            normalized.append(target_learning_id)

        unit["prerequisite_unit_ids"] = normalized
        resolved_units[str(grammar_id)] = unit
    return resolved_units


@contextmanager
def _patched_cp01_prerequisite_identity() -> Iterator[None]:
    previous = _core.s02._verify_cp01
    _core.s02._verify_cp01 = _verify_cp01_with_resolved_prerequisites
    try:
        yield
    finally:
        _core.s02._verify_cp01 = previous


def build_full_admission(
    *,
    cp01_artifact: Mapping[str, Any],
    cp04_artifact: Mapping[str, Any],
    m03_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    """Build S09 admission with canonical prerequisite identity resolution."""

    with _patched_cp01_prerequisite_identity():
        return _original_build_full_admission(
            cp01_artifact=cp01_artifact,
            cp04_artifact=cp04_artifact,
            m03_artifact=m03_artifact,
        )


def build_consumer(
    admission: Mapping[str, Any],
    m03_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    """Project S09 population through the frozen S07 runtime consumer helper."""

    compatible = deepcopy(dict(admission))
    compatible["admission_summary"] = deepcopy(admission["population_summary"])
    with _core._patched_s07_identity():
        consumer = _core.s07.build_consumer(compatible, m03_artifact)
    for asset in consumer["asset_records"]:
        asset["release_scope"] = "PRIVATE_INTERNAL_A1FS_ONLINE_V1_S09"
    for lesson in consumer["lesson_catalog"]:
        lesson["release_scope"] = "PRIVATE_INTERNAL_A1FS_ONLINE_V1_S09"
        lesson["runtime_projection"]["selection_authority_task_id"] = TASK_ID
    projection = consumer["s07_runtime_projection"]
    projection.update({
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "admitted_unit_count": 24,
        "twentyfour_unit_population": True,
        "s07_runtime_engine_reused": True,
    })
    consumer["s09_runtime_projection"] = deepcopy(projection)
    consumer["next_short_step"] = NEXT_SHORT_STEP
    return consumer


_core.build_full_admission = build_full_admission
_core.build_consumer = build_consumer


if __name__ == "__main__":
    raise SystemExit(_core.main())

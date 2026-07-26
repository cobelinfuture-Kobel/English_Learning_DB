#!/usr/bin/env python3
"""Compatibility adapter over the frozen S09 24-unit population core."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from ulga.builders import _a1fs_online_v1_s09_twentyfour_unit_production_population_core as _core

for _name, _value in vars(_core).items():
    if not _name.startswith("__"):
        globals()[_name] = _value

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Adapts the frozen S09 population core to the existing S07 consumer summary contract. "
    "It creates no curriculum, learner content, answer key, audio, mastery, or public delivery."
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


_core.build_consumer = build_consumer


if __name__ == "__main__":
    raise SystemExit(_core.main())

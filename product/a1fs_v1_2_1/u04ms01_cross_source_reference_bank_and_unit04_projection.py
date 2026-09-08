from __future__ import annotations

from typing import Any

from product.a1fs_v1_2_1 import u04ms01_cross_source_reference_bank_and_unit04_projection_impl as _impl

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Compatibility adapter for the read-only Unit04 cross-source reference projection; "
    "does not author or promote learner-facing content."
)


def _validate_authorities(
    q02: dict[str, Any],
    q04: dict[str, Any],
    q05: dict[str, Any],
    q06: dict[str, Any],
) -> None:
    expected = {
        "q02": (q02.get("status"), "PASS_Q02_UNIT04_VOCABULARY_AND_EXACT_SURFACE_ADMISSION"),
        "q04": (q04.get("status"), "PASS_Q04_UNIT04_PLACE_CHUNK_AUTHORITY_AND_CUMULATIVE_DEDUP"),
        "q05": (q05.get("status"), "PASS_Q05_UNIT04_CORE_SENTENCE_FRAME_AUTHORITY"),
        "q06": (q06.get("status"), "PASS_Q06_UNIT04_SENTENCE_ASSET_PRODUCTION_AND_SEMANTIC_ADMISSION"),
    }
    bad = [f"{key}:{actual}" for key, (actual, wanted) in expected.items() if actual != wanted]
    if bad:
        raise _impl.ProjectionError("unit04_authority_not_pass:" + ",".join(bad))


_impl._validate_authorities = _validate_authorities

for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)

# Keep policy declarations explicit on this public entrypoint for governance scanners.
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Compatibility adapter for the read-only Unit04 cross-source reference projection; "
    "does not author or promote learner-facing content."
)

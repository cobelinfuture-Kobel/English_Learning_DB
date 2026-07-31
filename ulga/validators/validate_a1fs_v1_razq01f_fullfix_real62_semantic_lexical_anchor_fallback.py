#!/usr/bin/env python3
"""Validate RAZQ01F with the Real62 semantic lexical-anchor FullFix installed."""
from __future__ import annotations

from ulga.builders import (
    build_a1fs_v1_razq01f_fullfix_real62_semantic_lexical_anchor_fallback
    as fullfix,
)
from ulga.validators import (
    validate_a1fs_v1_razq01f_unit01_real_content_multi_session_diversity_learner_use_acceptance
    as _core,
)

for _name in dir(_core):
    if _name not in {"__name__", "__loader__", "__package__", "__spec__"}:
        globals()[_name] = getattr(_core, _name)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = (
    "A1FS_V1_RAZQ01F_FULLFIX_REAL62_SEMANTIC_LEXICAL_ANCHOR_VALIDATOR"
)


def main(argv=None) -> int:
    fullfix.install_fullfix()
    result = _core.main(argv)
    if result == 0:
        print(f"FULLFIX_VALIDATION_STATUS={fullfix.FULLFIX_PASS_STATUS}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())

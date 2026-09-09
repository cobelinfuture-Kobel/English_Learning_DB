from __future__ import annotations

from pathlib import Path

from product.a1fs_v1_2_1.u04neb01_natural_episode_authority_cutover_108 import (
    A1FS_CONTENT_POLICY_EXEMPTION,
    A1FS_CONTENT_POLICY_MODE,
    REVISION,
    STATUS,
    TASK_ID,
    build_unit04_natural_episode_authority_cutover_108,
)


# Compatibility entrypoint retained only because PR #579 originally introduced this module path.
# Natural learner language now comes exclusively from the static GPT-5.6 Sol authored NEB01 bank.
def build_unit04_m2_capability_learner_facing_consumer_integration(
    repo_root: Path | str | None = None,
):
    return build_unit04_natural_episode_authority_cutover_108(repo_root)

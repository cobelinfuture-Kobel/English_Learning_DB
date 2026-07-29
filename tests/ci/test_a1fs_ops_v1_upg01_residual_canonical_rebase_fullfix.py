from tests.ulga.test_a1fs_ops_v1_upg01_residual_canonical_rebase_fullfix import *  # noqa: F401,F403
from ulga.builders import (
    build_a1fs_ops_v1_upg01_python_upgrade_fullfix_residual_canonical_rebase as fix,
)


def teardown_module() -> None:
    fix.s05._core.s04.learner_evidence = fix.s05._S04_LEARNER_EVIDENCE
    fix.s05._core.s17.s16.s15.s14._decorate_bootstrap = (
        fix.s05._S14_DECORATE_BOOTSTRAP
    )
    fix.s05._core.V12Handler.do_GET = fix.s05._V12_DO_GET

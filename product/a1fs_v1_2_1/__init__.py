"""A1FS V1.2.1 pull-to-run product package."""

# Product-only runtime quality guards. These do not install a second runtime,
# planner, bank or scoring authority. U01QB16 strengthens whole-form item
# matching with learner-visible distinctness; U01QB16B strengthens the existing
# U01QB09/U01QB14R1 allocation so synonymous Reading task labels cannot masquerade
# as pedagogical progression; U01QB16C migrates only still-unbound persisted
# Reading blueprint rows before the existing U01QB13 consumer binds a new form.
from ulga.builders import _u01qb16_learner_visible_distinctness_adapter as _u01qb16
from ulga.builders import _u01qb16b_task_angle_progression_adapter as _u01qb16b
from ulga.builders import _u01qb16c_unbound_progression_runtime_hook as _u01qb16c

_u01qb16.install()
_u01qb16b.install()
_u01qb16c.install()

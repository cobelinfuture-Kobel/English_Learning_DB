"""A1FS V1.2.1 pull-to-run product package."""

# Product-only runtime quality guards. These do not install a second runtime,
# planner, bank or scoring authority. U01QB16 strengthens whole-form item
# matching with learner-visible distinctness; U01QB16B adds a capacity-preserving
# Reading capability-diversity preference; U01QB16C applies that progression to
# already-cut-over product databases only for forms that have never been bound.
from ulga.builders import _u01qb16_learner_visible_distinctness_adapter as _u01qb16
from ulga.builders import _u01qb16b_task_angle_progression_adapter as _u01qb16b
from ulga.builders import _u01qb16c_unbound_form_progression_overlay as _u01qb16c

_u01qb16.install()
_u01qb16b.install()
_u01qb16c.install()

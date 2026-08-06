"""A1FS V1.2.1 pull-to-run product package."""

# Product-only runtime quality guards. These do not install a second runtime,
# planner, bank, scoring or mastery authority. U01QB16 strengthens whole-form
# item matching; U01QB16B/C improve safe Reading progression; U01QB16D attaches
# exact QuestionBank attempt/task identity and a different-item reassessment
# candidate to the existing canonical M7 diagnosis/remediation chain.
from ulga.builders import _u01qb16_learner_visible_distinctness_adapter as _u01qb16
from ulga.builders import _u01qb16b_task_angle_progression_adapter as _u01qb16b
from ulga.builders import _u01qb16c_unbound_form_progression_overlay as _u01qb16c
from ulga.builders import _u01qb16d_questionbank_diagnosis_remediation_identity_adapter as _u01qb16d

_u01qb16.install()
_u01qb16b.install()
_u01qb16c.install()
_u01qb16d.install()

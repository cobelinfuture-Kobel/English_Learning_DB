"""A1FS V1.2.1 pull-to-run product package."""

# Product-only runtime quality guard. Importing the product package does not
# install a second runtime or matcher; it only upgrades the existing U01QB13
# whole-form matching decision so different item IDs cannot render the exact
# same learner-visible question inside one form/skill session.
from ulga.builders import _u01qb16_learner_visible_distinctness_adapter as _u01qb16

_u01qb16.install()

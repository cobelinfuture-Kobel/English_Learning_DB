"""A1FS V1.2.1 pull-to-run product package."""

# Product-only runtime quality guards. These do not install a second runtime,
# planner, bank, scoring or mastery authority. U01QB16 strengthens whole-form
# item matching; U01QB16B/C improve safe Reading progression; U01QB16D attaches
# exact QuestionBank attempt/task identity and a different-item reassessment
# candidate to the existing canonical M7 diagnosis/remediation chain. U01QB18C
# repairs learner-facing interaction/scaffolding/content quality, U01QB18E
# preserves approved micro-scene semantics and language-asset lineage, and
# U01QB18F-R2/R3 makes scene_ref_id dereference the full canonical scene package
# through the same U01QB13/U01QB15 learner-facing projection.
from ulga.builders import _u01qb16_learner_visible_distinctness_adapter as _u01qb16
from ulga.builders import _u01qb16b_task_angle_progression_adapter as _u01qb16b
from ulga.builders import _u01qb16c_unbound_form_progression_overlay as _u01qb16c
from ulga.builders import _u01qb16d_questionbank_diagnosis_remediation_identity_adapter as _u01qb16d
from ulga.builders import _u01qb18c_form01_learner_quality_adapter as _u01qb18c
from ulga.builders import _u01qb18e_micro_scene_semantic_lineage_e2e_adapter as _u01qb18e
from ulga.builders import _u01qb18f_r1_sqlite_row_compat_adapter as _u01qb18f_r1
from ulga.builders import _u01qb18f_r3_micro_scene_cross_layer_consumer_cutover_adapter as _u01qb18f_r3

_u01qb16.install()
_u01qb16b.install()
_u01qb16c.install()
_u01qb16d.install()
_u01qb18c.install()

# U18C focused/historical tests legitimately exercise repair_learner_item with
# synthetic rows that predate semantic-lineage materialization. Preserve that
# exact contract while requiring the richer U18E repair for formal payload rows,
# which receive semantic_lineage from U18E's base payload delegate first.
_u01qb18e_semantic_repair = _u01qb18e.repair_learner_item_with_semantic_lineage


def _u01qb18e_compatible_repair(
    item,
    *,
    private_item,
    form_ordinal,
    scene_anchors,
    setting,
):
    if not isinstance(item.get("semantic_lineage"), dict):
        return _u01qb18e._ORIGINAL_18C_REPAIR(
            item,
            private_item=private_item,
            form_ordinal=form_ordinal,
            scene_anchors=scene_anchors,
            setting=setting,
        )
    return _u01qb18e_semantic_repair(
        item,
        private_item=private_item,
        form_ordinal=form_ordinal,
        scene_anchors=scene_anchors,
        setting=setting,
    )


_u01qb18e.repair_learner_item_with_semantic_lineage = _u01qb18e_compatible_repair
_u01qb18e.install()
_u01qb18f_r1.install()
_u01qb18f_r3.install()

# R4R2 must not replace matching.assemble_form_component: U16C remains the
# public assembler owner and U18E remains its internal semantic delegate. R1
# installs Writing parity at U16C's existing pre-assemble migration call point.
from ulga.builders import (  # noqa: E402
    _u01qb18f_r4r2_r1_preserve_u16c_public_ownership_adapter as _u01qb18f_r4r2_r1,
)

_u01qb18f_r4r2_r1.install()

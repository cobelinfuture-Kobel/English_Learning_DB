from __future__ import annotations

import json

from product import a1fs_v1_2_1 as product_package  # noqa: F401
from ulga.builders import _u01qb13_distinct_item_matching_adapter as matching
from ulga.builders import _u01qb16c_unbound_form_progression_overlay as u16c
from ulga.builders import _u01qb18c_form01_learner_quality_adapter as quality
from ulga.builders import _u01qb18f_r4r2_unbound_writing_selector_parity_fullfix as r4r2
from ulga.builders import (
    _u01qb18f_r4r2_r1_preserve_u16c_public_ownership_adapter as r4r2_r1,
)
from ulga.builders import (
    build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration
    as u13,
)


def _activity(
    *,
    scene: str,
    slot: int,
    ordinal: int,
    noun: str,
    angle: str,
    family: str,
) -> dict[str, object]:
    return {
        "activity_id": f"U01-FORM-06-S{slot:02d}-A{ordinal:02d}",
        "form_id": "U01-FORM-06",
        "form_ordinal": 6,
        "scene_ref_id": scene,
        "situation_family": "OUTDOORS_SOCIAL",
        "setting": "PARK_AND_BIRTHDAY",
        "skill": "WRITING",
        "task_angle": angle,
        "support_level": "REDUCED_SUPPORT",
        "scored": 1,
        "assessment_candidate": 0,
        "pattern_family_ids_json": json.dumps([family]),
        "scene_anchors_json": json.dumps([noun]),
        "activity_digest": f"DIGEST-{slot}-{ordinal}",
    }


def _catalog_row(
    *,
    item_id: str,
    family: str,
    noun: str,
    stimulus: str,
) -> dict[str, object]:
    return {
        "item_id": item_id,
        "skill": "WRITING",
        "pattern_family_id": family,
        "private_item_json": json.dumps(
            {
                "pattern_family_id": family,
                "context_id": "U01-C5-PARK-BIRTHDAY",
                "lexical_slots": {
                    "noun": noun,
                    "context_id": "U01-C5-PARK-BIRTHDAY",
                },
                "stimulus": stimulus,
                "prompt": f"Write with {noun}.",
                "options": [],
            }
        ),
    }


def _fixture() -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, str]]:
    nouns = ["apple", "bag", "cat", "park"]
    activities: list[dict[str, object]] = []
    catalog: list[dict[str, object]] = []
    scoring: dict[str, str] = {}
    for slot, noun in enumerate(nouns, 1):
        scene = f"SCENE-{slot}"
        activities.extend(
            [
                _activity(
                    scene=scene,
                    slot=slot,
                    ordinal=3,
                    noun=noun,
                    angle="CONTEXTUAL_REFERENCE_GAP",
                    family=u13.PF09,
                ),
                _activity(
                    scene=scene,
                    slot=slot,
                    ordinal=4,
                    noun=noun,
                    angle="WORD_ORDER",
                    family=u13.PF07,
                ),
            ]
        )
        article = "an" if noun == "apple" else "a"
        context_stimulus = (
            f"There is {article} {noun} in the park. The {noun} is easy to see."
        )
        pf09_id = f"PF09-{noun}"
        pf07_id = f"PF07-{noun}"
        catalog.append(
            _catalog_row(
                item_id=pf09_id,
                family=u13.PF09,
                noun=noun,
                stimulus=context_stimulus,
            )
        )
        catalog.append(
            _catalog_row(
                item_id=pf07_id,
                family=u13.PF07,
                noun=noun,
                stimulus=f"Words for {noun}: {article} | {noun}",
            )
        )
        scoring[pf09_id] = matching.SCORING_CLASS_AUTO
        scoring[pf07_id] = matching.SCORING_CLASS_AUTO

    # Only the failing PARK scene gets one exact already-approved AUTO alternative.
    # It is not context-bound, so it remains semantically anchored by noun=park while
    # avoiding the learner-invalid "park in the park" PF09 surface form.
    catalog.append(
        _catalog_row(
            item_id="PF17-park",
            family=u13.PF17,
            noun="park",
            stimulus="use: a/an | noun: park",
        )
    )
    scoring["PF17-park"] = matching.SCORING_CLASS_AUTO
    return activities, catalog, scoring


def test_r4r2_replans_only_the_unexecutable_writing_activity_with_formal_product_predicates() -> None:
    activities, catalog, scoring = _fixture()

    assert r4r2._formal_assignment_exists(
        activities,
        catalog=catalog,
        scoring=scoring,
        learner_id="LEARNER",
        session_id="SESSION",
        exposed=set(),
        recent=set(),
    ) is False

    chosen = r4r2._choose_form_rows(
        activities,
        prior={},
        catalog=catalog,
        scoring=scoring,
        learner_id="LEARNER",
        session_id="SESSION",
        exposed=set(),
        recent=set(),
    )

    assert r4r2._formal_assignment_exists(
        chosen,
        catalog=catalog,
        scoring=scoring,
        learner_id="LEARNER",
        session_id="SESSION",
        exposed=set(),
        recent=set(),
    ) is True

    before = {str(row["activity_id"]): str(row["task_angle"]) for row in activities}
    after = {str(row["activity_id"]): str(row["task_angle"]) for row in chosen}
    changed = {activity_id: angle for activity_id, angle in after.items() if before[activity_id] != angle}
    assert changed == {"U01-FORM-06-S04-A03": "PHRASE_CONSTRUCTION"}
    assert next(
        row for row in chosen if row["activity_id"] == "U01-FORM-06-S04-A04"
    )["task_angle"] == "WORD_ORDER"


def test_r4r2_preserves_u16c_public_owner_and_uses_internal_pre_assemble_hook() -> None:
    assert u16c.installed() is True
    assert r4r2_r1.installed() is True
    assert r4r2.installed() is True
    assert matching.assemble_form_component is u16c.assemble_form_component
    assert (
        u16c.migrate_unbound_reading_form
        is r4r2_r1.pre_assemble_reading_then_writing_parity
    )
    assert (
        r4r2_r1._ORIGINAL_U16C_PRE_ASSEMBLE
        is not r4r2_r1.pre_assemble_reading_then_writing_parity
    )
    assert (
        matching.candidate_preserves_scoring_class
        is quality.candidate_preserves_scoring_class_with_learner_quality
    )

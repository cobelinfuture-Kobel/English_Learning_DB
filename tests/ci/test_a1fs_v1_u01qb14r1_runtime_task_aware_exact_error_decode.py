from ulga.builders import build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u01qb09


def test_form01_scene_activity03_is_guided_writing_phrase_construction_in_legacy_allocation() -> None:
    profile = u01qb09.SUPPORT_PROFILES["GUIDED"]["candidates"]
    assert profile["READING"][:2] == ["ARTICLE_CONTROL", "FIRST_MENTION_CONTEXT"]
    assert profile["WRITING"][:2] == ["PHRASE_CONSTRUCTION", "WORD_ORDER"]

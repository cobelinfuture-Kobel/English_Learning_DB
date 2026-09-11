from product.a1fs_v1_2_1 import u04formv3c_direct_authored_form01_04_validator as target


def test_u04_formv3c_direct_authored_form01_04_mechanical_validation():
    report = target.validate_form01_04()

    assert report["status"] == target.STATUS
    assert report["form_count"] == 4
    assert report["task_count"] == 160
    assert report["response_mode_coverage_count"] == 22
    assert report["distinct_current360_episode_count"] == 24
    assert report["cross_form_episode_reuse_count"] == 0
    assert report["exact_prompt_duplicate_count"] == 0
    assert report["picture_asset_pending_count"] == 8
    assert report["picture_asset_materialization_status"] == "PENDING"
    assert report["human_visual_acceptance"] == "PENDING"

    assert report["python_blueprint_generation_used"] is False
    assert report["python_response_mode_assignment_used"] is False
    assert report["python_task_family_assignment_used"] is False
    assert report["python_learner_content_authoring_used"] is False
    assert report["python_answer_option_authoring_used"] is False
    assert report["legacy_python_task_builder_used"] is False
    assert report["current360_passage_mutation_used"] is False
    assert report["formv3c_runtime_cutover"] is False
    assert report["current_fsv2_runtime_remains_active"] is True
    assert report["a2_a2plus_unlocked"] is False
    assert report["listening_modified"] is False

    assert len(report["forms"]) == 4
    for form in report["forms"]:
        assert form["context_count"] == 6
        assert form["task_count"] == 40
        assert form["distinct_response_mode_count"] == 21
        assert form["choice_position_max_delta"] <= 1
        assert form["picture_asset_pending_count"] == 2
        assert len(form["target_relation_coverage"]) == 8
        assert len(form["episode_ids"]) == 6


def test_u04_formv3c_gpt56_source_binding_semantic_rebinds_are_locked():
    root = target._root()
    expected = {
        1: ["U04-NEB-E002", "U04-NEB-E007", "U04-NEB-E013", "U04-NEB-E022", "U04-NEB-E102", "U04-NEB-E069"],
        2: ["U04-NEB-E003", "U04-NEB-E010", "U04-NEB-E019", "U04-NEB-E038", "U04-NEB-E081", "U04-NEB-E108"],
        3: ["U04-NEB-E004", "U04-NEB-E014", "U04-NEB-E024", "U04-NEB-E034", "U04-NEB-E053", "U04-NEB-E101"],
        4: ["U04-NEB-E005", "U04-NEB-E015", "U04-NEB-E056", "U04-NEB-E075", "U04-NEB-E009", "U04-NEB-E041"],
    }
    for form_number, episode_ids in expected.items():
        form = target._load_asset(root, form_number)["form"]
        assert [row["episode_id"] for row in form["contexts"]] == episode_ids


def test_u04_formv3c_blueprint_dimensions_are_not_python_reassigned():
    root = target._root()
    blueprint_payload = target.blueprint._load(root)
    plans = {int(row["form_number"]): row for row in blueprint_payload["forms"]}

    for form_number in target.EXPECTED_FORMS:
        form = target._load_asset(root, form_number)["form"]
        planned_tasks = plans[form_number]["tasks"]
        assert len(form["tasks"]) == len(planned_tasks) == 40
        for task, planned in zip(form["tasks"], planned_tasks):
            for key in (
                "question_number", "section", "context_role", "skill", "assessment_capability",
                "task_family", "response_mode", "response_field_count", "picture_required",
            ):
                assert task[key] == planned[key]

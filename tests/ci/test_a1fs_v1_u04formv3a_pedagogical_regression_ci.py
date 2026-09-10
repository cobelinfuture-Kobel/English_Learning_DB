from product.a1fs_v1_2_1 import u04formv3_direct_authoring_contract as contract
from product.a1fs_v1_2_1 import u04formv3a_direct_authored_form01_04_validator as target


def _forms():
    root = target._root()
    return [target._load_asset(root, number)["form"] for number in target.EXPECTED_FORMS]


def test_u04_formv3a_action_sequence_is_event_sequence_not_mention_order():
    action_count = 0
    for form in _forms():
        contexts = {row["slot"]: row["passage"] for row in form["contexts"]}
        action_items = [item for item in form["questions"] if item["family"] == "ACTION_SEQUENCE"]
        assert len(action_items) == 2
        action_count += len(action_items)

        for item in action_items:
            prompt = item["prompt"].casefold()
            passage = contexts[item["context_slot"]].casefold()

            # A sequence item must ask about event order, never token/mention order.
            assert "mention" not in prompt
            assert any(cue in prompt for cue in ("first", "before", "after", "in order", "then"))

            # The bound Current360 passage itself must expose sequence evidence.
            assert any(
                cue in passage
                for cue in ("first", "then", "before", "after", "one thing at a time", "step by step")
            )

    assert action_count == 8


def test_u04_formv3a_support_relations_are_exposure_only_not_assessed_answers():
    question_count = 0
    for form in _forms():
        for item in form["questions"]:
            question_count += 1
            reference = str(item["reference_answer"])
            for relation in contract.SUPPORT_RELATIONS:
                assert not target._contains_surface(reference, relation), (
                    item["question_id"], relation, reference
                )

    assert question_count == 160

#!/usr/bin/env python3
"""Apply R7-M105R learner-safe item delivery FullFix atomically."""

from __future__ import annotations

import py_compile
import subprocess
import tempfile
from pathlib import Path

EXPECTED_BRANCH = "agent/r7-m105r-learner-safe-item-delivery-fullfix"
ROOT = Path.cwd()
BUILDER = ROOT / "ulga/builders/build_a1_grammar_text_mode_practice_item_fullfix.py"
RUNNER = ROOT / "ulga/builders/run_a1_grammar_text_mode_private_pilot_next_unit.py"
PRACTICE_TEST = ROOT / "tests/ulga/test_a1_grammar_text_mode_practice_item_fullfix.py"
REVIEW_TEST = ROOT / "tests/ulga/test_a1_grammar_text_mode_review_session.py"

CONTEXT_OLD = 'def _context(unit: Mapping[str, Any], target: str, *, purpose: str) -> dict[str, Any]:\n    meaning = next(iter(unit.get("meaning_functions", [])), "express the target grammar meaning")\n    usage = next(iter(unit.get("usage_conditions", [])), "Use the target form accurately.")\n    return {\n        "situation": f"A learner needs to {meaning} in a short A1 message.",\n        "communicative_goal": purpose,\n        "grammar_clue": usage,\n        "model_target": target,\n    }\n\n\n'
CONTEXT_NEW = 'def _context(unit: Mapping[str, Any], target: str, *, purpose: str) -> dict[str, Any]:\n    meaning = next(iter(unit.get("meaning_functions", [])), "express the target grammar meaning")\n    usage = next(iter(unit.get("usage_conditions", [])), "Use the target form accurately.")\n    return {\n        "situation": f"A learner needs to {meaning} in a short A1 message.",\n        "communicative_goal": purpose,\n        "grammar_clue": usage,\n    }\n\n\ndef _regular_plural_source_form(target: str) -> str:\n    word = target.strip()\n    if not re.fullmatch(r"[A-Za-z]+", word):\n        raise ValueError(f"regular_plural_target_not_single_word:{target}")\n    lowered = word.casefold()\n    if lowered.endswith("ies") and len(word) > 3:\n        return word[:-3] + "y"\n    if re.search(r"(ches|shes|sses|xes|zes|oes)$", lowered):\n        return word[:-2]\n    if lowered.endswith("s") and len(word) > 1:\n        return word[:-1]\n    raise ValueError(f"regular_plural_source_form_not_derivable:{target}")\n\n\n'
GAP_OLD = 'def _gap_item(unit: Mapping[str, Any], target: str) -> dict[str, Any]:\n    grammar_id = unit["grammar_unit_id"]\n    tokens = _tokens(target)\n    index = _focus_index(grammar_id, tokens)\n    missing = tokens[index]\n    display = tokens[:]\n    display[index] = "____"\n    item = _base_item(\n        unit,\n        code="P04",\n        skill="writing",\n        dimension="controlled_production",\n        role="practice",\n        task_type="structured_gap_fill",\n        prompt=f"Complete the sentence or phrase with the missing target form: {\' \'.join(display)}",\n        target=target,\n        response_mode="short_text",\n    )\n    item["gap_spec"] = {\n        "display_tokens": display,\n        "missing_token_index": index,\n        "accepted_missing_tokens": [missing],\n        "full_answer_tokens": tokens,\n    }\n    item["accepted_variation_policy"] = {\n        "exact_missing_token_required": True,\n        "case_insensitive": missing != "I",\n        "punctuation_tolerance": True,\n    }\n    return item\n\n\n'
GAP_NEW = 'def _gap_item(unit: Mapping[str, Any], target: str) -> dict[str, Any]:\n    grammar_id = unit["grammar_unit_id"]\n    tokens = _tokens(target)\n    index = _focus_index(grammar_id, tokens)\n    missing = tokens[index]\n    display = tokens[:]\n    display[index] = "____"\n    source_form: str | None = None\n    cue_contract: str | None = None\n\n    if len(tokens) == 1:\n        if grammar_id != "GRAMMAR_REGULAR_PLURAL_NOUNS":\n            raise ValueError(\n                f"single_token_gap_requires_unique_cue_contract:{grammar_id}:{target}"\n            )\n        source_form = _regular_plural_source_form(target)\n        cue_contract = "REGULAR_PLURAL_SOURCE_FORM"\n        prompt = f\'Write the regular plural form of "{source_form}": ____\'\n    else:\n        prompt = (\n            "Complete the sentence or phrase with the missing target form: "\n            f"{\' \'.join(display)}"\n        )\n\n    item = _base_item(\n        unit,\n        code="P04",\n        skill="writing",\n        dimension="controlled_production",\n        role="practice",\n        task_type="structured_gap_fill",\n        prompt=prompt,\n        target=target,\n        response_mode="short_text",\n    )\n    item["gap_spec"] = {\n        "display_tokens": display,\n        "missing_token_index": index,\n        "accepted_missing_tokens": [missing],\n        "full_answer_tokens": tokens,\n    }\n    if source_form is not None:\n        item["gap_spec"]["source_form"] = source_form\n        item["gap_spec"]["cue_contract"] = cue_contract\n    item["accepted_variation_policy"] = {\n        "exact_missing_token_required": True,\n        "case_insensitive": missing != "I",\n        "punctuation_tolerance": True,\n    }\n    return item\n\n\n'
VALIDATOR_OLD = '        task_type = item.get("task_type")\n        if task_type == "context_choice" and not item.get("context"):\n            errors.append(f"context_payload_missing:{item_id}")\n        if task_type == "structured_gap_fill" and not item.get("gap_spec"):\n            errors.append(f"gap_spec_missing:{item_id}")\n        if task_type == "structured_word_order" and not item.get("token_sequence"):\n            errors.append(f"token_sequence_missing:{item_id}")\n        if task_type == "structured_morphology_build" and not item.get("morphology_parts"):\n            errors.append(f"morphology_parts_missing:{item_id}")\n'
VALIDATOR_NEW = '        task_type = item.get("task_type")\n        context = item.get("context")\n        if isinstance(context, Mapping) and "model_target" in context:\n            errors.append(f"learner_context_answer_leak:{item_id}")\n        if task_type == "context_choice" and not context:\n            errors.append(f"context_payload_missing:{item_id}")\n        if task_type == "structured_gap_fill":\n            gap = item.get("gap_spec")\n            if not isinstance(gap, Mapping):\n                errors.append(f"gap_spec_missing:{item_id}")\n            else:\n                answer_tokens = gap.get("full_answer_tokens", [])\n                if len(answer_tokens) == 1:\n                    if gap.get("cue_contract") != "REGULAR_PLURAL_SOURCE_FORM":\n                        errors.append(f"single_token_gap_cue_contract_missing:{item_id}")\n                    source_form = gap.get("source_form")\n                    if not isinstance(source_form, str) or not source_form.strip():\n                        errors.append(f"single_token_gap_source_form_missing:{item_id}")\n                    if source_form == item.get("answer_key", {}).get("canonical_target"):\n                        errors.append(f"single_token_gap_source_equals_answer:{item_id}")\n        if task_type == "structured_word_order" and not item.get("token_sequence"):\n            errors.append(f"token_sequence_missing:{item_id}")\n        if task_type == "structured_morphology_build" and not item.get("morphology_parts"):\n            errors.append(f"morphology_parts_missing:{item_id}")\n'
RUNNER_DISPLAY_OLD = 'def _display_item(item: Mapping[str, Any], number: int, total: int) -> None:\n    print()\n    print("-" * 72)\n    print(\n        f"[{number}/{total}] {item.get(\'skill\')} / "\n        f"{item.get(\'item_role\')} / {item.get(\'task_type\')}"\n    )\n    print(f"Item ID: {item.get(\'item_id\')}")\n    context = item.get("context")\n    if context:\n        print("Context:", json.dumps(context, ensure_ascii=False))\n    print("Question:", item.get("prompt", ""))\n    for option_number, option in enumerate(item.get("options", []), start=1):\n        print(f"  {option_number}. {option}")\n\n\n'
RUNNER_DISPLAY_NEW = 'LEARNER_CONTEXT_FIELDS = (\n    "situation",\n    "communicative_goal",\n    "grammar_clue",\n)\n\n\ndef _learner_visible_context(item: Mapping[str, Any]) -> dict[str, Any]:\n    context = item.get("context")\n    if not isinstance(context, Mapping):\n        return {}\n    return {\n        field: context[field]\n        for field in LEARNER_CONTEXT_FIELDS\n        if field in context\n    }\n\n\ndef _learner_task_material(\n    item: Mapping[str, Any],\n) -> tuple[str, list[str]] | None:\n    task_type = item.get("task_type")\n    if task_type == "structured_morphology_build":\n        values = item.get("morphology_parts", [])\n        label = "Supplied parts"\n    elif task_type == "structured_word_order":\n        values = item.get("token_sequence", [])\n        label = "Supplied tokens"\n    elif task_type == "structured_gap_fill":\n        gap = item.get("gap_spec", {})\n        source_form = gap.get("source_form") if isinstance(gap, Mapping) else None\n        values = [source_form] if isinstance(source_form, str) else []\n        label = "Source form"\n    else:\n        return None\n    visible = [str(value) for value in values if str(value).strip()]\n    return (label, visible) if visible else None\n\n\ndef _display_item(item: Mapping[str, Any], number: int, total: int) -> None:\n    print()\n    print("-" * 72)\n    print(\n        f"[{number}/{total}] {item.get(\'skill\')} / "\n        f"{item.get(\'item_role\')} / {item.get(\'task_type\')}"\n    )\n    print(f"Item ID: {item.get(\'item_id\')}")\n    context = _learner_visible_context(item)\n    if context:\n        print("Context:", json.dumps(context, ensure_ascii=False))\n    print("Question:", item.get("prompt", ""))\n    material = _learner_task_material(item)\n    if material is not None:\n        label, values = material\n        print(f"{label}: {\' | \'.join(values)}")\n    for option_number, option in enumerate(item.get("options", []), start=1):\n        print(f"  {option_number}. {option}")\n\n\n'
PRACTICE_CONTEXT_OLD = '        if item["task_type"] == "context_choice":\n            assert item["context"]["situation"]\n            assert item["context"]["communicative_goal"]\n            assert item["context"]["grammar_clue"]\n'
PRACTICE_CONTEXT_NEW = '        if item["task_type"] == "context_choice":\n            assert item["context"]["situation"]\n            assert item["context"]["communicative_goal"]\n            assert item["context"]["grammar_clue"]\n            assert "model_target" not in item["context"]\n'
PRACTICE_PRODUCTIVE_OLD = '        if item["task_type"] in {\n            "guided_contextual_writing",\n            "text_mode_writing_checkpoint",\n        }:\n            assert item["context"]["communicative_goal"]\n            assert item["scoring_rubric"]["minimum_score"] == 0.8\n'
PRACTICE_PRODUCTIVE_NEW = '        if item["task_type"] in {\n            "guided_contextual_writing",\n            "text_mode_writing_checkpoint",\n        }:\n            assert item["context"]["communicative_goal"]\n            assert "model_target" not in item["context"]\n            assert item["scoring_rubric"]["minimum_score"] == 0.8\n'
PRACTICE_APPEND = '\n\ndef test_regular_plural_single_token_gap_has_unique_source_cue():\n    artifact, _, _, _ = built()\n    item = next(\n        item\n        for item in artifact["item_bank"]\n        if item["item_id"] == "GRAMMAR_REGULAR_PLURAL_NOUNS__TFX_P04"\n    )\n\n    assert item["task_type"] == "structured_gap_fill"\n    assert item["gap_spec"]["cue_contract"] == "REGULAR_PLURAL_SOURCE_FORM"\n    assert item["gap_spec"]["source_form"] == "cat"\n    assert \'"cat"\' in item["prompt"]\n    assert item["answer_key"]["canonical_target"] == "cats"\n    assert \'"cats"\' not in item["prompt"]\n\n\ndef test_learner_context_answer_leak_fails_closed():\n    artifact, _, candidate, _ = built()\n    productive = next(\n        item\n        for item in artifact["item_bank"]\n        if item["task_type"] == "guided_contextual_writing"\n    )\n    productive["context"]["model_target"] = productive["answer_key"][\n        "canonical_target"\n    ]\n\n    report = validate_artifact(artifact, candidate)\n\n    assert report["validation_status"] == "FAIL"\n    assert any(\n        error.startswith("learner_context_answer_leak:")\n        for error in report["errors"]\n    )\n'
REVIEW_IMPORT_OLD = 'from ulga.builders.run_a1_grammar_text_mode_private_pilot_next_unit import (\n    _collect_response,\n    _contains_linguistic_content,\n)\n'
REVIEW_IMPORT_NEW = 'from ulga.builders.run_a1_grammar_text_mode_private_pilot_next_unit import (\n    _collect_response,\n    _contains_linguistic_content,\n    _learner_task_material,\n    _learner_visible_context,\n)\n'
REVIEW_APPEND = '\n\ndef test_learner_visible_context_hides_legacy_model_target():\n    item = {\n        "context": {\n            "situation": "Write about more than one animal.",\n            "communicative_goal": "produce a plural noun",\n            "grammar_clue": "Use regular -s.",\n            "model_target": "cats",\n            "internal_note": "not learner-facing",\n        }\n    }\n\n    visible = _learner_visible_context(item)\n\n    assert visible == {\n        "situation": "Write about more than one animal.",\n        "communicative_goal": "produce a plural noun",\n        "grammar_clue": "Use regular -s.",\n    }\n    assert "model_target" not in visible\n\n\ndef test_learner_task_material_exposes_morphology_parts_not_answer():\n    item = {\n        "task_type": "structured_morphology_build",\n        "morphology_parts": ["es", "box"],\n        "correct_morphology_parts": ["box", "es"],\n        "answer_key": {"canonical_target": "boxes"},\n    }\n\n    material = _learner_task_material(item)\n\n    assert material == ("Supplied parts", ["es", "box"])\n    assert "boxes" not in material[1]\n\n\ndef test_learner_task_material_exposes_word_order_tokens():\n    item = {\n        "task_type": "structured_word_order",\n        "token_sequence": ["likes", "She", "cats"],\n        "correct_token_sequence": ["She", "likes", "cats"],\n    }\n\n    assert _learner_task_material(item) == (\n        "Supplied tokens",\n        ["likes", "She", "cats"],\n    )\n'


def current_branch() -> str:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"replacement_count_error:{label}:expected=1:actual={count}"
        )
    return text.replace(old, new, 1)


def main() -> int:
    branch = current_branch()
    if branch != EXPECTED_BRANCH:
        raise SystemExit(
            f"wrong_branch:expected={EXPECTED_BRANCH}:actual={branch}"
        )

    builder = BUILDER.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")
    practice_tests = PRACTICE_TEST.read_text(encoding="utf-8")
    review_tests = REVIEW_TEST.read_text(encoding="utf-8")

    marker = "test_regular_plural_single_token_gap_has_unique_source_cue"
    if marker in practice_tests:
        raise SystemExit("learner_safe_delivery_fullfix_already_applied")

    new_builder = replace_once(
        builder, CONTEXT_OLD, CONTEXT_NEW, "context"
    )
    new_builder = replace_once(
        new_builder, GAP_OLD, GAP_NEW, "gap_item"
    )
    new_builder = replace_once(
        new_builder, VALIDATOR_OLD, VALIDATOR_NEW, "validator"
    )
    new_runner = replace_once(
        runner, RUNNER_DISPLAY_OLD, RUNNER_DISPLAY_NEW, "runner_display"
    )
    new_practice_tests = replace_once(
        practice_tests,
        PRACTICE_CONTEXT_OLD,
        PRACTICE_CONTEXT_NEW,
        "practice_context_test",
    )
    new_practice_tests = replace_once(
        new_practice_tests,
        PRACTICE_PRODUCTIVE_OLD,
        PRACTICE_PRODUCTIVE_NEW,
        "practice_productive_test",
    ) + PRACTICE_APPEND
    new_review_tests = replace_once(
        review_tests,
        REVIEW_IMPORT_OLD,
        REVIEW_IMPORT_NEW,
        "review_import",
    ) + REVIEW_APPEND

    staged = {
        BUILDER: new_builder,
        RUNNER: new_runner,
        PRACTICE_TEST: new_practice_tests,
        REVIEW_TEST: new_review_tests,
    }

    with tempfile.TemporaryDirectory(prefix="r7_m105r_delivery_") as temp_dir:
        temp_root = Path(temp_dir)
        for index, (target, content) in enumerate(staged.items(), start=1):
            temp = temp_root / f"{index}_{target.name}"
            temp.write_text(content, encoding="utf-8")
            py_compile.compile(str(temp), doraise=True)

    for target, content in staged.items():
        target.write_text(content, encoding="utf-8")

    print("PASS_R7_M105R_LEARNER_SAFE_ITEM_DELIVERY_FULLFIX_APPLIED")
    for target in staged:
        print(target.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

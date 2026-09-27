from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1 import u04formv3_direct_authoring_contract as contract
from product.a1fs_v1_2_1 import u04neb02_natural_episode_bank_360 as current360

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Mechanical validation only over GPT-5.6-direct-selected Current360 bindings for "
    "Unit04 Form05-08. Python does not select episodes, mutate passages, or author learner text."
)

TASK_ID = "A1FS-V1-U04FORMV3C_GPT56Current360Binding_Form05To08"
STATUS = "PASS_A1FS_V1_U04FORMV3C_REDUCED_SUPPORT_CURRENT360_BINDING_FORM05_TO08"
REVISION = "FORMV3C_REDUCED_SUPPORT_CURRENT360_BINDING_VALIDATOR_V1"
BINDING_PATH = "product/a1fs_v1_2_1/u04formv3c_reduced_support_current360_binding_form05_08.json"
EXPECTED_FORMS = (5, 6, 7, 8)
EXPECTED_SLOTS = ("A1", "A2", "BC1", "BC2", "DE1", "DE2")
EXPECTED_CONTEXTS_PER_FORM = 6
EXPECTED_TOTAL_CONTEXTS = 24
GUIDED_FORM_PATH = "product/a1fs_v1_2_1/u04formv3c_direct_authored_form{number:02d}.json"


class Unit04ReducedSupportBindingError(ValueError):
    pass


def _root(repo_root: Path | str | None = None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _contains_surface(text: str, surface: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(surface)}(?!\w)", text, flags=re.I))


def _sentence_count(text: str) -> int:
    return len([part for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()])


def _guided_episode_ids(root: Path) -> set[str]:
    ids: set[str] = set()
    for form_number in range(1, 5):
        payload = _load_json(root / GUIDED_FORM_PATH.format(number=form_number))
        contexts = list((payload.get("form") or {}).get("contexts") or [])
        if len(contexts) != 6:
            raise Unit04ReducedSupportBindingError(f"GUIDED_CONTEXT_COUNT_DRIFT:F{form_number:02d}")
        ids.update(str(row.get("episode_id") or "") for row in contexts)
    if len(ids) != 24:
        raise Unit04ReducedSupportBindingError(f"GUIDED_EPISODE_ID_COUNT_DRIFT:{len(ids)}")
    return ids


def validate_binding(repo_root: Path | str | None = None) -> dict[str, Any]:
    root = _root(repo_root)
    payload = _load_json(root / BINDING_PATH)
    if payload.get("schema_version") != "a1fs.v1.u04.formv3c.reduced_support_current360_binding.v1":
        raise Unit04ReducedSupportBindingError("BINDING_SCHEMA_DRIFT")
    if payload.get("task_id") != TASK_ID:
        raise Unit04ReducedSupportBindingError("TASK_ID_DRIFT")
    if payload.get("stage") != "REDUCED_SUPPORT" or payload.get("support_level") != "MEDIUM":
        raise Unit04ReducedSupportBindingError("STAGE_SUPPORT_DRIFT")
    provenance = payload.get("authoring_provenance") or {}
    if provenance.get("current360_binding_author") != "GPT-5.6_SOL_DIRECT_DESIGN":
        raise Unit04ReducedSupportBindingError("BINDING_AUTHOR_DRIFT")
    for key in ("python_current360_selection_used", "python_passage_authoring_used", "python_passage_mutation_used"):
        if provenance.get(key) is not False:
            raise Unit04ReducedSupportBindingError(f"FORBIDDEN_PYTHON_ROLE:{key}")
    if payload.get("picture_interaction_active") is not False:
        raise Unit04ReducedSupportBindingError("PICTURE_INTERACTION_PREMATURELY_ACTIVE")
    if payload.get("listening_modified") is not False or payload.get("a2_a2plus_unlocked") is not False:
        raise Unit04ReducedSupportBindingError("BOUNDARY_DRIFT")

    source_report = current360.build_unit04_neb02_natural_episode_bank_360(root)
    if source_report.get("status") != current360.STATUS:
        raise Unit04ReducedSupportBindingError("CURRENT360_SOURCE_NOT_PASS")
    source_rows = {str(row["episode_id"]): dict(row) for row in source_report["effective_episodes"]}
    if len(source_rows) != 360:
        raise Unit04ReducedSupportBindingError(f"CURRENT360_COUNT_DRIFT:{len(source_rows)}")

    guided_ids = _guided_episode_ids(root)
    forms = list(payload.get("forms") or [])
    if [row.get("form_number") for row in forms] != list(EXPECTED_FORMS):
        raise Unit04ReducedSupportBindingError("FORM_IDENTITY_DRIFT")

    all_ids: list[str] = []
    form_reports: list[dict[str, Any]] = []
    for form in forms:
        form_number = int(form["form_number"])
        contexts = list(form.get("contexts") or [])
        if len(contexts) != EXPECTED_CONTEXTS_PER_FORM:
            raise Unit04ReducedSupportBindingError(f"CONTEXT_COUNT_DRIFT:F{form_number:02d}:{len(contexts)}")
        if tuple(str(row.get("slot")) for row in contexts) != EXPECTED_SLOTS:
            raise Unit04ReducedSupportBindingError(f"CONTEXT_SLOT_ORDER_DRIFT:F{form_number:02d}")
        episode_ids: list[str] = []
        target_coverage: set[str] = set()
        sentence_counts: Counter[int] = Counter()
        for row in contexts:
            episode_id = str(row.get("episode_id") or "")
            source = source_rows.get(episode_id)
            if source is None:
                raise Unit04ReducedSupportBindingError(f"UNKNOWN_CURRENT360_EPISODE:F{form_number:02d}:{episode_id}")
            if str(row.get("passage") or "") != str(source.get("passage") or ""):
                raise Unit04ReducedSupportBindingError(f"CURRENT360_PASSAGE_NOT_EXACT:F{form_number:02d}:{episode_id}")
            episode_ids.append(episode_id)
            all_ids.append(episode_id)
            sentence_counts[_sentence_count(str(row["passage"]))] += 1
            for relation in contract.TARGET_RELATIONS:
                if _contains_surface(str(row["passage"]), relation):
                    target_coverage.add(relation)
        if len(set(episode_ids)) != EXPECTED_CONTEXTS_PER_FORM:
            raise Unit04ReducedSupportBindingError(f"WITHIN_FORM_EPISODE_REUSE:F{form_number:02d}")
        if target_coverage != set(contract.TARGET_RELATIONS):
            raise Unit04ReducedSupportBindingError(
                f"TARGET_RELATION_COVERAGE_DRIFT:F{form_number:02d}:{sorted(target_coverage)}"
            )
        if any(count not in {3, 4} for count in sentence_counts):
            raise Unit04ReducedSupportBindingError(f"SOURCE_SENTENCE_COUNT_OUTSIDE_REDUCED_SUPPORT:F{form_number:02d}:{dict(sentence_counts)}")
        form_reports.append({
            "form_number": form_number,
            "episode_ids": episode_ids,
            "target_relation_coverage": sorted(target_coverage),
            "sentence_count_distribution": dict(sorted(sentence_counts.items())),
        })

    if len(all_ids) != EXPECTED_TOTAL_CONTEXTS or len(set(all_ids)) != EXPECTED_TOTAL_CONTEXTS:
        raise Unit04ReducedSupportBindingError("CROSS_FORM_EPISODE_REUSE_OR_COUNT_DRIFT")
    overlap = sorted(set(all_ids) & guided_ids)
    if overlap:
        raise Unit04ReducedSupportBindingError(f"GUIDED_REDUCED_SUPPORT_EPISODE_REUSE:{overlap}")

    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "form_count": len(forms),
        "context_count": len(all_ids),
        "unique_episode_count": len(set(all_ids)),
        "guided_overlap_count": 0,
        "current360_passages_exact": True,
        "all_forms_cover_all_target_relations": True,
        "source_sentence_count_preference_pass": True,
        "picture_interaction_active": False,
        "listening_modified": False,
        "a2_a2plus_unlocked": False,
        "forms": form_reports,
    }

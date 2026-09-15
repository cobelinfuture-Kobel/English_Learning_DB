from __future__ import annotations

import json

from product.a1fs_v1_2_1 import u04fsv2_current360_contextual_form_runtime as fsv2


def test_readback_current_d05_q31_and_shared_e05_q39_lineage() -> None:
    report = fsv2.build_unit04_fsv2_current360_contextual_form_runtime()
    rows = []
    for form_number in range(1, 21):
        d05 = next(
            row for row in report["active_items"]
            if row["form_number"] == form_number
            and row["section"] == "D"
            and row["section_activity_ordinal"] == 5
        )
        e05 = next(
            row for row in report["active_items"]
            if row["form_number"] == form_number
            and row["section"] == "E"
            and row["section_activity_ordinal"] == 5
        )
        d_lineage = d05["current360_episode_lineage"]
        e_lineage = e05["current360_episode_lineage"]
        assert d_lineage["episode_id"] == e_lineage["episode_id"]
        assert d_lineage["micro_scene_id"] == e_lineage["micro_scene_id"]
        rows.append({
            "form_number": form_number,
            "progression_stage": d05["progression_stage"],
            "d05_episode_id": d_lineage["episode_id"],
            "micro_scene_id": d_lineage["micro_scene_id"],
            "source_fact_lineage": d_lineage["source_fact_lineage"],
            "passage": d_lineage["passage"],
            "target_relation_surface": d05["target_relation_surface"],
            "existing_task_variant": d05["task_variant"],
            "shared_e05_episode_id": e_lineage["episode_id"],
        })
    print("U04_D05_Q31_CURRENT_RUNTIME_READBACK=" + json.dumps(rows, ensure_ascii=False))
    assert len(rows) == 20

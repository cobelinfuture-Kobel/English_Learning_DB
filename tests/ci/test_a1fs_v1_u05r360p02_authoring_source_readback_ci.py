from __future__ import annotations

import json

from product.a1fs_v1_2_1 import u05r360p01_natural360_source_projection as p01


def test_u05_r360_p02_authoring_source_readback(capfd):
    report = p01.build_unit05_natural360_source_projection()
    compact = []
    for cluster in report["source_clusters"]:
        compact.append({
            "cluster_id": cluster["cluster_id"],
            "scene_family": cluster["scene_family"],
            "medium_setting": cluster["medium_setting"],
            "truths": [
                {
                    "scene_ref_id": row["scene_ref_id"],
                    "frame_id": row["semantic_frame_id"],
                    "polarity": row["polarity"],
                    "subject_surface": row["subject_surface"],
                    "subject_class": row["subject_class"],
                    "complement_surface": row["complement_surface"],
                    "relation_surface": row["relation_surface"],
                    "referent_anchor": row["referent_binding_spec"].get("anchor_label"),
                    "truth_mode": row["truth_evidence_spec"].get("evidence_mode"),
                }
                for row in cluster["candidate_truth_facts"]
            ],
        })
    assert len(compact) == 36
    with capfd.disabled():
        print("U05_R360_P02_SOURCE_READBACK=" + json.dumps(compact, ensure_ascii=False, separators=(",", ":")), flush=True)

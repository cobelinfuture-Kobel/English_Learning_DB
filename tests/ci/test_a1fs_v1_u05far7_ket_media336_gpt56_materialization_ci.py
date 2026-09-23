from __future__ import annotations
from product.a1fs_v1_2_1 import u05far7_ket_media336_gpt56_materialization as media
REPORT=media.build_report()

def test_u05_far7_ket_media336_authoring_complete_but_assets_pending():
 assert REPORT["status"]==media.STATUS
 assert REPORT["ket_authored_count"]==672
 assert REPORT["text_executable_count"]==336
 assert REPORT["media_asset_pending_count"]==336
 assert set(REPORT["media_family_counts"])==media.MEDIA_FAMILIES
 assert set(REPORT["media_family_counts"].values())=={48}

def test_u05_far7_ket_media336_preserves_asset_gates():
 assert REPORT["audio_only_count"]==192
 assert REPORT["visual_only_count"]==96
 assert REPORT["audio_visual_count"]==48
 assert REPORT["audio_list_bundle_review_pass_count"]==48
 assert REPORT["actual_media_assets_generated"]==0

def test_u05_far7_ket_media336_advances_to_dictation():
 assert REPORT["next_short_step"]==media.NEXT_SHORT_STEP

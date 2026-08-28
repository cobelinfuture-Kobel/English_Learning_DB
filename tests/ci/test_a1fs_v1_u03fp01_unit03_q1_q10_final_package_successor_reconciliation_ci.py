from functools import lru_cache
import json
from ulga.builders import build_a1fs_v1_u03fp01_unit03_q1_q10_final_package_successor_reconciliation as b

@lru_cache(maxsize=1)
def p(): return b.build_export_payload()

def test_q01_q10_current_contract():
 b.validate(p()); assert list(p()["q01_q10_map"])==[f"Q{i:02d}" for i in range(1,11)]

def test_q01_q05_preserved_and_current():
 q=p()["q01_q10_map"]; assert q["Q01"]["pronoun_count"]==7 and q["Q01"]["canonical_promotion_claimed"] is False
 assert q["Q02"]["support_pool_count"]==40 and q["Q02"]["unit03_definitely_new_vocabulary_claimed"] is False
 assert q["Q03"]["closed_subject_pronoun_form_count"]==7 and q["Q03"]["generated_inflection_count"]==0
 assert q["Q04"]["cumulative_distinct_surface_rows"]==50 and q["Q04"]["unit03_new_admitted_surface_rows"]==0
 assert (q["Q05"]["current_pattern_family_count"],q["Q05"]["current_exact_frame_count"],q["Q05"]["old_eight_family_working_handoff_current"])==(7,15,False)

def test_q06_q08_provenance_preserved():
 q=p()["q01_q10_map"]; assert (q["Q06"]["unit03_new_admitted"],q["Q06"]["unit03_cumulative"],q["Q06"]["successor_sentence_assets_created"])==(18983,26514,0)
 assert (q["Q07"]["pronoun_scene_covered"],q["Q07"]["structural_pronoun_projection_rows"],q["Q07"]["unit03_new_canonical_scenes"])==(7,540,0)
 assert q["Q08"]["functions"]==["IDENTIFY","DESCRIBE","QUANTITY_PLURALITY","REFERENCE_TRACKING"] and q["Q08"]["missing_function_count"]==0

def test_q09_q10_current_successor():
 q=p()["q01_q10_map"]; assert q["Q09"]["task_family_count"]==10 and q["Q09"]["family_11_created"] is False and q["Q09"]["connected_passage_question_type_count"]==6
 assert q["Q10"]["materialization_identity"]=="U03Q10R1_SUCCESSOR_20X40_6_10_10_8_6"
 assert (q["Q10"]["form_count"],q["Q10"]["activities_per_form"],q["Q10"]["runtime_occurrence_count"])==(20,40,800)
 assert q["Q10"]["section_counts_per_form"]=={"A":6,"B":10,"C":10,"D":8,"E":6} and q["Q10"]["global_800_distinct_selected_item_proof"] is True

def test_learner_current_and_history():
 l=p()["learner_facing_current"]; assert (l["form_count"],l["activity_count"],l["rendered_activity_count"],l["connected_passage_question_count"])==(20,800,800,120)
 h=p()["historical_provenance"]; assert h["old_q10_runtime_count"]==640 and h["old_q10_current"] is False and h["u03scfv2_runtime_count"]==800 and h["u03scfv2_current"] is False and h["current_successor_identity_is_new"] is True

def test_write_exports_only_q09_q10_and_manifest(tmp_path):
 paths=b.write_exports(tmp_path); assert set(paths)==set(b.EXPORT_FILENAMES) and all(x.is_file() for x in paths.values())
 assert not any(x.name in {"Unit03_Q01_Grammar.json","Unit03_Q03_Pronoun_Forms.json","Unit03_Q04_Chunks.json","Unit03_Q06_Sentence_Assets.json","Unit03_Q07_MicroScene_Coverage.json","Unit03_Q08_Communicative_Functions.json"} for x in paths.values())
 m=json.loads(paths[b.MANIFEST].read_text(encoding="utf-8")); assert m["export_contract"]["q01_q08_reexported"] is False and m["claim_boundaries"]["q09_q10_read_only_export"] is True

def test_boundaries_and_next():
 x=p()["claim_boundaries"]; assert x["q09_q10_read_only_export"] is True
 assert all(v is False for k,v in x.items() if k!="q09_q10_read_only_export")
 assert p()["next_short_step"]==b.NEXT_SHORT_STEP
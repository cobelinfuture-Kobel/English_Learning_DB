from copy import deepcopy
import pytest
from ulga.builders import build_a1fs_v1_r7_route_batch_execution_and_replay_closure as r7

def sources():
    item={"item_id":"I","level":"A1","skill":"READING","candidate_sha256":"a"*64,"stimulus_fingerprint":"b"*64,
          "learner_contract":{"response_mode":"short_text"},"private_scoring_contract":{"human_review_fallback":False}}
    deps=[]
    for i in range(209):
        deps.append({"work_item_id":f"W{i}","finding_id":f"F{i}","breadth_cell_id":f"B{i}","selected_item_id":f"I{i}",
                     "selected_stimulus_fingerprint":"b"*64})
    items=[{**item,"item_id":f"I{i}"} for i in range(209)]
    controller={"next_short_step":r7.TASK_ID}; controller["controller_sha256"]=r7.digest(controller)
    queue={}; queue["queue_sha256"]=r7.digest(queue)
    bank={"items":items}; bank["bank_sha256"]=r7.digest(bank)
    deployment={"counts":{"ready_for_real_learner_session_count":209,"blocked_approved_supply_required_count":0},
                "deployments":deps,
                "source_bindings":{"r7_queue_sha256":queue["queue_sha256"],"r4_bank_sha256":bank["bank_sha256"]},
                "runtime_consumer_contract":{"consumer_builder":"r5.py","start_command_template":"start"}}
    deployment["deployment_queue_sha256"]=r7.digest(deployment)
    return controller,queue,deployment,bank

def test_missing_evidence_builds_single_item_safe_batches_and_is_idempotent():
    c,q,d,b=sources(); first=r7.build(controller=c,queue=q,deployment_queue=d,bank=b,packages=[])
    second=r7.build(controller=c,queue=q,deployment_queue=d,bank=b,packages=[],previous_session=first[2])
    assert first==second
    assert first[0]["counts"]["learner_attempt_missing_count"]==209
    assert first[2]["session_batch_count"]==209
    assert all(len(row["work_item_ids"])==1 for row in first[2]["session_batches"])
    r7.safe_scan(first[1]); r7.safe_scan(first[3])

def test_valid_exact_attempt_is_classified_without_copying_raw_response():
    c,q,d,b=sources(); dep=d["deployments"][0]
    attempt={"attempt_id":"A","attempt_hash":"1"*64,"session_id":"S","item_id":"I0","breadth_cell_id":"B0",
             "stimulus_fingerprint":"b"*64,"response":"real response","submitted_at":"2026-01-01T00:00:00Z",
             "score":1,"outcome":"PASS","validity_status":"VALID","human_review_required":False}
    package={"entries":[attempt]}; package["package_sha256"]=r7.digest(package)
    result=r7.build(controller=c,queue=q,deployment_queue=d,bank=b,packages=[package])
    assert result[0]["counts"]["valid_real_evidence_ready_count"]==1
    assert "real response" not in r7.canonical(result[0])
    assert result[2]["session_batch_count"]==208

def test_synthetic_evidence_fails_closed():
    c,q,d,b=sources(); package={"entries":[{"synthetic":True}]}; package["package_sha256"]=r7.digest(package)
    with pytest.raises(r7.ExecutionError,match="synthetic_evidence_prohibited"):
        r7.build(controller=c,queue=q,deployment_queue=d,bank=b,packages=[package])

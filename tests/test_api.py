"""
Integration and End-to-End Test Suite for MediKiosk
Validates the complete 10-hour SIH 2026 build specifications.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.seed import seed_database
from backend.app.ml.document_ai import check_abnormal_lab, check_drug_interactions

client = TestClient(app)

def setup_module():
    """Seed clean state before running tests."""
    seed_database()

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
    assert res.json()["ayush_aiia_ready"] is True

def test_mock_abha_login():
    res = client.post("/auth/abha-login", json={"abha_id": "91-8822-1144-5566", "otp": "123456"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "token" in data
    assert data["name"] == "Smt. Shanti Devi"

def test_dpdp_consent():
    res = client.post("/consent", json={
        "patient_id": "p_001",
        "storage_consent": True,
        "doctor_access": True,
        "research_consent": True
    })
    assert res.status_code == 200
    assert res.json()["dpdp_compliant"] is True

def test_interview_flow_and_red_flag():
    # Start interview
    res = client.post("/interview/start", json={
        "patient_id": "p_001",
        "language": "hi",
        "mode": "standard_and_ayush"
    })
    assert res.status_code == 200
    session_id = res.json()["session_id"]
    assert session_id.startswith("ses_")

    # Answer Chief Complaint -> chest pain
    res_ans1 = client.post("/interview/answer", json={
        "session_id": session_id,
        "question_id": "complaint_select",
        "answer_value": "chest_pain"
    })
    assert res_ans1.status_code == 200
    assert res_ans1.json()["next_question"]["id"] == "cp_site"

    # Answer Associated symptoms with sweating and breathlessness -> MUST TRIGGER RED FLAG
    res_flag = client.post("/interview/answer", json={
        "session_id": session_id,
        "question_id": "cp_associated",
        "answer_value": ["cold_sweating", "breathlessness"]
    })
    assert res_flag.status_code == 200
    red_flags = res_flag.json()["red_flags"]
    assert len(red_flags) > 0
    assert red_flags[0]["code"] == "EMERGENCY_ACS_CARDIAC"

def test_abnormal_lab_detection():
    eval_hba1c = check_abnormal_lab("HbA1c", 8.6)
    assert eval_hba1c["status"] == "HIGH"
    assert eval_hba1c["is_abnormal"] is True

    eval_creat = check_abnormal_lab("Serum Creatinine", 1.8)
    assert eval_creat["status"] == "HIGH"
    assert eval_creat["is_abnormal"] is True

    eval_hb = check_abnormal_lab("Hemoglobin", 13.5)
    assert eval_hb["status"] == "NORMAL"
    assert eval_hb["is_abnormal"] is False

def test_drug_interaction_detection():
    # Warfarin + Aspirin
    interactions = check_drug_interactions(["Warfarin 2.5mg", "Aspirin 75mg", "Amlodipine 5mg"])
    assert len(interactions) >= 1
    assert interactions[0]["severity"] == "CRITICAL"
    assert "Warfarin" in interactions[0]["pair"] and "Aspirin" in interactions[0]["pair"]

def test_doctor_queue_red_flag_pinning():
    res = client.get("/doctor/queue")
    assert res.status_code == 200
    queue = res.json()["queue"]
    assert len(queue) >= 2
    # First patient in queue MUST have red_flag_alert == True
    assert queue[0]["red_flag_alert"] is True
    assert queue[0]["token_number"] == "TK-042"

def test_summary_and_fhir_his_push():
    # Verify summary fetch
    res = client.get("/summary/sum_demo_01")
    assert res.status_code == 200
    sum_data = res.json()
    assert sum_data["red_flag_alert"] is True
    assert "[Patient Stated]" in sum_data["summary"]["sections"]["chief_complaint"]

    # Confirm summary by doctor
    res_confirm = client.post("/summary/sum_demo_01/confirm", json={"decision": "ACCEPT", "doctor_notes": "Emergency ECG ordered."})
    assert res_confirm.status_code == 200
    assert res_confirm.json()["decision"] == "ACCEPT"

    # Push to HIS and get FHIR R4 Bundle
    res_his = client.post("/his/push", json={"summary_id": "sum_demo_01"})
    assert res_his.status_code == 200
    bundle = res_his.json()["fhir_bundle"]
    assert bundle["resourceType"] == "Bundle"
    
    # Check bundled FHIR resources
    types = [e["resource"]["resourceType"] for e in bundle["entry"]]
    assert "Patient" in types
    assert "Condition" in types
    assert "MedicationStatement" in types
    assert "Observation" in types

def test_dpdp_session_wipe():
    res = client.delete("/session/ses_demo_01")
    assert res.status_code == 200
    assert res.json()["status"] == "wiped"

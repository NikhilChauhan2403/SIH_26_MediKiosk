import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.seed import seed_database
from backend.app.ml.document_ai import check_abnormal_lab, check_drug_interactions

class TestMediKioskSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database()
        cls.client = TestClient(app)

    def test_01_health_check(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["ayush_aiia_ready"])

    def test_02_mock_abha_login(self):
        res = self.client.post("/auth/abha-login", json={"abha_id": "91-8822-1144-5566", "otp": "123456"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("token", data)
        self.assertEqual(data["name"], "Smt. Shanti Devi")

    def test_03_dpdp_consent(self):
        res = self.client.post("/consent", json={
            "patient_id": "p_001",
            "storage_consent": True,
            "doctor_access": True,
            "research_consent": True
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["dpdp_compliant"])

    def test_04_interview_flow_and_red_flag(self):
        # 1. Start interview
        res = self.client.post("/interview/start", json={
            "patient_id": "p_001",
            "language": "hi",
            "mode": "standard_and_ayush"
        })
        self.assertEqual(res.status_code, 200)
        session_id = res.json()["session_id"]
        self.assertTrue(session_id.startswith("ses_"))

        # 2. Select Chief Complaint: Chest Pain
        res_ans1 = self.client.post("/interview/answer", json={
            "session_id": session_id,
            "question_id": "complaint_select",
            "answer_value": "chest_pain"
        })
        self.assertEqual(res_ans1.status_code, 200)
        self.assertEqual(res_ans1.json()["next_question"]["id"], "cp_site")

        # 3. Associated symptoms with sweating and breathlessness -> MUST TRIGGER RED FLAG
        res_flag = self.client.post("/interview/answer", json={
            "session_id": session_id,
            "question_id": "cp_associated",
            "answer_value": ["cold_sweating", "breathlessness"]
        })
        self.assertEqual(res_flag.status_code, 200)
        red_flags = res_flag.json()["red_flags"]
        self.assertGreater(len(red_flags), 0)
        self.assertEqual(red_flags[0]["code"], "EMERGENCY_ACS_CARDIAC")

    def test_05_abnormal_lab_detection(self):
        eval_hba1c = check_abnormal_lab("HbA1c", 8.6)
        self.assertEqual(eval_hba1c["status"], "HIGH")
        self.assertTrue(eval_hba1c["is_abnormal"])

        eval_creat = check_abnormal_lab("Serum Creatinine", 1.8)
        self.assertEqual(eval_creat["status"], "HIGH")
        self.assertTrue(eval_creat["is_abnormal"])

        eval_hb = check_abnormal_lab("Hemoglobin", 13.5)
        self.assertEqual(eval_hb["status"], "NORMAL")
        self.assertFalse(eval_hb["is_abnormal"])

    def test_06_drug_interaction_detection(self):
        # Concurrent Warfarin and Aspirin
        interactions = check_drug_interactions(["Warfarin 2.5mg", "Aspirin 75mg", "Amlodipine 5mg"])
        self.assertGreaterEqual(len(interactions), 1)
        self.assertEqual(interactions[0]["severity"], "CRITICAL")
        pair = interactions[0]["pair"]
        self.assertTrue("Warfarin" in pair and "Aspirin" in pair)

    def test_07_doctor_queue_red_flag_priority(self):
        res = self.client.get("/doctor/queue")
        self.assertEqual(res.status_code, 200)
        queue = res.json()["queue"]
        self.assertGreaterEqual(len(queue), 2)
        # CRITICAL TEST: Red flag alert case MUST be strictly #1 at the top of the queue
        self.assertTrue(queue[0]["red_flag_alert"])
        self.assertEqual(queue[0]["token_number"], "TK-042")

    def test_08_summary_doctor_review_and_fhir_push(self):
        # 1. Fetch summary
        res = self.client.get("/summary/sum_demo_01")
        self.assertEqual(res.status_code, 200)
        sum_data = res.json()
        self.assertTrue(sum_data["red_flag_alert"])
        self.assertIn("[Patient Stated]", sum_data["summary"]["sections"]["chief_complaint"])

        # 2. Confirm summary by doctor
        res_confirm = self.client.post("/summary/sum_demo_01/confirm", json={
            "decision": "ACCEPT",
            "doctor_notes": "Emergency ECG ordered. Troponin-I sent."
        })
        self.assertEqual(res_confirm.status_code, 200)
        self.assertEqual(res_confirm.json()["decision"], "ACCEPT")

        # 3. Export to HIS and generate HL7 FHIR R4 Bundle
        res_his = self.client.post("/his/push", json={"summary_id": "sum_demo_01"})
        self.assertEqual(res_his.status_code, 200)
        bundle = res_his.json()["fhir_bundle"]
        self.assertEqual(bundle["resourceType"], "Bundle")
        
        # Verify FHIR resource contents
        types = [e["resource"]["resourceType"] for e in bundle["entry"]]
        self.assertIn("Patient", types)
        self.assertIn("Condition", types)
        self.assertIn("MedicationStatement", types)
        self.assertIn("Observation", types)

    def test_09_dpdp_session_wipe(self):
        res = self.client.delete("/session/ses_demo_01")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "wiped")

if __name__ == "__main__":
    unittest.main(verbosity=2)

import json
import datetime
from .database import get_db, init_db
from .security import hash_password
from .ml.document_ai import extract_and_analyze_document
from .ml.summary_generator import generate_clinical_summary

def seed_database():
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    # Clear prior data for fresh demo
    cursor.execute("DELETE FROM his_records")
    cursor.execute("DELETE FROM alerts")
    cursor.execute("DELETE FROM summaries")
    cursor.execute("DELETE FROM documents")
    cursor.execute("DELETE FROM consents")
    cursor.execute("DELETE FROM sessions")
    cursor.execute("DELETE FROM patients")

    # 1. Staff / Doctor User
    doc_id = "doc_aiia_01"
    cursor.execute("""
        INSERT INTO patients (id, abha_id, name, age, gender, phone, role, password_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (doc_id, "91-0000-1111-2222", "Dr. A. K. Sharma (MD, AIIA)", 48, "Male", "9810012345", "doctor", hash_password("doctor123")))

    # 2. Patient 1: Smt. Shanti Devi (Chest Pain + Red Flag Demo Patient)
    p1_id = "p_001"
    cursor.execute("""
        INSERT INTO patients (id, abha_id, name, age, gender, phone, role, password_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (p1_id, "91-8822-1144-5566", "Smt. Shanti Devi", 62, "Female", "9876543210", "patient", hash_password("patient123")))

    # Patient 1 Consent (DPDP compliant)
    cursor.execute("""
        INSERT INTO consents (id, patient_id, storage_consent, doctor_access, research_consent)
        VALUES (?, ?, ?, ?, ?)
    """, ("cns_001", p1_id, 1, 1, 1))

    # Patient 1 Interview State (Acute Chest Pain with SOCRATES details)
    p1_state = {
        "patient_id": p1_id,
        "language": "hi",
        "mode": "standard_and_ayush",
        "chief_complaint": "chest_pain",
        "hpi": {
            "site": "center_substernal",
            "onset": "last_2_hours",
            "character": "heavy_pressure",
            "radiation": ["left_arm", "jaw_neck"],
            "associated": ["cold_sweating", "breathlessness"],
            "exacerbating_relieving": "worse_exertion_better_rest",
            "severity": 8
        },
        "past_history": {
            "medical": ["Hypertension (5 years)", "Type 2 Diabetes Mellitus (3 years)"]
        },
        "drugs": ["Amlodipine 5mg OD", "Metformin 500mg BD"],
        "allergies": ["Penicillin"],
        "ayush": {
            "prakriti": "pitta",
            "agni": "vishamagni",
            "koshtha": "madhyama",
            "ahara_vihara": ["ratri_jagarana", "manasika_chinta"]
        },
        "red_flags": [
            {
                "code": "EMERGENCY_ACS_CARDIAC",
                "title": "Suspected Acute Coronary Syndrome (ACS) / Myocardial Infarction",
                "message_en": "CRITICAL EMERGENCY: Signs of heart distress (Chest pain with cold sweating/breathlessness). Route to Triage & Emergency Desk IMMEDIATELY.",
                "message_hi": "अति आवश्यक आपातकाल: हृदय संबंधी गंभीर लक्षण (सीने में दर्द व पसीना/सांस फूलना)। कृपया तुरंत आपातकालीन डेस्क (Emergency Desk) पर संपर्क करें।",
                "action": "Immediate ECG, Oxygen saturation check, and Doctor Emergency Alert."
            }
        ],
        "answered_questions": ["complaint_select", "cp_site", "cp_onset", "cp_character", "cp_radiation", "cp_associated", "cp_exacerbating", "cp_severity", "past_conditions", "current_drugs", "allergies", "ayush_prakriti", "ayush_agni", "ayush_koshtha", "ayush_ahara_vihara"],
        "current_step": 15,
        "completed": True
    }

    cursor.execute("""
        INSERT INTO sessions (id, patient_id, language, mode, state_json, is_active)
        VALUES (?, ?, ?, ?, ?, 1)
    """, ("ses_demo_01", p1_id, "hi", "standard_and_ayush", json.dumps(p1_state)))

    # Patient 1 Documents (Prescription + Lab Report)
    doc1 = extract_and_analyze_document("prescription_cardiology.pdf", demo_type="cardiology")
    doc1["document_id"] = "doc_p1_01"
    doc1["patient_id"] = p1_id

    doc2 = extract_and_analyze_document("biochemistry_lab_report.pdf", demo_type="lab")
    doc2["document_id"] = "doc_p1_02"
    doc2["patient_id"] = p1_id

    cursor.execute("""
        INSERT INTO documents (id, patient_id, filename, doc_type, document_date, encrypted_path, extracted_json, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (doc1["document_id"], p1_id, "prescription_cardiology.pdf", doc1["doc_type"], doc1["document_date"], "encrypted_vault", json.dumps(doc1), 0.94))

    cursor.execute("""
        INSERT INTO documents (id, patient_id, filename, doc_type, document_date, encrypted_path, extracted_json, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (doc2["document_id"], p1_id, "biochemistry_lab_report.pdf", doc2["doc_type"], doc2["document_date"], "encrypted_vault", json.dumps(doc2), 0.97))

    # Patient 1 Summary (Drafted with RED FLAG)
    summary_data = generate_clinical_summary(p1_state, [doc1, doc2], {"id": p1_id, "name": "Smt. Shanti Devi", "age": 62, "gender": "Female"})
    cursor.execute("""
        INSERT INTO summaries (id, patient_id, session_id, token_number, status, red_flag_alert, summary_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("sum_demo_01", p1_id, "ses_demo_01", "TK-042", "pending_review", 1, json.dumps(summary_data)))

    # Record Active Red Flag Alert
    cursor.execute("""
        INSERT INTO alerts (id, patient_id, session_id, title, message_en, message_hi, severity, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("alt_001", p1_id, "ses_demo_01", "Suspected ACS / Cardiac Emergency", 
           "Chest pain radiating to left arm with profuse sweating. Priority Triage.", 
           "सीने में तेज दर्द, पसीना व सांस में तकलीफ। आपातकालीन परामर्श आवश्यक।", "CRITICAL", "ACTIVE"))

    # 3. Patient 2: Rajesh Kumar (Fever Case)
    p2_id = "p_002"
    cursor.execute("""
        INSERT INTO patients (id, abha_id, name, age, gender, phone, role, password_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (p2_id, "91-9933-2255-7788", "Rajesh Kumar", 28, "Male", "9823456789", "patient", hash_password("patient123")))

    p2_state = {
        "patient_id": p2_id, "language": "en", "chief_complaint": "fever",
        "hpi": {"duration": "2_4_days", "pattern": "high_chills", "associated": ["body_ache"]},
        "past_history": {"medical": []}, "drugs": ["Paracetamol 650mg SOS"], "allergies": [],
        "ayush": {"prakriti": "pitta", "agni": "tikshnagni"},
        "red_flags": [], "completed": True
    }
    p2_sum = generate_clinical_summary(p2_state, [], {"id": p2_id, "name": "Rajesh Kumar", "age": 28, "gender": "Male"})
    cursor.execute("""
        INSERT INTO summaries (id, patient_id, session_id, token_number, status, red_flag_alert, summary_json)
        VALUES (?, ?, ?, ?, ?, 0, ?)
    """, ("sum_demo_02", p2_id, "ses_demo_02", "TK-019", "pending_review", json.dumps(p2_sum)))

    # 4. Patient 3: Meera Bai (Headache, Accepted Case)
    p3_id = "p_003"
    cursor.execute("""
        INSERT INTO patients (id, abha_id, name, age, gender, phone, role, password_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (p3_id, "91-7711-3366-9900", "Meera Bai", 45, "Female", "9834567890", "patient", hash_password("patient123")))

    p3_state = {
        "patient_id": p3_id, "language": "hi", "chief_complaint": "headache",
        "hpi": {"onset_type": "gradual_hours", "associated": ["photophobia_nausea"]},
        "past_history": {"medical": ["Migraine"]}, "drugs": [], "allergies": [],
        "ayush": {"prakriti": "vata", "agni": "samagni"},
        "red_flags": [], "completed": True
    }
    p3_sum = generate_clinical_summary(p3_state, [], {"id": p3_id, "name": "Meera Bai", "age": 45, "gender": "Female"})
    cursor.execute("""
        INSERT INTO summaries (id, patient_id, session_id, token_number, status, red_flag_alert, summary_json, doctor_notes, doctor_decision)
        VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)
    """, ("sum_demo_03", p3_id, "ses_demo_03", "TK-008", "accepted", json.dumps(p3_sum), "Verified classical migraine with aura. Advised sleep hygiene and hydration.", "ACCEPT"))

    conn.commit()
    conn.close()
    print("Database successfully seeded with realistic multi-lingual clinic demo data.")

if __name__ == "__main__":
    seed_database()

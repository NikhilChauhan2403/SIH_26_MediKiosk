import json
from fastapi import APIRouter, HTTPException, Depends
from ..database import get_db

router = APIRouter(prefix="/patient", tags=["Patient Health Record Portal"])

@router.get("/timeline/{patient_id}")
def get_patient_timeline(patient_id: str):
    """
    Returns an aggregated chronological timeline of patient encounters,
    uploaded prescriptions/labs, and verified summaries.
    """
    conn = get_db()
    cursor = conn.cursor()

    # 1. Patient profile
    cursor.execute("SELECT id, abha_id, name, age, gender, phone FROM patients WHERE id = ?", (patient_id,))
    patient = cursor.fetchone()
    if not patient:
        conn.close()
        raise HTTPException(status_code=404, detail="Patient not found.")

    # 2. Documents
    cursor.execute("SELECT * FROM documents WHERE patient_id = ? ORDER BY document_date DESC", (patient_id,))
    docs = [json.loads(d["extracted_json"]) for d in cursor.fetchall() if d["extracted_json"]]

    # 3. Summaries
    cursor.execute("SELECT * FROM summaries WHERE patient_id = ? ORDER BY created_at DESC", (patient_id,))
    summaries = []
    for s in cursor.fetchall():
        s_obj = json.loads(s["summary_json"]) if s["summary_json"] else {}
        summaries.append({
            "summary_id": s["id"],
            "token_number": s["token_number"],
            "status": s["status"],
            "doctor_decision": s["doctor_decision"],
            "doctor_notes": s["doctor_notes"],
            "created_at": s["created_at"],
            "chief_complaint": s_obj.get("sections", {}).get("chief_complaint", ""),
            "red_flags": s_obj.get("red_flags", []),
            "patient_summary": s_obj.get("patient_vernacular_summary", "")
        })

    # 4. Consent status
    cursor.execute("SELECT * FROM consents WHERE patient_id = ? ORDER BY timestamp DESC LIMIT 1", (patient_id,))
    consent_row = cursor.fetchone()
    consent_info = dict(consent_row) if consent_row else {"active": False, "revoked": 0}

    conn.close()

    return {
        "patient": dict(patient),
        "consent": consent_info,
        "documents": docs,
        "consultations": summaries
    }

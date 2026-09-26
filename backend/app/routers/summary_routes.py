import uuid
import json
import random
import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from ..database import get_db
from ..ml.summary_generator import generate_clinical_summary

router = APIRouter(prefix="/summary", tags=["Clinical Summary & Review"])

class GenerateSummaryRequest(BaseModel):
    patient_id: str
    session_id: str

class PatchSummaryRequest(BaseModel):
    doctor_notes: Optional[str] = None
    edited_sections: Optional[Dict[str, str]] = None

class ConfirmSummaryRequest(BaseModel):
    decision: str  # "ACCEPT" or "REJECT"
    doctor_notes: Optional[str] = ""

@router.post("/generate")
def generate_summary(req: GenerateSummaryRequest):
    conn = get_db()
    cursor = conn.cursor()

    # 1. Fetch patient
    cursor.execute("SELECT * FROM patients WHERE id = ?", (req.patient_id,))
    patient = cursor.fetchone()
    if not patient:
        conn.close()
        raise HTTPException(status_code=404, detail="Patient record not found.")

    # 2. Fetch session
    cursor.execute("SELECT * FROM sessions WHERE id = ?", (req.session_id,))
    session_row = cursor.fetchone()
    if not session_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Session record not found.")
    
    interview_state = json.loads(session_row["state_json"]) if session_row["state_json"] else {}

    # 3. Fetch patient documents
    cursor.execute("SELECT extracted_json FROM documents WHERE patient_id = ?", (req.patient_id,))
    doc_rows = cursor.fetchall()
    documents = [json.loads(d["extracted_json"]) for d in doc_rows if d["extracted_json"]]

    # 4. Generate draft summary
    summary_data = generate_clinical_summary(interview_state, documents, dict(patient))

    # 5. Generate token number
    token_num = f"TK-{random.randint(10, 99)}"
    summary_id = f"sum_{uuid.uuid4().hex[:8]}"
    has_red_flags = 1 if summary_data.get("red_flag_alert") else 0

    cursor.execute("""
        INSERT INTO summaries (id, patient_id, session_id, token_number, status, red_flag_alert, summary_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        summary_id,
        req.patient_id,
        req.session_id,
        token_num,
        "pending_review",
        has_red_flags,
        json.dumps(summary_data)
    ))

    conn.commit()
    conn.close()

    return {
        "status": "generated",
        "summary_id": summary_id,
        "token_number": token_num,
        "patient_name": patient["name"],
        "red_flag_alert": bool(has_red_flags),
        "summary": summary_data
    }

@router.get("/{id}")
def get_summary(id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, p.name as patient_name, p.age, p.gender, p.abha_id, p.phone
        FROM summaries s
        JOIN patients p ON s.patient_id = p.id
        WHERE s.id = ?
    """, (id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Clinical summary not found.")

    summary_obj = json.loads(row["summary_json"]) if row["summary_json"] else {}
    return {
        "summary_id": row["id"],
        "patient_id": row["patient_id"],
        "patient_name": row["patient_name"],
        "age": row["age"],
        "gender": row["gender"],
        "abha_id": row["abha_id"],
        "token_number": row["token_number"],
        "status": row["status"],
        "red_flag_alert": bool(row["red_flag_alert"]),
        "doctor_notes": row["doctor_notes"],
        "doctor_decision": row["doctor_decision"],
        "created_at": row["created_at"],
        "reviewed_at": row["reviewed_at"],
        "summary": summary_obj
    }

@router.patch("/{id}")
def edit_summary(id: str, req: PatchSummaryRequest):
    """Allows doctor to edit sections or add physician notes."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT summary_json, doctor_notes FROM summaries WHERE id = ?", (id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Clinical summary not found.")

    data = json.loads(row["summary_json"])
    if req.edited_sections:
        for sec_key, sec_val in req.edited_sections.items():
            data["sections"][sec_key] = f"{sec_val} [Edited by Doctor]"

    notes = req.doctor_notes if req.doctor_notes is not None else row["doctor_notes"]

    cursor.execute("""
        UPDATE summaries SET summary_json = ?, doctor_notes = ?, reviewed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (json.dumps(data), notes, id))

    conn.commit()
    conn.close()

    return {
        "status": "updated",
        "summary_id": id,
        "doctor_notes": notes,
        "summary": data
    }

@router.post("/{id}/confirm")
def confirm_summary(id: str, req: ConfirmSummaryRequest):
    """Physician confirms with ACCEPT or REJECT decision."""
    decision = req.decision.upper()
    if decision not in ["ACCEPT", "REJECT"]:
        raise HTTPException(status_code=400, detail="Decision must be either 'ACCEPT' or 'REJECT'")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE summaries
        SET status = ?, doctor_decision = ?, doctor_notes = ?, reviewed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, ("accepted" if decision == "ACCEPT" else "rejected", decision, req.doctor_notes, id))

    conn.commit()
    conn.close()

    return {
        "status": "confirmed",
        "summary_id": id,
        "decision": decision,
        "reviewed_at": datetime.datetime.now().isoformat(),
        "ready_for_his_push": decision == "ACCEPT"
    }

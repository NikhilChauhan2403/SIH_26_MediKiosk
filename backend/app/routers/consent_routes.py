import uuid
import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..database import get_db

router = APIRouter(prefix="/consent", tags=["Consent & DPDP Compliance"])

class ConsentRequest(BaseModel):
    patient_id: str
    storage_consent: bool = True
    doctor_access: bool = True
    research_consent: bool = False

@router.post("")
def record_consent(req: ConsentRequest):
    conn = get_db()
    cursor = conn.cursor()
    
    consent_id = f"cns_{uuid.uuid4().hex[:8]}"
    cursor.execute("""
        INSERT INTO consents (id, patient_id, storage_consent, doctor_access, research_consent)
        VALUES (?, ?, ?, ?, ?)
    """, (consent_id, req.patient_id, int(req.storage_consent), int(req.doctor_access), int(req.research_consent)))

    conn.commit()
    conn.close()

    return {
        "status": "recorded",
        "consent_id": consent_id,
        "patient_id": req.patient_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "dpdp_compliant": True,
        "message": "Consent recorded under Digital Personal Data Protection (DPDP) Act 2023."
    }

@router.get("/{patient_id}")
def get_consent(patient_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM consents WHERE patient_id = ? ORDER BY timestamp DESC LIMIT 1", (patient_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"status": "none", "active": False}

    return dict(row)

@router.delete("/{patient_id}")
def revoke_consent(patient_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE consents SET revoked = 1, revoked_at = CURRENT_TIMESTAMP
        WHERE patient_id = ?
    """, (patient_id,))
    conn.commit()
    conn.close()

    return {
        "status": "revoked",
        "patient_id": patient_id,
        "revoked_at": datetime.datetime.now().isoformat(),
        "message": "Patient consent has been revoked. Data sharing halted per DPDP Act."
    }

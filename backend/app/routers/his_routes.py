import uuid
import json
import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..database import get_db
from ..ml.fhir_builder import build_fhir_bundle

router = APIRouter(prefix="/his", tags=["Hospital Information System (HIS) & FHIR R4"])

class PushHisRequest(BaseModel):
    summary_id: str

@router.post("/push")
def push_to_his(req: PushHisRequest):
    """
    Transforms the verified clinical case summary into an HL7 FHIR R4 Bundle
    and records it into the hospital's electronic health record (mock HIS).
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.*, p.name, p.abha_id, p.gender, p.age, p.phone
        FROM summaries s
        JOIN patients p ON s.patient_id = p.id
        WHERE s.id = ?
    """, (req.summary_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Summary not found.")

    summary_data = json.loads(row["summary_json"]) if row["summary_json"] else {}
    patient_info = {
        "id": row["patient_id"],
        "name": row["name"],
        "abha_id": row["abha_id"],
        "gender": row["gender"],
        "phone": row["phone"],
        "dob": f"{2026 - row['age']}-01-01" if row["age"] else "1980-01-01"
    }

    # Generate standards-compliant FHIR R4 Bundle
    fhir_bundle = build_fhir_bundle(summary_data, patient_info)

    his_record_id = f"his_{uuid.uuid4().hex[:8]}"
    cursor.execute("""
        INSERT INTO his_records (id, patient_id, summary_id, fhir_bundle_json, status)
        VALUES (?, ?, ?, ?, ?)
    """, (his_record_id, row["patient_id"], req.summary_id, json.dumps(fhir_bundle), "COMMITTED_TO_HIS"))

    conn.commit()
    conn.close()

    return {
        "status": "pushed",
        "his_record_id": his_record_id,
        "patient_id": row["patient_id"],
        "patient_name": row["name"],
        "pushed_at": datetime.datetime.now().isoformat(),
        "fhir_resource_type": fhir_bundle.get("resourceType"),
        "fhir_entries_count": len(fhir_bundle.get("entry", [])),
        "fhir_bundle": fhir_bundle
    }

@router.get("/records")
def list_his_records():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT h.id, h.patient_id, h.summary_id, h.pushed_at, h.status, p.name as patient_name, p.abha_id
        FROM his_records h
        JOIN patients p ON h.patient_id = p.id
        ORDER BY h.pushed_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return {"records": [dict(r) for r in rows]}

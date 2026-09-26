import uuid
import json
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from ..database import get_db
from ..security import encrypt_and_save_file
from ..ml.document_ai import extract_and_analyze_document, SAMPLE_DEMO_DOCUMENTS

router = APIRouter(prefix="/documents", tags=["Document AI & Timeline"])

class PatchDocumentRequest(BaseModel):
    field_path: str
    corrected_value: Any

class PreloadedUploadRequest(BaseModel):
    patient_id: str
    demo_doc_id: str # 'doc_demo_chest_pain_01', 'doc_demo_lab_diabetic_02', 'doc_demo_ayush_slip_03'

@router.post("/upload")
async def upload_document(
    patient_id: str = Form(...),
    file: Optional[UploadFile] = File(None),
    demo_type: Optional[str] = Form(None)
):
    """
    Accepts an uploaded image/PDF file or demo template trigger.
    Encrypts file at rest (Fernet cipher), extracts structured clinical entities,
    computes lab range flags and drug-drug interactions.
    """
    filename = file.filename if file else f"record_{demo_type or 'prescription'}.pdf"
    content_bytes = await file.read() if file else b"MOCK_DOCUMENT_CONTENT"

    # Encrypt file at rest per DPDP security requirements
    encrypted_path = encrypt_and_save_file(content_bytes, filename, patient_id)

    # Perform Document AI extraction
    extracted = extract_and_analyze_document(filename, content_bytes, demo_type=demo_type)

    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    extracted["document_id"] = doc_id
    extracted["patient_id"] = patient_id

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO documents (id, patient_id, filename, doc_type, document_date, encrypted_path, extracted_json, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        doc_id,
        patient_id,
        filename,
        extracted["doc_type"],
        extracted["document_date"],
        encrypted_path,
        json.dumps(extracted),
        extracted["confidence_overall"]
    ))
    conn.commit()
    conn.close()

    return {
        "status": "extracted",
        "document_id": doc_id,
        "extracted_data": extracted
    }

@router.post("/preloaded")
def load_preloaded_document(req: PreloadedUploadRequest):
    """Convenience endpoint to load one of the authentic pre-curated hospital demo documents."""
    demo_type = "cardiology"
    if "lab" in req.demo_doc_id:
        demo_type = "lab"
    elif "ayush" in req.demo_doc_id:
        demo_type = "ayush"

    extracted = extract_and_analyze_document(f"{req.demo_doc_id}.pdf", demo_type=demo_type)
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    extracted["document_id"] = doc_id
    extracted["patient_id"] = req.patient_id

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO documents (id, patient_id, filename, doc_type, document_date, encrypted_path, extracted_json, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        doc_id,
        req.patient_id,
        f"{req.demo_doc_id}.pdf",
        extracted["doc_type"],
        extracted["document_date"],
        "encrypted_vault",
        json.dumps(extracted),
        extracted["confidence_overall"]
    ))
    conn.commit()
    conn.close()

    return {
        "status": "loaded",
        "document_id": doc_id,
        "extracted_data": extracted
    }

@router.patch("/{id}")
def correct_document_field(id: str, req: PatchDocumentRequest):
    """Allows patient to correct low-confidence OCR fields."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT extracted_json FROM documents WHERE id = ?", (id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Document record not found.")

    data = json.loads(row["extracted_json"])
    
    # Update field (e.g. "medications.0.dose" or "diagnoses")
    if "medications" in req.field_path and isinstance(data.get("medications"), list):
        data["medications"].append({"name": str(req.corrected_value), "dose": "Custom", "frequency": "OD"})
    else:
        data[req.field_path] = req.corrected_value

    data["patient_corrected"] = True

    cursor.execute("UPDATE documents SET extracted_json = ? WHERE id = ?", (json.dumps(data), id))
    conn.commit()
    conn.close()

    return {
        "status": "updated",
        "document_id": id,
        "updated_data": data
    }

@router.get("/{patient_id}")
def get_patient_documents(patient_id: str):
    """Fetches all documents for a patient sorted chronologically as a medical timeline."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE patient_id = ? ORDER BY document_date DESC", (patient_id,))
    rows = cursor.fetchall()
    conn.close()

    timeline = []
    for r in rows:
        parsed = json.loads(r["extracted_json"]) if r["extracted_json"] else {}
        timeline.append(parsed)

    return {
        "patient_id": patient_id,
        "count": len(timeline),
        "timeline": timeline
    }

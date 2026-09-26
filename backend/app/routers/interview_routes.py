import uuid
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any, List
from ..database import get_db
from ..ml.interview_engine import interview_engine

router = APIRouter(prefix="/interview", tags=["Clinical Interview Engine"])

class StartInterviewRequest(BaseModel):
    patient_id: str
    language: Optional[str] = "en"
    mode: Optional[str] = "standard_and_ayush"

class AnswerRequest(BaseModel):
    session_id: str
    question_id: str
    answer_value: Optional[Any] = None
    voice_transcript: Optional[str] = None

@router.post("/start")
def start_interview(req: StartInterviewRequest):
    session_id = f"ses_{uuid.uuid4().hex[:8]}"
    state = interview_engine.initialize_session(
        patient_id=req.patient_id,
        language=req.language,
        mode=req.mode
    )

    first_q = interview_engine.next_question(state)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sessions (id, patient_id, language, mode, state_json)
        VALUES (?, ?, ?, ?, ?)
    """, (session_id, req.patient_id, req.language, req.mode, json.dumps(state)))
    conn.commit()
    conn.close()

    return {
        "session_id": session_id,
        "first_question": first_q,
        "language": req.language,
        "mode": req.mode
    }

@router.post("/answer")
def submit_answer(req: AnswerRequest):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT state_json, is_active, patient_id FROM sessions WHERE id = ?", (req.session_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found.")
    
    if not row["is_active"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Session has expired or was wiped.")

    state = json.loads(row["state_json"])
    result = interview_engine.process_answer(
        state=state,
        question_id=req.question_id,
        answer_value=req.answer_value,
        voice_transcript=req.voice_transcript
    )

    updated_state = result["state"]

    # If new red flag triggered, record alert in alerts table
    if result["red_flags"]:
        for flag in result["red_flags"]:
            alert_id = f"alt_{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT OR IGNORE INTO alerts (id, patient_id, session_id, title, message_en, message_hi, severity)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (alert_id, row["patient_id"], req.session_id, flag["title"], flag["message_en"], flag["message_hi"], "CRITICAL"))

    # Update session in DB
    cursor.execute("""
        UPDATE sessions SET state_json = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (json.dumps(updated_state), req.session_id))

    conn.commit()
    conn.close()

    return {
        "session_id": req.session_id,
        "next_question": result["next_question"],
        "red_flags": result["red_flags"],
        "completed": result["completed"],
        "current_step": updated_state.get("current_step", 0)
    }

@router.get("/{session_id}")
def get_session_state(session_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Session not found.")

    state = json.loads(row["state_json"]) if row["state_json"] else {}
    return {
        "session_id": row["id"],
        "patient_id": row["patient_id"],
        "language": row["language"],
        "mode": row["mode"],
        "is_active": bool(row["is_active"]),
        "state": state
    }

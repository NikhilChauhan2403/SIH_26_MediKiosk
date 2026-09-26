import json
from fastapi import APIRouter
from ..database import get_db

router = APIRouter(prefix="/doctor", tags=["Doctor Clinical Queue & Triage"])

@router.get("/queue")
def get_doctor_queue():
    """
    Returns active waiting patient queue for the doctor.
    CRITICAL REQUIREMENT: Red Flag Emergency cases are strictly pinned and sorted at the TOP.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            s.id as summary_id,
            s.patient_id,
            p.name as patient_name,
            p.age,
            p.gender,
            p.abha_id,
            s.token_number,
            s.status,
            s.red_flag_alert,
            s.doctor_decision,
            s.created_at,
            s.summary_json
        FROM summaries s
        JOIN patients p ON s.patient_id = p.id
        ORDER BY s.red_flag_alert DESC, s.created_at ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    queue = []
    for r in rows:
        summary_obj = json.loads(r["summary_json"]) if r["summary_json"] else {}
        cc = summary_obj.get("sections", {}).get("chief_complaint", "Pending")
        queue.append({
            "summary_id": r["summary_id"],
            "patient_id": r["patient_id"],
            "patient_name": r["patient_name"],
            "age": r["age"],
            "gender": r["gender"],
            "abha_id": r["abha_id"],
            "token_number": r["token_number"],
            "status": r["status"],
            "red_flag_alert": bool(r["red_flag_alert"]),
            "chief_complaint": cc,
            "created_at": r["created_at"],
            "doctor_decision": r["doctor_decision"]
        })

    return {
        "count": len(queue),
        "red_flag_count": sum(1 for q in queue if q["red_flag_alert"]),
        "queue": queue
    }

@router.get("/stats")
def get_triage_stats():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM summaries")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as rf FROM summaries WHERE red_flag_alert = 1")
    rf = cursor.fetchone()["rf"]

    cursor.execute("SELECT COUNT(*) as accepted FROM summaries WHERE status = 'accepted'")
    accepted = cursor.fetchone()["accepted"]

    cursor.execute("SELECT COUNT(*) as pending FROM summaries WHERE status = 'pending_review'")
    pending = cursor.fetchone()["pending"]

    conn.close()
    return {
        "total_screened": total,
        "critical_red_flags": rf,
        "accepted_by_physicians": accepted,
        "pending_in_queue": pending
    }

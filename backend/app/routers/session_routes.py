from fastapi import APIRouter
from ..security import wipe_session_data

router = APIRouter(prefix="/session", tags=["Session Lifecycle & Security"])

@router.delete("/{session_id}")
def delete_session(session_id: str):
    """
    Session wipe (DPDP Act 2023 requirement):
    Deletes temporary audio recordings, voice transcripts, and scratch uploads
    associated with a completed or cancelled kiosk session, and marks session inactive.
    """
    return wipe_session_data(session_id)

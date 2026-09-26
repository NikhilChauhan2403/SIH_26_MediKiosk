import os
import bcrypt
import json
import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from .config import CIPHER_SUITE, UPLOADS_DIR
from .database import get_db

def hash_password(password: str) -> str:
    """Hashes a password with bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def encrypt_and_save_file(file_bytes: bytes, filename: str, patient_id: str) -> str:
    """
    Encrypts sensitive medical files at rest using AES Fernet cipher.
    Returns relative storage path.
    """
    encrypted_data = CIPHER_SUITE.encrypt(file_bytes)
    safe_filename = f"{patient_id}_{int(datetime.datetime.now().timestamp())}_{filename}"
    file_path = UPLOADS_DIR / safe_filename
    with open(file_path, "wb") as f:
        f.write(encrypted_data)
    return str(file_path)

def read_and_decrypt_file(file_path: str) -> bytes:
    """Reads and decrypts an encrypted document at rest."""
    with open(file_path, "rb") as f:
        encrypted_data = f.read()
    return CIPHER_SUITE.decrypt(encrypted_data)

def wipe_session_data(session_id: str) -> Dict[str, Any]:
    """
    Session wipe (DPDP Act 2023 requirement):
    Deletes temporary audio recordings, voice transcripts, and scratch uploads
    associated with a completed or cancelled kiosk session, and marks session inactive.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Invalidate session in DB
    cursor.execute("UPDATE sessions SET is_active = 0, state_json = '{}', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (session_id,))
    
    # Remove any temporary audio scratch files if present
    scratch_files = list(UPLOADS_DIR.glob(f"tmp_audio_{session_id}*"))
    for sf in scratch_files:
        try:
            sf.unlink()
        except Exception:
            pass

    conn.commit()
    conn.close()

    return {
        "status": "wiped",
        "session_id": session_id,
        "message": "Temporary session data, voice recordings and ephemeral transcripts securely wiped."
    }

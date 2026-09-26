import os
from pathlib import Path
from cryptography.fernet import Fernet

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True, parents=True)

UPLOADS_DIR = DATA_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True, parents=True)

DB_PATH = DATA_DIR / "medikiosk.db"

JWT_SECRET_KEY = os.getenv("MEDIKIOSK_JWT_SECRET", "sih2026-medikiosk-secure-jwt-key-998822")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = 60 * 12 # 12 hours for clinical kiosk / shift

# Encryption key for patient documents at rest (DPDP Act 2023 requirement)
FERNET_KEY = os.getenv("MEDIKIOSK_FERNET_KEY", Fernet.generate_key().decode())
CIPHER_SUITE = Fernet(FERNET_KEY.encode() if isinstance(FERNET_KEY, str) else FERNET_KEY)

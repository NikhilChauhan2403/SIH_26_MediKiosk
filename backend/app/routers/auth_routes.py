import uuid
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from ..database import get_db
from ..security import hash_password, verify_password
from ..auth import create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

class RegisterRequest(BaseModel):
    name: str
    age: Optional[int] = 35
    gender: Optional[str] = "Female"
    phone: str
    password: str
    abha_id: Optional[str] = None
    role: Optional[str] = "patient"

class LoginRequest(BaseModel):
    phone: str
    password: str

class AbhaLoginRequest(BaseModel):
    abha_id: str
    otp: str  # Mock OTP: 123456

@router.post("/register")
def register_user(req: RegisterRequest):
    conn = get_db()
    cursor = conn.cursor()
    
    # Check existing phone
    cursor.execute("SELECT id FROM patients WHERE phone = ?", (req.phone,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="A user with this mobile number already exists.")

    user_id = f"pat_{uuid.uuid4().hex[:8]}"
    pwd_hash = hash_password(req.password)
    abha = req.abha_id or f"91-{req.phone[-4:]}-8822-1144"

    cursor.execute("""
        INSERT INTO patients (id, abha_id, name, age, gender, phone, role, password_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, abha, req.name, req.age, req.gender, req.phone, req.role, pwd_hash))

    conn.commit()
    conn.close()

    token = create_access_token({"sub": user_id, "role": req.role, "name": req.name})
    return {
        "status": "success",
        "user_id": user_id,
        "name": req.name,
        "abha_id": abha,
        "role": req.role,
        "token": token
    }

@router.post("/login")
def login_user(req: LoginRequest):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, abha_id, role, password_hash FROM patients WHERE phone = ?", (req.phone,))
    user = cursor.fetchone()
    conn.close()

    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid phone number or password.")

    token = create_access_token({"sub": user["id"], "role": user["role"], "name": user["name"]})
    return {
        "status": "success",
        "user_id": user["id"],
        "name": user["name"],
        "abha_id": user["abha_id"],
        "role": user["role"],
        "token": token
    }

@router.post("/abha-login")
def abha_login(req: AbhaLoginRequest):
    """
    Mock ABHA login as specified in SIH requirements.
    Accepts ABHA ID/number and OTP '123456'.
    """
    if req.otp != "123456":
        raise HTTPException(status_code=400, detail="Invalid ABHA OTP. Use demo OTP: 123456")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, abha_id, role, age, gender FROM patients WHERE abha_id = ?", (req.abha_id,))
    user = cursor.fetchone()

    if not user:
        # Auto-create mock patient record for ABHA
        user_id = f"pat_{uuid.uuid4().hex[:8]}"
        mock_name = "Smt. Shanti Devi"
        cursor.execute("""
            INSERT INTO patients (id, abha_id, name, age, gender, phone, role)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, req.abha_id, mock_name, 62, "Female", "+919876543210", "patient"))
        conn.commit()
        cursor.execute("SELECT id, name, abha_id, role, age, gender FROM patients WHERE id = ?", (user_id,))
        user = cursor.fetchone()

    conn.close()
    token = create_access_token({"sub": user["id"], "role": user["role"], "name": user["name"]})

    return {
        "status": "success",
        "message": "ABHA Verified via ABDM Gateway (Mocked)",
        "user_id": user["id"],
        "name": user["name"],
        "abha_id": user["abha_id"],
        "age": user["age"],
        "gender": user["gender"],
        "token": token
    }

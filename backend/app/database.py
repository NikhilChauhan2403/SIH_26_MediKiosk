import sqlite3
import json
from typing import Dict, Any, List, Optional
from .config import DB_PATH

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes tables and seeds initial hospital staff & demo patients."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS patients (
        id TEXT PRIMARY KEY,
        abha_id TEXT UNIQUE,
        name TEXT NOT NULL,
        age INTEGER,
        gender TEXT,
        phone TEXT UNIQUE,
        role TEXT DEFAULT 'patient',
        password_hash TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        patient_id TEXT,
        language TEXT DEFAULT 'en',
        mode TEXT DEFAULT 'standard_and_ayush',
        state_json TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id)
    );

    CREATE TABLE IF NOT EXISTS consents (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        storage_consent INTEGER DEFAULT 1,
        doctor_access INTEGER DEFAULT 1,
        research_consent INTEGER DEFAULT 0,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        revoked INTEGER DEFAULT 0,
        revoked_at TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id)
    );

    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        filename TEXT NOT NULL,
        doc_type TEXT,
        document_date TEXT,
        encrypted_path TEXT,
        extracted_json TEXT,
        confidence REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id)
    );

    CREATE TABLE IF NOT EXISTS summaries (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        session_id TEXT,
        token_number TEXT,
        status TEXT DEFAULT 'pending_review',
        red_flag_alert INTEGER DEFAULT 0,
        summary_json TEXT,
        doctor_notes TEXT DEFAULT '',
        doctor_decision TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reviewed_at TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id)
    );

    CREATE TABLE IF NOT EXISTS alerts (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        session_id TEXT,
        title TEXT NOT NULL,
        message_en TEXT,
        message_hi TEXT,
        severity TEXT DEFAULT 'HIGH',
        status TEXT DEFAULT 'ACTIVE',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id)
    );

    CREATE TABLE IF NOT EXISTS his_records (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        summary_id TEXT,
        fhir_bundle_json TEXT NOT NULL,
        pushed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'COMMITTED',
        FOREIGN KEY(patient_id) REFERENCES patients(id)
    );
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")

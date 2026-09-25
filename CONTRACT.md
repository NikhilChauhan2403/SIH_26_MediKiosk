# MediKiosk Contract Specification
**SIH 2026 | Problem Statement SIH26047: Patient Case-Taking Software**
**Ministry of Ayush / All India Institute of Ayurveda (AIIA)**

This document defines the shared JSON schemas, state machines, and API endpoints for the MediKiosk platform.

---

## 1. Interview Result Contract

```json
{
  "session_id": "ses_9281a",
  "patient_id": "p_001",
  "language": "hi",
  "mode": "allopathic_and_ayush",
  "chief_complaint": "chest pain",
  "hpi": {
    "site": "substernal / retrosternal",
    "onset": "2 days ago, acute",
    "character": "constricting / pressure",
    "radiation": "left arm and jaw",
    "associated": ["profuse sweating", "breathlessness on exertion"],
    "time_course": "worsening over 4 hours",
    "exacerbating": "walking or climbing stairs",
    "relieving": "rest",
    "severity": 8
  },
  "past_history": {
    "medical": ["Hypertension (5 years)", "Type 2 Diabetes Mellitus (3 years)"],
    "surgical": ["Appendectomy (2018)"]
  },
  "drugs": [
    {"name": "Amlodipine", "dose": "5mg", "frequency": "OD", "duration": "Ongoing"},
    {"name": "Metformin", "dose": "500mg", "frequency": "BD", "duration": "Ongoing"}
  ],
  "allergies": [
    {"allergen": "Penicillin", "reaction": "Skin rash & urticaria", "severity": "Moderate"}
  ],
  "family": [
    {"relation": "Father", "condition": "Coronary Artery Disease (CAD) / MI at age 52"}
  ],
  "personal": {
    "smoking": "Non-smoker",
    "alcohol": "Occasional",
    "diet": "Vegetarian",
    "sleep": "Disturbed"
  },
  "ros": {
    "cardiovascular": ["Chest tightness", "Palpitations"],
    "respiratory": ["Shortness of breath on mild exertion"],
    "gastrointestinal": ["No nausea or vomiting"],
    "neurological": ["No dizziness or syncope"]
  },
  "ayush": {
    "prakriti": "Pitta-Vata",
    "vikriti": "Vata vriddhi with Pitta anubandha",
    "agni": "Vishamagni (Irregular digestive fire)",
    "koshtha": "Madhyama (Moderate bowel movement)",
    "ahara_vihara": "Ushna-tikshna ahara, ratri jagarana (late night work)",
    "nidana": "Vega dharana, chinta, ativyayama"
  },
  "red_flags": [
    {
      "severity": "CRITICAL",
      "code": "RED_ACS_SUSPECT",
      "trigger": "Chest pain + sweating + left arm radiation",
      "timestamp": "2026-09-26T00:55:00Z",
      "action": "Immediate emergency triage desk routing; priority doctor alert"
    }
  ]
}
```

---

## 2. Document AI Extraction Contract

```json
{
  "document_id": "doc_8172b",
  "patient_id": "p_001",
  "doc_type": "prescription_and_lab",
  "document_date": "2026-08-15",
  "hospital_or_doctor": "Dr. R. K. Sharma, MD (Cardiology), AIIA OPD",
  "diagnoses": ["Essential Hypertension", "Mild Dyslipidemia"],
  "medications": [
    {
      "name": "Aspirin",
      "dose": "75mg",
      "frequency": "OD",
      "duration": "30 days",
      "confidence": 0.96
    },
    {
      "name": "Warfarin",
      "dose": "2.5mg",
      "frequency": "OD (Night)",
      "duration": "30 days",
      "confidence": 0.88,
      "requires_verification": false
    }
  ],
  "lab_tests": [
    {
      "name": "HbA1c",
      "value": 8.4,
      "unit": "%",
      "reference_range": "4.0 - 5.6 %",
      "status": "HIGH",
      "confidence": 0.98
    },
    {
      "name": "Serum Creatinine",
      "value": 1.7,
      "unit": "mg/dL",
      "reference_range": "0.7 - 1.3 mg/dL",
      "status": "HIGH",
      "confidence": 0.94
    },
    {
      "name": "Hemoglobin",
      "value": 13.8,
      "unit": "g/dL",
      "reference_range": "13.0 - 17.0 g/dL",
      "status": "NORMAL",
      "confidence": 0.99
    }
  ],
  "drug_interaction_warnings": [
    {
      "drugs": ["Warfarin", "Aspirin"],
      "severity": "HIGH",
      "description": "Concurrent use of Warfarin and Aspirin significantly increases risk of major gastrointestinal and systemic bleeding."
    }
  ],
  "confidence_overall": 0.94
}
```

---

## 3. Clinical Summary (Doctor Review Contract)

```json
{
  "summary_id": "sum_4410",
  "patient_id": "p_001",
  "patient_name": "Smt. Shanti Devi",
  "age": 62,
  "gender": "Female",
  "token_number": "TK-042",
  "created_at": "2026-09-26T00:56:00Z",
  "status": "pending_review",
  "doctor_decision": null,
  "doctor_notes": "",
  "red_flag_alert": true,
  "red_flag_details": "Chest pain with sweating and left arm radiation (Potential Acute Coronary Syndrome)",
  "sections": {
    "chief_complaint": "Retrosternal chest pressure radiating to left arm for 2 days [Patient Stated]",
    "hpi": "62-year-old female presents with acute onset severe retrosternal pressure (severity 8/10) radiating to left arm and jaw. Associated with profuse sweating and shortness of breath upon exertion. Relieved by rest. [Patient Stated]",
    "past_medical_history": "Hypertension (5 years), Type 2 Diabetes Mellitus (3 years) [From Document & Patient Stated]",
    "medications": "Amlodipine 5mg OD, Metformin 500mg BD [Patient Stated]; Aspirin 75mg OD, Warfarin 2.5mg OD [From Document - ALERT: Concurrent Bleeding Risk]",
    "allergies": "Penicillin (Moderate urticarial skin rash) [Patient Stated]",
    "family_history": "Father with premature CAD / Myocardial Infarction at 52 [Patient Stated]",
    "personal_history": "Vegetarian diet, non-smoker, sleep fragmentation [Patient Stated]",
    "review_of_systems": "Cardiorespiratory positive for chest tightness and dyspnea; GI/Neuro unremarkable [Patient Stated]",
    "prior_investigations": "HbA1c 8.4% (Elevated), Serum Creatinine 1.7 mg/dL (Elevated), Hb 13.8 g/dL (Normal) [From Document]",
    "ayush_assessment": "Prakriti: Pitta-Vata; Agni: Vishamagni; Koshtha: Madhyama; Nidana: Chinta, Vega-dharana [Patient Stated]"
  },
  "patient_vernacular_summary": "आपको 2 दिनों से सीने में भारीपन व पसीना आने की शिकायत है जो बाएं हाथ में जा रहा है। डॉक्टर को तत्काल सूचित कर दिया गया है।"
}
```

---

## 4. FHIR R4 Minimal Bundle

Generated on Doctor confirmation and exported to ABDM / HIS:
- `resourceType`: `Bundle`
- `type`: `document` / `transaction`
- Entries:
  1. `Patient`: Demographics, identifiers, contact
  2. `Condition`: Chief complaint & chronic conditions (SNOMED-CT / ICD-10)
  3. `MedicationStatement`: Active medicines extracted and reported
  4. `Observation`: Vital signs, abnormal lab findings (LOINC / Ayush parameters)
  5. `AllergyIntolerance`: Documented allergies and reactions

---

## 5. REST API Endpoints Specification

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Register new patient account |
| `POST` | `/auth/login` | Login with username/password (returns JWT) |
| `POST` | `/auth/abha-login` | Mock ABHA authentication (ID + OTP `123456`) |
| `POST` | `/consent` | Log granular DPDP Act 2023 consent with timestamp |
| `GET` | `/consent/{patient_id}` | Fetch active patient consent record |
| `DELETE` | `/consent/{patient_id}` | Revoke patient consent (Right to be forgotten) |
| `POST` | `/interview/start` | Initialize interview session, return first question |
| `POST` | `/interview/answer` | Submit answer (voice transcript or tap card) -> returns next question or done |
| `GET` | `/interview/{session_id}` | Get complete interview state |
| `POST` | `/documents/upload` | Upload document image/PDF -> OCR & structured JSON |
| `PATCH` | `/documents/{id}` | Patient manually corrects an OCR field |
| `GET` | `/documents/{patient_id}` | Get patient document timeline |
| `POST` | `/summary/generate` | Synthesize interview + documents into clinical summary |
| `GET` | `/summary/{id}` | Retrieve clinical summary for doctor review |
| `PATCH` | `/summary/{id}` | Doctor edits clinical summary |
| `POST` | `/summary/{id}/confirm` | Doctor accepts or rejects summary (`ACCEPT`/`REJECT`) |
| `GET` | `/doctor/queue` | Doctor's active patient queue (Red flags pinned at top) |
| `POST` | `/his/push` | Transform accepted case into FHIR R4 Bundle and push to mock HIS |
| `GET` | `/his/records` | Query mock HIS database for exported patient encounters |
| `GET` | `/patient/timeline` | View chronological medical timeline for patient portal |
| `DELETE` | `/session/{id}` | Wipe temporary audio, transcripts, and cached files |

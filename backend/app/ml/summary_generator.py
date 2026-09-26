"""
Clinical Summary Generator for MediKiosk
Drafts standard structured medical summaries from patient interview state and document AI data.
Strict Rule: The AI only drafts; it NEVER diagnoses. Every clinical finding is explicitly tagged
as '[Patient Stated]' or '[From Document]'.
"""

from typing import Dict, Any, List

def generate_clinical_summary(interview_state: Dict[str, Any], documents: List[Dict[str, Any]] = None, patient_info: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Synthesizes the interview responses and document records into a structured draft for the doctor.
    """
    documents = documents or []
    patient_info = patient_info or {}
    
    # 1. Chief Complaint
    cc_raw = interview_state.get("chief_complaint") or "Not reported"
    cc_map = {
        "chest_pain": "Chest pain / discomfort",
        "fever": "Fever with chills",
        "headache": "Severe acute headache",
        "ayush_consult": "Ayush / Holistic Wellness Evaluation"
    }
    cc_text = f"{cc_map.get(cc_raw, cc_raw)} [Patient Stated]"

    # 2. History of Present Illness (HPI - SOCRATES)
    hpi = interview_state.get("hpi", {})
    hpi_parts = []
    if hpi.get("site"):
        hpi_parts.append(f"Site: {hpi['site']}")
    if hpi.get("onset"):
        hpi_parts.append(f"Onset: {hpi['onset']}")
    if hpi.get("character"):
        hpi_parts.append(f"Character: {hpi['character']}")
    if hpi.get("radiation"):
        hpi_parts.append(f"Radiation: {', '.join(hpi['radiation'])}")
    if hpi.get("associated"):
        hpi_parts.append(f"Associated symptoms: {', '.join(hpi['associated'])}")
    if hpi.get("exacerbating_relieving"):
        hpi_parts.append(f"Exacerbating/Relieving factors: {hpi['exacerbating_relieving']}")
    if hpi.get("severity"):
        hpi_parts.append(f"Reported severity: {hpi['severity']}/10")
    if hpi.get("duration"):
        hpi_parts.append(f"Duration: {hpi['duration']}")
    if hpi.get("pattern"):
        hpi_parts.append(f"Pattern: {hpi['pattern']}")
    if hpi.get("onset_type"):
        hpi_parts.append(f"Onset profile: {hpi['onset_type']}")

    hpi_text = "; ".join(hpi_parts) + " [Patient Stated]" if hpi_parts else "No detailed HPI reported."

    # 3. Past Medical / Surgical History
    past_medical = interview_state.get("past_history", {}).get("medical", [])
    past_med_text = ", ".join(past_medical) + " [Patient Stated]" if past_medical else "None reported [Patient Stated]"

    # Merge diagnoses from uploaded documents
    doc_diagnoses = []
    for doc in documents:
        for diag in doc.get("diagnoses", []):
            doc_diagnoses.append(f"{diag} ({doc.get('hospital_or_doctor', 'Prior Record')})")
    if doc_diagnoses:
        past_med_text += f"; Prior documented diagnoses: {', '.join(doc_diagnoses)} [From Document]"

    # 4. Current Drugs and Medication Statement
    patient_drugs = interview_state.get("drugs", [])
    drug_items = []
    if patient_drugs:
        drug_items.append(f"Reported regular drugs: {', '.join(patient_drugs)} [Patient Stated]")
    
    # Drugs from documents
    doc_drugs = []
    for doc in documents:
        for med in doc.get("medications", []):
            doc_drugs.append(f"{med.get('name')} {med.get('dose', '')} ({med.get('frequency', '')})")
    if doc_drugs:
        drug_items.append(f"Prescribed medications: {', '.join(doc_drugs)} [From Document]")
    
    medications_text = " | ".join(drug_items) if drug_items else "No current medications documented."

    # Drug Interaction Warnings
    all_interactions = []
    for doc in documents:
        all_interactions.extend(doc.get("drug_interaction_warnings", []))

    # 5. Allergies
    patient_allergies = interview_state.get("allergies", [])
    allergies_text = ", ".join(patient_allergies) + " [Patient Stated]" if patient_allergies else "No known drug allergies reported [Patient Stated]"

    # 6. Prior Investigations & Abnormal Lab Findings
    lab_entries = []
    for doc in documents:
        for lab in doc.get("lab_tests", []):
            flag_marker = f" [{lab['status']}]" if lab.get("is_abnormal") else ""
            lab_entries.append(f"{lab['name']}: {lab['value']} {lab.get('unit', '')}{flag_marker} (Ref: {lab.get('reference_range', 'N/A')}) [From Document: {doc.get('document_date', '')}]")
    investigations_text = " | ".join(lab_entries) if lab_entries else "No prior laboratory investigations on file."

    # 7. AYUSH Clinical Assessment
    ayush = interview_state.get("ayush", {})
    ayush_parts = []
    if ayush.get("prakriti"):
        ayush_parts.append(f"Prakriti: {ayush['prakriti'].capitalize()}")
    if ayush.get("agni"):
        ayush_parts.append(f"Agni (Digestive Fire): {ayush['agni'].capitalize()}")
    if ayush.get("koshtha"):
        ayush_parts.append(f"Koshtha (Bowel Habit): {ayush['koshtha'].capitalize()}")
    if ayush.get("ahara_vihara"):
        ayush_parts.append(f"Ahara-Vihara Factors: {', '.join(ayush['ahara_vihara'])}")
    ayush_text = "; ".join(ayush_parts) + " [Patient Stated]" if ayush_parts else "Not evaluated."

    # 8. Red Flag Triage Assessment
    red_flags = interview_state.get("red_flags", [])
    has_red_flags = len(red_flags) > 0
    red_flag_text = " | ".join([f"{f['title']}: {f['message_en']}" for f in red_flags]) if has_red_flags else "None identified during screening."

    # 9. Vernacular patient confirmation text (Hindi / English)
    lang = interview_state.get("language", "hi")
    if lang == "hi":
        patient_vernacular = (
            f"मरीज का मुख्य कारण: {cc_map.get(cc_raw, cc_raw)}। "
            f"लक्षण: {', '.join(hpi.get('associated', [])) if hpi.get('associated') else 'सामान्य'}। "
            f"कृपया डॉक्टर के कमरे में प्रवेश करने से पहले इस जानकारी की पुष्टि करें।"
        )
    else:
        patient_vernacular = (
            f"Chief Complaint: {cc_map.get(cc_raw, cc_raw)}. "
            f"Reported symptoms: {', '.join(hpi.get('associated', [])) if hpi.get('associated') else 'None'}. "
            f"Please verify this preliminary summary before meeting the physician."
        )

    return {
        "status": "pending_review",
        "red_flag_alert": has_red_flags,
        "red_flags": red_flags,
        "drug_interaction_warnings": all_interactions,
        "sections": {
            "chief_complaint": cc_text,
            "hpi": hpi_text,
            "past_medical_surgical": past_med_text,
            "medications": medications_text,
            "allergies": allergies_text,
            "prior_investigations": investigations_text,
            "ayush_assessment": ayush_text,
            "red_flags_summary": red_flag_text
        },
        "patient_vernacular_summary": patient_vernacular,
        "clinical_disclaimer": "AI Case-Taking Assistant Draft only. Not a medical diagnosis. Requires physician validation."
    }

"""
Red Flag Alert Detection System for MediKiosk
Evaluates clinical interview answers and triage markers for life-threatening emergencies.
"""

from typing import List, Dict, Any

RED_FLAG_RULES = [
    {
        "code": "EMERGENCY_ACS_CARDIAC",
        "title": "Suspected Acute Coronary Syndrome (ACS) / Myocardial Infarction",
        "criteria": lambda state: (
            state.get("chief_complaint") == "chest_pain" and (
                any(sym in state.get("hpi", {}).get("associated", []) for sym in ["cold_sweating", "breathlessness", "dizziness_syncope"])
                or any(rad in state.get("hpi", {}).get("radiation", []) for rad in ["left_arm", "jaw_neck"])
                or state.get("hpi", {}).get("character") == "heavy_pressure"
            )
        ),
        "message_en": "CRITICAL EMERGENCY: Signs of heart distress (Chest pain with cold sweating/breathlessness). Route to Triage & Emergency Desk IMMEDIATELY.",
        "message_hi": "अति आवश्यक आपातकाल: हृदय संबंधी गंभीर लक्षण (सीने में दर्द व पसीना/सांस फूलना)। कृपया तुरंत आपातकालीन डेस्क (Emergency Desk) पर संपर्क करें।",
        "action": "Immediate ECG, Oxygen saturation check, and Doctor Emergency Alert."
    },
    {
        "code": "EMERGENCY_STROKE_FAST",
        "title": "Suspected Stroke / Acute Neurological Deficit",
        "criteria": lambda state: (
            any(sym in state.get("hpi", {}).get("associated", []) for sym in ["face_arm_weakness", "slurred_speech"])
        ),
        "message_en": "CRITICAL EMERGENCY: Signs of acute stroke (FAST protocol: Facial droop, limb weakness, slurred speech). Every minute counts.",
        "message_hi": "अति आवश्यक आपातकाल: स्ट्रोक/लकवे के लक्षण (चेहरे का झुकना, बोलने में लड़खड़ाहट, कमजोरी)। तुरंत आपातकालीन चिकित्सा आवश्यक है।",
        "action": "Immediate Code Stroke activation and CT brain triage."
    },
    {
        "code": "EMERGENCY_MENINGEAL_THUNDERCLAP",
        "title": "Thunderclap Headache / Meningism",
        "criteria": lambda state: (
            state.get("hpi", {}).get("onset_type") == "thunderclap_peak"
            or "neck_stiffness" in state.get("hpi", {}).get("associated", [])
        ),
        "message_en": "HIGH PRIORITY ALERT: Thunderclap headache or neck stiffness suspected. Risk of subarachnoid hemorrhage or meningitis.",
        "message_hi": "उच्च प्राथमिकता चेतावनी: अचानक असहनीय सिरदर्द या गर्दन में अकड़न। तत्काल विशेषज्ञ जांच आवश्यक है।",
        "action": "Urgent neurological evaluation and vitals monitoring."
    },
    {
        "code": "EMERGENCY_SEPSIS_RESPIRATORY",
        "title": "Severe Infection / Sepsis Risk with Respiratory Distress",
        "criteria": lambda state: (
            state.get("chief_complaint") == "fever" and (
                "confusion_drowsy" in state.get("hpi", {}).get("associated", [])
                or "rash_petechiae" in state.get("hpi", {}).get("associated", [])
                or "severe_breathlessness" in state.get("hpi", {}).get("associated", [])
            )
        ),
        "message_en": "HIGH PRIORITY ALERT: High fever with altered consciousness, petechial rash or respiratory distress.",
        "message_hi": "उच्च प्राथमिकता चेतावनी: तेज बुखार के साथ भ्रम, चकत्ते या सांस में रुकावट। तुरंत ट्राइएज में दिखाएं।",
        "action": "Immediate blood work, vitals check, and physician consult."
    }
]

def evaluate_red_flags(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Evaluates the patient interview state against all medical emergency rules."""
    active_flags = []
    for rule in RED_FLAG_RULES:
        try:
            if rule["criteria"](state):
                active_flags.append({
                    "code": rule["code"],
                    "title": rule["title"],
                    "message_en": rule["message_en"],
                    "message_hi": rule["message_hi"],
                    "action": rule["action"]
                })
        except Exception:
            continue
    return active_flags

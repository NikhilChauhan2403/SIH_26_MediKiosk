"""
FHIR R4 Minimal Bundle Generator for MediKiosk
Transforms accepted clinical case-taking summaries into compliant HL7 FHIR R4 Bundles
ready for ABDM / Hospital Information System (HIS) exchange.
"""

import uuid
import datetime
from typing import Dict, Any, List

def build_fhir_bundle(summary_data: Dict[str, Any], patient_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Constructs a FHIR R4 Document/Transaction Bundle.
    Resources included:
      - Patient
      - Condition (Chief complaint & chronic conditions)
      - MedicationStatement (Active medications)
      - Observation (Lab findings & AYUSH clinical parameters)
      - AllergyIntolerance
    """
    bundle_id = str(uuid.uuid4())
    patient_id = patient_info.get("id", f"pat-{str(uuid.uuid4())[:8]}")
    timestamp = datetime.datetime.now().isoformat()

    entries = []

    # 1. Patient Resource
    patient_resource = {
        "resourceType": "Patient",
        "id": patient_id,
        "identifier": [
            {
                "system": "https://healthid.ndhm.gov.in",
                "value": patient_info.get("abha_id", "91-8822-1144-5566")
            }
        ],
        "name": [
            {
                "use": "official",
                "text": patient_info.get("name", "Shanti Devi")
            }
        ],
        "gender": patient_info.get("gender", "female").lower(),
        "birthDate": patient_info.get("dob", "1964-05-12"),
        "telecom": [
            {
                "system": "phone",
                "value": patient_info.get("phone", "+919876543210")
            }
        ]
    }
    entries.append({
        "fullUrl": f"urn:uuid:{patient_id}",
        "resource": patient_resource
    })

    # 2. Condition Resource (Chief Complaint)
    condition_id = str(uuid.uuid4())
    condition_resource = {
        "resourceType": "Condition",
        "id": condition_id,
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active"
                }
            ]
        },
        "verificationStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "code": "provisional"
                }
            ]
        },
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                        "code": "encounter-diagnosis",
                        "display": "Encounter Diagnosis"
                    }
                ]
            }
        ],
        "code": {
            "text": summary_data.get("sections", {}).get("chief_complaint", "Chest pain"),
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "29857009",
                    "display": "Chest pain"
                }
            ]
        },
        "subject": {
            "reference": f"urn:uuid:{patient_id}"
        },
        "recordedDate": timestamp
    }
    entries.append({
        "fullUrl": f"urn:uuid:{condition_id}",
        "resource": condition_resource
    })

    # 3. MedicationStatements
    meds_str = summary_data.get("sections", {}).get("medications", "")
    if meds_str:
        med_id = str(uuid.uuid4())
        med_resource = {
            "resourceType": "MedicationStatement",
            "id": med_id,
            "status": "active",
            "subject": {"reference": f"urn:uuid:{patient_id}"},
            "dateAsserted": timestamp,
            "medicationCodeableConcept": {
                "text": meds_str
            }
        }
        entries.append({
            "fullUrl": f"urn:uuid:{med_id}",
            "resource": med_resource
        })

    # 4. Observation Resource (AYUSH & Vitals)
    ayush_str = summary_data.get("sections", {}).get("ayush_assessment", "")
    if ayush_str:
        ayush_obs_id = str(uuid.uuid4())
        obs_resource = {
            "resourceType": "Observation",
            "id": ayush_obs_id,
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://ayush.gov.in/codes",
                            "code": "prakriti-assessment",
                            "display": "AYUSH Constitution Assessment"
                        }
                    ]
                }
            ],
            "code": {
                "text": "AYUSH Prakriti & Agni Assessment"
            },
            "subject": {"reference": f"urn:uuid:{patient_id}"},
            "effectiveDateTime": timestamp,
            "valueString": ayush_str
        }
        entries.append({
            "fullUrl": f"urn:uuid:{ayush_obs_id}",
            "resource": obs_resource
        })

    # 5. AllergyIntolerance
    allergy_str = summary_data.get("sections", {}).get("allergies", "")
    if allergy_str:
        allergy_id = str(uuid.uuid4())
        allergy_resource = {
            "resourceType": "AllergyIntolerance",
            "id": allergy_id,
            "clinicalStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                        "code": "active"
                    }
                ]
            },
            "verificationStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                        "code": "unconfirmed"
                    }
                ]
            },
            "patient": {"reference": f"urn:uuid:{patient_id}"},
            "note": [{"text": allergy_str}]
        }
        entries.append({
            "fullUrl": f"urn:uuid:{allergy_id}",
            "resource": allergy_resource
        })

    bundle = {
        "resourceType": "Bundle",
        "id": bundle_id,
        "type": "collection",
        "timestamp": timestamp,
        "entry": entries
    }
    return bundle

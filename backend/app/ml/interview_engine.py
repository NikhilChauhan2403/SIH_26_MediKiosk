"""
Interview Engine for MediKiosk
Manages adaptive case-taking questions, multi-lingual keyword recognition for voice answers,
SOCRATES clinical flow, AYUSH mode, and red-flag evaluations.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from .red_flags import evaluate_red_flags

DATA_PATH = Path(__file__).parent / "complaints.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    KNOWLEDGE_BASE = json.load(f)

# Natural language intent dictionary for speech recognition (English + Hindi/Hinglish)
VOICE_INTENT_MAP = {
    # Chief Complaints
    "chest pain": {"field": "chief_complaint", "value": "chest_pain"},
    "seene mein dard": {"field": "chief_complaint", "value": "chest_pain"},
    "seena me dard": {"field": "chief_complaint", "value": "chest_pain"},
    "sine me dard": {"field": "chief_complaint", "value": "chest_pain"},
    "chhati me dard": {"field": "chief_complaint", "value": "chest_pain"},
    "heart problem": {"field": "chief_complaint", "value": "chest_pain"},
    "fever": {"field": "chief_complaint", "value": "fever"},
    "bukhar": {"field": "chief_complaint", "value": "fever"},
    "bukhar hai": {"field": "chief_complaint", "value": "fever"},
    "thand lag rahi hai": {"field": "chief_complaint", "value": "fever"},
    "headache": {"field": "chief_complaint", "value": "headache"},
    "sir dard": {"field": "chief_complaint", "value": "headache"},
    "sar me dard": {"field": "chief_complaint", "value": "headache"},
    "ayurveda": {"field": "chief_complaint", "value": "ayush_consult"},
    "ayush": {"field": "chief_complaint", "value": "ayush_consult"},

    # Chest Pain SOCRATES triggers
    "center": {"field": "hpi.site", "value": "center_substernal"},
    "beech me": {"field": "hpi.site", "value": "center_substernal"},
    "left": {"field": "hpi.site", "value": "left_side"},
    "baye taraf": {"field": "hpi.site", "value": "left_side"},
    "heavy": {"field": "hpi.character", "value": "heavy_pressure"},
    "bharipan": {"field": "hpi.character", "value": "heavy_pressure"},
    "dabav": {"field": "hpi.character", "value": "heavy_pressure"},
    "stabbing": {"field": "hpi.character", "value": "sharp_stabbing"},
    "chubhan": {"field": "hpi.character", "value": "sharp_stabbing"},
    "jalan": {"field": "hpi.character", "value": "burning"},
    "burning": {"field": "hpi.character", "value": "burning"},

    # Radiation
    "left arm": {"field": "hpi.radiation", "value": "left_arm", "is_list": True},
    "baya hath": {"field": "hpi.radiation", "value": "left_arm", "is_list": True},
    "baye hath": {"field": "hpi.radiation", "value": "left_arm", "is_list": True},
    "jaw": {"field": "hpi.radiation", "value": "jaw_neck", "is_list": True},
    "gardan": {"field": "hpi.radiation", "value": "jaw_neck", "is_list": True},
    "gala": {"field": "hpi.radiation", "value": "jaw_neck", "is_list": True},

    # Associated symptoms (High Red-Flag indicators)
    "sweating": {"field": "hpi.associated", "value": "cold_sweating", "is_list": True},
    "pasina": {"field": "hpi.associated", "value": "cold_sweating", "is_list": True},
    "paseena": {"field": "hpi.associated", "value": "cold_sweating", "is_list": True},
    "breathless": {"field": "hpi.associated", "value": "breathlessness", "is_list": True},
    "saans phulna": {"field": "hpi.associated", "value": "breathlessness", "is_list": True},
    "sans phul rahi": {"field": "hpi.associated", "value": "breathlessness", "is_list": True},
    "sans lene me dikkat": {"field": "hpi.associated", "value": "breathlessness", "is_list": True},
    "chakkar": {"field": "hpi.associated", "value": "dizziness_syncope", "is_list": True},
    "dizziness": {"field": "hpi.associated", "value": "dizziness_syncope", "is_list": True}
}

class InterviewEngine:
    def __init__(self):
        self.kb = KNOWLEDGE_BASE

    def initialize_session(self, patient_id: str, language: str = "en", mode: str = "standard_and_ayush") -> Dict[str, Any]:
        """Creates a fresh interview state container."""
        state = {
            "patient_id": patient_id,
            "language": language,
            "mode": mode,
            "chief_complaint": None,
            "hpi": {
                "site": None,
                "onset": None,
                "character": None,
                "radiation": [],
                "associated": [],
                "exacerbating_relieving": None,
                "severity": None,
                "duration": None,
                "pattern": None,
                "onset_type": None
            },
            "past_history": {
                "medical": []
            },
            "drugs": [],
            "allergies": [],
            "ayush": {
                "prakriti": None,
                "agni": None,
                "koshtha": None,
                "ahara_vihara": []
            },
            "answered_questions": [],
            "current_step": 0,
            "red_flags": [],
            "completed": False
        }
        return state

    def get_question_sequence(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Returns the ordered list of questions applicable for this patient state."""
        questions = []
        # Step 1: Always Chief Complaint first
        questions.extend(self.kb["complaints"])

        cc = state.get("chief_complaint")
        if cc == "chest_pain":
            questions.extend(self.kb["chest_pain"])
        elif cc == "fever":
            questions.extend(self.kb["fever"])
        elif cc == "headache":
            questions.extend(self.kb["headache"])

        # Next: Common medical history
        if cc:
            questions.extend(self.kb["common_history"])

            # If AYUSH mode enabled, append AYUSH assessment questions
            if state.get("mode") in ["ayush_only", "standard_and_ayush"]:
                questions.extend(self.kb["ayush_mode"])

        return questions

    def next_question(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Determines the next unanswered question based on flow logic."""
        all_questions = self.get_question_sequence(state)
        answered = set(state.get("answered_questions", []))

        for q in all_questions:
            if q["id"] not in answered:
                return q
        return None

    def process_answer(self, state: Dict[str, Any], question_id: str, answer_value: Any, voice_transcript: Optional[str] = None) -> Dict[str, Any]:
        """
        Applies either explicit option selection or parses voice transcript,
        updates state, evaluates red-flags, and selects the next question.
        """
        # 1. Voice transcription keyword extraction if voice transcript is provided
        if voice_transcript and not answer_value:
            norm_speech = voice_transcript.lower()
            matched = False
            for phrase, mapping in VOICE_INTENT_MAP.items():
                if phrase in norm_speech:
                    target_field = mapping["field"]
                    val = mapping["value"]
                    if mapping.get("is_list"):
                        self._append_to_nested_list(state, target_field, val)
                    else:
                        self._set_nested_field(state, target_field, val)
                    matched = True
            if not matched:
                # Store raw transcript as free text answer if no keyword matched
                answer_value = voice_transcript

        # 2. Direct answer assignment
        if answer_value is not None:
            # Find the question definition
            all_q = self.get_question_sequence(state)
            q_def = next((q for q in all_q if q["id"] == question_id), None)
            if q_def:
                target_field = q_def.get("field")
                if target_field:
                    if isinstance(answer_value, list):
                        self._set_nested_field(state, target_field, answer_value)
                    else:
                        self._set_nested_field(state, target_field, answer_value)

        # Mark question as answered
        if question_id not in state["answered_questions"]:
            state["answered_questions"].append(question_id)

        # Evaluate Red Flags
        flags = evaluate_red_flags(state)
        state["red_flags"] = flags

        # Check for next question
        nxt = self.next_question(state)
        if not nxt:
            state["completed"] = True

        state["current_step"] = len(state["answered_questions"])
        return {
            "state": state,
            "next_question": nxt,
            "red_flags": flags,
            "completed": state["completed"]
        }

    def _set_nested_field(self, obj: dict, path: str, value: Any):
        keys = path.split(".")
        for k in keys[:-1]:
            obj = obj.setdefault(k, {})
        obj[keys[-1]] = value

    def _append_to_nested_list(self, obj: dict, path: str, value: Any):
        keys = path.split(".")
        for k in keys[:-1]:
            obj = obj.setdefault(k, {})
        target = obj.setdefault(keys[-1], [])
        if value not in target:
            target.append(value)

interview_engine = InterviewEngine()

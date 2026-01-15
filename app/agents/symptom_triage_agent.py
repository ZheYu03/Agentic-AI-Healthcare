import json
import re
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.planner import _build_llm
from app.core.config import get_settings
from app.tools.supabase_tool import get_supabase_client
from app.tools.encounter_memory import upsert_encounter_memory
# Import ALLOWED_SPECIALTIES to ensure consistency
from app.agents.clinic_recommendation_agent import ALLOWED_SPECIALTIES

SYSTEM_PROMPT = (
    "You are a clinical triage assistant. "
    "You assess urgency and recommend next steps. "
    "You do not diagnose or treat. "
    "You generate structured, explainable outputs. "
    "If uncertain, choose the safer option."
)

# Build schema hint dynamically with ALLOWED_SPECIALTIES
def _get_output_schema_hint() -> str:
    """Generate output schema with current ALLOWED_SPECIALTIES list."""
    specialty_list = ", ".join(ALLOWED_SPECIALTIES)
    return f"""
Return JSON only in this shape:
{{
  "triage": {{
    "triage_level": "emergency|urgent|semi-urgent|non-urgent|information",
    "urgency_score": <integer 1-10>,
    "recommended_action": "<short next step>",
    "reasoning": ["<bullet1>", "<bullet2>"],
    "recommended_specialty": "<specialty name or null>"
  }},
  "follow_up_requests": [
    {{
      "intent": "<semantic_key>",
      "question": "<human-readable question>",
      "confidence_blocking": true | false
    }}
  ],
  "ehr_record": {{
    "chief_complaint": "",
    "symptoms": [],
    "associated_symptoms": [],
    "risk_factors": [],
    "red_flags_detected": [],
    "clinical_considerations": [
      {{"label": "", "reason": "", "urgency_relevance": "high|medium|low"}}
    ],
    "disclaimer": "For clinician review only. Not a diagnosis."
  }}
}}

For recommended_specialty, choose EXACTLY from this list: {specialty_list}, or use null if unclear.
CRITICAL: Use the EXACT spelling from the list above (e.g., "Cardiologist" not "Cardiology").
"""


def _build_user_context(state: Dict[str, Any]) -> str:
    """Assemble user context for the LLM without adding new logic."""
    clinical = state.get("clinical", {}) or {}
    lines = []
    
    # CRITICAL: Show original chief complaint first so LLM has full context
    original_complaint = clinical.get("original_chief_complaint")
    if original_complaint:
        lines.append(f"Original chief complaint: {original_complaint}")
    
    # Current user input (may be a follow-up answer)
    current_input = state.get('user_input', '')
    if current_input:
        lines.append(f"Current user input: {current_input}")
    
    if clinical.get("age"):
        lines.append(f"Age: {clinical.get('age')}")
    if clinical.get("sex"):
        lines.append(f"Sex: {clinical.get('sex')}")
    if clinical.get("blood_type"):
        lines.append(f"Blood type: {clinical.get('blood_type')}")
    if clinical.get("pregnancy_status"):
        lines.append(f"Pregnancy: {clinical.get('pregnancy_status')}")
    if clinical.get("chronic_conditions"):
        lines.append(f"Chronic conditions: {clinical.get('chronic_conditions')}")
    if clinical.get("medications"):
        lines.append(f"Medications: {clinical.get('medications')}")
    if clinical.get("allergies"):
        lines.append(f"Allergies: {clinical.get('allergies')}")
    if clinical.get("duration"):
        lines.append(f"Duration: {clinical.get('duration')}")
    if clinical.get("severity"):
        lines.append(f"Severity: {clinical.get('severity')}")
    # Inject resolved follow-up answers so we don't re-ask and LLM has needed facts.
    if "symptoms_ongoing" in clinical:
        lines.append(f"Symptoms ongoing: {'yes' if clinical.get('symptoms_ongoing') else 'no'}")
    if "radiating_pain" in clinical:
        lines.append(f"Radiating pain: {'yes' if clinical.get('radiating_pain') else 'no'}")
    if clinical.get("symptom_trend"):
        lines.append(f"Symptom trend: {clinical.get('symptom_trend')}")
    if "diabetes" in clinical:
        lines.append(f"Diabetes: {'yes' if clinical.get('diabetes') else 'no'}")
    if "prior_heart_disease" in clinical:
        lines.append(f"Prior heart disease: {'yes' if clinical.get('prior_heart_disease') else 'no'}")
    if clinical.get("triage_context_summary"):
        lines.append(f"Encounter summary: {clinical['triage_context_summary']}")
    # Include resolved follow-up intents for continuity.
    resolved = clinical.get("resolved_intents") or {}
    if resolved:
        lines.append("Resolved follow-up intents:")
        for intent, payload in resolved.items():
            lines.append(f"- {intent}: {payload.get('value')}")
    return "\n".join(lines)


def ingest_followup_answer(intent: str, user_text: str, clinical: Dict[str, Any]) -> Dict[str, Any]:
    """
    Store the user's answer for a specific intent in short-term clinical state.
    No interpretation; do not overwrite existing resolved intents.
    """
    updated = dict(clinical or {})
    resolved = dict(updated.get("resolved_intents") or {})
    # Normalize key to lower case to prevent duplicates from casing differences
    key = intent.strip().lower()
    if key not in resolved:
        resolved[key] = {"value": user_text, "source": "user"}
        updated["resolved_intents"] = resolved
    return updated


def _filter_answered_followups_intent(followups: List[Dict[str, Any]], clinical: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Drop follow-up requests whose intent is already resolved.
    """
    resolved = set((clinical.get("resolved_intents") or {}).keys())
    return [
        fq for fq in followups 
        if fq.get("intent") and fq["intent"].strip().lower() not in resolved
    ]


def _update_triage_context_summary(clinical: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministically summarize key facts so the LLM sees encounter continuity without raw chat logs.
    """
    parts: List[str] = []
    if clinical.get("duration"):
        parts.append(f"Duration: {clinical['duration']}")
    if "symptoms_ongoing" in clinical:
        parts.append(f"Symptoms ongoing: {'yes' if clinical.get('symptoms_ongoing') else 'no'}")
    if "radiating_pain" in clinical:
        parts.append(f"Radiating pain: {'yes' if clinical.get('radiating_pain') else 'no'}")
    if clinical.get("symptom_trend"):
        parts.append(f"Symptom trend: {clinical.get('symptom_trend')}")
    if "diabetes" in clinical:
        parts.append(f"Diabetes: {'yes' if clinical.get('diabetes') else 'no'}")
    if "prior_heart_disease" in clinical:
        parts.append(f"Prior heart disease: {'yes' if clinical.get('prior_heart_disease') else 'no'}")
    if clinical.get("associated_symptoms"):
        parts.append(f"Associated symptoms: {', '.join(map(str, clinical.get('associated_symptoms')))}")
    clinical["triage_context_summary"] = "; ".join(parts)
    return clinical


def _safe_parse(content: Any) -> Dict[str, Any]:
    """
    Parse JSON defensively; tolerate extra text by extracting the first JSON object.
    Falls back to a minimal skeleton on failure.
    """
    # Handle already-structured returns
    if isinstance(content, dict):
        embedded = content.get("text") if "text" in content else None
        if embedded and "triage" not in content:
            fence = re.search(r"```(?:json)?(.*?)```", embedded, re.DOTALL | re.IGNORECASE)
            if fence:
                embedded = fence.group(1)
            m = re.search(r"\{.*\}", embedded, re.DOTALL)
            if m:
                clean = m.group(0).replace("“", "\"").replace("”", "\"").replace("’", "'")
                try:
                    parsed = json.loads(clean)
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    pass
            # If parsing failed, treat the embedded text as the new raw content
            content = embedded
        else:
            return content
    if isinstance(content, list) and content and isinstance(content[0], dict):
        content = content[0]

    raw = content
    if isinstance(content, str):
        # Try to extract the first JSON object to avoid LLM prefix/suffix noise.
        fence = re.search(r"```(?:json)?(.*?)```", content, re.DOTALL | re.IGNORECASE)
        if fence:
            content = fence.group(1)
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            raw = m.group(0).replace("“", "\"").replace("”", "\"").replace("’", "'")
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(parsed, dict):
            return parsed
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to parse triage JSON. Error: {e}")
        logger.error(f"Raw content type: {type(content)}")
        logger.error(f"Raw content (first 500 chars): {str(content)[:500]}")
        pass
    # Fallback minimal skeleton
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("Using fallback triage skeleton due to parsing failure")
    return {
        "triage": {
            "triage_level": "information",
            "urgency_score": 3,
            "recommended_action": "Follow up with a clinician for more details.",
            "reasoning": ["Unable to parse structured triage output."],
        },
        "follow_up_questions": [],
        "ehr_record": {
            "chief_complaint": "",
            "symptoms": [],
            "associated_symptoms": [],
            "risk_factors": [],
            "red_flags_detected": [],
            "clinical_considerations": [],
            "disclaimer": "For clinician review only. Not a diagnosis.",
        },
    }


def symptom_triage_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Symptom Triage Agent:
    - Uses LLM with structured prompt to assess urgency.
    - Produces clinician-facing considerations; no diagnoses or treatments.
    - Persists triage result to Supabase "Symptom EHR" when patient_id is provided.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    settings = get_settings()
    llm = _build_llm(settings)
    
    # Hydrate LTM context and fetch patient profile
    from app.tools.memory import hydrate_state_from_long_term_memory
    from app.tools.patient_data import fetch_patient_profile
    
    patient_id = state.get("patient_id")
    
    # Hydrate LTM context
    if patient_id:
        state = hydrate_state_from_long_term_memory(state, patient_id)
    
    # Fetch patient demographics from database
    if patient_id:
        try:
            patient_profile = fetch_patient_profile(patient_id)
            if patient_profile:
                clinical = state.get("clinical", {}) or {}
                
                # Set age from profile if not already provided
                if patient_profile.get("age") is not None and not clinical.get("age"):
                    clinical["age"] = patient_profile["age"]
                    logger.info(f"Set age={patient_profile['age']} from patient profile")
                
                # Set sex from profile if not already provided
                if patient_profile.get("gender") and not clinical.get("sex"):
                    clinical["sex"] = patient_profile["gender"]
                    logger.info(f"Set sex={patient_profile['gender']} from patient profile")
                
                # Store name for personalized interaction
                if patient_profile.get("full_name"):
                    clinical["patient_full_name"] = patient_profile["full_name"]
                    # Extract first name for greetings
                    full_name = patient_profile["full_name"]
                    clinical["patient_first_name"] = full_name.split()[0] if full_name else None
                
                # Add blood type if available
                if patient_profile.get("blood_type"):
                    clinical["blood_type"] = patient_profile["blood_type"]
                
                # Add allergy information
                nkda = patient_profile.get("nkda", False)
                if nkda:
                    clinical["allergies"] = "NKDA (No Known Drug Allergies)"
                else:
                    # Compile all allergies into a single field
                    allergies = []
                    if patient_profile.get("drug_allergies"):
                        allergies.append(f"Drug: {patient_profile['drug_allergies']}")
                    if patient_profile.get("medical_allergies"):
                        allergies.append(f"Medical: {patient_profile['medical_allergies']}")
                    if patient_profile.get("food_env_allergies"):
                        allergies.append(f"Food/Environmental: {patient_profile['food_env_allergies']}")
                    
                    if allergies:
                        clinical["allergies"] = "; ".join(allergies)
                
                state["clinical"] = clinical
        except Exception as e:
            logger.warning(f"Failed to fetch patient profile: {e}")

    # Ingest follow-up answers into short-term clinical state to avoid re-asking.
    clinical = state.get("clinical", {}) or {}
    if clinical.get("pending_follow_up") and state.get("user_input"):
        # Ingest answers for all pending intents; verbatim, no interpretation.
        pending_requests = clinical.get("follow_up_requests") or []
        resolved_any = False
        for req in pending_requests:
            intent_key = req.get("intent")
            if intent_key:
                clinical = ingest_followup_answer(intent_key, state.get("user_input", ""), clinical)
                resolved_any = True
        clinical["pending_follow_up"] = False
        clinical["follow_up_requests"] = []
        clinical["answered_followups"] = resolved_any or clinical.get("answered_followups")
        state["clinical"] = clinical
    # Maintain a concise encounter summary for continuity.
    clinical = _update_triage_context_summary(state.get("clinical", {}) or {})
    
    # CRITICAL: Store original chief complaint on first run so it's preserved in all follow-ups
    # BUT: Don't overwrite if we just processed a follow-up answer
    is_followup_answer = clinical.get("answered_followups", False)
    if not clinical.get("original_chief_complaint") and state.get("user_input") and not is_followup_answer:
        clinical["original_chief_complaint"] = state.get("user_input")
        logger.info(f"Stored original chief complaint: {state.get('user_input')[:100]}")
    
    state["clinical"] = clinical

    user_ctx = _build_user_context(state)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT + " " + _get_output_schema_hint()),
        HumanMessage(
            content=(
                "Assess urgency using digital triage principles (Infermedica/Ada style). "
                "Identify red flags (e.g., chest pain, breathing difficulty). "
                "Consider age, chronic conditions, pregnancy, medications. "
                "If uncertain, choose higher urgency. "
                "CRITICAL: Only ask follow-up questions for information NOT already provided in patient context. "
                "Do NOT ask for duration, symptoms, or details the user has already mentioned. "
                "If severity/duration/key symptoms are clear from context, proceed with triage. "
                "Do not diagnose or recommend medications.\n\n"
                f"Patient context:\n{user_ctx}"
            )
        ),
    ]

    try:
        resp = llm.invoke(
            messages,
            config={
                "run_name": "SymptomTriageAssessment",
                "tags": [
                    "agent:SymptomTriageAgent",
                    "route:triage",
                    "component:clinical",
                    "capability:urgency_assessment"
                ],
                "metadata": {
                    "has_clinical_context": bool(user_ctx and len(user_ctx) > 50),
                    "has_followup_answers": bool(clinical.get("answered_followups")),
                    "patient_id": patient_id or "anonymous",
                    "has_patient_profile": bool(clinical.get("patient_first_name")),
                    "age_source": "database" if clinical.get("patient_first_name") and clinical.get("age") else "user_provided"
                }
            },
        )
        parsed = _safe_parse(resp.content if hasattr(resp, "content") else resp)
        # If the model returned a dict wrapper without triage, try parsing its text payload.
        if isinstance(parsed, dict) and "triage" not in parsed and parsed.get("text"):
            parsed = _safe_parse(parsed.get("text"))
    except Exception:
        parsed = _safe_parse(None)

    triage = parsed.get("triage") or {}
    ehr = parsed.get("ehr_record") or {}
    # Normalize follow-ups: accept legacy key and convert.
    followups = parsed.get("follow_up_requests")
    if followups is None:
        legacy = parsed.get("follow_up_questions") or []
        followups = []
        for idx, q in enumerate(legacy):
            if isinstance(q, str) and q.strip():
                followups.append(
                    {
                        "intent": f"unknown_{idx}",
                        "question": q.strip(),
                        "confidence_blocking": True,
                    }
                )
    parsed["follow_up_requests"] = followups or []
    followups = parsed["follow_up_requests"]
    clinical = state.get("clinical", {}) or {}
    # Drop any follow-ups whose intent is already resolved.
    resolved_keys = set((clinical.get("resolved_intents") or {}).keys())
    # Filter using normalized lower-case keys
    followups = [
        fq for fq in (followups or []) 
        if fq.get("intent") and fq["intent"].strip().lower() not in resolved_keys
    ]
    parsed["follow_up_requests"] = followups

    is_emergency = triage.get("triage_level") == "emergency"

    # Emergency is terminal: discard follow-ups and finalize immediately.
    if is_emergency:
        followups = []
        parsed["follow_up_requests"] = []
    else:
        # For non-emergency, block until required intents are answered.
        blocking = [fq for fq in followups if fq.get("confidence_blocking") is True and fq.get("intent")]
        if blocking:
            clinical = dict(state.get("clinical", {}) or {})
            clinical["pending_follow_up"] = True
            clinical["follow_up_requests"] = blocking
            state["clinical"] = clinical
            execution = state.get("execution", {}) or {}
            execution["awaiting_followup"] = True
            execution["pending_agent"] = "SymptomTriageAgent"
            state["execution"] = execution
            return state

    clinical = state.get("clinical", {}) or {}
    care = state.get("care", {}) or {}
    
    # CRITICAL: Clear stale specialty from previous triage so clinic agent uses fresh one
    care.pop("_triage_specialty_backup", None)
    care.pop("required_specialty", None)
    care.pop("raw_specialty_input", None)
    care.pop("specialty_selection_audit", None)
    state["care"] = care
    logger.info("Cleared stale specialty backup for fresh triage result")
    
    # Finalize path: clear follow-ups, store triage result, set urgency, persist.
    parsed["follow_up_requests"] = []
    clinical["triage_result"] = parsed
    triage_level = (parsed.get("triage") or {}).get("triage_level")
    if triage_level:
        clinical["urgency_level"] = triage_level
    
    # PRIORITY 1: Use LLM-recommended specialty (most reliable)
    triage_obj = parsed.get("triage", {}) or {}
    llm_specialty = triage_obj.get("recommended_specialty")
    
    if llm_specialty and llm_specialty.strip() and llm_specialty.lower() != "null":
        clinical["triage_specialty"] = llm_specialty
        logger.info(f"Set triage_specialty from LLM recommendation: {llm_specialty}")
    else:
        # FALLBACK: Keyword matching for backward compatibility
        ehr = parsed.get("ehr_record", {}) or {}
        chief_complaint = ehr.get("chief_complaint", "").lower()
        
        # Simple specialty mapping based on chief complaint
        specialty_mapping = {
            "dengue": "General Practice",
            "fever": "General Practice",
            "cough": "General Practice",
            "cold": "General Practice",
            "flu": "General Practice",
            "respiratory": "General Practice",
            "chest pain": "Cardiology",
            "heart": "Cardiology",
            "breathing": "General Practice",
            "headache": "General Practice",
            "skin": "Dermatology",
            "rash": "Dermatology",
            "stomach": "Gastroenterology",
            "abdominal": "Gastroenterology",
            "eye": "Ophthalmology",
            "ear": "ENT",
            "throat": "ENT",
            "sinus": "ENT",
            "mental": "Mental health service",
            "anxiety": "Mental health service",
            "depression": "Mental health service",
        }
        
        for keyword, specialty in specialty_mapping.items():
            if keyword in chief_complaint:
                clinical["triage_specialty"] = specialty
                logger.info(f"Set triage_specialty via keyword '{keyword}': {specialty}")
                break
        
        # If urgent/emergency and still no specialty, default to General Practice
        if triage_level in ["emergency", "urgent"] and "triage_specialty" not in clinical:
            clinical["triage_specialty"] = "General Practice"
            logger.info(f"Set triage_specialty to General Practice for {triage_level} triage")
    
    state["clinical"] = clinical
    execution = state.get("execution", {}) or {}
    execution["awaiting_followup"] = False
    execution["pending_agent"] = None
    state["execution"] = execution

    # Persist to Supabase if patient_id is available and no follow-ups are pending
    patient_id = state.get("patient_id")
    if patient_id:
        try:
            sb = get_supabase_client()
            triage = parsed.get("triage") or {}
            ehr = parsed.get("ehr_record") or {}
            payload = {
                "patient_id": patient_id,
                "user_id": state.get("user_id"),
                "triage_level": triage.get("triage_level"),
                "urgency_score": triage.get("urgency_score"),
                "recommended_action": triage.get("recommended_action"),
                "chief_complaint": ehr.get("chief_complaint"),
                "symptoms": ehr.get("symptoms"),
                "associated_symptoms": ehr.get("associated_symptoms"),
                "risk_factors": ehr.get("risk_factors"),
                "red_flags_detected": ehr.get("red_flags_detected"),
                "clinical_considerations": ehr.get("clinical_considerations"),
                "disclaimer": ehr.get("disclaimer"),
                "follow_up_questions": [],
                "source_agent": "SymptomTriageAgent",
            }
            resp = sb.table("Symptom EHR").insert(payload).execute()
            if resp.data:
                clinical["triage_ehr_id"] = resp.data[0].get("id")
                state["clinical"] = clinical
        except Exception as e:
            # Log error but don't fail the agent
            logger.error(f"Failed to save Symptom EHR for patient {patient_id}: {e}")
    
    # Store confirmed medical history to LTM (90-day expiration for medical data)
    from datetime import datetime, timedelta
    
    # CRITICAL FIX: conversation_id has "session-" prefix but DB expects raw UUID
    raw_conversation_id = state.get("conversation_id", "")
    encounter_id = raw_conversation_id.replace("session-", "") if raw_conversation_id else None
    patient_id = state.get("patient_id")
    ehr_record = parsed.get("ehr_record") or {} # Ensure ehr_record is defined
    
    if encounter_id and patient_id and ehr_record:
        try:
            # Store chief complaint as encounter topic
            chief_complaint = ehr_record.get("chief_complaint", "")
            if chief_complaint:
                upsert_encounter_memory(
                    encounter_id=encounter_id,
                    patient_id=patient_id,
                    memory_type="context",
                    memory_key="chief_complaint",
                    memory_value=chief_complaint
                )
            
            # Store triage level for this encounter
            urgency_level = clinical.get("urgency_level")
            if urgency_level:
                upsert_encounter_memory(
                    encounter_id=encounter_id,
                    patient_id=patient_id,
                    memory_type="context",
                    memory_key="triage_level",
                    memory_value=urgency_level
                )
            
            logger.info(f"Stored triage context in encounter memory for {encounter_id}")
        except Exception as e:
            logger.warning(f"Failed to store triage context to encounter memory: {e}")
    
    # Store important patient-level facts in global LTM (Patient Profile Memory)
    # These help future sessions understand patient history without exposing detailed medical data
    from app.tools.memory import upsert_long_term_memory
    
    if patient_id and ehr_record:
        expires_at = (datetime.utcnow() + timedelta(days=90)).isoformat()
        
        try:
            # 1. Extract and store chronic conditions from risk factors
            risk_factors = ehr_record.get("risk_factors", [])
            chronic_conditions = [rf for rf in risk_factors if any(
                term in rf.lower() for term in ["diabetes", "hypertension", "asthma", "copd", "heart disease", "arthritis", "cancer"]
            )]
            
            if chronic_conditions:
                upsert_long_term_memory(
                    patient_id=patient_id,
                    memory_type="context",
                    memory_key="chronic_conditions",
                    memory_value=chronic_conditions,
                    source_agent="SymptomTriageAgent",
                    confidence=0.9,
                    expires_at=expires_at
                )
            
            # 2. Store last triage date
            upsert_long_term_memory(
                patient_id=patient_id,
                memory_type="context",
                memory_key="last_triage_date",
                memory_value=datetime.utcnow().isoformat(),
                source_agent="SymptomTriageAgent",
                confidence=1.0,
                expires_at=expires_at
            )
            
            # 3. Store last triage level (useful for urgency patterns)
            triage_level = clinical.get("urgency_level") or (parsed.get("triage", {}).get("triage_level"))
            if triage_level:
                upsert_long_term_memory(
                    patient_id=patient_id,
                    memory_type="context",
                    memory_key="last_triage_level",
                    memory_value=triage_level,
                    source_agent="SymptomTriageAgent",
                    confidence=1.0,
                    expires_at=expires_at
                )
            
            # 4. Store recommended specialty (patient's primary health concern area)
            recommended_specialty = clinical.get("recommended_specialty") or (parsed.get("triage", {}).get("recommended_specialty"))
            if recommended_specialty:
                upsert_long_term_memory(
                    patient_id=patient_id,
                    memory_type="context",
                    memory_key="preferred_specialty",
                    memory_value=recommended_specialty,
                    source_agent="SymptomTriageAgent",
                    confidence=0.8,
                    expires_at=None  # No expiry - specialty preference is long-term
                )
            
            # 5. Store symptom keywords (top 3 main symptoms, helps identify recurring issues)
            chief_complaint = ehr_record.get("chief_complaint", "")
            if chief_complaint:
                stop_words = {'pain', 'feeling', 'having', 'been', 'very', 'some', 'like', 'with', 'from'}
                symptom_words = [w.lower() for w in chief_complaint.split() 
                                if len(w) > 3 and w.lower() not in stop_words]
                if symptom_words:
                    upsert_long_term_memory(
                        patient_id=patient_id,
                        memory_type="context",
                        memory_key="recent_symptoms",
                        memory_value=symptom_words[:5],  # Top 5 symptom keywords
                        source_agent="SymptomTriageAgent",
                        confidence=0.7,
                        expires_at=expires_at
                    )
            
            logger.info(f"Stored triage context to Patient Profile Memory for patient {patient_id}")
        except Exception as e:
            logger.warning(f"Failed to store triage context to LTM: {e}")

    return state

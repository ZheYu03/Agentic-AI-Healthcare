import time
import logging
import uuid
import json
import asyncio
from typing import Any, Dict, List, Optional, AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.planner import generate_plan
from app.workflows.orchestrator_graph import OrchestratorState, build_orchestrator
from app.tools.chat_persistence import (
    ensure_encounter_exists,
    save_message,
    update_encounter_summary
)
from app.utils.status_messages import get_agent_start_message, get_agent_status_message
from app.utils.sse_utils import (
    emit_status,
    emit_agent_start,
    emit_agent_complete,
    emit_execution_plan,
    emit_response_ready,
    emit_done,
    emit_error
)

app = FastAPI(title="LangGraph Healthcare Chat", version="0.1.0")

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint for deployment platforms."""
    return {"status": "healthy", "service": "agentic-ai-healthcare"}


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Agentic AI Healthcare API",
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "chat_stream": "/chat/stream"
        }
    }



class SessionStore:
    """
    Simple in-memory session store for short-term state across turns.
    TTL-based eviction keeps memory bounded; replace with Redis/DB for durability.
    """

    def __init__(self, ttl_seconds: int = 1800):
        self.ttl = ttl_seconds
        self._data: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        entry = self._data.get(key)
        if not entry:
            return None
        if time.time() - entry["ts"] > self.ttl:
            # Expired
            self._data.pop(key, None)
            return None
        return entry["state"]

    def set(self, key: str, state: Dict[str, Any]) -> None:
        self._data[key] = {"state": state, "ts": time.time()}

    def clear(self, key: str) -> None:
        self._data.pop(key, None)


SESSION_STATE = SessionStore()



class ChatRequest(BaseModel):
    input: str
    session_id: str
    encounter_id: Optional[str] = None
    patient_id: Optional[str] = None
    user_coordinates: Optional[List[float]] = None  # [lat, lon]
    # Optional profile hints
    age: Optional[int] = None
    sex: Optional[str] = None
    pregnancy_status: Optional[str] = None
    chronic_conditions: Optional[List[str]] = None
    medications: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    duration: Optional[str] = None
    severity: Optional[str] = None


graph = build_orchestrator()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _build_initial_state(body: ChatRequest, planner_output: Dict[str, Any]) -> OrchestratorState:
    clinical: Dict[str, Any] = {}
    if body.age is not None:
        clinical["age"] = body.age
    if body.sex:
        clinical["sex"] = body.sex
    if body.pregnancy_status:
        clinical["pregnancy_status"] = body.pregnancy_status
    if body.chronic_conditions:
        clinical["chronic_conditions"] = body.chronic_conditions
    if body.medications:
        clinical["medications"] = body.medications
    if body.allergies:
        clinical["allergies"] = body.allergies
    if body.duration:
        clinical["duration"] = body.duration
    if body.severity:
        clinical["severity"] = body.severity

    # Generate stable patient_id from session_id if not provided
    # This enables LTM (Long-Term Memory) to work across sessions
    patient_id = body.patient_id
    if not patient_id:
        # Use UUID5 (namespace-based) for deterministic, valid UUID from session_id
        # Use DNS namespace as base, session_id as name
        patient_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, body.session_id)
        patient_id = str(patient_uuid)
        logger.info(f"Generated patient_id from session: {patient_id}")

    state: OrchestratorState = {
        "conversation_id": body.session_id,
        "user_input": body.input,
        "planner_output": planner_output,
        "patient_id": patient_id,
        "execution": {
            "current_agent": None,
            "completed_agents": [],
            "status": "idle",
            "active_intent": planner_output.get("intent"),
            "pending_agent": None,
            "awaiting_followup": False,
        },
        "clinical": clinical,
        "care": {},
        "insurance": {},
        "errors": [],
    }

    # Pass user coordinates into care preferences if supplied
    if body.user_coordinates and len(body.user_coordinates) == 2:
        lat, lon = body.user_coordinates
        state["care"] = {"user_location": {"lat": lat, "lon": lon}}

    return state


def _build_followup_messages(followups: List[Any]) -> List[str]:
    """
    Accept either legacy string followups or intent-based follow_up_requests (dicts with 'question').
    """
    messages: List[str] = []
    for item in followups:
        if isinstance(item, str) and item.strip():
            messages.append(item.strip())
        elif isinstance(item, dict):
            q = item.get("question")
            if isinstance(q, str) and q.strip():
                messages.append(q.strip())
    return messages


def _triage_summary(final_state: Dict[str, Any]) -> Optional[str]:
    triage = (final_state.get("clinical") or {}).get("triage_result") or {}
    triage_block = triage.get("triage") or {}
    ehr = triage.get("ehr_record") or {}
    
    level = triage_block.get("triage_level")
    action = triage_block.get("recommended_action")
    reasoning = triage_block.get("reasoning") or []
    red_flags = ehr.get("red_flags_detected") or []
    
    if not level and not action:
        return None
    
    # Build user-friendly summary
    lines = []
    
    # 1. Triage level (capitalize first letter)
    if level:
        level_display = level.capitalize()
        lines.append(f"Triage level: {level_display}\n")
    
    # 2. What this means (simplified reasoning)
    if reasoning:
        lines.append("What this means:")
        # Take first reasoning point as the main explanation
        lines.append(f"{reasoning[0]}\n")
    
    # 3. Recommended action
    if action:
        lines.append("Recommended action:")
        lines.append(f"{action}\n")
    
    # 4. Red flags / warning signs (if urgent or emergency)
    if level in ["urgent", "emergency"] and red_flags:
        lines.append("Go immediately or call emergency services if:")
        for flag in red_flags[:3]:  # Show top 3
            lines.append(f"• {flag}")
        lines.append("")
    
    # 5. Why this matters (additional reasoning)
    if len(reasoning) > 1:
        lines.append("Why this matters:")
        lines.append(f"{reasoning[1]}\n")
    
    # 6. Important note for non-emergency cases
    if level in ["semi-urgent", "non-urgent"]:
        lines.append("Important:")
        lines.append("This does not mean a serious condition is certain, but it is important to get evaluated. Avoid strenuous activity until you are seen by a healthcare provider.")
    
    return "\n".join(lines)


def _qna_summary(final_state: Dict[str, Any]) -> Optional[str]:
    mq = final_state.get("medical_qna") or {}
    answer = mq.get("answer")
    if not answer:
        return None
    
    # Try to parse if it's JSON
    import json
    import re
    try:
        if isinstance(answer, str) and answer.strip().startswith('['):
            parsed = json.loads(answer)
            if isinstance(parsed, list) and len(parsed) > 0:
                # Extract text from first item
                first_item = parsed[0]
                if isinstance(first_item, dict) and 'text' in first_item:
                    answer = first_item['text']
    except:
        pass
    
    # Clean up escaped newlines and formatting
    if isinstance(answer, str):
        answer = answer.replace('\\n\\n', '\n\n').replace('\\n', '\n')
        answer = answer.replace('\\"', '"')
        # Fix broken markdown
        answer = answer.replace('* **', '**')
        answer = re.sub(r'\*\s+\*\*', '**', answer)
        # Remove citation numbers
        answer = re.sub(r'\s*\[\d+(?:,\s*\d+)*\]', '', answer)
        answer = re.sub(r'\.\.+', '.', answer)
        # Remove markdown bold syntax
        answer = re.sub(r'\*\*([^*]+)\*\*', r'\1', answer)
    
    # Try to intelligently restructure the content
    lines = []
    
    # Extract sections if they exist
    sections = answer.split('\n\n')
    
    # Add "In short:" summary (first paragraph or create one)
    if sections:
        first_para = sections[0].strip()
        if len(first_para) < 300:  # If first paragraph is concise
            lines.append("In short:")
            lines.append(f"{first_para}\n")
            remaining_sections = sections[1:]
        else:
            remaining_sections = sections
    else:
        remaining_sections = [answer]
    
    # Add remaining content with better structure
    # Detect section headers and ensure they end with colon
    for section in remaining_sections:
        if not section.strip():
            continue
            
        section_lines = section.split('\n')
        first_line = section_lines[0].strip()
        
        # Check if first line looks like a header (short, title case, no ending punctuation)
        is_header = (
            len(first_line) < 50 and 
            len(first_line) > 0 and
            first_line[0].isupper() and
            not first_line.endswith('.') and
            not first_line.endswith('?') and
            not first_line.endswith('!')
        )
        
        if is_header:
            # Ensure header ends with colon
            if not first_line.endswith(':'):
                first_line = first_line + ':'
            lines.append(first_line)
            # Add rest of section content
            if len(section_lines) > 1:
                lines.append('\n'.join(section_lines[1:]))
        else:
            lines.append(section.strip())
        lines.append("")
    
    # Add when to see a doctor (if not already present)
    content = '\n'.join(lines)
    if 'when to see' not in content.lower() and 'seek medical' not in content.lower():
        lines.append("When to see a doctor:")
        lines.append("Seek medical advice if symptoms are severe, worsen, or last longer than expected.\n")
    
    # Add disclaimer
    lines.append("Note: This information is for general education and does not replace professional medical advice.")
    
    return '\n'.join(lines)


def _clinic_summary(final_state: Dict[str, Any]) -> Optional[str]:
    care = final_state.get("care") or {}
    recs = care.get("recommended_clinics") or []
    clinical = final_state.get("clinical") or {}
    
    # Check if clinic agent ran (has any output in care)
    has_specialty = care.get("required_specialty") or care.get("raw_specialty_input")
    
    if not recs:
        # If clinic agent ran but found nothing, explain why
        if has_specialty:
            specialty = care.get("required_specialty", "the requested specialty")
            return f"No clinics found for {specialty} in your area. Try a different specialty or location."
        return None
    
    # Get user context for LLM explanation
    user_specialty = care.get("required_specialty", "")
    urgency_level = clinical.get("urgency_level", "")
    chief_complaint = (clinical.get("triage_result") or {}).get("ehr_record", {}).get("chief_complaint", "")
    
    lines = []
    
    for idx, rec in enumerate(recs[:3]):  # Show top 3 clinics
        name = rec.get('name', 'Clinic')
        distance = rec.get('distance_km', 0)
        rating = rec.get('rating')
        facility_type = rec.get('facility_type', '')
        address = rec.get('address', '')
        city = rec.get('city', '')
        state = rec.get('state', '')
        phone = rec.get('phone', '')
        website = rec.get('website', '')
        services = rec.get('services', [])
        specialties = rec.get('specialties', [])
        operating_hours = rec.get('operating_hours', {})
        is_24_hours = rec.get('is_24_hours', False)
        has_emergency = rec.get('has_emergency', False)
        latitude = rec.get('latitude')
        longitude = rec.get('longitude')
        
        # Clinic header
        lines.append(f"{name}:")
        # Distance
        lines.append(f"Distance: {distance} km away")
        # Rating
        if rating:
            lines.append(f"Rating: {rating} / 5")
        # Facility type
        if facility_type:
            lines.append(f"Facility type: {facility_type}")
        # Address
        full_address = f"{city}, {state}" if city and state else (city or state or address)
        if full_address:
            lines.append(f"Address: {full_address}")
        # Location with navigation link
        if latitude and longitude:
            maps_url = f"https://www.google.com/maps/dir/?api=1&destination={latitude},{longitude}"
            lines.append(f"Location: {maps_url}")
        # Operating hours
        if is_24_hours:
            lines.append("Operating hours: 24 Hours")
        elif operating_hours:
            hours_str = _format_operating_hours(operating_hours)
            if hours_str:
                lines.append("Operating hours:")
                lines.append(hours_str)
        # Phone
        if phone:
            lines.append(f"Phone: {phone}")
        # Website
        if website:
            lines.append(f"Website: {website}")
        # Services offered (no spacing)
        if services and len(services) > 0:
            lines.append("Services offered:")
            for service in services[:3]:  # Top 3 services
                lines.append(f"• {service}")
        # Why this clinic is recommended (no spacing)
        lines.append("Why we recommend this clinic:")
        reasons = []
        if distance < 5:
            reasons.append("Very close to your location")
        elif distance < 10:
            reasons.append("Conveniently located nearby")
        if rating and rating >= 4.0:
            reasons.append("Highly rated by patients")
        if has_emergency and urgency_level in ["urgent", "emergency"]:
            reasons.append("Has emergency services for urgent cases")
        if is_24_hours:
            reasons.append("Open 24 hours for your convenience")
        if user_specialty and specialties:
            if any(user_specialty.lower() in s.lower() for s in specialties):
                reasons.append(f"Specializes in {user_specialty}")
        if facility_type:
            reasons.append(f"Specializes in {facility_type}")
        if not reasons:
            reasons.append("Good match based on your needs")
        for reason in reasons[:3]:
            lines.append(f"• {reason}")
        
        # Spacing between different clinics only
        if idx < len(recs[:3]) - 1:
            lines.append("")
            lines.append("")
    
    return "\n".join(lines)


def _format_operating_hours(hours) -> str:
    """Format operating hours to readable string showing all days."""
    if not hours:
        return ""
    try:
        import json
        
        # Parse if it's a JSON string
        if isinstance(hours, str):
            try:
                hours = json.loads(hours)
            except:
                return hours  # Return as-is if not valid JSON
        
        if not isinstance(hours, dict):
            return str(hours)
        
        # Handle weekday_text format from Google Places
        if "weekday_text" in hours:
            weekday_text = hours["weekday_text"]
            if isinstance(weekday_text, list) and len(weekday_text) > 0:
                # Format each day on separate line
                formatted_days = []
                for text in weekday_text:
                    # Clean unicode and extra spaces
                    clean = text.replace("\u202f", " ").replace("\u2013", "-").replace("–", "-")
                    clean = ' '.join(clean.split())  # Remove extra whitespace
                    # Remove ALL special unicode characters (including box icons)
                    clean = ''.join(c for c in clean if ord(c) < 128)
                    clean = clean.strip()
                    if clean:
                        formatted_days.append(f"• {clean}")
                return "\n".join(formatted_days)
        
        # Handle dict with day names
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        formatted_days = []
        for day in day_order:
            for key in [day, day.lower(), day[:3]]:
                if key in hours:
                    day_data = hours[key]
                    if isinstance(day_data, dict):
                        open_t = day_data.get("open", "")
                        close_t = day_data.get("close", "")
                        if open_t and close_t:
                            formatted_days.append(f"• {day}: {open_t} - {close_t}")
                    elif isinstance(day_data, str):
                        formatted_days.append(f"• {day}: {day_data}")
                    break
        
        if formatted_days:
            return "\n".join(formatted_days)
        
        return ""
    except:
        return ""


def _insurance_summary(final_state: Dict[str, Any]) -> Optional[str]:
    ins = final_state.get("insurance") or {}
    recs = ins.get("recommended_plans") or []
    
    # Check if insurance agent ran (has any output)
    has_profile = ins.get("user_profile")
    
    if not recs:
        # If insurance agent ran but found nothing, explain why
        if has_profile:
            age = has_profile.get("age")
            if age:
                return f"No insurance plans found for age {age}. Try adjusting your criteria."
            return "No insurance plans found. Try providing more information like age or budget."
        return None
    
    # Build detailed response for top recommendation
    lines = []
    
    for idx, rec in enumerate(recs[:3]):  # Show top 3 plans
        plan_name = rec.get('plan_name', 'Plan')
        provider_name = rec.get('provider_name', '')
        fit = rec.get('fit', 'good')
        premium_range = rec.get('monthly_premium_range', '')
        warnings = rec.get('warnings', [])
        
        # Get actual database values
        annual_limit = rec.get('annual_limit')
        deductible = rec.get('deductible')
        outpatient = rec.get('outpatient_covered')
        maternity = rec.get('maternity_covered')
        dental = rec.get('dental_covered')
        optical = rec.get('optical_covered')
        mental_health = rec.get('mental_health_covered')
        min_age = rec.get('min_age')
        max_age = rec.get('max_age')
        contact_phone = rec.get('contact_phone')
        website = rec.get('website')
        
        # Plan header
        lines.append(f"{plan_name} ({provider_name}):")
        # Best for section
        if fit == 'good':
            lines.append("Best for:")
            if min_age and max_age:
                lines.append(f"Adults aged {min_age}-{max_age} seeking medical coverage")
            else:
                lines.append("Adults seeking comprehensive medical coverage")
        # What it covers - from database fields
        lines.append("What it covers:")
        coverages = []
        if outpatient:
            coverages.append("Outpatient treatment")
        if maternity:
            coverages.append("Maternity benefits")
        if dental:
            coverages.append("Dental care")
        if optical:
            coverages.append("Optical/Vision")
        if mental_health:
            coverages.append("Mental health")
        if not coverages:
            coverages = ["Medical consultations", "Hospitalization"]
        for cov in coverages[:4]:
            lines.append(f"• {cov}")
        # Plan details from database
        lines.append("Plan details:")
        if annual_limit:
            lines.append(f"• Annual limit: RM{annual_limit:,}")
        if deductible:
            lines.append(f"• Deductible: RM{deductible}")
        if premium_range and premium_range != " - " and premium_range != "None - None":
            lines.append(f"• Premium: RM{premium_range}/month")
        # Why this plan is suitable
        lines.append("Why this plan is suitable:")
        if fit == 'good':
            lines.append("• Good match for your profile")
        else:
            lines.append("• Partial match for your needs")
        if mental_health:
            lines.append("• Includes mental health coverage")
        if outpatient:
            lines.append("• Outpatient benefits included")
        # Warnings if any
        if warnings:
            lines.append("Important notes:")
            for warning in warnings[:2]:
                lines.append(f"• {warning}")
        
        # Spacing before contact info
        lines.append("")
        # Contact info from database
        if contact_phone:
            lines.append(f"Customer Service: {contact_phone}")
        if website:
            lines.append(f"Website: {website}")
        
        # Spacing between different plans only
        if idx < len(recs[:3]) - 1:
            lines.append("")
            lines.append("")
    
    return "\n".join(lines)


def _extract_response_messages(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract all response messages from agent state for database persistence."""
    messages = []
    clinical = state.get("clinical", {})
    
    # Save triage result if it exists (final triage summary)
    triage_result = clinical.get("triage_result")
    if triage_result:
        triage_summary = _triage_summary(state)
        if triage_summary:
            messages.append({
                "content": triage_summary,
                "agent_name": "SymptomTriageAgent",
                "metadata": {"type": "triage", "urgency": clinical.get("urgency_level")}
            })
    
    # CRITICAL FIX: Save follow-up questions INDEPENDENTLY of triage_result
    # This ensures Q&A messages are saved even before triage is complete
    followups = clinical.get("follow_up_requests", [])
    if followups:
        for fq in followups:
            question = fq.get("question")
            if question:
                messages.append({
                    "content": question,
                    "agent_name": "SymptomTriageAgent",
                    "metadata": {"type": "followup", "intent": fq.get("intent")}
                })
    care = state.get("care", {})
    clinic_summary = _clinic_summary(state)
    if clinic_summary:
        messages.append({"content": clinic_summary, "agent_name": "ClinicRecommendationAgent", "metadata": {"type": "clinic_recommendation"}})
    clarification = care.get("clarification_question")
    if clarification:
        messages.append({"content": clarification, "agent_name": "ClinicRecommendationAgent", "metadata": {"type": "clarification", "clarification_type": care.get("clarification_type")}})
    insurance_summary = _insurance_summary(state)
    if insurance_summary:
        messages.append({"content": insurance_summary, "agent_name": "InsuranceAdvisorAgent", "metadata": {"type": "insurance_recommendation"}})
    ins = state.get("insurance", {})
    ins_clarification = ins.get("clarification_question")
    if ins_clarification:
        messages.append({"content": ins_clarification, "agent_name": "InsuranceAdvisorAgent", "metadata": {"type": "clarification", "clarification_type": ins.get("clarification_type")}})
    qna = state.get("medical_qna", {})
    qna_answer = qna.get("answer")
    if qna_answer:
        messages.append({"content": qna_answer, "agent_name": "MedicalQnAAgent", "metadata": {"type": "qna", "confidence": qna.get("confidence"), "source_count": len(qna.get("sources", []))}})
    errors = state.get("errors", [])
    if errors:
        error_text = "\n".join([f"- {err}" for err in errors])
        messages.append({"content": f"Some issues occurred:\n{error_text}", "agent_name": "System", "metadata": {"type": "error"}})
    return messages


@app.post("/chat/stream")
async def chat_stream(body: ChatRequest):
    """
    SSE streaming endpoint for real-time agent status updates.
    
    Returns Server-Sent Events showing:
    - execution_plan: Which agents will run
    - status: User-friendly status messages
    - agent_start: When each agent begins
    - agent_complete: When each agent finishes with summary
    - response_ready: Final messages to display
    - done: Stream completion
    """
    from app.entrypoints.chat_stream import chat_stream_generator
    
    return StreamingResponse(
        chat_stream_generator(body),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering for SSE
        }
    )


@app.post("/chat")
async def chat(body: ChatRequest):
    if not body.input.strip() or not body.session_id.strip():
        raise HTTPException(status_code=400, detail="Missing 'input' or 'session_id'")
    
    # Ensure encounter exists and save user message
    encounter_id = body.encounter_id
    patient_id = body.patient_id
    
    if encounter_id and patient_id:
        # Determine if this is the first message (for chief complaint)
        is_first_message = SESSION_STATE.get(body.session_id) is None
        chief_complaint = body.input[:100] if is_first_message else None
        
        # Create encounter if needed
        ensure_encounter_exists(encounter_id, patient_id, chief_complaint)
        
        # Save user message
        save_message(
            encounter_id=encounter_id,
            role="user",
            content=body.input
        )

    prev_state = SESSION_STATE.get(body.session_id)
    
    if prev_state:
        prev_exec = prev_state.get("execution") or {}
        
        # --- FOLLOW-UP PATH: Skip planner, reuse existing state/plan ---
        if prev_exec.get("awaiting_followup") or prev_exec.get("status") == "waiting_for_user":
            logger.info("[/chat] RESUME: session=%s pending_agent=%s", 
                        body.session_id, prev_exec.get("pending_agent"))
            state = prev_state
            state["user_input"] = body.input  # Update with user's follow-up answer
            # Keep planner_output IMMUTABLE - do NOT overwrite
            # Keep completed_agents intact
            # Keep pending_agent and awaiting_followup - dispatcher will handle resume
            if body.patient_id:
                state["patient_id"] = body.patient_id
            # CRITICAL: Reset status to allow dispatcher to enter RESUME path
            # (Dispatcher early-exits if status is still "waiting_for_user")
            execution = state.get("execution", {})
            execution["status"] = "idle"  # Reset so dispatcher can process
            state["execution"] = execution
            # Merge clinical hints if provided
            clinical = state.get("clinical", {}) or {}
            # CRITICAL: Set pending_follow_up=True so the agent ingests the answer
            clinical["pending_follow_up"] = True
            if body.age is not None: clinical["age"] = body.age
            if body.sex: clinical["sex"] = body.sex
            if body.pregnancy_status: clinical["pregnancy_status"] = body.pregnancy_status
            if body.chronic_conditions: clinical["chronic_conditions"] = body.chronic_conditions
            if body.medications: clinical["medications"] = body.medications
            if body.allergies: clinical["allergies"] = body.allergies
            if body.duration: clinical["duration"] = body.duration
            if body.severity: clinical["severity"] = body.severity
            state["clinical"] = clinical
            planner_output = state.get("planner_output") or {}
        else:
            # --- NEW REQUEST in existing session: Re-plan ---
            logger.info("[/chat] NEW REQUEST: session=%s", body.session_id)
            planner_context = {
                "active_intent": prev_exec.get("active_intent"),
                "pending_agent": prev_exec.get("pending_agent"),
                "awaiting_followup": False,
            }
            planner_output = generate_plan(body.input, conversation_context=planner_context)
            state = prev_state
            state["user_input"] = body.input
            state["planner_output"] = planner_output
            if body.patient_id:
                state["patient_id"] = body.patient_id
            # Merge clinical hints
            clinical = state.get("clinical", {}) or {}
            if body.age is not None: clinical["age"] = body.age
            if body.sex: clinical["sex"] = body.sex
            if body.pregnancy_status: clinical["pregnancy_status"] = body.pregnancy_status
            if body.chronic_conditions: clinical["chronic_conditions"] = body.chronic_conditions
            if body.medications: clinical["medications"] = body.medications
            if body.allergies: clinical["allergies"] = body.allergies
            if body.duration: clinical["duration"] = body.duration
            if body.severity: clinical["severity"] = body.severity
            state["clinical"] = clinical
            
            # CRITICAL FIX: Clear agent states so previous results don't carry over
            # This prevents old Q&A results from polluting new questions
            state["medical_qna"] = {}  # Clear previous Q&A results
            
            # Reset execution for fresh run
            state["execution"] = {
                "current_agent": None,
                "completed_agents": [],
                "status": "idle",
                "active_intent": prev_exec.get("active_intent"),
                "pending_agent": None,
                "awaiting_followup": False,
            }
    else:
        # --- BRAND NEW SESSION ---
        logger.info("[/chat] NEW SESSION: session=%s", body.session_id)
        planner_output = generate_plan(body.input, conversation_context=None)
        state = _build_initial_state(body, planner_output)

    # If planner output is unusably empty, reuse the previous non-empty plan as a fallback.
    if prev_state and not planner_output.get("agent_sequence") and prev_state.get("planner_output", {}).get("agent_sequence"):
        planner_output = prev_state["planner_output"]
        state["planner_output"] = planner_output

    # Fallback: if the planner returned no agent_sequence, derive a minimal route from intent.
    if not planner_output.get("agent_sequence"):
        intent = planner_output.get("intent")
        exec_state = state.get("execution") or {}
        intent_fallback = intent or exec_state.get("active_intent")
        fallback_map = {
            "medical_qna": ["MedicalQnAAgent"],
            "symptoms": ["SymptomTriageAgent"],
            "care_navigation": ["ClinicRecommendationAgent"],
            "insurance": ["InsuranceAdvisorAgent"],
        }
        planner_output["agent_sequence"] = fallback_map.get(intent_fallback, [])
        state["planner_output"] = planner_output

    logger.info("[/chat] session=%s planner_output=%s", body.session_id, planner_output)

    # Keep active intent updated when not awaiting a follow-up.
    exec_state = state.get("execution") or {}
    if not exec_state.get("awaiting_followup"):
        exec_state["active_intent"] = planner_output.get("intent")
    state["execution"] = exec_state

    # Track previously completed agents before execution
    prev_completed = set(exec_state.get("completed_agents", []))

    final_state = graph.invoke(state)
    SESSION_STATE.set(body.session_id, final_state)
    
    # Save assistant responses to database - ONLY from newly completed agents
    if encounter_id:
        # Track newly completed agents
        executed_agents = (final_state.get("execution") or {}).get("completed_agents") or []
        newly_completed = set(executed_agents) - prev_completed
        
        messages_to_save = []
        
        # Only save MedicalQnA response if agent just completed
        if "MedicalQnAAgent" in newly_completed:
            qna_msg = _qna_summary(final_state)
            if qna_msg:
                qna = final_state.get("medical_qna", {})
                messages_to_save.append({
                    "content": qna_msg,
                    "agent_name": "MedicalQnAAgent",
                    "metadata": {
                        "type": "qna",
                        "confidence": qna.get("confidence"),
                        "source_count": len(qna.get("sources", []))
                    }
                })
        
        # Only save triage result if agent just completed
        if "SymptomTriageAgent" in newly_completed:
            triage_msg = _triage_summary(final_state)
            if triage_msg:
                clinical = final_state.get("clinical", {})
                messages_to_save.append({
                    "content": triage_msg,
                    "agent_name": "SymptomTriageAgent",
                    "metadata": {
                        "type": "triage",
                        "urgency": clinical.get("urgency_level")
                    }
                })
            
            # Save new follow-up questions
            clinical = final_state.get("clinical", {})
            followups = clinical.get("follow_up_requests", [])
            for fq in followups:
                question = fq.get("question")
                if question:
                    messages_to_save.append({
                        "content": question,
                        "agent_name": "SymptomTriageAgent",
                        "metadata": {
                            "type": "followup",
                            "intent": fq.get("intent")
                        }
                    })
        
        # Only save clinic results if agent just completed
        if "ClinicRecommendationAgent" in newly_completed:
            clinic_msg = _clinic_summary(final_state)
            if clinic_msg:
                messages_to_save.append({
                    "content": clinic_msg,
                    "agent_name": "ClinicRecommendationAgent",
                    "metadata": {"type": "clinic_recommendation"}
                })
            
            # Save clarification question if exists
            care = final_state.get("care", {})
            clarification = care.get("clarification_question")
            if clarification:
                messages_to_save.append({
                    "content": clarification,
                    "agent_name": "ClinicRecommendationAgent",
                    "metadata": {
                        "type": "clarification",
                        "clarification_type": care.get("clarification_type")
                    }
                })
        
        # Only save insurance results if agent just completed
        if "InsuranceAdvisorAgent" in newly_completed:
            ins_msg = _insurance_summary(final_state)
            if ins_msg:
                messages_to_save.append({
                    "content": ins_msg,
                    "agent_name": "InsuranceAdvisorAgent",
                    "metadata": {"type": "insurance_recommendation"}
                })
            
            # Save clarification question if exists
            ins = final_state.get("insurance", {})
            ins_clarification = ins.get("clarification_question")
            if ins_clarification:
                messages_to_save.append({
                    "content": ins_clarification,
                    "agent_name": "InsuranceAdvisorAgent",
                    "metadata": {
                        "type": "clarification",
                        "clarification_type": ins.get("clarification_type")
                    }
                })
        
        # Save only new messages
        for msg in messages_to_save:
            save_message(
                encounter_id=encounter_id,
                role="assistant",
                content=msg["content"],
                agent_name=msg.get("agent_name"),
                metadata=msg.get("metadata")
            )
        
        # CRITICAL: Save follow-up questions even if triage isn't complete yet
        # Triage sets awaiting_followup=True and doesn't mark as complete when asking questions
        clinical = final_state.get("clinical", {})
        pending_follow_up = clinical.get("pending_follow_up", False)
        exec_state = final_state.get("execution", {})
        awaiting_followup = exec_state.get("awaiting_followup", False)
        
        if awaiting_followup or pending_follow_up:
            followups = clinical.get("follow_up_requests", [])
            logger.info(f"[/chat] Triage awaiting follow-up. Saving {len(followups)} follow-up questions")
            for idx, fq in enumerate(followups):
                question = fq.get("question")
                if question:
                    logger.info(f"[/chat] Saving follow-up {idx}: {question[:50]}...")
                    save_message(
                        encounter_id=encounter_id,
                        role="assistant",
                        content=question,
                        agent_name="SymptomTriageAgent",
                        metadata={
                            "type": "followup",
                            "intent": fq.get("intent")
                        }
                    )
        
        # Update encounter with urgency level if triage completed
        clinical = final_state.get("clinical", {})
        urgency_level = clinical.get("urgency_level")
        if urgency_level:
            update_encounter_summary(
                encounter_id=encounter_id,
                urgency_level=urgency_level
            )

    clinical = final_state.get("clinical") or {}
    followups = clinical.get("follow_up_questions") or clinical.get("follow_up_requests") or []
    pending = clinical.get("pending_follow_up", False)

    route = planner_output.get("agent_sequence", [])
    executed_agents = (final_state.get("execution") or {}).get("completed_agents") or []
    errors = final_state.get("errors") or []

    logger.info("[/chat] session=%s executed_agents=%s pending=%s followups=%s errors=%s",
                body.session_id, executed_agents, pending, followups, errors)

    # Follow-up phase: return only follow-up questions and stop.
    exec_state = final_state.get("execution") or {}
    awaiting_followup = exec_state.get("awaiting_followup", False)

    care = final_state.get("care") or {}
    pending_care = care.get("needs_clarification", False)
    care_question = care.get("clarification_question")

    ins = final_state.get("insurance") or {}
    pending_ins = ins.get("needs_clarification", False)
    ins_question = ins.get("clarification_question")

    if awaiting_followup or pending or followups or pending_care or pending_ins:
        # Build summaries for NEWLY COMPLETED agents (not from previous turns)
        messages: List[str] = []
        
        # Determine which agents completed in THIS turn (not previous turns)
        prev_completed = set()
        if prev_state:
            prev_exec = prev_state.get("execution", {})
            prev_completed = set(prev_exec.get("completed_agents", []))
        
        newly_completed = set(executed_agents) - prev_completed
        
        # If MedicalQnA JUST completed in this turn, show its result FIRST
        if "MedicalQnAAgent" in newly_completed:
            qna_msg = _qna_summary(final_state)
            if qna_msg: messages.append(qna_msg)
        
        # If triage JUST completed in this turn, show its result
        if "SymptomTriageAgent" in newly_completed:
            triage_msg = _triage_summary(final_state)
            if triage_msg: messages.append(triage_msg)
        
        # If clinic JUST completed in this turn, show its result
        if "ClinicRecommendationAgent" in newly_completed:
            clinic_msg = _clinic_summary(final_state)
            if clinic_msg: messages.append(clinic_msg)
        
        # If insurance JUST completed in this turn, show its result
        if "InsuranceAdvisorAgent" in newly_completed:
            ins_msg = _insurance_summary(final_state)
            if ins_msg: messages.append(ins_msg)
        
        # Now add follow-up questions
        followup_msgs = _build_followup_messages(followups)
        if pending_care and care_question:
            followup_msgs.append(care_question)
        if pending_ins and ins_question:
            followup_msgs.append(ins_question)
        
        messages.extend(followup_msgs)
            
        return {
            "messages": messages,
            "route": route,
            "execution_plan": planner_output,
            "executed_agents": executed_agents,
            "patient_context": {"patient_id": body.patient_id},
        }

    # Decision phase: build patient-facing summaries.
    # ONLY show summaries for agents that completed in THIS turn, not previous turns
    messages: List[str] = []
    
    # Determine which agents completed in THIS turn (not previous turns)
    prev_completed = set()
    if prev_state:
        prev_exec = prev_state.get("execution", {})
        prev_completed = set(prev_exec.get("completed_agents", []))
    
    newly_completed = set(executed_agents) - prev_completed
    
    # DEBUG: Log to help diagnose triage summary issue
    logger.info(f"[/chat] Decision phase: executed_agents={executed_agents}, prev_completed={prev_completed}, newly_completed={newly_completed}")
    
    # Only show summaries for newly completed agents
    if "SymptomTriageAgent" in newly_completed:
        triage_msg = _triage_summary(final_state)
        if triage_msg: 
            logger.info(f"[/chat] Adding triage summary (newly completed)")
            messages.append(triage_msg)
    
    if "MedicalQnAAgent" in newly_completed:
        qna_msg = _qna_summary(final_state)
        if qna_msg: messages.append(qna_msg)
    
    if "ClinicRecommendationAgent" in newly_completed:
        clinic_msg = _clinic_summary(final_state)
        if clinic_msg: messages.append(clinic_msg)
    
    if "InsuranceAdvisorAgent" in newly_completed:
        ins_msg = _insurance_summary(final_state)
        if ins_msg: messages.append(ins_msg)

    if not messages:
        messages.append("I've captured your request. If you have more details, please share them.")

    return {
        "messages": messages,
        "route": route,
        "execution_plan": planner_output,
        "executed_agents": executed_agents,
        "patient_context": {"patient_id": body.patient_id},
    }

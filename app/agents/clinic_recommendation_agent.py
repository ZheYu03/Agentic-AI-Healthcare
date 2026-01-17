import json
import logging
import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.agents.planner import _build_llm
from app.core.config import get_settings
from app.tools.supabase_tool import get_supabase_client
from app.tools.memory import upsert_long_term_memory

logger = logging.getLogger(__name__)

# Allowed specialties for filtering and normalization
ALLOWED_SPECIALTIES = [
    "Acupuncture clinic",
    "Aromatherapy service",
    "Cardiologist",
    "Cardiovascular and thoracic surgeon",
    "Child health care center",
    "Chinese physician clinic",
    "Dental clinic",
    "Dermatology",
    "Dialysis center",
    "Diagnostic center",
    "Emergency care physician",
    "ENT",
    "Gastroenterology",
    "General Practice",
    "Health counselor",
    "Mental health service",
    "Ophthalmology",
    "Physical therapist",
    "Sports medicine physician",
    "Urology clinic",
    "X-ray lab",
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Pure haversine distance in kilometers."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def parse_open_now(
    operating_hours: Optional[Dict[str, Any]],
    now_dt: Optional[datetime],
    is_24_hours: bool = False,
) -> bool:
    """
    Tolerant open-today check for human-formatted hours.
    Rules:
    - If is_24_hours: open.
    - If data missing/malformed: closed.
    - Open if today's weekday (full or short) appears in the line OR a day-range
      (Mon–Fri, Sun–Thu) covers today, and the line does not say Closed.
    - Time-of-day is ignored to avoid false positives from brittle parsing.
    """
    if is_24_hours:
        return True
    if not operating_hours or "weekday_text" not in operating_hours:
        return False

    weekday_text = operating_hours.get("weekday_text") or []
    if not weekday_text:
        return False

    now_dt = now_dt or datetime.now()
    full_day = now_dt.strftime("%A").lower()   # e.g., wednesday
    short_day = now_dt.strftime("%a").lower()  # e.g., wed

    day_order = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    day_to_idx = {d: i for i, d in enumerate(day_order)}

    def in_range(token: str) -> bool:
        """
        Check tokens like 'mon-fri' or 'sun–thu' (full or short forms) to see
        if today falls within the range.
        """
        token = token.replace("—", "-").replace("–", "-").lower()
        if "-" not in token:
            return False
        start, end = [t.strip() for t in token.split("-", 1)]

        def day_key(val: str) -> Optional[str]:
            val = val.strip().lower()
            if len(val) >= 3:
                val = val[:3]
            return val if val in day_to_idx else None

        s_key, e_key = day_key(start), day_key(end)
        if s_key is None or e_key is None:
            return False
        s_idx, e_idx = day_to_idx[s_key], day_to_idx[e_key]
        today_idx = day_to_idx[short_day]
        if s_idx <= e_idx:
            return s_idx <= today_idx <= e_idx
        # wrap-around ranges (e.g., thu-mon)
        return today_idx >= s_idx or today_idx <= e_idx

    for raw_line in weekday_text:
        # Drop holiday annotations after '(' and normalize spaces
        cleaned = raw_line.split("(", 1)[0].strip()
        lowered = cleaned.lower()
        if "closed" in lowered:
            continue
        # Fast path: explicit day mention
        if full_day in lowered or short_day in lowered:
            return True
        # Check any token for a day range
        for tok in lowered.replace(",", " ").split():
            if in_range(tok):
                return True

    return False


def normalize_specialty_input(user_text: str, llm=None, allowed_list: Optional[List[str]] = None) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Deterministic normalization first; optional LLM fallback with strict JSON.
    Returns (specialty_or_none, audit_dict).
    """
    allowed = allowed_list or ALLOWED_SPECIALTIES
    text = (user_text or "").strip().lower()
    audit = {"method": "deterministic", "input": user_text, "output": None, "confidence": 0.0, "rationale": ""}

    # Exact/trimmed match
    for spec in allowed:
        if text == spec.lower():
            audit.update({"output": spec, "confidence": 1.0})
            return spec, audit

    # Simple synonym map
    synonym_map = {
        "dentist": "Dental clinic",
        "dental": "Dental clinic",
        "xray": "X-ray lab",
        "x-ray": "X-ray lab",
        "physio": "Physical therapist",
        "physiotherapy": "Physical therapist",
        "mental": "Mental health service",
        "counsellor": "Health counselor",
        "counselor": "Health counselor",
        "heart": "Cardiologist",
        "gp": "General Practice",
        "general practitioner": "General Practice",
        "family doctor": "General Practice",
        "skin": "Dermatology",
        "dermatologist": "Dermatology",
        "stomach": "Gastroenterology",
        "digestive": "Gastroenterology",
        "gastro": "Gastroenterology",
        "eye": "Ophthalmology",
        "eyes": "Ophthalmology",
        "vision": "Ophthalmology",
        "ear nose throat": "ENT",
        "ear": "ENT",
    }
    if text in synonym_map and synonym_map[text] in allowed:
        spec = synonym_map[text]
        audit.update({"output": spec, "confidence": 0.9})
        return spec, audit

    # LLM fallback
    audit["method"] = "llm"
    if not llm:
        audit["rationale"] = "No LLM provided."
        return None, audit

    prompt = (
        "You are normalizing a user-provided clinic specialty into one allowed value. "
        "Allowed: " + ", ".join(allowed) + ". "
        "Return JSON only: {\"specialty\": \"<allowed_or_null>\", \"confidence\": 0..1, \"rationale\": \"short\"}."
        "If unsure, return null."
    )
    try:
        resp = llm.invoke(
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_text},
            ],
            config={
                "run_name": "SpecialtyNormalization",
                "tags": [
                    "agent:ClinicRecommendationAgent",
                    "route:care_navigation",
                    "component:specialty_normalization"
                ],
                "metadata": {
                    "raw_specialty": user_text,
                    "allowed_specialties_count": len(allowed or [])
                }
            },
        )
        # Handle different response formats (Gemini returns list like [{'text': '...'}])
        if isinstance(resp.content, str):
            content = resp.content
        elif isinstance(resp.content, list) and len(resp.content) > 0:
            # Gemini format: [{'text': '{"specialty": "..."}'}]
            first_part = resp.content[0]
            if isinstance(first_part, dict) and 'text' in first_part:
                content = first_part['text']
            elif isinstance(first_part, str):
                content = first_part
            else:
                content = json.dumps(resp.content)
        else:
            content = json.dumps(resp.content)
        
        # Strip markdown code blocks if present
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]  # Remove ```json
        elif content.startswith("```"):
            content = content[3:]  # Remove ```
        if content.endswith("```"):
            content = content[:-3]  # Remove trailing ```
        content = content.strip()
        
        data = json.loads(content)
        specialty = data.get("specialty")
        if specialty not in allowed:
            specialty = None
        audit.update(
            {
                "output": specialty,
                "confidence": float(data.get("confidence") or 0.0),
                "rationale": data.get("rationale") or "",
            }
        )
        return specialty, audit
    except Exception as exc:
        audit["rationale"] = f"LLM normalization failed: {exc}"
        return None, audit


def get_required_specialty(state: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Decide required_specialty per priority rules.
    Priority (highest to lowest):
    1. User's explicit input in current turn (required_specialty in care state)
    2. Triage specialty from previous turn (triage_specialty in clinical state)
    3. None (need clarification)
    """
    clinical = state.get("clinical", {})
    care = state.get("care", {})
    
    # Priority 1: Explicitly set in care state (from user input in THIS turn)
    # This takes precedence over triage because user is explicitly requesting a specialty
    care_spec = care.get("required_specialty")
    if care_spec in ALLOWED_SPECIALTIES:
        return care_spec, {"source": "user_input"}
    
    # Priority 2: triage_specialty (fallback from previous turn)
    # Use this if user hasn't explicitly provided a specialty
    triage_spec = clinical.get("triage_specialty")
    if triage_spec in ALLOWED_SPECIALTIES:
        return triage_spec, {"source": "triage"}

    # Priority 3: missing -> need clarification
    return None, {"source": "missing"}


def query_candidate_clinics(
    required_specialty: str,
    urgent: bool,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Query Supabase for clinic candidates with server-side filters.
    Returns (rows, error_message).
    """
    try:
        supabase = get_supabase_client()
        query = (
            supabase.table("Clinic Facilities")
            .select("*")
            .eq("is_active", True)
            .not_.is_("latitude", "null")
            .not_.is_("longitude", "null")
            .contains("specialties", [required_specialty])
        )
        if urgent:
            # Urgent: prefilter for 24h or emergency
            query = query.or_("is_24_hours.eq.true,has_emergency.eq.true")
        resp = query.execute()
        rows = resp.data or []
        return rows, None
    except Exception as exc:
        return [], f"Supabase clinic query failed: {exc}"


def clinic_recommendation_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clinic Recommendation Agent:
    - Hydrate LTM
    - Clarify missing specialty/location
    - Query Supabase with strict filters, no LLM filtering
    - Post-filter for open_now (non-urgent) and distance, rank top 3
    - Write audit and results into state['care']
    - Optional LTM write only if confirmed_by_user is True
    """
    care = state.get("care", {})
    clinical = state.get("clinical", {})
    errors = state.get("errors", [])
    patient_id = state.get("patient_id")

    # CRITICAL: Preserve triage recommended_specialty FIRST before any extraction or clearing
    # Priority: Use recommended_specialty from triage LLM output (most reliable)
    triage_result = clinical.get("triage_result", {})
    triage_obj = triage_result.get("triage", {}) if isinstance(triage_result, dict) else {}
    recommended_specialty = triage_obj.get("recommended_specialty")
    
    # Also check old triage_specialty field for backward compatibility
    if not recommended_specialty:
        recommended_specialty = clinical.get("triage_specialty")
    
    if recommended_specialty and recommended_specialty.strip() and recommended_specialty.lower() != "null":
        care["_triage_specialty_backup"] = recommended_specialty
        logger.info(f"Preserved triage recommended_specialty: {recommended_specialty}")

    # --- UPFRONT EXTRACTION: Extract specialty/location from user message ---
    # This reduces unnecessary clarification questions
    # RUN THIS FIRST, before follow-up ingestion
    if state.get("user_input") and not care.get("extracted_clinic_info"):
        from app.agents.structured_extraction import extract_clinic_request
        try:
            llm = _build_llm(get_settings())
            extracted = extract_clinic_request(state.get("user_input", ""), llm)
            
            # Populate raw inputs if extracted (will be used by normalization)
            extracted_anything = False
            if extracted.get("specialty"):
                # CRITICAL: Only clear old results if user is providing a NEW specialty
                # This preserves triage_specialty when user just asks "find clinic near me"
                care.pop("recommended_clinics", None)
                care.pop("required_specialty", None)
                care.pop("filter_audit", None)
                care.pop("specialty_selection_audit", None)
                
                care["raw_specialty_input"] = extracted["specialty"]
                logger.info(f"Pre-extracted specialty: {extracted['specialty']}")
                extracted_anything = True
            
            if extracted.get("location"):
                care["raw_location_input"] = extracted["location"]
                # Try geocoding immediately
                from app.tools.geocoding import geocode_location
                coords = geocode_location(extracted["location"])
                if coords:
                    care["user_location"] = coords
                    logger.info(f"Pre-extracted & geocoded location: {extracted['location']} → {coords}")
                extracted_anything = True
            
            # Only mark as extracted if we actually found something
            # This allows extraction to run again if first attempt found nothing
            if extracted_anything:
                care["extracted_clinic_info"] = True
            state["care"] = care
        except Exception as e:
            logger.error(f"Upfront extraction failed: {e}")

    # --- INGEST FOLLOW-UP ANSWER ---
    # If we were awaiting clarification and user provided input, ingest it
    # BUT: If extraction already ran and found something, don't overwrite
    if care.get("needs_clarification") and state.get("user_input"):
        user_input = state.get("user_input", "").strip()
        clarification_type = care.get("clarification_type")
        
        if clarification_type == "specialty":
            # CRITICAL: Clear old results when changing specialty
            care.pop("recommended_clinics", None)
            care.pop("required_specialty", None)
            care.pop("filter_audit", None)
            care.pop("specialty_selection_audit", None)
            
            # Check if user is accepting LTM suggestion
            ltm_suggestion = care.get("ltm_specialty_suggestion")
            if ltm_suggestion and user_input.lower().strip() in ["yes", "y", "yeah", "yep"]:
                # User accepted LTM suggestion
                care["raw_specialty_input"] = ltm_suggestion
                logger.info(f"User accepted LTM specialty suggestion: {ltm_suggestion}")
            elif not care.get("raw_specialty_input"):
                # Normal specialty input
                care["raw_specialty_input"] = user_input
            # Clear suggestion flag
            care.pop("ltm_specialty_suggestion", None)
        elif clarification_type == "location":
            # Only overwrite if extraction didn't find location
            if not care.get("raw_location_input"):
                care["raw_location_input"] = user_input
            
            # Try to geocode if we stored something
            if care.get("raw_location_input") and not care.get("user_location"):
                try:
                    from app.tools.geocoding import geocode_location
                    coords = geocode_location(care["raw_location_input"])
                    if coords:
                        care["user_location"] = coords
                        logger.info(f"Geocoded user location: {care['raw_location_input']} → {coords}")
                    else:
                        logger.warning(f"Failed to geocode location: {care['raw_location_input']}")
                except Exception as e:
                    logger.error(f"Geocoding error: {e}")
        
        # Clear the clarification flags so we don't re-ask
        care["needs_clarification"] = False
        care.pop("clarification_question", None)
        care.pop("clarification_type", None)
        # CRITICAL: Reset extracted flag so extraction runs again on next message
        care["extracted_clinic_info"] = False
        state["care"] = care

    # Note: LTM hydration now handled by orchestrator wrapper
    care = state.get("care", {})
    clinical = state.get("clinical", {})
    
    # CRITICAL: Restore triage specialty from backup if required_specialty was cleared
    # This ensures triage specialty is ALWAYS used when available
    triage_backup = care.get("_triage_specialty_backup")
    if triage_backup and not care.get("required_specialty") and not care.get("raw_specialty_input"):
        # No user override, restore triage specialty
        care["required_specialty"] = triage_backup
        care["specialty_selection_audit"] = {
            "method": "triage",
            "input": triage_backup,
            "output": triage_backup,
            "confidence": 1.0
        }
        state["care"] = care
        logger.info(f"Restored triage_specialty from backup: {triage_backup}")
    
    # SECONDARY: Normalize raw_specialty_input if user explicitly provided one
    # This allows user to override triage specialty
    raw_specialty = care.get("raw_specialty_input")
    if raw_specialty:
        # User is explicitly requesting a specialty - this overrides triage
        try:
            llm = _build_llm(get_settings())
        except Exception:
            llm = None
        normalized, audit = normalize_specialty_input(raw_specialty, llm=llm, allowed_list=ALLOWED_SPECIALTIES)
        if normalized:
            care["required_specialty"] = normalized
            care["specialty_selection_audit"] = audit
            state["care"] = care
            logger.info(f"User override: normalized '{raw_specialty}' → '{normalized}'")
    
    # Now determine required_specialty with correct priority
    required_specialty, specialty_meta = get_required_specialty(state)
    if not required_specialty:
        # Ask for specialty if still missing
        care["needs_clarification"] = True
        care["clarification_type"] = "specialty"
        care["clarification_question"] = (
            "Which clinic specialty do you need? Choose one: " + ", ".join(ALLOWED_SPECIALTIES)
        )
        
        state["care"] = care
        # FIX: Signal orchestrator to pause and wait for user input
        execution = state.get("execution") or {}
        execution["awaiting_followup"] = True
        execution["pending_agent"] = "ClinicRecommendationAgent"
        state["execution"] = execution
        return state

    # Location check
    user_loc = care.get("user_location")
    if not user_loc or "lat" not in user_loc or "lon" not in user_loc:
        # Always set the location question (even if we just cleared needs_clarification)
        care["needs_clarification"] = True
        care["clarification_type"] = "location"
        care["clarification_question"] = "What is your current location (lat, lon) or postcode/city?"
        state["care"] = care
        # FIX: Signal orchestrator to pause and wait for user input
        execution = state.get("execution") or {}
        execution["awaiting_followup"] = True
        execution["pending_agent"] = "ClinicRecommendationAgent"
        state["execution"] = execution
        return state

    lat, lon = float(user_loc["lat"]), float(user_loc["lon"])
    urgency_level = clinical.get("urgency_level")
    urgent = urgency_level == "high"

    # Supabase query
    rows, err = query_candidate_clinics(required_specialty, urgent)
    if err:
        errors.append(err)
        state["errors"] = errors
        return state

    # Post-filter
    max_distance = care.get("preferences", {}).get("max_distance_km", 25.0)
    now_dt = datetime.now()
    filtered: List[Dict[str, Any]] = []
    for row in rows:
        try:
            rlat, rlon = float(row.get("latitude")), float(row.get("longitude"))
        except (TypeError, ValueError):
            continue
        distance = haversine_km(lat, lon, rlat, rlon)
        if distance > max_distance:
            continue
        open_now = True
        if not urgent:
            open_now = parse_open_now(
                row.get("operating_hours"),
                now_dt,
                is_24_hours=bool(row.get("is_24_hours")),
            )
        if not open_now:
            continue
        # Validate website URL - filter out malformed Google redirect URLs
        website = row.get("website", "")
        if website:
            # Filter out malformed URLs:
            # - Must start with http:// or https://
            # - Don't include Google redirect patterns (/aclk, /url?, etc.)
            # - Must be reasonably short (< 200 chars for clean URLs)
            website = website.strip()
            is_valid = (
                website.startswith(("http://", "https://")) and
                "/aclk" not in website and
                "/url?" not in website and
                "?sa=" not in website and
                len(website) < 200
            )
            if not is_valid:
                website = ""  # Clear invalid URLs
        
        filtered.append(
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "distance_km": round(distance, 2),
                "rating": row.get("google_rating"),
                "is_24_hours": row.get("is_24_hours"),
                "has_emergency": row.get("has_emergency"),
                "address": row.get("address"),
                "city": row.get("city"),
                "state": row.get("state"),
                "facility_type": row.get("facility_type"),
                "phone": row.get("phone"),
                "website": website,
                "services": row.get("services") or [],
                "specialties": row.get("specialties") or [],
                "operating_hours": row.get("operating_hours"),
                "latitude": row.get("latitude"),
                "longitude": row.get("longitude"),
            }
        )

    # Rank
    filtered.sort(key=lambda x: (x["distance_km"], -(x["rating"] or -1)))
    top3 = filtered[:3]

    # Audit
    care["filter_audit"] = {
        "required_specialty": required_specialty,
        "urgency_level": urgency_level,
        "max_distance_km": max_distance,
        "open_now_policy": "skip" if urgent else "require_open_now",
        "candidates_count_pre": len(rows),
        "candidates_count_post": len(filtered),
    }
    care["required_specialty"] = required_specialty
    care["recommended_clinics"] = top3
    care.pop("needs_clarification", None)
    care.pop("clarification_type", None)
    care.pop("clarification_question", None)
    care.pop("extracted_clinic_info", None)  # Clear to avoid polluting next agent

    # Auto-confirm for LTM: If we have recommendations and patient_id, store preferences
    if patient_id and top3:
        care["confirmed_by_user"] = True
        logger.info(f"Auto-confirming preferences for patient {patient_id}")

    # Optional LTM writes if user confirmed
    if patient_id and care.get("confirmed_by_user"):
        # context: preferred_specialty
        upsert_long_term_memory(
            patient_id=patient_id,
            memory_type="context",
            memory_key="preferred_specialty",
            memory_value=required_specialty,
            source_agent="ClinicRecommendationAgent",
        )
        prefs = care.get("preferences", {})
        if "max_distance_km" in prefs:
            upsert_long_term_memory(
                patient_id=patient_id,
                memory_type="preference",
                memory_key="max_distance_km",
                memory_value=prefs["max_distance_km"],
                source_agent="ClinicRecommendationAgent",
            )
        if "clinic_type" in prefs:
            upsert_long_term_memory(
                patient_id=patient_id,
                memory_type="preference",
                memory_key="clinic_type",
                memory_value=prefs["clinic_type"],
                source_agent="ClinicRecommendationAgent",
            )

    state["care"] = care
    state["errors"] = errors
    return state

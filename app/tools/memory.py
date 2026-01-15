"""
Long-term memory helpers for Supabase-backed storage.

Rules:
- Read at agent entry to hydrate missing short-term fields.
- Write only confirmed, non-diagnostic facts (preferences/constraints/context).
- Never store raw chat logs, symptoms, or diagnoses.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langsmith import traceable

from app.tools.supabase_tool import get_supabase_client

TABLE_NAME = 'Patient Profile Memory'


@traceable(
    run_type="tool",
    name="LTM_Read",
    tags=["tool:memory", "operation:read"]
)
def read_long_term_memory(patient_id: str, memory_type: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch non-expired memory rows grouped by memory_type.
    Returns {memory_type: [rows...]}.
    """
    supabase = get_supabase_client()
    query = supabase.table(TABLE_NAME).select("*").eq("patient_id", patient_id)
    if memory_type:
        query = query.eq("memory_type", memory_type)
    resp = query.execute()
    rows = resp.data or []

    now = datetime.now(timezone.utc)
    filtered = [r for r in rows if not r.get("expires_at") or datetime.fromisoformat(r["expires_at"]).replace(tzinfo=timezone.utc) > now]

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for r in filtered:
        grouped.setdefault(r.get("memory_type", "unknown"), []).append(r)
    return grouped

def ensure_patient_exists(patient_id: str) -> None:
    """
    Ensure patient record exists in Patient Data table.
    Creates minimal record if missing to satisfy foreign key constraint.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    supabase = get_supabase_client()
    try:
        # Check if patient exists
        resp = supabase.table("Patient Data").select("patient_id").eq("patient_id", patient_id).execute()
        if not resp.data:
            logger.info(f"Creating new patient record for {patient_id}")
            # Create minimal patient record - just patient_id, let DB set defaults
            supabase.table("Patient Data").insert({
                "patient_id": patient_id
            }).execute()
            logger.info(f"Successfully created patient record for {patient_id}")
    except Exception as e:
        # Log the error so we can debug
        logger.warning(f"Failed to create patient record for {patient_id}: {e}")
        # Don't re-raise - let the upsert show the actual constraint error if this fails


@traceable(
    run_type="tool",
    name="LTM_Upsert",
    tags=["tool:memory", "operation:upsert"]
)
def upsert_long_term_memory(
    patient_id: str,
    memory_type: str,
    memory_key: str,
    memory_value: Any,
    source_agent: str,
    confidence: float = 1.0,
    expires_at: Optional[str] = None,
) -> None:
    """
    UPSERT memory by (patient_id, memory_type, memory_key).
    Updates confidence/updated_at on conflict.
    memory_value must remain structured (JSONB) and NOT cast to string.
    """
    # Ensure patient exists in Patient Data table first (satisfies foreign key constraint)
    ensure_patient_exists(patient_id)
    
    supabase = get_supabase_client()
    payload = {
        "patient_id": patient_id,
        "memory_type": memory_type,
        "memory_key": memory_key,
        "memory_value": memory_value,
        "source_agent": source_agent,
        "confidence": confidence,
    }
    if expires_at:
        payload["expires_at"] = expires_at

    try:
        supabase.table(TABLE_NAME).upsert(payload, on_conflict="patient_id,memory_type,memory_key").execute()
    except Exception as e:
        # Gracefully handle foreign key constraint errors for non-registered patients
        import logging
        logger = logging.getLogger(__name__)
        if "23503" in str(e) or "foreign key" in str(e).lower():
            logger.info(f"LTM skipped: patient {patient_id} not registered in Patient Data")
        else:
            logger.warning(f"LTM upsert failed: {e}")
        # Don't re-raise - continue without LTM for unregistered users


@traceable(
    run_type="tool",
    name="LTM_Hydrate",
    tags=["tool:memory", "operation:hydrate"]
)
def hydrate_state_from_long_term_memory(state: Dict[str, Any], patient_id: str) -> Dict[str, Any]:
    """
    Populate missing fields from long-term memory without overwriting short-term values.
    preference  -> state['care']['preferences']
    constraint  -> state['insurance']['constraints']
    context     -> state['clinical']['context']
    """
    ltm = read_long_term_memory(patient_id)
    care = state.get("care", {})
    insurance = state.get("insurance", {})
    clinical = state.get("clinical", {})

    if "preference" in ltm:
        prefs = care.get("preferences", {})
        for row in ltm["preference"]:
            key, val = row.get("memory_key"), row.get("memory_value")
            if key and key not in prefs:
                prefs[key] = val
        care["preferences"] = prefs

    if "constraint" in ltm:
        constraints = insurance.get("constraints", {})
        for row in ltm["constraint"]:
            key, val = row.get("memory_key"), row.get("memory_value")
            if key and key not in constraints:
                constraints[key] = val
        insurance["constraints"] = constraints

    if "context" in ltm:
        ctx = clinical.get("context", {})
        for row in ltm["context"]:
            key, val = row.get("memory_key"), row.get("memory_value")
            if key:
                # Special case: insurance_age should go to insurance state
                if key == "insurance_age" and "age" not in insurance:
                    insurance["age"] = val
                elif key not in ctx:
                    ctx[key] = val
        clinical["context"] = ctx

    state["care"] = care
    state["insurance"] = insurance
    state["clinical"] = clinical
    return state

"""
Chat persistence module for saving messages to database.
Handles encounter creation and message storage in Supabase.
"""

from typing import Dict, Any, List, Optional
import logging

from app.tools.supabase_tool import get_supabase_client

logger = logging.getLogger(__name__)


def ensure_encounter_exists(
    encounter_id: str,
    patient_id: str,
    chief_complaint: Optional[str] = None
) -> bool:
    """
    Ensure encounter exists in database. Creates if missing.
    
    Args:
        encounter_id: UUID of encounter
        patient_id: UUID of patient
        chief_complaint: Optional initial complaint
    
    Returns:
        True if encounter exists/created, False on error
    """
    try:
        sb = get_supabase_client()
        
        # Check if encounter exists
        check = sb.table("Patient Encounters").select("id").eq("id", encounter_id).execute()
        
        if check.data:
            return True  # Already exists
        
        # Create new encounter
        payload = {
            "id": encounter_id,
            "patient_id": patient_id,
            "encounter_type": "chat",
            "chief_complaint": chief_complaint or "Chat session",
            "status": "active",
        }
        
        sb.table("Patient Encounters").insert(payload).execute()
        logger.info(f"Created encounter {encounter_id} for patient {patient_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to ensure encounter exists: {e}")
        return False


def save_message(
    encounter_id: str,
    role: str,  # 'user' or 'assistant'
    content: str,
    agent_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Save a single message to Encounter Messages table.
    
    Args:
        encounter_id: UUID of encounter
        role: 'user' or 'assistant'
        content: Message text
        agent_name: Name of agent that generated response (for assistant messages)
        metadata: Optional metadata dict
    
    Returns:
        True if saved, False on error
    """
    try:
        sb = get_supabase_client()
        
        payload = {
            "encounter_id": encounter_id,
            "role": role,
            "content": content,
            "agent_name": agent_name,
            "metadata": metadata or {}
        }
        
        sb.table("Encounter Messages").insert(payload).execute()
        logger.debug(f"Saved {role} message to encounter {encounter_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save message: {e}")
        return False


def update_encounter_summary(
    encounter_id: str,
    urgency_level: Optional[str] = None,
    visit_summary: Optional[str] = None,
    status: str = "active"
) -> bool:
    """
    Update encounter with triage results or summary.
    
    Args:
        encounter_id: UUID of encounter
        urgency_level: Triage urgency level
        visit_summary: Text summary of visit
        status: Encounter status
    
    Returns:
        True if updated, False on error
    """
    try:
        sb = get_supabase_client()
        
        update_data = {"status": status}
        if urgency_level:
            update_data["urgency_level"] = urgency_level
        if visit_summary:
            update_data["visit_summary"] = visit_summary
        
        sb.table("Patient Encounters").update(update_data).eq("id", encounter_id).execute()
        logger.debug(f"Updated encounter {encounter_id} summary")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update encounter: {e}")
        return False


def load_encounter_messages(encounter_id: str) -> List[Dict[str, Any]]:
    """
    Load all messages for an encounter from database.
    
    Args:
        encounter_id: UUID of encounter
    
    Returns:
        List of message dicts with role, content, agent_name, created_at
    """
    try:
        sb = get_supabase_client()
        
        result = sb.table("Encounter Messages")\
            .select("role, content, agent_name, created_at, metadata")\
            .eq("encounter_id", encounter_id)\
            .order("created_at")\
            .execute()
        
        return result.data or []
        
    except Exception as e:
        logger.error(f"Failed to load encounter messages: {e}")
        return []

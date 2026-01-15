"""
Encounter-scoped memory functions for conversation-specific context.
Separate from global Patient Profile Memory (LTM) to prevent cross-contamination between chats.
"""

from typing import Dict, Any, Optional, List
import logging

from app.tools.supabase_tool import get_supabase_client

logger = logging.getLogger(__name__)


def read_encounter_memory(encounter_id: str, memory_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Read encounter-specific memory (conversation context for THIS chat only).
    
    Args:
        encounter_id: UUID of the encounter
        memory_key: Optional specific key to retrieve. If None, returns all memories.
    
    Returns:
        Dict of memory_key -> memory_value
    """
    try:
        sb = get_supabase_client()
        
        query = sb.table("Encounter Memory")\
            .select("memory_key, memory_value, memory_type")\
            .eq("encounter_id", encounter_id)
        
        if memory_key:
            query = query.eq("memory_key", memory_key)
        
        result = query.execute()
        
        if not result.data:
            return {}
        
        # Convert to dict
        memories = {}
        for row in result.data:
            memories[row["memory_key"]] = row["memory_value"]
        
        logger.info(f"Loaded {len(memories)} encounter memories for {encounter_id}")
        return memories
        
    except Exception as e:
        logger.error(f"Failed to read encounter memory: {e}")
        return {}


def upsert_encounter_memory(
    encounter_id: str,
    patient_id: str,
    memory_type: str,
    memory_key: str,
    memory_value: Any
) -> bool:
    """
    Store encounter-specific memory (THIS chat only).
    
    Args:
        encounter_id: UUID of the encounter
        patient_id: UUID of the patient
        memory_type: Type of memory ('context', 'topic', 'intent')
        memory_key: Key for the memory
        memory_value: Value to store (will be converted to JSON)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        sb = get_supabase_client()
        
        payload = {
            "encounter_id": encounter_id,
            "patient_id": patient_id,
            "memory_type": memory_type,
            "memory_key": memory_key,
            "memory_value": memory_value
        }
        
        # Upsert (insert or update if exists)
        sb.table("Encounter Memory")\
            .upsert(payload, on_conflict="encounter_id,memory_key")\
            .execute()
        
        logger.info(f"Stored encounter memory: {memory_key} for encounter {encounter_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to upsert encounter memory: {e}")
        return False


def delete_encounter_memory(encounter_id: str, memory_key: Optional[str] = None) -> bool:
    """
    Delete encounter memory. If memory_key is None, deletes all memories for the encounter.
    
    Args:
        encounter_id: UUID of the encounter
        memory_key: Optional specific key to delete
    
    Returns:
        True if successful, False otherwise
    """
    try:
        sb = get_supabase_client()
        
        query = sb.table("Encounter Memory").delete().eq("encounter_id", encounter_id)
        
        if memory_key:
            query = query.eq("memory_key", memory_key)
        
        query.execute()
        
        logger.info(f"Deleted encounter memory for {encounter_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete encounter memory: {e}")
        return False


def get_encounter_topics(encounter_id: str) -> List[str]:
    """
    Get list of topics discussed in this encounter.
    
    Args:
        encounter_id: UUID of the encounter
    
    Returns:
        List of topic strings
    """
    memories = read_encounter_memory(encounter_id, "recent_topics")
    return memories.get("recent_topics", [])


def add_encounter_topic(encounter_id: str, patient_id: str, topic: str, max_topics: int = 5) -> bool:
    """
    Add a topic to the encounter's topic list.
    
    Args:
        encounter_id: UUID of the encounter
        patient_id: UUID of the patient
        topic: Topic to add
        max_topics: Maximum number of topics to keep (default 5)
    
    Returns:
        True if successful
    """
    current_topics = get_encounter_topics(encounter_id)
    
    # Add new topic, avoiding duplicates
    if topic not in current_topics:
        current_topics.append(topic)
    
    # Keep only the last N topics
    current_topics = current_topics[-max_topics:]
    
    return upsert_encounter_memory(
        encounter_id=encounter_id,
        patient_id=patient_id,
        memory_type="topic",
        memory_key="recent_topics",
        memory_value=current_topics
    )

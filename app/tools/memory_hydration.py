"""
Unified memory hydration for both Patient Profile Memory and Encounter Memory.
This should be called at the start of agent execution to load all relevant context.
"""

from typing import Dict, Any
import logging

from app.tools.memory import read_long_term_memory
from app.tools.encounter_memory import read_encounter_memory

logger = logging.getLogger(__name__)


def hydrate_all_memories(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Hydrate state with both Patient Profile Memory (LTM) and Encounter Memory.
    
    This is the centralized memory loader that should be called before agent execution.
    
    Args:
        state: Current state dict
    
    Returns:
        Updated state with both memory systems loaded
    
    Memory Structure in State:
        state["ltm"] = {
            "chronic_conditions": [...],
            "budget_max": 500,
            ...
        }
        state["encounter_memory"] = {
            "recent_topics": [...],
            "chief_complaint": "...",
            ...
        }
    """
    patient_id = state.get("patient_id")
    encounter_id = state.get("conversation_id")  # conversation_id is the encounter_id
    
    # 1. Load Patient Profile Memory (Global LTM)
    if patient_id:
        try:
            ltm_data = read_long_term_memory(patient_id)
            state["ltm"] = ltm_data
            logger.info(f"Loaded {len(ltm_data)} items from Patient Profile Memory for patient {patient_id}")
        except Exception as e:
            logger.error(f"Failed to load Patient Profile Memory: {e}")
            state["ltm"] = {}
    else:
        state["ltm"] = {}
    
    # 2. Load Encounter Memory (Conversation-scoped)
    # CRITICAL FIX: conversation_id has "session-" prefix but DB expects raw UUID
    raw_encounter_id = state.get("conversation_id", "")
    encounter_id = raw_encounter_id.replace("session-", "") if raw_encounter_id else None
    
    if encounter_id:
        try:
            encounter_data = read_encounter_memory(encounter_id)
            state["encounter_memory"] = encounter_data
            logger.info(f"Loaded {len(encounter_data)} items from Encounter Memory for encounter {encounter_id}")
        except Exception as e:
            logger.error(f"Failed to load Encounter Memory: {e}")
            state["encounter_memory"] = {}
    else:
        state["encounter_memory"] = {}
    
    return state


def get_ltm_value(state: Dict[str, Any], key: str, default: Any = None) -> Any:
    """
    Helper to safely get a value from Patient Profile Memory.
    
    Args:
        state: Current state
        key: Memory key to retrieve
        default: Default value if not found
    
    Returns:
        Value from LTM or default
    """
    ltm = state.get("ltm", {})
    return ltm.get(key, default)


def get_encounter_value(state: Dict[str, Any], key: str, default: Any = None) -> Any:
    """
    Helper to safely get a value from Encounter Memory.
    
    Args:
        state: Current state
        key: Memory key to retrieve
        default: Default value if not found
    
    Returns:
        Value from Encounter Memory or default
    """
    encounter_memory = state.get("encounter_memory", {})
    return encounter_memory.get(key, default)

import copy
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.graph import END, StateGraph

from app.core.config import Settings, get_settings
from app.workflows.medical_qa_graph import medical_qna_agent
from app.tools.memory import hydrate_state_from_long_term_memory, upsert_long_term_memory
from app.tools.memory_hydration import hydrate_all_memories
from app.agents.clinic_recommendation_agent import clinic_recommendation_agent
from app.agents.insurance_recommendation_agent import insurance_recommendation_agent
from app.agents.symptom_triage_agent import symptom_triage_agent as triage_impl


class OrchestratorState(TypedDict, total=False):
    """
    Shared state for the entire orchestration.
    - conversation_id: unique trace id for this run.
    - user_input: raw user text that kicked off planning.
    - patient_id: canonical patient identifier (required for LTM).
    - planner_output: IMMUTABLE planner JSON (intent, agent_sequence, rationales, constraints).
    - execution: runtime execution progress and status.
        - current_agent: agent being executed (None if idle/done/waiting).
        - completed_agents: ordered list of agents already run.
        - status: "idle" | "running" | "waiting_for_user" | "completed" | "error".
        - active_intent: last planned intent label.
        - pending_agent: agent awaiting follow-up (set when paused).
        - awaiting_followup: True when waiting for user's follow-up answer.
    - clinical: placeholder for clinical agent outputs.
    - care: placeholder for care navigation outputs.
    - insurance: placeholder for insurance-related outputs.
    - medical_qna: placeholder for MedicalQnAAgent outputs.
    - errors: list of error messages encountered during routing/execution.
    """

    conversation_id: str
    user_input: str
    patient_id: str
    planner_output: Dict[str, Any]
    execution: Dict[str, Any]
    clinical: Dict[str, Any]
    care: Dict[str, Any]
    insurance: Dict[str, Any]
    medical_qna: Dict[str, Any]
    errors: List[str]


ALLOWED_AGENTS = [
    "SymptomTriageAgent",
    "ClinicRecommendationAgent",
    "InsuranceAdvisorAgent",
    "MedicalQnAAgent",
]


ALLOWED_AGENTS = [
    "SymptomTriageAgent",
    "ClinicRecommendationAgent",
    "InsuranceAdvisorAgent",
    "MedicalQnAAgent",
]





def initialize_execution_state(state: OrchestratorState) -> OrchestratorState:
    """
    Initialize execution scaffolding defensively and treat planner_output as immutable.
    """
    execution = copy.deepcopy(state.get("execution") or {})
    execution.setdefault("current_agent", None)
    execution.setdefault("completed_agents", [])
    execution.setdefault("status", "idle")
    execution.setdefault("active_intent", state.get("planner_output", {}).get("intent"))
    execution.setdefault("pending_agent", None)
    execution.setdefault("awaiting_followup", False)
    planner_output = copy.deepcopy(state.get("planner_output") or {})
    return {
        **state,
        "execution": execution,
        "planner_output": planner_output,
        "errors": list(state.get("errors", [])),
    }


def hydrate_memories(state: OrchestratorState) -> OrchestratorState:
    """
    Centralized memory hydration: Load both Patient Profile Memory and Encounter Memory.
    This runs ONCE at the start of orchestration before any agents execute.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        state = hydrate_all_memories(state)
        logger.info("Successfully hydrated both Patient Profile Memory and Encounter Memory")
    except Exception as e:
        logger.error(f"Failed to hydrate memories: {e}")
        # Continue execution even if hydration fails
    
    return state


# Constraint handlers registry for extensibility
def _constraint_requires_triage_first(state: OrchestratorState, next_agent: str) -> Optional[str]:
    constraints = (state.get("planner_output") or {}).get("constraints") or {}
    requires_triage_first = constraints.get("requires_triage_first", False)
    completed = state.get("execution", {}).get("completed_agents", [])
    if (
        requires_triage_first
        and next_agent in {"ClinicRecommendationAgent", "InsuranceAdvisorAgent"}
        and "SymptomTriageAgent" not in completed
    ):
        return (
            "Constraint violation: SymptomTriageAgent must run before "
            f"{next_agent} when triage is required."
        )
    return None


CONSTRAINT_HANDLERS = {
    "requires_triage_first": _constraint_requires_triage_first,
}


def enforce_constraints(state: OrchestratorState, next_agent: str) -> Optional[str]:
    """
    Iterate constraint handlers dynamically to keep enforcement extensible.
    """
    constraints = (state.get("planner_output") or {}).get("constraints") or {}
    for name, handler in CONSTRAINT_HANDLERS.items():
        if constraints.get(name):
            error = handler(state, next_agent)
            if error:
                return error
    return None


def select_next_agent(state: OrchestratorState) -> Optional[str]:
    """
    Determine the next agent based on planner_output.agent_sequence and completed_agents.
    Handles empty/invalid sequences defensively.
    """
    planner_output = state.get("planner_output") or {}
    agent_sequence: List[str] = planner_output.get("agent_sequence") or []
    # Filter to allowed agents to avoid invalid routing.
    agent_sequence = [a for a in agent_sequence if a in ALLOWED_AGENTS]
    completed = state.get("execution", {}).get("completed_agents", [])

    for agent in agent_sequence:
        if agent not in completed:
            return agent
    return None


def mark_execution_status(
    state: OrchestratorState,
    *,
    current_agent: Optional[str],
    status: str,
    error: Optional[str] = None,
) -> OrchestratorState:
    """
    Central place to update execution status to avoid drift and prepare for future states.
    """
    execution = state.get("execution", {})
    execution["current_agent"] = current_agent
    execution["status"] = status
    errors = list(state.get("errors", []))
    if error:
        errors.append(error)
    return {**state, "execution": execution, "errors": errors}


def dispatcher(state: OrchestratorState) -> OrchestratorState:
    """
    Dynamic router with RESUME support:
    1. EARLY EXIT: If status is already waiting_for_user, pass through (let route() end).
    2. RESUME PATH: If awaiting_followup=True and pending_agent is set,
       route directly to that agent (do NOT select_next_agent).
    3. NORMAL PATH: Select next agent from planner_output.agent_sequence.
    
    NOTE: Constraint enforcement is DISABLED to strictly follow planner output.
    """
    state = initialize_execution_state(state)
    execution = state.get("execution", {})

    # --- EARLY EXIT: Already waiting for user, don't re-process ---
    if execution.get("status") == "waiting_for_user":
        return state

    # --- RESUME PATH: Agent paused for follow-up, user has answered ---
    if execution.get("awaiting_followup") and execution.get("pending_agent"):
        resume_agent = execution["pending_agent"]
        # Clear the waiting state; agent will run again with new user_input
        execution["awaiting_followup"] = False
        execution["current_agent"] = resume_agent
        execution["status"] = "running"
        state["execution"] = execution
        return state

    # --- NORMAL PATH: Select next agent from immutable agent_sequence ---
    next_agent = select_next_agent(state)
    if not next_agent:
        # All agents done or empty plan
        return mark_execution_status(state, current_agent=None, status="completed")

    # DISABLED: Constraint enforcement to strictly follow planner
    # constraint_error = enforce_constraints(state, next_agent)
    # if constraint_error:
    #     return mark_execution_status(
    #         state,
    #         current_agent=None,
    #         status="error",
    #         error=constraint_error,
    #     )

    # Safe to proceed; mark running
    return mark_execution_status(state, current_agent=next_agent, status="running")


def symptom_triage_agent(state: OrchestratorState) -> OrchestratorState:
    """
    Symptom Triage Agent wrapper with PAUSE/RESUME support.
    - Hydrates LTM, runs triage, handles follow-up pausing.
    """
    patient_id = state.get("patient_id")
    if patient_id:
        state = hydrate_state_from_long_term_memory(state, patient_id)

    state = triage_impl(state)
    execution = state.get("execution", {})

    # --- PAUSE: Agent requested follow-up (set by triage_impl) ---
    if execution.get("awaiting_followup"):
        # Do NOT mark as completed; set pending_agent and waiting status
        execution["pending_agent"] = "SymptomTriageAgent"
        execution["status"] = "waiting_for_user"
        execution["current_agent"] = None
        state["execution"] = execution
        return state

    # --- COMPLETION: No follow-up needed, mark as done ---
    execution["awaiting_followup"] = False
    execution["pending_agent"] = None
    completed = execution.get("completed_agents", [])
    if "SymptomTriageAgent" not in completed:
        execution["completed_agents"] = completed + ["SymptomTriageAgent"]
    execution["current_agent"] = None
    state["execution"] = execution
    return state


def clinic_recommendation_agent(state: OrchestratorState) -> OrchestratorState:
    """
    Clinic Recommendation Agent wrapper with PAUSE/RESUME support.
    """
    from app.agents.clinic_recommendation_agent import clinic_recommendation_agent as impl

    state = impl(state)
    execution = state.get("execution", {})

    # --- PAUSE: Agent requested clarification (e.g., specialty/location) ---
    care = state.get("care", {})
    if care.get("needs_clarification") or execution.get("awaiting_followup"):
        execution["awaiting_followup"] = True
        execution["pending_agent"] = "ClinicRecommendationAgent"
        execution["status"] = "waiting_for_user"
        execution["current_agent"] = None
        state["execution"] = execution
        return state

    # --- COMPLETION ---
    execution["awaiting_followup"] = False
    execution["pending_agent"] = None
    completed = execution.get("completed_agents", [])
    if "ClinicRecommendationAgent" not in completed:
        execution["completed_agents"] = completed + ["ClinicRecommendationAgent"]
    execution["current_agent"] = None
    state["execution"] = execution
    return state


def insurance_advisor_agent(state: OrchestratorState) -> OrchestratorState:
    """
    Insurance Advisor Agent wrapper with PAUSE/RESUME support.
    """
    patient_id = state.get("patient_id")
    if patient_id:
        state = hydrate_state_from_long_term_memory(state, patient_id)

    state = insurance_recommendation_agent(state)
    execution = state.get("execution", {})

    # --- PAUSE: Agent requested clarification (e.g., coverage criteria) ---
    ins = state.get("insurance", {})
    if ins.get("needs_clarification") or execution.get("awaiting_followup"):
        execution["awaiting_followup"] = True
        execution["pending_agent"] = "InsuranceAdvisorAgent"
        execution["status"] = "waiting_for_user"
        execution["current_agent"] = None
        state["execution"] = execution
        return state

    # --- COMPLETION ---
    execution["awaiting_followup"] = False
    execution["pending_agent"] = None
    completed = execution.get("completed_agents", [])
    if "InsuranceAdvisorAgent" not in completed:
        execution["completed_agents"] = completed + ["InsuranceAdvisorAgent"]
    execution["current_agent"] = None
    state["execution"] = execution
    return state


def medical_qna_agent_wrapper(state: OrchestratorState) -> OrchestratorState:
    """
    Wrapper to run MedicalQnAAgent and mark completion idempotently.
    """
    patient_id = state.get("patient_id")
    if patient_id:
        state = hydrate_state_from_long_term_memory(state, patient_id)

    state = medical_qna_agent(state)
    execution = state.get("execution", {})
    completed = execution.get("completed_agents", [])
    if "MedicalQnAAgent" not in completed:
        execution["completed_agents"] = completed + ["MedicalQnAAgent"]
    execution["current_agent"] = None

    # Persist only non-diagnostic, semantic context labels if confirmed.
    mq = state.get("medical_qna", {})
    confidence = mq.get("confidence", "low")
    context_label = mq.get("context_label")
    confirmed = mq.get("confirmed_context", False)
    if patient_id and confirmed and context_label and confidence in {"medium", "high"}:
        upsert_long_term_memory(
            patient_id=patient_id,
            memory_type="context",
            memory_key="qna_topic",
            memory_value=context_label,  # Just the keywords, no extra wrapper
            source_agent="MedicalQnAAgent",
            confidence=1.0 if confidence == "high" else 0.7,
        )

    return {**state, "execution": execution}


def build_orchestrator(settings: Optional[Settings] = None):
    """
    Build the LangGraph StateGraph for dynamic agent execution.
    - Dispatcher reads planner_output.agent_sequence and routes dynamically.
    - Agents are stubs; they return partial state only.
    - Constraints enforced in dispatcher (triage-before-clinic/insurance).
    """
    settings = settings or get_settings()
    graph = StateGraph(OrchestratorState)

    # 1. Initialize execution state
    graph.add_node("initialize", initialize_execution_state)
    
    # 2. Hydrate all memories (Patient Profile + Encounter)
    graph.add_node("hydrate_memories", hydrate_memories)
    
    # 3. Dispatcher picks next agent
    graph.add_node("dispatch", dispatcher)
    graph.add_node("SymptomTriageAgent", symptom_triage_agent)
    graph.add_node("ClinicRecommendationAgent", clinic_recommendation_agent)
    graph.add_node("InsuranceAdvisorAgent", insurance_advisor_agent)
    graph.add_node("MedicalQnAAgent", medical_qna_agent_wrapper)

    # Entry: initialize -> hydrate_memories -> dispatch
    graph.set_entry_point("initialize")
    graph.add_edge("initialize", "hydrate_memories")
    graph.add_edge("hydrate_memories", "dispatch")

    # Router: decide next node based on current_agent / status
    def route(state: OrchestratorState) -> str:
        exec_state = state.get("execution", {})
        status = exec_state.get("status")
        current = exec_state.get("current_agent")
        
        # END conditions: waiting_for_user, completed, error
        if status in ("waiting_for_user", "completed", "error"):
            return "END"
        
        if current is None:
            # No current agent but not terminal -> re-dispatch to find next
            return "dispatch"
        
        return current

    graph.add_conditional_edges(
        "dispatch",
        route,
        {
            "SymptomTriageAgent": "SymptomTriageAgent",
            "ClinicRecommendationAgent": "ClinicRecommendationAgent",
            "InsuranceAdvisorAgent": "InsuranceAdvisorAgent",
            "MedicalQnAAgent": "MedicalQnAAgent",
            "dispatch": "dispatch",
            "END": END,
        },
    )

    # After each agent, go back to dispatcher to pick next
    graph.add_edge("SymptomTriageAgent", "dispatch")
    graph.add_edge("ClinicRecommendationAgent", "dispatch")
    graph.add_edge("InsuranceAdvisorAgent", "dispatch")
    graph.add_edge("MedicalQnAAgent", "dispatch")

    return graph.compile()


def example_state() -> OrchestratorState:
    """
    Example initial state for testing the orchestrator without real agents.
    """
    return {
        "conversation_id": "demo-123",
        "user_input": "I have chest tightness and need to know where to go and if insurance covers it.",
        "planner_output": {
            "intent": "symptoms",
            "agent_sequence": [
                "SymptomTriageAgent",
                "ClinicRecommendationAgent",
                "InsuranceAdvisorAgent",
            ],
            "rationales": {
                "SymptomTriageAgent": "Symptoms present",
                "ClinicRecommendationAgent": "May need care navigation",
                "InsuranceAdvisorAgent": "Asked about coverage",
            },
            "constraints": {"requires_triage_first": True},
        },
        "execution": {
            "current_agent": None,
            "completed_agents": [],
            "status": "idle",
        },
        "clinical": {},
        "care": {},
        "insurance": {},
        "errors": [],
    }

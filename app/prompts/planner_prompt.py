import json
from typing import List, Optional, Dict

from langchain_core.messages import HumanMessage, SystemMessage


def build_planner_messages(
    user_request: str, available_agents: List[str], conversation_context: Optional[Dict[str, object]] = None
) -> List[object]:
    """
    Return the messages for the planner agent (strict JSON plan, no medical reasoning).
    """
    intents = ["medical_qna", "symptoms", "care_navigation", "insurance", "unknown"]
    instructions = (
        "You are a planner that routes work to specialist agents. "
        "Available agents: " + ", ".join(available_agents) + ". "
        "Your job: decide intent and a linear agent sequence. "
        "Rules: "
        "- Do NOT perform medical advice, triage, or detect emergencies. "
        "- Do NOT include task instructions or outcomes. "
        "- Use only allowed agent names; omit unnecessary agents. "
        "- SymptomTriageAgent is for users REPORTING symptoms they are experiencing (e.g., 'I have chest pain', 'I feel dizzy'). "
        "- MedicalQnAAgent is for users asking EDUCATIONAL questions about medical topics (e.g., 'What causes diabetes?', 'How does aspirin work?'). "
        "- CRITICAL: If user is reporting symptoms, use ONLY SymptomTriageAgent. Do NOT add MedicalQnAAgent unless they explicitly ask for educational information. "
        "- If user just asks for 'clinic recommendation' or 'where to go' WITHOUT symptoms in THIS message, use ClinicRecommendationAgent directly - do NOT add SymptomTriageAgent. "
        "- Re-triage logic: If SymptomTriageAgent is in completed_agents, you can STILL add it again IF the user mentions NEW or ADDITIONAL symptoms not previously discussed (e.g., 'now I also have chest pain', 'my condition worsened'). But if user is just asking follow-up questions about existing symptoms, do NOT re-triage. "
        "- Only include ClinicRecommendationAgent if the user explicitly asks for clinic/facility/doctor/hospital recommendations or 'where to go'. "
        "- Only include InsuranceAdvisorAgent if the user explicitly asks about insurance plans or coverage. "
        "- If awaiting_followup is true, continue with pending_agent unless the user clearly changes topic. "
        "- IMPORTANT for requires_triage_first constraint: "
        "  * Set TRUE ONLY if user is EXPERIENCING symptoms AND needs Clinic/Insurance after triage (e.g., 'I have cough, recommend clinic'). "
        "  * Set FALSE if user wants educational info first then triage (e.g., 'What are flu symptoms? Then triage me') - in this case MedicalQnA runs first. "
        "  * Set FALSE if no triage is needed at all. "
        "  * The agent_sequence order determines execution order. requires_triage_first=TRUE only blocks Clinic/Insurance until triage completes. "
        "Respond with JSON ONLY, no prose, in this schema:\n"
        "{\n"
        f'  "intent": "<intent_label from {intents}>",\n'
        '  "agent_sequence": ["<AgentName>", "..."],\n'
        '  "rationales": {"<AgentName>": "<short reason (max 1 sentence)>"} ,\n'
        '  "constraints": {"requires_triage_first": true | false}\n'
        "}\n"
        "Ensure the JSON is valid and machine-readable."
    )
    ctx_text = ""
    if conversation_context:
        ctx_text = "\nPlanner context (do not infer medical details): " + json.dumps(conversation_context)
    return [
        SystemMessage(content=instructions),
        HumanMessage(content=f"User intention: {user_request}{ctx_text}"),
    ]

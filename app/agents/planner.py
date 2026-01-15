import json
from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.core.config import Settings, get_settings
from app.prompts.planner_prompt import build_planner_messages

# Canonical agent names this planner can orchestrate.
ALLOWED_AGENTS = [
    "MedicalQnAAgent",
    "SymptomTriageAgent",
    "ClinicRecommendationAgent",
    "InsuranceAdvisorAgent",
]


def _build_llm(settings: Settings) -> BaseChatModel:
    """Instantiate the chat model based on configured provider."""
    provider = settings.llm_provider.lower()
    if provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            temperature=0.2,
            google_api_key=settings.gemini_api_key,
        )
    return ChatOpenAI(model=settings.openai_model, temperature=0.2, api_key=settings.openai_api_key)


def _contains_symptom_language(text: str) -> bool:
    symptoms = [
        "pain",
        "ache",
        "fever",
        "cough",
        "shortness of breath",
        "breathless",
        "nausea",
        "vomit",
        "rash",
        "dizzy",
        "bleeding",
    ]
    lower = text.lower()
    return any(term in lower for term in symptoms)


def _enforce_constraints(
    data: Dict[str, Any],
    user_request: str,
    conversation_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    # Start with planner-provided sequence
    seq = data.get("agent_sequence") or []
    if isinstance(seq, str):
        seq = [seq]

    # Filter to allowed agents and dedupe
    filtered = []
    seen = set()
    
    for a in seq:
        if a in ALLOWED_AGENTS and a not in seen:
            filtered.append(a)
            seen.add(a)

    # Minimal safety: if symptoms detected and SymptomTriageAgent not present, prepend it.
    # But only if LLM didn't explicitly set requires_triage_first to false
    llm_constraints = data.get("constraints") or {}
    llm_requires_triage = llm_constraints.get("requires_triage_first")
    
    # Use LLM decision if provided, otherwise fallback to keyword detection
    if llm_requires_triage is not None:
        requires_triage = llm_requires_triage
    else:
        requires_triage = _contains_symptom_language(user_request)
    
    # Only auto-add triage if LLM says triage is required AND it's not in sequence
    if requires_triage and "SymptomTriageAgent" not in filtered:
        filtered.insert(0, "SymptomTriageAgent")

    constraints = llm_constraints
    constraints["requires_triage_first"] = requires_triage

    rationales = data.get("rationales") or {}
    rationales = {a: rationales.get(a, "") for a in filtered}

    intent = data.get("intent", "unknown")
    # If LLM intent is missing, fall back to prior active intent when provided.
    ctx = conversation_context or {}
    active_intent = ctx.get("active_intent")
    if (not intent or intent == "unknown") and active_intent:
        intent = active_intent

    return {
        "intent": intent,
        "agent_sequence": filtered,
        "rationales": rationales,
        "constraints": constraints,
    }


def generate_plan(
    user_request: str,
    settings: Settings | None = None,
    conversation_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a structured execution plan (JSON) for agent orchestration.
    """
    settings = settings or get_settings()
    llm = _build_llm(settings)
    messages = build_planner_messages(user_request, ALLOWED_AGENTS, conversation_context)
    
    # Extract intent from context for tagging
    ctx = conversation_context or {}
    intent_tag = ctx.get("active_intent") or "initial"
    
    response = llm.invoke(
        messages,
        config={
            "run_name": "Planner",
            "tags": [
                "agent:Planner",
                "route:plan",
                "component:planner",
                f"intent:{intent_tag}"
            ],
            "metadata": {
                "agent_type": "planner",
                "allowed_agents": ALLOWED_AGENTS,
                "has_conversation_context": bool(conversation_context)
            }
        },
    )

    print(f"Raw content type: {type(response.content)}")
    print(f"Raw content value: {response.content}")

    # 1. Access the first element of the list and the 'text' field
    raw_json_string = response.content[0].get('text', '{}')

    try:
        # 2. Parse that specific string
        data = json.loads(raw_json_string)
    except (json.JSONDecodeError, TypeError, IndexError):
        data = {}

    # 3. Final safety check
    if not isinstance(data, dict):
        data = {}

    print("data", data)

    plan = _enforce_constraints(data, user_request, conversation_context)

    rationales = plan.get("rationales") or {}
    for agent in plan.get("agent_sequence", []):
        if not rationales.get(agent):
            fallback_reason = {
                "SymptomTriageAgent": "Symptoms mentioned; triage first.",
                "ClinicRecommendationAgent": "User may need care navigation.",
                "InsuranceAdvisorAgent": "User mentioned coverage/benefits.",
                "MedicalQnAAgent": "User asked a medical question.",
            }.get(agent, "Agent selected based on intent.")
            rationales[agent] = fallback_reason
    plan["rationales"] = rationales

    return plan

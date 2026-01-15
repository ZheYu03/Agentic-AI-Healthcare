"""
Status message definitions for user-facing agent progress updates.

These messages are emitted during agent execution to keep users informed.
Each message represents a visible UI step with emoji and clear action.
"""

# Agent status messages - shown to users during execution
AGENT_STATUS_MESSAGES = {
    "PlannerAgent": {
        "start": "🧭 Understanding your request and planning next steps…",
    },
    "MedicalQnAAgent": {
        "start": "📚 Retrieving reliable medical information…",
        "searching": "🔎 Searching medical knowledge database…",
        "preparing": "🧠 Preparing an easy-to-understand explanation…",
    },
    "SymptomTriageAgent": {
        "start": "🩺 Reviewing your symptoms…",
        "assessing": "⚖️ Assessing symptom severity and urgency…",
        "complete": "✅ Symptom assessment complete",
    },
    "ClinicRecommendationAgent": {
        "start": "🏥 Finding clinics near your location…",
        "filtering": "📍 Filtering clinics by distance and specialty…",
        "selecting": "⭐ Selecting the most suitable clinics for you…",
    },
    "InsuranceAdvisorAgent": {
        "start": "🛡️ Checking insurance plans that may apply…",
        "matching": "📄 Matching your visit with insurance coverage…",
        "complete": "✅ Insurance information ready",
    },
}


def get_agent_start_message(agent_name: str) -> str:
    """Get the initial status message for an agent"""
    return AGENT_STATUS_MESSAGES.get(agent_name, {}).get("start", f"⏳ Running {agent_name}…")


def get_agent_status_message(agent_name: str, step: str) -> str:
    """Get a specific status message for an agent step"""
    return AGENT_STATUS_MESSAGES.get(agent_name, {}).get(step, "")

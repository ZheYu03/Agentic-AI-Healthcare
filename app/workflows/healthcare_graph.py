from typing import TypedDict

from langgraph.graph import END, StateGraph
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.clients.vector_store import build_vector_store
from app.core.config import Settings


class AgentState(TypedDict):
    question: str
    context: str
    answer: str


def _build_llm(settings: Settings) -> BaseChatModel:
    provider = settings.llm_provider.lower()
    if provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            temperature=0.2,
            google_api_key=settings.gemini_api_key,
        )
    return ChatOpenAI(model=settings.openai_model, temperature=0.2, api_key=settings.openai_api_key)


def build_workflow(settings: Settings):
    """Create and compile the LangGraph workflow."""
    llm = _build_llm(settings)
    vector_store = build_vector_store(settings)
    retriever = vector_store.as_retriever() if vector_store else None

    def retrieve(state: AgentState) -> AgentState:
        context = ""
        if retriever:
            docs = retriever.invoke(state["question"])
            context = "\n\n".join(doc.page_content for doc in docs)
        return {**state, "context": context}

    def answer(state: AgentState) -> AgentState:
        system_prompt = (
            "You are a helpful healthcare assistant. "
            "Use the provided context from medical knowledge bases when available. "
            "Avoid offering definitive diagnoses; suggest questions a clinician would ask."
        )
        messages = [
            AIMessage(content=system_prompt),
            HumanMessage(
                content=f"Context:\n{state.get('context') or 'No retrieved context'}\n\n"
                f"Question: {state['question']}"
            ),
        ]
        result = llm.invoke(messages)
        return {**state, "answer": result.content}

    graph = StateGraph(AgentState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("answer", answer)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "answer")
    graph.add_edge("answer", END)

    return graph.compile()

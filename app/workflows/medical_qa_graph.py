import json
from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.runnables import RunnableLambda

from app.core.config import get_settings
from app.agents.planner import _build_llm  # reuse provider-aware LLM builder
from app.tools.pinecone_tool import get_pinecone_index
from app.tools.encounter_memory import get_encounter_topics, add_encounter_topic

# Retrieval configuration
TOP_K = 3
SCORE_THRESHOLD = 0.35


def _get_question(state: Dict[str, Any]) -> str:
    """Prefer refined medical_qna.question if present, else user_input."""
    mq = state.get("medical_qna") or {}
    return mq.get("question") or state.get("user_input") or ""


def _normalize_query(question: str) -> str:
    """
    Deterministic normalization to improve retrieval recall without LLMs.
    - Lowercase and strip filler prefixes (e.g., 'what is', 'can you explain')
    - Preserve medical concepts; no disease hardcoding
    - Append light intent hints for symptom/treatment language to aid embeddings
    """
    q = question.strip().lower()
    fillers = [
        "what is",
        "what are",
        "can you explain",
        "could you explain",
        "please explain",
        "tell me",
        "do you know",
        "i want to know",
    ]
    for f in fillers:
        if q.startswith(f):
            q = q[len(f) :].strip(" ,.?")
            break
    if any(term in q for term in ["symptom", "sign", "feel", "pain", "ache", "cough", "shortness of breath"]):
        q = q + " symptom information"
    elif any(term in q for term in ["treat", "therapy", "medication", "manage"]):
        q = q + " treatment information"
    return q


def _build_context_block(results: List[Dict[str, Any]]) -> str:
    """Format retrieved chunks for grounding."""
    lines = []
    for idx, item in enumerate(results, 1):
        doc_id = item.get("id") or f"doc_{idx}"
        snippet = item.get("snippet") or ""
        lines.append(f"[{idx}] id={doc_id}\n{snippet}")
    return "\n\n".join(lines)


def _confidence(best_score: float, has_context: bool) -> str:
    if not has_context:
        return "low"
    if best_score >= 0.65:
        return "high"
    if best_score >= SCORE_THRESHOLD:
        return "medium"
    return "low"


def _safe_failure(state: Dict[str, Any], question: str, message: str) -> Dict[str, Any]:
    """Return state with a low-confidence, safe refusal and logged error."""
    errors = list(state.get("errors", []))
    errors.append(message)
    state["errors"] = errors
    state["medical_qna"] = {
        "question": question,
        "normalized_query": _normalize_query(question),
        "answer": "I don’t have enough information in my knowledge base to answer safely.",
        "sources": [],
        "confidence": "low",
    }
    return state


def medical_qna_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Medical Q&A agent:
    - RAG-only answer using Pinecone retrieval
    - No triage/emergency logic
    - Writes output to state['medical_qna']
    """
    question = _get_question(state)
    settings = get_settings()

    # Build vector store using pinecone_tool (ensures index connectivity)
    try:
        index = get_pinecone_index()
    except Exception as exc:  # pragma: no cover
        return _safe_failure(state, question, f"Pinecone index init failed: {exc}")

    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=settings.gemini_api_key,
        )
        vector_store = PineconeVectorStore.from_existing_index(
            index_name=settings.pinecone_index_name,
            embedding=embeddings,
        )
    except Exception as exc:  # pragma: no cover
        return _safe_failure(state, question, f"Vector store init failed: {exc}")

    normalized_query = _normalize_query(question)
    
    # CRITICAL FIX: Use ONLY the current question for retrieval
    # Previous implementation was appending encounter topics which caused
    # subsequent queries to retrieve documents from the FIRST question
    query_for_retrieval = normalized_query
    
    # Wrap retrieval in a Runnable to surface in LangSmith traces.
    retrieval = RunnableLambda(
        lambda q: vector_store.similarity_search_with_score(q, k=TOP_K)
    ).with_config(
        run_name="PineconeRetrieval",
        tags=[
            "tool:pinecone",
            "operation:similarity_search",
            "agent:MedicalQnAAgent"
        ],
        metadata={
            "top_k": TOP_K,
            "score_threshold": SCORE_THRESHOLD,
            "normalized_query": normalized_query,
            "query_used": query_for_retrieval
        }
    )

    try:
        raw_results = retrieval.invoke(query_for_retrieval)
    except Exception as exc:  # pragma: no cover
        return _safe_failure(state, question, f"Retrieval failed: {exc}")

    results: List[Dict[str, Any]] = []
    best_score = 0.0
    for doc, score in raw_results:
        score_val = score or 0.0
        best_score = max(best_score, score_val)
        results.append(
            {
                "id": (doc.metadata or {}).get("id") or (doc.metadata or {}).get("doc_id") or "",
                "snippet": doc.page_content,
                "score": score_val,
            }
        )

    # Filter by threshold
    filtered = [r for r in results if r.get("score", 0.0) >= SCORE_THRESHOLD]
    has_context = bool(filtered)
    if not has_context:
        state["medical_qna"] = {
            "question": question,
            "normalized_query": normalized_query,
            "answer": "I don’t have enough retrieved information to answer safely. Please consult a clinician or provide more detail.",
            "sources": [],
            "confidence": "low",
        }
        return state

    # Build LLM prompt with strict grounding
    context_block = _build_context_block(filtered)
    system_prompt = (
        "You are a medical Q&A assistant. Answer using the provided context snippets. "
        "Do not use outside knowledge. Be neutral, factual, and educational."
    )
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=(
                f"Context:\n{context_block}\n\n"
                f"Question: {question}\n"
            )
        ),
    ]

    llm: BaseChatModel = _build_llm(settings)
    try:
        response = llm.invoke(
            messages,
            config={
                "run_name": "MedicalQnAGeneration",
                "tags": [
                    "agent:MedicalQnAAgent",
                    "route:qa",
                    "component:rag_generation",
                    f"retrieval_top_k:{TOP_K}"
                ],
                "metadata": {
                    "retrieved_docs_count": len(filtered),
                    "best_similarity_score": best_score,
                    "confidence": _confidence(best_score, has_context=True),
                    "has_context": has_context
                }
            },
        )
        answer_text = response.content if isinstance(response.content, str) else json.dumps(response.content)
    except Exception as exc:  # pragma: no cover
        return _safe_failure(state, question, f"LLM generation failed: {exc}")

    # Prepare sources and confidence
    sources = [{"id": r.get("id") or f"doc_{idx+1}", "snippet": r.get("snippet", "")} for idx, r in enumerate(filtered)]
    confidence = _confidence(best_score, has_context=True)
    
    # Extract keywords from the question for LTM storage (concise, not full sentence)
    # Filter out common words to keep only meaningful medical terms
    stop_words = {'what', 'when', 'where', 'which', 'about', 'does', 'cause', 'causes', 
                  'difference', 'between', 'is', 'are', 'the', 'and', 'or', 'how', 'can',
                  'why', 'tell', 'symptom', 'symptoms', 'treatment', 'information'}
    keywords = [word.lower() for word in normalized_query.split() 
                if len(word) > 3 and word.lower() not in stop_words]
    context_label = ", ".join(keywords[:3]) if keywords else None  # Top 3 keywords only

    state["medical_qna"] = {
        "question": question,
        "normalized_query": normalized_query,
        "answer": answer_text,
        "sources": sources,
        "confidence": confidence,
        # Enable LTM storage in orchestrator_graph.py (lines 338-346)
        "context_label": context_label,
        "confirmed_context": True if confidence in ["medium", "high"] else False,
    }
    
    # Store topics in encounter memory (THIS chat only, not global LTM)
    from app.tools.encounter_memory import add_encounter_topic
    
    # CRITICAL FIX: conversation_id has "session-" prefix but DB expects raw UUID
    raw_conversation_id = state.get("conversation_id", "")
    encounter_id = raw_conversation_id.replace("session-", "") if raw_conversation_id else None
    patient_id = state.get("patient_id")
    
    if encounter_id and patient_id and normalized_query and confidence in ["medium", "high"]:
        try:
            # Extract keywords from query as topics
            keywords = [word.lower() for word in normalized_query.split() 
                       if len(word) > 4 and word.lower() not in ['what', 'when', 'where', 'which', 'about']]
            
            # Add each keyword as a topic
            for keyword in keywords[:3]:  # Limit to top 3 keywords
                add_encounter_topic(encounter_id, patient_id, keyword)
            
            logger.info(f"Stored QnA topics in encounter memory: {keywords[:3]}")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to store QnA topic to encounter memory: {e}")
    
    return state

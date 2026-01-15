"""
SSE Streaming endpoint for real-time agent status updates.

This module contains the /chat/stream endpoint that emits Server-Sent Events
showing real-time progress as agents execute.
"""

import time
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional

from app.entrypoints.chat_server import (
    ChatRequest,
    SESSION_STATE,
    graph,
    _build_initial_state,
    _extract_response_messages,
    _qna_summary,
    _triage_summary,
    _clinic_summary,
    _insurance_summary,
    _build_followup_messages,
    logger,
)
from app.agents.planner import generate_plan
from app.utils.status_messages import get_agent_start_message, get_agent_status_message, AGENT_STATUS_MESSAGES
from app.utils.sse_utils import (
    emit_status,
    emit_agent_start,
    emit_agent_complete,
    emit_execution_plan,
    emit_response_ready,
    emit_done,
    emit_error,
)
from app.tools.chat_persistence import ensure_encounter_exists, save_message, update_encounter_summary


def extract_agent_summary(agent_name: str, state: Dict[str, Any]) -> str:
    """Extract human-readable summary from agent execution result.
    
    Args:
        agent_name: Name of the agent that completed
        state: Current orchestrator state
        
    Returns:
        User-friendly summary of what the agent accomplished
    """
    if agent_name == "PlannerAgent":
        planner_output = state.get("planner_output", {})
        sequence = planner_output.get("agent_sequence", [])
        return f"Determined plan: {' → '.join(sequence)}" if sequence else "Analyzed your request"
    
    elif agent_name == "SymptomTriageAgent":
        clinical = state.get("clinical", {})
        urgency = clinical.get("urgency_level", "")
        specialty = clinical.get("triage_specialty", "")
        if urgency and specialty:
            return f"Assessed urgency: {urgency}. Recommended: {specialty}"
        elif urgency:
            return f"Assessed urgency: {urgency}"
        return "Completed symptom assessment"
    
    elif agent_name == "ClinicRecommendationAgent":
        care = state.get("care", {})
        clinics = care.get("recommended_clinics", [])
        if clinics:
            return f"Found {len(clinics)} suitable clinics"
        return "Completed clinic search"
    
    elif agent_name == "InsuranceAdvisorAgent":
        insurance = state.get("insurance", {})
        plans = insurance.get("recommended_plans", [])
        if plans:
            return f"Found {len(plans)} insurance plans"
        return "Completed insurance check"
    
    elif agent_name == "MedicalQnAAgent":
        return "Retrieved medical information"
    
    return "Completed successfully"


def extract_key_findings(agent_name: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key data points from agent result.
    
    Args:
        agent_name: Name of the agent
        state: Current orchestrator state
        
    Returns:
        Dictionary of key findings
    """
    findings = {}
    
    if agent_name == "SymptomTriageAgent":
        clinical = state.get("clinical", {})
        if clinical.get("urgency_level"):
            findings["urgency"] = clinical["urgency_level"]
        if clinical.get("triage_specialty"):
            findings["specialty"] = clinical["triage_specialty"]
    
    elif agent_name == "ClinicRecommendationAgent":
        care = state.get("care", {})
        clinics = care.get("recommended_clinics", [])
        findings["clinic_count"] = len(clinics)
    
    elif agent_name == "InsuranceAdvisorAgent":
        insurance = state.get("insurance", {})
        plans = insurance.get("recommended_plans", [])
        findings["plan_count"] = len(plans)
    
    return findings


async def chat_stream_generator(body: ChatRequest) -> AsyncGenerator[str, None]:
    """Generate SSE events for chat streaming.
    
    This is the core streaming logic that emits status updates as agents execute.
    
    Args:
        body: Chat request body
        
    Yields:
        SSE formatted event strings
    """
    try:
        # Validate input
        if not body.input.strip() or not body.session_id.strip():
            yield await emit_error("Missing 'input' or 'session_id'")
            yield await emit_done()
            return
        
        # Handle encounter persistence
        encounter_id = body.encounter_id
        patient_id = body.patient_id
        
        if encounter_id and patient_id:
            is_first_message = SESSION_STATE.get(body.session_id) is None
            chief_complaint = body.input[:100] if is_first_message else None
            ensure_encounter_exists(encounter_id, patient_id, chief_complaint)
            save_message(encounter_id=encounter_id, role="user", content=body.input)
        
        prev_state = SESSION_STATE.get(body.session_id)
        
        # Determine if this is a follow-up or new request
        if prev_state:
            prev_exec = prev_state.get("execution") or {}
            
            if prev_exec.get("awaiting_followup") or prev_exec.get("status") == "waiting_for_user":
                # FOLLOW-UP PATH
                logger.info("[/chat/stream] RESUME: session=%s", body.session_id)
                state = prev_state
                state["user_input"] = body.input
                if body.patient_id:
                    state["patient_id"] = body.patient_id
                
                execution = state.get("execution", {})
                execution["status"] = "idle"
                state["execution"] = execution
                
                clinical = state.get("clinical", {}) or {}
                clinical["pending_follow_up"] = True
                if body.age is not None: clinical["age"] = body.age
                if body.sex: clinical["sex"] = body.sex
                if body.pregnancy_status: clinical["pregnancy_status"] = body.pregnancy_status
                if body.chronic_conditions: clinical["chronic_conditions"] = body.chronic_conditions
                if body.medications: clinical["medications"] = body.medications
                if body.allergies: clinical["allergies"] = body.allergies
                if body.duration: clinical["duration"] = body.duration
                if body.severity: clinical["severity"] = body.severity
                state["clinical"] = clinical
                planner_output = state.get("planner_output") or {}
            else:
                # NEW REQUEST in existing session
                logger.info("[/chat/stream] NEW REQUEST: session=%s", body.session_id)
                planner_context = {
                    "active_intent": prev_exec.get("active_intent"),
                    "pending_agent": prev_exec.get("pending_agent"),
                    "awaiting_followup": False,
                }
                planner_output = generate_plan(body.input, conversation_context=planner_context)
                state = prev_state
                state["user_input"] = body.input
                state["planner_output"] = planner_output
                if body.patient_id:
                    state["patient_id"] = body.patient_id
                
                clinical = state.get("clinical", {}) or {}
                if body.age is not None: clinical["age"] = body.age
                if body.sex: clinical["sex"] = body.sex
                if body.pregnancy_status: clinical["pregnancy_status"] = body.pregnancy_status
                if body.chronic_conditions: clinical["chronic_conditions"] = body.chronic_conditions
                if body.medications: clinical["medications"] = body.medications
                if body.allergies: clinical["allergies"] = body.allergies
                if body.duration: clinical["duration"] = body.duration
                if body.severity: clinical["severity"] = body.severity
                state["clinical"] = clinical
                
                state["medical_qna"] = {}
                state["execution"] = {
                    "current_agent": None,
                    "completed_agents": [],
                    "status": "idle",
                    "active_intent": prev_exec.get("active_intent"),
                    "pending_agent": None,
                    "awaiting_followup": False,
                }
        else:
            # BRAND NEW SESSION
            logger.info("[/chat/stream] NEW SESSION: session=%s", body.session_id)
            yield await emit_status("🧭 Understanding your request and planning next steps…")
            
            planner_output = generate_plan(body.input, conversation_context=None)
            state = _build_initial_state(body, planner_output)
        
        # Fallback for empty agent sequence
        if not planner_output.get("agent_sequence"):
            intent = planner_output.get("intent")
            exec_state = state.get("execution") or {}
            intent_fallback = intent or exec_state.get("active_intent")
            fallback_map = {
                "medical_qna": ["MedicalQnAAgent"],
                "symptoms": ["SymptomTriageAgent"],
                "care_navigation": ["ClinicRecommendationAgent"],
                "insurance": ["InsuranceAdvisorAgent"],
            }
            planner_output["agent_sequence"] = fallback_map.get(intent_fallback, [])
            state["planner_output"] = planner_output
        
        # Emit execution plan
        agent_sequence = planner_output.get("agent_sequence", [])
        if agent_sequence:
            yield await emit_execution_plan(agent_sequence, 0)
        
        # Keep active intent updated
        exec_state = state.get("execution") or {}
        if not exec_state.get("awaiting_followup"):
            exec_state["active_intent"] = planner_output.get("intent")
        state["execution"] = exec_state
        
        # Track completed agents before execution
        prev_completed = set(exec_state.get("completed_agents", []))
        
        # Execute graph with status tracking
        # We'll emit agent_start for each agent in the sequence
        for idx, agent_name in enumerate(agent_sequence):
            if agent_name not in prev_completed:
                # Emit agent start
                start_msg = get_agent_start_message(agent_name)
                yield await emit_agent_start(agent_name, start_msg)
                
                # Emit additional status messages for certain agents
                if agent_name == "MedicalQnAAgent":
                    yield await emit_status(get_agent_status_message(agent_name, "searching"))
                elif agent_name == "SymptomTriageAgent":
                    yield await emit_status(get_agent_status_message(agent_name, "assessing"))
                elif agent_name == "ClinicRecommendationAgent":
                    yield await emit_status(get_agent_status_message(agent_name, "filtering"))
                elif agent_name == "InsuranceAdvisorAgent":
                    yield await emit_status(get_agent_status_message(agent_name, "matching"))
        
        # Execute the graph
        final_state = graph.invoke(state)
        SESSION_STATE.set(body.session_id, final_state)
        
        # Emit completion events for newly completed agents
        executed_agents = (final_state.get("execution") or {}).get("completed_agents") or []
        newly_completed = set(executed_agents) - prev_completed
        
        for agent_name in agent_sequence:
            if agent_name in newly_completed:
                summary = extract_agent_summary(agent_name, final_state)
                key_findings = extract_key_findings(agent_name, final_state)
                yield await emit_agent_complete(agent_name, summary, key_findings)
        
        
        # Save assistant responses - ONLY from newly completed agents to prevent duplicates
        if encounter_id:
            messages_to_save = []
            
            # Only save MedicalQnA response if agent just completed
            if "MedicalQnAAgent" in newly_completed:
                qna_msg = _qna_summary(final_state)
                if qna_msg:
                    qna = final_state.get("medical_qna", {})
                    messages_to_save.append({
                        "content": qna_msg,
                        "agent_name": "MedicalQnAAgent",
                        "metadata": {
                            "type": "qna",
                            "confidence": qna.get("confidence"),
                            "source_count": len(qna.get("sources", []))
                        }
                    })
            
            # Only save triage result if agent just completed
            if "SymptomTriageAgent" in newly_completed:
                clinical = final_state.get("clinical", {})
                
                # Save triage summary if it exists
                triage_msg = _triage_summary(final_state)
                if triage_msg:
                    messages_to_save.append({
                        "content": triage_msg,
                        "agent_name": "SymptomTriageAgent",
                        "metadata": {
                            "type": "triage",
                            "urgency": clinical.get("urgency_level")
                        }
                    })
                
                # ALWAYS save follow-up questions if they exist (even without full triage)
                followups = clinical.get("follow_up_requests", [])
                logger.info(f"[chat_stream] Triage completed. Follow-ups in state: {len(followups)}")
                for idx, fq in enumerate(followups):
                    question = fq.get("question")
                    logger.info(f"[chat_stream] Follow-up {idx}: {question}")
                    if question:
                        messages_to_save.append({
                            "content": question,
                            "agent_name": "SymptomTriageAgent",
                            "metadata": {
                                "type": "followup",
                                "intent": fq.get("intent")
                            }
                        })
                        logger.info(f"[chat_stream] Saved follow-up question to database: {question[:50]}...")
            
            # Only save clinic results if agent just completed
            if "ClinicRecommendationAgent" in newly_completed:
                clinic_msg = _clinic_summary(final_state)
                if clinic_msg:
                    messages_to_save.append({
                        "content": clinic_msg,
                        "agent_name": "ClinicRecommendationAgent",
                        "metadata": {"type": "clinic_recommendation"}
                    })
                
                # Save clarification question if exists
                care = final_state.get("care", {})
                clarification = care.get("clarification_question")
                if clarification:
                    messages_to_save.append({
                        "content": clarification,
                        "agent_name": "ClinicRecommendationAgent",
                        "metadata": {
                            "type": "clarification",
                            "clarification_type": care.get("clarification_type")
                        }
                    })
            
            # Only save insurance results if agent just completed
            if "InsuranceAdvisorAgent" in newly_completed:
                ins_msg = _insurance_summary(final_state)
                if ins_msg:
                    messages_to_save.append({
                        "content": ins_msg,
                        "agent_name": "InsuranceAdvisorAgent",
                        "metadata": {"type": "insurance_recommendation"}
                    })
                
                # Save clarification question if exists
                ins = final_state.get("insurance", {})
                ins_clarification = ins.get("clarification_question")
                if ins_clarification:
                    messages_to_save.append({
                        "content": ins_clarification,
                        "agent_name": "InsuranceAdvisorAgent",
                        "metadata": {
                            "type": "clarification",
                            "clarification_type": ins.get("clarification_type")
                        }
                    })
            
            # Save only new messages
            for msg in messages_to_save:
                save_message(
                    encounter_id=encounter_id,
                    role="assistant",
                    content=msg["content"],
                    agent_name=msg.get("agent_name"),
                    metadata=msg.get("metadata")
                )
            
            # CRITICAL: Save follow-up questions even if triage isn't complete yet
            # Triage sets awaiting_followup=True and doesn't mark as complete when asking questions
            clinical = final_state.get("clinical", {})
            pending_follow_up = clinical.get("pending_follow_up", False)
            exec_state = final_state.get("execution", {})
            awaiting_followup = exec_state.get("awaiting_followup", False)
            
            if awaiting_followup or pending_follow_up:
                followups = clinical.get("follow_up_requests", [])
                logger.info(f"[chat_stream] Triage awaiting follow-up. Saving {len(followups)} follow-up questions")
                for idx, fq in enumerate(followups):
                    question = fq.get("question")
                    if question:
                        logger.info(f"[chat_stream] Saving follow-up {idx}: {question[:50]}...")
                        save_message(
                            encounter_id=encounter_id,
                            role="assistant",
                            content=question,
                            agent_name="SymptomTriageAgent",
                            metadata={
                                "type": "followup",
                                "intent": fq.get("intent")
                            }
                        )
            
            clinical = final_state.get("clinical", {})
            urgency_level = clinical.get("urgency_level")
            if urgency_level:
                update_encounter_summary(encounter_id=encounter_id, urgency_level=urgency_level)
        
        # Build final response messages
        clinical = final_state.get("clinical") or {}
        followups = clinical.get("follow_up_questions") or clinical.get("follow_up_requests") or []
        pending = clinical.get("pending_follow_up", False)
        
        exec_state = final_state.get("execution") or {}
        awaiting_followup = exec_state.get("awaiting_followup", False)
        
        care = final_state.get("care") or {}
        pending_care = care.get("needs_clarification", False)
        care_question = care.get("clarification_question")
        
        ins = final_state.get("insurance") or {}
        pending_ins = ins.get("needs_clarification", False)
        ins_question = ins.get("clarification_question")
        
        
        messages = []
        
        # Only show summaries for newly completed agents
        if "MedicalQnAAgent" in newly_completed:
            qna_msg = _qna_summary(final_state)
            if qna_msg: messages.append(qna_msg)
        
        if "SymptomTriageAgent" in newly_completed:
            triage_msg = _triage_summary(final_state)
            if triage_msg: messages.append(triage_msg)
        
        if "ClinicRecommendationAgent" in newly_completed:
            clinic_msg = _clinic_summary(final_state)
            if clinic_msg: messages.append(clinic_msg)
        
        if "InsuranceAdvisorAgent" in newly_completed:
            ins_msg = _insurance_summary(final_state)
            if ins_msg: messages.append(ins_msg)
        
        # Add follow-up questions
        if awaiting_followup or pending or followups or pending_care or pending_ins:
            followup_msgs = _build_followup_messages(followups)
            if pending_care and care_question:
                followup_msgs.append(care_question)
            if pending_ins and ins_question:
                followup_msgs.append(ins_question)
            messages.extend(followup_msgs)
        
        if not messages:
            messages.append("I've captured your request. If you have more details, please share them.")
        
        # Emit final response
        yield await emit_response_ready(messages)
        yield await emit_done()
        
    except Exception as e:
        logger.error(f"[/chat/stream] Error: {e}", exc_info=True)
        yield await emit_error(f"An error occurred: {str(e)}")
        yield await emit_done()

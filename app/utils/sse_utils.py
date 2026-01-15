"""Helper functions for SSE (Server-Sent Events) streaming."""

import json
import asyncio
from typing import Dict, Any


def sse_event(data: Dict[str, Any]) -> str:
    """Format data as an SSE event.
    
    Args:
        data: Dictionary to send as JSON
        
    Returns:
        Formatted SSE event string
    """
    return f"data: {json.dumps(data)}\n\n"


async def emit_status(message: str) -> str:
    """Emit a status update event.
    
    Args:
        message: Status message to display to user
        
    Returns:
        SSE formatted status event
    """
    return sse_event({"type": "status", "message": message})


async def emit_agent_start(agent_name: str, message: str) -> str:
    """Emit agent start event.
    
    Args:
        agent_name: Name of the agent starting
        message: User-friendly message describing what the agent is doing
        
    Returns:
        SSE formatted agent_start event
    """
    return sse_event({
        "type": "agent_start",
        "agent": agent_name,
        "message": message
    })


async def emit_agent_complete(agent_name: str, summary: str = "", key_findings: Dict[str, Any] = None) -> str:
    """Emit agent completion event.
    
    Args:
        agent_name: Name of the completed agent
        summary: Human-readable summary of what the agent accomplished
        key_findings: Key data extracted from agent result
        
    Returns:
        SSE formatted agent_complete event
    """
    return sse_event({
        "type": "agent_complete",
        "agent": agent_name,
        "summary": summary,
        "key_findings": key_findings or {}
    })


async def emit_execution_plan(agents: list, current_index: int = 0) -> str:
    """Emit the execution plan showing all agents to run.
    
    Args:
        agents: List of agent names in execution order
        current_index: Index of currently executing agent
        
    Returns:
        SSE formatted execution_plan event
    """
    return sse_event({
        "type": "execution_plan",
        "agents": agents,
        "current_index": current_index
    })


async def emit_response_ready(messages: list) -> str:
    """Emit final response ready event.
    
    Args:
        messages: List of response messages to display
        
    Returns:
        SSE formatted response_ready event
    """
    return sse_event({
        "type": "response_ready",
        "messages": messages
    })


async def emit_done() -> str:
    """Emit stream completion event.
    
    Returns:
        SSE formatted done event
    """
    return sse_event({"type": "done"})


async def emit_error(error_message: str) -> str:
    """Emit error event.
    
    Args:
        error_message: Error message to display
        
    Returns:
        SSE formatted error event
    """
    return sse_event({
        "type": "error",
        "message": error_message
    })

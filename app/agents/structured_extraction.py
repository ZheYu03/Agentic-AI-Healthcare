"""
Structured extraction utilities for extracting information from user messages.
Used to avoid unnecessary clarification questions.
"""

import json
import logging
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


def extract_clinic_request(user_input: str, llm) -> Dict[str, Optional[str]]:
    """
    Extract specialty and location from user's clinic request.
    
    Args:
        user_input: User's message (e.g., "Diagnostic center at bukit bintang")
        llm: LLM instance to use for extraction
    
    Returns:
        {"specialty": str | None, "location": str | None}
    """
    if not user_input or not user_input.strip():
        return {"specialty": None, "location": None}
    
    system_prompt = """You are extracting structured information from clinic requests.
Extract the clinic specialty and location if mentioned.

Examples:
- "Diagnostic center at bukit bintang" → {"specialty": "Diagnostic center", "location": "bukit bintang"}
- "I need a cardiologist near KL" → {"specialty": "Cardiologist", "location": "KL"}
- "find me a clinic in Petaling Jaya" → {"specialty": null, "location": "Petaling Jaya"}
- "I need to see a doctor" → {"specialty": null, "location": null}

Return JSON only: {"specialty": "<specialty_or_null>", "location": "<location_or_null>"}
If not mentioned, use null."""

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Extract from: {user_input}")
        ]
        
        response = llm.invoke(messages)
        
        # Handle different response formats
        if hasattr(response, 'content'):
            if isinstance(response.content, str):
                content = response.content
            elif isinstance(response.content, list):
                # If content is a list of parts, join them
                content = " ".join(str(part.get("text", part)) if isinstance(part, dict) else str(part) for part in response.content)
            else:
                content = str(response.content)
        else:
            content = str(response)
        
        # Parse JSON response
        # Handle markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # Clean up content - extract just the JSON part
        content = content.strip()
        if not content.startswith("{"):
            # Try to find JSON in the content
            import re
            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                content = json_match.group()
        
        result = json.loads(content)
        
        specialty = result.get("specialty")
        location = result.get("location")
        
        # Convert null/None to actual None
        if specialty in (None, "null", ""):
            specialty = None
        if location in (None, "null", ""):
            location = None
        
        logger.info(f"Extracted from '{user_input}': specialty={specialty}, location={location}")
        
        return {"specialty": specialty, "location": location}
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return {"specialty": None, "location": None}

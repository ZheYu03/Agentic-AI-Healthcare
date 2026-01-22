import json
import re
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.planner import _build_llm
from app.core.config import get_settings
from app.tools.supabase_tool import get_supabase_client
from app.tools.memory import hydrate_state_from_long_term_memory, upsert_long_term_memory
import logging

logger = logging.getLogger(__name__)


# ---------- Pydantic Schema for LLM Extraction ----------

class RequiredCoverages(BaseModel):
    """Coverage flags that user explicitly mentioned."""
    outpatient_covered: Optional[bool] = None
    maternity_covered: Optional[bool] = None
    mental_health_covered: Optional[bool] = None
    dental_covered: Optional[bool] = None
    optical_covered: Optional[bool] = None


class InsuranceIntentSchema(BaseModel):
    """Structured schema for LLM to extract insurance preferences.
    
    CRITICAL: Only extract information explicitly stated in the user input.
    Use None for fields that are not mentioned. DO NOT guess or infer values.
    """
    age: Optional[int] = Field(
        None,
        ge=1,
        le=119,
        description="User's age in years. Only set if explicitly mentioned (e.g., 'I am 45', 'age 30'). Use None if not stated."
    )
    budget_max: Optional[float] = Field(
        None,
        ge=0,
        le=100000,
        description="Maximum monthly budget for insurance premium. Only set if explicitly mentioned with currency or 'monthly' context. Use None if not stated."
    )
    user_conditions: List[str] = Field(
        default_factory=list,
        description="List of medical conditions explicitly mentioned (e.g., 'diabetes', 'high blood pressure', 'pregnancy'). Empty list if none mentioned."
    )
    required_coverages: RequiredCoverages = Field(
        default_factory=RequiredCoverages,
        description="Coverage types explicitly requested by user. Set to true only if user mentions needing that coverage."
    )
    plan_type: Optional[str] = Field(
        None,
        description="Type of insurance plan requested: 'Medical', 'Life', or None if not specified."
    )
    extraction_confidence: str = Field(
        "medium",
        description="Confidence in extraction quality: 'high' (all fields clearly stated), 'medium' (some ambiguity), 'low' (input unclear or incomplete)."
    )



# ---------- Parsing helpers (deterministic, no LLM) ----------

def _extract_age(text: str) -> Optional[int]:
    """
    Extract age from common phrasings:
    - "I am 45 years old", "I'm 45", "age 45", "45 years old", "45yo"
    Age must be 1..119. Avoids misreading currency/budget.
    """
    lowered = text.lower()
    # Punctuation-safe explicit age phrases (no trailing \\b so commas/periods are allowed).
    patterns = [
        r"age\s*(\d{1,3})",                          # "age 45"
        r"(?:i am|i'm)\s*(\d{1,3})\s*(?:years?\s*old)?",  # "I am 45 years old", "I'm 45"
        r"(\d{1,3})\s*years?\s*old",                # "45 years old,"
        r"(\d{1,3})\s*yo",                           # "45yo"
    ]
    for pat in patterns:
        m = re.search(pat, lowered)
        if not m:
            continue
        num = m.group(1)
        if num and num.isdigit():
            age_val = int(num)
            if 1 <= age_val <= 119:
                return age_val
    return None


def _extract_budget(text: str) -> Optional[float]:
    """
    Extract a monthly budget only when currency or explicit monthly wording is present.
    Prevents ages being misread as budgets.
    """
    # Require currency or explicit monthly wording; allow commas in numbers.
    pattern = re.compile(
        r"""
        (?:                                   # currency + number OR number + monthly wording
            (?P<cur>rm|usd|\$)\s*(?P<num1>\d{1,3}(?:,\d{3})*(?:\.\d+)?) |
            (?P<num2>\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(per\s*month|monthly|/\s*mo|budget\s*is)
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )
    m = pattern.search(text)
    if not m:
        return None
    val = m.group("num1") or m.group("num2")
    try:
        return float(val.replace(",", ""))
    except Exception:
        return None


def _extract_conditions(text: str) -> List[str]:
    """
    Extract conditions only after cue phrases and drop generic/insurance words.
    Keeps a short list to limit LLM calls.
    """
    lowered = text.lower()
    cues = ["i have", "diagnosed with", "suffering from", "condition is", "living with"]
    stopwords = {"insurance", "coverage", "plan", "support", "medical", "policy", "help"}
    found: List[str] = []
    for cue in cues:
        if cue in lowered:
            after = lowered.split(cue, 1)[1]
            parts = re.split(r"[,.]| and | with ", after)
            for part in parts:
                phrase = part.strip()
                if not phrase or any(sw in phrase for sw in stopwords):
                    continue
                if 1 <= len(phrase.split()) <= 6 and any(ch.isalpha() for ch in phrase):
                    found.append(phrase)
    # Deduplicate preserving order
    seen = set()
    uniq = []
    for c in found:
        if c not in seen:
            uniq.append(c)
            seen.add(c)
    return uniq[:5]


# ---------- LLM-based Intent Extraction with Validation ----------

def _parse_intent_with_llm(
    llm: BaseChatModel,
    user_input: str,
    existing_state: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Use LLM to extract structured insurance constraints from natural language.
    Applies multi-layer validation to prevent hallucinations and extraction errors.
    """
    system_prompt = """You are extracting insurance requirements from user messages.

CRITICAL RULES:
1. Only extract information EXPLICITLY stated in the user input
2. Use null/None for any field not clearly mentioned
3. DO NOT guess, infer, or make up values
4. Set extraction_confidence based on clarity:
   - "high": All extracted fields are clearly stated
   - "medium": Some ambiguity or partial information
   - "low": Input is unclear, incomplete, or off-topic

Examples:
- "I'm 35 and need insurance" → age: 35, confidence: medium (no budget mentioned)
- "I'm in my mid-40s, budget around $300" → age: 45, budget_max: 300, confidence: high
- "I'm pregnant" → maternity_covered: true, user_conditions: ["pregnancy"], confidence: high
- "I live at 123 Main St" → age: null, confidence: low (address number, not age)

Return JSON following InsuranceIntentSchema."""

    user_message = f"User input: {user_input}"
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]
    
    try:
        # Use structured output if supported (Gemini/GPT-4 with function calling)
        response = llm.invoke(
            messages,
            config={
                "run_name": "InsuranceIntentExtraction",
                "tags": [
                    "agent:InsuranceAdvisorAgent",
                    "route:insurance",
                    "component:intent_parsing",
                    "capability:structured_extraction"
                ],
                "metadata": {
                    "input_length": len(user_input),
                    "has_existing_state": bool(existing_state)
                }
            }
        )
        
        # Parse JSON from response
        content = response.content if isinstance(response.content, str) else json.dumps(response.content)
        
        # Try to find JSON object in response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if not json_match:
            logger.warning(f"LLM response did not contain valid JSON: {content[:200]}")
            return {"extraction_confidence": "low"}
        
        llm_data = json.loads(json_match.group(0))
        
        # Validate against schema (will raise ValidationError if invalid)
        validated = InsuranceIntentSchema(**llm_data)
        
        # Convert to dict
        extracted = validated.model_dump()
        
        # Apply validation safeguards
        return _validate_extraction(extracted, user_input)
        
    except Exception as exc:
        logger.error(f"LLM intent extraction failed: {exc}", exc_info=True)
        return {"extraction_confidence": "low"}


def _validate_extraction(llm_result: Dict[str, Any], user_input: str) -> Dict[str, Any]:
    """
    Apply multi-layer validation to LLM extraction results.
    
    Layers:
    1. Range validation (age, budget sanity checks)
    2. Cross-validation with regex patterns
    3. Confidence-based filtering for critical fields
    """
    validated = dict(llm_result)
    
    # Layer 1: Range Validation
    if validated.get("age") is not None:
        age = validated["age"]
        if not (1 <= age <= 119):
            logger.warning(f"LLM extracted invalid age: {age} - discarding")
            validated["age"] = None
    
    if validated.get("budget_max") is not None:
        budget = validated["budget_max"]
        if budget < 0 or budget > 100000:
            logger.warning(f"LLM extracted invalid budget: {budget} - discarding")
            validated["budget_max"] = None
    
    # Layer 2: Cross-validation with regex patterns (prefer regex for exact matches)
    regex_age = _extract_age(user_input)
    llm_age = validated.get("age")
    
    if regex_age and llm_age:
        if regex_age != llm_age:
            logger.warning(
                f"Age mismatch - LLM: {llm_age}, Regex: {regex_age}. "
                f"Preferring regex (more deterministic)"
            )
            validated["age"] = regex_age
        else:
            logger.info(f"Age {llm_age} validated by both LLM and regex")
    elif regex_age and not llm_age:
        # Regex found age but LLM didn't - trust regex
        logger.info(f"Using regex-extracted age {regex_age} (LLM missed it)")
        validated["age"] = regex_age
    
    regex_budget = _extract_budget(user_input)
    llm_budget = validated.get("budget_max")
    
    if regex_budget and llm_budget:
        # Both found budget - check for major discrepancies
        if abs(regex_budget - llm_budget) > 50:  # Allow small rounding differences
            logger.warning(
                f"Budget mismatch - LLM: {llm_budget}, Regex: {regex_budget}. "
                f"Preferring regex"
            )
            validated["budget_max"] = regex_budget
    elif regex_budget and not llm_budget:
        logger.info(f"Using regex-extracted budget {regex_budget}")
        validated["budget_max"] = regex_budget
    
    # Layer 3: Confidence-based filtering
    # For low confidence, discard critical fields (age/budget) to force clarification
    if validated.get("extraction_confidence") == "low":
        logger.info("Low confidence extraction - clearing age and budget to trigger clarification")
        validated["age"] = None
        validated["budget_max"] = None
    
    # Flatten required_coverages for compatibility
    coverages = validated.get("required_coverages", {})
    if isinstance(coverages, dict):
        # Filter out None values
        validated["required_coverages"] = {k: v for k, v in coverages.items() if v is not None}
    
    return validated


def parse_insurance_intent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Hybrid intent extraction: LLM-based with regex validation and state merging.
    
    Flow:
    1. Use LLM to extract intent from user_input (handles natural language)
    2. Merge with existing state fields (explicit state takes priority)
    3. Apply validation safeguards
    4. Return enriched constraints with confidence scoring
    """
    insurance = state.get("insurance") or {}
    text = (state.get("user_input") or "").strip()
    
    # Early return if no new input to parse
    if not text:
        return {
            "age": insurance.get("age"),
            "budget_max": insurance.get("budget_max"),
            "required_coverages": insurance.get("required_coverages", {}),
            "plan_type": insurance.get("plan_type"),
            "user_conditions": insurance.get("user_conditions", []),
            "extraction_confidence": "medium"
        }
    
    # Use LLM-based extraction for natural language understanding
    settings = get_settings()
    llm = _build_llm(settings)
    
    logger.info(f"Parsing insurance intent from user input: {text[:100]}...")
    llm_extracted = _parse_intent_with_llm(llm, text, insurance)
    
    # Merge with existing state (explicit state fields take priority over extracted)
    age = insurance.get("age") or llm_extracted.get("age")
    budget_max = insurance.get("budget_max") or llm_extracted.get("budget_max")
    plan_type = insurance.get("plan_type") or llm_extracted.get("plan_type")
    
    # Merge conditions (combine existing + newly extracted, dedupe)
    existing_conditions = insurance.get("user_conditions") or []
    extracted_conditions = llm_extracted.get("user_conditions") or []
    all_conditions = existing_conditions + extracted_conditions
    user_conditions = list(dict.fromkeys(all_conditions))  # Dedupe preserving order
    
    # Merge coverages (OR logic - if either source says true, it's required)
    existing_coverages = insurance.get("required_coverages") or {}
    extracted_coverages = llm_extracted.get("required_coverages") or {}
    required_coverages = {}
    all_coverage_keys = set(existing_coverages.keys()) | set(extracted_coverages.keys())
    for key in all_coverage_keys:
        required_coverages[key] = existing_coverages.get(key, False) or extracted_coverages.get(key, False)
    
    extraction_confidence = llm_extracted.get("extraction_confidence", "medium")
    
    logger.info(
        f"Parsed intent - Age: {age}, Budget: {budget_max}, "
        f"Conditions: {user_conditions}, Confidence: {extraction_confidence}"
    )
    
    return {
        "age": age,
        "budget_max": budget_max,
        "required_coverages": {k: v for k, v in required_coverages.items() if v},
        "plan_type": plan_type,
        "user_conditions": user_conditions,
        "extraction_confidence": extraction_confidence,
    }


# ---------- Supabase deterministic filtering ----------

def fetch_candidate_plans(constraints: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Apply deterministic filters in Supabase:
    - is_active = true
    - age between min_age and max_age (if age provided)
    - monthly_premium_min <= budget_max (if provided)
    - required coverage booleans
    - plan_type (case-insensitive equality)
    
    Note: Age filtering is partially done here and completed in Python-side (_age_ok)
    because Supabase doesn't support complex AND/OR combinations.
    """
    try:
        sb = get_supabase_client()
        query = sb.table("Insurance Plans").select("*").eq("is_active", True)
        
        age = constraints.get("age")
        if age is not None:
            # Filter out plans where min_age > age (user is too young)
            # We'll handle max_age in Python because Supabase OR can't express both bounds properly
            query = query.or_(f"min_age.is.null,min_age.lte.{age}")
            
        budget = constraints.get("budget_max")
        if budget is not None:
            # Only include plans where premium is within budget (or NULL if price not set)
            query = query.or_(f"monthly_premium_min.is.null,monthly_premium_min.lte.{budget}")
            
        plan_type = constraints.get("plan_type")
        if plan_type:
            # Partial match to allow plan type variants (safe improvement)
            query = query.ilike("plan_type", f"%{plan_type}%")

        # Apply required coverage filters (these are AND conditions)
        for cov_key, cov_val in (constraints.get("required_coverages") or {}).items():
            if cov_val:
                query = query.eq(cov_key, True)

        resp = query.execute()
        plans = resp.data or []
        
        # Log for debugging
        logger.info(
            f"Fetched {len(plans)} candidate plans from Supabase "
            f"(age={age}, budget={budget}, plan_type={plan_type}, "
            f"required_coverages={list((constraints.get('required_coverages') or {}).keys())})"
        )
        
        return plans, None
    except Exception as exc:
        logger.error(f"Supabase insurance query failed: {exc}", exc_info=True)
        return [], f"Supabase insurance query failed: {exc}"


# Python-side age check because Supabase OR cannot express both bounds reliably.
def _age_ok(plan: Dict[str, Any], age: Optional[int]) -> bool:
    """
    Strict age validation: user age must be within [min_age, max_age].
    - If min_age is set and age < min_age → reject (too young)
    - If max_age is set and age > max_age → reject (too old)
    - If both are NULL → accept (no age restrictions)
    """
    if age is None:
        return True
    
    plan_name = plan.get("plan_name", "Unknown")
    min_age = plan.get("min_age")
    max_age = plan.get("max_age")
    
    # User is too young for this plan
    if min_age is not None and age < min_age:
        logger.debug(f"Filtering out '{plan_name}': age {age} < min_age {min_age}")
        return False
    
    # User is too old for this plan
    if max_age is not None and age > max_age:
        logger.debug(f"Filtering out '{plan_name}': age {age} > max_age {max_age}")
        return False
    
    return True


# ---------- Semantic condition matching (LLM) ----------

def _normalize_list_field(val: Any) -> List[str]:
    """Ensure JSONB fields are materialized as string lists."""
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x) for x in val if x is not None]
    if isinstance(val, str):
        try:
            loaded = json.loads(val)
            if isinstance(loaded, list):
                return [str(x) for x in loaded if x is not None]
        except Exception:
            return [val]
    return []


def _classify_condition_fit(
    llm: BaseChatModel,
    condition: str,
    covered: List[str],
    excluded: List[str],
) -> str:
    """
    Ask the LLM to classify one condition; memoize to avoid call explosion.
    Attempts to parse the first JSON object returned; defaults to 'unclear' on failure.
    """
    # Sort lists so cache keys are stable regardless of ordering.
    covered_tuple = tuple(sorted(covered))
    excluded_tuple = tuple(sorted(excluded))
    llm_key = getattr(llm, "model_name", "") or getattr(llm, "model", "") or "llm"

    @lru_cache(maxsize=256)
    def _run(condition_key: str, cov: Tuple[str, ...], exc: Tuple[str, ...], key: str) -> str:
        system = (
            "You are evaluating insurance coverage. "
            "Decide if the user condition is covered, excluded, or unclear based ONLY on the lists provided. "
            "Reply with a single JSON object: {\"status\": \"covered|excluded|unclear\"}."
        )
        user = (
            f"User condition: {condition_key}\n"
            f"Covered conditions list: {json.dumps(list(cov))}\n"
            f"Excluded conditions list: {json.dumps(list(exc))}\n"
        )
        msg = [
            SystemMessage(content=system),
            HumanMessage(content=user),
        ]
        resp = llm.invoke(
            msg,
            config={
                "run_name": "ConditionCoverageCheck",
                "tags": [
                    "agent:InsuranceAdvisorAgent",
                    "route:insurance",
                    "component:coverage_evaluation",
                    "capability:semantic_matching"
                ],
                "metadata": {
                    "condition": condition_key,
                    "covered_items_count": len(cov),
                    "excluded_items_count": len(exc)
                }
            }
        )
        raw = resp.content if isinstance(resp.content, str) else json.dumps(resp.content)
        # Extract first JSON object defensively
        m = re.search(r"\\{.*?\\}", raw, re.DOTALL)
        if not m:
            return "unclear"
        try:
            data = json.loads(m.group(0))
            status = (data or {}).get("status")
            if status in {"covered", "excluded", "unclear"}:
                return status
        except Exception:
            return "unclear"
        return "unclear"

    return _run(condition, covered_tuple, excluded_tuple, llm_key)


def evaluate_plan_conditions(
    llm: BaseChatModel,
    plan: Dict[str, Any],
    user_conditions: List[str],
) -> Tuple[str, List[str]]:
    """
    Evaluate condition fit for a plan.
    Returns (fit_label, warnings)
    fit_label: good | partial | reject
    
    Note: If no user_conditions provided, all plans get "good" fit.
    This is intentional - differentiation comes from premium/benefits ranking.
    """
    covered = _normalize_list_field(plan.get("covered_conditions"))
    excluded = _normalize_list_field(plan.get("excluded_conditions"))
    
    if not user_conditions:
        # No specific medical conditions to check
        # All plans are considered "good" from a condition perspective
        # Differentiation will come from premium, coverage, and benefits
        return "good", []

    warnings: List[str] = []
    has_unclear = False
    
    for cond in user_conditions:
        status = _classify_condition_fit(llm, cond, covered, excluded)
        
        if status == "excluded":
            warnings.append(f"{cond} is excluded by this plan.")
            return "reject", warnings
        
        if status == "unclear":
            # Return partial status - caller will handle follow-up logic if needed
            has_unclear = True
            warnings.append(f"Coverage for {cond} is unclear based on plan data.")
    
    if has_unclear:
        return "partial", warnings
    
    return "good", warnings


# ---------- Explanation (optional LLM) ----------

def build_explanation(
    llm: BaseChatModel,
    plan: Dict[str, Any],
    fit: str,
    user_conditions: List[str],
    warnings: List[str],
) -> str:
    """
    Short explanation using plan data; optionally LLM-generated but grounded only on provided fields.
    """
    # Deterministic template fallback
    base = f"{plan.get('plan_name') or 'This plan'} from {plan.get('provider_name', 'the provider')}."
    expl_parts = [base]
    
    # Handle premium (may be None for some plans)
    premium = plan.get("monthly_premium_min")
    if premium is not None:
        expl_parts.append(f"Estimated monthly premium starts around RM{premium}.")
    else:
        # Premium not available - mention annual limit or other benefits
        annual_limit = plan.get("annual_limit")
        if annual_limit:
            expl_parts.append(f"Annual coverage limit: RM{annual_limit:,}.")
        else:
            expl_parts.append("Contact provider for premium details.")
    
    if user_conditions:
        expl_parts.append(f"Fit assessment: {fit} for your conditions ({', '.join(user_conditions)}).")
    if warnings:
        expl_parts.append("Warnings: " + "; ".join(warnings))
    return " ".join(expl_parts)


# ---------- Agent entrypoint ----------

def insurance_recommendation_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recommend insurance plans based on deterministic filters + LLM for condition coverage.
    Writes results to state['insurance'].
    """
    insurance_state = state.get("insurance") or {}
    patient_id = state.get("patient_id")
    
    # Note: LTM hydration now handled by orchestrator wrapper


    # --- INGEST FOLLOW-UP ANSWER ---
    if insurance_state.get("needs_clarification") and state.get("user_input"):
        user_input = state.get("user_input", "").strip()
        clarification_type = insurance_state.get("clarification_type")
        
        if clarification_type == "age":
            # Extract age from answer (e.g., "I am 30 years old" or just "30")
            import re
            age_match = re.search(r'\b(\d{1,3})\b', user_input)
            if age_match:
                age = int(age_match.group(1))
                if 0 < age < 120:  # Sanity check
                    insurance_state["age"] = age
                    print(f"[DEBUG] Ingested age from user answer: {age}")
                else:
                    print(f"[DEBUG] Age {age} out of range")
            else:
                print(f"[DEBUG] Could not extract age from: {user_input}")
        
        # Clear clarification flags
        insurance_state["needs_clarification"] = False
        insurance_state.pop("clarification_type", None)
        insurance_state.pop("clarification_question", None)
        # CRITICAL: Save state before parsing
        state["insurance"] = insurance_state
    
    parsed = parse_insurance_intent(state)
    print(f"[DEBUG] Parsed insurance intent: {parsed}")
    
    # CHECK LTM: Smart age change detection
    ltm_age = insurance_state.get("constraints", {}).get("insurance_age")
    current_age = parsed.get("age")
    
    if ltm_age and current_age and ltm_age != current_age:
        logger.info(f"Age changed from {ltm_age} to {current_age} - updating recommendations")
        # Could add to messages later: f"Updated from age {ltm_age} to {current_age}"
    
    insurance_state["user_profile"] = parsed
    
    # Check if we have minimum required information
    # At least age is needed for most insurance recommendations
    if parsed.get("age") is None:
        # Ask for age if not provided
        if not insurance_state.get("needs_clarification"):
            insurance_state["needs_clarification"] = True
            insurance_state["clarification_type"] = "age"
            insurance_state["clarification_question"] = "What is your age? This helps us recommend suitable insurance plans."
            state["insurance"] = insurance_state
            # Signal orchestrator to pause
            execution = state.get("execution") or {}
            execution["awaiting_followup"] = True
            execution["pending_agent"] = "InsuranceAdvisorAgent"
            execution["status"] = "waiting_for_user"
            state["execution"] = execution
            return state

    candidates, err = fetch_candidate_plans(parsed)
    logger.info(f"Initial candidates from Supabase: {len(candidates)}")
    
    # Supabase OR cannot cleanly enforce both age bounds; apply definitive age filter here.
    if parsed.get("age") is not None:
        before_age_filter = len(candidates)
        candidates = [p for p in candidates if _age_ok(p, parsed["age"])]
        logger.info(f"After age filter: {len(candidates)} plans (filtered out {before_age_filter - len(candidates)})")
    
    if err:
        logger.error(f"Error fetching plans: {err}")
        errs = list(state.get("errors", []))
        errs.append(err)
        state["errors"] = errs
        insurance_state["recommended_plans"] = []
        insurance_state["confidence"] = "low"
        state["insurance"] = insurance_state
        return state

    if not candidates:
        logger.warning(f"No candidate plans found for constraints: {parsed}")
        insurance_state["recommended_plans"] = []
        insurance_state["confidence"] = "low"
        state["insurance"] = insurance_state
        return state

    settings = get_settings()
    llm = _build_llm(settings)
    evaluated: List[Tuple[str, Dict[str, Any]]] = []  # (fit_label, plan)

    user_conditions = parsed.get("user_conditions") or []
    logger.info(f"Evaluating {len(candidates)} plans against conditions: {user_conditions}")
    
    for plan in candidates:
        plan_name = plan.get("plan_name", "Unknown")
        fit, warnings = evaluate_plan_conditions(llm, plan, user_conditions)
        
        if fit == "reject":
            logger.info(f"Plan '{plan_name}' rejected due to excluded conditions")
            continue
        
        logger.debug(
            f"Plan '{plan_name}': fit={fit}, premium={plan.get('monthly_premium_min')}, "
            f"annual_limit={plan.get('annual_limit')}, warnings={warnings}"
        )
        
        plan_copy = dict(plan)
        plan_copy["_fit_label"] = fit
        plan_copy["_warnings"] = warnings
        evaluated.append((fit, plan_copy))

    logger.info(f"After condition evaluation: {len(evaluated)} plans passed")
    
    if not evaluated:
        logger.warning("No plans passed condition evaluation")
        insurance_state["recommended_plans"] = []
        insurance_state["confidence"] = "low"
        state["insurance"] = insurance_state
        return state

    # Rank plans: fit (good > partial) then lower premium, higher annual_limit, lower deductible
    def rank_key(item: Tuple[str, Dict[str, Any]]):
        fit_label, plan = item
        fit_score = 0 if fit_label == "good" else 1
        
        # Handle NULL premiums: treat as medium-high value (not lowest, not highest)
        # This allows plans with actual prices to rank by price,
        # while plans without prices still appear (sorted by benefits)
        premium = plan.get("monthly_premium_min")
        if premium is None:
            # NULL premiums sort after priced plans but still appear
            # Use 500 as "unknown price" marker (between budget and premium plans)
            premium_sort = (1, 500)  # (has_null=1, assumed_value=500)
        else:
            premium_sort = (0, premium)  # (has_null=0, actual_price)
        
        annual_limit = -(plan.get("annual_limit") or 0)  # negative for descending (higher is better)
        deductible = plan.get("deductible") or 0  # ascending (lower is better)
        
        return (fit_score, premium_sort, annual_limit, deductible)

    evaluated.sort(key=rank_key)
    
    # Log ranking details (show diversity of recommendations)
    logger.info(f"Plan ranking details (top 10 of {len(evaluated)}):")
    for idx, (fit_label, plan) in enumerate(evaluated[:10], 1):
        premium = plan.get('monthly_premium_min')
        premium_str = f"RM{premium}/mo" if premium else "Price TBD"
        logger.info(
            f"  {idx}. {plan.get('plan_name')} ({plan.get('provider_name')}): "
            f"fit={fit_label}, premium={premium_str}, "
            f"annual_limit=RM{plan.get('annual_limit') or 0}, "
            f"deductible=RM{plan.get('deductible') or 0}"
        )

    recommended = []
    for fit_label, plan in evaluated[:3]:  # cap list to keep response concise
        summary = build_explanation(llm, plan, fit_label, parsed.get("user_conditions") or [], plan.get("_warnings", []))
        rec = {
            "provider_name": plan.get("provider_name"),
            "plan_name": plan.get("plan_name"),
            "fit": "good" if fit_label == "good" else "partial",
            "monthly_premium_range": f"{plan.get('monthly_premium_min', '')} - {plan.get('monthly_premium_max', '')}",
            "coverage_summary": summary,
            "warnings": plan.get("_warnings", []),
            # Include more database fields for detailed display
            "annual_limit": plan.get("annual_limit"),
            "deductible": plan.get("deductible"),
            "room_board_limit": plan.get("room_board_limit"),
            "outpatient_covered": plan.get("outpatient_covered"),
            "maternity_covered": plan.get("maternity_covered"),
            "dental_covered": plan.get("dental_covered"),
            "optical_covered": plan.get("optical_covered"),
            "mental_health_covered": plan.get("mental_health_covered"),
            "min_age": plan.get("min_age"),
            "max_age": plan.get("max_age"),
            "contact_phone": plan.get("contact_phone"),
            "website": plan.get("website"),
            "claim_process": plan.get("claim_process"),
            "covered_conditions": plan.get("covered_conditions"),
        }
        recommended.append(rec)

    confidence = "high" if any(r["fit"] == "good" for r in recommended) else "medium"
    insurance_state["recommended_plans"] = recommended
    insurance_state["confidence"] = confidence
    
    # Log final recommendations
    logger.info(
        f"Returning {len(recommended)} insurance recommendations with {confidence} confidence. "
        f"Top plan: {recommended[0].get('plan_name') if recommended else 'None'}"
    )
    
    # Clear clarification flags on successful completion
    insurance_state.pop("needs_clarification", None)
    insurance_state.pop("clarification_type", None)
    insurance_state.pop("clarification_question", None)
    state["insurance"] = insurance_state
    
    # Store preferences in LTM if patient_id exists and we have recommendations
    if patient_id and recommended:
        if parsed.get("age"):
            upsert_long_term_memory(
                patient_id=patient_id,
                memory_type="context",
                memory_key="insurance_age",
                memory_value=parsed["age"],
                source_agent="InsuranceAdvisorAgent"
            )
        if parsed.get("budget_max"):
            upsert_long_term_memory(
                patient_id=patient_id,
                memory_type="constraint",
                memory_key="budget_max",
                memory_value=parsed["budget_max"],
                source_agent="InsuranceAdvisorAgent"
            )
        if parsed.get("plan_type"):
            upsert_long_term_memory(
                patient_id=patient_id,
                memory_type="context",
                memory_key="plan_type",
                memory_value=parsed["plan_type"],
                source_agent="InsuranceAdvisorAgent"
            )
        logger.info(f"Stored insurance preferences in LTM for patient {patient_id}")
    
    # CRITICAL: Clear execution flags so response builder knows agent completed
    execution = state.get("execution") or {}
    execution["awaiting_followup"] = False
    execution.pop("pending_agent", None)
    if execution.get("status") == "waiting_for_user":
        execution["status"] = "completed"
    state["execution"] = execution
    
    return state

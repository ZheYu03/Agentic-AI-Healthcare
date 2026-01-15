import json
import re
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.planner import _build_llm
from app.core.config import get_settings
from app.tools.supabase_tool import get_supabase_client
from app.tools.memory import hydrate_state_from_long_term_memory, upsert_long_term_memory
import logging

logger = logging.getLogger(__name__)


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


def parse_insurance_intent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic intent/constraint extraction (no LLM).
    Prefers structured fields already in state['insurance'] and falls back to regex parsing of user_input.
    """
    insurance = state.get("insurance") or {}
    text = (state.get("user_input") or "").strip()

    age = insurance.get("age") or _extract_age(text)
    budget = insurance.get("budget_max") or _extract_budget(text)

    coverages = insurance.get("required_coverages") or {}
    # Simple keyword toggles
    lower_text = text.lower()
    keyword_map = {
        "outpatient_covered": ["outpatient", "clinic visits"],
        "maternity_covered": ["maternity", "pregnancy"],
        "mental_health_covered": ["mental health", "psych", "depression", "anxiety"],
        "dental_covered": ["dental", "teeth"],
        "optical_covered": ["optical", "vision", "glasses"],
    }
    for key, kws in keyword_map.items():
        if key not in coverages:
            coverages[key] = any(kw in lower_text for kw in kws)

    plan_type = insurance.get("plan_type")
    if not plan_type:
        if "life" in lower_text:
            plan_type = "Life"
        elif "medical" in lower_text or "health" in lower_text:
            plan_type = "Medical"

    user_conditions = insurance.get("user_conditions") or _extract_conditions(text)

    return {
        "age": age,
        "budget_max": budget,
        "required_coverages": {k: v for k, v in coverages.items() if v},
        "plan_type": plan_type,
        "user_conditions": user_conditions,
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
    """
    try:
        sb = get_supabase_client()
        query = sb.table("Insurance Plans").select("*").eq("is_active", True)
        age = constraints.get("age")
        if age is not None:
            # Single OR clause combining both bound checks to avoid chaining errors.
            # (min_age IS NULL OR min_age <= age) AND (max_age IS NULL OR max_age >= age)
            query = query.or_(f"min_age.is.null,min_age.lte.{age},max_age.is.null,max_age.gte.{age}")
        budget = constraints.get("budget_max")
        if budget is not None:
            # Allow null premium lower bound
            query = query.or_(f"monthly_premium_min.is.null,monthly_premium_min.lte.{budget}")
        plan_type = constraints.get("plan_type")
        if plan_type:
            # Partial match to allow plan type variants (safe improvement)
            query = query.ilike("plan_type", f"%{plan_type}%")

        for cov_key, cov_val in (constraints.get("required_coverages") or {}).items():
            if cov_val:
                query = query.eq(cov_key, True)

        resp = query.execute()
        return resp.data or [], None
    except Exception as exc:
        return [], f"Supabase insurance query failed: {exc}"


# Python-side age check because Supabase OR cannot express both bounds reliably.
def _age_ok(plan: Dict[str, Any], age: Optional[int]) -> bool:
    if age is None:
        return True
    min_age = plan.get("min_age")
    max_age = plan.get("max_age")
    if min_age is not None and age < min_age:
        return False
    if max_age is not None and age > max_age:
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
    """
    covered = _normalize_list_field(plan.get("covered_conditions"))
    excluded = _normalize_list_field(plan.get("excluded_conditions"))
    if not user_conditions:
        return "good", []  # No condition constraints provided

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
    premium = plan.get("monthly_premium_min")
    expl_parts = [base]
    if premium is not None:
        expl_parts.append(f"Estimated monthly premium starts around {premium}.")
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
    # Supabase OR cannot cleanly enforce both age bounds; apply definitive age filter here.
    if parsed.get("age") is not None:
        candidates = [p for p in candidates if _age_ok(p, parsed["age"])]
    if err:
        errs = list(state.get("errors", []))
        errs.append(err)
        state["errors"] = errs
        insurance_state["recommended_plans"] = []
        insurance_state["confidence"] = "low"
        state["insurance"] = insurance_state
        return state

    if not candidates:
        insurance_state["recommended_plans"] = []
        insurance_state["confidence"] = "low"
        state["insurance"] = insurance_state
        return state

    settings = get_settings()
    llm = _build_llm(settings)
    evaluated: List[Tuple[str, Dict[str, Any]]] = []  # (fit_label, plan)

    for plan in candidates:
        fit, warnings = evaluate_plan_conditions(llm, plan, parsed.get("user_conditions") or [])
        if fit == "reject":
            continue
        plan_copy = dict(plan)
        plan_copy["_fit_label"] = fit
        plan_copy["_warnings"] = warnings
        evaluated.append((fit, plan_copy))

    if not evaluated:
        insurance_state["recommended_plans"] = []
        insurance_state["confidence"] = "low"
        state["insurance"] = insurance_state
        return state

    # Rank plans: fit (good > partial) then lower premium, higher annual_limit, lower deductible
    def rank_key(item: Tuple[str, Dict[str, Any]]):
        fit_label, plan = item
        fit_score = 0 if fit_label == "good" else 1
        premium = plan.get("monthly_premium_min") or float("inf")
        annual_limit = -(plan.get("annual_limit") or 0)  # negative for descending
        deductible = plan.get("deductible") or 0
        return (fit_score, premium, annual_limit, deductible)

    evaluated.sort(key=rank_key)

    recommended = []
    for fit_label, plan in evaluated[:5]:  # cap list to keep response concise
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

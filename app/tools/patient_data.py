"""
Patient data helper for fetching patient profile information.
Used to enhance agent context with demographics and medical history.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import logging

from app.tools.supabase_tool import get_supabase_client

logger = logging.getLogger(__name__)


def fetch_patient_profile(patient_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch patient profile from Patient Data table.
    
    Args:
        patient_id: UUID of patient
    
    Returns:
        Dict with patient data or None if not found
        {
            "age": int,
            "gender": str,
            "full_name": str,
            "date_of_birth": str,
            "blood_type": str,
            "nkda": bool,
            "drug_allergies": str,
            "medical_allergies": str,
            "food_env_allergies": str
        }
    """
    try:
        sb = get_supabase_client()
        
        result = sb.table("Patient Data")\
            .select("full_name, date_of_birth, gender, ic_number, blood_type, nkda, drug_allergies, medical_allergies, food_env_allergies")\
            .eq("id", patient_id)\
            .execute()
        
        if not result.data:
            logger.warning(f"No patient profile found for {patient_id}")
            return None
        
        profile = result.data[0]
        
        # Calculate age from date_of_birth
        age = None
        dob_str = profile.get("date_of_birth")
        if dob_str:
            try:
                # Handle both date and datetime formats
                if 'T' in str(dob_str):
                    dob = datetime.fromisoformat(dob_str.replace("Z", "+00:00"))
                else:
                    # Date-only format
                    from datetime import date
                    if isinstance(dob_str, str):
                        dob = datetime.strptime(dob_str, "%Y-%m-%d")
                    else:
                        dob = datetime.combine(dob_str, datetime.min.time())
                age = (datetime.now() - dob).days // 365
            except Exception as e:
                logger.warning(f"Failed to calculate age from DOB {dob_str}: {e}")
        
        return {
            "age": age,
            "gender": profile.get("gender"),
            "full_name": profile.get("full_name"),
            "date_of_birth": dob_str,
            "ic_number": profile.get("ic_number"),
            "blood_type": profile.get("blood_type"),
            "nkda": profile.get("nkda", False),
            "drug_allergies": profile.get("drug_allergies"),
            "medical_allergies": profile.get("medical_allergies"),
            "food_env_allergies": profile.get("food_env_allergies")
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch patient profile: {e}")
        return None

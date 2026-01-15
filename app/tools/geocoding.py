"""
Geocoding utility using OpenStreetMap Nominatim API.
Free to use, no API key required, but must respect usage policy:
- Max 1 request per second
- Must include User-Agent header
"""

import time
import logging
from typing import Optional, Dict
import requests

from langsmith import traceable

logger = logging.getLogger(__name__)

# Rate limiting: last request timestamp
_last_request_time = 0
_MIN_REQUEST_INTERVAL = 1.0  # seconds


def geocode_location(location_text: str, country_bias: str = "MY") -> Optional[Dict[str, float]]:
    """
    Convert a text location (city, address, postcode) to lat/lon coordinates.
    
    Args:
        location_text: Location as text, e.g., "Petaling Jaya", "50000", "Kuala Lumpur"
        country_bias: ISO country code to prioritize results (default: MY for Malaysia)
    
    Returns:
        {"lat": float, "lon": float} or None if geocoding failed
    """
    global _last_request_time
    
    if not location_text or not location_text.strip():
        return None
    
    # Rate limiting: ensure at least 1 second between requests
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
    
    location_text = location_text.strip()
    
    try:
        # OpenStreetMap Nominatim API
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": location_text,
            "format": "json",
            "limit": 1,
            "countrycodes": country_bias,  # Prioritize Malaysia
        }
        headers = {
            "User-Agent": "MedicalChatbot/1.0 (Healthcare Assistant)"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        _last_request_time = time.time()
        
        if response.status_code != 200:
            logger.error(f"Geocoding failed with status {response.status_code}")
            return None
        
        results = response.json()
        
        if not results or len(results) == 0:
            logger.warning(f"No geocoding results for location: {location_text}")
            return None
        
        # Return first result
        result = results[0]
        lat = float(result["lat"])
        lon = float(result["lon"])
        
        logger.info(f"Geocoded '{location_text}' → ({lat}, {lon})")
        
        return {"lat": lat, "lon": lon}
        
    except requests.RequestException as e:
        logger.error(f"Geocoding request failed: {e}")
        return None
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Geocoding response parsing failed: {e}")
        return None

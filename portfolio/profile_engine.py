"""Demo investor profiles for Fintel personalization.

Edit PROFILES below to add or change demo users. No database is used.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

# Easy-to-edit demo data. Weights are portfolio fractions (should sum to ~1.0).
PROFILES: dict[str, dict[str, Any]] = {
    "rahul": {
        "user_id": "rahul",
        "name": "Rahul",
        "risk_tolerance": "CONSERVATIVE",
        "portfolio": {
            "TCS": 0.40,
            "INFY": 0.30,
            "RELIANCE": 0.30,
        },
        "behavior": {
            "recent_high_risk_searches": 1,
            "prefers_growth": False,
        },
    },
    "arjun": {
        "user_id": "arjun",
        "name": "Arjun",
        "risk_tolerance": "AGGRESSIVE",
        "portfolio": {
            "TCS": 0.10,
            "INFY": 0.10,
            "RELIANCE": 0.20,
            "CASH": 0.60,
        },
        "behavior": {
            "recent_high_risk_searches": 4,
            "prefers_growth": True,
        },
    },
}

_UNKNOWN_USER = {
    "error": "unknown_user",
    "user_id": "",
    "message": "Unknown user. Demo profiles: rahul, arjun.",
}


def get_profile(user_id: str) -> dict[str, Any]:
    """Return a copy of the demo investor profile for ``user_id``.

    Unknown users return a small error dict instead of raising.
    """
    if not user_id:
        result = dict(_UNKNOWN_USER)
        result["user_id"] = user_id
        result["message"] = "Missing user_id. Demo profiles: rahul, arjun."
        return result

    key = str(user_id).strip().lower()
    profile = PROFILES.get(key)
    if profile is None:
        result = dict(_UNKNOWN_USER)
        result["user_id"] = user_id
        return result
    return deepcopy(profile)


def get_behavioral_profile(user_id: str) -> dict[str, Any]:
    """Return demo behavior attributes only (not a psychological model).

    Unknown users return an error dict, same style as ``get_profile``.
    """
    profile = get_profile(user_id)
    if "error" in profile:
        return profile
    return deepcopy(profile.get("behavior", {}))

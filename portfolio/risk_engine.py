"""Illustrative, deterministic portfolio-risk helpers for the Fintel demo.

These are not a real suitability, VaR, or factor model. They exist so the
same market event can produce a different result for Rahul vs Arjun.
"""

from __future__ import annotations

from typing import Any

from portfolio.portfolio_loader import get_largest_position, get_stock_exposure
from portfolio.profile_engine import get_profile

# Concentration bands (inclusive HIGH at 40% so Rahul's 40% TCS is HIGH):
#   weight <= 0.20          -> LOW
#   0.20 < weight < 0.40    -> MODERATE
#   weight >= 0.40          -> HIGH
_DOWNGRADE = {"HIGH": "MODERATE", "MODERATE": "LOW", "LOW": "LOW"}
_UPGRADE = {"LOW": "MODERATE", "MODERATE": "HIGH", "HIGH": "HIGH"}


def classify_concentration(weight: float) -> str:
    """Map a portfolio weight to LOW / MODERATE / HIGH.

    40% is HIGH (not MODERATE) so Rahul's TCS position is HIGH in the demo.
    """
    try:
        value = float(weight)
    except (TypeError, ValueError):
        return "LOW"
    if value <= 0.20:
        return "LOW"
    if value < 0.40:
        return "MODERATE"
    return "HIGH"


def calculate_concentration(user_id: str) -> dict[str, Any]:
    """Identify the largest allocation (concentration) for a user.

    Example: Rahul's largest line is TCS at 0.40.
    """
    largest = get_largest_position(user_id)
    weight = float(largest.get("weight") or 0.0)
    return {
        "user_id": user_id,
        "symbol": largest.get("symbol"),
        "concentration": weight,
        "classification": classify_concentration(weight),
    }


def calculate_stock_impact(user_id: str, symbol: str, change_pct: float) -> dict[str, Any]:
    """Illustrative direct impact: ``portfolio_weight * market_change_pct``.

    Example: 0.40 * -2.8 = -1.12. Unknown user/stock uses weight 0.0.
    """
    try:
        market_change_pct = float(change_pct)
    except (TypeError, ValueError):
        market_change_pct = 0.0

    weight = get_stock_exposure(user_id, symbol)
    impact = round(weight * market_change_pct, 4)
    return {
        "symbol": str(symbol).upper() if symbol else None,
        "portfolio_weight": weight,
        "market_change_pct": market_change_pct,
        "estimated_portfolio_impact_pct": impact,
        "note": "Illustrative direct impact only (weight x percent change), not a full risk model.",
    }


def _parse_market_signal(market_signal: str | dict[str, Any]) -> tuple[str, float]:
    """Return (direction, confidence). Direction is BEARISH, BULLISH, or NEUTRAL."""
    if isinstance(market_signal, dict):
        raw = market_signal.get("signal") or market_signal.get("direction") or ""
        try:
            confidence = float(market_signal.get("confidence", 1.0))
        except (TypeError, ValueError):
            confidence = 1.0
    else:
        raw = market_signal
        confidence = 1.0

    direction = str(raw or "NEUTRAL").strip().upper()
    if direction not in {"BEARISH", "BULLISH", "NEUTRAL"}:
        direction = "NEUTRAL"
    if confidence < 0:
        confidence = 0.0
    if confidence > 1:
        confidence = 1.0
    return direction, confidence


def calculate_personalized_impact(
    user_id: str,
    symbol: str,
    market_signal: str | dict[str, Any],
) -> str:
    """Simple demo label from exposure + risk tolerance + signal.

    Demo targets:
    - Rahul + TCS + BEARISH -> HIGH (40% TCS, conservative)
    - Arjun + TCS + BEARISH -> LOW (10% TCS, aggressive)

    ``market_signal`` may be ``"BEARISH"`` or ``{"signal": "BEARISH", "confidence": 0.8}``.
    Unknown user/stock returns ``"LOW"``.
    """
    profile = get_profile(user_id)
    if "error" in profile:
        return "LOW"

    weight = get_stock_exposure(user_id, symbol)
    level = classify_concentration(weight)
    direction, confidence = _parse_market_signal(market_signal)
    risk = str(profile.get("risk_tolerance", "")).upper()
    prefers_growth = bool((profile.get("behavior") or {}).get("prefers_growth"))

    if direction == "BEARISH":
        # Conservative investors treat a drop in a large holding as more severe.
        if risk == "CONSERVATIVE":
            impact = level
        else:
            impact = _DOWNGRADE.get(level, "LOW")
        if confidence < 0.4 and impact != "LOW":
            impact = _DOWNGRADE.get(impact, "LOW")
        return impact

    if direction == "BULLISH":
        # Aggressive / growth-seeking users treat upside as more material.
        if risk == "AGGRESSIVE" or prefers_growth:
            impact = _UPGRADE.get(level, level)
        else:
            impact = level
        if confidence < 0.4 and impact != "LOW":
            impact = _DOWNGRADE.get(impact, "LOW")
        return impact

    return level

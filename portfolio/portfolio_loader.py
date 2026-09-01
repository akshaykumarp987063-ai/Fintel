"""Read a demo user's portfolio allocation for the rest of Fintel.

Unknown users and unknown symbols are handled without crashing.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from portfolio.profile_engine import get_profile

# Allow small float rounding error when checking that weights sum to 1.0.
ALLOCATION_SUM_TOLERANCE = 0.01


def validate_portfolio(portfolio: dict[str, float] | None, user_id: str | None = None) -> None:
    """Raise ``ValueError`` if allocations are missing, negative, or do not sum to ~1.0."""
    who = f" for user {user_id!r}" if user_id else ""
    if not portfolio:
        raise ValueError(f"Missing or empty portfolio{who}.")

    for symbol, weight in portfolio.items():
        try:
            value = float(weight)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid weight for {symbol}{who}: {weight!r}.") from exc
        if value < 0:
            raise ValueError(f"Negative weight for {symbol}{who}: {value}.")

    total = sum(float(w) for w in portfolio.values())
    if abs(total - 1.0) > ALLOCATION_SUM_TOLERANCE:
        raise ValueError(
            f"Portfolio weights{who} sum to {total:.4f}, expected about 1.0 "
            f"(tolerance {ALLOCATION_SUM_TOLERANCE})."
        )


def get_portfolio(user_id: str) -> dict[str, float]:
    """Return only the allocation dict, e.g. ``{"TCS": 0.40, ...}``.

    Unknown users return ``{}``. Invalid demo data raises ``ValueError``.
    """
    profile = get_profile(user_id)
    if "error" in profile:
        return {}

    portfolio = profile.get("portfolio") or {}
    validate_portfolio(portfolio, user_id=user_id)
    return {str(symbol).upper(): float(weight) for symbol, weight in deepcopy(portfolio).items()}


def get_stock_exposure(user_id: str, symbol: str) -> float:
    """Return this user's weight in ``symbol`` (0.0 if user or stock is unknown)."""
    if not symbol:
        return 0.0
    portfolio = get_portfolio(user_id)
    return float(portfolio.get(str(symbol).upper(), 0.0))


def get_largest_position(user_id: str) -> dict[str, Any]:
    """Return ``{"symbol": ..., "weight": ...}`` for the largest holding.

    Unknown or empty portfolios return ``{"symbol": None, "weight": 0.0}``.
    """
    portfolio = get_portfolio(user_id)
    if not portfolio:
        return {"symbol": None, "weight": 0.0}

    symbol, weight = max(portfolio.items(), key=lambda item: item[1])
    return {"symbol": symbol, "weight": float(weight)}

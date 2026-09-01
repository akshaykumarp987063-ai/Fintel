"""Technical Agent — price momentum and volume anomaly from supplied market data.

This module does not call APIs or LLMs. It only reads the dict you pass in.
"""

_PRICE_THRESHOLD = 1.0  # |change_pct| below this is a small move
_VOLUME_HIGH = 1.5  # volume_ratio at or above this is abnormal


def analyze_technical(market_data):
    """Score a symbol from price change and volume ratio.

    Args:
        market_data: dict with keys symbol, price, change_pct, volume_ratio.

    Returns:
        dict with agent, signal, confidence, reasoning, evidence, sources, status.
    """
    parsed, error = _parse_market_data(market_data)
    if error:
        return _result(
            signal="NEUTRAL",
            confidence=0.0,
            reasoning=error,
            evidence=[],
            status="ERROR",
        )

    symbol = parsed["symbol"]
    price = parsed["price"]
    change_pct = parsed["change_pct"]
    volume_ratio = parsed["volume_ratio"]

    abs_change = abs(change_pct)
    high_volume = volume_ratio >= _VOLUME_HIGH

    if abs_change < _PRICE_THRESHOLD:
        signal = "NEUTRAL"
        # Small move: more confident it is truly quiet when volume is also normal.
        if high_volume:
            confidence = 0.55
        else:
            confidence = 0.70
    elif change_pct > 0:
        signal = "BULLISH"
        confidence = _directional_confidence(abs_change, volume_ratio)
    else:
        signal = "BEARISH"
        confidence = _directional_confidence(abs_change, volume_ratio)

    reasoning = _build_reasoning(
        symbol, price, change_pct, volume_ratio, signal, high_volume
    )
    evidence = [
        {"field": "symbol", "value": symbol},
        {"field": "price", "value": price},
        {"field": "change_pct", "value": change_pct},
        {"field": "volume_ratio", "value": volume_ratio},
    ]

    return _result(
        signal=signal,
        confidence=confidence,
        reasoning=reasoning,
        evidence=evidence,
        status="OK",
    )


def _parse_market_data(market_data):
    """Return (parsed_dict, error_message). error is None when input is usable."""
    if not isinstance(market_data, dict):
        return None, "Invalid input: market_data must be a dictionary."

    required = ("symbol", "price", "change_pct", "volume_ratio")
    missing = [key for key in required if key not in market_data]
    if missing:
        return None, "Invalid or missing input: missing " + ", ".join(missing) + "."

    symbol = market_data["symbol"]
    if not isinstance(symbol, str) or not symbol.strip():
        return None, "Invalid input: symbol must be a non-empty string."

    try:
        price = float(market_data["price"])
        change_pct = float(market_data["change_pct"])
        volume_ratio = float(market_data["volume_ratio"])
    except (TypeError, ValueError):
        return None, "Invalid input: price, change_pct, and volume_ratio must be numbers."

    if price < 0:
        return None, "Invalid input: price cannot be negative."
    if volume_ratio < 0:
        return None, "Invalid input: volume_ratio cannot be negative."

    return {
        "symbol": symbol.strip(),
        "price": price,
        "change_pct": change_pct,
        "volume_ratio": volume_ratio,
    }, None


def _directional_confidence(abs_change, volume_ratio):
    """Larger |change_pct| and higher volume_ratio raise confidence, capped at 0.95."""
    # 5% move maps to a full price component of 0.45.
    price_part = min(abs_change / 5.0, 1.0) * 0.45
    # volume_ratio of 2.0 adds the full 0.20 volume component.
    volume_part = min(max(volume_ratio - 1.0, 0.0) / 1.0, 1.0) * 0.20
    confidence = 0.50 + price_part + volume_part
    return round(min(confidence, 0.95), 2)


def _build_reasoning(symbol, price, change_pct, volume_ratio, signal, high_volume):
    volume_text = (
        "abnormally high volume (volume_ratio {vr})".format(vr=volume_ratio)
        if high_volume
        else "normal volume (volume_ratio {vr})".format(vr=volume_ratio)
    )
    if signal == "NEUTRAL":
        return (
            "{symbol} at price {price} shows a small price move of {change}% with {volume}. "
            "Technical signal is NEUTRAL."
        ).format(
            symbol=symbol,
            price=price,
            change=change_pct,
            volume=volume_text,
        )
    direction = "positive" if signal == "BULLISH" else "negative"
    intensity = "strongly" if abs(change_pct) >= 2.0 else "notably"
    strength = "strengthens" if high_volume else "does not add extra strength to"
    return (
        "{symbol} at price {price} has a {intensity} {direction} price move of {change}%. "
        "{volume_cap} {strength} this {signal} signal."
    ).format(
        symbol=symbol,
        price=price,
        intensity=intensity,
        direction=direction,
        change=change_pct,
        volume_cap=volume_text[0].upper() + volume_text[1:],
        strength=strength,
        signal=signal,
    )


def _result(signal, confidence, reasoning, evidence, status):
    return {
        "agent": "technical",
        "signal": signal,
        "confidence": confidence,
        "reasoning": reasoning,
        "evidence": evidence,
        "sources": [],
        "status": status,
    }

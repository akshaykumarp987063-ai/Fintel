"""Sentiment Agent — maps a numeric sentiment score to a signal.

This module does not call APIs or LLMs. It only reads the number you pass in.
"""

_POSITIVE_CUTOFF = 0.3
_NEGATIVE_CUTOFF = -0.3


def analyze_sentiment(sentiment_score):
    """Map a sentiment score (about -1 to +1) to POSITIVE, NEUTRAL, or NEGATIVE.

    Args:
        sentiment_score: number, typically between -1 and +1.

    Returns:
        dict with agent, signal, confidence, reasoning, evidence, sources, status.
    """
    parsed, error = _parse_score(sentiment_score)
    if error:
        return {
            "agent": "sentiment",
            "signal": "NEUTRAL",
            "confidence": 0,
            "reasoning": error,
            "evidence": [],
            "sources": [],
            "status": "DEGRADED",
        }

    if parsed > _POSITIVE_CUTOFF:
        signal = "POSITIVE"
    elif parsed < _NEGATIVE_CUTOFF:
        signal = "NEGATIVE"
    else:
        signal = "NEUTRAL"

    if signal == "NEUTRAL":
        confidence = round(1.0 - abs(parsed), 2)
    else:
        confidence = round(min(1.0, abs(parsed)), 2)
    reasoning = (
        "Supplied sentiment score is {score}. "
        "Scores above 0.3 are POSITIVE, between -0.3 and 0.3 are NEUTRAL, "
        "and below -0.3 are NEGATIVE. Signal is {signal}."
    ).format(score=parsed, signal=signal)

    return {
        "agent": "sentiment",
        "signal": signal,
        "confidence": confidence,
        "reasoning": reasoning,
        "evidence": [{"field": "sentiment_score", "value": parsed}],
        "sources": [],
        "status": "OK",
    }


def _parse_score(sentiment_score):
    if isinstance(sentiment_score, bool) or sentiment_score is None:
        return None, "Invalid input: sentiment_score must be a number."
    try:
        score = float(sentiment_score)
    except (TypeError, ValueError):
        return None, "Invalid input: sentiment_score must be a number."
    if score != score:  # NaN
        return None, "Invalid input: sentiment_score cannot be NaN."
    return score, None

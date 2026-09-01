"""Synthesis Agent — combines technical, fundamental, and sentiment results.

This module does not retrieve documents, call APIs, or run the portfolio engine.
It only combines the three agent dicts (and optional portfolio_context) you pass in.
"""

_BULLISH = "BULLISH"
_BEARISH = "BEARISH"
_NEUTRAL = "NEUTRAL"
_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"

_DIRECTION = {
    "BULLISH": _BULLISH,
    "POSITIVE": _BULLISH,
    "BEARISH": _BEARISH,
    "NEGATIVE": _BEARISH,
    "NEUTRAL": _NEUTRAL,
    "INSUFFICIENT_EVIDENCE": _INSUFFICIENT,
}

_MAX_CONFIDENCE = 0.85  # never claim certainty


def synthesize_analysis(
    technical_result,
    fundamental_result,
    sentiment_result,
    portfolio_context=None,
):
    """Combine three agent outputs into one overall view.

    Args:
        technical_result: dict from analyze_technical.
        fundamental_result: dict from analyze_fundamentals.
        sentiment_result: dict from analyze_sentiment.
        portfolio_context: optional dict with selected_stock, exposure_pct,
            risk_tolerance. Person 4 owns the portfolio engine.

    Returns:
        dict with overall_signal, confidence, portfolio_impact, summary,
        reasoning_chain, sources, status.
    """
    technical = _read_agent(technical_result, "technical")
    fundamental = _read_agent(fundamental_result, "fundamental")
    sentiment = _read_agent(sentiment_result, "sentiment")

    bullish_votes = []
    bearish_votes = []
    for agent in (technical, fundamental, sentiment):
        if agent["direction"] == _BULLISH:
            bullish_votes.append(agent["name"])
        elif agent["direction"] == _BEARISH:
            bearish_votes.append(agent["name"])

    fund_missing = fundamental["direction"] == _INSUFFICIENT
    overall_signal, agreement = _overall_signal(
        bullish_votes, bearish_votes, technical, fundamental, sentiment
    )
    confidence = _confidence(
        technical, fundamental, sentiment, agreement, fund_missing
    )
    impact = _portfolio_impact(portfolio_context)
    sources = _collect_sources(technical, fundamental, sentiment)
    reasoning_chain = _reasoning_chain(
        technical,
        fundamental,
        sentiment,
        overall_signal,
        agreement,
        fund_missing,
        portfolio_context,
        impact,
    )
    summary = _summary(
        overall_signal, agreement, fund_missing, impact, portfolio_context
    )
    status = _status(technical, fundamental, sentiment, overall_signal)

    return {
        "overall_signal": overall_signal,
        "confidence": confidence,
        "portfolio_impact": impact,
        "summary": summary,
        "reasoning_chain": reasoning_chain,
        "sources": sources,
        "status": status,
    }


def _read_agent(result, fallback_name):
    if not isinstance(result, dict):
        return {
            "name": fallback_name,
            "signal": _INSUFFICIENT,
            "direction": _INSUFFICIENT,
            "confidence": 0.0,
            "reasoning": "{name} result was missing or malformed.".format(
                name=fallback_name.capitalize()
            ),
            "sources": [],
            "status": "DEGRADED",
        }

    name = result.get("agent") or fallback_name
    raw_signal = result.get("signal")
    direction = _DIRECTION.get(raw_signal, _INSUFFICIENT)
    confidence = _safe_confidence(result.get("confidence"))
    reasoning = result.get("reasoning")
    if not isinstance(reasoning, str) or not reasoning.strip():
        reasoning = "{name} Agent reported {signal}.".format(
            name=str(name).capitalize(),
            signal=raw_signal if raw_signal else "no signal",
        )
    sources = result.get("sources")
    if not isinstance(sources, list):
        sources = []
    status = result.get("status") or "DEGRADED"

    return {
        "name": name,
        "signal": raw_signal if isinstance(raw_signal, str) else _INSUFFICIENT,
        "direction": direction,
        "confidence": confidence,
        "reasoning": reasoning.strip(),
        "sources": sources,
        "status": status,
    }


def _safe_confidence(value):
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    if confidence != confidence:
        return 0.0
    return max(0.0, min(1.0, confidence))


def _overall_signal(bullish_votes, bearish_votes, technical, fundamental, sentiment):
    n_bull = len(bullish_votes)
    n_bear = len(bearish_votes)
    directions = {technical["direction"], fundamental["direction"], sentiment["direction"]}

    if directions <= {_INSUFFICIENT}:
        return _INSUFFICIENT, "none"
    if directions <= {_NEUTRAL, _INSUFFICIENT}:
        return _NEUTRAL, "neutral"

    if n_bull >= 2 and n_bull > n_bear:
        return _BULLISH, "agree" if n_bear == 0 else "majority"
    if n_bear >= 2 and n_bear > n_bull:
        return _BEARISH, "agree" if n_bull == 0 else "majority"
    if n_bull > 0 and n_bear > 0:
        return _NEUTRAL, "conflict"
    if n_bull == 1 and n_bear == 0:
        return _NEUTRAL, "weak"
    if n_bear == 1 and n_bull == 0:
        return _NEUTRAL, "weak"
    return _NEUTRAL, "conflict"


def _confidence(technical, fundamental, sentiment, agreement, fund_missing):
    values = [
        agent["confidence"]
        for agent in (technical, fundamental, sentiment)
        if agent["direction"] != _INSUFFICIENT
    ]
    if not values:
        return 0.0
    average = sum(values) / float(len(values))

    if agreement == "agree":
        factor = 0.90
    elif agreement == "majority":
        factor = 0.60
    elif agreement == "conflict":
        factor = 0.40
    elif agreement == "weak":
        factor = 0.45
    else:
        factor = 0.55

    if fund_missing:
        factor *= 0.75

    return round(min(_MAX_CONFIDENCE, average * factor), 2)


def _portfolio_impact(portfolio_context):
    if not isinstance(portfolio_context, dict):
        return "UNKNOWN"
    if "exposure_pct" not in portfolio_context:
        return "UNKNOWN"
    try:
        exposure = float(portfolio_context["exposure_pct"])
    except (TypeError, ValueError):
        return "UNKNOWN"
    if exposure != exposure:
        return "UNKNOWN"
    if exposure >= 40:
        return "HIGH"
    if exposure >= 20:
        return "MODERATE"
    return "LOW"


def _collect_sources(technical, fundamental, sentiment):
    sources = []
    for agent in (technical, fundamental, sentiment):
        for source in agent["sources"]:
            if isinstance(source, str) and source.strip() and source not in sources:
                sources.append(source)
    return sources


def _reasoning_chain(
    technical,
    fundamental,
    sentiment,
    overall_signal,
    agreement,
    fund_missing,
    portfolio_context,
    impact,
):
    chain = [
        "Technical Agent signal is {signal}. {reasoning}".format(
            signal=technical["signal"],
            reasoning=technical["reasoning"],
        ),
        "Fundamental Agent signal is {signal}. {reasoning}".format(
            signal=fundamental["signal"],
            reasoning=fundamental["reasoning"],
        ),
        "Sentiment Agent signal is {signal}. {reasoning}".format(
            signal=sentiment["signal"],
            reasoning=sentiment["reasoning"],
        ),
    ]

    if agreement == "agree":
        chain.append(
            "Two or more independent signals support a {signal} interpretation.".format(
                signal=overall_signal.lower()
            )
        )
    elif agreement == "majority":
        chain.append(
            "A majority of agents support {signal}, but at least one agent disagrees, "
            "so confidence is reduced.".format(signal=overall_signal.lower())
        )
    elif agreement == "conflict":
        chain.append(
            "Signals are split or strongly conflicting, so the overall view is NEUTRAL "
            "and confidence is reduced."
        )
    elif agreement == "weak":
        chain.append(
            "Only one directional signal was available, which is not enough for a "
            "strong overall call, so the view is NEUTRAL."
        )
    else:
        chain.append(
            "Available signals do not support a strong directional call."
        )

    if fund_missing:
        chain.append(
            "Fundamental evidence was unavailable, so that gap is called out and "
            "confidence is reduced."
        )

    chain.append(_portfolio_step(portfolio_context, impact))
    chain.append(
        "This is a synthesis of supplied agent outputs only. It is not investment "
        "advice and does not claim certainty or guaranteed returns."
    )
    return chain


def _portfolio_step(portfolio_context, impact):
    if impact == "UNKNOWN":
        return (
            "Portfolio context was not supplied, so portfolio impact is UNKNOWN."
        )
    stock = ""
    if isinstance(portfolio_context, dict):
        selected = portfolio_context.get("selected_stock")
        if isinstance(selected, str) and selected.strip():
            stock = " for {stock}".format(stock=selected.strip())
        exposure = portfolio_context.get("exposure_pct")
        risk = portfolio_context.get("risk_tolerance")
    else:
        exposure = None
        risk = None
    extra = ""
    if exposure is not None:
        extra += " Exposure is {pct}%.".format(pct=exposure)
    if isinstance(risk, str) and risk.strip():
        extra += " Stated risk tolerance is {risk}.".format(risk=risk.strip())
    return (
        "Portfolio exposure was considered when determining impact{stock}: "
        "portfolio_impact is {impact}.{extra}"
    ).format(stock=stock, impact=impact, extra=extra)


def _summary(overall_signal, agreement, fund_missing, impact, portfolio_context):
    parts = [
        "Overall signal is {signal} based only on the three agent outputs.".format(
            signal=overall_signal
        )
    ]
    if agreement == "conflict":
        parts.append("The agents do not agree, so confidence is reduced.")
    elif agreement == "majority":
        parts.append("There is partial disagreement, so confidence is reduced.")
    elif agreement == "agree":
        parts.append("Independent signals pointed in the same direction.")
    if fund_missing:
        parts.append("Fundamental evidence was unavailable.")
    parts.append("Portfolio impact is {impact}.".format(impact=impact))
    if isinstance(portfolio_context, dict):
        stock = portfolio_context.get("selected_stock")
        if isinstance(stock, str) and stock.strip():
            parts.append("Symbol considered: {stock}.".format(stock=stock.strip()))
    parts.append(
        "This view is uncertain and does not guarantee returns."
    )
    return " ".join(parts)


def _status(technical, fundamental, sentiment, overall_signal):
    if overall_signal == _INSUFFICIENT:
        return "DEGRADED"
    for agent in (technical, fundamental, sentiment):
        if agent["status"] != "OK":
            return "DEGRADED"
        if agent["direction"] == _INSUFFICIENT:
            return "DEGRADED"
    return "OK"

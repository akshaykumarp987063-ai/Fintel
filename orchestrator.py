"""Fintel hackathon MVP orchestrator — fully self-contained, offline, deterministic."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

logger = logging.getLogger(__name__)

STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_UNAVAILABLE = "UNAVAILABLE"

# ---------------------------------------------------------------------------
# Demo users
# ---------------------------------------------------------------------------
DEMO_USERS: dict[str, dict[str, Any]] = {
    "rahul": {
        "name": "Rahul",
        "risk_tolerance": "CONSERVATIVE",
        "portfolio": {"TCS": 0.40, "INFY": 0.30, "RELIANCE": 0.30},
    },
    "arjun": {
        "name": "Arjun",
        "risk_tolerance": "AGGRESSIVE",
        "portfolio": {"TCS": 0.10, "INFY": 0.10, "RELIANCE": 0.20, "CASH": 0.60},
    },
}

# ---------------------------------------------------------------------------
# Demo market data (SIMULATED — no live API)
# ---------------------------------------------------------------------------
DEMO_MARKET_DATA: dict[str, dict[str, Any]] = {
    "TCS": {
        "symbol": "TCS",
        "price": 3412.0,
        "change_pct": -2.8,
        "volume_ratio": 2.1,
        "sentiment_score": -0.72,
        "source_type": "SIMULATED",
    },
    "INFY": {
        "symbol": "INFY",
        "price": 1585.0,
        "change_pct": -1.4,
        "volume_ratio": 1.5,
        "sentiment_score": -0.45,
        "source_type": "SIMULATED",
    },
    "RELIANCE": {
        "symbol": "RELIANCE",
        "price": 2890.0,
        "change_pct": 0.6,
        "volume_ratio": 0.9,
        "sentiment_score": 0.15,
        "source_type": "SIMULATED",
    },
}

# ---------------------------------------------------------------------------
# Demo document corpus (in-memory RAG)
# ---------------------------------------------------------------------------
DEMO_DOCUMENT_CORPUS: list[dict[str, Any]] = [
    {
        "symbol": "TCS",
        "title": "TCS Quarterly Financial Disclosure",
        "source": "TCS_Q2_Filing.txt",
        "text": (
            "TCS reported slower revenue growth this quarter amid weaker discretionary "
            "spending from enterprise clients. Operating margins faced pressure due to "
            "wage hikes and subcontracting costs. Management cited a mixed demand outlook "
            "with strength in BFSI offset by softness in retail and manufacturing verticals."
        ),
        "keywords": ["tcs", "revenue", "growth", "margin", "discretionary", "demand", "quarterly"],
    },
    {
        "symbol": "TCS",
        "title": "TCS Sector Commentary",
        "source": "TCS_Sector_Note.txt",
        "text": (
            "IT services peers are navigating elongated deal cycles. TCS deal pipeline "
            "remains healthy but conversion timelines have extended, creating near-term "
            "revenue recognition headwinds."
        ),
        "keywords": ["tcs", "deal", "pipeline", "revenue", "it services"],
    },
    {
        "symbol": "INFY",
        "title": "Infosys Quarterly Financial Disclosure",
        "source": "INFY_Q2_Filing.txt",
        "text": (
            "Infosys delivered modest revenue growth but noted margin compression from "
            "investments in generative AI capabilities. Client spending on discretionary "
            "projects remains cautious. Large-deal wins provide medium-term visibility "
            "but near-term growth is uneven."
        ),
        "keywords": ["infy", "infosys", "revenue", "margin", "growth", "discretionary"],
    },
    {
        "symbol": "INFY",
        "title": "Infosys Client Spending Outlook",
        "source": "INFY_Outlook.txt",
        "text": (
            "Management highlighted stabilizing demand in financial services while "
            "retail and communications clients continue to defer non-critical spend."
        ),
        "keywords": ["infosys", "demand", "spending", "clients"],
    },
    {
        "symbol": "RELIANCE",
        "title": "Reliance Industries Quarterly Disclosure",
        "source": "RELIANCE_Q2_Filing.txt",
        "text": (
            "Reliance reported steady refining margins and resilient retail footfall. "
            "Jio subscriber additions remained strong. New energy investments continue "
            "to weigh on consolidated margins but support long-term diversification."
        ),
        "keywords": ["reliance", "retail", "jio", "margins", "revenue", "energy"],
    },
    {
        "symbol": "RELIANCE",
        "title": "Reliance Sector Analysis",
        "source": "RELIANCE_Sector_Note.txt",
        "text": (
            "Conglomerate diversification provides earnings stability. O2C segment "
            "benefited from improved crack spreads while digital services sustained "
            "double-digit growth."
        ),
        "keywords": ["reliance", "o2c", "digital", "growth", "earnings"],
    },
]


def get_user_profile(user_id: str) -> dict[str, Any] | None:
    return DEMO_USERS.get(user_id)


def get_market_data(symbol: str) -> dict[str, Any]:
    data = DEMO_MARKET_DATA.get(symbol.upper())
    if data:
        return dict(data)
    return {
        "symbol": symbol.upper(),
        "price": 0.0,
        "change_pct": 0.0,
        "volume_ratio": 1.0,
        "sentiment_score": 0.0,
        "source_type": "SIMULATED",
    }


def retrieve_documents(query: str, symbol: str, top_k: int = 2) -> list[dict[str, Any]]:
    """Keyword-based in-memory retrieval (demo RAG — no embeddings)."""
    symbol = symbol.upper()
    query_tokens = set(query.lower().split())

    scored: list[tuple[float, dict[str, Any]]] = []
    for doc in DEMO_DOCUMENT_CORPUS:
        if doc["symbol"] != symbol:
            continue
        doc_tokens = set(doc["keywords"]) | set(doc["text"].lower().split())
        overlap = len(query_tokens & doc_tokens)
        symbol_bonus = 2.0 if symbol.lower() in query.lower() else 0.0
        score = round(min(0.99, 0.55 + overlap * 0.08 + symbol_bonus * 0.1), 2)
        if overlap > 0 or symbol_bonus > 0:
            scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, doc in scored[:top_k]:
        results.append({
            "title": doc["source"],
            "text": doc["text"],
            "score": score,
            "display_title": doc["title"],
        })
    return results


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------
def technical_agent(market_data: dict[str, Any]) -> dict[str, Any]:
    change_pct = market_data.get("change_pct", 0.0)
    volume_ratio = market_data.get("volume_ratio", 1.0)
    symbol = market_data.get("symbol", "UNKNOWN")

    if change_pct > 1:
        momentum = "BULLISH"
    elif change_pct < -1:
        momentum = "BEARISH"
    else:
        momentum = "NEUTRAL"

    if volume_ratio > 2:
        volume_label = "ANOMALY"
    elif volume_ratio > 1.2:
        volume_label = "ELEVATED"
    else:
        volume_label = "NORMAL"

    confidence = 0.82 if momentum != "NEUTRAL" else 0.55
    if volume_label == "ANOMALY":
        confidence = min(0.92, confidence + 0.08)

    return {
        "agent": "technical",
        "signal": momentum,
        "confidence": round(confidence, 2),
        "reasoning": (
            f"{symbol} price change is {change_pct:+.1f}% (momentum: {momentum}). "
            f"Volume is {volume_ratio:.1f}x normal ({volume_label})."
        ),
        "evidence": [
            {"change_pct": change_pct, "volume_ratio": volume_ratio, "volume_label": volume_label},
        ],
        "sources": [],
        "status": STATUS_OK,
        "dimensions": {"momentum": momentum, "volume": volume_label},
    }


def fundamental_agent(
    market_data: dict[str, Any],
    documents: list[dict[str, Any]],
) -> dict[str, Any]:
    symbol = market_data.get("symbol", "UNKNOWN")

    if not documents:
        return {
            "agent": "fundamental",
            "signal": "INSUFFICIENT_EVIDENCE",
            "confidence": 0.0,
            "reasoning": f"No financial filings retrieved for {symbol}. Cannot assess fundamentals.",
            "evidence": [],
            "sources": [],
            "status": STATUS_DEGRADED,
        }

    combined_text = " ".join(doc["text"].lower() for doc in documents)
    bearish_terms = ["slower", "weaker", "pressure", "compression", "cautious", "defer", "headwind"]
    bullish_terms = ["strong", "resilient", "steady", "healthy", "growth", "stability"]

    bearish_hits = sum(1 for t in bearish_terms if t in combined_text)
    bullish_hits = sum(1 for t in bullish_terms if t in combined_text)

    if bearish_hits > bullish_hits:
        signal = "BEARISH"
        confidence = min(0.88, 0.65 + bearish_hits * 0.05)
        outlook = "challenging fundamentals"
    elif bullish_hits > bearish_hits:
        signal = "BULLISH"
        confidence = min(0.88, 0.65 + bullish_hits * 0.05)
        outlook = "supportive fundamentals"
    else:
        signal = "NEUTRAL"
        confidence = 0.60
        outlook = "mixed fundamentals"

    sources = [doc["title"] for doc in documents]
    primary = documents[0]["title"]

    return {
        "agent": "fundamental",
        "signal": signal,
        "confidence": round(confidence, 2),
        "reasoning": (
            f"Retrieved financial evidence ({primary}) indicates {outlook} for {symbol}. "
            f"Cited {len(documents)} simulated filing(s)."
        ),
        "evidence": [{"title": doc["title"], "score": doc["score"]} for doc in documents],
        "sources": sources,
        "status": STATUS_OK,
    }


def sentiment_agent(market_data: dict[str, Any]) -> dict[str, Any]:
    score = market_data.get("sentiment_score", 0.0)
    symbol = market_data.get("symbol", "UNKNOWN")

    if score > 0.3:
        signal = "POSITIVE"
        normalized = "BULLISH"
    elif score < -0.3:
        signal = "NEGATIVE"
        normalized = "BEARISH"
    else:
        signal = "NEUTRAL"
        normalized = "NEUTRAL"

    confidence = min(0.90, 0.60 + abs(score) * 0.35)

    return {
        "agent": "sentiment",
        "signal": signal,
        "normalized_signal": normalized,
        "confidence": round(confidence, 2),
        "reasoning": (
            f"Simulated sentiment score for {symbol} is {score:+.2f} ({signal})."
        ),
        "evidence": [{"sentiment_score": score}],
        "sources": [],
        "status": STATUS_OK,
        "dimensions": {"sentiment": signal},
    }


def _normalize_agent_signal(agent_result: dict[str, Any]) -> str | None:
    signal = agent_result.get("signal", "")
    if signal in ("BULLISH", "BEARISH", "NEUTRAL"):
        return signal
    if signal == "POSITIVE":
        return "BULLISH"
    if signal == "NEGATIVE":
        return "BEARISH"
    if signal == "NEUTRAL":
        return "NEUTRAL"
    return None


def synthesis_agent(
    technical: dict[str, Any],
    fundamental: dict[str, Any],
    sentiment: dict[str, Any],
    portfolio: dict[str, Any],
) -> dict[str, Any]:
    agents = [technical, fundamental, sentiment]
    normalized = []
    confidences = []

    for agent in agents:
        norm = _normalize_agent_signal(agent)
        if norm and agent.get("signal") != "INSUFFICIENT_EVIDENCE":
            normalized.append(norm)
            confidences.append(agent.get("confidence", 0.0))

    has_conflict = len(set(normalized)) > 1 if normalized else False

    if not normalized:
        overall = "NEUTRAL"
        confidence = 0.0
    else:
        bullish = normalized.count("BULLISH")
        bearish = normalized.count("BEARISH")
        if bullish > bearish:
            overall = "BULLISH"
        elif bearish > bullish:
            overall = "BEARISH"
        else:
            overall = "NEUTRAL"

        confidence = round(sum(confidences) / len(confidences), 2)
        if has_conflict:
            confidence = round(confidence * 0.65, 2)
        elif len(set(normalized)) == 1 and normalized[0] != "NEUTRAL":
            confidence = round(min(0.92, confidence + 0.08), 2)

    symbol = portfolio.get("symbol", "")
    user_name = portfolio.get("user_name", "Investor")

    conflict_note = " Signal conflict detected." if has_conflict else ""
    summary = (
        f"Simulated analysis for {symbol}: overall {overall} view with "
        f"{confidence:.0%} confidence.{conflict_note} "
        f"This is illustrative intelligence for {user_name}'s portfolio — not investment advice."
    )

    sources: list[dict[str, str]] = []
    for agent in agents:
        for src in agent.get("sources", []):
            if src:
                sources.append({"type": agent["agent"], "label": src})

    return {
        "overall_signal": overall,
        "confidence": confidence,
        "summary": summary,
        "has_conflict": has_conflict,
        "sources": sources,
    }


def calculate_portfolio_impact(
    user_profile: dict[str, Any],
    symbol: str,
    market_data: dict[str, Any],
    overall_signal: str,
) -> dict[str, Any]:
    portfolio = user_profile.get("portfolio", {})
    exposure = portfolio.get(symbol.upper(), 0.0)
    change_pct = market_data.get("change_pct", 0.0)
    direct_impact_pct = round(exposure * change_pct, 2)

    if exposure >= 0.40:
        classification = "HIGH"
    elif exposure >= 0.20:
        classification = "MODERATE"
    else:
        classification = "LOW"

    return {
        "user": user_profile.get("name", "Unknown"),
        "risk_tolerance": user_profile.get("risk_tolerance", "UNKNOWN"),
        "exposure": exposure,
        "direct_impact_pct": direct_impact_pct,
        "classification": classification,
        "overall_signal": overall_signal,
        "symbol": symbol.upper(),
    }


def _build_reasoning_chain(
    market_data: dict[str, Any],
    documents: list[dict[str, Any]],
    technical: dict[str, Any],
    fundamental: dict[str, Any],
    sentiment: dict[str, Any],
    portfolio_impact: dict[str, Any],
    synthesis: dict[str, Any],
) -> list[str]:
    symbol = market_data.get("symbol", "UNKNOWN")
    change = market_data.get("change_pct", 0.0)
    volume_ratio = market_data.get("volume_ratio", 1.0)
    chain: list[str] = []

    chain.append(f"{symbol} price changed by {change:+.1f}% (simulated market data).")
    chain.append(f"Trading volume is {volume_ratio:.1f}x normal.")

    if documents:
        chain.append(
            f"Retrieved financial evidence ({documents[0]['title']}) indicates "
            f"{fundamental.get('reasoning', 'fundamental factors to review').split(' indicates ')[-1]}"
            if " indicates " in fundamental.get("reasoning", "")
            else f"Retrieved financial evidence from {documents[0]['title']}."
        )
    elif fundamental.get("signal") == "INSUFFICIENT_EVIDENCE":
        chain.append("No financial filings were available; fundamental analysis is degraded.")

    chain.append(f"Sentiment signal is {sentiment.get('signal', 'NEUTRAL').lower()}.")

    exposure_pct = portfolio_impact.get("exposure", 0.0) * 100
    user = portfolio_impact.get("user", "Investor")
    chain.append(f"{symbol} represents {exposure_pct:.0f}% of {user}'s portfolio.")

    chain.append(
        f"Estimated direct portfolio impact: {portfolio_impact.get('direct_impact_pct', 0):+.2f}% "
        f"— classified as {portfolio_impact.get('classification', 'LOW')}."
    )

    if synthesis.get("has_conflict"):
        chain.append("Signal conflict detected across agents; confidence was reduced.")

    chain.append(
        f"Overall synthesized signal: {synthesis.get('overall_signal', 'NEUTRAL')} "
        f"at {synthesis.get('confidence', 0):.0%} confidence."
    )

    return chain


def _apply_conflict_override(
    technical: dict[str, Any],
    fundamental: dict[str, Any],
    sentiment: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Force deterministic disagreement for demo mode."""
    technical = dict(technical)
    fundamental = dict(fundamental)
    sentiment = dict(sentiment)

    technical["signal"] = "BULLISH"
    technical["confidence"] = 0.85
    technical["reasoning"] = (
        "[DEMO OVERRIDE] Forced BULLISH technical signal to demonstrate agent conflict."
    )

    fundamental["signal"] = "BEARISH"
    fundamental["confidence"] = 0.80
    fundamental["reasoning"] = (
        "[DEMO OVERRIDE] Forced BEARISH fundamental signal to demonstrate agent conflict."
    )

    sentiment["signal"] = "NEGATIVE"
    sentiment["normalized_signal"] = "BEARISH"
    sentiment["confidence"] = 0.78
    sentiment["reasoning"] = (
        "[DEMO OVERRIDE] Forced NEGATIVE sentiment to demonstrate agent conflict."
    )

    return technical, fundamental, sentiment


def _empty_result(summary: str, status: str = "error") -> dict[str, Any]:
    return {
        "overall_signal": None,
        "confidence": 0.0,
        "portfolio_impact": {},
        "summary": summary,
        "reasoning_chain": [],
        "sources": [],
        "agents": {},
        "market_data": {},
        "signal_dimensions": {},
        "metrics": {
            "latency_seconds": 0.0,
            "signal_confidence": 0.0,
            "portfolio_concentration": 0.0,
            "agents_completed": 0,
            "sources_retrieved": 0,
        },
        "status": status,
    }


def analyze_market_event(
    symbol: str,
    user_id: str,
    simulate_missing_filing: bool = False,
    simulate_agent_conflict: bool = False,
) -> dict[str, Any]:
    """Run the full Fintel analysis pipeline."""
    start = time.perf_counter()

    try:
        if not symbol:
            return _empty_result("No symbol provided.")

        user_profile = get_user_profile(user_id)
        if not user_profile:
            return _empty_result(f"Unknown investor: {user_id}.")

        symbol = symbol.upper()
        market_data = get_market_data(symbol)

        query = f"{symbol} quarterly financial disclosure revenue margin growth"
        documents = [] if simulate_missing_filing else retrieve_documents(query, symbol, top_k=2)

        # Run agents in parallel
        technical: dict[str, Any] = {}
        fundamental: dict[str, Any] = {}
        sentiment: dict[str, Any] = {}

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(technical_agent, market_data): "technical",
                executor.submit(fundamental_agent, market_data, documents): "fundamental",
                executor.submit(sentiment_agent, market_data): "sentiment",
            }
            for future in as_completed(futures):
                name = futures[future]
                try:
                    result = future.result()
                    if name == "technical":
                        technical = result
                    elif name == "fundamental":
                        fundamental = result
                    else:
                        sentiment = result
                except Exception:
                    logger.exception("Agent %s failed", name)
                    fallback = {
                        "agent": name,
                        "signal": "NEUTRAL",
                        "confidence": 0.0,
                        "reasoning": f"{name} agent encountered an error.",
                        "evidence": [],
                        "sources": [],
                        "status": STATUS_UNAVAILABLE,
                    }
                    if name == "technical":
                        technical = fallback
                    elif name == "fundamental":
                        fundamental = fallback
                    else:
                        sentiment = fallback

        if simulate_agent_conflict:
            technical, fundamental, sentiment = _apply_conflict_override(
                technical, fundamental, sentiment
            )

        portfolio_ctx = {
            "symbol": symbol,
            "user_name": user_profile["name"],
            "portfolio": user_profile["portfolio"],
        }
        synthesis = synthesis_agent(technical, fundamental, sentiment, portfolio_ctx)
        portfolio_impact = calculate_portfolio_impact(
            user_profile, symbol, market_data, synthesis["overall_signal"]
        )

        reasoning_chain = _build_reasoning_chain(
            market_data, documents, technical, fundamental, sentiment,
            portfolio_impact, synthesis,
        )

        sources: list[dict[str, str]] = [
            {"type": "market_data", "label": f"Simulated quote — {symbol}"},
        ]
        for doc in documents:
            sources.append({"type": "rag", "label": doc["title"]})
        for agent in (technical, fundamental, sentiment):
            for src in agent.get("sources", []):
                entry = {"type": agent["agent"], "label": src}
                if entry not in sources:
                    sources.append(entry)

        agents_completed = sum(
            1 for a in (technical, fundamental, sentiment)
            if a.get("status") in (STATUS_OK, STATUS_DEGRADED)
        )

        latency = round(time.perf_counter() - start, 3)
        pipeline_status = "success"
        if simulate_missing_filing or fundamental.get("status") == STATUS_DEGRADED:
            pipeline_status = "success"  # degraded but running
        if any(a.get("status") == STATUS_UNAVAILABLE for a in (technical, fundamental, sentiment)):
            pipeline_status = "degraded"

        signal_dimensions = {
            "momentum": technical.get("dimensions", {}).get("momentum", technical.get("signal")),
            "volume": technical.get("dimensions", {}).get("volume", "NORMAL"),
            "sentiment": sentiment.get("dimensions", {}).get("sentiment", sentiment.get("signal")),
        }

        return {
            "overall_signal": synthesis["overall_signal"],
            "confidence": synthesis["confidence"],
            "portfolio_impact": {
                "classification": portfolio_impact["classification"],
                "exposure": portfolio_impact["exposure"],
                "direct_impact_pct": portfolio_impact["direct_impact_pct"],
                "user": portfolio_impact["user"],
                "risk_tolerance": portfolio_impact["risk_tolerance"],
            },
            "summary": synthesis["summary"],
            "reasoning_chain": reasoning_chain,
            "sources": sources,
            "agents": {
                "technical": technical,
                "fundamental": fundamental,
                "sentiment": sentiment,
            },
            "market_data": market_data,
            "signal_dimensions": signal_dimensions,
            "metrics": {
                "latency_seconds": latency,
                "signal_confidence": synthesis["confidence"],
                "portfolio_concentration": portfolio_impact["exposure"],
                "agents_completed": agents_completed,
                "sources_retrieved": len(documents),
            },
            "status": pipeline_status,
        }

    except Exception as exc:
        logger.exception("Pipeline failed")
        result = _empty_result(f"Analysis failed: {exc}")
        result["metrics"]["latency_seconds"] = round(time.perf_counter() - start, 3)
        return result

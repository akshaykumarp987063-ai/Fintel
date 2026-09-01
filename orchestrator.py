"""Fintel hackathon MVP orchestrator — live data with offline demo fallback."""

from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_UNAVAILABLE = "UNAVAILABLE"

SUPPORTED_SYMBOLS = frozenset({"TCS", "INFY", "RELIANCE"})
YAHOO_TICKERS = {"TCS": "TCS.NS", "INFY": "INFY.NS", "RELIANCE": "RELIANCE.NS"}
LIVE_PROVIDER_NAME = "yfinance"
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "").strip()
LIVE_FETCH_TIMEOUT_SECONDS = 6

# In-memory cache of last successful live fetches (symbol -> record)
_MARKET_CACHE: dict[str, dict[str, Any]] = {}

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
# Demo market data (SIMULATED — offline fallback)
# ---------------------------------------------------------------------------
DEMO_MARKET_DATA: dict[str, dict[str, Any]] = {
    "TCS": {
        "symbol": "TCS",
        "price": 3412.0,
        "change_pct": -2.8,
        "volume": 2_905_846,
        "volume_ratio": 2.1,
        "sentiment_score": -0.72,
        "source_type": "SIMULATED",
        "data_status": "SIMULATED",
        "provider": "demo",
        "data_timestamp": "2026-01-01T00:00:00+00:00",
    },
    "INFY": {
        "symbol": "INFY",
        "price": 1585.0,
        "change_pct": -1.4,
        "volume": 4_120_000,
        "volume_ratio": 1.5,
        "sentiment_score": -0.45,
        "source_type": "SIMULATED",
        "data_status": "SIMULATED",
        "provider": "demo",
        "data_timestamp": "2026-01-01T00:00:00+00:00",
    },
    "RELIANCE": {
        "symbol": "RELIANCE",
        "price": 2890.0,
        "change_pct": 0.6,
        "volume": 8_500_000,
        "volume_ratio": 0.9,
        "sentiment_score": 0.15,
        "source_type": "SIMULATED",
        "data_status": "SIMULATED",
        "provider": "demo",
        "data_timestamp": "2026-01-01T00:00:00+00:00",
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


# ---------------------------------------------------------------------------
# Market data provider abstraction
# ---------------------------------------------------------------------------
class MarketDataProvider(ABC):
    @abstractmethod
    def fetch(self, symbol: str) -> dict[str, Any] | None:
        """Return a normalized market record or None if unavailable."""


class LiveMarketDataProvider(MarketDataProvider):
    """Fetches near-current quotes via yfinance (NSE symbols)."""

    def fetch(self, symbol: str) -> dict[str, Any] | None:
        import yfinance as yf

        ticker_symbol = YAHOO_TICKERS.get(symbol)
        if not ticker_symbol:
            return None

        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info or {}

        price = info.get("regularMarketPrice") or info.get("currentPrice")
        if price is None:
            history = ticker.history(period="1d")
            if history is not None and not history.empty:
                price = float(history["Close"].iloc[-1])

        if price is None:
            return None

        change_pct = info.get("regularMarketChangePercent")
        if change_pct is None:
            prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
            if prev_close:
                change_pct = ((float(price) - float(prev_close)) / float(prev_close)) * 100

        volume = info.get("regularMarketVolume") or info.get("volume")
        history = ticker.history(period="10d")
        volume_ratio = _compute_volume_ratio(history)
        data_timestamp = _extract_data_timestamp(history, info)

        return {
            "symbol": symbol,
            "price": round(float(price), 2),
            "change_pct": round(float(change_pct), 2) if change_pct is not None else None,
            "volume": int(volume) if volume is not None else None,
            "volume_ratio": volume_ratio,
            "data_timestamp": data_timestamp,
            "source_type": "LIVE",
            "data_status": "LIVE",
            "provider": LIVE_PROVIDER_NAME,
        }


class FallbackMarketDataProvider(MarketDataProvider):
    """Deterministic demo quotes — works fully offline."""

    def fetch(self, symbol: str) -> dict[str, Any] | None:
        data = DEMO_MARKET_DATA.get(symbol)
        if not data:
            return None
        record = dict(data)
        record["data_status"] = "SIMULATED"
        record["source_type"] = "SIMULATED"
        return record


def _compute_volume_ratio(history: Any) -> float | None:
    if history is None or getattr(history, "empty", True):
        return None
    if len(history) < 2:
        return None

    today_volume = history["Volume"].iloc[-1]
    prior_volumes = history["Volume"].iloc[:-1]
    if prior_volumes.empty:
        return None

    avg_volume = float(prior_volumes.mean())
    if avg_volume <= 0:
        return None

    return round(float(today_volume) / avg_volume, 2)


def _extract_data_timestamp(history: Any, info: dict[str, Any]) -> str:
    if history is not None and not getattr(history, "empty", True):
        ts = history.index[-1]
        if hasattr(ts, "to_pydatetime"):
            ts = ts.to_pydatetime()
        if getattr(ts, "tzinfo", None) is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc).isoformat()

    market_time = info.get("regularMarketTime")
    if market_time:
        return datetime.fromtimestamp(int(market_time), tz=timezone.utc).isoformat()

    return datetime.now(timezone.utc).isoformat()


def _attach_sentiment(market_data: dict[str, Any]) -> dict[str, Any]:
    """Add sentiment score without blocking the core pipeline."""
    symbol = market_data.get("symbol", "")
    news = _fetch_news_sentiment(symbol)
    if news is not None:
        market_data["sentiment_score"] = news["score"]
        market_data["sentiment_source"] = news["source"]
        market_data["sentiment_headline"] = news.get("headline")
        return market_data

    demo = DEMO_MARKET_DATA.get(symbol, {})
    market_data["sentiment_score"] = demo.get("sentiment_score", 0.0)
    market_data["sentiment_source"] = "DETERMINISTIC_FALLBACK"
    market_data["sentiment_headline"] = None
    return market_data


def _fetch_news_sentiment(symbol: str) -> dict[str, Any] | None:
    if not NEWS_API_KEY:
        return None

    company_names = {
        "TCS": "Tata Consultancy Services",
        "INFY": "Infosys",
        "RELIANCE": "Reliance Industries",
    }
    query = company_names.get(symbol, symbol)
    params = urlencode(
        {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 5,
            "apiKey": NEWS_API_KEY,
        }
    )
    url = f"https://newsapi.org/v2/everything?{params}"

    try:
        request = Request(url, headers={"User-Agent": "Fintel/1.0"})
        with urlopen(request, timeout=8) as response:
            payload = response.read().decode("utf-8")
        import json

        data = json.loads(payload)
        if data.get("status") != "ok":
            return None

        articles = data.get("articles") or []
        if not articles:
            return None

        bearish_terms = ["fall", "drop", "decline", "miss", "weak", "cut", "loss", "down"]
        bullish_terms = ["rise", "gain", "beat", "strong", "growth", "up", "surge", "record"]
        score = 0.0
        headline = articles[0].get("title", "")

        for article in articles[:5]:
            title = (article.get("title") or "").lower()
            score += sum(0.15 for term in bullish_terms if term in title)
            score -= sum(0.15 for term in bearish_terms if term in title)

        score = max(-1.0, min(1.0, round(score, 2)))
        return {"score": score, "source": "NEWS_API", "headline": headline}
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        logger.warning("News API unavailable for %s: %s", symbol, exc)
        return None


def _fetch_live_record(symbol: str) -> dict[str, Any] | None:
    """Attempt a live fetch with a hard timeout so offline demo mode stays fast."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(LiveMarketDataProvider().fetch, symbol)
        try:
            return future.result(timeout=LIVE_FETCH_TIMEOUT_SECONDS)
        except Exception as exc:
            logger.warning("Live market fetch timed out or failed for %s: %s", symbol, exc)
            return None


def get_live_market_data(symbol: str, force_refresh: bool = False) -> dict[str, Any]:
    """
    Live → cached → demo fallback chain.

    Returns a normalized market record with data_status of LIVE, CACHED, or SIMULATED.
    """
    symbol = symbol.upper().strip()
    if not symbol:
        return _market_error("No symbol provided.")
    if symbol not in SUPPORTED_SYMBOLS:
        return _market_error(f"Unsupported symbol: {symbol}. Supported: TCS, INFY, RELIANCE.")

    _ = force_refresh  # reserved for explicit refresh semantics; always attempts live first

    live_api_attempted = True
    try:
        live_record = _fetch_live_record(symbol)
        if live_record and live_record.get("price") is not None:
            live_record = _attach_sentiment(live_record)
            _MARKET_CACHE[symbol] = dict(live_record)
            live_record["live_api_attempted"] = True
            live_record["live_api_success"] = True
            return live_record
    except Exception as exc:
        logger.warning("Live market fetch failed for %s: %s", symbol, exc)

    if symbol in _MARKET_CACHE:
        cached = dict(_MARKET_CACHE[symbol])
        cached["data_status"] = "CACHED"
        cached["source_type"] = "CACHED"
        cached["provider"] = cached.get("provider", LIVE_PROVIDER_NAME)
        cached["live_api_attempted"] = live_api_attempted
        cached["live_api_success"] = False
        return cached

    fallback = FallbackMarketDataProvider().fetch(symbol)
    if fallback:
        fallback = _attach_sentiment(fallback)
        fallback["live_api_attempted"] = live_api_attempted
        fallback["live_api_success"] = False
        return fallback

    return _market_error(f"No market data available for {symbol}.")


def _market_error(message: str) -> dict[str, Any]:
    return {
        "symbol": "",
        "price": None,
        "change_pct": None,
        "volume": None,
        "volume_ratio": None,
        "data_timestamp": None,
        "source_type": "UNAVAILABLE",
        "data_status": "UNAVAILABLE",
        "provider": None,
        "error": message,
        "live_api_attempted": False,
        "live_api_success": False,
    }


def get_market_data(symbol: str, force_refresh: bool = False) -> dict[str, Any]:
    """Backward-compatible entry point used by the analysis pipeline."""
    return get_live_market_data(symbol, force_refresh=force_refresh)


def get_user_profile(user_id: str) -> dict[str, Any] | None:
    return DEMO_USERS.get(user_id)


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
            "source": doc["source"],
        })
    return results


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------
def technical_agent(market_data: dict[str, Any]) -> dict[str, Any]:
    change_pct = market_data.get("change_pct")
    volume_ratio = market_data.get("volume_ratio")
    symbol = market_data.get("symbol", "UNKNOWN")
    data_status = market_data.get("data_status", "SIMULATED")

    if change_pct is None:
        change_pct = 0.0
    if change_pct > 1:
        momentum = "BULLISH"
    elif change_pct < -1:
        momentum = "BEARISH"
    else:
        momentum = "NEUTRAL"

    if volume_ratio is None:
        volume_label = "Volume anomaly unavailable"
    elif volume_ratio > 2:
        volume_label = "ANOMALY"
    elif volume_ratio > 1.2:
        volume_label = "ELEVATED"
    else:
        volume_label = "NORMAL"

    confidence = 0.82 if momentum != "NEUTRAL" else 0.55
    if volume_ratio is not None and volume_ratio > 2:
        confidence = min(0.92, confidence + 0.08)

    status_label = data_status.lower()
    if volume_ratio is None:
        volume_reason = "Volume anomaly unavailable — insufficient historical data."
    else:
        volume_reason = f"Volume is {volume_ratio:.1f}x recent average ({volume_label})."

    return {
        "agent": "technical",
        "signal": momentum,
        "confidence": round(confidence, 2),
        "reasoning": (
            f"{symbol} price change is {change_pct:+.1f}% (momentum: {momentum}) "
            f"using {status_label} market data. {volume_reason}"
        ),
        "evidence": [
            {
                "change_pct": change_pct,
                "volume_ratio": volume_ratio,
                "volume_label": volume_label,
                "data_status": data_status,
            },
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
            f"Cited {len(documents)} filing(s) from the demo corpus."
        ),
        "evidence": [
            {"title": doc["title"], "text": doc["text"], "score": doc["score"], "source": doc["source"]}
            for doc in documents
        ],
        "sources": sources,
        "status": STATUS_OK,
    }


def sentiment_agent(market_data: dict[str, Any]) -> dict[str, Any]:
    score = market_data.get("sentiment_score", 0.0)
    symbol = market_data.get("symbol", "UNKNOWN")
    sentiment_source = market_data.get("sentiment_source", "DETERMINISTIC_FALLBACK")
    headline = market_data.get("sentiment_headline")

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

    source_labels = {
        "NEWS_API": "live news headlines",
        "DETERMINISTIC_FALLBACK": "deterministic demo fallback",
        "SIMULATED": "simulated demo sentiment",
    }
    source_label = source_labels.get(sentiment_source, sentiment_source.lower())

    reasoning = f"Sentiment score for {symbol} is {score:+.2f} ({signal}) from {source_label}."
    if headline and sentiment_source == "NEWS_API":
        reasoning += f' Latest headline: "{headline}".'

    return {
        "agent": "sentiment",
        "signal": signal,
        "normalized_signal": normalized,
        "confidence": round(confidence, 2),
        "reasoning": reasoning,
        "evidence": [{"sentiment_score": score, "source": sentiment_source}],
        "sources": [sentiment_source] if sentiment_source else [],
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
    market_data: dict[str, Any],
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
    data_status = market_data.get("data_status", "SIMULATED")

    conflict_note = " Signal conflict detected." if has_conflict else ""
    summary = (
        f"Market intelligence for {symbol} ({data_status} data): overall {overall} signal with "
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
    change_pct = market_data.get("change_pct")
    if change_pct is None:
        change_pct = 0.0
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
    change = market_data.get("change_pct")
    volume_ratio = market_data.get("volume_ratio")
    data_status = market_data.get("data_status", "SIMULATED")
    provider = market_data.get("provider", "unknown")
    chain: list[str] = []

    if change is not None:
        chain.append(
            f"[LIVE MARKET OBSERVATION] {symbol} price changed by {change:+.1f}% "
            f"({data_status} data via {provider})."
        )
    else:
        chain.append(
            f"[LIVE MARKET OBSERVATION] {symbol} price change unavailable ({data_status} data)."
        )

    if volume_ratio is not None:
        chain.append(
            f"[LIVE MARKET OBSERVATION] Trading volume is {volume_ratio:.1f}x recent average."
        )
    else:
        chain.append("[LIVE MARKET OBSERVATION] Volume anomaly unavailable — insufficient history.")

    if documents:
        chain.append(
            f"[FINANCIAL EVIDENCE] Retrieved {documents[0]['title']} "
            f"(relevance {documents[0]['score']:.0%}) — "
            f"{fundamental.get('reasoning', 'fundamental factors to review')}"
        )
    elif fundamental.get("signal") == "INSUFFICIENT_EVIDENCE":
        chain.append(
            "[FINANCIAL EVIDENCE] No financial filings were available; fundamental analysis is degraded."
        )

    chain.append(
        f"[SENTIMENT SIGNAL] {sentiment.get('reasoning', 'Sentiment signal unavailable.')}"
    )

    exposure_pct = portfolio_impact.get("exposure", 0.0) * 100
    user = portfolio_impact.get("user", "Investor")
    chain.append(
        f"[USER PORTFOLIO EXPOSURE] {symbol} represents {exposure_pct:.0f}% of {user}'s portfolio."
    )

    chain.append(
        f"[FINAL IMPACT] Estimated direct portfolio impact: "
        f"{portfolio_impact.get('direct_impact_pct', 0):+.2f}% "
        f"— classified as {portfolio_impact.get('classification', 'LOW')}."
    )

    if synthesis.get("has_conflict"):
        chain.append(
            "[FINAL IMPACT] Signal conflict detected across agents; confidence was reduced."
        )

    chain.append(
        f"[FINAL IMPACT] Overall synthesized signal: {synthesis.get('overall_signal', 'NEUTRAL')} "
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
        "retrieved_evidence": [],
        "agents": {},
        "market_data": {},
        "signal_dimensions": {},
        "metrics": {
            "latency_seconds": 0.0,
            "signal_confidence": 0.0,
            "portfolio_concentration": 0.0,
            "agents_completed": 0,
            "sources_retrieved": 0,
            "market_data_source": "UNAVAILABLE",
            "data_freshness": None,
            "live_api_success": False,
        },
        "status": status,
    }


def _market_data_label(market_data: dict[str, Any]) -> str:
    status = market_data.get("data_status", "SIMULATED")
    provider = market_data.get("provider", "unknown")
    symbol = market_data.get("symbol", "")
    if status == "LIVE":
        return f"Live quote — {symbol} ({provider})"
    if status == "CACHED":
        return f"Cached quote — {symbol} ({provider})"
    return f"Simulated demo quote — {symbol}"


def analyze_market_event(
    symbol: str,
    user_id: str,
    simulate_missing_filing: bool = False,
    simulate_agent_conflict: bool = False,
    force_market_refresh: bool = False,
    market_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the full Fintel analysis pipeline."""
    start = time.perf_counter()

    try:
        if not symbol:
            return _empty_result("No symbol provided.")

        user_profile = get_user_profile(user_id)
        if not user_profile:
            return _empty_result(f"Unknown investor: {user_id}.")

        symbol = symbol.upper().strip()
        if market_data is None:
            market_data = get_live_market_data(symbol, force_refresh=force_market_refresh)

        if market_data.get("error"):
            return _empty_result(market_data["error"])
        if market_data.get("price") is None:
            return _empty_result(f"Market data unavailable for {symbol}.")

        query = f"{symbol} quarterly financial disclosure revenue margin growth"
        documents = [] if simulate_missing_filing else retrieve_documents(query, symbol, top_k=2)

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
        synthesis = synthesis_agent(
            technical, fundamental, sentiment, portfolio_ctx, market_data
        )
        portfolio_impact = calculate_portfolio_impact(
            user_profile, symbol, market_data, synthesis["overall_signal"]
        )

        reasoning_chain = _build_reasoning_chain(
            market_data, documents, technical, fundamental, sentiment,
            portfolio_impact, synthesis,
        )

        sources: list[dict[str, str]] = [
            {"type": "market_data", "label": _market_data_label(market_data)},
        ]
        for doc in documents:
            sources.append({"type": "rag", "label": doc["title"]})
        for agent in (technical, fundamental, sentiment):
            for src in agent.get("sources", []):
                entry = {"type": agent["agent"], "label": str(src)}
                if entry not in sources:
                    sources.append(entry)

        agents_completed = sum(
            1 for a in (technical, fundamental, sentiment)
            if a.get("status") in (STATUS_OK, STATUS_DEGRADED)
        )

        latency = round(time.perf_counter() - start, 3)
        pipeline_status = "success"
        if simulate_missing_filing or fundamental.get("status") == STATUS_DEGRADED:
            pipeline_status = "success"
        if any(a.get("status") == STATUS_UNAVAILABLE for a in (technical, fundamental, sentiment)):
            pipeline_status = "degraded"
        if market_data.get("data_status") == "CACHED":
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
            "retrieved_evidence": documents,
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
                "market_data_source": market_data.get("data_status", "SIMULATED"),
                "data_freshness": market_data.get("data_timestamp"),
                "live_api_success": market_data.get("live_api_success", False),
                "provider": market_data.get("provider"),
            },
            "status": pipeline_status,
        }

    except Exception as exc:
        logger.exception("Pipeline failed")
        result = _empty_result(f"Analysis failed: {exc}")
        result["metrics"]["latency_seconds"] = round(time.perf_counter() - start, 3)
        return result

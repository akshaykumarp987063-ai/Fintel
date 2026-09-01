"""Fundamental Agent — scores a symbol from retrieved documents only.

This agent never invents results, numbers, statements, or sources.
It does not retrieve documents (Person 1 owns RAG).
An LLM is optional; keyword scoring always works without an API.
"""

import json
import os

_ALLOWED_SIGNALS = ("BULLISH", "NEUTRAL", "BEARISH", "INSUFFICIENT_EVIDENCE")

# Longer phrases first so "growth slowed" is not counted as bullish "growth".
_BEARISH_PHRASES = (
    "growth slowed",
    "lowered guidance",
    "cut guidance",
    "margin compression",
    "missed estimates",
    "weak demand",
    "slowed",
    "declined",
    "decreased",
    "missed",
    "compressed",
    "weakness",
    "warning",
    "loss",
    "fell",
    "drop",
    "cut",
)

_BULLISH_PHRASES = (
    "raised guidance",
    "margin expansion",
    "beat estimates",
    "strong growth",
    "strong demand",
    "increased",
    "improved",
    "expanded",
    "outperformed",
    "record",
    "beat",
    "growth",
)


def analyze_fundamentals(symbol, retrieved_documents):
    """Score fundamentals using only the documents passed in.

    Args:
        symbol: ticker or company name (used in reasoning only).
        retrieved_documents: list of dicts with source, text, and optional score.

    Returns:
        dict with agent, signal, confidence, reasoning, evidence, sources, status.
    """
    label = _safe_symbol(symbol)
    docs = _normalize_documents(retrieved_documents)

    if not docs:
        return {
            "agent": "fundamental",
            "signal": "INSUFFICIENT_EVIDENCE",
            "confidence": 0,
            "reasoning": "No relevant financial evidence was retrieved.",
            "evidence": [],
            "sources": [],
            "status": "DEGRADED",
        }

    llm_view = _try_llm_classify(label, docs)
    keyword_view = _keyword_classify(label, docs)

    if llm_view is not None:
        chosen = llm_view
    else:
        chosen = keyword_view

    evidence = [
        {
            "source": doc["source"],
            "text": doc["text"],
            "score": doc["score"],
        }
        for doc in docs
    ]
    sources = []
    for doc in docs:
        if doc["source"] and doc["source"] not in sources:
            sources.append(doc["source"])

    return {
        "agent": "fundamental",
        "signal": chosen["signal"],
        "confidence": chosen["confidence"],
        "reasoning": chosen["reasoning"],
        "evidence": evidence,
        "sources": sources,
        "status": chosen["status"],
    }


def _safe_symbol(symbol):
    if symbol is None:
        return "UNKNOWN"
    text = str(symbol).strip()
    return text if text else "UNKNOWN"


def _normalize_documents(retrieved_documents):
    """Keep only usable docs. Malformed items are skipped, not raised."""
    if retrieved_documents is None:
        return []
    if isinstance(retrieved_documents, dict):
        items = [retrieved_documents]
    elif isinstance(retrieved_documents, (list, tuple)):
        items = retrieved_documents
    else:
        return []

    docs = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        source = item.get("source")
        if isinstance(source, str) and source.strip():
            source = source.strip()
        else:
            source = ""
        score = _safe_score(item.get("score"))
        docs.append({"source": source, "text": text.strip(), "score": score})
    return docs


def _safe_score(value):
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.5
    if score < 0:
        return 0.0
    if score > 1:
        return 1.0
    return score


def _keyword_classify(symbol, docs):
    bull_weight = 0.0
    bear_weight = 0.0
    snippets = []

    for doc in docs:
        bull, bear = _phrase_counts(doc["text"])
        weight = doc["score"] if doc["score"] > 0 else 0.5
        bull_weight += bull * weight
        bear_weight += bear * weight
        if bull or bear:
            snippets.append(doc["text"][:240])

    if bull_weight == 0 and bear_weight == 0:
        return {
            "signal": "INSUFFICIENT_EVIDENCE",
            "confidence": 0,
            "reasoning": (
                "Documents were retrieved for {symbol}, but they did not contain "
                "recognizable fundamental language, so no signal is assigned."
            ).format(symbol=symbol),
            "status": "DEGRADED",
        }

    gap = abs(bull_weight - bear_weight)
    total = bull_weight + bear_weight
    avg_score = sum(doc["score"] for doc in docs) / float(len(docs))

    if gap < 0.15 * total:
        signal = "NEUTRAL"
    elif bull_weight > bear_weight:
        signal = "BULLISH"
    else:
        signal = "BEARISH"

    confidence = round(min(0.95, 0.45 + 0.35 * avg_score + 0.20 * min(gap / total, 1.0)), 2)
    quoted = snippets[0] if snippets else docs[0]["text"][:240]
    reasoning = (
        "Based only on retrieved documents for {symbol}, the text leans {signal}. "
        "Relevant excerpt: \"{quoted}\""
    ).format(symbol=symbol, signal=signal, quoted=quoted)

    return {
        "signal": signal,
        "confidence": confidence,
        "reasoning": reasoning,
        "status": "OK",
    }


def _phrase_counts(text):
    remaining = text.lower()
    bear = 0
    for phrase in sorted(_BEARISH_PHRASES, key=len, reverse=True):
        hits = remaining.count(phrase)
        if hits:
            bear += hits
            remaining = remaining.replace(phrase, " ")
    bull = 0
    for phrase in sorted(_BULLISH_PHRASES, key=len, reverse=True):
        hits = remaining.count(phrase)
        if hits:
            bull += hits
            remaining = remaining.replace(phrase, " ")
    return bull, bear


def _try_llm_classify(symbol, docs):
    """Optional OpenAI call. Returns None so keyword scoring is used instead."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    excerpts = []
    for doc in docs:
        excerpts.append(
            "source={source}\n{text}".format(
                source=doc["source"] or "(no filename)",
                text=doc["text"][:800],
            )
        )
    prompt = (
        "Classify the fundamental outlook for {symbol} using ONLY the excerpts. "
        "Do not invent numbers, statements, or sources. "
        "Return JSON with keys signal (BULLISH, NEUTRAL, BEARISH, or "
        "INSUFFICIENT_EVIDENCE), confidence (0 to 1), and reasoning. "
        "Excerpts:\n{excerpts}"
    ).format(symbol=symbol, excerpts="\n---\n".join(excerpts))

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.environ.get("FINTEL_FUNDAMENTAL_MODEL", "gpt-4o-mini"),
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": "You only classify provided excerpts. Never invent facts.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content
        parsed = _parse_llm_json(content)
        if parsed is None:
            return None
        signal = parsed.get("signal")
        if signal not in _ALLOWED_SIGNALS:
            return None
        confidence = _safe_score(parsed.get("confidence"))
        reasoning = parsed.get("reasoning")
        if not isinstance(reasoning, str) or not reasoning.strip():
            return None
        status = "OK" if signal != "INSUFFICIENT_EVIDENCE" else "DEGRADED"
        return {
            "signal": signal,
            "confidence": round(confidence, 2),
            "reasoning": reasoning.strip(),
            "status": status,
        }
    except Exception:
        return None


def _parse_llm_json(content):
    if not isinstance(content, str):
        return None
    text = content.strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            data = json.loads(text[start : end + 1])
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None

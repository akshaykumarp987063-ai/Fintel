"""
Temporary UI contract: mock of the final structured payload the Fintel
orchestrator will send to Person 5's Streamlit app.

Replace get_mock_analysis() with a real backend call at integration time.
Values are demo-only — not live market data or computed analysis.
"""

from typing import Any


def get_mock_analysis() -> dict[str, Any]:
    """Return a realistic but clearly mock orchestrator result for UI development."""
    return {
        "investor": {
            "name": "Alex Rivera (DEMO)",
            "risk_profile": "Moderate",
        },
        "selected_stock": {
            "symbol": "AAPL",
            "company_name": "Apple Inc. (MOCK)",
        },
        "portfolio_summary": {
            "total_holdings": 125000.00,
            "portfolio_risk": "Medium",
            "stock_exposure": 0.18,
        },
        "market_signals": {
            "momentum": "Positive",
            "volume": "Above average (MOCK)",
            "sentiment": "Cautiously bullish",
        },
        "agent_results": [
            {
                "name": "Fundamental Analyst Agent",
                "recommendation": "Hold",
                "confidence": 0.74,
                "summary": (
                    "MOCK: Balance-sheet quality looks stable in this demo payload. "
                    "No live fundamentals were fetched."
                ),
            },
            {
                "name": "Technical Analyst Agent",
                "recommendation": "Buy",
                "confidence": 0.68,
                "summary": (
                    "MOCK: Short-term trend is framed as constructive for the UI. "
                    "This is not a real technical signal."
                ),
            },
            {
                "name": "Risk & Sentiment Agent",
                "recommendation": "Hold",
                "confidence": 0.71,
                "summary": (
                    "MOCK: Headline sentiment is mixed-to-positive in this sample. "
                    "Risk flags are illustrative only."
                ),
            },
        ],
        "supporting_evidence": [
            {
                "title": "Q2 earnings recap (demo excerpt)",
                "source": "MockWire / Internal RAG stub",
                "summary": (
                    "DEMO: Revenue and services mix are described as resilient. "
                    "This citation is fabricated for layout testing."
                ),
            },
            {
                "title": "Sector momentum note (demo excerpt)",
                "source": "MockStreet Research stub",
                "summary": (
                    "DEMO: Large-cap tech is labeled as in a consolidation phase. "
                    "Not sourced from a real research desk."
                ),
            },
            {
                "title": "Risk commentary (demo excerpt)",
                "source": "Fintel Evidence Store (placeholder)",
                "summary": (
                    "DEMO: Concentration and valuation are listed as watch items. "
                    "Replace with RAG chunks at integration."
                ),
            },
        ],
        "final_result": {
            "recommendation": "Hold",
            "confidence": 0.72,
            "explanation": (
                "DEMO orchestrator output: agents lean Hold with a mild Buy from "
                "technicals. The UI should treat this as a contract sample, not advice."
            ),
            "reasoning_steps": [
                "Collect investor profile and current AAPL exposure (MOCK).",
                "Read market-signal snapshot: momentum, volume, sentiment (MOCK).",
                "Run three specialist agents and collect recommendations (MOCK).",
                "Attach supporting evidence snippets for explainability (MOCK).",
                "Blend agent views into a single Hold recommendation at 72% confidence (MOCK).",
            ],
        },
    }

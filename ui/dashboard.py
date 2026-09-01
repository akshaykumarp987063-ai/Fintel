"""
Main Fintel dashboard: page flow, inputs, and section composition.

Display work is delegated to ui.components. Timing is delegated to metrics.
Analysis payloads currently come from mock_data; swap fetch_analysis() at
backend integration time.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from metrics.metrics import (
    get_metrics_summary,
    record_analysis_end,
    record_analysis_start,
    record_error,
)
from mock_data import get_mock_analysis
from ui.components import (
    render_agent_card,
    render_evidence,
    render_final_recommendation,
    render_header,
    render_portfolio_summary,
    render_reasoning,
    render_session_metrics,
    render_signal_card,
)

# Demo choices for independent UI work. Backend will own real investor/ticker lists.
_DEMO_INVESTORS = (
    "Alex Rivera (DEMO)",
    "Jordan Chen (DEMO)",
    "Sam Okonkwo (DEMO)",
)
_DEMO_STOCKS = {
    "AAPL — Apple Inc.": ("AAPL", "Apple Inc."),
    "MSFT — Microsoft Corp.": ("MSFT", "Microsoft Corp."),
    "NVDA — NVIDIA Corp.": ("NVDA", "NVIDIA Corp."),
}

_ANALYSIS_KEY = "analysis_result"
_QUERY_KEY = "analysis_query"
_ERROR_KEY = "analysis_error"


def fetch_analysis(investor_name: str, stock_symbol: str) -> dict[str, Any]:
    """Return a structured analysis payload for the dashboard.

    FUTURE BACKEND INTEGRATION:
        Replace the body of this function with a call to the Fintel orchestrator,
        passing investor_name and stock_symbol. Keep the return shape aligned with
        get_mock_analysis() so the rest of this file does not change.
    """
    # --- mock integration (remove at integration) ---
    payload = get_mock_analysis()
    # --- end mock integration ---
    if not isinstance(payload, dict) or not payload:
        raise ValueError("Analysis returned no data.")

    result = dict(payload)
    investor = _as_dict(result.get("investor"))
    investor["name"] = investor_name
    result["investor"] = investor

    selected = _as_dict(result.get("selected_stock"))
    selected["symbol"] = stock_symbol
    company_lookup = {symbol: company for symbol, company in _DEMO_STOCKS.values()}
    if stock_symbol in company_lookup:
        selected["company_name"] = company_lookup[stock_symbol]
    result["selected_stock"] = selected
    return result


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _run_analysis(investor_name: str, stock_symbol: str) -> None:
    """Time a successful analysis, or record an error and keep the prior result."""
    record_analysis_start()
    try:
        result = fetch_analysis(investor_name, stock_symbol)
        st.session_state[_ANALYSIS_KEY] = result
        st.session_state[_QUERY_KEY] = {
            "investor_name": investor_name,
            "stock_symbol": stock_symbol,
        }
        st.session_state[_ERROR_KEY] = None
        record_analysis_end()
    except Exception:
        record_error()
        st.session_state[_ERROR_KEY] = (
            "Fintel could not complete this analysis. "
            "Please try again. If this continues after backend integration, "
            "check that the orchestrator is available."
        )


def _render_inputs() -> tuple[str, str, bool]:
    """Collect investor and ticker, plus whether Analyze was pressed."""
    st.subheader("New analysis")
    col_investor, col_stock, col_action = st.columns([2, 2, 1])

    with col_investor:
        investor_choice = st.selectbox("Investor", options=list(_DEMO_INVESTORS) + ["Custom name"])
        if investor_choice == "Custom name":
            investor_name = st.text_input("Investor name", placeholder="Full name").strip()
        else:
            investor_name = investor_choice

    with col_stock:
        stock_choice = st.selectbox("Stock", options=list(_DEMO_STOCKS.keys()) + ["Custom symbol"])
        if stock_choice == "Custom symbol":
            stock_symbol = st.text_input("Ticker symbol", placeholder="e.g. AAPL").strip().upper()
        else:
            stock_symbol = _DEMO_STOCKS[stock_choice][0]

    with col_action:
        st.markdown("<div style='height: 1.7rem'></div>", unsafe_allow_html=True)
        analyze_clicked = st.button("Analyze", type="primary", use_container_width=True)

    return investor_name, stock_symbol, analyze_clicked


def _render_welcome() -> None:
    """Clean empty state shown before the first analysis."""
    st.markdown("### Welcome to Fintel")
    st.markdown(
        """
        Fintel brings **market analysis**, **AI agent views**, **supporting evidence**,
        and **portfolio context** into one recommendation you can inspect.

        Choose an investor and a stock, then select **Analyze** to generate a Fintel Insight.
        Until the backend is connected, this workspace uses a demo payload with the same
        structure the orchestrator will return.
        """
    )
    st.caption("Not investment advice. Demo values only.")


def _render_results(result: dict[str, Any]) -> None:
    """Compose analysis sections in the required display order."""
    final_result = _as_dict(result.get("final_result"))
    signals = _as_dict(result.get("market_signals"))
    portfolio = _as_dict(result.get("portfolio_summary"))
    agents = _as_list(result.get("agent_results"))
    evidence = _as_list(result.get("supporting_evidence"))
    reasoning_steps = _as_list(final_result.get("reasoning_steps"))

    query = _as_dict(st.session_state.get(_QUERY_KEY))
    investor = query.get("investor_name") or _as_dict(result.get("investor")).get("name")
    symbol = query.get("stock_symbol") or _as_dict(result.get("selected_stock")).get("symbol")
    company = _as_dict(result.get("selected_stock")).get("company_name")
    context_bits = [part for part in (investor, symbol, company) if part]
    if context_bits:
        st.caption(" · ".join(str(part) for part in context_bits))

    # A. Final Fintel Insight
    st.markdown("### Final Fintel Insight")
    render_final_recommendation(final_result)

    # B. Market Signals
    st.markdown("### Market Signals")
    col_momentum, col_volume, col_sentiment = st.columns(3)
    with col_momentum:
        render_signal_card("Momentum", signals.get("momentum"))
    with col_volume:
        render_signal_card("Volume", signals.get("volume"))
    with col_sentiment:
        render_signal_card("Sentiment", signals.get("sentiment"))

    # C. Portfolio Summary
    render_portfolio_summary(portfolio)

    # D. AI Agent Analysis
    st.markdown("### AI Agent Analysis")
    if not agents:
        st.info("No agent results are available for this analysis.")
    else:
        columns = st.columns(max(len(agents), 1))
        for column, agent in zip(columns, agents):
            with column:
                render_agent_card(agent if isinstance(agent, dict) else None)

    # E. Supporting Evidence
    render_evidence(evidence)

    # F. Explainability
    st.markdown("### Explainability")
    render_reasoning(reasoning_steps)


def render_dashboard() -> None:
    """Run the Person 5 dashboard: header, inputs, welcome or analysis results."""
    if _ANALYSIS_KEY not in st.session_state:
        st.session_state[_ANALYSIS_KEY] = None
    if _QUERY_KEY not in st.session_state:
        st.session_state[_QUERY_KEY] = {}
    if _ERROR_KEY not in st.session_state:
        st.session_state[_ERROR_KEY] = None

    render_header()
    investor_name, stock_symbol, analyze_clicked = _render_inputs()

    if analyze_clicked:
        if not investor_name or not stock_symbol:
            st.warning("Enter an investor name and a stock symbol before analyzing.")
        else:
            _run_analysis(investor_name, stock_symbol)

    error_message = st.session_state.get(_ERROR_KEY)
    if error_message:
        st.error(error_message)

    result = st.session_state.get(_ANALYSIS_KEY)
    if isinstance(result, dict) and result:
        _render_results(result)
    elif not error_message:
        _render_welcome()

    with st.sidebar:
        st.markdown("### Session metrics")
        render_session_metrics(get_metrics_summary())

"""Fintel Streamlit entry point — thin UI layer."""

import streamlit as st

from orchestrator import DEMO_USERS, analyze_market_event, get_live_market_data

INVESTORS = {uid: profile["name"] for uid, profile in DEMO_USERS.items()}
STOCKS = ["TCS", "INFY", "RELIANCE"]

st.set_page_config(page_title="Fintel", page_icon="📊", layout="wide")
st.title("Fintel")
st.caption(
    "Personalized, explainable financial intelligence — live market data with offline demo fallback"
)

col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

with col1:
    investor_id = st.selectbox(
        "Investor",
        options=list(INVESTORS.keys()),
        format_func=lambda uid: INVESTORS[uid],
    )

with col2:
    symbol = st.selectbox("Stock", options=STOCKS)

with col3:
    st.write("")
    analyze_clicked = st.button("Analyze", type="primary", use_container_width=True)

with col4:
    st.write("")
    refresh_clicked = st.button("Refresh Market Data", use_container_width=True)

demo_col1, demo_col2 = st.columns(2)
with demo_col1:
    simulate_missing_filing = st.checkbox("Simulate missing filing")
with demo_col2:
    simulate_agent_conflict = st.checkbox("Simulate agent conflict")


def _status_color(status: str) -> str:
    return {
        "LIVE": "green",
        "CACHED": "orange",
        "SIMULATED": "gray",
        "UNAVAILABLE": "red",
    }.get(status, "gray")


def render_market_data_status(md: dict) -> None:
    status = md.get("data_status", "SIMULATED")
    provider = md.get("provider") or "—"
    timestamp = md.get("data_timestamp") or "—"
    st.markdown(
        f"**Data status:** :{_status_color(status)}[{status}] &nbsp;|&nbsp; "
        f"**Provider:** {provider} &nbsp;|&nbsp; "
        f"**Timestamp:** {timestamp}"
    )
    if status == "CACHED":
        st.info("LIVE API unavailable — using most recent cached market data (not realtime).")
    elif status == "SIMULATED":
        st.info("Using deterministic demo data — fully offline fallback mode.")


if refresh_clicked:
    with st.spinner(f"Refreshing live market data for {symbol}..."):
        refreshed = get_live_market_data(symbol, force_refresh=True)
    st.session_state["last_market_data"] = refreshed
    st.session_state["last_market_symbol"] = symbol

if st.session_state.get("last_market_symbol") == symbol and st.session_state.get("last_market_data"):
    st.subheader("Market Data Status")
    render_market_data_status(st.session_state["last_market_data"])
    md = st.session_state["last_market_data"]
    if md.get("price") is not None:
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Price", f"₹{md['price']:,.2f}")
        change = md.get("change_pct")
        r2.metric("Change", f"{change:+.2f}%" if change is not None else "—")
        vol = md.get("volume")
        r3.metric("Volume", f"{vol:,}" if vol is not None else "—")
        vr = md.get("volume_ratio")
        r4.metric("Volume Ratio", f"{vr:.1f}x" if vr is not None else "N/A")

if analyze_clicked:
    with st.spinner(f"Analyzing {symbol} for {INVESTORS[investor_id]}..."):
        result = analyze_market_event(
            symbol=symbol,
            user_id=investor_id,
            simulate_missing_filing=simulate_missing_filing,
            simulate_agent_conflict=simulate_agent_conflict,
            force_market_refresh=False,
        )

    if result["status"] == "error":
        st.error(result["summary"])
    else:
        if result["status"] == "degraded":
            st.warning("Analysis completed in degraded mode — cached, simulated, or partial data was used.")

        md = result["market_data"]
        st.subheader("Market Data Status")
        render_market_data_status(md)

        st.subheader("Market Signal")
        m1, m2, m3, m4 = st.columns(4)
        price_label = {
            "LIVE": "Price (live)",
            "CACHED": "Price (cached)",
            "SIMULATED": "Price (simulated)",
        }.get(md.get("data_status", "SIMULATED"), "Price")
        m1.metric(price_label, f"₹{md.get('price', 0):,.2f}")
        change = md.get("change_pct")
        m2.metric("Change", f"{change:+.2f}%" if change is not None else "—")
        vr = md.get("volume_ratio")
        m3.metric("Volume Ratio", f"{vr:.1f}x" if vr is not None else "Unavailable")
        m4.metric("Sentiment Score", f"{md.get('sentiment_score', 0):+.2f}")

        st.subheader("Signal Classification")
        dims = result["signal_dimensions"]
        d1, d2, d3 = st.columns(3)
        d1.metric("Momentum", dims.get("momentum", "—"))
        d2.metric("Volume", dims.get("volume", "—"))
        d3.metric("Sentiment", dims.get("sentiment", "—"))

        st.subheader("Agent Outputs")
        agents = result["agents"]
        a1, a2, a3 = st.columns(3)
        for col, key in zip([a1, a2, a3], ["technical", "fundamental", "sentiment"]):
            agent = agents.get(key, {})
            with col:
                st.markdown(f"**{key.title()} Agent**")
                st.metric("Signal", agent.get("signal", "—"))
                st.caption(f"Confidence: {agent.get('confidence', 0):.0%}")
                st.caption(f"Status: {agent.get('status', '—')}")
                st.write(agent.get("reasoning", ""))

        st.subheader("Evidence & Sources")
        for doc in result.get("retrieved_evidence", []):
            with st.expander(f"{doc['title']} — relevance {doc['score']:.0%}"):
                st.caption(f"Source: {doc.get('source', doc['title'])}")
                st.write(doc.get("text", ""))
        for src in result["sources"]:
            st.write(f"- **[{src['type']}]** {src['label']}")

        st.subheader("Personalized Portfolio Impact")
        pi = result["portfolio_impact"]
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Impact Level", pi.get("classification", "—"), delta=None)
        p2.metric("Exposure", f"{pi.get('exposure', 0):.0%}")
        p3.metric("Direct Impact", f"{pi.get('direct_impact_pct', 0):+.2f}%")
        p4.metric("Risk Profile", pi.get("risk_tolerance", "—"))

        st.info(
            f"**{pi.get('user', 'Investor')}** ({pi.get('risk_tolerance', '')}) — "
            f"Overall signal: **{result['overall_signal']}** "
            f"at **{result['confidence']:.0%}** confidence. "
            f"{result['summary']}"
        )

        st.subheader("Why did Fintel reach this conclusion?")
        for step in result["reasoning_chain"]:
            st.write(f"- {step}")

        st.subheader("Session Metrics")
        metrics = result["metrics"]
        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric("Latency", f"{metrics.get('latency_seconds', 0):.3f}s")
        s2.metric("Signal Confidence", f"{metrics.get('signal_confidence', 0):.0%}")
        s3.metric("Portfolio Concentration", f"{metrics.get('portfolio_concentration', 0):.0%}")
        s4.metric("Agents Completed", metrics.get("agents_completed", 0))
        s5.metric("Sources Retrieved", metrics.get("sources_retrieved", 0))

        m1, m2, m3 = st.columns(3)
        m1.metric("Market Data Source", metrics.get("market_data_source", "—"))
        freshness = metrics.get("data_freshness")
        m2.metric("Data Freshness", freshness[:19] if freshness else "—")
        api_ok = metrics.get("live_api_success", False)
        m3.metric("Live API", "Success" if api_ok else "Fallback")

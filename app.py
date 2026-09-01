"""Fintel Streamlit entry point — thin UI layer."""

import streamlit as st

from orchestrator import DEMO_USERS, analyze_market_event

INVESTORS = {uid: profile["name"] for uid, profile in DEMO_USERS.items()}
STOCKS = ["TCS", "INFY", "RELIANCE"]

st.set_page_config(page_title="Fintel", page_icon="📊", layout="wide")
st.title("Fintel")
st.caption("Personalized, explainable financial intelligence (hackathon demo — simulated data)")

col1, col2, col3 = st.columns([2, 2, 1])

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

demo_col1, demo_col2 = st.columns(2)
with demo_col1:
    simulate_missing_filing = st.checkbox("Simulate missing filing")
with demo_col2:
    simulate_agent_conflict = st.checkbox("Simulate agent conflict")

if analyze_clicked:
    with st.spinner(f"Analyzing {symbol} for {INVESTORS[investor_id]}..."):
        result = analyze_market_event(
            symbol=symbol,
            user_id=investor_id,
            simulate_missing_filing=simulate_missing_filing,
            simulate_agent_conflict=simulate_agent_conflict,
        )

    if result["status"] == "error":
        st.error(result["summary"])
    else:
        if result["status"] == "degraded":
            st.warning("Analysis completed in degraded mode — some data was unavailable.")

        # 1. Market information
        st.subheader("Market Signal")
        md = result["market_data"]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Price (simulated)", f"₹{md.get('price', 0):,.2f}")
        m2.metric("Change", f"{md.get('change_pct', 0):+.1f}%")
        m3.metric("Volume Ratio", f"{md.get('volume_ratio', 0):.1f}x")
        m4.metric("Sentiment Score", f"{md.get('sentiment_score', 0):+.2f}")

        # 2. Signal classification (3 dimensions)
        st.subheader("Signal Classification")
        dims = result["signal_dimensions"]
        d1, d2, d3 = st.columns(3)
        d1.metric("Momentum", dims.get("momentum", "—"))
        d2.metric("Volume", dims.get("volume", "—"))
        d3.metric("Sentiment", dims.get("sentiment", "—"))

        # 3. Agent cards
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

        # 4. Evidence / sources
        st.subheader("Evidence & Sources")
        for src in result["sources"]:
            st.write(f"- **[{src['type']}]** {src['label']}")

        # 5. Personalized portfolio impact
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

        # 6. Why / reasoning chain
        st.subheader("Why did Fintel reach this conclusion?")
        for step in result["reasoning_chain"]:
            st.write(f"- {step}")

        # 7. Session metrics
        st.subheader("Session Metrics")
        metrics = result["metrics"]
        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric("Latency", f"{metrics.get('latency_seconds', 0):.3f}s")
        s2.metric("Signal Confidence", f"{metrics.get('signal_confidence', 0):.0%}")
        s3.metric("Portfolio Concentration", f"{metrics.get('portfolio_concentration', 0):.0%}")
        s4.metric("Agents Completed", metrics.get("agents_completed", 0))
        s5.metric("Sources Retrieved", metrics.get("sources_retrieved", 0))

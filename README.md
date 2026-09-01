# Fintel

### Personalized Financial Intelligence

Fintel is a multi-agent financial intelligence platform built for retail investors.

Instead of only showing *what is happening* in the market, Fintel tries to answer the more useful question:

> **"What does this market event mean for this particular investor?"**

It combines the latest available market data, company-relevant news, financial evidence, independent specialist agents, and the user's portfolio exposure to produce a personalized, explainable result.

---

## What problem does Fintel solve?

Retail investors often have access to far more financial data than they can realistically interpret.

A stock can move because of price momentum, trading activity, company fundamentals, news, or a combination of factors. The same market event can also have very different consequences for two investors depending on how much of that stock they own and how they approach risk.

Fintel bridges that gap.

It turns:

**Raw financial data → evidence → independent analysis → personalized portfolio impact → explainable intelligence**

The goal is not to pretend that an AI can predict the future with certainty. The goal is to make financial information easier to understand, traceable to evidence, and relevant to the individual investor.

---

## Why Fintel is different

Fintel does not rely on a single signal or a single model.

It brings together three independent perspectives:

- **Technical Agent** — looks at price movement and trading-volume behavior.
- **Fundamental Agent** — evaluates retrieved financial evidence and company fundamentals.
- **Sentiment Agent** — evaluates company-relevant news sentiment.

Those perspectives are then synthesized and weighted against the selected investor's portfolio exposure and risk profile.

This creates a result such as:

> **TCS is showing a bearish overall signal, but live news sentiment is neutral. Because TCS represents 40% of the selected investor's portfolio, the estimated portfolio impact is classified as high.**

The important part is that Fintel also shows **why** it reached that conclusion.

---

## Core features

### 1. Live market intelligence

Fintel retrieves the latest available market information through `yfinance`.

The dashboard clearly labels market-data status as:

- **LIVE**
- **CACHED**
- **SIMULATED**

This means the application does not silently present fallback data as live data.

Market information includes:

- price
- percentage change
- volume
- volume ratio
- timestamp
- provider/source

### 2. Company-relevant live news

Fintel can retrieve live/latest available company-relevant news for supported stocks.

The news pipeline:

1. Retrieves candidate headlines.
2. Applies company-specific relevance filtering.
3. Keeps only relevant headlines.
4. Calculates a simple deterministic sentiment score from the retrieved text.
5. Falls back to deterministic demo sentiment when live news is unavailable.

News items can show:

- headline
- publisher
- publication time
- sentiment contribution
- source link

Fintel deliberately avoids presenting unrelated market headlines as company sentiment.

### 3. Multi-agent analysis

Three specialist agents independently contribute to the analysis:

```text
                 MARKET EVENT
                      |
          +-----------+-----------+
          |           |           |
          v           v           v
      Technical   Fundamental  Sentiment
        Agent       Agent        Agent
          |           |           |
          +-----------+-----------+
                      |
                      v
                  Synthesis
```

The agents can agree, disagree, or produce mixed signals.

Fintel does not hide disagreement.

For example:

```text
Technical      BEARISH
Fundamental    BEARISH
Sentiment      NEUTRAL

Consensus: MIXED
```

When there is meaningful disagreement, the system can reduce confidence and make that uncertainty visible.

### 4. Financial evidence / RAG

The Fundamental Agent uses retrieved financial evidence from the project's document corpus.

Fintel exposes:

- retrieved document
- relevance score
- supporting text/evidence

This creates a traceable path from a conclusion back to the information that supported it.

### 5. Personalized portfolio impact

A market signal is not equally important to every investor.

Fintel therefore combines the analysis with the selected investor's:

- portfolio exposure
- risk profile
- selected-stock concentration

The result includes:

- impact level
- selected-stock exposure
- estimated direct impact
- investor risk profile

The estimate is deliberately described as illustrative/exposure-weighted rather than guaranteed.

### 6. Explainability

One of Fintel's main goals is to make the reasoning easy to follow.

The dashboard presents a step-by-step explanation:

```text
1. LIVE MARKET OBSERVATION
2. FINANCIAL EVIDENCE
3. LIVE NEWS SENTIMENT
4. USER PORTFOLIO EXPOSURE
5. FINAL IMPACT
```

This helps answer:

- What happened?
- What evidence supports it?
- What do the independent agents think?
- Why does it matter to this investor?
- How confident is the system?
- What happens if a data source fails?

### 7. Resilient fallback behavior

Fintel is designed so that an unavailable external data source does not automatically break the demo.

For market data:

```text
LIVE
  ↓
CACHED
  ↓
SIMULATED
```

For news sentiment:

```text
LIVE NEWS
  ↓
DEMO FALLBACK
```

Fallback states are explicitly labeled.

---

## How Fintel works

At a high level:

```text
              +----------------------+
              |   Latest Market Data |
              |       yfinance       |
              +----------+-----------+
                         |
                         |
              +----------v-----------+
              |   Company News       |
              |   + Relevance Filter |
              +----------+-----------+
                         |
                         |
              +----------v-----------+
              | Financial Evidence   |
              |       / RAG          |
              +----------+-----------+
                         |
            +------------+------------+
            |            |            |
            v            v            v
       Technical    Fundamental   Sentiment
         Agent         Agent        Agent
            |            |            |
            +------------+------------+
                         |
                         v
                    Synthesis
                         |
                         v
              Investor Profile
              + Risk Profile
              + Portfolio Exposure
                         |
                         v
                Portfolio Impact
                         |
                         v
              Explainable Result
              + Sources
              + Confidence
              + Reasoning
```

---

## Result structure

The orchestrator produces a structured analysis result containing fields such as:

```python
{
    "overall_signal": "...",
    "confidence": 0.0,
    "portfolio_impact": {...},
    "summary": "...",
    "reasoning_chain": [...],
    "sources": [...],
    "status": "success"
}
```

This keeps the UI relatively thin while the orchestration layer handles the analysis pipeline.

---

## Tech stack

- **Python**
- **Streamlit** — interactive dashboard
- **yfinance** — market-data retrieval
- **News API integration** — optional live/latest available news
- **RAG / document retrieval** — financial evidence
- **Multi-agent analysis pipeline** — technical, fundamental, and sentiment perspectives
- **Git / GitHub** — version control and collaboration

---

## Project structure

```text
fintel/
├── app.py
├── orchestrator.py
├── config.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

### Main files

`app.py`
- Streamlit user interface
- Investor and stock selection
- Dashboard rendering
- Results, reasoning, evidence, metrics

`orchestrator.py`
- Market-data pipeline
- News pipeline
- RAG/evidence retrieval
- Specialist agents
- Synthesis
- Portfolio impact
- Fallback handling

`config.py`
- Application/configuration values

`.env.example`
- Safe template for environment variables

`.env`
- Local secrets/configuration
- **Never commit this file**

---

## Getting started

### 1. Clone the repository

```bash
git clone https://github.com/akshaykumarp987063-ai/fintel.git
cd fintel
```

### 2. Create a virtual environment

#### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

#### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure optional live news

Create a local `.env` file in the project root:

```text
NEWS_API_KEY=your_key_here
```

You can use `.env.example` as the template.

**Never commit your real API key.**

The market-data path through `yfinance` does not require a market-data API key.

### 5. Run Fintel

From the project root, run:

```bash
python -m streamlit run app.py
```

If `python` is not available on your system, try:

```bash
py -m streamlit run app.py
```

On macOS / Linux, you can also use:

```bash
python3 -m streamlit run app.py
```

Then open the local Streamlit URL shown in your terminal (typically `http://localhost:8501`).

---

## Using the dashboard

A typical Fintel flow is:

1. Choose an investor.
2. Choose a stock.
3. Click **Analyze**.
4. Fintel retrieves the latest available market data.
5. Fintel retrieves relevant financial/news evidence.
6. Technical, fundamental, and sentiment agents analyze the event independently.
7. The system synthesizes those perspectives.
8. Portfolio exposure and risk profile are applied.
9. Fintel displays the estimated portfolio impact.
10. The reasoning chain and evidence explain how the result was reached.

The dashboard also includes **Demo / Reliability Tests** for demonstrating missing evidence and agent conflict scenarios.

---

## Example user journey

Imagine Rahul has a conservative portfolio where TCS represents 40% of his holdings.

Fintel may observe:

```text
Market:
TCS is down

Technical:
BEARISH

Fundamental:
BEARISH

Live News:
NEUTRAL

Portfolio Exposure:
40%

Agent Consensus:
MIXED

Overall Signal:
BEARISH

Portfolio Impact:
HIGH
```

Instead of stopping at "TCS is down", Fintel connects the market event to Rahul's actual exposure and explains why the impact is considered important for that portfolio.

This is the central idea behind Fintel:

> **The same market event can mean something different to different investors.**

---

## Reliability and graceful degradation

External APIs can fail, time out, return empty results, or become temporarily unavailable.

Fintel is intentionally designed to handle those situations.

### Market data

```text
Live provider
    ↓
Cached result
    ↓
Simulated demo data
```

### Sentiment

```text
Live news
    ↓
Deterministic demo fallback
```

The dashboard makes degraded/fallback states visible instead of silently pretending the data is live.

This is particularly useful during demos where internet connectivity or third-party API availability may be unpredictable.

---

## Demo / reliability scenarios

Fintel includes demonstration controls for:

### Missing filing

Simulates a situation where financial evidence is unavailable.

The Fundamental Agent should move into a degraded / insufficient-evidence state instead of fabricating evidence.

### Agent conflict

Simulates disagreement between specialist agents.

The final system should make the disagreement visible and reduce confidence rather than hiding the conflict.

---

## Transparency principles

Fintel follows a few simple principles:

### Do not fabricate data

If live data is unavailable, show a fallback state.

### Do not fabricate evidence

If evidence is missing, show insufficient evidence.

### Do not hide disagreement

If agents disagree, surface the disagreement.

### Do not overstate certainty

Confidence is shown explicitly and should not be interpreted as a guarantee.

### Do not pretend fallback data is live

The UI labels the source and status.

---

## Current limitations

Fintel is a hackathon-focused prototype, not a production trading system.

Current limitations include:

- Market data is based on the latest data available from the provider rather than a guaranteed tick-by-tick realtime feed.
- News quality and availability depend on the external news provider, API key, quota, and connectivity.
- Company-news relevance filtering is intentionally conservative and primarily keyword-based.
- The sentiment calculation is a lightweight deterministic approach rather than a production-grade NLP model.
- The financial evidence corpus included with the prototype is limited and primarily intended for demonstration.
- Market-data caching is lightweight/in-memory rather than a production persistent cache.
- Supported stocks are currently limited to the symbols configured in the application.
- Portfolio impact is an illustrative exposure-weighted estimate, not a guaranteed forecast.

These limitations are deliberate and help keep the hackathon prototype simple, transparent, and reliable.

---

## Security

Never commit secrets.

Your local `.env` should remain outside Git tracking.

Use:

```text
.env.example
```

to document the required configuration without exposing credentials.

Before making the repository public, verify that:

```bash
git ls-files .env
```

returns nothing.

---

## Disclaimer

Fintel provides illustrative financial intelligence and evidence-backed analysis for research and demonstration purposes.

It is **not investment advice**, a recommendation to buy or sell securities, or a guarantee of future performance.

---

## What Fintel demonstrates

At its core, Fintel demonstrates how a multi-agent AI system can move from:

**data**

to

**evidence**

to

**independent reasoning**

to

**personalized financial context**

to

**transparent decision support**

without hiding uncertainty or pretending that external data is always available.

---

## Repository

GitHub:

https://github.com/akshaykumarp987063-ai/fintel

Built as a hackathon prototype focused on personalized, explainable financial intelligence.

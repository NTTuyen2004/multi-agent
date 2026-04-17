# Financial AI Agent Team System

A multi-agent system designed for Vietnamese Stock Market Analysis based on the Leader-Worker architecture. This project emphasizes three critical "production-ready" features: Stateful Memory, Parallel Execution, and Smart Caching.

## 1. Overview: What Problem Does It Solve?

### Context & Challenges

Analyzing a stock in Vietnam involves synthesizing multiple complex data dimensions:

- **Historical Price (OHLCV)**: For trend and volatility analysis.
- **News & Sentiment**: For short-term market impact assessment.
- **Technical Indicators**: (SMA, RSI, etc.).
- **Corporate Profiles**: Industry, scale, and business model.
- **Financial Reports**: For long-term fundamental perspectives.

Traditional approaches often suffer from:

- **Sequential Latency**: Fetching data step-by-step leads to high cumulative wait times.
- **Context Loss**: Systems often forget previous interactions (e.g., "Analyze it" — where "it" refers to a ticker mentioned previously).

- **Redundancy & Cost**: Repeated queries lead to unnecessary API costs and latency.

### Quick Demo

Run the interactive mode to experience Stateful Memory (multi-turn conversation):

```bash
python -m src.fin_agent_team.cli --interactive
```

**Example Flow:**

- **Turn 1:** "Give me info on VCB."
- **Turn 2:** "What about its technical indicators?" → The system maintains context and knows you are still talking about VCB.

## 2. System Architecture: Leader–Worker Model

### Orchestration Workflow

- **Stateful Conversation Memory**: Stores chat history and identified entities (symbols, timeframes, intents), allowing subsequent queries to inherit context.
- **Supervisor**: Orchestrates the entire pipeline.
- **Leader Layer:**
  - Router: Dynamically selects the minimum necessary tasks (data/news/analysis/info/report).
  - Synthesizer: Aggregates worker outputs into a cohesive final recommendation.
- **Worker Layer**: 5 specialized agents running in parallel using asyncio to maximize throughput.

### System Diagram

```mermaid
    classDef cli fill:#f8fafc,stroke:#475569,stroke-width:2px,color:#0f172a,font-weight:bold;
    classDef control fill:#eff6ff,stroke:#2563eb,stroke-width:2px,color:#1e3a8a,font-weight:bold;
    classDef worker fill:#ecfdf5,stroke:#10b981,stroke-width:2px,color:#064e3b;
    classDef data fill:#fdf4ff,stroke:#c026d3,stroke-width:2px,color:#701a75,font-weight:bold;
    classDef cache fill:#fff7ed,stroke:#ea580c,stroke-width:2px,color:#9a3412;

    CLI(["🖥️ Client / CLI"]):::cli
    MEM[("🧠 Conversation Memory")]:::cache
    LLM_CACHE[("💾 LangChain LLM Cache")]:::cache

    subgraph PHASE1 [1. ORCHESTRATION & DISPATCH]
        SUP["🎯 Supervisor"]:::control
        ROUTER{"🔀 Leader.Router"}:::control
        FANOUT[["⚡ Fan-out (asyncio.gather)"]]:::control
    end

    subgraph PHASE2 [2. WORKER LAYER]
        A1["📈 DataAgent"]:::worker
        A2["📰 NewsAgent"]:::worker
        A3["🧪 AnalystAgent"]:::worker
        A4["🏢 InfoAgent"]:::worker
        A5["📑 ReportAgent"]:::worker
    end

    subgraph PHASE3 [3. DATA & LOCAL CACHE]
        VNSTOCK[("💹 vnstock API")]:::data
        FILE_CACHE[("📁 File-based Cache")]:::cache
    end

    subgraph PHASE4 [4. SYNTHESIS & REPORTING]
        MERGE[["🧬 Merge results -> AgentState"]]:::control
        SYNTH{"📊 Leader.Synthesizer"}:::control
    end

    CLI --> SUP
    SUP <--> MEM
    SUP --> ROUTER
    ROUTER --> FANOUT
    FANOUT --> A1 & A2 & A3 & A4 & A5
    A1 & A2 & A3 & A4 & A5 -.-> VNSTOCK
    A1 & A2 & A3 & A4 & A5 -.-> FILE_CACHE
    A1 & A2 & A3 & A4 & A5 --> MERGE
    MERGE --> SYNTH
    SYNTH --> CLI
```

## 3. Unique Selling Points (USPs)

### 3.1 Stateful Memory

Leverages persistent conversation states to identify entities across turns. This enables a natural UX where users don't need to repeat the ticker symbol in every prompt.

### 3.2 Parallel Execution

By utilizing asyncio.gather for worker orchestration, the total latency is reduced to the execution time of the slowest agent rather than the sum of all agents.

**Production Insight (Fault Tolerance):** To ensure robustness, the system utilizes return_exceptions=True within the fan-out layer. If one agent (e.g., NewsAgent) fails due to network issues, the Synthesizer still provides a partial report based on the remaining agents instead of a total system crash.

### 3.3 Smart Dual-Layer Caching

- **LLM Cache**: Uses LangChain's InMemoryCache to avoid redundant LLM calls for identical prompts.
- **Data Cache**: Implements a file-based decorator layer to cache raw market data, drastically reducing API dependency and latency during iterative analysis.

## 4. Senior Insights & Production Roadmap

### 4.A Solving the "Financial Data Retrieval" Challenge (Hybrid RAG)

Traditional RAG often fails on tabular financial data (e.g., balance sheets) due to period mismatches or numerical hallucination.

**Proposed Solution:** Implement a Text-to-SQL or Text-to-Pandas approach.

**Architecture:** Use a relational database (PostgreSQL/SQLite) for structured financial figures and a Vector Store (Milvus) strictly for unstructured narrative text (news, executive summaries). This ensures 100% numerical accuracy while maintaining semantic search capabilities.

### 4.B Scalability & Data Integrity

- **Fault Isolation:** Each worker is containerized in logic, ensuring that a failure in the vnstock scraper does not halt the AnalystAgent's internal logic.
- **Data Dump Strategy:** For tickers with heavy data protection, an offline ingestion pipeline to Milvus (with metadata filtering by ticker/quarter) is planned to bypass real-time scraping limits.

## 5. Tech Stack

- **Orchestration:** langchain, langchain-core
- **LLM Provider:** langchain-openai (GPT-4o)
- **Asynchronous I/O:** asyncio, aiohttp
- **Market Data:** vnstock (V3.4+)
- **Analysis:** pandas, numpy, textblob (Sentiment)
- **Environment:** python-dotenv (Python 3.9+ required)

## 6. Installation & Quick Start

### Setup Environment

```bash
python -m venv venv
source venv/bin/activate  # Or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Configure API Key

Create a `.env` file in the root directory:

```
OPENAI_API_KEY=sk-your-key-here
```

### Run Demo

```bash
python -m src.fin_agent_team.cli --interactive
```

### Run Verification Tests

```bash
python tests/test_full_workflow.py
```
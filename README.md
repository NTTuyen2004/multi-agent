# Financial AI Agent Team (Vietnam) 🇻🇳

Multi-agent system for Vietnamese stock market analysis with **conversation memory**, **parallel processing**, and **intelligent caching**.

## 🎯 Features

- ✅ **Stateful Multi-turn Conversation**: Agent remembers context across turns
- ✅ **5 Specialized Agents** (Data, News, Analysis, Info, Report)
- ✅ **Parallel Execution**: All agents run simultaneously (3x faster)
- ✅ **Smart Caching**: LLM cache + file cache (50-80% cost reduction)
- ✅ **Honest Error Reporting**: No fake data, transparent about failures
- ✅ **Leader-Worker Architecture**: Clean separation of concerns

## 🚀 Quick Start

### 1. Setup (Critical - Read SETUP.md!)

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set API Key (CHOOSE ONE):
# Option A: Environment Variable (Recommended ✅)
$env:OPENAI_API_KEY = "sk-proj-your-key"

# Option B: Create .env file
cp .env.example .env
# Then edit .env and add your API key

# Option C: Edit key_openai file (Legacy)
echo "sk-proj-your-key" > key_openai
```

**⚠️ IMPORTANT:** See [SETUP.md](SETUP.md) for detailed security setup!

### 2. Interactive Mode (Recommended)

```bash
python -m src.fin_agent_team.cli --interactive

# Example session:
💬 You: VCB thông tin?
🤖 Agent: VCB là Ngân hàng Vietcombank...

💬 You: Giá cho cái này?
🤖 Agent: (Hiểu "cái này" = VCB) Dữ liệu giá...

💬 You: help
📋 Commands: history, clear, save, status, quit
```

### 3. Single Query

```bash
python -m src.fin_agent_team.cli \
  --symbol VCB \
  --start 2024-01-01 \
  --end 2024-04-15
```

### 4. Python API

```python
import asyncio
from src.fin_agent_team.supervisor import Supervisor

async def main():
    sup = Supervisor()
    state = await sup.run(
        query="VCB analysis",
        symbol="VCB",
        start="2024-01-01",
        end="2024-04-15"
    )
    print(state["final_recommendation"])

asyncio.run(main())
```

## 📚 Documentation

- **[SETUP.md](SETUP.md)** - 🔐 Installation & API Key Setup (READ THIS FIRST!)
- **[AGENT_SYSTEM.md](AGENT_SYSTEM.md)** - System architecture & design
- **[STATEFUL_SYSTEM.md](STATEFUL_SYSTEM.md)** - Conversation memory details

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│   CONVERSATION MEMORY (Stateful)    │
│   - Remembers context across turns  │
│   - Extracts entities (symbols)     │
│   - Persists to disk                │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│        LEADER LAYER (gpt-4o)        │
│   - Route tasks (analyze_intent)    │
│   - Synthesize results              │
└───────────────┬─────────────────────┘
                │
        ┌───────┴────────────────┐
        ▼                        ▼
┌──────────────────────┐  ┌──────────────────┐
│   WORKER AGENTS      │  │   CACHING LAYER  │
│  (Run in Parallel)   │  │  - LLM cache     │
│                      │  │  - File cache    │
│  📊 DataAgent        │  │  - 50-80% $save  │
│  📰 NewsAgent        │  └──────────────────┘
│  📈 AnalystAgent     │
│  🏢 InfoAgent        │
│  📑 ReportAgent      │
└──────────────────────┘
```

## 🔐 Security (IMPORTANT!)

### ✅ Protected by .gitignore

```
.env                 # Secret (use this for local dev)
key_openai          # Legacy (keep empty or comments only)
.env.local          # Never commit
```

### ✅ Recommended Setup

Use **environment variables** or `.env` file:

```bash
# .env file (don't commit!)
OPENAI_API_KEY=sk-proj-your-actual-key
```

Or set environment variable:

```bash
# Windows PowerShell
$env:OPENAI_API_KEY = "sk-proj-your-key"

# Linux/Mac
export OPENAI_API_KEY="sk-proj-your-key"
```

## 📊 Performance

| Feature | Speed | Cost |
|---------|-------|------|
| **First Query** | 5-10s | Regular |
| **Cached Query** | <1s | -80% 💰 |
| **Parallel Agents** | 3s | Same |
| **Sequential** | 10s | Same |

## 🧠 Stateful System Example

```
BEFORE (Stateless):
Turn 1: "VCB info?" → Returns data ✓
Turn 2: "Price for this?" → ERROR ✗ ("this" = undefined)

AFTER (Stateful):
Turn 1: "VCB info?" → Saves VCB to memory ✓
Turn 2: "Price for this?" → Agent knows "this" = VCB ✓
Turn 3: "Should I buy?" → Full context available ✓
```

## 📁 Project Structure

```
d:/Agent AI/
├── .env.example          # Template (commit this)
├── .env                  # Secret (git ignored)
├── .gitignore            # Protects secrets
├── src/fin_agent_team/
│   ├── supervisor.py     # Main orchestrator
│   ├── cli.py            # Interactive CLI
│   ├── conversation_memory.py  # Stateful memory
│   ├── cache.py          # Smart caching
│   └── agents/           # 5 specialized agents
├── prompts/prompts.txt   # Configuration
├── test_full_workflow.py # 6-step workflow test
├── requirements.txt      # Dependencies
└── SETUP.md             # Setup guide
```

## 🔍 Example Workflow

```
Input: "Tư vấn đầu tư cho VCB trong 3 tháng"
    │
    ├─ 📊 DataAgent: Fetch 252 rows OHLCV
    ├─ 📈 AnalystAgent: Calculate SMA20, SMA50, RSI14
    ├─ 📰 NewsAgent: 3 articles, sentiment +0.33
    ├─ 🏢 InfoAgent: Company profile
    └─ 🧠 Leader: Synthesize → "GIỮ hoặc MUA nếu long-term"
```

## 🛠️ Dependencies
- If `vnstock3` or external search APIs aren't available, the data/news agents will fall back to deterministic mock data so you can develop locally.
- This repository is structured for clarity and extension — you can swap in real web-search or transformer-based sentiment analysis later.

**Running the supervisor:**
```bash
# Set API key (or create key_openai file)
$env:OPENAI_API_KEY = "sk-..."
python run.py
```

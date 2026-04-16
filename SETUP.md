# 🚀 Setup Hướng Dẫn - Financial AI Agent System

## 1️⃣ Prerequisites

- Python 3.9+
- OpenAI API Key (lấy từ https://platform.openai.com/api-keys)
- pip hoặc conda

---

## 2️⃣ Installation

### Clone hoặc Download

```bash
cd d:/Agent\ AI
```

### Tạo Virtual Environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 3️⃣ 🔐 Cấu Hình API Key (QUAN TRỌNG)

### ✅ Cách 1: Environment Variable (RECOMMENDED)

**Windows PowerShell:**
```powershell
$env:OPENAI_API_KEY = "sk-proj-your-actual-key-here"
```

**Windows Command Prompt:**
```cmd
set OPENAI_API_KEY=sk-proj-your-actual-key-here
```

**Linux/Mac:**
```bash
export OPENAI_API_KEY="sk-proj-your-actual-key-here"
```

### ✅ Cách 2: .env File (Gợi Ý)

1. Tạo file `.env` từ template:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` và điền API key:
   ```
   OPENAI_API_KEY=sk-proj-your-actual-key-here
   OPENAI_API_BASE=https://api.openai.com/v1
   ```

3. File sẽ tự động được load khi chạy hệ thống

⚠️ **IMPORTANT:** Đừng commit `.env` file lên Git! (`.gitignore` đã bảo vệ)

### ⚠️ Cách 3: key_openai File (Legacy - Không Recommended)

Nếu tuyệt đối phải dùng file:
```bash
echo "sk-proj-your-actual-key-here" > key_openai
```

---

## 4️⃣ Kiểm Tra Setup

```bash
# Activate venv
.venv\Scripts\activate

# Test import
python -c "from src.fin_agent_team.supervisor import Supervisor; print('✅ Setup OK!')"
```

---

## 5️⃣ Chạy Hệ Thống

### Interactive Mode (Recommended)

```bash
python -m src.fin_agent_team.cli --interactive
```

**Ví dụ:**
```
💬 You: VCB thông tin?
🤖 Agent: VCB là Ngân hàng Vietcombank...

💬 You: Lấy giá cho cái này?
🤖 Agent: (Hiểu "cái này" = VCB) Giá lịch sử...

💬 You: help
📋 Available commands:
  • history: Show conversation history
  • clear: Clear conversation
  • save: Save conversation
  • status: Show session info
  • quit: Exit

💬 You: save
✅ Conversation saved to: .cache/conversations/20240415_143022.json
```

### Single Query Mode

```bash
python -m src.fin_agent_team.cli \
  --symbol VCB \
  --query "Tư vấn đầu tư cho VCB" \
  --start 2024-01-01 \
  --end 2024-04-15
```

### Python API

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

---

## 6️⃣ Troubleshooting

### ❌ Error: "OPENAI_API_KEY not found"

**Giải pháp:**
1. Kiểm tra env var: `echo $env:OPENAI_API_KEY` (PowerShell)
2. Hoặc kiểm tra `.env` file tồn tại
3. Hoặc kiểm tra `key_openai` file không rỗng

### ❌ Error: "ModuleNotFoundError"

**Giải pháp:**
```bash
# Ensure venv is activated
.venv\Scripts\activate  # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### ❌ Error: "vnstock API blocked"

**Giải pháp:**
- vnstock có thể bị chặn theo địa phương
- System sẽ báo lỗi trung thực: "Không lấy được data"
- Các agents khác vẫn hoạt động bình thường

---

## 7️⃣ Project Structure

```
d:/Agent AI/
├── .env                  # 🔐 Secret (ignored by git)
├── .env.example          # Template (committed)
├── .gitignore            # Bảo vệ secrets
├── src/fin_agent_team/   # 💎 Core code
├── prompts/prompts.txt   # Configuration
├── test_full_workflow.py # Workflow test
├── run.py                # Legacy entry point
├── README.md             # Quick start
└── SETUP.md              # This file
```

---

## 8️⃣ Best Practices

✅ **DO:**
- Use environment variables for API keys
- Use `.env` file for local development
- Commit `.env.example` (NOT `.env`)
- Keep `key_openai` empty or comment-only
- Use virtual environment

❌ **DON'T:**
- Commit actual `.env` file
- Commit `key_openai` with real keys
- Share API keys in code
- Use hardcoded secrets

---

## Cần Giúp?

1. Check `AGENT_SYSTEM.md` - Mô tả hệ thống
2. Check `STATEFUL_SYSTEM.md` - Memory system
3. Check logs: `agent_debug.log`
4. Run tests: `python test_full_workflow.py`

---

**Happy analyzing! 🚀📈**

# 🧠 Stateful Multi-Turn Conversation System

## Overview

The system has been converted from **Stateless** to **Stateful**, meaning the agent now remembers context from previous conversations instead of starting fresh with each query.

### Problem Solved

**Before (Stateless):**
```
Turn 1: "Thông tin về VCB?"  → Agent retrieves VCB info
Turn 2: "Lấy giá lịch sử 3 tháng cho cái này?" → Agent confused: doesn't know what "cái này" is
```

**After (Stateful):**
```
Turn 1: "Thông tin về VCB?"  → Agent retrieves VCB info, saves to memory
Turn 2: "Lấy giá lịch sử 3 tháng cho cái này?" → Agent remembers: "cái này" = VCB!
```

## Architecture

### ConversationMemory Class
**File:** `src/fin_agent_team/conversation_memory.py`

Stores and manages:
- ✅ **Conversation history**: User queries and agent responses
- ✅ **Entity extraction**: Stock symbols, dates, keywords
- ✅ **Context inference**: User patterns and preferences
- ✅ **Session persistence**: Save/load conversations to file

**Key Methods:**
```python
memory = ConversationMemory()

# Record interactions
memory.add_user_message(query)
memory.add_agent_response(response)

# Get context for current query
context = memory.get_context_for_query("Lấy giá cho cái này?")
# Returns: recent_focus_symbol, previous_intents, user_patterns

# Persist
memory.save_to_file()
loaded_memory = ConversationMemory.load_from_file(path)
```

## Usage

### 1. Programmatic Usage

**Single Query (Stateless):**
```python
from src.fin_agent_team.supervisor import Supervisor

sup = Supervisor()
final_state = await sup.run(query="VCB", symbol="VCB")
```

**Multi-Turn (Stateful):**
```python
from src.fin_agent_team.supervisor import Supervisor
from src.fin_agent_team.conversation_memory import ConversationMemory

# Initialize with memory
memory = ConversationMemory()
sup = Supervisor(conversation_memory=memory)

# Turn 1
state1 = await sup.run(query="VCB info")

# Turn 2 - Agent remembers VCB from Turn 1
state2 = await sup.run(query="Price data for this?", 
                       conversation_memory=memory)

# Turn 3
state3 = await sup.run(query="Technical analysis", 
                       conversation_memory=memory)

# Save conversation
sup.save_conversation()
```

### 2. Interactive CLI Mode

**Start interactive mode with conversation memory:**
```bash
python -m src.fin_agent_team.cli --interactive
```

**Commands available:**
- `help` - Show available commands
- `history` - Display conversation history
- `clear` - Clear conversation, start fresh
- `save` - Persist conversation to file
- `status` - Show session info and tracked symbols
- `quit` - Exit

**Example session:**
```
💬 You: VCB の情報を教えてください
🤖 Agent: VCB はベトナムコムバンク...

💬 You: この株の過去3ヶ月の株価を取ってください
🤖 Agent: VCB の過去3ヶ月の株価データ...

💬 You: history
📝 Lịch sử cuộc hội thoại:
1. 👤 Người dùng: VCB의 정보를 알려주세요
2. 🤖 Agent: VCB는 베트남 상업 은행입니다...
```

### 3. Load Previous Session

```bash
# Save session
python -m src.fin_agent_team.cli --interactive --save

# Continue previous session
python -m src.fin_agent_team.cli --interactive --session .cache/conversations/20240101_120000.json
```

## How It Works

### 1. Entity Extraction

The system automatically extracts:
- **Symbols**: VCB, HPG, TCB, etc.
- **Date keywords**: "3 tháng", "1 năm", "tuần này"
- **Intent keywords**: "đầu tư", "báo cáo", "tin tức"

### 2. Context Enhancement

When analyzing intent or synthesizing response:

```python
# Original query:
query = "Lấy giá cho cái này?"

# Enhanced with context:
enhanced = """
Lấy giá cho cái này?
[Bối cảnh: Người dùng đang quan tâm mã VCB]
[Trước đó: Người dùng hỏi về company_info, news_analysis]
"""

# LLM makes better decision with context!
```

### 3. Memory Persistence

Conversations are stored in `.cache/conversations/`:
```json
{
  "session_id": "20240415_143022",
  "turns": [
    {
      "timestamp": "2024-04-15T14:30:22",
      "type": "user",
      "message": "VCB thông tin",
      "entities": {"symbols": ["VCB"]}
    },
    {
      "timestamp": "2024-04-15T14:30:25",
      "type": "agent",
      "message": "VCB là Ngân hàng Vietcombank...",
      "metadata": {"data_available": true}
    }
  ],
  "entities": {
    "last_symbol": "VCB",
    "all_symbols": ["VCB"]
  }
}
```

## Configuration

### Change Memory Limit

```python
# Default: 20 turns (40 messages)
memory = ConversationMemory(max_history=50)
```

### Custom Session ID

```python
memory = ConversationMemory(session_id="my_custom_session")
```

## Benefits

| Feature | Stateless | Stateful |
|---------|-----------|----------|
| Context memory | ❌ | ✅ |
| Pronoun resolution | ❌ | ✅ ("cho cái này" = VCB) |
| Pattern learning | ❌ | ✅ |
| Session persistence | ❌ | ✅ |
| Cost efficiency | ⚠️ | ✅ (reuse context) |
| User experience | Poor | Excellent |

## Examples

### Example 1: Investment Analysis Over Multiple Turns

```
Turn 1: "Bạn có thể cho tôi thông tin về VCB?"
→ Memory: {"symbols": ["VCB"]}

Turn 2: "Lấy giá lịch sử 1 năm cho mã này"
→ Agent UNDERSTANDS: "mã này" = VCB

Turn 3: "Phân tích kỹ thuật của nó"
→ Agent KNOWS: "nó" = VCB
→ Memory context suggests: previous_intents = ["company_info", "price_data"]

Turn 4: "Nên mua không?"
→ Agent SYNTHESIZES all prior context + latest data
→ → Decision informed by entire conversation history!
```

### Example 2: Comparative Analysis

```
Turn 1: "So sánh VCB và TCB"
→ Memory: {"symbols": ["VCB", "TCB"]}

Turn 2: "VCB có tốt hơn không?"
→ Agent KNOWS: comparing VCB vs TCB (from context)
→ Makes informed comparison

Turn 3: "Còn cái khác?"
→ Agent REMEMBERS: "cái khác" = TCB
```

## Files Changed

1. **NEW:** `src/fin_agent_team/conversation_memory.py` - Memory system
2. **UPDATED:** `src/fin_agent_team/supervisor.py` - Integrated memory in analyze_intent and synthesize
3. **UPDATED:** `src/fin_agent_team/cli.py` - Interactive multi-turn mode
4. **UPDATED:** `src/fin_agent_team/__init__.py` - Export conversation_memory

## Next Steps

1. ✅ Multi-turn conversation with memory
2. ⏳ User preference learning (favorite sectors, risk tolerance)
3. ⏳ Session recovery from crashes
4. ⏳ Analytics: "What symbols are users most interested in?"
5. ⏳ Multi-user support with isolated sessions

## Testing

Run the demo to see memory in action:
```bash
python demo_stateful.py
```

This will show:
- Multi-turn conversation with memory context
- Comparison of stateless vs stateful responses
- Memory persistence and entity tracking

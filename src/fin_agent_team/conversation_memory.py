"""Conversation memory management for stateful multi-turn interactions."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Manages conversation history and context for multi-turn agent interactions.
    
    Stores:
    - User queries and agent responses
    - Extracted entities (symbols, dates, etc.)
    - Previous analysis results for context
    - User preferences inferred from conversation
    """

    def __init__(self, session_id: Optional[str] = None, max_history: int = 20):
        """Initialize conversation memory.
        
        Args:
            session_id: Optional unique session identifier
            max_history: Maximum number of turns to keep in memory
        """
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.max_history = max_history
        self.turns: List[Dict[str, Any]] = []
        self.entities: Dict[str, Any] = {}  # symbols, dates, etc.
        self.inferred_context: Dict[str, Any] = {}

    def add_user_message(self, query: str) -> None:
        """Record a user query."""
        turn = {
            "timestamp": datetime.now().isoformat(),
            "type": "user",
            "message": query,
            "entities": self._extract_entities(query),
        }
        self.turns.append(turn)
        self._trim_history()
        logger.info("[ConversationMemory] Added user message: %s", query[:100])

    def add_agent_response(self, response: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record an agent response with optional metadata."""
        turn = {
            "timestamp": datetime.now().isoformat(),
            "type": "agent",
            "message": response,
            "metadata": metadata or {},
        }
        self.turns.append(turn)
        self._trim_history()
        logger.info("[ConversationMemory] Added agent response")

    def _extract_entities(self, query: str) -> Dict[str, Any]:
        """Extract entities from query (symbols, dates, etc.)."""
        entities = {}
        
        # Extract stock symbols (uppercase words like VCB, TCB, etc.)
        words = query.split()
        symbols = [w.upper() for w in words if 2 <= len(w) <= 5 and w.isupper()]
        if symbols:
            entities["symbols"] = symbols
            self.entities["last_symbol"] = symbols[0]
            self.entities["all_symbols"] = list(set(self.entities.get("all_symbols", []) + symbols))
        
        # Check for date-related keywords
        date_keywords = {
            "hôm nay": "today",
            "hôm qua": "yesterday",
            "tuần": "week",
            "tháng": "month",
            "năm": "year",
            "3 tháng": "3m",
            "6 tháng": "6m",
            "1 năm": "1y",
        }
        for vi_keyword, en_keyword in date_keywords.items():
            if vi_keyword.lower() in query.lower():
                entities["date_keyword"] = en_keyword
                break
        
        return entities

    def update_entities(self, **kwargs) -> None:
        """Update extracted entities."""
        self.entities.update(kwargs)
        logger.info("[ConversationMemory] Updated entities: %s", list(kwargs.keys()))

    def get_context_for_query(self, current_query: str) -> Dict[str, Any]:
        """Get relevant context for current query from conversation history."""
        context = {
            "current_query": current_query,
            "conversation_turn": len(self.turns) // 2,
            "last_symbols": self.entities.get("all_symbols", [])[-3:] if self.entities.get("all_symbols") else [],
            "recent_focus_symbol": self.entities.get("last_symbol"),
            "history_summary": self._summarize_history(),
            "previous_intents": self._extract_previous_intents(),
            "user_patterns": self._infer_user_patterns(),
        }
        
        logger.info("[ConversationMemory] Context for query: turn=%d, symbols=%s", 
                   context["conversation_turn"], context["last_symbols"])
        return context

    def _summarize_history(self) -> str:
        """Create a brief summary of recent conversation history."""
        if not self.turns:
            return "Bắt đầu cuộc hội thoại mới."
        
        recent = self.turns[-6:]  # Last 3 turns (user + agent pairs)
        summary_parts = []
        
        for turn in recent:
            if turn["type"] == "user":
                msg = turn["message"][:100]
                summary_parts.append(f"Người dùng hỏi: {msg}...")
            elif turn["type"] == "agent":
                msg = turn["message"][:80]
                summary_parts.append(f"Agent trả lời: {msg}...")
        
        return " | ".join(summary_parts) if summary_parts else "Không có lịch sử."

    def _extract_previous_intents(self) -> List[str]:
        """Extract what the user was trying to do in previous turns."""
        intents = []
        intent_keywords = {
            "đầu tư|mua|bán|giữ": "investment_decision",
            "thông tin|tra cứu|hồ sơ": "company_info",
            "giá|kỹ thuật|sma|rsi": "technical_analysis",
            "tin tức|sentiment": "news_analysis",
            "báo cáo|tài chính": "financial_report",
        }
        
        for turn in self.turns[-4:]:
            if turn["type"] == "user":
                msg = turn["message"].lower()
                for keywords, intent in intent_keywords.items():
                    if any(kw in msg for kw in keywords.split("|")):
                        if intent not in intents:
                            intents.append(intent)
        
        return intents

    def _infer_user_patterns(self) -> Dict[str, Any]:
        """Infer user preferences and patterns from conversation."""
        patterns = {
            "preferred_stock": self.entities.get("last_symbol"),
            "prefers_technical_analysis": "technical" in " ".join(t.get("message", "") for t in self.turns if t["type"] == "user").lower(),
            "prefers_fundamental_analysis": "tài chính" in " ".join(t.get("message", "") for t in self.turns if t["type"] == "user").lower(),
            "conversation_language": "vietnamese",  # Could detect this
            "total_turns": len(self.turns) // 2,
        }
        return patterns

    def _trim_history(self) -> None:
        """Keep only the most recent turns to avoid excessive memory."""
        if len(self.turns) > self.max_history:
            oldest_count = len(self.turns) - self.max_history
            self.turns = self.turns[oldest_count:]
            logger.info("[ConversationMemory] Trimmed history, kept %d turns", len(self.turns))

    def get_all_turns(self) -> List[Dict[str, Any]]:
        """Get all conversation turns."""
        return self.turns

    def get_formatted_history(self) -> str:
        """Get conversation history formatted for LLM context."""
        if not self.turns:
            return "Không có lịch sử cuộc hội thoại."
        
        lines = ["📝 Lịch sử cuộc hội thoại:"]
        for i, turn in enumerate(self.turns):
            role = "👤 Người dùng" if turn["type"] == "user" else "🤖 Agent"
            msg = turn["message"][:150]
            lines.append(f"{i+1}. {role}: {msg}")
        
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize memory to dict."""
        return {
            "session_id": self.session_id,
            "turns": self.turns,
            "entities": self.entities,
            "inferred_context": self.inferred_context,
            "timestamp": datetime.now().isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ConversationMemory:
        """Deserialize memory from dict."""
        memory = cls(session_id=data.get("session_id"))
        memory.turns = data.get("turns", [])
        memory.entities = data.get("entities", {})
        memory.inferred_context = data.get("inferred_context", {})
        return memory

    def save_to_file(self, path: Optional[Path] = None) -> Path:
        """Persist conversation to file."""
        if path is None:
            cache_dir = Path(".cache/conversations")
            cache_dir.mkdir(parents=True, exist_ok=True)
            path = cache_dir / f"{self.session_id}.json"
        
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info("[ConversationMemory] Saved to %s", path)
        return path

    @classmethod
    def load_from_file(cls, path: Path) -> ConversationMemory:
        """Load conversation from file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        memory = cls.from_dict(data)
        logger.info("[ConversationMemory] Loaded from %s", path)
        return memory

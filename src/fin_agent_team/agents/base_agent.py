"""Base agent class with reasoning capability."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for all agents with LLM reasoning capability."""

    def __init__(self, llm: Optional[ChatOpenAI] = None) -> None:
        """Initialize agent with optional LLM for reasoning."""
        self.llm = llm
        self._model = "gpt-4o-mini" if llm is None else llm.model

    async def think(self, context: str, task: str) -> str:
        """Generate reasoning/thought process before acting."""
        if self.llm is None:
            return f"[local thought] Chuẩn bị thực hiện: {task}"

        sys_msg = SystemMessage(content="Bạn là một agent thông minh. Hãy suy luận ngắn gọn về cách tiếp cận nhiệm vụ.")
        human_msg = HumanMessage(content=f"Ngữ cảnh: {context}\n\nNhiệm vụ: {task}")

        try:
            response = await asyncio.to_thread(
                lambda: self.llm.invoke([sys_msg, human_msg])
            )
            return str(response.content)
        except Exception as e:
            logger.warning("[BaseAgent.think] LLM failed, using default thought: %s", e)
            return f"[local thought] {task}"

    @staticmethod
    def _format_thought(task: str, symbol: Optional[str] = None, extra: str = "") -> str:
        """Format a standard thought message."""
        parts = [f"Thực hiện: {task}"]
        if symbol:
            parts.append(f"Mục tiêu: {symbol}")
        if extra:
            parts.append(extra)
        return " | ".join(parts)


__all__ = ["BaseAgent"]

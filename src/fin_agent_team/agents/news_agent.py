"""News agent: performs web-search-like article extraction and simple sentiment.

This agent provides a simple, language-agnostic fallback sentiment scanner
based on token matching (useful for Vietnamese keywords). It's intentionally
pluggable so you can replace the search/sentiment implementation later.
"""
from __future__ import annotations

import asyncio
from typing import Dict, List, Any


class NewsAgent:
    async def fetch_news_and_sentiment(self, query: str) -> Dict[str, Any]:
        return await asyncio.to_thread(self._blocking_fetch, query)

    def _blocking_fetch(self, query: str) -> Dict[str, Any]:
        # Deterministic faux articles
        articles = [
            {"title": f"{query} tăng trong quý gần đây", "snippet": "Cổ phiếu tăng trưởng tích cực"},
            {"title": f"Cập nhật: {query} và thị trường", "snippet": "Một số rủi ro ngắn hạn"},
            {"title": f"Phân tích {query}", "snippet": "Nhà đầu tư kỳ vọng lợi nhuận"},
        ]

        # Very small Vietnamese-focused lexicon for demo sentiment
        pos = ["tăng", "tích cực", "kỳ vọng", "lợi nhuận", "tốt"]
        neg = ["giảm", "rủi ro", "tiêu cực", "thua lỗ", "khó khăn"]

        def score_text(text: str) -> float:
            t = text.lower()
            s = 0
            for p in pos:
                if p in t:
                    s += 1
            for n in neg:
                if n in t:
                    s -= 1
            # Normalize to roughly [-1, 1]
            if s == 0:
                return 0.0
            return max(-1.0, min(1.0, s / 3.0))

        scores = [score_text(a["title"] + " " + a["snippet"]) for a in articles]
        sentiment = {
            "article_count": len(articles),
            "average_score": float(sum(scores) / len(scores)),
            "scores": scores,
        }
        return {"query": query, "articles": articles, "sentiment": sentiment}


__all__ = ["NewsAgent"]

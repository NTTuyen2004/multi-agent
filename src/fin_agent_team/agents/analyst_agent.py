"""Analyst agent: computes SMA and RSI using pandas."""
from __future__ import annotations

import asyncio
from typing import Dict, Any

import pandas as pd


class AnalystAgent:
    async def compute_indicators(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Compute SMA and RSI for the given dataframe (expects 'close')."""
        return await asyncio.to_thread(self._blocking_compute, symbol, df)

    def _blocking_compute(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        if df is None or df.empty:
            return {"symbol": symbol, "indicators": {}}

        indicators: Dict[str, Any] = {}
        close = df["close"].astype(float)

        # Simple Moving Averages
        # Simple Moving Averages (THÊM HÀM float() BAO NGOÀI)
        indicators["sma_20"] = float(close.rolling(window=20, min_periods=1).mean().iloc[-1])
        indicators["sma_50"] = float(close.rolling(window=50, min_periods=1).mean().iloc[-1])

        # RSI (14)
        delta = close.diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        roll_up = up.rolling(14, min_periods=1).mean()
        roll_down = down.rolling(14, min_periods=1).mean()
        rs = roll_up / (roll_down + 1e-9)
        rsi = 100.0 - (100.0 / (1.0 + rs))
        indicators["rsi_14"] = float(rsi.iloc[-1])

        return {"symbol": symbol, "indicators": indicators}


__all__ = ["AnalystAgent"]

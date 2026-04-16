"""Report agent: Generates comprehensive report by aggregating all agent insights."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ReportAgent(BaseAgent):
    """Agent that generates comprehensive stock analysis report from VN market data."""

    def __init__(self, llm: Optional[ChatOpenAI] = None) -> None:
        super().__init__(llm)

    async def generate_report(
        self,
        symbol: str,
        query: str,
        report_type: str = 'IncomeStatement',
        frequency: str = 'Quarterly',
    ) -> Dict[str, Any]:
        """
        Fetches financial reports (IncomeStatement, BalanceSheet) for a stock symbol.
        This function is designed to fail gracefully if the data source is blocked,
        and it will report the failure honestly.

        Args:
            symbol: The stock symbol (e.g., 'VCB', 'FPT').
            query: The original user query.
            report_type: 'IncomeStatement' or 'BalanceSheet'.
            frequency: 'Quarterly' or 'Yearly'.

        Returns:
            A dictionary containing the report data or an error message.
        """
        logger.info(
            "[report.generate_report] Fetching %s %s for %s",
            frequency,
            report_type,
            symbol,
        )

        try:
            # This is the part that is expected to fail due to the source being blocked.
            # We keep it to ensure the agent learns to handle the failure.
            from vnstock import company
            
            financial_data = await asyncio.to_thread(
                company.financial_report,
                symbol=symbol,
                report_type=report_type,
                frequency=frequency,
            )

            if financial_data is None or financial_data.empty:
                raise ValueError("No data returned from financial_report.")

            # If it somehow succeeds, process the data.
            records = financial_data.to_dict(orient='records')
            
            return {
                "symbol": symbol,
                "query": query,
                "report_type": report_type,
                "frequency": frequency,
                "thought": f"Successfully fetched {len(records)} records for {symbol}.",
                "generated_at": datetime.now().isoformat(),
                "summary": f"Fetched {len(records)} records of {frequency} {report_type} for {symbol}.",
                "records": records,
                "error": None,
            }

        except Exception as e:
            error_message = f"Không thể lấy được báo cáo tài chính ({report_type}) cho mã {symbol}. Nguồn dữ liệu có thể đang bị chặn hoặc có lỗi xảy ra: {str(e)}"
            logger.error("[report.generate_report] failed: %s", error_message)
            return {
                "symbol": symbol,
                "query": query,
                "report_type": report_type,
                "frequency": frequency,
                "thought": f"Attempted to fetch financial data for {symbol} but failed.",
                "generated_at": datetime.now().isoformat(),
                "summary": f"Lỗi khi lấy báo cáo tài chính cho {symbol}.",
                "records": [],
                "error": error_message,
            }

    def _build_summary(self, symbol: str, market_data: Dict, records: list) -> str:
        close = market_data.get('latest_close', 'N/A')
        rows = market_data.get('total_rows', 0)
        record_count = len(records)
        return f"Mã: {symbol} | close={close} | rows={rows} | records={record_count}"

    def _build_markdown(self, symbol: str, query: str, market_data: Dict, records: list) -> str:
        # Returns a simple JSON dump for now, as per previous refactoring.
        # The primary goal is data integrity, not formatting.
        output = {
            "symbol": symbol,
            "query": query,
            "market_data": market_data,
            "records": records[:5],  # Limit records in markdown for brevity
        }
        return json.dumps(output, indent=2, ensure_ascii=False)


    async def _fetch_vn_stock_records(self, symbol: str, period: str = "1y") -> list:
        """Fetch VN stock records for report."""
        return await asyncio.to_thread(self._blocking_fetch_records, symbol, period)

    @staticmethod
    def _blocking_fetch_records(symbol: str, period: str = "1y") -> list:
        """Blocking fetch of VN stock records."""
        try:
            from vnstock import Quote
            import pandas as pd
            
            quote = Quote(symbol=symbol)
            
            # Map period to date range
            period_map = {
                "1m": ("2024-11-01", "2024-12-01"),
                "3m": ("2024-09-01", "2024-12-01"),
                "6m": ("2024-06-01", "2024-12-01"),
                "1y": ("2023-12-01", "2024-12-01"),
                "2y": ("2022-12-01", "2024-12-01"),
            }
            
            start, end = period_map.get(period, ("2023-12-01", "2024-12-01"))
            
            df = quote.history(start=start, end=end)
            
            if df is None or df.empty:
                return []
            
            # Convert to records
            records = []
            for idx, row in df.iterrows():
                records.append({
                    "date": str(idx) if hasattr(idx, '__str__') else str(idx),
                    "open": float(row.get("open", 0)) if "open" in row else None,
                    "close": float(row.get("close", 0)) if "close" in row else None,
                    "high": float(row.get("high", 0)) if "high" in row else None,
                    "low": float(row.get("low", 0)) if "low" in row else None,
                    "volume": float(row.get("volume", 0)) if "volume" in row else None,
                })
            
            return records[-20:]  # Return last 20 records
            
        except Exception as e:
            logger.warning("[ReportAgent._blocking_fetch_records] Failed: %s", e)
            return []

    @staticmethod
    def _generate_markdown_report(symbol: str, query: str, market_data: Dict) -> str:
        """Backward-compatible wrapper for older callers."""
        return ReportAgent._build_markdown(symbol, query, market_data, [])

    @staticmethod
    def _build_summary(symbol: str, market_data: Dict[str, Any], records: list) -> str:
        if market_data.get("status") == "success":
            parts = [f"Mã: {symbol}"]
            if market_data.get("latest_close") is not None:
                parts.append(f"close={market_data.get('latest_close')}")
            if market_data.get("total_rows") is not None:
                parts.append(f"rows={market_data.get('total_rows')}")
            if records:
                parts.append(f"records={len(records)}")
            return " | ".join(parts)
        return f"Không lấy được dữ liệu cho mã {symbol}"

    @staticmethod
    def _build_markdown(symbol: str, query: str, market_data: Dict[str, Any], records: list) -> str:
        payload = {
            "symbol": symbol,
            "query": query,
            "market_data": market_data,
            "records": records[-5:] if records else [],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)


__all__ = ["ReportAgent"]

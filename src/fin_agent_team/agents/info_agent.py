"""Info agent: Fetch company profile data from vnstock."""
from __future__ import annotations

import asyncio
import contextlib
import io
import logging
from typing import Any, Dict

import pandas as pd
from vnstock import Company

logger = logging.getLogger(__name__)


class InfoAgent:
	"""Fetches company profile data from vnstock with a safe fallback."""

	SOURCE_PRIORITY = ("KBS", "VCI")
	TIMEOUT = 20  # seconds

	@staticmethod
	@contextlib.contextmanager
	def _suppress_library_output():
		"""Hide noisy stdout/stderr from vnstock banners and notices."""
		with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
			yield

	async def fetch_info(self, symbol: str) -> Dict[str, Any]:
		"""Fetch company profile info for symbol from vnstock."""
		logger.info("[info.fetch_info] symbol=%s", symbol)
		try:
			return await asyncio.wait_for(
				asyncio.to_thread(self._blocking_fetch, symbol),
				timeout=self.TIMEOUT,
			)
		except asyncio.TimeoutError:
			logger.error("[info.fetch_info] timeout symbol=%s", symbol)
			return self._fallback_payload(symbol, "Timeout khi lấy dữ liệu từ vnstock")

	def _blocking_fetch(self, symbol: str) -> Dict[str, Any]:
		"""Fetch company profile data from vnstock."""
		clean_symbol = symbol.strip().upper()
		logger.info("[info.blocking_fetch] start symbol=%s", clean_symbol)

		try:
			with self._suppress_library_output():
				for source in self.SOURCE_PRIORITY:
					try:
						company = Company(symbol=clean_symbol, source=source, show_log=False)
						overview = company.overview()
						profile = self._normalize_overview(clean_symbol, source, overview)
						if profile:
							logger.info("[info.blocking_fetch] success symbol=%s source=%s", clean_symbol, source)
							return profile
					except Exception as exc:
						logger.warning("[info.blocking_fetch] source=%s failed symbol=%s error=%s", source, clean_symbol, exc)

			logger.warning("[info.blocking_fetch] all vnstock sources failed symbol=%s", clean_symbol)
		except Exception as e:
			logger.exception("[info.blocking_fetch] vnstock error: %s", e)

		return self._fallback_payload(clean_symbol, "Không lấy được hồ sơ doanh nghiệp từ vnstock")

	def _normalize_overview(self, symbol: str, source: str, overview: Any) -> Dict[str, Any] | None:
		"""Normalize vnstock overview result into a stable dict shape."""
		row: Dict[str, Any] | None = None

		if isinstance(overview, pd.DataFrame):
			if overview.empty:
				return None
			row = overview.iloc[0].to_dict()
		elif isinstance(overview, dict):
			row = overview
		elif isinstance(overview, list) and overview:
			first = overview[0]
			row = first if isinstance(first, dict) else {"value": first}
		else:
			return None

		if not row:
			return None

		markdown = self._build_markdown(symbol, row)
		summary = self._build_summary(symbol, row)
		return {
			"symbol": row.get("symbol", symbol),
			"source": f"vnstock_{source}",
			"company_type": row.get("company_type"),
			"exchange": row.get("exchange"),
			"ceo_name": row.get("ceo_name"),
			"ceo_position": row.get("ceo_position"),
			"founded_date": row.get("founded_date"),
			"charter_capital": row.get("charter_capital"),
			"number_of_employees": row.get("number_of_employees"),
			"website": row.get("website"),
			"address": row.get("address"),
			"business_model": row.get("business_model"),
			"history": row.get("history"),
			"raw_data": row,
			"summary": summary,
			"markdown": markdown,
			"error": None,
		}

	@staticmethod
	def _build_summary(symbol: str, row: Dict[str, Any]) -> str:
		"""Build a concise one-line summary for logs and supervisor output."""
		parts = [f"Mã: {symbol}"]
		if row.get("company_type"):
			parts.append(f"Loại hình: {row.get('company_type')}")
		if row.get("exchange"):
			parts.append(f"Sàn: {row.get('exchange')}")
		if row.get("ceo_name"):
			parts.append(f"CEO: {row.get('ceo_name')}")
		if row.get("founded_date"):
			parts.append(f"Thành lập: {row.get('founded_date')}")
		return " | ".join(parts)

	@staticmethod
	def _build_markdown(symbol: str, row: Dict[str, Any]) -> str:
		"""Build compact markdown summary for the LLM."""
		fields = []
		fields.append(f"# Thông tin doanh nghiệp - {symbol}")
		fields.append("")
		fields.append(f"- Mã: {row.get('symbol', symbol)}")
		if row.get("company_type"):
			fields.append(f"- Loại hình: {row.get('company_type')}")
		if row.get("exchange"):
			fields.append(f"- Sàn: {row.get('exchange')}")
		if row.get("founded_date"):
			fields.append(f"- Thành lập: {row.get('founded_date')}")
		if row.get("ceo_name"):
			fields.append(f"- CEO: {row.get('ceo_name')}")
		if row.get("charter_capital"):
			fields.append(f"- Vốn điều lệ: {row.get('charter_capital')}")
		if row.get("website"):
			fields.append(f"- Website: {row.get('website')}")
		if row.get("address"):
			fields.append(f"- Địa chỉ: {row.get('address')}")
		return "\n".join(fields)

	@staticmethod
	def _fallback_payload(symbol: str, note: str) -> Dict[str, Any]:
		return {
			"symbol": symbol,
			"source": "vnstock_fallback",
			"company_type": None,
			"exchange": None,
			"ceo_name": None,
			"ceo_position": None,
			"founded_date": None,
			"charter_capital": None,
			"number_of_employees": None,
			"website": None,
			"address": None,
			"business_model": None,
			"history": None,
			"raw_data": {},
			"summary": f"Mã: {symbol} | Không lấy được dữ liệu từ vnstock",
			"markdown": f"# Thông tin doanh nghiệp - {symbol}\n\n{note}",
			"error": note,
		}


__all__ = ["InfoAgent"]

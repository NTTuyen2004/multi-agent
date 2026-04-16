"""Data agent: fetches OHLCV for Vietnam stocks using vnstock (latest version) with a safe fallback."""
from __future__ import annotations

import asyncio
import contextlib
import io
import os

import pandas as pd
import numpy as np


class DataAgent:
    """Agent that provides historical OHLCV data."""

    _COLUMN_ALIASES = {
        "time": "date",
        "date": "date",
        "datetime": "date",
        "timestamp": "date",
        "trading_date": "date",
        "tradingdate": "date",
        "open": "open",
        "open_price": "open",
        "price_open": "open",
        "high": "high",
        "high_price": "high",
        "price_high": "high",
        "low": "low",
        "low_price": "low",
        "price_low": "low",
        "close": "close",
        "close_price": "close",
        "price_close": "close",
        "volume": "volume",
        "vol": "volume",
        "matched_volume": "volume",
    }

    _REQUIRED_COLUMNS = ["open", "high", "low", "close", "volume"]

    @staticmethod
    @contextlib.contextmanager
    def _suppress_library_output():
        """Hide noisy third-party stdout/stderr banners from terminal output."""
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            yield

    async def fetch_ohlcv(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """Fetch OHLCV for symbol between start and end.

        The returned dataframe is normalized to a stable schema:
        DatetimeIndex named ``date`` with columns ``open``, ``high``, ``low``, ``close``,
        and ``volume``. If vnstock is unavailable and USE_SYNTHETIC_DATA=1, a deterministic
        fallback dataframe with the same schema is returned.
        """
        return await asyncio.to_thread(self._fetch_blocking, symbol, start, end)

    def _fetch_blocking(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        # Approach 1: Use Quote class directly (simpler & more reliable)
        try:
            with self._suppress_library_output():
                from vnstock import Quote
                quote = Quote(symbol=symbol)

            with self._suppress_library_output():
                df = quote.history(start=start, end=end)

            return self._normalize_ohlcv_frame(df, symbol)

        except Exception as e:
            print(f"⚠️ [DataAgent] Quote class failed: {e}")
            
            # Approach 2: Try Vnstock with KBS source (fallback)
            try:
                with self._suppress_library_output():
                    from vnstock import Vnstock
                    vs = Vnstock()
                    stock = vs.stock(symbol=symbol, source="KBS")
                    df = stock.quote.history(start=start, end=end)

                return self._normalize_ohlcv_frame(df, symbol)
                
            except ImportError:
                if os.getenv("USE_SYNTHETIC_DATA", "0") == "1":
                    print("⚠️ [DataAgent] Chưa cài vnstock — Chuyển sang dùng dữ liệu giả (Synthetic)")
                    return self._synthetic(symbol, start, end)
                raise RuntimeError("Chưa cài thư viện vnstock. Hãy chạy lệnh: pip install vnstock --upgrade")
                
            except Exception as e:
                print(f"❌ [DataAgent] LỖI GỌI VNSTOCK: {e}")
                if os.getenv("USE_SYNTHETIC_DATA", "0") == "1":
                    print("⚠️ [DataAgent] Lỗi kết nối API — Chuyển sang dùng dữ liệu giả (Synthetic).")
                    return self._synthetic(symbol, start, end)
                raise RuntimeError(f"Không thể lấy dữ liệu thực tế cho mã {symbol}. Chi tiết: {e}")

    def _normalize_ohlcv_frame(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        if df is None or df.empty:
            raise ValueError(f"Dữ liệu trả về rỗng cho mã {symbol}.")

        frame = df.copy()
        frame.columns = [str(column).strip().lower() for column in frame.columns]
        frame = frame.rename(columns={column: self._COLUMN_ALIASES.get(column, column) for column in frame.columns})

        if "date" in frame.columns:
            frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
            frame = frame.dropna(subset=["date"])
            frame = frame.set_index("date")
        else:
            if not isinstance(frame.index, pd.DatetimeIndex):
                frame.index = pd.to_datetime(frame.index, errors="coerce")
            frame.index.name = "date"

        frame = frame.sort_index()

        for column in self._REQUIRED_COLUMNS:
            if column not in frame.columns:
                raise ValueError(f"Dữ liệu cho mã {symbol} thiếu cột bắt buộc: {column}.")
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

        frame = frame[self._REQUIRED_COLUMNS].dropna(subset=["close"])
        frame.index.name = "date"
        return frame

    def _synthetic(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """Hàm sinh dữ liệu giả định (Fallback) nếu vnstock bị lỗi mạng."""
        rng = np.random.RandomState(abs(hash(symbol)) % (2 ** 32))
        dates = pd.date_range(start=start, end=end, freq="B")
        n = len(dates)
        base = 100 + (rng.rand() - 0.5) * 10
        changes = rng.normal(loc=0, scale=1, size=n).cumsum()
        close = (base + changes).round(2)
        open_ = (close + rng.normal(0, 0.5, size=n)).round(2)
        high = np.maximum(open_, close) + rng.rand(n)
        low = np.minimum(open_, close) - rng.rand(n)
        volume = (rng.randint(1000, 10000, size=n)).astype(int)
        
        df = pd.DataFrame(
            {
                "open": open_,
                "high": high.round(2),
                "low": low.round(2),
                "close": close,
                "volume": volume,
            },
            index=dates,
        )
        df.index.name = "date"
        return df

__all__ = ["DataAgent"]
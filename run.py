#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Main entry point for Multi-Agent Stock Advisory System."""
import asyncio
import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
import traceback
import sys
import os
from pathlib import Path

# Cap BLAS threads early to avoid OpenBLAS memory spikes on low-memory Windows setups.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("BLIS_NUM_THREADS", "1")

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from fin_agent_team.supervisor import Supervisor


def setup_logging() -> None:
    log_path = Path(__file__).parent / "agent_debug.log"
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if root_logger.handlers:
        return

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def _format_value(value):
    if value is None:
        return ""
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item) for item in value if item not in (None, ""))
    return str(value)


def _print_brief_step(title: str, node_state: dict) -> None:
    print(f"=== {title} ===")

    thought = node_state.get("thought")
    action = node_state.get("action")
    arguments = node_state.get("arguments")
    route = node_state.get("route")
    error = node_state.get("error")  # Check for a single error field

    if thought:
        print(f" THOUGHT: {_format_value(thought)}")
    if action:
        print(f" ACTION: {_format_value(action)}")
    if arguments:
        print(f" ARGUMENTS: {_format_value(arguments)}")
    
    # Determine status based on the presence of an error
    status = "ERROR" if error else "OK"
    print(f" Status: {status}")

    if error:
        print(f" ERROR_DETAILS: {_format_value(error)}")

    # Display route decision for supervisor
    if route and isinstance(route, list) and len(route) > 0:
        agent_icons = {
            "data": " DATA_AGENT",
            "news": " NEWS_AGENT",
            "analysis": " ANALYST_AGENT",
            "info": " INFO_AGENT",
            "report": " REPORT_AGENT"
        }
        print(f"  ROUTE DECISION:")
        for i, agent in enumerate(route):
            is_last = (i == len(route) - 1)
            prefix = "└─ " if is_last else "├─ "
            agent_name = agent_icons.get(agent, f" {agent.upper()}")
            print(f"   {prefix}{agent_name}")
    
    if error:
        print(f"  ERROR: {_format_value(error)}")
    else:
        print(" Status: OK")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Multi-Agent Financial Assistant")
    parser.add_argument("--query", type=str, default="", help="User query")
    parser.add_argument("--symbol", type=str, default="VCB", help="Stock ticker")
    parser.add_argument("--start", type=str, default="2024-03-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default="2024-04-10", help="End date (YYYY-MM-DD)")
    parser.add_argument("--period", type=str, default="1y", help="Report period (1m/3m/6m/1y/2y)")
    return parser.parse_args()


async def main():
    setup_logging()
    args = _parse_args()

    print(" Đang khởi động Hệ thống Multi-Agent Tư vấn Chứng khoán...\n")

    query = "•	Truy xuất và thống kê dữ liệu giá lịch sử (open, high, low, close, volume) cho từng mã VCB, hỗ trợ lọc theo ngày hoặc khung thời gian cụ thể. (ví dụ: 3 tháng gần nhất, từ 2023-01-01 đến 2023-06-30)."
    symbol = "VCB"

    payload = {
        "query": query,
        "symbol": symbol,
        "start": args.start,
        "end": args.end,
        "period": args.period,
    }

    print(f"👤 Người dùng: {query}\n")
    print("-" * 70)

    try:
        supervisor = Supervisor()
        async for step in supervisor.stream(payload):
            node_name = step.get("node_name", "")
            state = step.get("node_state", {})

            if node_name == "supervisor":
                _print_brief_step(" AGENT_MAIN (Điều phối)", state)
                print()

            elif node_name == "data_worker":
                _print_brief_step("DATA_AGENT (Dữ liệu giá)", state)
                print()

            elif node_name == "news_worker":
                _print_brief_step(" NEWS_AGENT (Tin tức)", state)
                print()

            elif node_name == "analyst_worker":
                _print_brief_step(" ANALYST_AGENT (Kỹ thuật)", state)
                print()

            elif node_name == "info_worker":
                _print_brief_step(" INFO_AGENT (Thông tin doanh nghiệp)", state)
                print()

            elif node_name == "report_worker":
                _print_brief_step(" REPORT_AGENT (Báo cáo tổng hợp)", state)
                print()

            elif node_name == "final_report":
                print("\n" + "=" * 70)
                print("🎬 FINAL_REPORT (Kết luận cuối cùng)")
                print("=" * 70)
                print(state.get("final_recommendation"))
                print("=" * 70 + "\n")
    except Exception as exc:
        print("❌ Chạy hệ thống thất bại.")
        print(f"   Lỗi: {exc}")
        if "OPENAI_API_KEY" in str(exc):
            print("   Gợi ý: thêm key vào biến môi trường OPENAI_API_KEY hoặc file key_openai.")
        logging.getLogger(__name__).error("run.py failed: %s", traceback.format_exc())


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())

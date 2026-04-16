#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test full workflow with sequential queries for VCB (Vietcombank)."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from fin_agent_team.supervisor import Supervisor


async def test_full_workflow():
    """
    Test the full agent workflow with a sequence of related queries about VCB.
    Each query builds on the previous one, testing contextual understanding.
    """
    print("\n" + "="*80)
    print("FULL WORKFLOW TEST: VCB (Vietcombank)")
    print("="*80)
    
    supervisor = Supervisor()
    
    # Define a sequence of queries following the workflow
    queries = [
        {
            "step": 1,
            "title": "Tra cứu thông tin doanh nghiệp VCB",
            "query": "Tra cứu thông tin doanh nghiệp dựa theo mã chứng khoán VCB",
            "symbol": "VCB",
        },
        {
            "step": 2,
            "title": "Truy xuất dữ liệu giá lịch sử 3 tháng",
            "query": "Truy xuất và thống kê dữ liệu giá lịch sử (open, high, low, close, volume) cho VCB trong 3 tháng gần nhất",
            "symbol": "VCB",
            "start": "2024-01-01",
            "end": "2024-04-01",
        },
        {
            "step": 3,
            "title": "Phân tích kỹ thuật với SMA và RSI",
            "query": "Tính toán chỉ số phân tích kỹ thuật SMA20, SMA50 và RSI14 cho mã VCB để đánh giá xu hướng",
            "symbol": "VCB",
            "start": "2024-01-01",
            "end": "2024-04-01",
        },
        {
            "step": 4,
            "title": "Đánh giá sentiment từ tin tức",
            "query": "Truy cập tin tức về VCB để đánh giá sentiment của các mã, các nhóm cổ phiếu ngân hàng",
            "symbol": "VCB",
        },
        {
            "step": 5,
            "title": "Báo cáo tài chính VCB",
            "query": "Agent có thể truy cập các báo cáo tài chính, các báo cáo phân tích của ngân hàng VCB để tổng hợp đánh giá",
            "symbol": "VCB",
        },
        {
            "step": 6,
            "title": "Tư vấn đầu tư cho VCB",
            "query": "Dựa vào tất cả thông tin đã thu thập (dữ liệu giá, kỹ thuật, tin tức, báo cáo tài chính), hãy đưa ra tư vấn đầu tư cho VCB - có nên mua, giữ hay bán?",
            "symbol": "VCB",
            "start": "2024-01-01",
            "end": "2024-04-01",
        },
    ]
    
    # Run each query in sequence
    for query_info in queries:
        step = query_info["step"]
        title = query_info["title"]
        query = query_info["query"]
        symbol = query_info.get("symbol", "")
        start = query_info.get("start", "2023-01-01")
        end = query_info.get("end", "2024-01-01")
        
        print(f"\n{'='*80}")
        print(f" STEP {step}: {title}")
        print(f"{'='*80}")
        print(f" Query: {query}\n")
        
        payload = {
            "query": query,
            "symbol": symbol,
            "start": start,
            "end": end,
        }
        
        try:
            print(" Processing...")
            final_state = await supervisor.run(**payload)
            
            # Extract and display key results
            final_rec = final_state.get("final_recommendation", "")
        
            print(f"\n Result:")
            print("-" * 80)
            
            # Show first 500 characters of recommendation, then ellipsis
            if len(final_rec) > 500:
                print(final_rec[:500] + "...\n[Content truncated]")
            else:
                print(final_rec)
            
            print("-" * 80)
            
            # Show data availability - safely check for empty/None
            ohlcv = final_state.get("data", {}).get("ohlcv")
            has_data = ohlcv is not None and len(ohlcv) > 0 if hasattr(ohlcv, '__len__') else bool(ohlcv)
            has_news = final_state.get("news") is not None
            has_analysis = final_state.get("analysis") is not None
            has_info = final_state.get("info") is not None
            has_report = final_state.get("report") is not None
            
            print(f"\n Data Status:")
            print(f"   • Price Data (OHLCV): {'✓' if has_data else '✗'}")
            print(f"   • News & Sentiment: {'✓' if has_news else '✗'}")
            print(f"   • Technical Analysis: {'✓' if has_analysis else '✗'}")
            print(f"   • Company Info: {'✓' if has_info else '✗'}")
            print(f"   • Financial Report: {'✓' if has_report else '✗'}")
            
            # Check for errors
            errors = final_state.get("errors", {})
            if errors:
                print(f"\n  Errors encountered:")
                for agent, error_msg in errors.items():
                    print(f"   • {agent}: {error_msg}")
            
        except Exception as e:
            print(f"\n Error: {e}")
            import traceback
            traceback.print_exc()
        
        # Separator between steps
        if step < len(queries):
            print(f"\n Moving to next step...\n")
    
    print(f"\n{'='*80}")
    print("✅ WORKFLOW TEST COMPLETED")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(test_full_workflow())

"""Supervisor module with clear leader-worker layering and pure state yielding."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, AsyncGenerator, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.globals import set_llm_cache
from langchain_core.caches import InMemoryCache

from .agents import AnalystAgent, DataAgent, InfoAgent, NewsAgent, ReportAgent
from .types import AgentState, DecisionState
from .cache import cache_result
from .conversation_memory import ConversationMemory

# Kích hoạt Cache trên RAM cho tất cả LLM calls
set_llm_cache(InMemoryCache())

_ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger(__name__)


def load_prompts() -> Dict[str, Any]:
    """Load prompt config from prompts/prompts.txt as JSON."""
    prompt_path = _ROOT / "prompts" / "prompts.txt"
    try:
        return json.loads(prompt_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"⚠️ Cảnh báo: Không đọc được file prompts ({exc}).")
        return {}


def get_openai_key() -> str:
    """
    Resolve API key from environment variable or key_openai file.
    Priority: 1) OPENAI_API_KEY env var, 2) .env file, 3) key_openai file
    """
    # Priority 1: Environment variable (recommended ✅)
    key = os.getenv("OPENAI_API_KEY")
    if key and key.strip().startswith("sk-"):
        logger.info("✅ Using OPENAI_API_KEY from environment variable")
        return key.strip()
    
    # Priority 2: Load from .env file if python-dotenv available
    try:
        from dotenv import load_dotenv
        env_path = _ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            key = os.getenv("OPENAI_API_KEY")
            if key and key.strip().startswith("sk-"):
                logger.info("✅ Using OPENAI_API_KEY from .env file")
                return key.strip()
    except ImportError:
        pass  # python-dotenv not installed, skip
    
    # Priority 3: key_openai file (legacy, less secure)
    key_path = Path(os.getenv("OPENAI_API_KEY_FILE", _ROOT / "key_openai"))
    if key_path.exists():
        try:
            content = key_path.read_text(encoding="utf-8").strip()
            # Filter out comments and empty lines
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and line.startswith("sk-"):
                    logger.warning("⚠️ Using API key from key_openai file (not recommended)")
                    logger.info("💡 Better security: Set OPENAI_API_KEY environment variable instead")
                    return line
        except Exception as exc:
            logger.debug(f"Failed to read key_openai: {exc}")
    
    # No key found
    raise ValueError(
        "🚨 LỖI: Không tìm thấy OPENAI_API_KEY.\n"
        "💡 Giải pháp:\n"
        "  1. Windows PowerShell: $env:OPENAI_API_KEY = 'sk-proj-...'\n"
        "  2. Linux/Mac: export OPENAI_API_KEY='sk-proj-...'\n"
        "  3. Hoặc tạo .env file và điền: OPENAI_API_KEY=sk-proj-...\n"
        "  4. Hoặc sửa file key_openai và thêm key"
    )


class LeaderLayer:
    """Leader tier: route tasks and synthesize final recommendation."""

    def __init__(self, prompts: Dict[str, Any], api_key: str, base_url: str) -> None:
        self.prompts = prompts
        # Model nhỏ để chia việc
        self.router = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=api_key,
            base_url=base_url,
        )
        # Model lớn để viết báo cáo
        self.synthesizer = ChatOpenAI(
            model="gpt-4o",
            temperature=0.2,
            api_key=api_key,
            base_url=base_url,
        )

    def _leader_router_prompt(self) -> str:
        return self.prompts.get("LEADER", {}).get("router", "Bạn là bộ điều phối hệ thống. Trả về actions từ: data, news, analysis, info, report.")

    def _leader_synth_prompt(self, state: AgentState) -> str:
        """Generate the final synthesis prompt directly from prompts.txt."""
        query = state.get("query", "")
        synthesis_prompts = self.prompts.get("SYNTHESIS", {})

        query_lower = query.lower()
        invest_keywords = [
            "đầu tư", "nên mua", "nên bán", "nên giữ", "phân tích", "khuyến nghị",
            "có nên", "mục tiêu giá", "rủi ro", "dự báo",
        ]
        info_keywords = [
            "tra cứu", "thông tin", "hồ sơ", "giới thiệu", "cơ bản", "thành lập",
            "vốn", "ngành", "sàn", "ceo", "website",
        ]

        if any(keyword in query_lower for keyword in invest_keywords):
            return synthesis_prompts.get("investment", self.prompts.get("LEADER", {}).get("synthesizer", ""))
        if any(keyword in query_lower for keyword in info_keywords):
            return synthesis_prompts.get("info", self.prompts.get("LEADER", {}).get("synthesizer", ""))
        return synthesis_prompts.get("general", self.prompts.get("LEADER", {}).get("synthesizer", ""))

    @staticmethod
    def _needs_analysis(query: str) -> bool:
        lowered = (query or "").lower()
        keywords = (
            "thống kê",
            "thong ke",
            "chỉ số",
            "chi so",
            "phân tích",
            "phan tich",
            "sma",
            "rsi",
            "trung bình",
            "trung binh",
            "cao nhất",
            "cao nhat",
            "thấp nhất",
            "thap nhat",
            "biến động",
            "bien dong",
            "xu hướng",
            "xu huong",
        )
        return any(keyword in lowered for keyword in keywords)

    @staticmethod
    def _needs_report(query: str) -> bool:
        lowered = (query or "").lower()
        keywords = (
            "báo cáo tài chính",
            "bao cao tai chinh",
            "báo cáo phân tích",
            "bao cao phan tich",
            "tổng hợp đánh giá",
            "tong hop danh gia",
            "báo cáo",
            "bao cao",
            "financial report",
            "analysis report",
            "income statement",
            "thuyết minh",
            "thuyet minh",
        )
        return any(keyword in lowered for keyword in keywords)

    @staticmethod
    def _needs_info(query: str) -> bool:
        lowered = (query or "").lower()
        keywords = (
            "thông tin",
            "thong tin",
            "hồ sơ",
            "ho so",
            "doanh nghiệp",
            "doanh nghiep",
            "profile",
            "company",
            "ceo",
            "vốn điều lệ",
            "von dieu le",
        )
        return any(keyword in lowered for keyword in keywords)

    @staticmethod
    def _needs_news(query: str) -> bool:
        lowered = (query or "").lower()
        keywords = (
            "tin tức",
            "tin tuc",
            "news",
            "sentiment",
            "thị trường",
            "thi truong",
        )
        return any(keyword in lowered for keyword in keywords)

    @staticmethod
    def _needs_data(query: str) -> bool:
        lowered = (query or "").lower()
        keywords = (
            "giá lịch sử",
            "gia lich su",
            "ohlcv",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "thống kê",
            "thong ke",
            "sma",
            "rsi",
            "phân tích kỹ thuật",
            "phan tich ky thuat",
            "kỹ thuật",
            "ky thuat",
        )
        return any(keyword in lowered for keyword in keywords)

    def _minimal_actions_for_query(self, query: str) -> list[str]:
        actions: list[str] = []
        if self._needs_report(query):
            actions.append("report")
        if self._needs_info(query):
            actions.append("info")
        if self._needs_data(query):
            actions.append("data")
        if self._needs_news(query):
            actions.append("news")
        if self._needs_data(query):
            actions.append("analysis")

        deduped: list[str] = []
        for action in actions:
            if action not in deduped:
                deduped.append(action)
        return deduped or ["info"]

    @staticmethod
    def _summarize_ohlcv(data_rows: Any) -> str:
        if data_rows is None or len(data_rows) == 0:
            return "Thiếu dữ liệu giá."

        try:
            open_series = data_rows["open"].astype(float)
            high_series = data_rows["high"].astype(float)
            low_series = data_rows["low"].astype(float)
            close_series = data_rows["close"].astype(float)
            volume_series = data_rows["volume"].astype(float)

            first_close = float(close_series.iloc[0])
            last_close = float(close_series.iloc[-1])
            change_pct = ((last_close - first_close) / first_close * 100.0) if first_close else 0.0

            return (
                f"{len(data_rows)} dòng | "
                f"open TB={open_series.mean():.2f} | "
                f"high max={high_series.max():.2f} | "
                f"low min={low_series.min():.2f} | "
                f"close đầu={first_close:.2f} | close cuối={last_close:.2f} | "
                f"biến động={change_pct:.2f}% | "
                f"volume TB={volume_series.mean():.0f}"
            )
        except Exception:
            return f"{len(data_rows)} dòng dữ liệu giá"

    @staticmethod
    def _normalize_actions(text: str) -> list[str]:
        allowed = ["data", "news", "analysis", "info", "report"]
        alias_map = {
            "data_worker": "data",
            "news_worker": "news",
            "analyst_worker": "analysis",
            "analysis_worker": "analysis",
            "info_worker": "info",
            "report_worker": "report",
            "report": "report",
        }

        def normalize_item(item: Any) -> str | None:
            value = str(item).strip().lower()
            if not value:
                return None
            value = alias_map.get(value, value)
            if value in allowed:
                return value
            return None

        candidates: list[str] = []
        if isinstance(text, list):
            candidates = [item for item in (normalize_item(x) for x in text) if item]
        else:
            cleaned = str(text).replace(",", " ").replace(";", " ").split()
            candidates = [item for item in (normalize_item(x) for x in cleaned) if item]

        deduped: list[str] = []
        for item in candidates:
            if item not in deduped:
                deduped.append(item)

        return deduped or ["data", "news", "analysis"]

    async def analyze_intent(self, query: str, conversation_memory: ConversationMemory | None = None) -> DecisionState:
        """Sếp suy luận ý định và chia việc (Bản nâng cấp JSON) với conversation context."""
        sys_msg = SystemMessage(content=self._leader_router_prompt())
        logger.info("[leader.analyze_intent] query=%s", query)
        
        # Enhance query with conversation context if available
        enhanced_query = query
        if conversation_memory:
            context = conversation_memory.get_context_for_query(query)
            if context.get("recent_focus_symbol"):
                enhanced_query += f"\n[Bối cảnh: Người dùng đang quan tâm mã {context['recent_focus_symbol']}]"
            if context.get("previous_intents"):
                enhanced_query += f"\n[Trước đó: Người dùng hỏi về {', '.join(context['previous_intents'])}]"
        
        # Ép GPT-4o-mini phải trả về định dạng JSON nghiêm ngặt
        router_with_json = self.router.bind(response_format={"type": "json_object"})
        
        try:
            # Gọi LLM
            response = await router_with_json.ainvoke([sys_msg, HumanMessage(content=enhanced_query)])
            
            # Đọc file JSON từ não LLM
            result = json.loads(response.content)
            
            # Bóc tách các thành phần LLM vừa suy luận
            thought = result.get("thought", "Không có suy luận.")
            intent = result.get("intent", "phan_tich_tong_hop")
            actions = result.get("actions", ["data", "news", "analysis"])
            actions_text = " ".join(actions) if isinstance(actions, list) else str(actions)
            actions = self._normalize_actions(actions_text)
            minimal_actions = self._minimal_actions_for_query(query)
            if minimal_actions:
                actions = minimal_actions
            logger.info("[leader.analyze_intent] intent=%s actions=%s", intent, actions)
            
        except Exception as e:
            thought = f"Không điều phối được: {e}"
            intent = "error"
            actions = []
            logger.exception("[leader.analyze_intent] failed: %s", e)

        return {
            "intent": intent,
            "actions": actions,
            "thought": thought,
            "action": "route_to_continue",
            "arguments": {"query": query},
            "route": actions,
            "reasons": thought,
            "by_model": "gpt-4o-mini",
        }

    async def synthesize(self, state: AgentState, conversation_memory: ConversationMemory | None = None) -> str:
        """Sếp tổng hợp số liệu với context-aware prompt từ conversation history."""
        # Chỉ báo lỗi nếu không có BẤT KỲ dữ liệu nào để tổng hợp
        if not any(state.get(key) for key in ["data", "news", "analysis", "info", "report"]):
            return "Tôi không lấy được data."

        sys_msg = SystemMessage(content=self._leader_synth_prompt(state))
        logger.info("[leader.synthesize] keys=%s", list(state.keys()))

        info_profile = state.get("info", {}).get("profile")
        report_result = state.get("report", {})
        info_markdown = info_profile.get("markdown", "") if isinstance(info_profile, dict) else ""
        report_markdown = report_result.get("markdown", "") if isinstance(report_result, dict) else ""
        
        payload = {
            "query": state.get("query", ""),
            "data_available": True,
            "news_summary": state.get("news", {}).get("sentiment", "Không có tin tức"),
            "analysis_summary": state.get("analysis", {}).get("indicators", "Không có chỉ báo kỹ thuật"),
            "info_summary": self._summarize_info(info_profile),
            "info_markdown": info_markdown,
            "report_summary": report_result.get("summary", "Không có báo cáo tổng hợp") if isinstance(report_result, dict) else "Không có báo cáo tổng hợp",
            "report_markdown": report_markdown,
        }
        
        # Add conversation context if available
        if conversation_memory:
            context = conversation_memory.get_context_for_query(state.get("query", ""))
            payload["conversation_context"] = {
                "recent_focus": context.get("recent_focus_symbol"),
                "previous_intents": context.get("previous_intents"),
                "user_patterns": context.get("user_patterns"),
                "turn_number": context.get("conversation_turn"),
            }
            logger.info("[leader.synthesize] Using conversation context: turn=%d", context.get("conversation_turn", 0))

        messages = [sys_msg, HumanMessage(content=json.dumps(payload, ensure_ascii=False))]
        try:
            response = await self.synthesizer.ainvoke(messages)
            logger.info("[leader.synthesize] used primary synthesizer")
            return str(response.content)
        except Exception:
            # Fallback 1: dùng router model để tổng hợp nếu model lớn không khả dụng
            try:
                response = await self.router.ainvoke(messages)
                logger.info("[leader.synthesize] used router fallback")
                return str(response.content)
            except Exception as exc:
                logger.exception("[leader.synthesize] both LLM paths failed: %s", exc)
                return "Tôi không lấy được data."

    @staticmethod
    def _summarize_info(profile: Any) -> str:
        if not isinstance(profile, dict) or not profile:
            return "Không có thông tin doanh nghiệp"
        
        if profile.get("error"):
            return f"Thông tin doanh nghiệp lỗi: {profile.get('error')}"

        summary = profile.get("summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()

        # ✅ Handle NEW TCBS income statement format
        if profile.get("source") == "TCBS" and profile.get("markdown"):
            symbol = profile.get("symbol", "N/A")
            years = profile.get("years_available", [])
            total_records = profile.get("total_records", 0)
            years_str = ", ".join(str(y) for y in years) if years else "N/A"
            return f"Báo cáo tài chính {symbol}: {total_records} năm dữ liệu | Năm: {years_str}"

        # ⬜ Handle OLD vnstock profile format (fallback)
        symbol = profile.get("symbol")
        company_type = profile.get("company_type") or profile.get("companyType")
        exchange = profile.get("exchange") or profile.get("comGroupCode") or profile.get("listed_exchange")
        ceo = profile.get("ceo_name") or profile.get("ceoName")
        website = profile.get("website")
        capital = profile.get("charter_capital")
        founded_date = profile.get("founded_date") or profile.get("founding_date")

        fields = []
        if symbol:
            fields.append(f"Mã: {symbol}")
        if company_type:
            fields.append(f"Loại hình: {company_type}")
        if exchange:
            fields.append(f"Sàn: {exchange}")
        if ceo:
            fields.append(f"CEO: {ceo}")
        if capital:
            fields.append(f"Vốn: {capital}")
        if founded_date:
            fields.append(f"Thành lập: {founded_date}")
        if website:
            fields.append(f"Website: {website}")
        
        if not fields:
            return f"Dữ liệu: {json.dumps(profile, ensure_ascii=False)[:200]}"
        
        return " | ".join(fields)

class WorkerLayer:
    """Worker tier: execute specialized tasks."""

    def __init__(self, llm: ChatOpenAI = None) -> None:
        self.data_worker = DataAgent()
        self.news_worker = NewsAgent()
        self.analyst_worker = AnalystAgent()
        self.info_worker = InfoAgent()
        self.report_worker = ReportAgent(llm=llm)

    async def run_data(self, symbol: str, start: str, end: str):
        return await self.data_worker.fetch_ohlcv(symbol, start, end)

    async def run_news(self, query: str):
        return await self.news_worker.fetch_news_and_sentiment(query)

    async def run_analysis(self, symbol: str, ohlcv_df):
        return await self.analyst_worker.compute_indicators(symbol, ohlcv_df)

    async def run_info(self, symbol: str):
        return await self.info_worker.fetch_info(symbol)

    async def run_report(self, symbol: str, query: str, period: str = "1y"):
        return await self.report_worker.generate_report(symbol, query, period)


class Supervisor:
    """Orchestrator that enforces leader-worker layering without fake reasoning."""

    _LLM_TIMEOUT_SECONDS = 30
    _WORKER_TIMEOUT_SECONDS = 45

    def __init__(self, conversation_memory: ConversationMemory | None = None) -> None:
        prompts = load_prompts()
        api_key = get_openai_key()
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

        self.leader = LeaderLayer(prompts=prompts, api_key=api_key, base_url=base_url)
        
        # Create LLM for worker agents reasoning
        worker_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            api_key=api_key,
            base_url=base_url,
        )
        self.workers = WorkerLayer(llm=worker_llm)
        
        # Initialize conversation memory (stateful system)
        self.conversation_memory = conversation_memory or ConversationMemory()

    async def stream(self, payload: Dict[str, Any], conversation_memory: ConversationMemory | None = None) -> AsyncGenerator[Dict[str, Any], None]:
        query = payload.get("query", "")
        symbol = payload.get("symbol", "")
        start = payload.get("start", "2023-01-01")
        end = payload.get("end", "2024-01-01")
        state: AgentState = {"query": query, "errors": {}}
        logger.info("[supervisor.stream] start query=%s symbol=%s", query, symbol)
        
        # Use provided conversation_memory or instance memory
        memory = conversation_memory or self.conversation_memory
        memory.add_user_message(query)  # Record user query in memory

        # 1. SẾP ĐIỀU PHỐI (Có suy luận thật từ LLM)
        try:
            decision = await asyncio.wait_for(
                self.leader.analyze_intent(query or symbol, conversation_memory=memory),
                timeout=self._LLM_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            decision = {
                "intent": "error",
                "actions": [],
                "thought": f"Không điều phối được: {exc}",
                "action": "stop",
                "arguments": {"query": query, "symbol": symbol},
                "route": [],
                "reasons": f"Không điều phối được: {exc}",
                "by_model": "error",
            }
            logger.exception("[supervisor.stream] analyze_intent failed: %s", exc)

        actions = list(decision.get("actions", []))
        decision["actions"] = actions
        state["decision"] = decision
        logger.info("[supervisor.stream] routed actions=%s", actions)

        yield {
            "node_name": "supervisor",
            "node_state": {
                "thought": decision.get("thought") or decision.get("reasons") or "Đang điều phối các tác vụ cần thiết.",
                "action": decision.get("action", "route_to_continue"),
                "arguments": {
                    "query": query,
                    "symbol": symbol,
                    "start": start,
                    "end": end,
                },
                "route": actions,
                "intent": decision.get("intent"),
                "decision": decision,
            } # Trả về đúng quyết định thực tế
        }

        # 2. CHẠY PARALLEL DATA & NEWS
        parallel_tasks: Dict[str, asyncio.Task] = {}
        if "data" in actions and symbol:
            parallel_tasks["data"] = asyncio.create_task(
                self._run_data_safe(symbol, start, end)
            )
            logger.info(
                "[supervisor.stream] scheduled data worker symbol=%s start=%s end=%s",
                symbol,
                start,
                end,
            )
        if "news" in actions:
            parallel_tasks["news"] = asyncio.create_task(
                self._run_news_safe(query or symbol)
            )
            logger.info("[supervisor.stream] scheduled news worker")
        if "info" in actions and symbol:
            parallel_tasks["info"] = asyncio.create_task(self._run_info_safe(symbol))
            logger.info("[supervisor.stream] scheduled info worker symbol=%s", symbol)

        if parallel_tasks:
            results = await asyncio.gather(*parallel_tasks.values(), return_exceptions=True)
            results_by_name = dict(zip(parallel_tasks.keys(), results))

            if "data" in results_by_name:
                data_result = results_by_name["data"]
                if isinstance(data_result, Exception):
                    state["errors"]["data"] = str(data_result)
                    logger.exception("[supervisor.stream] data worker failed: %s", data_result)
                else:
                    state["data"] = {"symbol": symbol, "ohlcv": data_result}
                    logger.info("[supervisor.stream] data worker done")
                
                # Trả về trạng thái thuần túy, KHÔNG fake reasoning
                yield {
                    "node_name": "data_worker",
                    "node_state": {
                        "thought": f"Lấy dữ liệu giá lịch sử cho mã {symbol}.",
                        "action": "fetch_ohlcv",
                        "arguments": {"symbol": symbol, "start": start, "end": end},
                        "route": "continue",
                        "tool": "vnstock.Quote.history",
                        "summary": f"{len(data_result)} dòng OHLCV" if not isinstance(data_result, Exception) and data_result is not None else "Không có dữ liệu",
                        "status": "done" if not state["errors"].get("data") else "error",
                        "errors": state["errors"].get("data"),
                    }
                }

            if "news" in results_by_name:
                news_result = results_by_name["news"]
                if isinstance(news_result, Exception):
                    state["errors"]["news"] = str(news_result)
                    logger.exception("[supervisor.stream] news worker failed: %s", news_result)
                else:
                    state["news"] = news_result
                    logger.info("[supervisor.stream] news worker done")
                
                yield {
                    "node_name": "news_worker",
                    "node_state": {
                        "thought": "Đọc tin tức liên quan và chấm điểm sentiment.",
                        "action": "fetch_news_and_sentiment",
                        "arguments": {"query": query or symbol},
                        "route": "continue",
                        "tool": "NewsAgent.fetch_news_and_sentiment",
                        "summary": f"{news_result.get('sentiment', {}).get('article_count', 0)} bài, điểm TB {news_result.get('sentiment', {}).get('average_score', 0.0):.2f}" if isinstance(news_result, dict) else "Không có dữ liệu",
                        "status": "done" if not state["errors"].get("news") else "error",
                        "errors": state["errors"].get("news"),
                    }
                }

            if "info" in results_by_name:
                info_result = results_by_name["info"]
                if isinstance(info_result, Exception):
                    state["errors"]["info"] = str(info_result)
                    logger.exception("[supervisor.stream] info worker failed: %s", info_result)
                else:
                    if isinstance(info_result, dict) and info_result.get("error"):
                        state["errors"]["info"] = str(info_result.get("error"))
                    state["info"] = {"symbol": symbol, "profile": info_result}
                    logger.info("[supervisor.stream] info worker done")

                yield {
                    "node_name": "info_worker",
                    "node_state": {
                        "thought": "Tra cứu hồ sơ doanh nghiệp, ưu tiên làm mới từ vnstock rồi đọc lại từ cache.",
                        "action": "fetch_info",
                        "arguments": {"symbol": symbol},
                        "route": "continue",
                        "tool": "vnstock.Company.overview/profile",
                        "summary": self.leader._summarize_info(info_result if isinstance(info_result, dict) else {"error": str(info_result)}),
                        "status": "done" if not state["errors"].get("info") else "error",
                        "errors": state["errors"].get("info"),
                        "profile": state.get("info", {}).get("profile"),
                    },
                }

        # 3. CHẠY ANALYST (Chỉ chạy khi có Data)
        ohlcv_df = state.get("data", {}).get("ohlcv")
        if "analysis" in actions and ohlcv_df is not None and len(ohlcv_df) > 0:
            try:
                analysis = await self.workers.run_analysis(symbol, ohlcv_df)
                state["analysis"] = {"symbol": symbol, "indicators": analysis.get("indicators", {})}
                logger.info("[supervisor.stream] analyst worker done")
            except Exception as exc:
                state["errors"]["analysis"] = str(exc)
                logger.exception("[supervisor.stream] analyst worker failed: %s", exc)
                
            yield {
                "node_name": "analyst_worker",
                "node_state": {
                    "thought": "Tính SMA và RSI từ dữ liệu giá đã lấy về.",
                    "action": "compute_indicators",
                    "arguments": {"symbol": symbol, "rows": len(ohlcv_df)},
                    "route": "continue",
                    "tool": "AnalystAgent.compute_indicators",
                    "summary": f"RSI14={analysis.get('indicators', {}).get('rsi_14', 'NA')}" if isinstance(analysis, dict) else "Không có dữ liệu",
                    "status": "done" if not state["errors"].get("analysis") else "error",
                    "errors": state["errors"].get("analysis"),
                }
            }

        # 4. REPORT AGENT (Tạo báo cáo toàn diện)
        if "report" in actions and symbol:
            try:
                report_result = await self._run_report_safe(symbol, query or symbol)
                if report_result and not isinstance(report_result, Exception) and not report_result.get("error"):
                    state["report"] = report_result
                    logger.info("[supervisor.stream] report agent done")
                else:
                    error_msg = str(report_result.get("error") if isinstance(report_result, dict) else report_result)
                    state["errors"]["report"] = error_msg
            except Exception as exc:
                state["errors"]["report"] = str(exc)
                logger.exception("[supervisor.stream] report agent failed: %s", exc)
                report_result = {
                    "symbol": symbol,
                    "query": query,
                    "period": payload.get("period", "1y"),
                    "mode": "error",
                    "summary": f"Lỗi: {str(exc)}",
                    "markdown": "",
                    "records": [],
                    "error": str(exc),
                }

            yield {
                "node_name": "report_worker",
                "node_state": {
                    "thought": f"Tạo báo cáo phân tích toàn diện cho mã {symbol} từ thị trường Việt Nam.",
                    "action": "generate_report",
                    "arguments": {"symbol": symbol, "query": query},
                    "route": "continue",
                    "tool": "ReportAgent.generate_report",
                    "summary": report_result.get("summary", "Báo cáo được tạo") if isinstance(report_result, dict) else "Lỗi tạo báo cáo",
                    "status": "done" if not state["errors"].get("report") else "error",
                    "errors": state["errors"].get("report"),
                    "market_data": report_result.get("market_data") if isinstance(report_result, dict) else {},
                    "records_count": len(report_result.get("records", [])) if isinstance(report_result, dict) else 0,
                }
            }

        # 5. SẾP TỔNG HỢP (Suy luận thật để ra quyết định đầu tư)
        try:
            final_recommendation = await asyncio.wait_for(
                self.leader.synthesize(state, conversation_memory=memory),
                timeout=self._LLM_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            final_recommendation = "Tôi không lấy được data."
            logger.exception("[supervisor.stream] synthesize failed: %s", exc)

        state["final_recommendation"] = final_recommendation
        logger.info("[supervisor.stream] final_report ready")
        
        # Record agent response in conversation memory
        memory.add_agent_response(final_recommendation, metadata={
            "query": query,
            "symbol": symbol,
            "data_available": any(state.get(key) for key in ["data", "news", "analysis", "info", "report"]),
        })
        logger.info("[supervisor.stream] Recorded response in conversation memory")
        
        yield {
            "node_name": "final_report",
            "node_state": {"final_recommendation": final_recommendation}
        }
        
        yield {"node_name": "__end__", "state": state}

    async def run(self, conversation_memory: ConversationMemory | None = None, **kwargs) -> AgentState:
        final_state: AgentState = {}
        memory = conversation_memory or self.conversation_memory
        async for step in self.stream(kwargs, conversation_memory=memory):
            if step["node_name"] == "__end__":
                final_state = step["state"]
        return final_state

    async def _run_data_safe(self, symbol: str, start: str, end: str):
        try:
            logger.info("[_run_data_safe] start symbol=%s", symbol)
            return await asyncio.wait_for(
                self.workers.run_data(symbol, start, end),
                timeout=self._WORKER_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            logger.exception("[_run_data_safe] failed: %s", exc)
            raise

    async def _run_news_safe(self, query: str):
        try:
            logger.info("[_run_news_safe] start query=%s", query)
            return await asyncio.wait_for(
                self.workers.run_news(query),
                timeout=self._WORKER_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            logger.exception("[_run_news_safe] failed: %s", exc)
            return {"error": f"Tôi không lấy được data cho tin tức: {query}", "query": query}

    async def _run_info_safe(self, symbol: str):
        try:
            logger.info("[_run_info_safe] start symbol=%s", symbol)
            return await asyncio.wait_for(
                self.workers.run_info(symbol),
                timeout=self._WORKER_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            logger.exception("[_run_info_safe] failed: %s", exc)
            return {"error": f"Không lấy được thông tin doanh nghiệp cho mã {symbol}: {exc}"}

    async def _run_report_safe(self, symbol: str, query: str):
        try:
            logger.info("[_run_report_safe] start symbol=%s query=%s", symbol, query)
            return await asyncio.wait_for(
                self.workers.run_report(symbol, query),
                timeout=self._WORKER_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            logger.exception("[_run_report_safe] failed: %s", exc)
            return {
                "symbol": symbol,
                "query": query,
                "mode": "error",
                "summary": f"Tôi không lấy được data: {str(exc)}",
                "markdown": f"Tôi không lấy được data: {str(exc)}",
                "records": [],
                "error": str(exc),
            }

    @staticmethod
    def _format_fast_path_report(symbol: str, profile: Dict[str, Any]) -> str:
        if not isinstance(profile, dict) or not profile:
            return f"THÔNG TIN DOANH NGHIỆP: Không có dữ liệu cho mã {symbol}."

        if profile.get("error"):
            return f"THÔNG TIN DOANH NGHIỆP: {profile.get('error')}"

        def first_value(*keys: str) -> Any:
            for key in keys:
                value = profile.get(key)
                if value not in (None, "", []):
                    return value
            return None

        def fmt(value: Any) -> str:
            if value is None:
                return ""
            if isinstance(value, (list, tuple, set)):
                return ", ".join(str(item) for item in value if item not in (None, ""))
            return str(value).strip()

        company_name = first_value("companyName", "company_name", "name", "symbol") or symbol
        business_model = first_value("business_model", "industry", "icb_name3", "icbName3", "company_type")
        exchange = first_value("exchange", "comGroupCode", "listed_exchange")
        founded_date = first_value("founded_date", "founding_date")
        charter_capital = first_value("charter_capital")
        employees = first_value("number_of_employees")
        listing_date = first_value("listing_date")
        par_value = first_value("par_value")
        listing_price = first_value("listing_price")
        listed_volume = first_value("listed_volume")
        ceo_name = first_value("ceo_name", "ceoName")
        ceo_position = first_value("ceo_position", "ceoPosition")
        company_type = first_value("company_type", "companyType")
        address = first_value("address")
        website = first_value("website")
        as_of_date = first_value("as_of_date")

        lines = [f"THÔNG TIN DOANH NGHIỆP: {fmt(company_name)}"]

        summary_parts = []
        if business_model:
            summary_parts.append(f"Mô hình/Ngành: {fmt(business_model)}")
        if exchange:
            summary_parts.append(f"Sàn: {fmt(exchange)}")
        if company_type:
            summary_parts.append(f"Loại hình: {fmt(company_type)}")
        if summary_parts:
            lines.extend(summary_parts)

        detail_map = [
            ("Mã", symbol),
            ("Ngày thành lập", founded_date),
            ("Vốn điều lệ", charter_capital),
            ("Số nhân viên", employees),
            ("CEO", ceo_name),
            ("Chức vụ CEO", ceo_position),
            ("Địa chỉ", address),
            ("Website", website),
            ("Cập nhật dữ liệu", as_of_date),
        ]

        for label, value in detail_map:
            if value not in (None, "", [], ()):
                lines.append(f"- {label}: {fmt(value)}")

        if len(lines) == 1:
            lines.append(f"- Dữ liệu thô: {json.dumps(profile, ensure_ascii=False)[:400]}")

        return "\n".join(lines)

    def get_conversation_memory(self) -> ConversationMemory:
        """Get the current conversation memory."""
        return self.conversation_memory

    def set_conversation_memory(self, memory: ConversationMemory) -> None:
        """Set a new conversation memory."""
        self.conversation_memory = memory
        logger.info("[Supervisor] Conversation memory updated: session_id=%s", memory.session_id)

    def get_conversation_history(self) -> str:
        """Get formatted conversation history for display."""
        return self.conversation_memory.get_formatted_history()

    def save_conversation(self) -> Path:
        """Save current conversation to file."""
        return self.conversation_memory.save_to_file()

    def clear_conversation(self) -> None:
        """Clear conversation history and start fresh."""
        self.conversation_memory = ConversationMemory()
        logger.info("[Supervisor] Conversation cleared, new session started")


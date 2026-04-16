from typing import TypedDict, Any, Dict, List, Optional
from datetime import datetime


class LLMResponse(TypedDict, total=False):
    model: str
    prompt: str
    completion: str
    raw: Any
    timestamp: datetime


class DataState(TypedDict, total=False):
    symbol: str
    start: str
    end: str
    ohlcv: Any  # usually a pandas.DataFrame or a serialized list of rows
    fetched_at: datetime


class NewsState(TypedDict, total=False):
    query: str
    articles: List[Dict[str, Any]]
    sentiment: Dict[str, float]
    fetched_at: datetime


class AnalysisState(TypedDict, total=False):
    symbol: str
    indicators: Dict[str, Any]
    computed_at: datetime

class InfoState(TypedDict, total=False):
    symbol: str
    profile: Dict[str, Any]
    fetched_at: datetime

class ReportState(TypedDict, total=False):
    symbol: str
    query: str
    period: str
    mode: str
    summary: str
    markdown: str
    records: List[Dict[str, Any]]
    market_data: Dict[str, Any]
    thought: str
    error: Optional[str]
    generated_at: datetime


class DecisionState(TypedDict, total=False):
    intent: str
    actions: List[str]
    reasons: Optional[str]
    by_model: Optional[str]


class AgentState(TypedDict, total=False):
    # Shared memory between agents
    query: str
    decision: DecisionState
    data: DataState
    news: NewsState
    analysis: AnalysisState
    info: InfoState
    report: ReportState
    llm: Dict[str, LLMResponse]
    errors: Dict[str, str]



"""Pydantic schemas for ext-analytics (Platform Usage Analytics).

Response schemas for the 4 API endpoints.
Read-only analytics on existing Onyx tables — no mutations.
"""

from datetime import date
from datetime import datetime

from pydantic import BaseModel


# --- Summary ---


class UserMetrics(BaseModel):
    registered: int
    active_period: int
    dau_avg: float
    new_in_period: int
    inactive_30d: int


class SessionMetrics(BaseModel):
    total: int
    avg_per_user: float
    avg_messages_per_session: float
    avg_duration_seconds: float


class TokenByModel(BaseModel):
    model: str
    tokens: int
    requests: int


class TokenMetrics(BaseModel):
    total: int
    prompt: int
    completion: int
    requests: int
    by_model: list[TokenByModel]


class QualityMetrics(BaseModel):
    feedback_total: int
    feedback_positive: int
    feedback_negative: int
    satisfaction_pct: float
    error_rate_pct: float
    avg_response_time_seconds: float | None
    p95_response_time_seconds: float | None


class AgentStats(BaseModel):
    name: str
    sessions: int
    messages: int


class AgentMetrics(BaseModel):
    total: int
    active_in_period: int
    top: list[AgentStats]


class ContentMetrics(BaseModel):
    total_documents: int
    active_connectors: int
    error_connectors: int
    document_sets: int


class ComplianceMetrics(BaseModel):
    admin_actions: int
    admin_actions_by_type: dict[str, int]


class AnalyticsPeriod(BaseModel):
    from_date: date
    to_date: date


class AnalyticsSummaryResponse(BaseModel):
    period: AnalyticsPeriod
    users: UserMetrics
    sessions: SessionMetrics
    tokens: TokenMetrics
    quality: QualityMetrics
    agents: AgentMetrics
    content: ContentMetrics
    compliance: ComplianceMetrics


# --- Users Table ---


class UserActivityRow(BaseModel):
    email: str
    role: str
    registered: datetime
    sessions: int
    messages: int
    tokens: int
    last_activity: datetime | None


class UserActivityResponse(BaseModel):
    total: int
    users: list[UserActivityRow]


# --- Agents Table ---


class AgentDetailRow(BaseModel):
    name: str
    sessions: int
    messages: int
    unique_users: int


class AgentDetailResponse(BaseModel):
    total: int
    agents: list[AgentDetailRow]

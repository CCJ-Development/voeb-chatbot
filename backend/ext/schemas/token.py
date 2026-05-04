"""Pydantic schemas for ext-token (LLM Usage Tracking + Token Limits).

Request/Response schemas for the 6 API endpoints.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field

# --- Usage Summary ---


class UsageByUser(BaseModel):
    user_id: UUID
    user_email: str | None
    total_tokens: int
    total_requests: int


class UsageByModel(BaseModel):
    model_name: str
    total_tokens: int
    total_requests: int


class UsageSummaryResponse(BaseModel):
    period_hours: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_requests: int
    by_user: list[UsageByUser]
    by_model: list[UsageByModel]


# --- Usage Timeseries ---


class TimeseriesBucket(BaseModel):
    timestamp: datetime
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    request_count: int


class UsageTimeseriesResponse(BaseModel):
    granularity: str
    data: list[TimeseriesBucket]


# --- User Limits ---


class UserLimitCreate(BaseModel):
    user_id: UUID
    token_budget: int = Field(gt=0)
    period_hours: int = Field(gt=0)
    enabled: bool = True


class UserLimitUpdate(BaseModel):
    token_budget: int = Field(gt=0)
    period_hours: int = Field(gt=0)
    enabled: bool = True


class UserLimitResponse(BaseModel):
    id: int
    user_id: UUID
    user_email: str | None
    token_budget: int
    period_hours: int
    enabled: bool
    current_usage: int

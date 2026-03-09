"""Pydantic schemas for ext-prompts (Custom System Prompts).

Request/Response schemas for the 5 API endpoints.
"""

from datetime import datetime

from pydantic import BaseModel
from pydantic import Field


class PromptCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    prompt_text: str = Field(min_length=1, max_length=10_000)
    category: str = Field(
        default="general",
        pattern=r"^(compliance|tone|context|instructions|general)$",
    )
    priority: int = Field(default=100, ge=0, le=1000)
    is_active: bool = True


class PromptUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    prompt_text: str | None = Field(default=None, min_length=1, max_length=10_000)
    category: str | None = Field(
        default=None,
        pattern=r"^(compliance|tone|context|instructions|general)$",
    )
    priority: int | None = Field(default=None, ge=0, le=1000)
    is_active: bool | None = None


class PromptResponse(BaseModel):
    id: int
    name: str
    prompt_text: str
    category: str
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PromptPreviewResponse(BaseModel):
    assembled_text: str
    active_count: int
    total_count: int

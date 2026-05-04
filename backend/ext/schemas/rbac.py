"""Pydantic schemas for ext-rbac (Group Management).

Request/Response schemas for the 7 API endpoints.
Compatible with the TypeScript UserGroup interface in web/src/lib/types.ts.
"""

from uuid import UUID

from pydantic import BaseModel
from pydantic import Field

# --- Request Schemas ---


class UserGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    user_ids: list[UUID] = Field(default_factory=list)
    cc_pair_ids: list[int] = Field(default_factory=list)


class UserGroupUpdate(BaseModel):
    user_ids: list[UUID]
    cc_pair_ids: list[int]


class AddUsersRequest(BaseModel):
    user_ids: list[UUID] = Field(..., min_length=1)


class SetCuratorRequest(BaseModel):
    user_id: UUID
    is_curator: bool


# --- Response Schemas ---
# Response format matches TypeScript UserGroup interface exactly.
# We use dicts built in the service layer for maximum compatibility.
# No dedicated response model — endpoints return list[dict] or dict.


class MinimalUserGroup(BaseModel):
    """Minimal group info for non-admin contexts (Agent editor, LLM config)."""

    id: int
    name: str

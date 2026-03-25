"""ext-audit: Pydantic Schemas."""

from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    id: str
    timestamp: str | None
    actor_email: str | None
    actor_role: str | None
    action: str
    resource_type: str
    resource_id: str | None
    resource_name: str | None
    details: dict | None
    ip_address: str | None


class AuditEventsListResponse(BaseModel):
    events: list[AuditEventResponse]
    total: int
    page: int
    page_size: int

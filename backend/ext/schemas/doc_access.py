"""ext-access: Pydantic Schemas fuer Admin-Endpoints."""

from pydantic import BaseModel


class ResyncResponse(BaseModel):
    status: str
    groups_queued: int
    estimated_documents: int


class SyncStatusResponse(BaseModel):
    enabled: bool
    groups_total: int
    groups_synced: int
    groups_pending: int

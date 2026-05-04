"""ext-audit: Admin-Endpoints + Audit-Context Dependency.

Endpoints:
- GET /ext/audit/events   — Paginierter Audit-Log Browser
- GET /ext/audit/export   — CSV-Export fuer Compliance

Dependency:
- get_audit_context()     — Extrahiert Client-IP + User-Agent (fuer andere ext-Router)
"""

import logging
from datetime import datetime
from datetime import timedelta

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from ext.auth import current_admin_user
from ext.schemas.audit import AuditEventsListResponse
from ext.services.audit import export_audit_csv
from ext.services.audit import query_audit_events
from onyx.db.engine.sql_engine import get_session
from onyx.db.models import User

logger = logging.getLogger("ext.audit")

router = APIRouter(prefix="/ext/audit", tags=["ext-audit"])


# ---------------------------------------------------------------------------
# Dependency: Audit-Context (IP + User-Agent)
# ---------------------------------------------------------------------------


def get_audit_context(request: Request) -> dict:
    """Extrahiert Client-IP und User-Agent aus dem HTTP-Request.

    Beruecksichtigt X-Forwarded-For (NGINX Proxy, SEC-09 externalTrafficPolicy: Local).
    Kein Namenskonflikt mit Pydantic 'request'-Parametern weil
    FastAPI Dependencies ueber den Typ (Request vs Pydantic) aufgeloest werden.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else None
    if not ip and request.client:
        ip = request.client.host
    return {
        "ip_address": ip,
        "user_agent": request.headers.get("user-agent"),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/events")
def api_list_audit_events(
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
    actor_email: str | None = Query(None),
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> AuditEventsListResponse:
    """Paginierter Audit-Log Browser mit Filtern."""
    result = query_audit_events(
        db_session=db_session,
        actor_email=actor_email,
        action=action,
        resource_type=resource_type,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
    return AuditEventsListResponse(**result)


@router.get("/export")
def api_export_audit_csv(
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
    from_date: datetime = Query(...),
    to_date: datetime = Query(...),
) -> PlainTextResponse:
    """CSV-Export fuer Compliance-Reports. Max. 90 Tage Zeitraum."""
    if (to_date - from_date) > timedelta(days=90):
        raise HTTPException(
            status_code=400,
            detail="Maximaler Export-Zeitraum: 90 Tage",
        )

    csv_content = export_audit_csv(db_session, from_date, to_date)
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f"attachment; filename=audit-export-"
                f"{from_date.strftime('%Y%m%d')}-{to_date.strftime('%Y%m%d')}.csv"
            )
        },
    )

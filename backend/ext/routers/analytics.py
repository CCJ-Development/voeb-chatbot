"""FastAPI router for ext-analytics (Platform Usage Analytics).

All endpoints require admin auth. Prefix: /ext/analytics
Read-only — no mutations, no audit logging needed.
"""

import logging
from datetime import date
from datetime import timedelta

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from ext.auth import current_admin_user
from ext.schemas.analytics import AgentDetailResponse
from ext.schemas.analytics import AnalyticsSummaryResponse
from ext.schemas.analytics import UserActivityResponse
from ext.services.analytics import export_analytics_csv
from ext.services.analytics import get_agent_detail
from ext.services.analytics import get_analytics_summary
from ext.services.analytics import get_user_activity
from onyx.db.engine.sql_engine import get_session
from onyx.db.models import User

logger = logging.getLogger("ext.analytics")

router = APIRouter(prefix="/ext/analytics", tags=["ext-analytics"])


@router.get("/summary")
def api_analytics_summary(
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
    from_date: date = Query(default=None),
    to_date: date = Query(default=None),
) -> AnalyticsSummaryResponse:
    """All KPIs as JSON. Default: last 30 days."""
    if to_date is None:
        to_date = date.today()
    if from_date is None:
        from_date = to_date - timedelta(days=30)

    if from_date > to_date:
        raise HTTPException(status_code=400, detail="from_date > to_date")

    data = get_analytics_summary(db_session, from_date, to_date)
    return AnalyticsSummaryResponse(**data)


@router.get("/users")
def api_analytics_users(
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
    from_date: date = Query(default=None),
    to_date: date = Query(default=None),
) -> UserActivityResponse:
    """User activity table with sessions, messages, tokens."""
    if to_date is None:
        to_date = date.today()
    if from_date is None:
        from_date = to_date - timedelta(days=30)

    if from_date > to_date:
        raise HTTPException(status_code=400, detail="from_date > to_date")

    data = get_user_activity(db_session, from_date, to_date)
    return UserActivityResponse(**data)


@router.get("/agents")
def api_analytics_agents(
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
    from_date: date = Query(default=None),
    to_date: date = Query(default=None),
) -> AgentDetailResponse:
    """Agent usage statistics."""
    if to_date is None:
        to_date = date.today()
    if from_date is None:
        from_date = to_date - timedelta(days=30)

    if from_date > to_date:
        raise HTTPException(status_code=400, detail="from_date > to_date")

    data = get_agent_detail(db_session, from_date, to_date)
    return AgentDetailResponse(**data)


@router.get("/export")
def api_analytics_export(
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
    from_date: date = Query(...),
    to_date: date = Query(...),
) -> PlainTextResponse:
    """CSV export of all KPIs + user activity. Max 365 days."""
    if from_date > to_date:
        raise HTTPException(status_code=400, detail="from_date > to_date")
    if (to_date - from_date).days > 365:
        raise HTTPException(
            status_code=400,
            detail="Maximaler Export-Zeitraum: 365 Tage",
        )

    csv_content = export_analytics_csv(db_session, from_date, to_date)
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f"attachment; filename=analytics-"
                f"{from_date.isoformat()}-{to_date.isoformat()}.csv"
            )
        },
    )

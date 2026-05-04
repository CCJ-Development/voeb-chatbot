"""FastAPI router for ext-token (LLM Usage Tracking + Token Limits).

All endpoints require admin auth. Prefix: /ext/token
"""

import logging
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from sqlalchemy.orm import Session

from ext.auth import current_admin_user
from ext.routers.audit import get_audit_context
from ext.schemas.token import UsageSummaryResponse
from ext.schemas.token import UsageTimeseriesResponse
from ext.schemas.token import UserLimitCreate
from ext.schemas.token import UserLimitResponse
from ext.schemas.token import UserLimitUpdate
from ext.services.audit import log_audit_event
from ext.services.token_tracker import create_user_limit
from ext.services.token_tracker import delete_user_limit
from ext.services.token_tracker import get_usage_summary
from ext.services.token_tracker import get_usage_timeseries
from ext.services.token_tracker import get_user_limits
from ext.services.token_tracker import update_user_limit
from onyx.db.engine.sql_engine import get_session
from onyx.db.models import User

logger = logging.getLogger("ext.token")

router = APIRouter(prefix="/ext/token", tags=["ext-token"])


# --- Usage ---


@router.get("/usage/summary")
def api_usage_summary(
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
    period_hours: int = Query(default=168, gt=0),
    user_id: UUID | None = Query(default=None),
    model_name: str | None = Query(default=None, max_length=255),
) -> UsageSummaryResponse:
    data = get_usage_summary(
        db_session,
        period_hours=period_hours,
        user_id=user_id,
        model_name=model_name,
    )
    return UsageSummaryResponse(**data)


@router.get("/usage/timeseries")
def api_usage_timeseries(
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
    period_hours: int = Query(default=168, gt=0),
    granularity: str = Query(default="hour", pattern="^(hour|day)$"),
    user_id: UUID | None = Query(default=None),
    model_name: str | None = Query(default=None, max_length=255),
) -> UsageTimeseriesResponse:
    data = get_usage_timeseries(
        db_session,
        period_hours=period_hours,
        granularity=granularity,
        user_id=user_id,
        model_name=model_name,
    )
    return UsageTimeseriesResponse(granularity=granularity, data=data)


# --- User Limits ---


@router.get("/limits/users")
def api_get_user_limits(
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> list[UserLimitResponse]:
    rows = get_user_limits(db_session)
    return [UserLimitResponse(**r) for r in rows]


@router.post("/limits/users", status_code=201)
def api_create_user_limit(
    body: UserLimitCreate,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
    audit_ctx: dict = Depends(get_audit_context),
) -> UserLimitResponse:
    limit = create_user_limit(
        db_session,
        user_id=body.user_id,
        token_budget=body.token_budget,
        period_hours=body.period_hours,
        enabled=body.enabled,
    )
    log_audit_event(
        db_session,
        user,
        "CREATE",
        "TOKEN_LIMIT",
        resource_id=str(limit.id),
        details={"token_budget": body.token_budget},
        audit_ctx=audit_ctx,
    )
    return UserLimitResponse(
        id=limit.id,
        user_id=limit.user_id,
        user_email=None,
        token_budget=limit.token_budget,
        period_hours=limit.period_hours,
        enabled=limit.enabled,
        current_usage=0,
    )


@router.put("/limits/users/{limit_id}")
def api_update_user_limit(
    limit_id: int,
    body: UserLimitUpdate,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
    audit_ctx: dict = Depends(get_audit_context),
) -> UserLimitResponse:
    limit = update_user_limit(
        db_session,
        limit_id=limit_id,
        token_budget=body.token_budget,
        period_hours=body.period_hours,
        enabled=body.enabled,
    )
    log_audit_event(
        db_session,
        user,
        "UPDATE",
        "TOKEN_LIMIT",
        resource_id=str(limit_id),
        audit_ctx=audit_ctx,
    )
    return UserLimitResponse(
        id=limit.id,
        user_id=limit.user_id,
        user_email=None,
        token_budget=limit.token_budget,
        period_hours=limit.period_hours,
        enabled=limit.enabled,
        current_usage=0,
    )


@router.delete("/limits/users/{limit_id}", status_code=204)
def api_delete_user_limit(
    limit_id: int,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
    audit_ctx: dict = Depends(get_audit_context),
) -> None:
    log_audit_event(
        db_session,
        user,
        "DELETE",
        "TOKEN_LIMIT",
        resource_id=str(limit_id),
        audit_ctx=audit_ctx,
    )
    delete_user_limit(db_session, limit_id)

"""Business logic for ext-token (LLM Usage Tracking + Token Limits).

Core functions:
- log_token_usage(): Fire-and-forget INSERT after every LLM call
- check_user_token_limit(): Pre-call enforcement, raises 429 when over budget
- get_usage_summary(): Aggregated stats for dashboard
- get_usage_timeseries(): Time-bucketed data for charts
- CRUD for per-user limits

Prometheus-Metriken (automatisch via /metrics Endpoint exponiert):
- ext_token_prompt_total: Prompt-Tokens Counter (Label: model)
- ext_token_completion_total: Completion-Tokens Counter (Label: model)
- ext_token_requests_total: LLM-Request Counter (Label: model)
"""

import logging
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from uuid import UUID

from fastapi import HTTPException
from prometheus_client import Counter
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import Session

from ext.models.token_usage import ExtTokenUsage
from ext.models.token_usage import ExtTokenUserLimit
from onyx.db.engine.sql_engine import get_sqlalchemy_engine
from onyx.db.models import User

logger = logging.getLogger("ext.token")

# ---------------------------------------------------------------------------
# Prometheus Counters (exponiert via /metrics, gescrapt von Prometheus)
# ---------------------------------------------------------------------------

_prompt_tokens_counter = Counter(
    "ext_token_prompt_total",
    "Total prompt (input) tokens consumed",
    ["model"],
)
_completion_tokens_counter = Counter(
    "ext_token_completion_total",
    "Total completion (output) tokens consumed",
    ["model"],
)
_requests_counter = Counter(
    "ext_token_requests_total",
    "Total LLM requests",
    ["model"],
)

# Consistent with FOSS TOKEN_BUDGET_UNIT (token_limit.py:28)
TOKEN_BUDGET_UNIT = 1_000


def _resolve_user_uuid(db_session: Session, user_identifier: str) -> UUID | None:
    """Resolve a user identifier (UUID string or email) to a UUID.

    Onyx passes email (or 'anonymous_user') as user_identity.user_id,
    not the actual UUID. This helper handles both formats.
    """
    # Try UUID first
    try:
        return UUID(user_identifier)
    except (ValueError, AttributeError):
        pass

    # Try email lookup
    if user_identifier and user_identifier != "anonymous_user":
        row = db_session.execute(
            select(User.id).where(User.email == user_identifier)
        ).scalar_one_or_none()
        if row:
            return row

    return None


# ---------------------------------------------------------------------------
# Logging (fire-and-forget, called from multi_llm.py hook)
# ---------------------------------------------------------------------------


def log_token_usage(
    user_id: str | None,
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
) -> None:
    """Insert a single token usage row. Must never raise — all exceptions caught by caller."""
    if total_tokens <= 0:
        return

    # Prometheus Counter inkrementieren (in-memory, unabhaengig von DB)
    try:
        _prompt_tokens_counter.labels(model=model_name).inc(prompt_tokens)
        _completion_tokens_counter.labels(model=model_name).inc(completion_tokens)
        _requests_counter.labels(model=model_name).inc()
    except Exception:
        pass  # Prometheus-Fehler nie propagieren

    try:
        engine = get_sqlalchemy_engine()
        with Session(engine) as db_session:
            resolved_uid = _resolve_user_uuid(db_session, user_id) if user_id else None
            row = ExtTokenUsage(
                user_id=resolved_uid,
                model_name=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )
            db_session.add(row)
            db_session.commit()
            logger.debug(
                "Token usage logged: user=%s model=%s tokens=%d",
                user_id,
                model_name,
                total_tokens,
            )
    except Exception:
        logger.warning("Failed to log token usage", exc_info=True)


# ---------------------------------------------------------------------------
# Enforcement (called from multi_llm.py hook, before LLM call)
# ---------------------------------------------------------------------------


def check_user_token_limit(user_id: str) -> None:
    """Check if user has exceeded their token budget. Raises HTTPException(429)."""
    engine = get_sqlalchemy_engine()
    with Session(engine) as db_session:
        resolved_uid = _resolve_user_uuid(db_session, user_id)
        if resolved_uid is None:
            return  # Unknown user or anonymous — no limit to check

        limit = db_session.execute(
            select(ExtTokenUserLimit).where(
                ExtTokenUserLimit.user_id == resolved_uid,
                ExtTokenUserLimit.enabled.is_(True),
            )
        ).scalar_one_or_none()

        if limit is None:
            return

        window_start = datetime.now(timezone.utc) - timedelta(hours=limit.period_hours)

        usage = db_session.execute(
            select(func.coalesce(func.sum(ExtTokenUsage.total_tokens), 0)).where(
                ExtTokenUsage.user_id == resolved_uid,
                ExtTokenUsage.created_at >= window_start,
            )
        ).scalar_one()

        budget_tokens = limit.token_budget * TOKEN_BUDGET_UNIT

        if usage >= budget_tokens:
            # Calculate reset time: oldest relevant entry + period
            oldest_in_window = db_session.execute(
                select(func.min(ExtTokenUsage.created_at)).where(
                    ExtTokenUsage.user_id == resolved_uid,
                    ExtTokenUsage.created_at >= window_start,
                )
            ).scalar_one()

            if oldest_in_window:
                reset_at = oldest_in_window + timedelta(hours=limit.period_hours)
                remaining = reset_at - datetime.now(timezone.utc)
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                detail = (
                    f"Token-Limit erreicht. "
                    f"Naechstes Fenster beginnt in {hours}h {minutes}min."
                )
            else:
                detail = "Token-Limit erreicht."

            raise HTTPException(status_code=429, detail=detail)


# ---------------------------------------------------------------------------
# Usage Summary (for dashboard)
# ---------------------------------------------------------------------------


def get_usage_summary(
    db_session: Session,
    period_hours: int,
    user_id: UUID | None = None,
    model_name: str | None = None,
) -> dict:
    """Aggregate usage stats for the given time window."""
    window_start = datetime.now(timezone.utc) - timedelta(hours=period_hours)

    base_filter = [ExtTokenUsage.created_at >= window_start]
    if user_id:
        base_filter.append(ExtTokenUsage.user_id == user_id)
    if model_name:
        base_filter.append(ExtTokenUsage.model_name == model_name)

    # Totals
    totals = db_session.execute(
        select(
            func.coalesce(func.sum(ExtTokenUsage.prompt_tokens), 0),
            func.coalesce(func.sum(ExtTokenUsage.completion_tokens), 0),
            func.coalesce(func.sum(ExtTokenUsage.total_tokens), 0),
            func.count(ExtTokenUsage.id),
        ).where(*base_filter)
    ).one()

    # By user
    by_user_rows = db_session.execute(
        select(
            ExtTokenUsage.user_id,
            func.coalesce(func.sum(ExtTokenUsage.total_tokens), 0),
            func.count(ExtTokenUsage.id),
        )
        .where(*base_filter)
        .where(ExtTokenUsage.user_id.isnot(None))
        .group_by(ExtTokenUsage.user_id)
        .order_by(func.sum(ExtTokenUsage.total_tokens).desc())
    ).all()

    # Resolve user emails
    user_ids = [row[0] for row in by_user_rows]
    email_map: dict[UUID, str | None] = {}
    if user_ids:
        users = db_session.execute(
            select(User.id, User.email).where(User.id.in_(user_ids))
        ).all()
        email_map = {u.id: u.email for u in users}

    by_user = [
        {
            "user_id": str(row[0]),
            "user_email": email_map.get(row[0]),
            "total_tokens": row[1],
            "total_requests": row[2],
        }
        for row in by_user_rows
    ]

    # By model
    by_model_rows = db_session.execute(
        select(
            ExtTokenUsage.model_name,
            func.coalesce(func.sum(ExtTokenUsage.total_tokens), 0),
            func.count(ExtTokenUsage.id),
        )
        .where(*base_filter)
        .group_by(ExtTokenUsage.model_name)
        .order_by(func.sum(ExtTokenUsage.total_tokens).desc())
    ).all()

    by_model = [
        {
            "model_name": row[0],
            "total_tokens": row[1],
            "total_requests": row[2],
        }
        for row in by_model_rows
    ]

    return {
        "period_hours": period_hours,
        "total_prompt_tokens": totals[0],
        "total_completion_tokens": totals[1],
        "total_tokens": totals[2],
        "total_requests": totals[3],
        "by_user": by_user,
        "by_model": by_model,
    }


# ---------------------------------------------------------------------------
# Usage Timeseries (for dashboard charts)
# ---------------------------------------------------------------------------


def get_usage_timeseries(
    db_session: Session,
    period_hours: int,
    granularity: str = "hour",
    user_id: UUID | None = None,
    model_name: str | None = None,
) -> list[dict]:
    """Time-bucketed usage data. granularity: 'hour' or 'day'."""
    window_start = datetime.now(timezone.utc) - timedelta(hours=period_hours)

    base_filter = [ExtTokenUsage.created_at >= window_start]
    if user_id:
        base_filter.append(ExtTokenUsage.user_id == user_id)
    if model_name:
        base_filter.append(ExtTokenUsage.model_name == model_name)

    if granularity == "day":
        trunc = func.date_trunc("day", ExtTokenUsage.created_at)
    else:
        trunc = func.date_trunc("hour", ExtTokenUsage.created_at)

    rows = db_session.execute(
        select(
            trunc.label("bucket"),
            func.coalesce(func.sum(ExtTokenUsage.total_tokens), 0),
            func.coalesce(func.sum(ExtTokenUsage.prompt_tokens), 0),
            func.coalesce(func.sum(ExtTokenUsage.completion_tokens), 0),
            func.count(ExtTokenUsage.id),
        )
        .where(*base_filter)
        .group_by("bucket")
        .order_by("bucket")
    ).all()

    return [
        {
            "timestamp": row[0],
            "total_tokens": row[1],
            "prompt_tokens": row[2],
            "completion_tokens": row[3],
            "request_count": row[4],
        }
        for row in rows
        if row[0] is not None
    ]


# ---------------------------------------------------------------------------
# User Limits CRUD
# ---------------------------------------------------------------------------


def get_user_limits(db_session: Session) -> list[dict]:
    """Get all per-user token limits with current usage."""
    limits = db_session.execute(
        select(ExtTokenUserLimit).order_by(ExtTokenUserLimit.created_at)
    ).scalars().all()

    if not limits:
        return []

    # Resolve emails
    user_ids = [lim.user_id for lim in limits]
    users = db_session.execute(
        select(User.id, User.email).where(User.id.in_(user_ids))
    ).all()
    email_map = {u.id: u.email for u in users}

    result = []
    for lim in limits:
        # Calculate current usage in the limit's window
        window_start = datetime.now(timezone.utc) - timedelta(hours=lim.period_hours)
        current_usage = db_session.execute(
            select(
                func.coalesce(func.sum(ExtTokenUsage.total_tokens), 0)
            ).where(
                ExtTokenUsage.user_id == lim.user_id,
                ExtTokenUsage.created_at >= window_start,
            )
        ).scalar_one()

        result.append(
            {
                "id": lim.id,
                "user_id": str(lim.user_id),
                "user_email": email_map.get(lim.user_id),
                "token_budget": lim.token_budget,
                "period_hours": lim.period_hours,
                "enabled": lim.enabled,
                "current_usage": current_usage,
            }
        )

    return result


def create_user_limit(
    db_session: Session,
    user_id: UUID,
    token_budget: int,
    period_hours: int,
    enabled: bool = True,
) -> ExtTokenUserLimit:
    """Create a per-user token limit. Raises 404 if user not found, 409 if exists."""
    user = db_session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db_session.execute(
        select(ExtTokenUserLimit).where(ExtTokenUserLimit.user_id == user_id)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409, detail="Limit already exists for this user"
        )

    limit = ExtTokenUserLimit(
        user_id=user_id,
        token_budget=token_budget,
        period_hours=period_hours,
        enabled=enabled,
    )
    db_session.add(limit)
    db_session.commit()
    db_session.refresh(limit)
    logger.info("User limit created: user=%s budget=%d period=%dh", user_id, token_budget, period_hours)
    return limit


def update_user_limit(
    db_session: Session,
    limit_id: int,
    token_budget: int,
    period_hours: int,
    enabled: bool = True,
) -> ExtTokenUserLimit:
    """Update an existing per-user token limit. Raises 404 if not found."""
    limit = db_session.get(ExtTokenUserLimit, limit_id)
    if limit is None:
        raise HTTPException(status_code=404, detail="Limit not found")

    limit.token_budget = token_budget
    limit.period_hours = period_hours
    limit.enabled = enabled
    db_session.commit()
    db_session.refresh(limit)
    logger.info("User limit updated: id=%d budget=%d period=%dh", limit_id, token_budget, period_hours)
    return limit


def delete_user_limit(db_session: Session, limit_id: int) -> None:
    """Delete a per-user token limit. Raises 404 if not found."""
    limit = db_session.get(ExtTokenUserLimit, limit_id)
    if limit is None:
        raise HTTPException(status_code=404, detail="Limit not found")

    db_session.execute(
        delete(ExtTokenUserLimit).where(ExtTokenUserLimit.id == limit_id)
    )
    db_session.commit()
    logger.info("User limit deleted: id=%d", limit_id)

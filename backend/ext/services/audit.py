"""ext-audit: Audit-Logging Service.

Zentrale Funktionen:
- log_audit_event(): Schreibt Audit-Event (best-effort, bricht nie den Request ab)
- query_audit_events(): Paginierte Abfrage mit Filtern
- export_audit_csv(): CSV-Export fuer Compliance
- anonymize_old_ips(): DSGVO IP-Anonymisierung (>90d)
"""

import csv
import io
import logging
from datetime import datetime
from datetime import timedelta
from datetime import timezone

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import Session

from ext.models.audit import ExtAuditLog
from onyx.db.models import User

logger = logging.getLogger("ext.audit")


def log_audit_event(
    db_session: Session,
    actor: User | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    resource_name: str | None = None,
    details: dict | None = None,
    audit_ctx: dict | None = None,
) -> None:
    """Schreibt ein Audit-Event in die DB + stdout.

    WICHTIG: Faengt ALLE Exceptions — bricht NIEMALS den Request ab.
    Audit ist best-effort, nicht transaktional mit der Haupt-Aktion.
    """
    try:
        from ext.config import EXT_AUDIT_ENABLED

        if not EXT_AUDIT_ENABLED:
            return
    except ImportError:
        return

    try:
        actor_email = actor.email if actor else None
        actor_role = actor.role.value if actor and hasattr(actor.role, "value") else None

        ip_address = None
        user_agent = None
        if audit_ctx:
            ip_address = audit_ctx.get("ip_address")
            user_agent = audit_ctx.get("user_agent")

        entry = ExtAuditLog(
            actor_email=actor_email,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db_session.add(entry)
        db_session.commit()

        logger.info(
            "[EXT-AUDIT] %s %s %s (by %s)",
            action,
            resource_type,
            resource_name or resource_id or "",
            actor_email or "SYSTEM",
        )
    except Exception:
        logger.error("[EXT-AUDIT] Failed to write audit event", exc_info=True)


def query_audit_events(
    db_session: Session,
    actor_email: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Paginierte Audit-Event Abfrage mit Filtern."""
    query = select(ExtAuditLog)

    if actor_email:
        query = query.where(ExtAuditLog.actor_email == actor_email)
    if action:
        query = query.where(ExtAuditLog.action == action)
    if resource_type:
        query = query.where(ExtAuditLog.resource_type == resource_type)
    if from_date:
        query = query.where(ExtAuditLog.timestamp >= from_date)
    if to_date:
        query = query.where(ExtAuditLog.timestamp <= to_date)

    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total = db_session.execute(count_query).scalar() or 0

    # Paginated results
    query = (
        query.order_by(ExtAuditLog.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    events = db_session.execute(query).scalars().all()

    return {
        "events": [_event_to_dict(e) for e in events],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def export_audit_csv(
    db_session: Session,
    from_date: datetime,
    to_date: datetime,
) -> str:
    """CSV-Export fuer Compliance-Reports."""
    query = (
        select(ExtAuditLog)
        .where(ExtAuditLog.timestamp >= from_date)
        .where(ExtAuditLog.timestamp <= to_date)
        .order_by(ExtAuditLog.timestamp.desc())
    )
    events = db_session.execute(query).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "timestamp", "actor_email", "actor_role", "action",
        "resource_type", "resource_id", "resource_name",
        "details", "ip_address",
    ])
    for e in events:
        writer.writerow([
            e.timestamp.isoformat() if e.timestamp else "",
            e.actor_email or "",
            e.actor_role or "",
            e.action,
            e.resource_type,
            e.resource_id or "",
            e.resource_name or "",
            str(e.details) if e.details else "",
            str(e.ip_address) if e.ip_address else "",
        ])

    return output.getvalue()


def anonymize_old_ips(db_session: Session) -> int:
    """DSGVO: IP-Adressen aelter als 90 Tage anonymisieren."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    count = (
        db_session.query(ExtAuditLog)
        .filter(ExtAuditLog.timestamp < cutoff)
        .filter(ExtAuditLog.ip_address.isnot(None))
        .update(
            {ExtAuditLog.ip_address: None, ExtAuditLog.user_agent: None},
            synchronize_session=False,
        )
    )
    db_session.commit()
    if count > 0:
        logger.info("[EXT-AUDIT] Anonymized IPs for %d events (>90d)", count)
    return count


def _event_to_dict(event: ExtAuditLog) -> dict:
    """Konvertiert ein Audit-Event in ein dict fuer die API-Response."""
    return {
        "id": str(event.id),
        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        "actor_email": event.actor_email,
        "actor_role": event.actor_role,
        "action": event.action,
        "resource_type": event.resource_type,
        "resource_id": event.resource_id,
        "resource_name": event.resource_name,
        "details": event.details,
        "ip_address": str(event.ip_address) if event.ip_address else None,
    }

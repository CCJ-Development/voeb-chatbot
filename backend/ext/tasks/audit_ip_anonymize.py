"""ext-audit: Taeglicher Celery-Task fuer DSGVO IP-Anonymisierung.

Setzt ip_address und user_agent auf NULL fuer alle ext_audit_log Eintraege
die aelter als 90 Tage sind. Laeuft alle 24 Stunden.

DSGVO Art. 5(1)(e) Speicherbegrenzung: IP-Adressen dienen der
Sicherheitsanalyse, 90 Tage Aufbewahrung ist verhaeltnismaessig.
Danach werden sie anonymisiert (nicht geloescht — Audit-Trail bleibt).

Architektur: Gleiche Self-Scheduling-Pattern wie ext_doc_access_sync.
Idempotent — Mehrfachausfuehrung ist harmlos (UPDATE WHERE ip IS NOT NULL).
"""

import logging

from celery import shared_task

logger = logging.getLogger("ext.audit")

# 24 Stunden in Sekunden
_ANONYMIZE_INTERVAL = 86400


@shared_task(
    name="ext_audit_ip_anonymize",
    soft_time_limit=120,
    bind=True,
)
def ext_audit_ip_anonymize_task(self) -> None:  # type: ignore[no-untyped-def]  # noqa: ARG001
    """DSGVO: IP-Adressen aelter als 90 Tage anonymisieren. Laeuft taeglich."""
    try:
        from ext.config import EXT_AUDIT_ENABLED

        if not EXT_AUDIT_ENABLED:
            return
    except ImportError:
        return

    from onyx.db.engine.sql_engine import get_session_with_current_tenant

    try:
        with get_session_with_current_tenant() as db_session:
            from ext.services.audit import anonymize_old_ips

            count = anonymize_old_ips(db_session)
            if count > 0:
                logger.info(
                    "[EXT-AUDIT] IP anonymization: %d events anonymized", count
                )
    except Exception:
        logger.error("[EXT-AUDIT] IP anonymization task failed", exc_info=True)
    finally:
        # Re-schedule: naechster Lauf in 24h
        try:
            ext_audit_ip_anonymize_task.apply_async(countdown=_ANONYMIZE_INTERVAL)
        except Exception:
            logger.error("[EXT-AUDIT] Failed to re-schedule anonymization", exc_info=True)

"""ext-access: Periodischer Celery-Task fuer UserGroup ACL-Sync.

Prueft alle 60 Sekunden ob UserGroups mit is_up_to_date=False existieren
und aktualisiert die OpenSearch-ACLs fuer deren Dokumente.

Dieser Task umgeht bewusst die Onyx-Sync-Pipeline (redis_usergroup.py + tasks.py),
die durch EE-Guards blockiert ist. Stattdessen: einfacher Loop mit direktem
OpenSearch-Update. Ausreichend fuer ~150 User.

Architekturentscheidung: Ansatz C (docs/technisches-feinkonzept/ext-access.md)
"""

import logging

from celery import shared_task

logger = logging.getLogger("ext.doc_access")

# Sync-Intervall: Alle 60 Sekunden
EXT_DOC_ACCESS_SYNC_INTERVAL = 60


@shared_task(
    name="ext_doc_access_sync",
    soft_time_limit=300,  # 5 Min Timeout
    bind=True,
)
def ext_doc_access_sync_task(self) -> None:  # type: ignore[no-untyped-def]  # noqa: ARG001
    """Periodischer Sync: UserGroup-Aenderungen → OpenSearch ACLs."""
    try:
        from ext.config import EXT_DOC_ACCESS_ENABLED

        if not EXT_DOC_ACCESS_ENABLED:
            return
    except ImportError:
        return

    from onyx.db.engine.sql_engine import get_session_with_current_tenant

    try:
        with get_session_with_current_tenant() as db_session:
            from ext.services.doc_access import sync_usergroup_acls

            result = sync_usergroup_acls(db_session)
            if result["synced"] > 0:
                logger.info(
                    "[EXT-ACCESS] Sync completed: %d groups, %d documents",
                    result["synced"],
                    result["documents"],
                )
    except Exception:
        logger.error("[EXT-ACCESS] Sync task failed", exc_info=True)

"""ext-access: Admin-Endpoints fuer Document Access Control.

Endpoints:
- POST /ext/doc-access/resync  — Full Re-Sync aller Gruppen-ACLs
- GET  /ext/doc-access/status  — Aktueller Sync-Status
"""

import logging

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from ext.auth import current_admin_user
from onyx.db.engine.sql_engine import get_session
from onyx.db.models import User

from ext.routers.audit import get_audit_context
from ext.schemas.doc_access import ResyncResponse
from ext.schemas.doc_access import SyncStatusResponse
from ext.services.doc_access import get_sync_status
from ext.services.doc_access import trigger_full_resync

logger = logging.getLogger("ext.doc_access")

router = APIRouter(prefix="/ext/doc-access", tags=["ext-access"])


@router.post("/resync")
def resync_all_groups(
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
    audit_ctx: dict = Depends(get_audit_context),
) -> ResyncResponse:
    """Markiert alle Gruppen fuer ACL Re-Sync.

    Noetig bei:
    - Erstmalige Aktivierung von ext-access
    - Nach manuellem Daten-Fix
    """
    result = trigger_full_resync(db_session)
    from ext.services.audit import log_audit_event

    log_audit_event(db_session, user, "RESYNC", "DOC_ACCESS",
                    details={"groups_queued": result["groups_queued"]},
                    audit_ctx=audit_ctx)
    logger.info(
        f"[EXT-ACCESS] Resync triggered by admin: "
        f"{result['groups_queued']} groups"
    )
    return ResyncResponse(
        status="started",
        groups_queued=result["groups_queued"],
        estimated_documents=result["estimated_documents"],
    )


@router.get("/status")
def get_access_status(
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> SyncStatusResponse:
    """Aktueller Sync-Status."""
    status = get_sync_status(db_session)
    return SyncStatusResponse(**status)

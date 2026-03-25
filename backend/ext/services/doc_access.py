"""ext-access: Document Access Control via UserGroups.

Ermoeglicht gruppen-basierte Dokumentzugriffskontrolle.
Dokumente sind nur fuer User sichtbar, deren Gruppe dem
ConnectorCredentialPair des Dokuments zugewiesen ist.

Architektur (Ansatz C):
- Core #3 Hooks in access.py befuellen user_groups bei Indexierung + Suche
- Eigener Celery-Task synced ACLs bei Gruppenaenderungen (kein Onyx-Sync-Pipeline Patching)
"""

import logging
from datetime import datetime
from datetime import timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from onyx.access.models import DocumentAccess
from onyx.access.utils import prefix_user_group
from onyx.db.models import ConnectorCredentialPair
from onyx.db.models import DocumentByConnectorCredentialPair
from onyx.db.models import User
from onyx.db.models import User__UserGroup
from onyx.db.models import UserGroup
from onyx.db.models import UserGroup__ConnectorCredentialPair

logger = logging.getLogger("ext.doc_access")


# ---------------------------------------------------------------------------
# Query-Funktionen (aufgerufen von Core #3 Hooks)
# ---------------------------------------------------------------------------


def get_group_acls_for_user(user: User, db_session: Session) -> set[str]:
    """Alle Gruppen-ACL-Strings fuer einen User.

    Wird von Core #3 Hook in _get_acl_for_user() aufgerufen.
    Liefert z.B. {"user_group:Kreditabteilung", "user_group:IT"}.
    """
    groups = (
        db_session.query(UserGroup.name)
        .join(
            User__UserGroup,
            UserGroup.id == User__UserGroup.user_group_id,
        )
        .filter(User__UserGroup.user_id == user.id)
        .all()
    )
    return {prefix_user_group(name) for (name,) in groups}


def get_user_groups_for_document(
    document_id: str, db_session: Session
) -> list[str]:
    """Alle Gruppennamen die Zugriff auf ein Dokument haben.

    Wird von Core #3 Hook in _get_access_for_document(s)() aufgerufen.
    Join-Kette: Document → DocumentByCC → ConnectorCredentialPair → UserGroup__CC → UserGroup
    """
    groups = (
        db_session.query(UserGroup.name)
        .join(
            UserGroup__ConnectorCredentialPair,
            UserGroup.id == UserGroup__ConnectorCredentialPair.user_group_id,
        )
        .join(
            ConnectorCredentialPair,
            UserGroup__ConnectorCredentialPair.cc_pair_id
            == ConnectorCredentialPair.id,
        )
        .join(
            DocumentByConnectorCredentialPair,
            (
                ConnectorCredentialPair.connector_id
                == DocumentByConnectorCredentialPair.connector_id
            )
            & (
                ConnectorCredentialPair.credential_id
                == DocumentByConnectorCredentialPair.credential_id
            ),
        )
        .filter(DocumentByConnectorCredentialPair.id == document_id)
        .distinct()
        .all()
    )
    return [name for (name,) in groups]


# ---------------------------------------------------------------------------
# Sync-Funktionen (aufgerufen vom Celery-Task)
# ---------------------------------------------------------------------------


def get_document_ids_for_group(
    group_id: int, db_session: Session
) -> list[str]:
    """Alle Dokument-IDs die zu einer Gruppe gehoeren (via CC-Pairs)."""
    doc_ids = (
        db_session.query(DocumentByConnectorCredentialPair.id)
        .join(
            ConnectorCredentialPair,
            (
                ConnectorCredentialPair.connector_id
                == DocumentByConnectorCredentialPair.connector_id
            )
            & (
                ConnectorCredentialPair.credential_id
                == DocumentByConnectorCredentialPair.credential_id
            ),
        )
        .join(
            UserGroup__ConnectorCredentialPair,
            ConnectorCredentialPair.id
            == UserGroup__ConnectorCredentialPair.cc_pair_id,
        )
        .filter(UserGroup__ConnectorCredentialPair.user_group_id == group_id)
        .distinct()
        .all()
    )
    return [doc_id for (doc_id,) in doc_ids]


def sync_usergroup_acls(db_session: Session) -> dict:
    """Sync-Job: Aktualisiert OpenSearch ACLs fuer geaenderte Gruppen.

    Findet Gruppen mit is_up_to_date=False, berechnet deren Dokument-ACLs
    neu und aktualisiert den OpenSearch-Index.
    """
    from onyx.access.access import get_access_for_document
    from onyx.db.engine.sql_engine import get_session_with_current_tenant
    from onyx.document_index.factory import get_default_document_index
    from onyx.document_index.interfaces import UpdateRequest

    pending_groups = (
        db_session.query(UserGroup)
        .filter(UserGroup.is_up_to_date == False)  # noqa: E712
        .filter(UserGroup.is_up_for_deletion == False)  # noqa: E712
        .all()
    )

    if not pending_groups:
        return {"synced": 0, "documents": 0}

    document_index = get_default_document_index()
    total_docs = 0

    for group in pending_groups:
        doc_ids = get_document_ids_for_group(group.id, db_session)
        logger.info(
            f"[EXT-ACCESS] Syncing group '{group.name}' "
            f"(id={group.id}): {len(doc_ids)} documents"
        )

        # ACLs fuer jedes Dokument neu berechnen
        for doc_id in doc_ids:
            try:
                access = get_access_for_document(doc_id, db_session)
                update_request = UpdateRequest(
                    document_ids=[doc_id],
                    access=access,
                )
                document_index.update_single(update_request)
                total_docs += 1
            except Exception:
                logger.error(
                    f"[EXT-ACCESS] Failed to sync doc {doc_id} "
                    f"for group {group.name}",
                    exc_info=True,
                )

        # Gruppe als synced markieren
        group.is_up_to_date = True

    db_session.commit()

    logger.info(
        f"[EXT-ACCESS] Sync complete: {len(pending_groups)} groups, "
        f"{total_docs} documents"
    )
    return {"synced": len(pending_groups), "documents": total_docs}


def trigger_full_resync(db_session: Session) -> dict:
    """Markiert ALLE Gruppen fuer Re-Sync.

    Noetig bei Erstaktivierung (bestehende Dokumente haben keine group: ACLs)
    oder nach manuellem Daten-Fix.
    """
    count = (
        db_session.query(UserGroup)
        .filter(UserGroup.is_up_for_deletion == False)  # noqa: E712
        .update({UserGroup.is_up_to_date: False})
    )
    db_session.commit()

    logger.info(f"[EXT-ACCESS] Full resync triggered: {count} groups queued")

    # Geschaetzte Dokumente zaehlen
    estimated_docs = (
        db_session.query(
            func.count(DocumentByConnectorCredentialPair.id.distinct())
        )
        .join(
            ConnectorCredentialPair,
            (
                ConnectorCredentialPair.connector_id
                == DocumentByConnectorCredentialPair.connector_id
            )
            & (
                ConnectorCredentialPair.credential_id
                == DocumentByConnectorCredentialPair.credential_id
            ),
        )
        .join(
            UserGroup__ConnectorCredentialPair,
            ConnectorCredentialPair.id
            == UserGroup__ConnectorCredentialPair.cc_pair_id,
        )
        .scalar()
        or 0
    )

    return {"groups_queued": count, "estimated_documents": estimated_docs}


def get_sync_status(db_session: Session) -> dict:
    """Aktueller Sync-Status fuer Admin-Endpoint."""
    total = db_session.query(func.count(UserGroup.id)).scalar() or 0
    pending = (
        db_session.query(func.count(UserGroup.id))
        .filter(UserGroup.is_up_to_date == False)  # noqa: E712
        .filter(UserGroup.is_up_for_deletion == False)  # noqa: E712
        .scalar()
        or 0
    )

    return {
        "enabled": True,
        "groups_total": total,
        "groups_synced": total - pending,
        "groups_pending": pending,
    }

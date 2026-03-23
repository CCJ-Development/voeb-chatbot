"""Business logic for ext-rbac (Group Management).

Operates on existing FOSS database tables (user_group, user__user_group, etc.).
No new tables or migrations required.

Core functions:
- CRUD for UserGroup
- User-to-group assignment with is_curator
- Curator validation (CVE-2025-51479)
- Curator auto-demotion
- Response building compatible with TypeScript UserGroup interface
"""

import logging
from datetime import datetime
from datetime import timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from onyx.auth.schemas import UserRole
from onyx.db.models import ConnectorCredentialPair
from onyx.db.models import Credential__UserGroup
from onyx.db.models import DocumentSet__UserGroup
from onyx.db.models import LLMProvider__UserGroup
from onyx.db.models import Persona__UserGroup
from onyx.db.models import TokenRateLimit__UserGroup
from onyx.db.models import User
from onyx.db.models import User__UserGroup
from onyx.db.models import UserGroup
from onyx.db.models import UserGroup__ConnectorCredentialPair

logger = logging.getLogger("ext.rbac")


# --- Curator Validation (CVE-2025-51479) ---


def validate_curator_for_group(
    db_session: Session,
    user: User,
    user_group_id: int,
) -> None:
    """Validate that a curator has permission for this specific group.

    Admin: always allowed.
    GLOBAL_CURATOR: must be member of the group.
    CURATOR: must have is_curator=True for THIS group.
    """
    if user.role == UserRole.ADMIN:
        return

    if user.role == UserRole.GLOBAL_CURATOR:
        membership = db_session.execute(
            select(User__UserGroup).where(
                User__UserGroup.user_group_id == user_group_id,
                User__UserGroup.user_id == user.id,
            )
        ).scalar_one_or_none()
        if not membership:
            raise HTTPException(
                status_code=403,
                detail="Not a member of this group",
            )
        return

    if user.role == UserRole.CURATOR:
        membership = db_session.execute(
            select(User__UserGroup).where(
                User__UserGroup.user_group_id == user_group_id,
                User__UserGroup.user_id == user.id,
                User__UserGroup.is_curator == True,  # noqa: E712
            )
        ).scalar_one_or_none()
        if not membership:
            raise HTTPException(
                status_code=403,
                detail="Not a curator of this group",
            )
        return

    raise HTTPException(status_code=403, detail="Insufficient permissions")


# --- Curator Demotion ---


def _check_and_demote_curator(
    db_session: Session,
    user_id: UUID,
) -> None:
    """Demote user to BASIC if they have no remaining curator groups.

    Only applies to CURATOR role. GLOBAL_CURATOR and ADMIN are never demoted.
    """
    user = db_session.get(User, user_id)
    if not user or user.role != UserRole.CURATOR:
        return

    remaining = db_session.execute(
        select(func.count()).where(
            User__UserGroup.user_id == user_id,
            User__UserGroup.is_curator == True,  # noqa: E712
        )
    ).scalar_one()

    if remaining == 0:
        user.role = UserRole.BASIC
        logger.info(
            "[EXT-RBAC] User %s demoted to BASIC (no curator groups left)",
            user.email,
        )


# --- Response Building ---


def _build_user_group_response(
    db_session: Session,
    group: UserGroup,
) -> dict:
    """Build response dict compatible with TypeScript UserGroup interface.

    Interface expects: id, name, users[], curator_ids[], cc_pairs[],
    document_sets[], personas[], is_up_to_date, is_up_for_deletion
    """
    # Fetch memberships with curator flag
    memberships = db_session.execute(
        select(User__UserGroup).where(
            User__UserGroup.user_group_id == group.id
        )
    ).scalars().all()

    user_ids = [m.user_id for m in memberships if m.user_id is not None]
    curator_ids = [
        str(m.user_id) for m in memberships
        if m.is_curator and m.user_id is not None
    ]

    # Fetch users
    users = []
    if user_ids:
        user_rows = db_session.execute(
            select(User).where(User.id.in_(user_ids))
        ).scalars().all()
        users = [
            {
                "id": str(u.id),
                "email": u.email or "",
                "role": u.role.value if u.role else "basic",
            }
            for u in user_rows
        ]

    # Fetch cc_pairs (only current)
    cc_pair_rows = db_session.execute(
        select(UserGroup__ConnectorCredentialPair).where(
            UserGroup__ConnectorCredentialPair.user_group_id == group.id,
            UserGroup__ConnectorCredentialPair.is_current == True,  # noqa: E712
        )
    ).scalars().all()

    cc_pairs = []
    if cc_pair_rows:
        cc_pair_ids = [r.cc_pair_id for r in cc_pair_rows]
        pairs = db_session.execute(
            select(ConnectorCredentialPair).where(
                ConnectorCredentialPair.id.in_(cc_pair_ids)
            )
        ).scalars().all()
        cc_pairs = [
            {
                "id": p.id,
                "name": p.name or f"CC Pair {p.id}",
                "connector": {
                    "id": p.connector_id,
                    "name": p.connector.name if p.connector else "",
                    "source": p.connector.source.value if p.connector else "",
                },
            }
            for p in pairs
        ]

    # Fetch personas
    persona_rows = db_session.execute(
        select(Persona__UserGroup.persona_id).where(
            Persona__UserGroup.user_group_id == group.id
        )
    ).scalars().all()

    personas = []
    if persona_rows:
        from onyx.db.models import Persona

        persona_objs = db_session.execute(
            select(Persona).where(Persona.id.in_(persona_rows))
        ).scalars().all()
        personas = [
            {"id": p.id, "name": p.name or f"Persona {p.id}"}
            for p in persona_objs
        ]

    # Fetch document sets
    doc_set_rows = db_session.execute(
        select(DocumentSet__UserGroup.document_set_id).where(
            DocumentSet__UserGroup.user_group_id == group.id
        )
    ).scalars().all()

    document_sets = []
    if doc_set_rows:
        from onyx.db.models import DocumentSet

        doc_set_objs = db_session.execute(
            select(DocumentSet).where(DocumentSet.id.in_(doc_set_rows))
        ).scalars().all()
        document_sets = [
            {"id": ds.id, "name": ds.name or f"DocSet {ds.id}"}
            for ds in doc_set_objs
        ]

    return {
        "id": group.id,
        "name": group.name,
        "users": users,
        "curator_ids": curator_ids,
        "cc_pairs": cc_pairs,
        "document_sets": document_sets,
        "personas": personas,
        "is_up_to_date": group.is_up_to_date,
        "is_up_for_deletion": group.is_up_for_deletion,
    }


# --- CRUD Operations ---


def fetch_all_user_groups(
    db_session: Session,
    user: User,
) -> list[dict]:
    """Fetch all groups. Curators only see groups they curate."""
    if user.role == UserRole.ADMIN:
        groups = db_session.execute(
            select(UserGroup).where(
                UserGroup.is_up_for_deletion == False  # noqa: E712
            ).order_by(UserGroup.name)
        ).scalars().all()
    elif user.role in (UserRole.CURATOR, UserRole.GLOBAL_CURATOR):
        # Only groups where user is curator
        groups = db_session.execute(
            select(UserGroup)
            .join(User__UserGroup)
            .where(
                User__UserGroup.user_id == user.id,
                User__UserGroup.is_curator == True,  # noqa: E712
                UserGroup.is_up_for_deletion == False,  # noqa: E712
            )
            .order_by(UserGroup.name)
        ).scalars().all()
    else:
        return []

    return [_build_user_group_response(db_session, g) for g in groups]


def fetch_user_group_by_id(
    db_session: Session,
    user_group_id: int,
) -> UserGroup:
    """Fetch a single group by ID. Raises 404 if not found."""
    group = db_session.get(UserGroup, user_group_id)
    if not group or group.is_up_for_deletion:
        raise HTTPException(status_code=404, detail="User group not found")
    return group


def create_user_group(
    db_session: Session,
    name: str,
    user_ids: list[UUID],
    cc_pair_ids: list[int],
) -> dict:
    """Create a new group with optional initial members and cc_pairs."""
    # Check name uniqueness
    existing = db_session.execute(
        select(UserGroup).where(UserGroup.name == name)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Group with name '{name}' already exists",
        )

    # Validate user_ids exist
    if user_ids:
        found_count = db_session.execute(
            select(func.count()).where(User.id.in_(user_ids))
        ).scalar_one()
        if found_count != len(user_ids):
            raise HTTPException(
                status_code=404,
                detail="One or more user IDs not found",
            )

    # Validate cc_pair_ids exist
    if cc_pair_ids:
        found_count = db_session.execute(
            select(func.count()).where(
                ConnectorCredentialPair.id.in_(cc_pair_ids)
            )
        ).scalar_one()
        if found_count != len(cc_pair_ids):
            raise HTTPException(
                status_code=404,
                detail="One or more connector credential pair IDs not found",
            )

    # Create group
    group = UserGroup(
        name=name,
        is_up_to_date=False,
        is_up_for_deletion=False,
        time_last_modified_by_user=datetime.now(timezone.utc),
    )
    db_session.add(group)
    db_session.flush()  # Get group.id

    # Add users
    for uid in user_ids:
        db_session.add(
            User__UserGroup(
                user_group_id=group.id,
                user_id=uid,
                is_curator=False,
            )
        )

    # Add cc_pairs
    for cc_id in cc_pair_ids:
        db_session.add(
            UserGroup__ConnectorCredentialPair(
                user_group_id=group.id,
                cc_pair_id=cc_id,
                is_current=True,
            )
        )

    db_session.commit()
    logger.info("[EXT-RBAC] Group '%s' created (id=%d)", name, group.id)

    return _build_user_group_response(db_session, group)


def update_user_group(
    db_session: Session,
    user_group_id: int,
    user_ids: list[UUID],
    cc_pair_ids: list[int],
) -> dict:
    """Update group members and cc_pairs. Replaces complete lists."""
    group = fetch_user_group_by_id(db_session, user_group_id)

    # Validate user_ids
    if user_ids:
        found_count = db_session.execute(
            select(func.count()).where(User.id.in_(user_ids))
        ).scalar_one()
        if found_count != len(user_ids):
            raise HTTPException(
                status_code=404,
                detail="One or more user IDs not found",
            )

    # Validate cc_pair_ids
    if cc_pair_ids:
        found_count = db_session.execute(
            select(func.count()).where(
                ConnectorCredentialPair.id.in_(cc_pair_ids)
            )
        ).scalar_one()
        if found_count != len(cc_pair_ids):
            raise HTTPException(
                status_code=404,
                detail="One or more connector credential pair IDs not found",
            )

    # Track old curators for demotion check
    old_curator_ids = [
        m.user_id
        for m in db_session.execute(
            select(User__UserGroup).where(
                User__UserGroup.user_group_id == user_group_id,
                User__UserGroup.is_curator == True,  # noqa: E712
            )
        ).scalars().all()
        if m.user_id is not None
    ]

    # Replace users — preserve curator status for users that remain
    existing_memberships = {
        m.user_id: m.is_curator
        for m in db_session.execute(
            select(User__UserGroup).where(
                User__UserGroup.user_group_id == user_group_id
            )
        ).scalars().all()
        if m.user_id is not None
    }

    db_session.execute(
        delete(User__UserGroup).where(
            User__UserGroup.user_group_id == user_group_id
        )
    )

    new_user_id_set = set(user_ids)
    for uid in user_ids:
        db_session.add(
            User__UserGroup(
                user_group_id=user_group_id,
                user_id=uid,
                is_curator=existing_memberships.get(uid, False),
            )
        )

    # Replace cc_pairs
    db_session.execute(
        delete(UserGroup__ConnectorCredentialPair).where(
            UserGroup__ConnectorCredentialPair.user_group_id == user_group_id
        )
    )
    for cc_id in cc_pair_ids:
        db_session.add(
            UserGroup__ConnectorCredentialPair(
                user_group_id=user_group_id,
                cc_pair_id=cc_id,
                is_current=True,
            )
        )

    group.is_up_to_date = False
    group.time_last_modified_by_user = datetime.now(timezone.utc)

    db_session.commit()

    # Check curator demotion for removed curators
    for curator_id in old_curator_ids:
        if curator_id not in new_user_id_set:
            _check_and_demote_curator(db_session, curator_id)
            db_session.commit()

    logger.info("[EXT-RBAC] Group '%s' updated (id=%d)", group.name, group.id)
    return _build_user_group_response(db_session, group)


def delete_user_group(
    db_session: Session,
    user_group_id: int,
) -> None:
    """Hard delete a group and all M2M associations."""
    group = fetch_user_group_by_id(db_session, user_group_id)

    # Track curators for demotion
    curator_user_ids = [
        m.user_id
        for m in db_session.execute(
            select(User__UserGroup).where(
                User__UserGroup.user_group_id == user_group_id,
                User__UserGroup.is_curator == True,  # noqa: E712
            )
        ).scalars().all()
        if m.user_id is not None
    ]

    group_name = group.name

    # Delete all M2M associations
    db_session.execute(
        delete(User__UserGroup).where(
            User__UserGroup.user_group_id == user_group_id
        )
    )
    db_session.execute(
        delete(UserGroup__ConnectorCredentialPair).where(
            UserGroup__ConnectorCredentialPair.user_group_id == user_group_id
        )
    )
    db_session.execute(
        delete(Persona__UserGroup).where(
            Persona__UserGroup.user_group_id == user_group_id
        )
    )
    db_session.execute(
        delete(LLMProvider__UserGroup).where(
            LLMProvider__UserGroup.user_group_id == user_group_id
        )
    )
    db_session.execute(
        delete(DocumentSet__UserGroup).where(
            DocumentSet__UserGroup.user_group_id == user_group_id
        )
    )
    db_session.execute(
        delete(Credential__UserGroup).where(
            Credential__UserGroup.user_group_id == user_group_id
        )
    )
    db_session.execute(
        delete(TokenRateLimit__UserGroup).where(
            TokenRateLimit__UserGroup.user_group_id == user_group_id
        )
    )

    # Delete group itself
    db_session.delete(group)
    db_session.commit()

    # Check curator demotion for former curators
    for curator_id in curator_user_ids:
        _check_and_demote_curator(db_session, curator_id)
        db_session.commit()

    logger.info("[EXT-RBAC] Group '%s' deleted (id=%d)", group_name, user_group_id)


def add_users_to_group(
    db_session: Session,
    user_group_id: int,
    user_ids: list[UUID],
) -> None:
    """Add users to a group (additive, does not remove existing)."""
    group = fetch_user_group_by_id(db_session, user_group_id)

    # Validate user_ids
    found_count = db_session.execute(
        select(func.count()).where(User.id.in_(user_ids))
    ).scalar_one()
    if found_count != len(user_ids):
        raise HTTPException(
            status_code=404, detail="One or more user IDs not found"
        )

    # Get existing members
    existing = set(
        db_session.execute(
            select(User__UserGroup.user_id).where(
                User__UserGroup.user_group_id == user_group_id
            )
        ).scalars().all()
    )

    added = 0
    for uid in user_ids:
        if uid not in existing:
            db_session.add(
                User__UserGroup(
                    user_group_id=user_group_id,
                    user_id=uid,
                    is_curator=False,
                )
            )
            added += 1

    if added > 0:
        group.is_up_to_date = False
        group.time_last_modified_by_user = datetime.now(timezone.utc)
        db_session.commit()
        logger.info(
            "[EXT-RBAC] %d users added to group '%s'", added, group.name
        )


def set_curator_status(
    db_session: Session,
    user_group_id: int,
    user_id: UUID,
    is_curator: bool,
) -> None:
    """Set curator status for a user in a group.

    Also sets user.role to CURATOR (if is_curator=True)
    or demotes to BASIC (if last curator group removed).
    """
    group = fetch_user_group_by_id(db_session, user_group_id)

    # User must be member of the group
    membership = db_session.execute(
        select(User__UserGroup).where(
            User__UserGroup.user_group_id == user_group_id,
            User__UserGroup.user_id == user_id,
        )
    ).scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=400,
            detail="User is not a member of this group",
        )

    membership.is_curator = is_curator

    # Set user role
    user = db_session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if is_curator and user.role == UserRole.BASIC:
        user.role = UserRole.CURATOR
        logger.info(
            "[EXT-RBAC] User %s promoted to CURATOR (group '%s')",
            user.email,
            group.name,
        )

    db_session.commit()

    # If removing curator, check if demotion needed
    if not is_curator:
        _check_and_demote_curator(db_session, user_id)
        db_session.commit()


def fetch_minimal_user_groups(
    db_session: Session,
    user: User,
) -> list[dict]:
    """Fetch minimal group list (id + name) for non-admin contexts.

    Admin sees all groups. Other users see only their own groups.
    """
    if user.role == UserRole.ADMIN:
        groups = db_session.execute(
            select(UserGroup.id, UserGroup.name).where(
                UserGroup.is_up_for_deletion == False  # noqa: E712
            ).order_by(UserGroup.name)
        ).all()
    else:
        groups = db_session.execute(
            select(UserGroup.id, UserGroup.name)
            .join(User__UserGroup)
            .where(
                User__UserGroup.user_id == user.id,
                UserGroup.is_up_for_deletion == False,  # noqa: E712
            )
            .order_by(UserGroup.name)
        ).all()

    return [{"id": g.id, "name": g.name} for g in groups]

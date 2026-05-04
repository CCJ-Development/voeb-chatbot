"""FastAPI router for ext-rbac (Group Management).

Admin endpoints: /manage/admin/user-group (compatible with existing frontend)
Minimal endpoint: /manage/user-groups/minimal (for Agent editor, LLM config)
"""

import logging

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from ext.auth import current_admin_user
from ext.routers.audit import get_audit_context
from ext.schemas.rbac import AddUsersRequest
from ext.schemas.rbac import SetCuratorRequest
from ext.schemas.rbac import UserGroupCreate
from ext.schemas.rbac import UserGroupUpdate
from ext.services.audit import log_audit_event
from ext.services.rbac import add_users_to_group
from ext.services.rbac import create_user_group
from ext.services.rbac import delete_user_group
from ext.services.rbac import fetch_all_user_groups
from ext.services.rbac import fetch_minimal_user_groups
from ext.services.rbac import set_curator_status
from ext.services.rbac import update_user_group
from ext.services.rbac import validate_curator_for_group
from onyx.auth.users import current_curator_or_admin_user
from onyx.auth.users import current_user
from onyx.db.engine.sql_engine import get_session
from onyx.db.models import User

logger = logging.getLogger("ext.rbac")

# Admin router — full CRUD, compatible with GroupsPage frontend
admin_router = APIRouter(
    prefix="/manage/admin/user-group",
    tags=["ext-rbac"],
)

# Minimal router — lightweight group list for non-admin contexts
minimal_router = APIRouter(
    prefix="/manage/user-groups",
    tags=["ext-rbac"],
)


# --- Endpoint 1: List all groups ---


@admin_router.get("")
def api_list_user_groups(
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
) -> list[dict]:
    return fetch_all_user_groups(db_session, user)


# --- Endpoint 2: Create group ---


@admin_router.post("", status_code=201)
def api_create_user_group(
    request: UserGroupCreate,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
    audit_ctx: dict = Depends(get_audit_context),
) -> dict:
    result = create_user_group(
        db_session,
        name=request.name,
        user_ids=request.user_ids,
        cc_pair_ids=request.cc_pair_ids,
    )
    log_audit_event(db_session, user, "CREATE", "GROUP",
                    resource_id=str(result.get("id", "")),
                    resource_name=request.name, audit_ctx=audit_ctx)
    return result


# --- Endpoint 3: Update group ---


@admin_router.patch("/{user_group_id}")
def api_update_user_group(
    user_group_id: int,
    request: UserGroupUpdate,
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
    audit_ctx: dict = Depends(get_audit_context),
) -> dict:
    validate_curator_for_group(db_session, user, user_group_id)
    result = update_user_group(
        db_session,
        user_group_id=user_group_id,
        user_ids=request.user_ids,
        cc_pair_ids=request.cc_pair_ids,
    )
    log_audit_event(db_session, user, "UPDATE", "GROUP",
                    resource_id=str(user_group_id), audit_ctx=audit_ctx)
    return result


# --- Endpoint 4: Delete group ---


@admin_router.delete("/{user_group_id}", status_code=204)
def api_delete_user_group(
    user_group_id: int,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
    audit_ctx: dict = Depends(get_audit_context),
) -> None:
    log_audit_event(db_session, user, "DELETE", "GROUP",
                    resource_id=str(user_group_id), audit_ctx=audit_ctx)
    delete_user_group(db_session, user_group_id)


# --- Endpoint 5: Add users to group ---


@admin_router.post("/{user_group_id}/add-users")
def api_add_users_to_group(
    user_group_id: int,
    request: AddUsersRequest,
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
    audit_ctx: dict = Depends(get_audit_context),
) -> None:
    validate_curator_for_group(db_session, user, user_group_id)
    add_users_to_group(db_session, user_group_id, request.user_ids)
    log_audit_event(db_session, user, "UPDATE", "GROUP_MEMBERS",
                    resource_id=str(user_group_id),
                    details={"users_added": len(request.user_ids)},
                    audit_ctx=audit_ctx)


# --- Endpoint 6: Set curator status ---


@admin_router.post("/{user_group_id}/set-curator")
def api_set_curator(
    user_group_id: int,
    request: SetCuratorRequest,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
    audit_ctx: dict = Depends(get_audit_context),
) -> None:
    set_curator_status(
        db_session,
        user_group_id=user_group_id,
        user_id=request.user_id,
        is_curator=request.is_curator,
    )
    log_audit_event(db_session, user, "UPDATE", "GROUP_CURATOR",
                    resource_id=str(user_group_id),
                    details={"user_id": str(request.user_id),
                             "is_curator": request.is_curator},
                    audit_ctx=audit_ctx)


# --- Endpoint 7: Minimal group list ---


@minimal_router.get("/minimal")
def api_minimal_user_groups(
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> list[dict]:
    return fetch_minimal_user_groups(db_session, user)

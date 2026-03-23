"""FastAPI router for ext-rbac (Group Management).

Admin endpoints: /manage/admin/user-group (compatible with existing frontend)
Minimal endpoint: /manage/user-groups/minimal (for Agent editor, LLM config)
"""

import logging

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from onyx.auth.users import current_admin_user
from onyx.auth.users import current_curator_or_admin_user
from onyx.auth.users import current_user
from onyx.db.engine.sql_engine import get_session
from onyx.db.models import User

from ext.schemas.rbac import AddUsersRequest
from ext.schemas.rbac import SetCuratorRequest
from ext.schemas.rbac import UserGroupCreate
from ext.schemas.rbac import UserGroupUpdate
from ext.services.rbac import add_users_to_group
from ext.services.rbac import create_user_group
from ext.services.rbac import delete_user_group
from ext.services.rbac import fetch_all_user_groups
from ext.services.rbac import fetch_minimal_user_groups
from ext.services.rbac import set_curator_status
from ext.services.rbac import update_user_group
from ext.services.rbac import validate_curator_for_group

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
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> dict:
    return create_user_group(
        db_session,
        name=request.name,
        user_ids=request.user_ids,
        cc_pair_ids=request.cc_pair_ids,
    )


# --- Endpoint 3: Update group ---


@admin_router.patch("/{user_group_id}")
def api_update_user_group(
    user_group_id: int,
    request: UserGroupUpdate,
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
) -> dict:
    validate_curator_for_group(db_session, user, user_group_id)
    return update_user_group(
        db_session,
        user_group_id=user_group_id,
        user_ids=request.user_ids,
        cc_pair_ids=request.cc_pair_ids,
    )


# --- Endpoint 4: Delete group ---


@admin_router.delete("/{user_group_id}", status_code=204)
def api_delete_user_group(
    user_group_id: int,
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> None:
    delete_user_group(db_session, user_group_id)


# --- Endpoint 5: Add users to group ---


@admin_router.post("/{user_group_id}/add-users")
def api_add_users_to_group(
    user_group_id: int,
    request: AddUsersRequest,
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
) -> None:
    validate_curator_for_group(db_session, user, user_group_id)
    add_users_to_group(db_session, user_group_id, request.user_ids)


# --- Endpoint 6: Set curator status ---


@admin_router.post("/{user_group_id}/set-curator")
def api_set_curator(
    user_group_id: int,
    request: SetCuratorRequest,
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> None:
    set_curator_status(
        db_session,
        user_group_id=user_group_id,
        user_id=request.user_id,
        is_curator=request.is_curator,
    )


# --- Endpoint 7: Minimal group list ---


@minimal_router.get("/minimal")
def api_minimal_user_groups(
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> list[dict]:
    return fetch_minimal_user_groups(db_session, user)

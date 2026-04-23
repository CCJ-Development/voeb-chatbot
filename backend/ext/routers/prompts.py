"""FastAPI router for ext-prompts (Custom System Prompts).

All endpoints require admin auth. Prefix: /ext/prompts
"""

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ext.auth import current_admin_user
from onyx.db.engine.sql_engine import get_session
from onyx.db.models import User

from ext.routers.audit import get_audit_context
from ext.services.audit import log_audit_event

from ext.schemas.prompts import PromptCreate
from ext.schemas.prompts import PromptPreviewResponse
from ext.schemas.prompts import PromptResponse
from ext.schemas.prompts import PromptUpdate
from ext.services.prompt_manager import create_prompt
from ext.services.prompt_manager import delete_prompt
from ext.services.prompt_manager import get_all_prompts
from ext.services.prompt_manager import get_assembled_prompt_text
from ext.services.prompt_manager import update_prompt

if TYPE_CHECKING:
    from ext.models.prompts import ExtCustomPrompt

logger = logging.getLogger("ext.prompts")

router = APIRouter(prefix="/ext/prompts", tags=["ext-prompts"])


def _to_response(row: "ExtCustomPrompt") -> PromptResponse:
    return PromptResponse(
        id=row.id,
        name=row.name,
        prompt_text=row.prompt_text,
        category=row.category,
        priority=row.priority,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/preview")
def api_prompt_preview(
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> PromptPreviewResponse:
    text, active_count, total_count = get_assembled_prompt_text(db_session)
    return PromptPreviewResponse(
        assembled_text=text,
        active_count=active_count,
        total_count=total_count,
    )


@router.get("")
def api_list_prompts(
    _: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> list[PromptResponse]:
    rows = get_all_prompts(db_session)
    return [_to_response(r) for r in rows]


@router.post("", status_code=201)
def api_create_prompt(
    body: PromptCreate,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
    audit_ctx: dict = Depends(get_audit_context),
) -> PromptResponse:
    row = create_prompt(db_session, body)
    log_audit_event(db_session, user, "CREATE", "PROMPT",
                    resource_id=str(row.id), resource_name=body.name,
                    audit_ctx=audit_ctx)
    return _to_response(row)


@router.put("/{prompt_id}")
def api_update_prompt(
    prompt_id: int,
    body: PromptUpdate,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
    audit_ctx: dict = Depends(get_audit_context),
) -> PromptResponse:
    row = update_prompt(db_session, prompt_id, body)
    if row is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    log_audit_event(db_session, user, "UPDATE", "PROMPT",
                    resource_id=str(prompt_id), audit_ctx=audit_ctx)
    return _to_response(row)


@router.delete("/{prompt_id}", status_code=204)
def api_delete_prompt(
    prompt_id: int,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
    audit_ctx: dict = Depends(get_audit_context),
) -> None:
    log_audit_event(db_session, user, "DELETE", "PROMPT",
                    resource_id=str(prompt_id), audit_ctx=audit_ctx)
    deleted = delete_prompt(db_session, prompt_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Prompt not found")

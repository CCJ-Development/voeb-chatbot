"""Business logic for ext-prompts (Custom System Prompts).

Handles CRUD operations and in-memory caching of assembled prompt text.
The cache ensures zero DB overhead per LLM call when warm (< 1ms).
"""

import logging
import os
import threading
import time
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from ext.models.prompts import ExtCustomPrompt

if TYPE_CHECKING:
    from ext.schemas.prompts import PromptCreate
    from ext.schemas.prompts import PromptUpdate

logger = logging.getLogger("ext.prompts")

# --- Cache configuration ---

_CACHE_TTL_SECONDS: int = int(
    os.getenv("EXT_PROMPTS_CACHE_TTL_SECONDS", "60")
)

# Module-global cache (thread-safe via lock)
_cache_lock = threading.Lock()
_cached_text: str = ""
_cache_timestamp: float = 0.0

# Soft limits (warning, not hard-block)
SOFT_LIMIT_ACTIVE_PROMPTS = 20
SOFT_LIMIT_TOTAL_CHARS = 50_000


# --- Cache functions ---


def get_cached_global_prompt() -> str:
    """Return assembled text of all active prompts from cache.

    Called from the CORE #7 hook in build_system_prompt().
    Uses in-memory cache with TTL to avoid DB calls per LLM request.
    Thread-safe via threading.Lock.
    """
    global _cached_text, _cache_timestamp

    now = time.monotonic()

    with _cache_lock:
        if now - _cache_timestamp < _CACHE_TTL_SECONDS:
            return _cached_text

    # Cache expired — refresh from DB
    try:
        from onyx.db.engine.sql_engine import get_session_with_current_tenant

        with get_session_with_current_tenant() as db_session:
            text = _assemble_active_prompts(db_session)

        with _cache_lock:
            _cached_text = text
            _cache_timestamp = time.monotonic()

        logger.debug(
            "Cache refreshed: %d chars",
            len(text),
        )
        return text
    except Exception:
        logger.error("Cache refresh failed, returning stale value", exc_info=True)
        with _cache_lock:
            return _cached_text


def invalidate_cache() -> None:
    """Force cache invalidation. Called after every CRUD operation."""
    global _cache_timestamp
    with _cache_lock:
        _cache_timestamp = 0.0
    logger.debug("Cache invalidated")


# --- CRUD functions ---


def get_all_prompts(db_session: Session) -> list[ExtCustomPrompt]:
    """All prompts (active + inactive), sorted by priority ASC."""
    return (
        db_session.query(ExtCustomPrompt)
        .order_by(ExtCustomPrompt.priority.asc(), ExtCustomPrompt.id.asc())
        .all()
    )


def get_prompt_by_id(
    db_session: Session, prompt_id: int
) -> ExtCustomPrompt | None:
    """Single prompt by ID, or None."""
    return db_session.get(ExtCustomPrompt, prompt_id)


def create_prompt(
    db_session: Session, data: "PromptCreate"
) -> ExtCustomPrompt:
    """Create a new prompt and invalidate cache."""
    row = ExtCustomPrompt(
        name=data.name,
        prompt_text=data.prompt_text,
        category=data.category,
        priority=data.priority,
        is_active=data.is_active,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    invalidate_cache()
    logger.info("Prompt created: id=%d, name='%s'", row.id, row.name)

    # Soft-limit warning
    _check_soft_limits(db_session)

    return row


def update_prompt(
    db_session: Session,
    prompt_id: int,
    data: "PromptUpdate",
) -> ExtCustomPrompt | None:
    """Update an existing prompt. Returns None if not found."""
    row = db_session.get(ExtCustomPrompt, prompt_id)
    if row is None:
        return None

    update_fields = data.model_dump(exclude_unset=True)
    if not update_fields:
        return row

    for field, value in update_fields.items():
        setattr(row, field, value)

    db_session.commit()
    db_session.refresh(row)
    invalidate_cache()
    logger.info("Prompt updated: id=%d", row.id)

    # Soft-limit warning
    _check_soft_limits(db_session)

    return row


def delete_prompt(db_session: Session, prompt_id: int) -> bool:
    """Delete a prompt. Returns False if not found."""
    row = db_session.get(ExtCustomPrompt, prompt_id)
    if row is None:
        return False

    db_session.delete(row)
    db_session.commit()
    invalidate_cache()
    logger.info("Prompt deleted: id=%d", prompt_id)
    return True


def get_assembled_prompt_text(db_session: Session) -> tuple[str, int, int]:
    """Assemble all active prompts and return (text, active_count, total_count)."""
    text = _assemble_active_prompts(db_session)
    active_count = (
        db_session.query(ExtCustomPrompt)
        .filter(ExtCustomPrompt.is_active.is_(True))
        .count()
    )
    total_count = db_session.query(ExtCustomPrompt).count()
    return text, active_count, total_count


# --- Internal helpers ---


def _assemble_active_prompts(db_session: Session) -> str:
    """Load active prompts from DB and join them with double newline."""
    rows = (
        db_session.query(ExtCustomPrompt)
        .filter(ExtCustomPrompt.is_active.is_(True))
        .order_by(ExtCustomPrompt.priority.asc(), ExtCustomPrompt.id.asc())
        .all()
    )
    if not rows:
        return ""
    return "\n\n".join(row.prompt_text.strip() for row in rows)


def _check_soft_limits(db_session: Session) -> None:
    """Log a warning if soft limits are exceeded."""
    active_count = (
        db_session.query(ExtCustomPrompt)
        .filter(ExtCustomPrompt.is_active.is_(True))
        .count()
    )
    if active_count > SOFT_LIMIT_ACTIVE_PROMPTS:
        logger.warning(
            "Soft limit exceeded: %d active prompts (limit: %d)",
            active_count,
            SOFT_LIMIT_ACTIVE_PROMPTS,
        )

    text = _assemble_active_prompts(db_session)
    if len(text) > SOFT_LIMIT_TOTAL_CHARS:
        logger.warning(
            "Soft limit exceeded: %d total chars (limit: %d)",
            len(text),
            SOFT_LIMIT_TOTAL_CHARS,
        )

"""Tests for ext-prompts (Custom System Prompts).

Tests schema validation, service CRUD, cache behavior, and edge cases.
"""

import time
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from ext.schemas.prompts import PromptCreate
from ext.schemas.prompts import PromptPreviewResponse
from ext.schemas.prompts import PromptResponse
from ext.schemas.prompts import PromptUpdate

# --- Schema Validation Tests ---


class TestPromptCreateSchema:
    def test_valid_all_fields(self) -> None:
        p = PromptCreate(
            name="Compliance",
            prompt_text="No financial advice.",
            category="compliance",
            priority=10,
            is_active=True,
        )
        assert p.name == "Compliance"
        assert p.category == "compliance"
        assert p.priority == 10

    def test_valid_defaults(self) -> None:
        p = PromptCreate(name="Test", prompt_text="Hello")
        assert p.category == "general"
        assert p.priority == 100
        assert p.is_active is True

    def test_invalid_name_empty(self) -> None:
        with pytest.raises(ValidationError):
            PromptCreate(name="", prompt_text="Hello")

    def test_invalid_name_too_long(self) -> None:
        with pytest.raises(ValidationError):
            PromptCreate(name="x" * 101, prompt_text="Hello")

    def test_invalid_text_empty(self) -> None:
        with pytest.raises(ValidationError):
            PromptCreate(name="Test", prompt_text="")

    def test_invalid_text_too_long(self) -> None:
        with pytest.raises(ValidationError):
            PromptCreate(name="Test", prompt_text="x" * 10_001)

    def test_invalid_category(self) -> None:
        with pytest.raises(ValidationError):
            PromptCreate(name="Test", prompt_text="Hello", category="invalid")

    def test_invalid_priority_negative(self) -> None:
        with pytest.raises(ValidationError):
            PromptCreate(name="Test", prompt_text="Hello", priority=-1)

    def test_invalid_priority_too_high(self) -> None:
        with pytest.raises(ValidationError):
            PromptCreate(name="Test", prompt_text="Hello", priority=1001)

    def test_all_categories_valid(self) -> None:
        for cat in ["compliance", "tone", "context", "instructions", "general"]:
            p = PromptCreate(name="Test", prompt_text="Hello", category=cat)
            assert p.category == cat


class TestPromptUpdateSchema:
    def test_partial_update_name_only(self) -> None:
        u = PromptUpdate(name="New Name")
        data = u.model_dump(exclude_unset=True)
        assert data == {"name": "New Name"}

    def test_partial_update_active_only(self) -> None:
        u = PromptUpdate(is_active=False)
        data = u.model_dump(exclude_unset=True)
        assert data == {"is_active": False}

    def test_all_none_by_default(self) -> None:
        u = PromptUpdate()
        assert u.name is None
        assert u.prompt_text is None
        assert u.category is None
        assert u.priority is None
        assert u.is_active is None

    def test_invalid_category(self) -> None:
        with pytest.raises(ValidationError):
            PromptUpdate(category="invalid")


class TestPromptResponseSchema:
    def test_valid_response(self) -> None:
        r = PromptResponse(
            id=1,
            name="Test",
            prompt_text="Hello",
            category="general",
            priority=100,
            is_active=True,
            created_at="2026-03-09T10:00:00Z",
            updated_at="2026-03-09T10:00:00Z",
        )
        assert r.id == 1


class TestPromptPreviewSchema:
    def test_valid_preview(self) -> None:
        p = PromptPreviewResponse(
            assembled_text="Hello\n\nWorld",
            active_count=2,
            total_count=3,
        )
        assert p.active_count == 2

    def test_empty_preview(self) -> None:
        p = PromptPreviewResponse(
            assembled_text="",
            active_count=0,
            total_count=0,
        )
        assert p.assembled_text == ""


# --- Service Tests (with mocked DB) ---


class TestPromptManagerService:
    """Tests for prompt_manager.py using mocked DB sessions."""

    def _make_mock_prompt(
        self,
        id: int = 1,
        name: str = "Test",
        prompt_text: str = "Hello",
        category: str = "general",
        priority: int = 100,
        is_active: bool = True,
    ) -> MagicMock:
        mock = MagicMock()
        mock.id = id
        mock.name = name
        mock.prompt_text = prompt_text
        mock.category = category
        mock.priority = priority
        mock.is_active = is_active
        mock.created_at = "2026-03-09T10:00:00Z"
        mock.updated_at = "2026-03-09T10:00:00Z"
        return mock

    def test_assemble_empty(self) -> None:
        """No active prompts → empty string."""
        from ext.services.prompt_manager import _assemble_active_prompts

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        result = _assemble_active_prompts(mock_session)
        assert result == ""

    def test_assemble_ordering(self) -> None:
        """Prompts assembled in priority order, joined by double newline."""
        from ext.services.prompt_manager import _assemble_active_prompts

        p1 = self._make_mock_prompt(id=1, prompt_text="First", priority=10)
        p2 = self._make_mock_prompt(id=2, prompt_text="Second", priority=20)
        p3 = self._make_mock_prompt(id=3, prompt_text="Third", priority=30)

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [p1, p2, p3]

        result = _assemble_active_prompts(mock_session)
        assert result == "First\n\nSecond\n\nThird"

    def test_assemble_strips_whitespace(self) -> None:
        """Prompt text is stripped before assembly."""
        from ext.services.prompt_manager import _assemble_active_prompts

        p1 = self._make_mock_prompt(prompt_text="  Hello  \n  ")

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [p1]

        result = _assemble_active_prompts(mock_session)
        assert result == "Hello"


# --- Cache Tests ---


class TestPromptCache:
    def setup_method(self) -> None:
        """Reset cache before each test."""
        from ext.services import prompt_manager

        prompt_manager._cached_text = ""
        prompt_manager._cache_timestamp = 0.0

    def test_invalidate_resets_timestamp(self) -> None:
        from ext.services import prompt_manager
        from ext.services.prompt_manager import invalidate_cache

        prompt_manager._cache_timestamp = time.monotonic()
        invalidate_cache()
        assert prompt_manager._cache_timestamp == 0.0

    def test_cache_returns_cached_value(self) -> None:
        """Warm cache returns value without DB query."""
        from ext.services import prompt_manager
        from ext.services.prompt_manager import get_cached_global_prompt

        # Prime the cache manually
        prompt_manager._cached_text = "cached text"
        prompt_manager._cache_timestamp = time.monotonic()

        result = get_cached_global_prompt()
        assert result == "cached text"

    @patch("ext.services.prompt_manager._CACHE_TTL_SECONDS", 0)
    @patch("ext.services.prompt_manager._assemble_active_prompts")
    def test_cache_refreshes_after_ttl(
        self, mock_assemble: MagicMock
    ) -> None:
        """Cache refreshes after TTL expires."""
        from ext.services.prompt_manager import get_cached_global_prompt

        mock_session = MagicMock()
        mock_assemble.return_value = "fresh text"

        with patch(
            "onyx.db.engine.sql_engine.get_session_with_current_tenant"
        ) as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            result = get_cached_global_prompt()
            assert result == "fresh text"
            mock_assemble.assert_called_once_with(mock_session)

    def test_cache_db_error_returns_stale(self) -> None:
        """DB error during refresh returns stale cached value."""
        from ext.services import prompt_manager
        from ext.services.prompt_manager import get_cached_global_prompt

        prompt_manager._cached_text = "stale value"
        prompt_manager._cache_timestamp = 0.0  # expired

        with patch(
            "onyx.db.engine.sql_engine.get_session_with_current_tenant",
            side_effect=RuntimeError("DB down"),
        ):
            result = get_cached_global_prompt()
            assert result == "stale value"


# --- Feature Flag Tests ---


class TestFeatureFlag:
    def test_flag_disabled_by_default(self) -> None:
        """EXT_CUSTOM_PROMPTS_ENABLED defaults to false."""
        import importlib
        import os

        with patch.dict(os.environ, {}, clear=True):
            import ext.config

            importlib.reload(ext.config)
            assert ext.config.EXT_CUSTOM_PROMPTS_ENABLED is False

    def test_flag_enabled_requires_ext_enabled(self) -> None:
        """EXT_CUSTOM_PROMPTS_ENABLED requires EXT_ENABLED=true."""
        import importlib
        import os

        with patch.dict(
            os.environ,
            {
                "EXT_ENABLED": "false",
                "EXT_CUSTOM_PROMPTS_ENABLED": "true",
            },
        ):
            import ext.config

            importlib.reload(ext.config)
            assert ext.config.EXT_CUSTOM_PROMPTS_ENABLED is False


# --- Edge Case Tests ---


class TestEdgeCases:
    def test_special_characters_in_prompt(self) -> None:
        """Unicode and special chars are valid."""
        p = PromptCreate(
            name="Umlaute",
            prompt_text="Verwende formelles Deutsch. Umlaut-Test: aou",
        )
        assert "Umlaut" in p.prompt_text

    def test_max_length_prompt(self) -> None:
        """10,000 char prompt is valid."""
        p = PromptCreate(name="Long", prompt_text="x" * 10_000)
        assert len(p.prompt_text) == 10_000

    def test_boundary_priority_values(self) -> None:
        """Priority 0 and 1000 are valid."""
        p0 = PromptCreate(name="Min", prompt_text="Hello", priority=0)
        p1000 = PromptCreate(name="Max", prompt_text="Hello", priority=1000)
        assert p0.priority == 0
        assert p1000.priority == 1000

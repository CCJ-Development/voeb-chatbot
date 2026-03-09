"""Unit tests for ext.services.token_tracker.

Uses unittest.mock to avoid DB/service dependencies.
Run: pytest backend/ext/tests/test_token_tracker.py -xv
"""

from datetime import datetime
from datetime import timedelta
from datetime import timezone
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException


# --- log_token_usage ---


class TestLogTokenUsage:
    @patch("ext.services.token_tracker.get_sqlalchemy_engine")
    def test_stores_usage(self, mock_engine: MagicMock) -> None:
        """Token usage should be inserted into the DB."""
        from ext.services.token_tracker import log_token_usage

        mock_session = MagicMock()
        mock_engine.return_value = MagicMock()

        with patch("ext.services.token_tracker.Session") as mock_cls:
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)

            log_token_usage(
                user_id=str(uuid4()),
                model_name="openai/gpt-oss-120b",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
            )

            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    @patch("ext.services.token_tracker.get_sqlalchemy_engine")
    def test_skips_zero_tokens(self, mock_engine: MagicMock) -> None:
        """Should skip INSERT when total_tokens <= 0."""
        from ext.services.token_tracker import log_token_usage

        log_token_usage(
            user_id=str(uuid4()),
            model_name="test",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
        )

        # Engine should never be called
        mock_engine.assert_not_called()

    @patch("ext.services.token_tracker.get_sqlalchemy_engine")
    def test_handles_null_user(self, mock_engine: MagicMock) -> None:
        """Should accept None user_id for system/background calls."""
        from ext.services.token_tracker import log_token_usage

        mock_session = MagicMock()
        mock_engine.return_value = MagicMock()

        with patch("ext.services.token_tracker.Session") as mock_cls:
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)

            log_token_usage(
                user_id=None,
                model_name="test",
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
            )

            mock_session.add.assert_called_once()
            added_row = mock_session.add.call_args[0][0]
            assert added_row.user_id is None

    @patch("ext.services.token_tracker.get_sqlalchemy_engine", side_effect=Exception("DB down"))
    def test_never_raises(self, mock_engine: MagicMock) -> None:
        """log_token_usage must NEVER raise — it's fire-and-forget."""
        from ext.services.token_tracker import log_token_usage

        # Should not raise
        log_token_usage(
            user_id=str(uuid4()),
            model_name="test",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )


# --- check_user_token_limit ---


class TestCheckUserTokenLimit:
    @patch("ext.services.token_tracker.get_sqlalchemy_engine")
    def test_passes_when_no_limit(self, mock_engine: MagicMock) -> None:
        """Should return normally when user has no limit configured."""
        from ext.services.token_tracker import check_user_token_limit

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        mock_engine.return_value = MagicMock()

        with patch("ext.services.token_tracker.Session") as mock_cls:
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)

            # Should not raise
            check_user_token_limit(str(uuid4()))

    @patch("ext.services.token_tracker.get_sqlalchemy_engine")
    def test_passes_when_under_budget(self, mock_engine: MagicMock) -> None:
        """Should return normally when usage is below budget."""
        from ext.services.token_tracker import check_user_token_limit

        mock_limit = MagicMock()
        mock_limit.token_budget = 500  # 500k tokens
        mock_limit.period_hours = 168
        mock_limit.enabled = True

        mock_session = MagicMock()
        # First call: get limit
        # Second call: get usage sum
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_limit
        mock_session.execute.return_value.scalar_one.return_value = 100_000  # Under 500k

        mock_engine.return_value = MagicMock()

        with patch("ext.services.token_tracker.Session") as mock_cls:
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)

            check_user_token_limit(str(uuid4()))

    @patch("ext.services.token_tracker.get_sqlalchemy_engine")
    def test_raises_429_when_over_budget(self, mock_engine: MagicMock) -> None:
        """Should raise HTTPException(429) when usage exceeds budget."""
        from ext.services.token_tracker import check_user_token_limit

        mock_limit = MagicMock()
        mock_limit.token_budget = 100  # 100k tokens
        mock_limit.period_hours = 168
        mock_limit.enabled = True

        mock_session = MagicMock()
        results = [
            MagicMock(),  # limit query
            MagicMock(),  # usage sum query
            MagicMock(),  # oldest entry query
        ]
        results[0].scalar_one_or_none.return_value = mock_limit
        results[1].scalar_one.return_value = 200_000  # Over 100k budget
        results[2].scalar_one.return_value = datetime.now(timezone.utc) - timedelta(hours=12)

        mock_session.execute.side_effect = results
        mock_engine.return_value = MagicMock()

        with patch("ext.services.token_tracker.Session") as mock_cls:
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)

            with pytest.raises(HTTPException) as exc_info:
                check_user_token_limit(str(uuid4()))

            assert exc_info.value.status_code == 429
            assert "Token-Limit erreicht" in exc_info.value.detail


# --- Pydantic schemas ---


class TestTokenSchemas:
    def test_user_limit_create_rejects_zero_budget(self) -> None:
        """token_budget must be > 0."""
        from ext.schemas.token import UserLimitCreate

        with pytest.raises(Exception):
            UserLimitCreate(
                user_id=uuid4(),
                token_budget=0,
                period_hours=168,
            )

    def test_user_limit_create_rejects_zero_period(self) -> None:
        """period_hours must be > 0."""
        from ext.schemas.token import UserLimitCreate

        with pytest.raises(Exception):
            UserLimitCreate(
                user_id=uuid4(),
                token_budget=500,
                period_hours=0,
            )

    def test_user_limit_create_valid(self) -> None:
        """Valid input should create successfully."""
        from ext.schemas.token import UserLimitCreate

        limit = UserLimitCreate(
            user_id=uuid4(),
            token_budget=500,
            period_hours=168,
        )
        assert limit.token_budget == 500
        assert limit.period_hours == 168
        assert limit.enabled is True

    def test_usage_summary_response(self) -> None:
        """UsageSummaryResponse should serialize correctly."""
        from ext.schemas.token import UsageSummaryResponse

        resp = UsageSummaryResponse(
            period_hours=168,
            total_prompt_tokens=1000,
            total_completion_tokens=500,
            total_tokens=1500,
            total_requests=10,
            by_user=[],
            by_model=[],
        )
        assert resp.total_tokens == 1500

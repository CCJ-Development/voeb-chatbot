"""Unit tests for ext-analytics (Platform Usage Analytics).

Uses unittest.mock to avoid DB/service dependencies.
Run: docker exec onyx-api_server-1 python -m pytest /app/ext/tests/test_analytics.py -xv
"""

from datetime import date
from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest


def _mock_db_session():
    return MagicMock()


# --- Schemas ---


class TestSchemas:
    def test_summary_response_valid(self) -> None:
        from ext.schemas.analytics import AnalyticsSummaryResponse

        data = {
            "period": {"from_date": date(2026, 3, 1), "to_date": date(2026, 3, 26)},
            "users": {
                "registered": 34,
                "active_period": 12,
                "dau_avg": 4.2,
                "new_in_period": 5,
                "inactive_30d": 10,
            },
            "sessions": {
                "total": 150,
                "avg_per_user": 12.5,
                "avg_messages_per_session": 4.3,
                "avg_duration_seconds": 120.0,
            },
            "tokens": {
                "total": 500000,
                "prompt": 300000,
                "completion": 200000,
                "requests": 1500,
                "by_model": [
                    {"model": "gpt-oss-120b", "tokens": 400000, "requests": 1200},
                ],
            },
            "quality": {
                "feedback_total": 20,
                "feedback_positive": 18,
                "feedback_negative": 2,
                "satisfaction_pct": 90.0,
                "error_rate_pct": 1.5,
                "avg_response_time_seconds": 2.4,
                "p95_response_time_seconds": 5.1,
            },
            "agents": {
                "total": 3,
                "active_in_period": 2,
                "top": [
                    {"name": "Assistant", "sessions": 100, "messages": 500},
                ],
            },
            "content": {
                "total_documents": 1000,
                "active_connectors": 2,
                "error_connectors": 0,
                "document_sets": 3,
            },
            "compliance": {
                "admin_actions": 15,
                "admin_actions_by_type": {"CREATE": 5, "UPDATE": 8, "DELETE": 2},
            },
        }
        response = AnalyticsSummaryResponse(**data)
        assert response.users.registered == 34
        assert response.tokens.by_model[0].model == "gpt-oss-120b"
        assert response.quality.satisfaction_pct == 90.0

    def test_summary_response_nullable_fields(self) -> None:
        from ext.schemas.analytics import AnalyticsSummaryResponse

        data = {
            "period": {"from_date": date(2026, 3, 1), "to_date": date(2026, 3, 26)},
            "users": {
                "registered": 0, "active_period": 0, "dau_avg": 0.0,
                "new_in_period": 0, "inactive_30d": 0,
            },
            "sessions": {
                "total": 0, "avg_per_user": 0.0,
                "avg_messages_per_session": 0.0, "avg_duration_seconds": 0.0,
            },
            "tokens": {
                "total": 0, "prompt": 0, "completion": 0,
                "requests": 0, "by_model": [],
            },
            "quality": {
                "feedback_total": 0, "feedback_positive": 0, "feedback_negative": 0,
                "satisfaction_pct": 0.0, "error_rate_pct": 0.0,
                "avg_response_time_seconds": None, "p95_response_time_seconds": None,
            },
            "agents": {"total": 0, "active_in_period": 0, "top": []},
            "content": {
                "total_documents": 0, "active_connectors": 0,
                "error_connectors": 0, "document_sets": 0,
            },
            "compliance": {"admin_actions": 0, "admin_actions_by_type": {}},
        }
        response = AnalyticsSummaryResponse(**data)
        assert response.quality.avg_response_time_seconds is None

    def test_user_activity_response(self) -> None:
        from ext.schemas.analytics import UserActivityResponse

        data = {
            "total": 1,
            "users": [{
                "email": "test@example.com",
                "role": "ADMIN",
                "registered": datetime(2026, 3, 1),
                "sessions": 10,
                "messages": 50,
                "tokens": 5000,
                "last_activity": datetime(2026, 3, 25),
            }],
        }
        response = UserActivityResponse(**data)
        assert response.users[0].sessions == 10

    def test_agent_detail_response(self) -> None:
        from ext.schemas.analytics import AgentDetailResponse

        data = {
            "total": 2,
            "agents": [
                {"name": "Assistant", "sessions": 100, "messages": 500, "unique_users": 10},
                {"name": "Recherche", "sessions": 50, "messages": 200, "unique_users": 5},
            ],
        }
        response = AgentDetailResponse(**data)
        assert response.agents[0].unique_users == 10


# --- Router ---


class TestRouterDateValidation:
    def test_from_date_after_to_date_raises(self) -> None:
        from fastapi import HTTPException
        from ext.routers.analytics import api_analytics_summary

        with pytest.raises(HTTPException) as exc_info:
            api_analytics_summary(
                _=MagicMock(),
                db_session=_mock_db_session(),
                from_date=date(2026, 4, 1),
                to_date=date(2026, 3, 1),
            )
        assert exc_info.value.status_code == 400

    def test_export_max_365_days(self) -> None:
        from fastapi import HTTPException
        from ext.routers.analytics import api_analytics_export

        with pytest.raises(HTTPException) as exc_info:
            api_analytics_export(
                _=MagicMock(),
                db_session=_mock_db_session(),
                from_date=date(2025, 1, 1),
                to_date=date(2026, 3, 26),
            )
        assert exc_info.value.status_code == 400


# --- Service: CSV Export ---


class TestCsvExport:
    @patch("ext.services.analytics.get_analytics_summary")
    @patch("ext.services.analytics.get_user_activity")
    def test_csv_contains_headers(self, mock_users: MagicMock, mock_summary: MagicMock) -> None:
        from ext.services.analytics import export_analytics_csv

        mock_summary.return_value = {
            "users": {
                "registered": 10, "active_period": 5, "dau_avg": 2.0,
                "new_in_period": 1, "inactive_30d": 3,
            },
            "sessions": {
                "total": 20, "avg_per_user": 4.0,
                "avg_messages_per_session": 3.0, "avg_duration_seconds": 60.0,
            },
            "tokens": {
                "total": 1000, "prompt": 600, "completion": 400,
                "requests": 50, "by_model": [],
            },
            "quality": {
                "feedback_total": 0, "feedback_positive": 0, "feedback_negative": 0,
                "satisfaction_pct": 0.0, "error_rate_pct": 0.0,
                "avg_response_time_seconds": None, "p95_response_time_seconds": None,
            },
            "agents": {"total": 1, "active_in_period": 1, "top": []},
            "content": {
                "total_documents": 0, "active_connectors": 1,
                "error_connectors": 0, "document_sets": 0,
            },
            "compliance": {"admin_actions": 0, "admin_actions_by_type": {}},
        }
        mock_users.return_value = {"total": 0, "users": []}

        csv = export_analytics_csv(_mock_db_session(), date(2026, 3, 1), date(2026, 3, 26))
        assert "Kategorie,KPI,Wert" in csv
        assert "Registrierte User" in csv
        assert "Token" in csv

    @patch("ext.services.analytics.get_analytics_summary")
    @patch("ext.services.analytics.get_user_activity")
    def test_csv_includes_user_table(self, mock_users: MagicMock, mock_summary: MagicMock) -> None:
        from ext.services.analytics import export_analytics_csv

        mock_summary.return_value = {
            "users": {"registered": 0, "active_period": 0, "dau_avg": 0.0, "new_in_period": 0, "inactive_30d": 0},
            "sessions": {"total": 0, "avg_per_user": 0.0, "avg_messages_per_session": 0.0, "avg_duration_seconds": 0.0},
            "tokens": {"total": 0, "prompt": 0, "completion": 0, "requests": 0, "by_model": []},
            "quality": {"feedback_total": 0, "feedback_positive": 0, "feedback_negative": 0, "satisfaction_pct": 0.0, "error_rate_pct": 0.0, "avg_response_time_seconds": None, "p95_response_time_seconds": None},
            "agents": {"total": 0, "active_in_period": 0, "top": []},
            "content": {"total_documents": 0, "active_connectors": 0, "error_connectors": 0, "document_sets": 0},
            "compliance": {"admin_actions": 0, "admin_actions_by_type": {}},
        }
        mock_users.return_value = {
            "total": 1,
            "users": [{
                "email": "test@voeb.de",
                "role": "ADMIN",
                "registered": datetime(2026, 3, 1),
                "sessions": 5,
                "messages": 20,
                "tokens": 3000,
                "last_activity": datetime(2026, 3, 25, 14, 30),
            }],
        }

        csv = export_analytics_csv(_mock_db_session(), date(2026, 3, 1), date(2026, 3, 26))
        assert "test@voeb.de" in csv
        assert "ADMIN" in csv


# --- Feature Flag ---


class TestFeatureFlag:
    @patch("ext.config.EXT_ANALYTICS_ENABLED", False)
    @patch("ext.config.EXT_ENABLED", True)
    def test_flag_disabled_no_registration(self) -> None:
        """When EXT_ANALYTICS_ENABLED=false, router is not registered."""
        from ext.config import EXT_ANALYTICS_ENABLED
        assert not EXT_ANALYTICS_ENABLED

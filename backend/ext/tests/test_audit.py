"""Unit tests for ext.services.audit (Audit-Logging).

Uses unittest.mock to avoid DB/service dependencies.
Run: docker exec onyx-api_server-1 python -m pytest /app/ext/tests/test_audit.py -xv
"""

from datetime import datetime
from datetime import timedelta
from datetime import timezone
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import uuid4



def _mock_user(email: str = "admin@voeb-service.de", role_value: str = "admin"):
    user = MagicMock()
    user.id = uuid4()
    user.email = email
    user.role = MagicMock()
    user.role.value = role_value
    return user


def _mock_db_session():
    return MagicMock()


# --- log_audit_event ---


class TestLogAuditEvent:
    @patch("ext.config.EXT_AUDIT_ENABLED", True)
    def test_creates_entry(self) -> None:
        """Event wird in DB geschrieben."""
        from ext.services.audit import log_audit_event

        db = _mock_db_session()
        user = _mock_user()

        log_audit_event(
            db, user, "CREATE", "GROUP",
            resource_id="5", resource_name="Kreditabteilung",
        )

        db.add.assert_called_once()
        db.flush.assert_called_once()

    @patch("ext.config.EXT_AUDIT_ENABLED", True)
    def test_with_audit_context(self) -> None:
        """IP + User-Agent aus audit_ctx gespeichert."""
        from ext.services.audit import log_audit_event

        db = _mock_db_session()
        user = _mock_user()
        ctx = {"ip_address": "188.34.92.162", "user_agent": "Mozilla/5.0"}

        log_audit_event(
            db, user, "UPDATE", "BRANDING",
            audit_ctx=ctx,
        )

        call_args = db.add.call_args
        entry = call_args[0][0]
        assert entry.ip_address == "188.34.92.162"
        assert entry.user_agent == "Mozilla/5.0"

    @patch("ext.config.EXT_AUDIT_ENABLED", True)
    def test_without_actor(self) -> None:
        """System-Events (actor=None)."""
        from ext.services.audit import log_audit_event

        db = _mock_db_session()
        log_audit_event(db, None, "RESYNC", "DOC_ACCESS")

        call_args = db.add.call_args
        entry = call_args[0][0]
        assert entry.actor_email is None
        assert entry.actor_role is None

    @patch("ext.config.EXT_AUDIT_ENABLED", True)
    def test_never_raises(self) -> None:
        """Exception in DB → kein Crash."""
        from ext.services.audit import log_audit_event

        db = _mock_db_session()
        db.add.side_effect = Exception("DB down")

        # Sollte NICHT raisen
        log_audit_event(db, _mock_user(), "CREATE", "GROUP")

    @patch("ext.config.EXT_AUDIT_ENABLED", False)
    def test_noop_when_disabled(self) -> None:
        """Flag=false → kein DB-Write."""
        from ext.services.audit import log_audit_event

        db = _mock_db_session()
        log_audit_event(db, _mock_user(), "CREATE", "GROUP")

        db.add.assert_not_called()


# --- query_audit_events ---


class TestQueryAuditEvents:
    @patch("ext.services.audit.select")
    def test_with_filters(self, mock_select) -> None:
        """Filter nach actor, action, resource_type."""
        from ext.services.audit import query_audit_events

        db = _mock_db_session()
        db.execute.return_value.scalar.return_value = 0
        db.execute.return_value.scalars.return_value.all.return_value = []

        result = query_audit_events(
            db,
            actor_email="admin@voeb-service.de",
            action="CREATE",
            resource_type="GROUP",
        )

        assert "events" in result
        assert "total" in result
        assert result["page"] == 1
        assert result["page_size"] == 50

    @patch("ext.services.audit.select")
    def test_pagination(self, mock_select) -> None:
        """Page/PageSize korrekt."""
        from ext.services.audit import query_audit_events

        db = _mock_db_session()
        db.execute.return_value.scalar.return_value = 100
        db.execute.return_value.scalars.return_value.all.return_value = []

        result = query_audit_events(db, page=3, page_size=20)

        assert result["page"] == 3
        assert result["page_size"] == 20
        assert result["total"] == 100


# --- export_audit_csv ---


class TestExportCSV:
    @patch("ext.services.audit.select")
    def test_csv_format(self, mock_select) -> None:
        """CSV hat Header-Zeile."""
        from ext.services.audit import export_audit_csv

        db = _mock_db_session()
        db.execute.return_value.scalars.return_value.all.return_value = []

        now = datetime.now(timezone.utc)
        csv = export_audit_csv(db, now - timedelta(days=7), now)

        assert "timestamp" in csv
        assert "actor_email" in csv
        assert "action" in csv


# --- anonymize_old_ips ---


class TestAnonymizeOldIPs:
    def test_anonymize_function_exists(self) -> None:
        """anonymize_old_ips ist importierbar und aufrufbar."""
        from ext.services.audit import anonymize_old_ips

        assert callable(anonymize_old_ips)

    def test_anonymize_signature(self) -> None:
        """Funktion akzeptiert db_session und gibt int zurueck."""
        import inspect
        from ext.services.audit import anonymize_old_ips

        sig = inspect.signature(anonymize_old_ips)
        assert "db_session" in sig.parameters


class TestAuditIPAnonymizeTask:
    def test_task_importable(self) -> None:
        """Celery-Task ist importierbar."""
        from ext.tasks.audit_ip_anonymize import ext_audit_ip_anonymize_task

        assert callable(ext_audit_ip_anonymize_task)

    def test_task_name(self) -> None:
        """Task hat den erwarteten Celery-Namen."""
        from ext.tasks.audit_ip_anonymize import ext_audit_ip_anonymize_task

        assert ext_audit_ip_anonymize_task.name == "ext_audit_ip_anonymize"

    def test_task_interval_is_24h(self) -> None:
        """Self-Scheduling Intervall ist 24 Stunden."""
        from ext.tasks.audit_ip_anonymize import _ANONYMIZE_INTERVAL

        assert _ANONYMIZE_INTERVAL == 86400


# --- get_audit_context ---


class TestGetAuditContext:
    def test_extracts_forwarded_ip(self) -> None:
        """X-Forwarded-For Header → erste IP."""
        from ext.routers.audit import get_audit_context

        request = MagicMock()
        request.headers = {
            "x-forwarded-for": "188.34.92.162, 10.0.0.1",
            "user-agent": "Mozilla/5.0",
        }
        request.client = MagicMock()
        request.client.host = "10.0.0.1"

        ctx = get_audit_context(request)
        assert ctx["ip_address"] == "188.34.92.162"
        assert ctx["user_agent"] == "Mozilla/5.0"

    def test_fallback_to_client_host(self) -> None:
        """Kein X-Forwarded-For → client.host."""
        from ext.routers.audit import get_audit_context

        request = MagicMock()
        request.headers = {"user-agent": "curl/8.0"}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        ctx = get_audit_context(request)
        assert ctx["ip_address"] == "127.0.0.1"

    def test_empty_audit_log(self) -> None:
        """Keine Events → leere Response."""
        from ext.services.audit import query_audit_events

        db = _mock_db_session()
        db.execute.return_value.scalar.return_value = 0
        db.execute.return_value.scalars.return_value.all.return_value = []

        result = query_audit_events(db)
        assert result["events"] == []
        assert result["total"] == 0

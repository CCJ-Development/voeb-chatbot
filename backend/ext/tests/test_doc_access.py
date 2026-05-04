"""Unit tests for ext.services.doc_access (Document Access Control).

Uses unittest.mock to avoid DB/service dependencies.
Run: pytest backend/ext/tests/test_doc_access.py -xv
"""

from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import uuid4

# --- Helper: Mock Objects ---


def _mock_user(email: str = "alice@voeb-service.de", user_id=None):
    """Create a mock User."""
    user = MagicMock()
    user.id = user_id or uuid4()
    user.email = email
    user.is_anonymous = False
    return user


def _mock_anonymous_user():
    """Create a mock anonymous User."""
    user = MagicMock()
    user.is_anonymous = True
    return user


def _mock_db_session():
    """Create a mock DB session."""
    return MagicMock()


# --- get_group_acls_for_user ---


class TestGetGroupAclsForUser:
    @patch("ext.services.doc_access.User__UserGroup")
    @patch("ext.services.doc_access.UserGroup")
    def test_user_in_two_groups(self, mock_ug, mock_uug) -> None:
        """User in 2 Gruppen → 2 ACL-Strings."""
        from ext.services.doc_access import get_group_acls_for_user

        db = _mock_db_session()
        db.query.return_value.join.return_value.filter.return_value.all.return_value = [
            ("Kreditabteilung",),
            ("IT",),
        ]

        user = _mock_user()
        result = get_group_acls_for_user(user, db)

        assert len(result) == 2
        assert "group:Kreditabteilung" in result
        assert "group:IT" in result

    @patch("ext.services.doc_access.User__UserGroup")
    @patch("ext.services.doc_access.UserGroup")
    def test_user_in_no_groups(self, mock_ug, mock_uug) -> None:
        """User in 0 Gruppen → leeres Set."""
        from ext.services.doc_access import get_group_acls_for_user

        db = _mock_db_session()
        db.query.return_value.join.return_value.filter.return_value.all.return_value = (
            []
        )

        user = _mock_user()
        result = get_group_acls_for_user(user, db)

        assert result == set()

    @patch("ext.services.doc_access.User__UserGroup")
    @patch("ext.services.doc_access.UserGroup")
    def test_acl_prefix_format(self, mock_ug, mock_uug) -> None:
        """ACL-Strings muessen mit 'group:' prefixed sein."""
        from ext.services.doc_access import get_group_acls_for_user

        db = _mock_db_session()
        db.query.return_value.join.return_value.filter.return_value.all.return_value = [
            ("TestGruppe",),
        ]

        user = _mock_user()
        result = get_group_acls_for_user(user, db)

        acl = result.pop()
        assert acl.startswith("group:")


# --- get_user_groups_for_document ---


class TestGetUserGroupsForDocument:
    @patch("ext.services.doc_access.DocumentByConnectorCredentialPair")
    @patch("ext.services.doc_access.ConnectorCredentialPair")
    @patch("ext.services.doc_access.UserGroup__ConnectorCredentialPair")
    @patch("ext.services.doc_access.UserGroup")
    def test_document_in_one_group(self, mock_ug, mock_ugcc, mock_cc, mock_dcc) -> None:
        """Dokument via CC-Pair in Gruppe → Gruppenname."""
        from ext.services.doc_access import get_user_groups_for_document

        db = _mock_db_session()
        db.query.return_value.join.return_value.join.return_value.join.return_value.filter.return_value.distinct.return_value.all.return_value = [
            ("Kreditabteilung",),
        ]

        result = get_user_groups_for_document("doc-123", db)

        assert result == ["Kreditabteilung"]

    @patch("ext.services.doc_access.DocumentByConnectorCredentialPair")
    @patch("ext.services.doc_access.ConnectorCredentialPair")
    @patch("ext.services.doc_access.UserGroup__ConnectorCredentialPair")
    @patch("ext.services.doc_access.UserGroup")
    def test_document_no_groups(self, mock_ug, mock_ugcc, mock_cc, mock_dcc) -> None:
        """Dokument ohne Gruppen-Zuordnung → leere Liste."""
        from ext.services.doc_access import get_user_groups_for_document

        db = _mock_db_session()
        db.query.return_value.join.return_value.join.return_value.join.return_value.filter.return_value.distinct.return_value.all.return_value = (
            []
        )

        result = get_user_groups_for_document("doc-456", db)

        assert result == []

    @patch("ext.services.doc_access.DocumentByConnectorCredentialPair")
    @patch("ext.services.doc_access.ConnectorCredentialPair")
    @patch("ext.services.doc_access.UserGroup__ConnectorCredentialPair")
    @patch("ext.services.doc_access.UserGroup")
    def test_document_in_multiple_groups(self, mock_ug, mock_ugcc, mock_cc, mock_dcc) -> None:
        """Dokument in 2 Gruppen → beide Gruppennamen."""
        from ext.services.doc_access import get_user_groups_for_document

        db = _mock_db_session()
        db.query.return_value.join.return_value.join.return_value.join.return_value.filter.return_value.distinct.return_value.all.return_value = [
            ("Kreditabteilung",),
            ("Compliance",),
        ]

        result = get_user_groups_for_document("doc-789", db)

        assert len(result) == 2
        assert "Kreditabteilung" in result
        assert "Compliance" in result


# --- trigger_full_resync ---


class TestTriggerFullResync:
    @patch("ext.services.doc_access.DocumentByConnectorCredentialPair")
    @patch("ext.services.doc_access.ConnectorCredentialPair")
    @patch("ext.services.doc_access.UserGroup__ConnectorCredentialPair")
    @patch("ext.services.doc_access.UserGroup")
    def test_marks_all_groups(self, mock_ug, mock_ugcc, mock_cc, mock_dcc) -> None:
        """Alle Gruppen werden auf is_up_to_date=False markiert."""
        from ext.services.doc_access import trigger_full_resync

        db = _mock_db_session()
        # Erster Query-Chain: update (groups_queued)
        db.query.return_value.filter.return_value.update.return_value = 5
        # Zweiter Query-Chain: scalar (estimated_documents) — deep mock chain
        # trigger_full_resync macht: db.query(func.count(...)).join().join().scalar()
        # Nach commit() wird ein neuer query() gemacht
        db.query.return_value.join.return_value.join.return_value.scalar.return_value = 601

        result = trigger_full_resync(db)

        assert result["groups_queued"] == 5
        # estimated_documents kommt aus einem separaten Query nach commit
        assert "estimated_documents" in result
        db.commit.assert_called_once()


# --- get_sync_status ---


class TestGetSyncStatus:
    @patch("ext.services.doc_access.UserGroup")
    def test_all_synced(self, mock_ug) -> None:
        """Alle Gruppen synced → pending=0."""
        from ext.services.doc_access import get_sync_status

        db = _mock_db_session()
        # First call: total count
        # Second call: pending count
        db.query.return_value.scalar.return_value = 5
        db.query.return_value.filter.return_value.filter.return_value.scalar.return_value = 0

        result = get_sync_status(db)

        assert result["enabled"] is True
        assert result["groups_total"] == 5
        assert result["groups_pending"] == 0
        assert result["groups_synced"] == 5


# --- Feature Flag Tests ---


class TestFeatureFlag:
    def test_celery_task_noop_when_disabled(self) -> None:
        """Celery-Task macht nichts wenn Flag=false."""
        with patch("ext.config.EXT_DOC_ACCESS_ENABLED", False):
            from ext.tasks.doc_access_sync import ext_doc_access_sync_task

            # Sollte None returnen (early exit)
            result = ext_doc_access_sync_task()
            assert result is None


# --- Edge Cases ---


class TestEdgeCases:
    @patch("ext.services.doc_access.User__UserGroup")
    @patch("ext.services.doc_access.UserGroup")
    def test_user_in_many_groups(self, mock_ug, mock_uug) -> None:
        """User in 10 Gruppen → alle 10 als ACL."""
        from ext.services.doc_access import get_group_acls_for_user

        db = _mock_db_session()
        db.query.return_value.join.return_value.filter.return_value.all.return_value = [
            (f"Gruppe_{i}",) for i in range(10)
        ]

        user = _mock_user()
        result = get_group_acls_for_user(user, db)

        assert len(result) == 10

    def test_sync_status_empty_db(self) -> None:
        """Keine Gruppen → 0/0/0."""
        from ext.services.doc_access import get_sync_status

        db = _mock_db_session()
        db.query.return_value.scalar.return_value = 0
        db.query.return_value.filter.return_value.filter.return_value.scalar.return_value = 0

        result = get_sync_status(db)

        assert result["groups_total"] == 0
        assert result["groups_synced"] == 0
        assert result["groups_pending"] == 0

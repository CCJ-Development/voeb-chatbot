"""Unit tests for ext.services.rbac (Group Management).

Uses unittest.mock to avoid DB/service dependencies.
Run: pytest backend/ext/tests/test_rbac.py -xv
"""

from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

# --- Helper: Mock User ---


def _mock_user(role: str = "admin", user_id=None):
    """Create a mock User with the given role."""
    from onyx.auth.schemas import UserRole

    user = MagicMock()
    user.id = user_id or uuid4()
    user.email = f"{role}@voeb-service.de"
    user.role = getattr(UserRole, role.upper())
    return user


def _mock_db_session():
    """Create a mock DB session with common query patterns."""
    session = MagicMock()
    # Make session.get return None by default
    session.get.return_value = None
    return session


# --- validate_curator_for_group ---


class TestValidateCuratorForGroup:
    def test_admin_always_passes(self) -> None:
        """Admin should pass validation for any group."""
        from ext.services.rbac import validate_curator_for_group

        user = _mock_user("admin")
        db = _mock_db_session()

        # Should not raise
        validate_curator_for_group(db, user, user_group_id=999)

    def test_curator_passes_for_own_group(self) -> None:
        """Curator with is_curator=True for the group should pass."""
        from ext.services.rbac import validate_curator_for_group

        user = _mock_user("curator")
        db = _mock_db_session()

        # Mock: membership found with is_curator=True
        mock_membership = MagicMock()
        mock_membership.is_curator = True
        db.execute.return_value.scalar_one_or_none.return_value = mock_membership

        validate_curator_for_group(db, user, user_group_id=1)

    def test_curator_blocked_for_other_group(self) -> None:
        """Curator without is_curator for the group should get 403."""
        from ext.services.rbac import validate_curator_for_group

        user = _mock_user("curator")
        db = _mock_db_session()

        # Mock: no membership found
        db.execute.return_value.scalar_one_or_none.return_value = None

        with pytest.raises(HTTPException) as exc:
            validate_curator_for_group(db, user, user_group_id=1)
        assert exc.value.status_code == 403

    def test_global_curator_passes_as_member(self) -> None:
        """Global curator who is member of group should pass."""
        from ext.services.rbac import validate_curator_for_group

        user = _mock_user("global_curator")
        db = _mock_db_session()

        mock_membership = MagicMock()
        db.execute.return_value.scalar_one_or_none.return_value = mock_membership

        validate_curator_for_group(db, user, user_group_id=1)

    def test_global_curator_blocked_if_not_member(self) -> None:
        """Global curator who is NOT member of group should get 403."""
        from ext.services.rbac import validate_curator_for_group

        user = _mock_user("global_curator")
        db = _mock_db_session()

        db.execute.return_value.scalar_one_or_none.return_value = None

        with pytest.raises(HTTPException) as exc:
            validate_curator_for_group(db, user, user_group_id=1)
        assert exc.value.status_code == 403

    def test_basic_user_always_blocked(self) -> None:
        """Basic user should always get 403."""
        from ext.services.rbac import validate_curator_for_group

        user = _mock_user("basic")
        db = _mock_db_session()

        with pytest.raises(HTTPException) as exc:
            validate_curator_for_group(db, user, user_group_id=1)
        assert exc.value.status_code == 403


# --- _check_and_demote_curator ---


class TestCheckAndDemoteCurator:
    def test_demotes_when_no_curator_groups_left(self) -> None:
        """Curator with 0 remaining curator groups should be demoted to BASIC."""
        from ext.services.rbac import _check_and_demote_curator
        from onyx.auth.schemas import UserRole

        uid = uuid4()
        user = _mock_user("curator", user_id=uid)
        db = _mock_db_session()
        db.get.return_value = user

        # Mock: 0 remaining curator memberships
        db.execute.return_value.scalar_one.return_value = 0

        _check_and_demote_curator(db, uid)

        assert user.role == UserRole.BASIC

    def test_no_demotion_when_still_curator_somewhere(self) -> None:
        """Curator with remaining curator groups should NOT be demoted."""
        from ext.services.rbac import _check_and_demote_curator
        from onyx.auth.schemas import UserRole

        uid = uuid4()
        user = _mock_user("curator", user_id=uid)
        db = _mock_db_session()
        db.get.return_value = user

        # Mock: 1 remaining curator membership
        db.execute.return_value.scalar_one.return_value = 1

        _check_and_demote_curator(db, uid)

        assert user.role == UserRole.CURATOR

    def test_admin_never_demoted(self) -> None:
        """Admin should never be demoted regardless of curator status."""
        from ext.services.rbac import _check_and_demote_curator
        from onyx.auth.schemas import UserRole

        uid = uuid4()
        user = _mock_user("admin", user_id=uid)
        db = _mock_db_session()
        db.get.return_value = user

        _check_and_demote_curator(db, uid)

        # Should not even query for curator count
        assert user.role == UserRole.ADMIN

    def test_global_curator_never_demoted(self) -> None:
        """Global curator should never be demoted."""
        from ext.services.rbac import _check_and_demote_curator
        from onyx.auth.schemas import UserRole

        uid = uuid4()
        user = _mock_user("global_curator", user_id=uid)
        db = _mock_db_session()
        db.get.return_value = user

        _check_and_demote_curator(db, uid)

        assert user.role == UserRole.GLOBAL_CURATOR

    def test_nonexistent_user_no_error(self) -> None:
        """Should not raise if user not found."""
        from ext.services.rbac import _check_and_demote_curator

        db = _mock_db_session()
        db.get.return_value = None

        # Should not raise
        _check_and_demote_curator(db, uuid4())


# --- create_user_group ---


class TestCreateUserGroup:
    def test_creates_group(self) -> None:
        """Should create a group with correct name."""
        from ext.services.rbac import create_user_group

        db = _mock_db_session()

        # Mock: no existing group with same name
        db.execute.return_value.scalar_one_or_none.return_value = None
        # Mock: flush gives group.id
        db.add = MagicMock()
        db.flush = MagicMock()

        # We need to mock the _build_user_group_response call
        with patch("ext.services.rbac._build_user_group_response") as mock_build:
            mock_build.return_value = {"id": 1, "name": "Test"}
            result = create_user_group(db, name="Test", user_ids=[], cc_pair_ids=[])

        assert result["name"] == "Test"
        db.commit.assert_called_once()

    def test_rejects_duplicate_name(self) -> None:
        """Should raise 409 when group name already exists."""
        from ext.services.rbac import create_user_group

        db = _mock_db_session()

        # Mock: existing group found
        existing = MagicMock()
        existing.name = "Existing"
        db.execute.return_value.scalar_one_or_none.return_value = existing

        with pytest.raises(HTTPException) as exc:
            create_user_group(db, name="Existing", user_ids=[], cc_pair_ids=[])
        assert exc.value.status_code == 409


# --- fetch_user_group_by_id ---


class TestFetchUserGroupById:
    def test_returns_group(self) -> None:
        """Should return group when found."""
        from ext.services.rbac import fetch_user_group_by_id

        db = _mock_db_session()
        group = MagicMock()
        group.is_up_for_deletion = False
        db.get.return_value = group

        result = fetch_user_group_by_id(db, 1)
        assert result == group

    def test_raises_404_when_not_found(self) -> None:
        """Should raise 404 when group doesn't exist."""
        from ext.services.rbac import fetch_user_group_by_id

        db = _mock_db_session()
        db.get.return_value = None

        with pytest.raises(HTTPException) as exc:
            fetch_user_group_by_id(db, 999)
        assert exc.value.status_code == 404

    def test_raises_404_when_marked_for_deletion(self) -> None:
        """Should raise 404 when group is marked for deletion."""
        from ext.services.rbac import fetch_user_group_by_id

        db = _mock_db_session()
        group = MagicMock()
        group.is_up_for_deletion = True
        db.get.return_value = group

        with pytest.raises(HTTPException) as exc:
            fetch_user_group_by_id(db, 1)
        assert exc.value.status_code == 404


# --- set_curator_status ---


class TestSetCuratorStatus:
    @patch("ext.services.rbac._check_and_demote_curator")
    @patch("ext.services.rbac.fetch_user_group_by_id")
    def test_sets_curator_and_promotes_user(self, mock_fetch, mock_demote) -> None:
        """Setting is_curator=True should also set user.role to CURATOR."""
        from ext.services.rbac import set_curator_status
        from onyx.auth.schemas import UserRole

        db = _mock_db_session()
        uid = uuid4()

        # Mock group exists
        mock_fetch.return_value = MagicMock(name="TestGroup")

        # Mock membership found
        membership = MagicMock()
        db.execute.return_value.scalar_one_or_none.return_value = membership

        # Mock user is BASIC
        user = _mock_user("basic", user_id=uid)
        db.get.return_value = user

        set_curator_status(db, user_group_id=1, user_id=uid, is_curator=True)

        assert membership.is_curator is True
        assert user.role == UserRole.CURATOR

    @patch("ext.services.rbac._check_and_demote_curator")
    @patch("ext.services.rbac.fetch_user_group_by_id")
    def test_rejects_non_member(self, mock_fetch, mock_demote) -> None:
        """Should raise 400 when user is not a member of the group."""
        from ext.services.rbac import set_curator_status

        db = _mock_db_session()
        mock_fetch.return_value = MagicMock()

        # Mock: no membership
        db.execute.return_value.scalar_one_or_none.return_value = None

        with pytest.raises(HTTPException) as exc:
            set_curator_status(db, user_group_id=1, user_id=uuid4(), is_curator=True)
        assert exc.value.status_code == 400


# --- delete_user_group ---


class TestDeleteUserGroup:
    @patch("ext.services.rbac._check_and_demote_curator")
    @patch("ext.services.rbac.fetch_user_group_by_id")
    def test_deletes_group_and_cascades(self, mock_fetch, mock_demote) -> None:
        """Should delete group and all M2M associations."""
        from ext.services.rbac import delete_user_group

        db = _mock_db_session()
        group = MagicMock()
        group.name = "ToDelete"
        mock_fetch.return_value = group

        # Mock: no curators (empty list)
        db.execute.return_value.scalars.return_value.all.return_value = []

        delete_user_group(db, user_group_id=1)

        db.delete.assert_called_once_with(group)
        db.commit.assert_called()
        # 7 M2M deletes + 1 curator query = 8 execute calls
        assert db.execute.call_count >= 7

    @patch("ext.services.rbac._check_and_demote_curator")
    @patch("ext.services.rbac.fetch_user_group_by_id")
    def test_demotes_orphaned_curators(self, mock_fetch, mock_demote) -> None:
        """Should check curator demotion for former curators."""
        from ext.services.rbac import delete_user_group

        db = _mock_db_session()
        group = MagicMock()
        group.name = "ToDelete"
        mock_fetch.return_value = group

        curator_id = uuid4()
        curator_membership = MagicMock()
        curator_membership.user_id = curator_id

        # First execute call returns curator memberships, rest return empty
        # Code: .execute(...).scalars().unique().all()
        db.execute.return_value.scalars.return_value.unique.return_value.all.return_value = [
            curator_membership
        ]

        delete_user_group(db, user_group_id=1)

        mock_demote.assert_called_once_with(db, curator_id)


# --- fetch_all_user_groups ---


class TestFetchAllUserGroups:
    @patch("ext.services.rbac._build_user_group_response")
    def test_admin_sees_all_groups(self, mock_build) -> None:
        """Admin should see all non-deleted groups."""
        from ext.services.rbac import fetch_all_user_groups

        db = _mock_db_session()
        user = _mock_user("admin")

        group1 = MagicMock()
        group2 = MagicMock()
        # Code: .execute(...).scalars().unique().all()
        db.execute.return_value.scalars.return_value.unique.return_value.all.return_value = [
            group1,
            group2,
        ]

        mock_build.side_effect = [{"id": 1}, {"id": 2}]

        result = fetch_all_user_groups(db, user)
        assert len(result) == 2

    def test_basic_user_sees_nothing(self) -> None:
        """Basic user should see no groups."""
        from ext.services.rbac import fetch_all_user_groups

        db = _mock_db_session()
        user = _mock_user("basic")

        result = fetch_all_user_groups(db, user)
        assert result == []


# --- fetch_minimal_user_groups ---


class TestFetchMinimalUserGroups:
    def test_admin_gets_all(self) -> None:
        """Admin should see all groups (id + name only)."""
        from ext.services.rbac import fetch_minimal_user_groups

        db = _mock_db_session()
        user = _mock_user("admin")

        row1 = MagicMock()
        row1.id = 1
        row1.name = "Group1"
        row2 = MagicMock()
        row2.id = 2
        row2.name = "Group2"
        db.execute.return_value.all.return_value = [row1, row2]

        result = fetch_minimal_user_groups(db, user)
        assert len(result) == 2
        assert result[0]["name"] == "Group1"

    def test_basic_user_gets_own_groups(self) -> None:
        """Non-admin should only see groups they belong to."""
        from ext.services.rbac import fetch_minimal_user_groups

        db = _mock_db_session()
        user = _mock_user("basic")

        row = MagicMock()
        row.id = 1
        row.name = "MyGroup"
        db.execute.return_value.all.return_value = [row]

        result = fetch_minimal_user_groups(db, user)
        assert len(result) == 1
        assert result[0]["name"] == "MyGroup"


# --- Schema Validation ---


class TestSchemas:
    def test_user_group_create_valid(self) -> None:
        """Valid create request should pass."""
        from ext.schemas.rbac import UserGroupCreate

        req = UserGroupCreate(name="Test Group")
        assert req.name == "Test Group"
        assert req.user_ids == []
        assert req.cc_pair_ids == []

    def test_user_group_create_empty_name_fails(self) -> None:
        """Empty name should fail validation."""
        from pydantic import ValidationError

        from ext.schemas.rbac import UserGroupCreate

        with pytest.raises(ValidationError):
            UserGroupCreate(name="")

    def test_user_group_create_long_name_fails(self) -> None:
        """Name > 255 chars should fail validation."""
        from pydantic import ValidationError

        from ext.schemas.rbac import UserGroupCreate

        with pytest.raises(ValidationError):
            UserGroupCreate(name="x" * 256)

    def test_set_curator_request(self) -> None:
        """SetCuratorRequest should accept UUID + bool."""
        from ext.schemas.rbac import SetCuratorRequest

        uid = uuid4()
        req = SetCuratorRequest(user_id=uid, is_curator=True)
        assert req.user_id == uid
        assert req.is_curator is True

    def test_add_users_request_requires_at_least_one(self) -> None:
        """AddUsersRequest should require at least 1 user_id."""
        from pydantic import ValidationError

        from ext.schemas.rbac import AddUsersRequest

        with pytest.raises(ValidationError):
            AddUsersRequest(user_ids=[])

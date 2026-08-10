import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from modules.admin import admin_router
from modules.admin.admin_repo import AdminEmailConflict, AdminStateConflict
from modules.admin.admin_repo import AdminRepository
from modules.admin.admin_schemas import AdminBootstrapIn
from models.User import User
from models.user_credit import UserCredit
from modules.admin.admin_action_log import AdminActionLog


class FakeAdminRepository:
    initialization_required = True
    bootstrap_error = None
    calls = []

    def __init__(self, session):
        self.session = session

    async def bootstrap_status(self):
        return self.initialization_required

    async def bootstrap_admin(self, email, username, password):
        type(self).calls.append((email, username, password))
        if self.bootstrap_error:
            raise self.bootstrap_error
        return SimpleNamespace(id=9, email=email, username=username)


class AdminBootstrapTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FakeAdminRepository.initialization_required = True
        FakeAdminRepository.bootstrap_error = None
        FakeAdminRepository.calls = []
        self.payload = AdminBootstrapIn(
            email="owner@example.com",
            username="owner",
            password="safe-password",
            bootstrap_secret="deployment-secret-with-32-characters",
        )

    async def test_status_reports_required_and_enabled(self):
        with (
            patch.object(admin_router, "AdminRepository", FakeAdminRepository),
            patch.object(admin_router.settings, "ADMIN_BOOTSTRAP_SECRET", "deployment-secret-with-32-characters"),
        ):
            result = await admin_router.bootstrap_status(session=object())
        self.assertEqual(
            {"initialization_required": True, "bootstrap_enabled": True}, result
        )

    async def test_unconfigured_secret_disables_bootstrap(self):
        with patch.object(admin_router.settings, "ADMIN_BOOTSTRAP_SECRET", ""):
            with self.assertRaises(HTTPException) as context:
                await admin_router.bootstrap_admin(self.payload, session=object())
        self.assertEqual(503, context.exception.status_code)
        self.assertEqual([], FakeAdminRepository.calls)

    async def test_wrong_secret_is_rejected(self):
        with patch.object(admin_router.settings, "ADMIN_BOOTSTRAP_SECRET", "another-secret-with-32-characters"):
            with self.assertRaises(HTTPException) as context:
                await admin_router.bootstrap_admin(self.payload, session=object())
        self.assertEqual(403, context.exception.status_code)
        self.assertEqual([], FakeAdminRepository.calls)

    async def test_success_creates_first_admin(self):
        with (
            patch.object(admin_router, "AdminRepository", FakeAdminRepository),
            patch.object(admin_router.settings, "ADMIN_BOOTSTRAP_SECRET", "deployment-secret-with-32-characters"),
        ):
            result = await admin_router.bootstrap_admin(self.payload, session=object())
        self.assertEqual(9, result["user_id"])
        self.assertEqual("owner@example.com", result["email"])
        self.assertEqual(
            [("owner@example.com", "owner", "safe-password")],
            FakeAdminRepository.calls,
        )

    async def test_existing_admin_is_reported_as_conflict(self):
        FakeAdminRepository.bootstrap_error = AdminStateConflict("系统已经完成管理员初始化")
        with (
            patch.object(admin_router, "AdminRepository", FakeAdminRepository),
            patch.object(admin_router.settings, "ADMIN_BOOTSTRAP_SECRET", "deployment-secret-with-32-characters"),
        ):
            with self.assertRaises(HTTPException) as context:
                await admin_router.bootstrap_admin(self.payload, session=object())
        self.assertEqual(409, context.exception.status_code)

    async def test_existing_email_is_reported_as_conflict(self):
        FakeAdminRepository.bootstrap_error = AdminEmailConflict("该邮箱已经存在")
        with (
            patch.object(admin_router, "AdminRepository", FakeAdminRepository),
            patch.object(admin_router.settings, "ADMIN_BOOTSTRAP_SECRET", "deployment-secret-with-32-characters"),
        ):
            with self.assertRaises(HTTPException) as context:
                await admin_router.bootstrap_admin(self.payload, session=object())
        self.assertEqual(409, context.exception.status_code)


class FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeBootstrapSession:
    def __init__(self):
        self.scalar_results = [0, None]
        self.executed = []
        self.added = []

    def begin(self):
        return FakeTransaction()

    async def execute(self, statement, parameters=None):
        self.executed.append((str(statement), parameters))

    async def scalar(self, statement):
        return self.scalar_results.pop(0)

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        for value in self.added:
            if isinstance(value, User) and value.id is None:
                value.id = 42


class AdminBootstrapRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_bootstrap_builds_admin_credit_and_audit_in_locked_transaction(self):
        session = FakeBootstrapSession()
        user = await AdminRepository(session).bootstrap_admin(
            "owner@example.com", "owner", "safe-password"
        )

        self.assertEqual(42, user.id)
        self.assertEqual("admin", user.role)
        self.assertEqual("active", user.status)
        self.assertIn("pg_advisory_xact_lock", session.executed[0][0])
        credit = next(value for value in session.added if isinstance(value, UserCredit))
        audit = next(value for value in session.added if isinstance(value, AdminActionLog))
        self.assertEqual(0, credit.balance)
        self.assertEqual(0, credit.logo_balance)
        self.assertEqual("bootstrap_admin", audit.action)
        self.assertEqual(42, audit.admin_user_id)
        self.assertEqual(42, audit.target_user_id)

if __name__ == "__main__":
    unittest.main()

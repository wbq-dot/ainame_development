import unittest
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from pydantic import ValidationError

from models.package import Package
from models.user_credit import CreditLog, UserCredit
from modules.admin.admin_action_log import AdminActionLog
from modules.admin.admin_repo import (
    AdminRepository,
    AdminStateConflict,
    AdminTargetForbidden,
)
from modules.admin.admin_schemas import AdminCreditAdjustmentIn


class FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeSession:
    def __init__(self, *scalar_results):
        self.scalar_results = list(scalar_results)
        self.statements = []
        self.added = []

    def begin(self):
        return FakeTransaction()

    async def scalar(self, statement):
        self.statements.append(str(statement))
        return self.scalar_results.pop(0)

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        return None


class FakeScalarCollection:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class FakePackageListSession(FakeSession):
    def __init__(self, packages):
        super().__init__()
        self.packages = packages

    async def scalars(self, statement):
        self.statements.append(str(statement))
        return FakeScalarCollection(self.packages)


def make_user(status="active", role="user"):
    now = datetime.now()
    return SimpleNamespace(
        id=7,
        email="user@example.com",
        username="tester",
        role=role,
        status=status,
        created_at=now,
        updated_at=now,
        frozen_at=now if status == "frozen" else None,
        deleted_at=now if status == "deleted" else None,
    )


def make_credit():
    return SimpleNamespace(
        balance=8,
        total_used=3,
        total_recharge=10,
        total_refund=0,
        logo_balance=5,
        logo_total_used=2,
        logo_total_recharge=6,
        logo_total_refund=0,
    )


class AdminCreditAdjustmentTests(unittest.IsolatedAsyncioTestCase):
    async def test_name_credit_increase_is_audited_without_changing_totals(self):
        user = make_user()
        credit = make_credit()
        session = FakeSession(user, credit)

        result = await AdminRepository(session).adjust_user_credit(
            admin_user_id=1,
            target_user_id=user.id,
            credit_type="name",
            change_count=4,
            reason="客服补偿",
        )

        self.assertEqual(8, result["balance_before"])
        self.assertEqual(12, result["balance_after"])
        self.assertEqual(12, credit.balance)
        self.assertEqual(10, credit.total_recharge)
        self.assertEqual(3, credit.total_used)
        self.assertTrue(all("FOR UPDATE" in sql for sql in session.statements))

        credit_log = next(value for value in session.added if isinstance(value, CreditLog))
        audit = next(value for value in session.added if isinstance(value, AdminActionLog))
        self.assertEqual("name", credit_log.credit_type)
        self.assertEqual(4, credit_log.change_count)
        self.assertEqual(12, credit_log.balance_after)
        self.assertEqual("admin_adjustment", credit_log.type)
        self.assertEqual("adjust_name_credit", audit.action)
        self.assertEqual("客服补偿", audit.reason)
        self.assertEqual(user.id, audit.target_user_id)
        self.assertIsNone(audit.target_package_id)

    async def test_logo_credit_can_be_reduced_for_frozen_user(self):
        user = make_user(status="frozen")
        credit = make_credit()
        session = FakeSession(user, credit)

        result = await AdminRepository(session).adjust_user_credit(
            1, user.id, "logo", -3, "纠正误发"
        )

        self.assertEqual(2, result["balance_after"])
        self.assertEqual(2, credit.logo_balance)
        self.assertEqual(6, credit.logo_total_recharge)
        self.assertEqual(2, credit.logo_total_used)

    async def test_adjustment_creates_missing_credit_account(self):
        user = make_user()
        session = FakeSession(user, None)

        result = await AdminRepository(session).adjust_user_credit(
            1, user.id, "logo", 2, "补建账户"
        )

        credit = next(value for value in session.added if isinstance(value, UserCredit))
        self.assertEqual(2, credit.logo_balance)
        self.assertEqual(0, credit.total_recharge)
        self.assertEqual(2, result["balance_after"])

    async def test_adjustment_cannot_make_balance_negative(self):
        user = make_user()
        session = FakeSession(user, make_credit())

        with self.assertRaisesRegex(AdminStateConflict, "不能小于"):
            await AdminRepository(session).adjust_user_credit(
                1, user.id, "logo", -6, "扣回"
            )

        self.assertFalse(session.added)

    async def test_deleted_user_cannot_be_adjusted(self):
        user = make_user(status="deleted")
        session = FakeSession(user)

        with self.assertRaisesRegex(AdminStateConflict, "正常或冻结"):
            await AdminRepository(session).adjust_user_credit(
                1, user.id, "name", 1, "无效操作"
            )

    async def test_repository_rejects_zero_change_and_blank_reason(self):
        with self.assertRaisesRegex(AdminStateConflict, "不能为 0"):
            await AdminRepository(FakeSession()).adjust_user_credit(
                1, 7, "name", 0, "无效操作"
            )
        with self.assertRaisesRegex(AdminStateConflict, "不能为空"):
            await AdminRepository(FakeSession()).adjust_user_credit(
                1, 7, "name", 1, "   "
            )

    async def test_admin_account_cannot_be_adjusted(self):
        user = make_user(role="admin")
        session = FakeSession(user)

        with self.assertRaises(AdminTargetForbidden):
            await AdminRepository(session).adjust_user_credit(
                1, user.id, "name", 1, "无效操作"
            )

    def test_zero_change_and_blank_reason_are_rejected(self):
        with self.assertRaises(ValidationError):
            AdminCreditAdjustmentIn(
                credit_type="name", change_count=0, reason="客服补偿"
            )
        with self.assertRaises(ValidationError):
            AdminCreditAdjustmentIn(
                credit_type="logo", change_count=1, reason="   "
            )


class AdminPackageManagementTests(unittest.IsolatedAsyncioTestCase):
    async def test_admin_package_list_includes_active_and_inactive(self):
        active = Package(
            id=1,
            name="起名体验包",
            price=Decimal("9.90"),
            credit_count=5,
            credit_type="name",
            is_active=True,
        )
        inactive = Package(
            id=2,
            name="Logo 体验包",
            price=Decimal("19.90"),
            credit_count=3,
            credit_type="logo",
            is_active=False,
        )
        session = FakePackageListSession([active, inactive])

        result = await AdminRepository(session).list_packages()

        self.assertEqual([active, inactive], result)
        self.assertNotIn("WHERE", session.statements[0])

    async def test_package_can_be_deactivated_with_lock_and_audit(self):
        package = Package(
            id=3,
            name="起名体验包",
            price=Decimal("9.90"),
            credit_count=5,
            credit_type="name",
            is_active=True,
        )
        session = FakeSession(package)

        result, changed = await AdminRepository(session).change_package_status(
            admin_user_id=1,
            package_id=package.id,
            is_active=False,
        )

        self.assertIs(result, package)
        self.assertTrue(changed)
        self.assertFalse(package.is_active)
        self.assertIn("FOR UPDATE", session.statements[0])
        audit = next(value for value in session.added if isinstance(value, AdminActionLog))
        self.assertEqual("package_deactivate", audit.action)
        self.assertEqual(package.id, audit.target_package_id)
        self.assertIsNone(audit.target_user_id)

    async def test_repeated_package_status_is_idempotent(self):
        package = Package(
            id=3,
            name="起名体验包",
            price=Decimal("9.90"),
            credit_count=5,
            credit_type="name",
            is_active=False,
        )
        session = FakeSession(package)

        _, changed = await AdminRepository(session).change_package_status(
            1, package.id, False
        )

        self.assertFalse(changed)
        self.assertFalse(session.added)


if __name__ == "__main__":
    unittest.main()

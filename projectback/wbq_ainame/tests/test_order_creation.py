import unittest
from decimal import Decimal

from models.package import Package
from models.user_order import UserOrder
from repository.order_repo import OrderRepo, PackageUnavailableError


class FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeSession:
    def __init__(self, package):
        self.package = package
        self.statement = None
        self.added = []

    def begin(self):
        return FakeTransaction()

    async def scalar(self, statement):
        self.statement = str(statement)
        return self.package

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        return None


def make_package(is_active=True):
    return Package(
        id=4,
        name="Logo 入门包",
        price=Decimal("19.90"),
        credit_count=3,
        credit_type="logo",
        is_active=is_active,
    )


class AtomicOrderCreationTests(unittest.IsolatedAsyncioTestCase):
    async def test_active_package_is_locked_and_snapshotted(self):
        package = make_package()
        session = FakeSession(package)

        order, selected_package = await OrderRepo(session).create_order(8, package.id)

        self.assertIs(package, selected_package)
        self.assertIn("FOR UPDATE", session.statement)
        self.assertIsInstance(order, UserOrder)
        self.assertEqual(package.id, order.package_id)
        self.assertEqual(package.price, order.amount)
        self.assertEqual(package.credit_count, order.credit_count)
        self.assertEqual(package.credit_type, order.credit_type)
        self.assertEqual([order], session.added)

    async def test_inactive_package_cannot_create_new_order(self):
        session = FakeSession(make_package(is_active=False))

        with self.assertRaisesRegex(PackageUnavailableError, "已下架"):
            await OrderRepo(session).create_order(8, 4)

        self.assertFalse(session.added)

    async def test_missing_package_cannot_create_new_order(self):
        session = FakeSession(None)

        with self.assertRaises(PackageUnavailableError):
            await OrderRepo(session).create_order(8, 999)


if __name__ == "__main__":
    unittest.main()

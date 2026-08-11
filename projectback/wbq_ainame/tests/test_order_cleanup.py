import unittest

from sqlalchemy.dialects import mysql

from repository.order_repo import OrderRepo


class FakeResult:
    rowcount = 3


class FakeSession:
    def __init__(self):
        self.statement = None

    def begin(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def execute(self, statement):
        self.statement = statement
        return FakeResult()


class OrderCleanupTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_expired_pending_orders_are_closed_and_retained(self):
        session = FakeSession()

        deleted_count = await OrderRepo(session).delete_expired_pending_orders()

        sql = str(
            session.statement.compile(
                dialect=mysql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        normalized_sql = " ".join(sql.lower().split())

        self.assertEqual(3, deleted_count)
        self.assertIn("update user_order", normalized_sql)
        self.assertIn("set status='closed'", normalized_sql)
        self.assertIn("user_order.status = 'pending'", normalized_sql)
        self.assertIn("user_order.expires_at <= now()", normalized_sql)


if __name__ == "__main__":
    unittest.main()

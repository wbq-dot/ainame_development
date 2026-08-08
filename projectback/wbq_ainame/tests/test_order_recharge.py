import unittest
from types import SimpleNamespace

from repository.order_repo import OrderRepo


class FakeSession:
    def __init__(self, order, credit):
        self.results = [order, credit]
        self.added = []

    def begin(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def scalar(self, statement):
        return self.results.pop(0)

    def add(self, value):
        self.added.append(value)


def pending_order(credit_type="name", count=20):
    return SimpleNamespace(
        status="pending",
        user_id=1,
        credit_count=count,
        credit_type=credit_type,
        alipay_trade_no=None,
        paid_at=None,
    )


class OrderRechargeTests(unittest.IsolatedAsyncioTestCase):
    async def test_name_recharge_updates_balance_and_total(self):
        order = pending_order("name", 20)
        credit = SimpleNamespace(
            balance=46,
            total_recharge=53,
            logo_balance=7,
            logo_total_recharge=6,
        )
        session = FakeSession(order, credit)

        result, first_success = await OrderRepo(session).pay_success("order-1", "trade-1")

        self.assertIs(result, order)
        self.assertTrue(first_success)
        self.assertEqual(66, credit.balance)
        self.assertEqual(73, credit.total_recharge)
        self.assertEqual(7, credit.logo_balance)
        self.assertEqual(6, credit.logo_total_recharge)
        self.assertEqual("name", session.added[0].credit_type)

    async def test_logo_recharge_updates_separate_total(self):
        order = pending_order("logo", 5)
        credit = SimpleNamespace(
            balance=46,
            total_recharge=73,
            logo_balance=2,
            logo_total_recharge=1,
        )
        session = FakeSession(order, credit)

        _, first_success = await OrderRepo(session).pay_success("order-2", "trade-2")

        self.assertTrue(first_success)
        self.assertEqual(46, credit.balance)
        self.assertEqual(73, credit.total_recharge)
        self.assertEqual(7, credit.logo_balance)
        self.assertEqual(6, credit.logo_total_recharge)
        self.assertEqual("logo", session.added[0].credit_type)

    async def test_paid_order_is_not_counted_twice(self):
        order = SimpleNamespace(status="paid")
        session = FakeSession(order, credit=None)

        result, first_success = await OrderRepo(session).pay_success("order-3", "trade-3")

        self.assertIs(result, order)
        self.assertFalse(first_success)
        self.assertFalse(session.added)


if __name__ == "__main__":
    unittest.main()

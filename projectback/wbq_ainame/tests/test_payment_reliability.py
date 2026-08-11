import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from core import payment_service
from repository.payment_repo import PaymentRepository, RefundNotEligible
from routers import pay_router


class FakeRequest:
    def __init__(self, data=None):
        self.data = data or {}
        self.query_params = self.data

    async def form(self):
        return self.data


class FakeOrderRepo:
    order = None

    def __init__(self, session):
        self.session = session

    async def get_by_order_no(self, order_no):
        return self.order


class FakePaymentRepo:
    payment_calls = []
    close_calls = []

    def __init__(self, session):
        self.session = session

    async def record_payment_success(self, order_no, trade_no):
        self.payment_calls.append((order_no, trade_no))
        return "credited", None

    async def record_provider_closed(self, order_no):
        self.close_calls.append(order_no)


class PaymentNotifyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FakePaymentRepo.payment_calls = []
        FakePaymentRepo.close_calls = []
        FakeOrderRepo.order = SimpleNamespace(amount=Decimal("19.90"))
        self.base_data = {
            "sign": "signed",
            "sign_type": "RSA2",
            "app_id": "app-1",
            "seller_id": "seller-1",
            "out_trade_no": "order-1",
            "trade_no": "trade-1",
            "trade_status": "TRADE_SUCCESS",
            "total_amount": "19.90",
        }

    async def call_notify(self, data):
        fake_alipay = SimpleNamespace(verify=lambda payload, sign: True)
        with (
            patch.object(pay_router, "create_alipay", return_value=fake_alipay),
            patch.object(pay_router, "OrderRepo", FakeOrderRepo),
            patch.object(pay_router, "PaymentRepository", FakePaymentRepo),
            patch.object(pay_router.settings, "ALIPAY_APP_ID", "app-1"),
            patch.object(pay_router.settings, "ALIPAY_SELLER_ID", "seller-1"),
        ):
            return await pay_router.alipay_notify(FakeRequest(data), session=object())

    async def test_valid_notification_credits_once_through_repository(self):
        response = await self.call_notify(dict(self.base_data))
        self.assertEqual(b"success", response.body)
        self.assertEqual([("order-1", "trade-1")], FakePaymentRepo.payment_calls)

    async def test_wrong_seller_is_rejected_without_mutation(self):
        data = dict(self.base_data, seller_id="attacker")
        response = await self.call_notify(data)
        self.assertEqual(b"failure", response.body)
        self.assertEqual([], FakePaymentRepo.payment_calls)

    async def test_amount_mismatch_is_rejected_without_mutation(self):
        data = dict(self.base_data, total_amount="1.00")
        response = await self.call_notify(data)
        self.assertEqual(b"failure", response.body)
        self.assertEqual([], FakePaymentRepo.payment_calls)

    async def test_closed_notification_does_not_credit(self):
        data = dict(self.base_data, trade_status="TRADE_CLOSED")
        response = await self.call_notify(data)
        self.assertEqual(b"success", response.body)
        self.assertEqual([], FakePaymentRepo.payment_calls)
        self.assertEqual(["order-1"], FakePaymentRepo.close_calls)

    async def test_return_url_only_redirects_and_never_credits(self):
        request = FakeRequest(
            {
                "sign": "signed",
                "sign_type": "RSA2",
                "app_id": "app-1",
                "out_trade_no": "order-1",
            }
        )
        fake_alipay = SimpleNamespace(verify=lambda payload, sign: True)
        with (
            patch.object(pay_router, "create_alipay", return_value=fake_alipay),
            patch.object(pay_router.settings, "ALIPAY_APP_ID", "app-1"),
            patch.object(
                pay_router.settings,
                "PAYMENT_FRONTEND_RESULT_URL",
                "http://front/#/pages/payment/result",
            ),
        ):
            response = await pay_router.pay_success(request)
        self.assertEqual(302, response.status_code)
        self.assertIn("order_no=order-1", response.headers["location"])


class RefundEligibilityTests(unittest.TestCase):
    def make_order(self, paid_at):
        return SimpleNamespace(
            order_no="order-1",
            amount=Decimal("19.90"),
            credit_count=3,
            credit_type="name",
            status="paid",
            created_at=paid_at - timedelta(minutes=1),
            expires_at=paid_at,
            paid_at=paid_at,
            closed_at=None,
        )

    def test_refund_is_eligible_inside_24_hour_window(self):
        now = datetime.now()
        data = PaymentRepository._order_dict(self.make_order(now), None, now=now)
        self.assertTrue(data["refund_eligible"])

    def test_refund_is_ineligible_after_24_hour_window(self):
        now = datetime.now()
        data = PaymentRepository._order_dict(
            self.make_order(now - timedelta(hours=25)), None, now=now
        )
        self.assertFalse(data["refund_eligible"])
        self.assertIn("24小时", data["refund_ineligible_reason"])


class RefundReservationTests(unittest.TestCase):
    def test_reservation_deducts_matching_credit_type(self):
        credit = SimpleNamespace(balance=9, logo_balance=4)
        refund = SimpleNamespace(
            user_id=7,
            credit_count=3,
            credit_type="logo",
            reserved_credit_count=0,
            reservation_key=None,
        )
        log = PaymentRepository._reserve_credit(credit, refund, "rf-1:1")
        self.assertEqual(1, credit.logo_balance)
        self.assertEqual(9, credit.balance)
        self.assertEqual(3, refund.reserved_credit_count)
        self.assertEqual(-3, log.change_count)

    def test_reservation_rejects_insufficient_balance(self):
        credit = SimpleNamespace(balance=1, logo_balance=4)
        refund = SimpleNamespace(
            user_id=7,
            credit_count=3,
            credit_type="name",
            reserved_credit_count=0,
            reservation_key=None,
        )
        with self.assertRaises(RefundNotEligible):
            PaymentRepository._reserve_credit(credit, refund, "rf-1:1")


class DummySessionContext:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeRefundRepository:
    finalized_success = []
    finalized_failure = []
    retries = []
    pair = None

    def __init__(self, session):
        self.session = session

    async def get_refund_for_processing(self, refund_no):
        return self.pair

    async def finalize_refund_success(self, refund_no, amount):
        self.finalized_success.append((refund_no, amount))

    async def finalize_refund_failure(self, refund_no, error):
        self.finalized_failure.append((refund_no, error))

    async def schedule_refund_retry(self, refund_no, error):
        self.retries.append((refund_no, error))


class RefundRecoveryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FakeRefundRepository.finalized_success = []
        FakeRefundRepository.finalized_failure = []
        FakeRefundRepository.retries = []
        refund = SimpleNamespace(
            refund_no="rf-1",
            status="processing",
            amount=Decimal("19.90"),
            reason="test",
        )
        order = SimpleNamespace(order_no="order-1")
        FakeRefundRepository.pair = (refund, order)

    async def test_existing_provider_refund_is_recovered(self):
        fake_alipay = SimpleNamespace(
            api_alipay_trade_fastpay_refund_query=lambda *args, **kwargs: {
                "code": "10000",
                "refund_status": "REFUND_SUCCESS",
                "refund_amount": "19.90",
            }
        )
        with (
            patch.object(payment_service, "AsyncSessionFactory", lambda: DummySessionContext()),
            patch.object(payment_service, "PaymentRepository", FakeRefundRepository),
            patch.object(payment_service, "create_alipay", return_value=fake_alipay),
        ):
            await payment_service.process_refund("rf-1")
        self.assertEqual([("rf-1", Decimal("19.90"))], FakeRefundRepository.finalized_success)

    async def test_definitive_provider_failure_uses_terminal_failure_path(self):
        fake_alipay = SimpleNamespace(
            api_alipay_trade_fastpay_refund_query=lambda *args, **kwargs: {
                "code": "40004",
                "sub_code": "ACQ.REFUND_NOT_EXIST",
            },
            api_alipay_trade_refund=lambda *args, **kwargs: {
                "code": "40004",
                "sub_code": "ACQ.TRADE_STATUS_ERROR",
                "sub_msg": "trade cannot be refunded",
            },
        )
        with (
            patch.object(payment_service, "AsyncSessionFactory", lambda: DummySessionContext()),
            patch.object(payment_service, "PaymentRepository", FakeRefundRepository),
            patch.object(payment_service, "create_alipay", return_value=fake_alipay),
        ):
            await payment_service.process_refund("rf-1")
        self.assertEqual("rf-1", FakeRefundRepository.finalized_failure[0][0])
        self.assertEqual([], FakeRefundRepository.retries)


if __name__ == "__main__":
    unittest.main()

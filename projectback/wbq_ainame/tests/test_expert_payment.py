import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from core import alipaytools
from core.alipaytools import PaymentConfigurationError
from repository.expert_repo import ExpertDomainError, ExpertRepository
from routers import expert_pay_router, expert_router


class FakeRequest:
    def __init__(self, data=None):
        self.data = data or {}
        self.query_params = self.data

    async def form(self):
        return self.data


class FakeExpertRepository:
    calls = []
    failure = None

    def __init__(self, session):
        self.session = session

    async def mark_paid(self, order_no, trade_no, amount):
        self.calls.append((order_no, trade_no, amount))
        if self.failure:
            raise self.failure
        order = SimpleNamespace(order_no=order_no)
        return order, len(self.calls) == 1


class FakeStatusSession:
    def __init__(self, result):
        self.result = result
        self.statement = None

    async def scalar(self, statement):
        self.statement = statement
        return self.result


class ExpertPaymentRouterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FakeExpertRepository.calls = []
        FakeExpertRepository.failure = None
        self.base_data = {
            "sign": "signed",
            "sign_type": "RSA2",
            "app_id": "app-1",
            "seller_id": "seller-1",
            "out_trade_no": "EX1",
            "trade_no": "TRADE1",
            "trade_status": "TRADE_SUCCESS",
            "total_amount": "88.00",
        }

    async def call_notify(self, data, *, signature_valid=True, config_error=False):
        if config_error:
            alipay = patch.object(
                alipaytools,
                "create_alipay",
                side_effect=PaymentConfigurationError("支付配置缺失"),
            )
        else:
            fake_alipay = SimpleNamespace(
                verify=lambda payload, sign: signature_valid
            )
            alipay = patch.object(
                alipaytools,
                "create_alipay",
                return_value=fake_alipay,
            )
        with (
            alipay,
            patch.object(alipaytools.settings, "ALIPAY_APP_ID", "app-1"),
            patch.object(alipaytools.settings, "ALIPAY_SELLER_ID", "seller-1"),
            patch.object(
                expert_pay_router,
                "ExpertRepository",
                FakeExpertRepository,
            ),
        ):
            return await expert_pay_router.expert_alipay_notify(
                FakeRequest(data),
                session=object(),
            )

    async def test_valid_notification_marks_expert_order_paid(self):
        response = await self.call_notify(dict(self.base_data))
        self.assertEqual(b"success", response.body)
        self.assertEqual(
            [("EX1", "TRADE1", Decimal("88.00"))],
            FakeExpertRepository.calls,
        )

    async def test_duplicate_valid_notification_remains_successful(self):
        first = await self.call_notify(dict(self.base_data))
        second = await self.call_notify(dict(self.base_data))
        self.assertEqual(b"success", first.body)
        self.assertEqual(b"success", second.body)
        self.assertEqual(2, len(FakeExpertRepository.calls))

    async def test_invalid_provider_identity_never_reaches_repository(self):
        invalid_payloads = (
            dict(self.base_data, sign_type="RSA"),
            dict(self.base_data, app_id="attacker"),
            dict(self.base_data, seller_id="attacker"),
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = await self.call_notify(payload)
                self.assertEqual(b"failure", response.body)
        response = await self.call_notify(
            dict(self.base_data),
            signature_valid=False,
        )
        self.assertEqual(b"failure", response.body)
        self.assertEqual([], FakeExpertRepository.calls)

    async def test_incomplete_or_non_success_notification_is_rejected(self):
        invalid_payloads = (
            dict(self.base_data, trade_no=""),
            dict(self.base_data, total_amount="not-a-number"),
            dict(self.base_data, trade_status="WAIT_BUYER_PAY"),
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = await self.call_notify(payload)
                self.assertEqual(b"failure", response.body)
        self.assertEqual([], FakeExpertRepository.calls)

    async def test_amount_mismatch_and_unknown_error_return_failure(self):
        FakeExpertRepository.failure = ExpertDomainError("支付金额不匹配", 400)
        mismatch = await self.call_notify(dict(self.base_data, total_amount="8.80"))
        self.assertEqual(b"failure", mismatch.body)

        FakeExpertRepository.failure = RuntimeError("temporary database failure")
        unknown = await self.call_notify(dict(self.base_data))
        self.assertEqual(b"failure", unknown.body)

    async def test_configuration_error_returns_failure(self):
        response = await self.call_notify(dict(self.base_data), config_error=True)
        self.assertEqual(b"failure", response.body)
        self.assertEqual([], FakeExpertRepository.calls)

    async def test_return_page_never_marks_order_paid(self):
        mark_paid = AsyncMock()
        fake_alipay = SimpleNamespace(verify=lambda payload, sign: True)
        with (
            patch.object(alipaytools, "create_alipay", return_value=fake_alipay),
            patch.object(alipaytools.settings, "ALIPAY_APP_ID", "app-1"),
            patch.object(ExpertRepository, "mark_paid", mark_paid),
        ):
            valid = await expert_pay_router.expert_alipay_return(
                FakeRequest(dict(self.base_data))
            )
            invalid = await expert_pay_router.expert_alipay_return(
                FakeRequest(dict(self.base_data, sign_type="RSA"))
            )
        mark_paid.assert_not_awaited()
        self.assertIn("等待支付宝异步通知", valid)
        self.assertIn("支付结果验证失败", invalid)

        with patch.object(
            alipaytools,
            "create_alipay",
            side_effect=RuntimeError("temporary verify failure"),
        ):
            failed = await expert_pay_router.expert_alipay_return(
                FakeRequest(dict(self.base_data))
            )
        mark_paid.assert_not_awaited()
        self.assertIn("支付结果验证失败", failed)

    async def test_payment_status_is_scoped_to_current_user(self):
        order = SimpleNamespace(
            order_no="EX1",
            payment_status="paid",
            service_status="pending_acceptance",
        )
        session = FakeStatusSession(order)
        result = await expert_router.expert_payment_status(
            "EX1",
            user_id=7,
            session=session,
        )
        params = session.statement.compile().params
        self.assertIn("EX1", params.values())
        self.assertIn(7, params.values())
        self.assertEqual("paid", result["payment_status"])

        with self.assertRaises(HTTPException) as context:
            await expert_router.expert_payment_status(
                "EX1",
                user_id=8,
                session=FakeStatusSession(None),
            )
        self.assertEqual(404, context.exception.status_code)


if __name__ == "__main__":
    unittest.main()

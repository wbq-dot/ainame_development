import unittest
from unittest.mock import patch

from fastapi import HTTPException

from routers import logo_router
from schemas.logo_schemas import LogoGenerateIn
from core.logo_tools import build_logo_prompt


class FakeCreditRepository:
    consume_result = 0
    consume_error = None
    refund_calls = 0

    def __init__(self, session):
        self.session = session

    async def consume_logo_credit(self, user_id):
        if self.consume_error:
            raise self.consume_error
        return self.consume_result

    async def refund_logo_credit(self, user_id):
        type(self).refund_calls += 1
        return self.consume_result + 1


class LogoCreditTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FakeCreditRepository.consume_result = 0
        FakeCreditRepository.consume_error = None
        FakeCreditRepository.refund_calls = 0

    def test_rich_brand_brief_is_included_in_prompt(self):
        prompt = build_logo_prompt(
            "青衍科技",
            industry="人工智能",
            brand_personality="可信、克制",
            logo_style="几何科技",
            primary_colors="深海科技",
            graphic_elements="向上生长的线条",
            usage_scenes="App 图标、官网",
        )
        self.assertIn("人工智能", prompt)
        self.assertIn("几何科技", prompt)
        self.assertIn("向上生长的线条", prompt)
        self.assertIn("App 图标、官网", prompt)

    async def test_insufficient_credit_does_not_call_model(self):
        FakeCreditRepository.consume_error = ValueError("Logo次数不足")
        with (
            patch.object(logo_router, "CreditRepository", FakeCreditRepository),
            patch.object(logo_router, "run_in_threadpool") as model_call,
        ):
            with self.assertRaises(HTTPException) as context:
                await logo_router.generate_logo(
                    LogoGenerateIn(company_name="测试企业"),
                    user_id=7,
                    session=object(),
                )

        self.assertEqual(400, context.exception.status_code)
        model_call.assert_not_called()

    async def test_success_keeps_deduction_and_returns_balance(self):
        FakeCreditRepository.consume_result = 2

        async def fake_model_call(*args, **kwargs):
            return {
                "logo_prompt": "测试提示词",
                "logo_url": "https://example.com/logo.png",
                "logo_status": "生成成功",
            }

        with (
            patch.object(logo_router, "CreditRepository", FakeCreditRepository),
            patch.object(logo_router, "run_in_threadpool", fake_model_call),
            patch.object(logo_router, "account_is_active", return_value=True),
        ):
            result = await logo_router.generate_logo(
                LogoGenerateIn(company_name="测试企业"),
                user_id=7,
                session=object(),
            )

        self.assertEqual(2, result["remaining_logo_balance"])
        self.assertEqual(1, result["credit_cost"])
        self.assertEqual(0, FakeCreditRepository.refund_calls)

    async def test_deleted_during_generation_does_not_return_logo(self):
        async def fake_model_call(*args, **kwargs):
            return {
                "logo_prompt": "测试提示词",
                "logo_url": "https://example.com/logo.png",
                "logo_status": "生成成功",
            }

        with (
            patch.object(logo_router, "CreditRepository", FakeCreditRepository),
            patch.object(logo_router, "run_in_threadpool", fake_model_call),
            patch.object(logo_router, "account_is_active", return_value=False),
        ):
            with self.assertRaises(HTTPException) as context:
                await logo_router.generate_logo(
                    LogoGenerateIn(company_name="测试企业"),
                    user_id=7,
                    session=object(),
                )

        self.assertEqual(401, context.exception.status_code)

    async def test_failed_generation_refunds_credit(self):
        async def fake_model_call(*args, **kwargs):
            return {
                "logo_prompt": "测试提示词",
                "logo_url": "",
                "logo_status": "生成失败：请求超时",
            }

        with (
            patch.object(logo_router, "CreditRepository", FakeCreditRepository),
            patch.object(logo_router, "run_in_threadpool", fake_model_call),
        ):
            with self.assertRaises(HTTPException) as context:
                await logo_router.generate_logo(
                    LogoGenerateIn(company_name="测试企业"),
                    user_id=7,
                    session=object(),
                )

        self.assertEqual(502, context.exception.status_code)
        self.assertIn("已退回", context.exception.detail)
        self.assertEqual(1, FakeCreditRepository.refund_calls)


if __name__ == "__main__":
    unittest.main()

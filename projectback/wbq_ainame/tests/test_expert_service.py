import os
import tempfile
import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from starlette.datastructures import Headers, UploadFile

from repository.expert_repo import ExpertDomainError, ExpertRepository
from core.expert_service import (
    EXPERT_TIERS,
    calculate_commission,
    create_expert_order_no,
    private_file_path,
    save_private_pdf,
    save_private_image,
)
from schemas.expert_schemas import ExpertOrderCreateIn


class FakeSession:
    def __init__(self, scalar_results=None, scalars_results=None):
        self.scalar_results = list(scalar_results or [])
        self.scalars_results = list(scalars_results or [])
        self.added = []

    def begin(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def scalar(self, statement):
        return self.scalar_results.pop(0) if self.scalar_results else None

    async def scalars(self, statement):
        values = self.scalars_results.pop(0) if self.scalars_results else []
        return SimpleNamespace(all=lambda: values)

    async def flush(self):
        return None

    def add(self, value):
        self.added.append(value)


class ExpertServiceTests(unittest.IsolatedAsyncioTestCase):
    def test_commission_is_twenty_percent(self):
        fee, income = calculate_commission(Decimal("199.90"))
        self.assertEqual(Decimal("39.98"), fee)
        self.assertEqual(Decimal("159.92"), income)

    def test_order_number_is_namespaced_and_unique(self):
        now = datetime(2026, 8, 10, 12, 30, 0)
        first = create_expert_order_no(now)
        second = create_expert_order_no(now)
        self.assertTrue(first.startswith("EX20260810123000"))
        self.assertNotEqual(first, second)

    async def test_payment_callback_is_idempotent(self):
        order = SimpleNamespace(
            amount=Decimal("88.00"),
            payment_status="unpaid",
            service_status="pending_payment",
            alipay_trade_no=None,
            paid_at=None,
            accept_deadline=None,
        )
        first_order, first = await ExpertRepository(FakeSession([order])).mark_paid(
            "EX1", "TRADE1", Decimal("88.00")
        )
        second_order, second = await ExpertRepository(FakeSession([order])).mark_paid(
            "EX1", "TRADE1", Decimal("88.00")
        )
        self.assertIs(first_order, second_order)
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual("paid", order.payment_status)
        self.assertEqual("pending_acceptance", order.service_status)
        self.assertIsNotNone(order.accept_deadline)

    async def test_payment_rejects_wrong_amount(self):
        order = SimpleNamespace(
            amount=Decimal("88.00"),
            payment_status="unpaid",
            service_status="pending_payment",
        )
        with self.assertRaises(ExpertDomainError):
            await ExpertRepository(FakeSession([order])).mark_paid(
                "EX1", "TRADE1", Decimal("8.80")
            )

    async def test_order_keeps_package_price_and_delivery_snapshot(self):
        package = SimpleNamespace(
            id=2,
            expert_id=3,
            name="企业名深度精批",
            price=Decimal("100.00"),
            delivery_days=4,
        )
        profile = SimpleNamespace(id=3, user_id=4)
        session = FakeSession([package, profile])
        order = await ExpertRepository(session).create_order(
            9,
            {
                "package_id": 2,
                "candidate_name": "知名台",
                "naming_type": "company",
                "background": "面向创业者的智能起名平台",
                "focus": "读音与品牌辨识度",
                "notes": None,
            },
        )
        self.assertEqual("企业名深度精批", order.package_name)
        self.assertEqual(Decimal("100.00"), order.amount)
        self.assertEqual(4, order.delivery_days)
        self.assertEqual(Decimal("20.00"), order.platform_fee)
        self.assertEqual(Decimal("80.00"), order.expert_income)

    async def test_fixed_tier_order_enters_unassigned_expert_pool(self):
        order = await ExpertRepository(FakeSession()).create_order(
            9,
            {
                "package_id": None,
                "expert_level": "renowned",
                "service_mode": "naming",
                "candidate_name": None,
                "naming_type": "person",
                "surname": "林",
                "background": "希望给新生儿取一个温润大方的名字",
                "focus": "五行与读音",
                "notes": None,
            },
        )
        self.assertIsNone(order.expert_id)
        self.assertIsNone(order.package_id)
        self.assertEqual("renowned", order.expert_level)
        self.assertEqual(EXPERT_TIERS["renowned"]["price"], order.amount)
        self.assertEqual("知名专家", order.package_name)

    def test_person_naming_requires_surname_and_review_requires_name(self):
        common = {
            "package_id": None,
            "naming_type": "person",
            "background": "这是一段足够长的客户起名背景信息",
            "focus": "寓意与读音",
        }
        with self.assertRaises(ValueError):
            ExpertOrderCreateIn(service_mode="naming", **common)
        with self.assertRaises(ValueError):
            ExpertOrderCreateIn(service_mode="review", surname="林", **common)

    async def test_admin_approval_promotes_user_to_expert_role(self):
        profile = SimpleNamespace(
            user_id=8,
            status="pending",
            review_note=None,
            reviewed_at=None,
            updated_at=None,
        )
        user = SimpleNamespace(role="user")
        await ExpertRepository(FakeSession([profile, user])).admin_profile_decision(
            3, "approve", "资料通过"
        )
        self.assertEqual("approved", profile.status)
        self.assertEqual("expert", user.role)

    async def test_timeout_maintenance_marks_refund_and_dispute(self):
        now = datetime.now()
        unpaid = SimpleNamespace(
            service_status="pending_payment",
            payment_status="unpaid",
            created_at=now - timedelta(hours=2),
        )
        awaiting = SimpleNamespace(
            service_status="pending_acceptance",
            payment_status="paid",
            created_at=now,
            accept_deadline=now - timedelta(minutes=1),
        )
        working = SimpleNamespace(
            service_status="working",
            payment_status="paid",
            created_at=now,
            delivery_deadline=now - timedelta(minutes=1),
            dispute_reason=None,
        )
        result = await ExpertRepository(
            FakeSession(scalars_results=[[unpaid, awaiting, working]])
        ).run_maintenance(now)
        self.assertEqual("closed", unpaid.payment_status)
        self.assertEqual("refund_pending", awaiting.payment_status)
        self.assertEqual("disputed", working.service_status)
        self.assertEqual(1, result["accept_timeout"])
        self.assertEqual(1, result["delivery_timeout"])

    async def test_admin_refund_reverses_unpaid_income(self):
        order = SimpleNamespace(
            id=10,
            payment_status="paid",
            service_status="disputed",
            settlement_status="available",
            refund_reference=None,
            refunded_at=None,
            admin_note=None,
        )
        income = SimpleNamespace(status="available")
        await ExpertRepository(FakeSession([order, income])).admin_resolve_dispute(
            10, "refund", "管理员已在支付宝后台退款", "REFUND-10"
        )
        self.assertEqual("refunded", order.payment_status)
        self.assertEqual("cancelled", order.service_status)
        self.assertEqual("reversed", income.status)

    async def test_only_one_revision_can_be_requested(self):
        order = SimpleNamespace(
            service_status="delivered",
            revision_used=False,
            confirm_deadline=datetime.now() + timedelta(days=1),
            revision_reason=None,
        )
        await ExpertRepository(FakeSession([order])).request_revision(1, 9, "请加强读音分析")
        self.assertTrue(order.revision_used)
        self.assertEqual("revision_requested", order.service_status)

        order.service_status = "delivered"
        order.confirm_deadline = datetime.now() + timedelta(days=1)
        with self.assertRaises(ExpertDomainError):
            await ExpertRepository(FakeSession([order])).request_revision(1, 9, "再次修改")

    async def test_completion_creates_available_income(self):
        order = SimpleNamespace(
            id=12,
            expert_id=3,
            user_id=9,
            service_status="delivered",
            settlement_status="none",
            completed_at=None,
            amount=Decimal("100.00"),
            platform_fee=Decimal("20.00"),
            expert_income=Decimal("80.00"),
        )
        session = FakeSession([order, None])
        await ExpertRepository(session).user_confirm(12, 9)
        self.assertEqual("completed", order.service_status)
        self.assertEqual("available", order.settlement_status)
        self.assertEqual(1, len(session.added))
        self.assertEqual(Decimal("80.00"), session.added[0].net_amount)

    async def test_private_pdf_validation_and_random_storage_key(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"EXPERT_PRIVATE_STORAGE_DIR": directory}
        ):
            upload = UploadFile(
                BytesIO(b"%PDF-1.7\nexample"),
                filename="专家报告.pdf",
                headers=Headers({"content-type": "application/pdf"}),
            )
            key, name, size, mime = await save_private_pdf(upload, "report_12")
            self.assertNotEqual("专家报告.pdf", key)
            self.assertEqual("专家报告.pdf", name)
            self.assertEqual("application/pdf", mime)
            self.assertTrue(private_file_path(key).is_file())
            self.assertGreater(size, 0)

    async def test_non_pdf_and_fake_pdf_are_rejected(self):
        not_pdf = UploadFile(
            BytesIO(b"plain text"),
            filename="report.txt",
            headers=Headers({"content-type": "text/plain"}),
        )
        with self.assertRaises(HTTPException):
            await save_private_pdf(not_pdf, "report")

        fake_pdf = UploadFile(
            BytesIO(b"not really pdf"),
            filename="report.pdf",
            headers=Headers({"content-type": "application/pdf"}),
        )
        with self.assertRaises(HTTPException):
            await save_private_pdf(fake_pdf, "report")

    async def test_private_customer_image_validation_and_random_key(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"EXPERT_PRIVATE_STORAGE_DIR": directory}
        ):
            upload = UploadFile(
                BytesIO(b"\x89PNG\r\n\x1a\n" + b"image-data"),
                filename="出生资料.png",
                headers=Headers({"content-type": "image/png"}),
            )
            key, name, size, mime = await save_private_image(upload, "order_8")
            self.assertNotEqual(name, key)
            self.assertTrue(key.startswith("order_8_"))
            self.assertEqual("image/png", mime)
            self.assertTrue(private_file_path(key).is_file())
            self.assertGreater(size, 8)

        fake_image = UploadFile(
            BytesIO(b"not-an-image"),
            filename="fake.png",
            headers=Headers({"content-type": "image/png"}),
        )
        with self.assertRaises(HTTPException):
            await save_private_image(fake_image, "order_8")


if __name__ == "__main__":
    unittest.main()

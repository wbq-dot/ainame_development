import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from core.workflow import _knowledge_prompt
from modules.platform.platform_auth import DeveloperAuth, api_key_digest, issue_api_key
from modules.platform.platform_models import DeveloperAccount
from modules.platform.platform_repo import PlatformConflict, PlatformRepository, request_hash
from modules.platform.platform_schemas import BatchCreateIn, CampaignIn, DeveloperRegisterIn


class PlatformSecurityTests(unittest.TestCase):
    def test_api_key_only_exposes_prefix_and_digest_is_stable(self):
        raw, prefix, digest = issue_api_key()
        self.assertTrue(raw.startswith("zn_live_"))
        self.assertEqual(raw[:16], prefix)
        self.assertNotEqual(raw, digest)
        self.assertEqual(digest, api_key_digest(raw))

    def test_developer_token_has_separate_audience(self):
        developer = DeveloperAccount(id=7, email="dev@example.com", name="Dev", password_hash="x", status="active", auth_version=2, referral_code="ABC123")
        secret = "test-secret-that-is-at-least-32-bytes-long"
        with patch("modules.platform.platform_auth.settings.JWT_SECRET_KEY", secret):
            token = DeveloperAuth().login_tokens(developer)["access_token"]
            import jwt
            claims = jwt.decode(token, secret, algorithms=["HS256"], audience="developer")
        self.assertEqual("developer", claims["aud"])
        self.assertEqual("access", claims["type"])
        self.assertEqual("7", claims["sub"])

    def test_platform_naming_can_disable_private_user_knowledge(self):
        with patch("core.workflow.retrieve_user_knowledge") as retrieve:
            result = _knowledge_prompt(1, "query", "人名", "human", use_private_knowledge=False)
        retrieve.assert_not_called()
        self.assertIn("不读取普通用户私人资料", result)


class PlatformValidationTests(unittest.TestCase):
    def test_registration_passwords_must_match(self):
        with self.assertRaises(ValueError):
            DeveloperRegisterIn(email="dev@example.com", name="开发者", password="password1", confirm_password="password2", code="1234")

    def test_batch_limit_is_100(self):
        item = {"category": "人名", "surname": "张", "gender": "不限", "length": "不限", "other": "", "exclude": []}
        self.assertEqual(100, len(BatchCreateIn(items=[item] * 100).items))
        with self.assertRaises(ValueError): BatchCreateIn(items=[item] * 101)

    def test_campaign_requires_valid_window(self):
        now = datetime.now()
        with self.assertRaises(ValueError):
            CampaignIn(name="活动", starts_at=now, ends_at=now - timedelta(seconds=1))

    def test_request_hash_is_order_independent(self):
        self.assertEqual(request_hash({"a": 1, "b": 2}), request_hash({"b": 2, "a": 1}))


class FakeScalarResult:
    def __init__(self, value): self.value = value
    def first(self): return self.value


class AsyncContext:
    async def __aenter__(self): return self
    async def __aexit__(self, exc_type, exc, traceback): return False


class PlatformRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_idempotency_conflict_rejects_changed_payload(self):
        existing = type("Call", (), {"request_hash": request_hash({"a": 1})})()
        session = MagicMock()
        session.begin.return_value = AsyncContext()
        session.scalar = AsyncMock(return_value=existing)
        with self.assertRaises(PlatformConflict):
            await PlatformRepository(session).create_call(1, 2, "/x", "abcdefgh", {"a": 2})

    async def test_retry_of_already_queued_task_is_idempotent(self):
        task = type("Task", (), {"status": "queued"})()
        session = MagicMock()
        session.begin.return_value = AsyncContext()
        session.scalar = AsyncMock(return_value=task)
        result = await PlatformRepository(session).retry_task("task_1")
        self.assertIs(task, result)


if __name__ == "__main__":
    unittest.main()

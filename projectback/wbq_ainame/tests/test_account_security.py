import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from pydantic import ValidationError

from core import account_cleanup, authtools
from repository.account_repo import AdminSelfDeletionForbidden
from routers import account_router
from schemas.account_schemas import ChangeEmailIn, ChangePasswordIn, SendEmailChangeCodeIn


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.ttls = {}

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self.values:
            return False
        self.values[key] = value
        if ex is not None:
            self.ttls[key] = ex
        return True

    async def get(self, key):
        return self.values.get(key)

    async def ttl(self, key):
        return self.ttls.get(key, -2)

    async def delete(self, *keys):
        for key in keys:
            self.values.pop(key, None)
            self.ttls.pop(key, None)


class FakeSessionContext:
    def __init__(self, user):
        self.user = user

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def get(self, model, user_id):
        return self.user if self.user.id == user_id else None


class AccountSchemaTests(unittest.TestCase):
    def test_change_password_requires_matching_new_passwords(self):
        with self.assertRaises(ValidationError):
            ChangePasswordIn(
                current_password="old-password",
                new_password="new-password-1",
                confirm_password="new-password-2",
            )

    def test_change_password_rejects_same_password(self):
        with self.assertRaises(ValidationError):
            ChangePasswordIn(
                current_password="same-password",
                new_password="same-password",
                confirm_password="same-password",
            )


class AuthVersionTests(unittest.IsolatedAsyncioTestCase):
    async def test_auth_version_mismatch_invalidates_old_token(self):
        user = SimpleNamespace(
            id=7,
            status="active",
            role="user",
            auth_version=2,
        )
        handler = authtools.AuthHandler()
        with patch.object(
            authtools,
            "AsyncSessionFactory",
            return_value=FakeSessionContext(user),
        ):
            with self.assertRaises(HTTPException) as context:
                await handler._get_available_user(7, token_auth_version=1)
        self.assertEqual(401, context.exception.status_code)

    def test_legacy_token_defaults_to_version_zero(self):
        handler = authtools.AuthHandler()
        handler.secret = "account-security-test-secret-at-least-32-bytes"
        token = authtools.jwt.encode(
            {
                "user_id": 7,
                "type": "access",
                "exp": authtools.datetime.now(authtools.timezone.utc)
                + authtools.settings.JWT_ACCESS_TOKEN_EXPIRES,
            },
            handler.secret,
            algorithm=handler.algorithm,
        )
        claims = handler._decode_claims(token, "access", 401)
        self.assertEqual(0, claims["auth_version"])


class AccountRouterTests(unittest.IsolatedAsyncioTestCase):
    async def test_password_change_returns_relogin_message(self):
        repository = AsyncMock()
        with patch.object(account_router, "AccountRepository", return_value=repository):
            result = await account_router.change_password(
                ChangePasswordIn(
                    current_password="old-password",
                    new_password="new-password",
                    confirm_password="new-password",
                ),
                user_id=7,
                session=object(),
            )
        repository.change_password.assert_awaited_once_with(
            7,
            "old-password",
            "new-password",
        )
        self.assertIn("重新登录", result["message"])

    async def test_email_code_is_sent_to_new_email(self):
        redis = FakeRedis()
        repository = AsyncMock()
        mail = AsyncMock()
        with patch.object(account_router, "AccountRepository", return_value=repository):
            result = await account_router.send_email_change_code(
                SendEmailChangeCodeIn(new_email="New@Example.com"),
                user_id=7,
                session=object(),
                mail=mail,
                redis=redis,
            )
        repository.validate_email_target.assert_awaited_once_with(7, "new@example.com")
        mail.send_message.assert_awaited_once()
        saved = json.loads(redis.values[account_router._code_key(7)])
        self.assertEqual("new@example.com", saved["email"])
        self.assertRegex(saved["code"], r"^\d{6}$")
        self.assertEqual(300, redis.ttls[account_router._code_key(7)])
        self.assertIn("已发送", result["message"])

    async def test_email_code_send_is_rate_limited(self):
        redis = FakeRedis()
        redis.values[account_router._cooldown_key(7)] = "1"
        repository = AsyncMock()
        with patch.object(account_router, "AccountRepository", return_value=repository):
            with self.assertRaises(HTTPException) as context:
                await account_router.send_email_change_code(
                    SendEmailChangeCodeIn(new_email="new@example.com"),
                    user_id=7,
                    session=object(),
                    mail=AsyncMock(),
                    redis=redis,
                )
        self.assertEqual(429, context.exception.status_code)

    async def test_fifth_wrong_email_code_is_destroyed(self):
        redis = FakeRedis()
        key = account_router._code_key(7)
        redis.values[key] = json.dumps(
            {"email": "new@example.com", "code": "123456", "attempts": 4}
        )
        redis.ttls[key] = 120
        with self.assertRaises(HTTPException) as context:
            await account_router.change_email(
                ChangeEmailIn(new_email="new@example.com", code="000000"),
                user_id=7,
                session=object(),
                redis=redis,
            )
        self.assertEqual(400, context.exception.status_code)
        self.assertNotIn(key, redis.values)

    async def test_valid_email_code_is_single_use(self):
        redis = FakeRedis()
        key = account_router._code_key(7)
        redis.values[key] = json.dumps(
            {"email": "new@example.com", "code": "123456", "attempts": 0}
        )
        redis.ttls[key] = 120
        repository = AsyncMock()
        with patch.object(account_router, "AccountRepository", return_value=repository):
            result = await account_router.change_email(
                ChangeEmailIn(new_email="new@example.com", code="123456"),
                user_id=7,
                session=object(),
                redis=redis,
            )
        repository.change_email.assert_awaited_once_with(7, "new@example.com")
        self.assertNotIn(key, redis.values)
        self.assertIn("重新登录", result["message"])

    async def test_admin_cannot_self_delete(self):
        repository = AsyncMock()
        repository.soft_delete_self.side_effect = AdminSelfDeletionForbidden(
            "管理员账号不能自助注销"
        )
        with patch.object(account_router, "AccountRepository", return_value=repository):
            with self.assertRaises(HTTPException) as context:
                await account_router.delete_account(user_id=7, session=object())
        self.assertEqual(403, context.exception.status_code)


class AccountCleanupTests(unittest.IsolatedAsyncioTestCase):
    async def test_successful_cleanup_job_is_completed(self):
        with patch.object(
            account_cleanup,
            "_claim_due_jobs",
            AsyncMock(return_value=[(3, 7, 1)]),
        ), patch.object(
            account_cleanup,
            "purge_user_content",
            AsyncMock(),
        ) as purge, patch.object(
            account_cleanup,
            "_mark_completed",
            AsyncMock(),
        ) as completed:
            count = await account_cleanup.process_account_deletion_jobs()
        self.assertEqual(1, count)
        purge.assert_awaited_once_with(7)
        completed.assert_awaited_once_with(3)

    async def test_failed_cleanup_job_is_scheduled_for_retry(self):
        failure = RuntimeError("temporary store failure")
        with patch.object(
            account_cleanup,
            "_claim_due_jobs",
            AsyncMock(return_value=[(3, 7, 2)]),
        ), patch.object(
            account_cleanup,
            "purge_user_content",
            AsyncMock(side_effect=failure),
        ), patch.object(
            account_cleanup,
            "_mark_failed",
            AsyncMock(),
        ) as failed:
            count = await account_cleanup.process_account_deletion_jobs()
        self.assertEqual(0, count)
        failed.assert_awaited_once_with(3, 2, failure)


if __name__ == "__main__":
    unittest.main()

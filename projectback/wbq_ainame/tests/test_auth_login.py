import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from routers import auth_router
from schemas.user_schemas import LoginIn


class FakeUserRepository:
    user = None

    def __init__(self, session):
        self.session = session

    async def get_by_email(self, email):
        return self.user


def make_user(role, password="correct-password"):
    return SimpleNamespace(
        id=7,
        email=f"{role}@example.com",
        username=role,
        role=role,
        status="active",
        check_password=lambda candidate: candidate == password,
    )


class LoginEntryRoleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FakeUserRepository.user = None
        self.login_info = LoginIn(
            email="account@example.com",
            password="correct-password",
        )

    async def test_normal_login_rejects_admin_account(self):
        FakeUserRepository.user = make_user("admin")

        with (
            patch.object(auth_router, "UserRepository", FakeUserRepository),
            patch.object(auth_router.auth_handler, "encode_login_token") as encode_token,
        ):
            with self.assertRaises(HTTPException) as context:
                await auth_router.login(self.login_info, session=object())

        self.assertEqual(403, context.exception.status_code)
        self.assertEqual(
            "管理员账号请通过管理员登录入口登录",
            context.exception.detail,
        )
        encode_token.assert_not_called()

    async def test_admin_login_accepts_admin_account(self):
        FakeUserRepository.user = make_user("admin")
        tokens = {"access_token": "access", "refresh_token": "refresh"}

        with (
            patch.object(auth_router, "UserRepository", FakeUserRepository),
            patch.object(
                auth_router.auth_handler,
                "encode_login_token",
                return_value=tokens,
            ),
        ):
            result = await auth_router.admin_login(self.login_info, session=object())

        self.assertEqual("admin", result["user"].role)
        self.assertEqual("access", result["access_token"])
        self.assertEqual("refresh", result["refresh_token"])

    async def test_admin_login_rejects_normal_user(self):
        FakeUserRepository.user = make_user("user")

        with (
            patch.object(auth_router, "UserRepository", FakeUserRepository),
            patch.object(auth_router.auth_handler, "encode_login_token") as encode_token,
        ):
            with self.assertRaises(HTTPException) as context:
                await auth_router.admin_login(self.login_info, session=object())

        self.assertEqual(403, context.exception.status_code)
        self.assertEqual(
            "该账号不是管理员，请使用普通用户登录入口",
            context.exception.detail,
        )
        encode_token.assert_not_called()

    async def test_normal_login_accepts_normal_user(self):
        FakeUserRepository.user = make_user("user")
        tokens = {"access_token": "access", "refresh_token": "refresh"}

        with (
            patch.object(auth_router, "UserRepository", FakeUserRepository),
            patch.object(
                auth_router.auth_handler,
                "encode_login_token",
                return_value=tokens,
            ),
        ):
            result = await auth_router.login(self.login_info, session=object())

        self.assertEqual("user", result["user"].role)
        self.assertEqual("access", result["access_token"])


if __name__ == "__main__":
    unittest.main()

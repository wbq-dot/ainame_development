import secrets
from datetime import datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.User import User
from models.account_security import AccountDeletionJob


class AccountNotFound(Exception):
    pass


class AccountPasswordInvalid(Exception):
    pass


class AccountEmailConflict(Exception):
    pass


class AccountEmailUnchanged(Exception):
    pass


class AdminSelfDeletionForbidden(Exception):
    pass


class AccountRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def validate_email_target(self, user_id: int, new_email: str) -> User:
        async with self.session.begin():
            user = await self.session.get(User, user_id)
            if not user or user.status != "active":
                raise AccountNotFound("账号不存在或已失效")
            if user.email.lower() == new_email.lower():
                raise AccountEmailUnchanged("新邮箱不能与当前绑定邮箱相同")
            existing_id = await self.session.scalar(
                select(User.id).where(
                    func.lower(User.email) == new_email.lower(),
                    User.id != user_id,
                )
            )
            if existing_id is not None:
                raise AccountEmailConflict("该邮箱已被其他账号使用")
            return user

    async def change_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str,
    ) -> None:
        async with self.session.begin():
            user = await self.session.scalar(
                select(User).where(User.id == user_id).with_for_update()
            )
            if not user or user.status != "active":
                raise AccountNotFound("账号不存在或已失效")
            if not user.check_password(current_password):
                raise AccountPasswordInvalid("原密码错误，请重新输入")
            if user.check_password(new_password):
                raise AccountPasswordInvalid("新密码不能与原密码相同")

            user.password = new_password
            user.auth_version += 1
            user.updated_at = datetime.now()
            await self.session.flush()

    async def change_email(self, user_id: int, new_email: str) -> None:
        try:
            async with self.session.begin():
                user = await self.session.scalar(
                    select(User).where(User.id == user_id).with_for_update()
                )
                if not user or user.status != "active":
                    raise AccountNotFound("账号不存在或已失效")
                if user.email.lower() == new_email.lower():
                    raise AccountEmailUnchanged("新邮箱不能与当前绑定邮箱相同")
                existing_id = await self.session.scalar(
                    select(User.id).where(
                        func.lower(User.email) == new_email.lower(),
                        User.id != user_id,
                    )
                )
                if existing_id is not None:
                    raise AccountEmailConflict("该邮箱已被其他账号使用")

                user.email = new_email
                user.auth_version += 1
                user.updated_at = datetime.now()
                await self.session.flush()
        except IntegrityError as exc:
            raise AccountEmailConflict("该邮箱已被其他账号使用") from exc

    async def soft_delete_self(self, user_id: int) -> None:
        async with self.session.begin():
            user = await self.session.scalar(
                select(User).where(User.id == user_id).with_for_update()
            )
            if not user or user.status != "active":
                raise AccountNotFound("账号不存在或已失效")
            if user.role == "admin":
                raise AdminSelfDeletionForbidden("管理员账号不能自助注销")

            now = datetime.now()
            user.status = "deleted"
            user.email = f"deleted_{user.id}_{uuid4().hex}@deleted.local"
            user.username = f"已删除用户{user.id}"
            user.password = secrets.token_urlsafe(32)
            user.auth_version += 1
            user.frozen_at = None
            user.deleted_at = now
            user.updated_at = now

            self.session.add(
                AccountDeletionJob(
                    user_id=user.id,
                    status="pending",
                    attempts=0,
                    next_retry_at=now,
                    created_at=now,
                    updated_at=now,
                )
            )
            await self.session.flush()

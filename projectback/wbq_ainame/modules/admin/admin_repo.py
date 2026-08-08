import secrets
from datetime import datetime
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.User import User
from modules.admin.admin_action_log import AdminActionLog
from models.user_credit import UserCredit


class AdminTargetNotFound(Exception):
    pass


class AdminTargetForbidden(Exception):
    pass


class AdminStateConflict(Exception):
    pass


class AdminRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _to_dict(user: User, credit: UserCredit | None) -> dict:
        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "status": user.status,
            "balance": credit.balance if credit else 0,
            "total_used": credit.total_used if credit else 0,
            "total_recharge": credit.total_recharge if credit else 0,
            "logo_balance": credit.logo_balance if credit else 0,
            "logo_total_used": credit.logo_total_used if credit else 0,
            "logo_total_recharge": credit.logo_total_recharge if credit else 0,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "frozen_at": user.frozen_at,
            "deleted_at": user.deleted_at,
        }

    async def list_users(
        self,
        page: int,
        page_size: int,
        keyword: str | None = None,
        status: str | None = None,
    ) -> tuple[list[dict], int]:
        conditions = [User.role == "user"]
        if keyword:
            pattern = f"%{keyword.strip()}%"
            conditions.append(or_(User.email.ilike(pattern), User.username.ilike(pattern)))
        if status:
            conditions.append(User.status == status)

        async with self.session.begin():
            total = await self.session.scalar(
                select(func.count(User.id)).where(*conditions)
            )
            result = await self.session.execute(
                select(User, UserCredit)
                .outerjoin(UserCredit, UserCredit.user_id == User.id)
                .where(*conditions)
                .order_by(User.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            items = [self._to_dict(user, credit) for user, credit in result.all()]
        return items, int(total or 0)

    async def change_status(
        self,
        admin_user_id: int,
        target_user_id: int,
        target_status: str,
        reason: str | None,
    ) -> dict:
        async with self.session.begin():
            user = await self.session.scalar(
                select(User).where(User.id == target_user_id).with_for_update()
            )
            self._validate_target(user, admin_user_id)

            if target_status == "frozen":
                if user.status != "active":
                    raise AdminStateConflict("只有正常用户可以被冻结")
                user.status = "frozen"
                user.frozen_at = datetime.now()
                action = "freeze"
            elif target_status == "active":
                if user.status != "frozen":
                    raise AdminStateConflict("只有冻结用户可以被解冻")
                user.status = "active"
                user.frozen_at = None
                action = "unfreeze"
            else:
                raise AdminStateConflict("不支持的用户状态")

            user.updated_at = datetime.now()
            self.session.add(self._build_log(admin_user_id, user.id, action, reason))
            credit = await self.session.scalar(
                select(UserCredit).where(UserCredit.user_id == user.id)
            )
            await self.session.flush()
            return self._to_dict(user, credit)

    async def soft_delete_user(
        self,
        admin_user_id: int,
        target_user_id: int,
        reason: str | None,
    ) -> dict:
        async with self.session.begin():
            user = await self.session.scalar(
                select(User).where(User.id == target_user_id).with_for_update()
            )
            self._validate_target(user, admin_user_id)
            if user.status == "deleted":
                raise AdminStateConflict("用户已经被删除")

            now = datetime.now()
            user.status = "deleted"
            user.email = f"deleted_{user.id}_{uuid4().hex}@deleted.local"
            user.username = f"已删除用户{user.id}"
            user.password = secrets.token_urlsafe(32)
            user.frozen_at = None
            user.deleted_at = now
            user.updated_at = now

            self.session.add(self._build_log(admin_user_id, user.id, "delete", reason))
            credit = await self.session.scalar(
                select(UserCredit).where(UserCredit.user_id == user.id)
            )
            await self.session.flush()
            return self._to_dict(user, credit)

    @staticmethod
    def _validate_target(user: User | None, admin_user_id: int) -> None:
        if not user:
            raise AdminTargetNotFound("用户不存在")
        if user.id == admin_user_id or user.role == "admin":
            raise AdminTargetForbidden("不能操作自己或其他管理员")

    @staticmethod
    def _build_log(
        admin_user_id: int,
        target_user_id: int,
        action: str,
        reason: str | None,
    ) -> AdminActionLog:
        normalized_reason = reason.strip() if reason and reason.strip() else None
        return AdminActionLog(
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            action=action,
            reason=normalized_reason,
        )

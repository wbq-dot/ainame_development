import secrets
from datetime import datetime
from uuid import uuid4

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.User import User
from models.package import Package
from modules.admin.admin_action_log import AdminActionLog
from models.user_credit import CreditLog, UserCredit


class AdminTargetNotFound(Exception):
    pass


class AdminTargetForbidden(Exception):
    pass


class AdminStateConflict(Exception):
    pass


class AdminEmailConflict(Exception):
    pass


class AdminPackageNotFound(Exception):
    pass


class AdminRepository:
    BOOTSTRAP_LOCK_NAME = "ainame_admin_bootstrap"
    BOOTSTRAP_LOCK_TIMEOUT_SECONDS = 10

    def __init__(self, session: AsyncSession):
        self.session = session

    async def bootstrap_status(self) -> bool:
        admin_count = await self.session.scalar(
            select(func.count(User.id)).where(User.role == "admin")
        )
        return int(admin_count or 0) == 0

    async def bootstrap_admin(self, email: str, username: str, password: str) -> User:
        # MySQL 命名锁属于连接而非事务。使用独立连接持锁，确保锁覆盖业务事务
        # 的检查、写入和最终提交；业务事务结束后才释放锁。
        async with self.session.bind.connect() as lock_connection:
            lock_acquired = await lock_connection.scalar(
                text("SELECT GET_LOCK(:lock_name, :timeout_seconds)"),
                {
                    "lock_name": self.BOOTSTRAP_LOCK_NAME,
                    "timeout_seconds": self.BOOTSTRAP_LOCK_TIMEOUT_SECONDS,
                },
            )
            if lock_acquired != 1:
                raise AdminStateConflict("管理员初始化正在进行，请稍后重试")

            operation_failed = False
            try:
                async with self.session.begin():
                    admin_count = await self.session.scalar(
                        select(func.count(User.id)).where(User.role == "admin")
                    )
                    if int(admin_count or 0) > 0:
                        raise AdminStateConflict("系统已经完成管理员初始化")

                    existing = await self.session.scalar(
                        select(User).where(User.email == email)
                    )
                    if existing:
                        raise AdminEmailConflict("该邮箱已经存在")

                    user = User(
                        email=email,
                        username=username,
                        password=password,
                        role="admin",
                        status="active",
                    )
                    self.session.add(user)
                    await self.session.flush()
                    self.session.add(UserCredit(user_id=user.id, balance=0, logo_balance=0))
                    self.session.add(
                        self._build_log(
                            user.id,
                            user.id,
                            "bootstrap_admin",
                            "网页初始化首任管理员",
                        )
                    )
                    await self.session.flush()
                return user
            except BaseException:
                operation_failed = True
                raise
            finally:
                release_failed = False
                try:
                    lock_released = await lock_connection.scalar(
                        text("SELECT RELEASE_LOCK(:lock_name)"),
                        {"lock_name": self.BOOTSTRAP_LOCK_NAME},
                    )
                except BaseException:
                    release_failed = True
                else:
                    release_failed = lock_released != 1

                if release_failed:
                    # MySQL 命名锁属于连接；释放异常时销毁连接，避免锁随连接回到池中。
                    await lock_connection.invalidate()
                    if not operation_failed:
                        raise RuntimeError("管理员初始化数据库锁释放失败")

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

    async def list_packages(self) -> list[Package]:
        async with self.session.begin():
            result = await self.session.scalars(
                select(Package).order_by(Package.credit_type, Package.price, Package.id)
            )
            return list(result.all())

    async def change_package_status(
        self,
        admin_user_id: int,
        package_id: int,
        is_active: bool,
    ) -> tuple[Package, bool]:
        async with self.session.begin():
            package = await self.session.scalar(
                select(Package).where(Package.id == package_id).with_for_update()
            )
            if not package:
                raise AdminPackageNotFound("套餐不存在")
            if package.is_active == is_active:
                return package, False

            package.is_active = is_active
            action = "package_activate" if is_active else "package_deactivate"
            self.session.add(
                self._build_package_log(admin_user_id, package.id, action)
            )
            await self.session.flush()
            return package, True

    async def adjust_user_credit(
        self,
        admin_user_id: int,
        target_user_id: int,
        credit_type: str,
        change_count: int,
        reason: str,
    ) -> dict:
        if change_count == 0:
            raise AdminStateConflict("调整次数不能为 0")
        if not reason or not reason.strip():
            raise AdminStateConflict("调整原因不能为空")

        async with self.session.begin():
            user = await self.session.scalar(
                select(User).where(User.id == target_user_id).with_for_update()
            )
            self._validate_target(user, admin_user_id)
            if user.status not in {"active", "frozen"}:
                raise AdminStateConflict("只有正常或冻结用户可以调整余额")

            credit = await self.session.scalar(
                select(UserCredit)
                .where(UserCredit.user_id == target_user_id)
                .with_for_update()
            )
            if not credit:
                credit = UserCredit(
                    user_id=target_user_id,
                    balance=0,
                    total_used=0,
                    total_recharge=0,
                    logo_balance=0,
                    logo_total_used=0,
                    logo_total_recharge=0,
                )
                self.session.add(credit)

            if credit_type == "logo":
                balance_before = credit.logo_balance
            elif credit_type == "name":
                balance_before = credit.balance
            else:
                raise AdminStateConflict("不支持的余额类型")

            balance_after = balance_before + change_count
            if balance_after < 0:
                raise AdminStateConflict("调整后余额不能小于 0")
            if balance_after > 2147483647:
                raise AdminStateConflict("调整后余额超出允许范围")

            if credit_type == "logo":
                credit.logo_balance = balance_after
                credit_label = "Logo"
            else:
                credit.balance = balance_after
                credit_label = "起名"

            self.session.add(
                CreditLog(
                    user_id=target_user_id,
                    change_count=change_count,
                    balance_after=balance_after,
                    credit_type=credit_type,
                    type="admin_adjustment",
                    remark=f"管理员 {admin_user_id} 手动调整{credit_label}次数",
                )
            )
            self.session.add(
                self._build_log(
                    admin_user_id,
                    target_user_id,
                    f"adjust_{credit_type}_credit",
                    reason,
                )
            )
            await self.session.flush()
            return {
                "user": self._to_dict(user, credit),
                "credit_type": credit_type,
                "change_count": change_count,
                "balance_before": balance_before,
                "balance_after": balance_after,
            }

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
            target_package_id=None,
            action=action,
            reason=normalized_reason,
        )

    @staticmethod
    def _build_package_log(
        admin_user_id: int,
        target_package_id: int,
        action: str,
    ) -> AdminActionLog:
        return AdminActionLog(
            admin_user_id=admin_user_id,
            target_user_id=None,
            target_package_id=target_package_id,
            action=action,
            reason=None,
        )

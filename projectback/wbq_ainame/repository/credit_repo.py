from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user_credit import CreditLog, UserCredit
from models.account_security import NamingSession
from models.User import User


NAME_CREDIT_COST = 1
LOGO_CREDIT_COST = 1


class InactiveUserError(ValueError):
    pass


class CreditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_register_credit(
        self,
        user_id: int,
        gift_count: int = 3,
        logo_gift_count: int = 1,
    ) -> UserCredit:
        """创建双余额账户，并记录注册赠送流水。"""
        async with self.session.begin():
            credit = UserCredit(
                user_id=user_id,
                balance=gift_count,
                total_used=0,
                total_recharge=0,
                logo_balance=logo_gift_count,
                logo_total_used=0,
                logo_total_recharge=0,
            )
            self.session.add(credit)

            if gift_count:
                self.session.add(
                    CreditLog(
                        user_id=user_id,
                        change_count=gift_count,
                        balance_after=gift_count,
                        credit_type="name",
                        type="register_gift",
                        remark=f"注册赠送{gift_count}次起名机会",
                    )
                )
            if logo_gift_count:
                self.session.add(
                    CreditLog(
                        user_id=user_id,
                        change_count=logo_gift_count,
                        balance_after=logo_gift_count,
                        credit_type="logo",
                        type="register_gift",
                        remark=f"注册赠送{logo_gift_count}次Logo生成机会",
                    )
                )
            await self.session.flush()
            return credit

    async def get_balances(self, user_id: int) -> tuple[int, int]:
        async with self.session.begin():
            credit = await self.session.scalar(
                select(UserCredit).where(UserCredit.user_id == user_id)
            )
        if not credit:
            return 0, 0
        return credit.balance, credit.logo_balance

    async def get_balance(self, user_id: int) -> int:
        """兼容现有起名接口，只返回起名余额。"""
        name_balance, _ = await self.get_balances(user_id)
        return name_balance

    async def consume_name_credit(
        self,
        user_id: int,
        thread_id: str | None = None,
    ) -> int:
        return await self._consume_credit(
            user_id=user_id,
            credit_type="name",
            amount=NAME_CREDIT_COST,
            log_type="name_consume",
            remark="起名消耗1次",
            thread_id=thread_id,
            require_active_user=True,
        )

    async def consume_logo_credit(self, user_id: int) -> int:
        return await self._consume_credit(
            user_id=user_id,
            credit_type="logo",
            amount=LOGO_CREDIT_COST,
            log_type="logo_consume",
            remark="Logo生成预扣1次",
        )

    async def refund_logo_credit(self, user_id: int) -> int:
        """Logo 生成失败时退回预扣次数，并冲回累计使用量。"""
        async with self.session.begin():
            credit = await self.session.scalar(
                select(UserCredit)
                .where(UserCredit.user_id == user_id)
                .with_for_update()
            )
            if not credit:
                raise ValueError("用户次数账户不存在")

            credit.logo_balance += LOGO_CREDIT_COST
            credit.logo_total_used = max(
                0, credit.logo_total_used - LOGO_CREDIT_COST
            )
            self.session.add(
                CreditLog(
                    user_id=user_id,
                    change_count=LOGO_CREDIT_COST,
                    balance_after=credit.logo_balance,
                    credit_type="logo",
                    type="logo_refund",
                    remark="Logo生成失败，退回1次",
                )
            )
            await self.session.flush()
            return credit.logo_balance

    async def _consume_credit(
        self,
        user_id: int,
        credit_type: str,
        amount: int,
        log_type: str,
        remark: str,
        thread_id: str | None = None,
        require_active_user: bool = False,
    ) -> int:
        async with self.session.begin():
            if require_active_user:
                user = await self.session.scalar(
                    select(User).where(User.id == user_id).with_for_update()
                )
                if not user or user.status != "active":
                    raise InactiveUserError("账号已失效")
            credit = await self.session.scalar(
                select(UserCredit)
                .where(UserCredit.user_id == user_id)
                .with_for_update()
            )
            if not credit:
                raise ValueError("用户次数账户不存在")

            if credit_type == "logo":
                if credit.logo_balance < amount:
                    raise ValueError("Logo次数不足")
                credit.logo_balance -= amount
                credit.logo_total_used += amount
                balance_after = credit.logo_balance
            else:
                if credit.balance < amount:
                    raise ValueError("起名次数不足")
                credit.balance -= amount
                credit.total_used += amount
                balance_after = credit.balance

            self.session.add(
                CreditLog(
                    user_id=user_id,
                    change_count=-amount,
                    balance_after=balance_after,
                    credit_type=credit_type,
                    type=log_type,
                    remark=remark,
                )
            )
            if thread_id:
                self.session.add(
                    NamingSession(user_id=user_id, thread_id=thread_id)
                )
            await self.session.flush()
            return balance_after

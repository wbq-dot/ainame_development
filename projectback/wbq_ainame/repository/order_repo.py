from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select, update

import settings
from models.package import Package
from models.user_credit import CreditLog, UserCredit
from models.user_order import UserOrder

class PackageUnavailableError(Exception):
    pass


class OrderRepo:
    def __init__(self, session):
        self.session = session

    @staticmethod
    def create_order_no() -> str:
        return uuid4().hex

    async def create_order(
        self, user_id: int, package_id: int
    ) -> tuple[UserOrder, Package]:
        now = datetime.now()
        async with self.session.begin():
            # 套餐状态校验和订单写入必须在同一事务内，并与管理员上下架共用行锁。
            package = await self.session.scalar(
                select(Package).where(Package.id == package_id).with_for_update()
            )
            if not package or not package.is_active:
                raise PackageUnavailableError("套餐不存在或已下架")

            order = UserOrder(
                order_no=self.create_order_no(),
                user_id=user_id,
                package_id=package.id,
                amount=package.price,
                credit_count=package.credit_count,
                credit_type=package.credit_type,
                status="pending",
                created_at=now,
                expires_at=now
                + timedelta(minutes=settings.PAYMENT_ORDER_TIMEOUT_MINUTES),
                next_reconcile_at=now + timedelta(seconds=30),
            )
            self.session.add(order)
            await self.session.flush()
            return order, package

    async def get_by_order_no(
        self, order_no: str, user_id: int | None = None
    ) -> UserOrder | None:
        conditions = [UserOrder.order_no == order_no]
        if user_id is not None:
            conditions.append(UserOrder.user_id == user_id)
        async with self.session.begin():
            return await self.session.scalar(select(UserOrder).where(*conditions))

    async def delete_expired_pending_orders(self) -> int:
        """兼容旧调用：保留订单并把过期待支付订单标记为关闭。"""
        async with self.session.begin():
            result = await self.session.execute(
                update(UserOrder)
                .where(
                    UserOrder.status == "pending",
                    UserOrder.expires_at <= func.now(),
                )
                .values(status="closed", closed_at=func.now())
            )
            rowcount = result.rowcount
            return rowcount if rowcount is not None and rowcount > 0 else 0

    async def pay_success(self, order_no: str, alipay_trade_no: str):
        """原子入账；保留原公开返回值以兼容现有调用和测试。"""
        async with self.session.begin():
            order = await self.session.scalar(
                select(UserOrder)
                .where(UserOrder.order_no == order_no)
                .with_for_update()
            )
            if not order:
                raise ValueError("订单不存在")

            existing_trade_no = getattr(order, "alipay_trade_no", None)
            if order.status == "paid":
                if existing_trade_no and existing_trade_no != alipay_trade_no:
                    raise ValueError("订单已绑定其他支付宝交易号")
                return order, False
            if order.status != "pending":
                raise ValueError("订单状态异常")
            if not alipay_trade_no:
                raise ValueError("支付宝交易号不能为空")

            order.status = "paid"
            order.alipay_trade_no = alipay_trade_no
            order.paid_at = datetime.now()
            order.last_reconcile_error = None

            credit: UserCredit | None = await self.session.scalar(
                select(UserCredit)
                .where(UserCredit.user_id == order.user_id)
                .with_for_update()
            )
            if not credit:
                raise ValueError("用户次数账户不存在")

            if order.credit_type == "logo":
                credit.logo_balance += order.credit_count
                credit.logo_total_recharge += order.credit_count
                balance_after = credit.logo_balance
                credit_label = "Logo"
            else:
                credit.balance += order.credit_count
                credit.total_recharge += order.credit_count
                balance_after = credit.balance
                credit_label = "起名"

            self.session.add(
                CreditLog(
                    user_id=order.user_id,
                    change_count=order.credit_count,
                    balance_after=balance_after,
                    credit_type=order.credit_type,
                    type="recharge",
                    remark=f"支付成功，充值{order.credit_count}次{credit_label}次数",
                    source_type="payment_credit",
                    source_id=order_no,
                )
            )
            return order, True

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

import settings
from models.User import User
from models.payment_refund import OrderRefund
from models.user_credit import CreditLog, UserCredit
from models.user_order import UserOrder
from models.admin_action_log import AdminActionLog


class PaymentNotFound(ValueError):
    pass


class PaymentConflict(ValueError):
    pass


class RefundNotEligible(ValueError):
    pass


ACTIVE_REFUND_STATUSES = ("requested", "processing")


def retry_delay(attempts: int) -> timedelta:
    minutes = (1, 5, 15, 30, 60)[min(max(attempts - 1, 0), 4)]
    return timedelta(minutes=minutes)


class PaymentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _refund_dict(
        refund: OrderRefund,
        order_no: str,
        email: str | None = None,
        username: str | None = None,
    ) -> dict:
        return {
            "refund_no": refund.refund_no,
            "order_no": order_no,
            "user_id": refund.user_id,
            "email": email,
            "username": username,
            "origin": refund.origin,
            "status": refund.status,
            "reason": refund.reason,
            "review_note": refund.review_note,
            "amount": refund.amount,
            "credit_count": refund.credit_count,
            "credit_type": refund.credit_type,
            "last_error": refund.last_error,
            "created_at": refund.created_at,
            "reviewed_at": refund.reviewed_at,
            "completed_at": refund.completed_at,
        }

    @staticmethod
    def _refund_deadline(order: UserOrder) -> datetime | None:
        if not order.paid_at:
            return None
        return order.paid_at + timedelta(hours=settings.REFUND_WINDOW_HOURS)

    @classmethod
    def _order_dict(
        cls,
        order: UserOrder,
        latest_refund: OrderRefund | None,
        now: datetime | None = None,
    ) -> dict:
        now = now or datetime.now()
        deadline = cls._refund_deadline(order)
        active_refund = latest_refund and latest_refund.status in ACTIVE_REFUND_STATUSES
        eligible = bool(
            order.status == "paid"
            and deadline
            and now <= deadline
            and not active_refund
            and (not latest_refund or latest_refund.status != "succeeded")
        )
        reason = None
        if not eligible:
            if order.status != "paid":
                reason = "当前订单状态不可退款"
            elif deadline and now > deadline:
                reason = "已超过24小时退款申请期限"
            elif active_refund:
                reason = "已有退款正在处理"
            elif latest_refund and latest_refund.status == "succeeded":
                reason = "订单已经退款"
        return {
            "order_no": order.order_no,
            "amount": order.amount,
            "credit_count": order.credit_count,
            "credit_type": order.credit_type,
            "status": order.status,
            "created_at": order.created_at,
            "expires_at": order.expires_at,
            "paid_at": order.paid_at,
            "closed_at": order.closed_at,
            "refund_eligible": eligible,
            "refund_deadline": deadline,
            "refund_ineligible_reason": reason,
            "latest_refund": (
                cls._refund_dict(latest_refund, order.order_no)
                if latest_refund
                else None
            ),
        }

    async def _latest_refund(self, order_id: int) -> OrderRefund | None:
        return await self.session.scalar(
            select(OrderRefund)
            .where(OrderRefund.order_id == order_id)
            .order_by(OrderRefund.id.desc())
            .limit(1)
        )

    async def list_user_orders(
        self, user_id: int, page: int, page_size: int
    ) -> tuple[list[dict], int]:
        async with self.session.begin():
            total = await self.session.scalar(
                select(func.count(UserOrder.id)).where(UserOrder.user_id == user_id)
            )
            orders = list(
                (
                    await self.session.scalars(
                        select(UserOrder)
                        .where(UserOrder.user_id == user_id)
                        .order_by(UserOrder.id.desc())
                        .offset((page - 1) * page_size)
                        .limit(page_size)
                    )
                ).all()
            )
            items = []
            for order in orders:
                items.append(self._order_dict(order, await self._latest_refund(order.id)))
        return items, int(total or 0)

    async def get_user_order(self, order_no: str, user_id: int) -> dict:
        async with self.session.begin():
            order = await self.session.scalar(
                select(UserOrder).where(
                    UserOrder.order_no == order_no,
                    UserOrder.user_id == user_id,
                )
            )
            if not order:
                raise PaymentNotFound("订单不存在")
            return self._order_dict(order, await self._latest_refund(order.id))

    async def create_refund_request(
        self, order_no: str, user_id: int, reason: str
    ) -> dict:
        now = datetime.now()
        async with self.session.begin():
            order = await self.session.scalar(
                select(UserOrder)
                .where(
                    UserOrder.order_no == order_no,
                    UserOrder.user_id == user_id,
                )
                .with_for_update()
            )
            if not order:
                raise PaymentNotFound("订单不存在")
            if order.status != "paid" or not order.paid_at:
                raise RefundNotEligible("只有已支付订单可以申请退款")
            if now > self._refund_deadline(order):
                raise RefundNotEligible("已超过24小时退款申请期限")
            active = await self.session.scalar(
                select(OrderRefund.id).where(
                    OrderRefund.order_id == order.id,
                    OrderRefund.status.in_(ACTIVE_REFUND_STATUSES),
                )
            )
            if active:
                raise PaymentConflict("该订单已有退款正在处理")
            succeeded = await self.session.scalar(
                select(OrderRefund.id).where(
                    OrderRefund.order_id == order.id,
                    OrderRefund.status == "succeeded",
                )
            )
            if succeeded:
                raise PaymentConflict("该订单已经退款")
            credit = await self.session.scalar(
                select(UserCredit)
                .where(UserCredit.user_id == user_id)
                .with_for_update()
            )
            if not credit:
                raise RefundNotEligible("用户次数账户不存在")
            balance = credit.logo_balance if order.credit_type == "logo" else credit.balance
            if balance < order.credit_count:
                raise RefundNotEligible("当前同类次数余额不足，不能申请整单退款")

            refund = OrderRefund(
                refund_no=f"rf_{uuid4().hex}",
                order_id=order.id,
                user_id=user_id,
                origin="user_request",
                status="requested",
                reason=reason,
                amount=order.amount,
                credit_count=order.credit_count,
                credit_type=order.credit_type,
                alipay_trade_no=order.alipay_trade_no,
                created_at=now,
                updated_at=now,
            )
            self.session.add(refund)
            await self.session.flush()
            return self._refund_dict(refund, order.order_no)

    async def list_admin_refunds(
        self,
        page: int,
        page_size: int,
        status: str | None,
        keyword: str | None,
    ) -> tuple[list[dict], int]:
        conditions = []
        if status:
            conditions.append(OrderRefund.status == status)
        if keyword:
            pattern = f"%{keyword.strip()}%"
            conditions.append(
                or_(
                    OrderRefund.refund_no.ilike(pattern),
                    UserOrder.order_no.ilike(pattern),
                    User.email.ilike(pattern),
                )
            )
        async with self.session.begin():
            joined = (
                select(OrderRefund, UserOrder, User)
                .join(UserOrder, UserOrder.id == OrderRefund.order_id)
                .join(User, User.id == OrderRefund.user_id)
                .where(*conditions)
            )
            total = await self.session.scalar(
                select(func.count(OrderRefund.id))
                .join(UserOrder, UserOrder.id == OrderRefund.order_id)
                .join(User, User.id == OrderRefund.user_id)
                .where(*conditions)
            )
            rows = (
                await self.session.execute(
                    joined.order_by(OrderRefund.id.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
            items = [
                self._refund_dict(refund, order.order_no, user.email, user.username)
                for refund, order, user in rows
            ]
        return items, int(total or 0)

    @staticmethod
    def _admin_log(
        admin_user_id: int, refund: OrderRefund, action: str, reason: str | None
    ) -> AdminActionLog:
        return AdminActionLog(
            admin_user_id=admin_user_id,
            target_user_id=refund.user_id,
            action=action,
            reason=(reason or refund.refund_no)[:200],
        )

    @staticmethod
    def _reserve_credit(
        credit: UserCredit, refund: OrderRefund, reservation_key: str
    ) -> CreditLog:
        if refund.credit_type == "logo":
            if credit.logo_balance < refund.credit_count:
                raise RefundNotEligible("用户Logo次数余额不足")
            credit.logo_balance -= refund.credit_count
            balance_after = credit.logo_balance
        else:
            if credit.balance < refund.credit_count:
                raise RefundNotEligible("用户起名次数余额不足")
            credit.balance -= refund.credit_count
            balance_after = credit.balance
        refund.reserved_credit_count = refund.credit_count
        refund.reservation_key = reservation_key
        return CreditLog(
            user_id=refund.user_id,
            change_count=-refund.credit_count,
            balance_after=balance_after,
            credit_type=refund.credit_type,
            type="refund_reserve",
            remark=f"退款审批，暂扣{refund.credit_count}次权益",
            source_type="refund_reserve",
            source_id=reservation_key,
        )

    async def approve_refund(
        self, refund_no: str, admin_user_id: int, note: str | None
    ) -> tuple[dict, bool]:
        now = datetime.now()
        async with self.session.begin():
            refund = await self.session.scalar(
                select(OrderRefund)
                .where(OrderRefund.refund_no == refund_no)
                .with_for_update()
            )
            if not refund:
                raise PaymentNotFound("退款申请不存在")
            if refund.status != "requested":
                raise PaymentConflict("只有待审核退款可以审批")
            order = await self.session.get(UserOrder, refund.order_id, with_for_update=True)
            credit = await self.session.scalar(
                select(UserCredit)
                .where(UserCredit.user_id == refund.user_id)
                .with_for_update()
            )
            if not order or not credit or order.status != "paid":
                refund.status = "rejected"
                refund.review_note = "订单或次数账户状态已变化，系统自动驳回"
                refund.reviewed_by = admin_user_id
                refund.reviewed_at = now
                self.session.add(self._admin_log(admin_user_id, refund, "reject_refund", refund.review_note))
                return self._refund_dict(refund, order.order_no if order else ""), False

            balance = credit.logo_balance if refund.credit_type == "logo" else credit.balance
            if balance < refund.credit_count:
                refund.status = "rejected"
                refund.review_note = "审批时同类次数余额不足，系统自动驳回"
                refund.reviewed_by = admin_user_id
                refund.reviewed_at = now
                self.session.add(self._admin_log(admin_user_id, refund, "reject_refund", refund.review_note))
                return self._refund_dict(refund, order.order_no), False

            reservation_key = f"{refund.refund_no}:1"
            self.session.add(self._reserve_credit(credit, refund, reservation_key))
            refund.status = "processing"
            refund.reviewed_by = admin_user_id
            refund.review_note = note.strip() if note and note.strip() else None
            refund.reviewed_at = now
            refund.next_retry_at = now
            refund.last_error = None
            order.status = "refunding"
            self.session.add(self._admin_log(admin_user_id, refund, "approve_refund", note))
            return self._refund_dict(refund, order.order_no), True

    async def reject_refund(
        self, refund_no: str, admin_user_id: int, reason: str
    ) -> dict:
        now = datetime.now()
        async with self.session.begin():
            refund = await self.session.scalar(
                select(OrderRefund)
                .where(OrderRefund.refund_no == refund_no)
                .with_for_update()
            )
            if not refund:
                raise PaymentNotFound("退款申请不存在")
            if refund.status != "requested":
                raise PaymentConflict("只有待审核退款可以驳回")
            order = await self.session.get(UserOrder, refund.order_id)
            refund.status = "rejected"
            refund.reviewed_by = admin_user_id
            refund.review_note = reason
            refund.reviewed_at = now
            self.session.add(self._admin_log(admin_user_id, refund, "reject_refund", reason))
            return self._refund_dict(refund, order.order_no)

    async def retry_refund(self, refund_no: str, admin_user_id: int) -> dict:
        now = datetime.now()
        async with self.session.begin():
            refund = await self.session.scalar(
                select(OrderRefund)
                .where(OrderRefund.refund_no == refund_no)
                .with_for_update()
            )
            if not refund:
                raise PaymentNotFound("退款申请不存在")
            order = await self.session.get(UserOrder, refund.order_id, with_for_update=True)
            if refund.status == "processing":
                refund.next_retry_at = now
                refund.last_error = None
            elif refund.status == "failed":
                if refund.origin == "user_request" and refund.reserved_credit_count == 0:
                    credit = await self.session.scalar(
                        select(UserCredit)
                        .where(UserCredit.user_id == refund.user_id)
                        .with_for_update()
                    )
                    if not credit:
                        raise RefundNotEligible("用户次数账户不存在")
                    key = f"{refund.refund_no}:retry:{refund.attempts + 1}"
                    self.session.add(self._reserve_credit(credit, refund, key))
                refund.status = "processing"
                refund.next_retry_at = now
                refund.last_error = None
                order.status = "refunding"
            else:
                raise PaymentConflict("当前退款状态不能重试")
            self.session.add(self._admin_log(admin_user_id, refund, "retry_refund", None))
            return self._refund_dict(refund, order.order_no)

    async def record_payment_success(
        self, order_no: str, trade_no: str
    ) -> tuple[str, OrderRefund | None]:
        now = datetime.now()
        async with self.session.begin():
            order = await self.session.scalar(
                select(UserOrder)
                .where(UserOrder.order_no == order_no)
                .with_for_update()
            )
            if not order:
                raise PaymentNotFound("订单不存在")
            if order.alipay_trade_no and order.alipay_trade_no != trade_no:
                raise PaymentConflict("订单已绑定其他支付宝交易号")
            if order.status in {"paid", "refunding", "refunded"}:
                return "duplicate", await self._latest_refund(order.id)

            order.alipay_trade_no = trade_no
            order.paid_at = order.paid_at or now
            order.last_reconcile_error = None
            if order.status == "closed":
                refund = await self.session.scalar(
                    select(OrderRefund)
                    .where(
                        OrderRefund.order_id == order.id,
                        OrderRefund.origin == "late_payment",
                    )
                    .order_by(OrderRefund.id.desc())
                    .limit(1)
                )
                if not refund:
                    refund = OrderRefund(
                        refund_no=f"rf_{uuid4().hex}",
                        order_id=order.id,
                        user_id=order.user_id,
                        origin="late_payment",
                        status="processing",
                        reason="订单超时关闭后确认付款，系统自动退款",
                        amount=order.amount,
                        credit_count=order.credit_count,
                        credit_type=order.credit_type,
                        alipay_trade_no=trade_no,
                        next_retry_at=now,
                        created_at=now,
                        updated_at=now,
                    )
                    self.session.add(refund)
                    await self.session.flush()
                order.status = "refunding"
                return "late_refund", refund

            if order.status != "pending":
                raise PaymentConflict("订单状态异常")
            await self._credit_order_locked(order, "payment_credit", order.order_no)
            order.status = "paid"
            return "credited", None

    async def _credit_order_locked(
        self, order: UserOrder, source_type: str, source_id: str
    ) -> None:
        credit = await self.session.scalar(
            select(UserCredit)
            .where(UserCredit.user_id == order.user_id)
            .with_for_update()
        )
        if not credit:
            raise PaymentConflict("用户次数账户不存在")
        if order.credit_type == "logo":
            credit.logo_balance += order.credit_count
            credit.logo_total_recharge += order.credit_count
            balance_after = credit.logo_balance
            label = "Logo"
        else:
            credit.balance += order.credit_count
            credit.total_recharge += order.credit_count
            balance_after = credit.balance
            label = "起名"
        if source_type == "late_payment_fallback":
            remark = (
                f"超时付款自动退款被拒绝，按原订单发放{order.credit_count}次{label}次数"
            )
        else:
            remark = f"支付成功，充值{order.credit_count}次{label}次数"
        self.session.add(
            CreditLog(
                user_id=order.user_id,
                change_count=order.credit_count,
                balance_after=balance_after,
                credit_type=order.credit_type,
                type=source_type,
                remark=remark,
                source_type=source_type,
                source_id=source_id,
            )
        )

    async def record_provider_closed(self, order_no: str) -> bool:
        now = datetime.now()
        async with self.session.begin():
            order = await self.session.scalar(
                select(UserOrder)
                .where(UserOrder.order_no == order_no)
                .with_for_update()
            )
            if not order:
                raise PaymentNotFound("订单不存在")
            if order.status != "pending":
                return False
            order.status = "closed"
            order.closed_at = now
            order.next_reconcile_at = None
            return True

    async def claim_due_orders(self, limit: int) -> list[str]:
        now = datetime.now()
        lease_until = now + timedelta(minutes=2)
        async with self.session.begin():
            orders = list(
                (
                    await self.session.scalars(
                        select(UserOrder)
                        .where(
                            UserOrder.status == "pending",
                            or_(
                                UserOrder.next_reconcile_at.is_(None),
                                UserOrder.next_reconcile_at <= now,
                            ),
                        )
                        .order_by(UserOrder.id)
                        .with_for_update(skip_locked=True)
                        .limit(limit)
                    )
                ).all()
            )
            for order in orders:
                order.next_reconcile_at = lease_until
                order.reconcile_attempts += 1
            return [order.order_no for order in orders]

    async def get_order_for_reconcile(self, order_no: str) -> UserOrder | None:
        async with self.session.begin():
            return await self.session.scalar(
                select(UserOrder).where(UserOrder.order_no == order_no)
            )

    async def schedule_order_retry(self, order_no: str, error: str) -> None:
        async with self.session.begin():
            order = await self.session.scalar(
                select(UserOrder)
                .where(UserOrder.order_no == order_no)
                .with_for_update()
            )
            if order and order.status == "pending":
                order.last_reconcile_error = error[:1000]
                order.next_reconcile_at = datetime.now() + retry_delay(
                    order.reconcile_attempts
                )

    async def claim_due_refunds(self, limit: int) -> list[str]:
        now = datetime.now()
        lease_until = now + timedelta(minutes=2)
        async with self.session.begin():
            refunds = list(
                (
                    await self.session.scalars(
                        select(OrderRefund)
                        .where(
                            OrderRefund.status == "processing",
                            or_(
                                OrderRefund.next_retry_at.is_(None),
                                OrderRefund.next_retry_at <= now,
                            ),
                        )
                        .order_by(OrderRefund.id)
                        .with_for_update(skip_locked=True)
                        .limit(limit)
                    )
                ).all()
            )
            for refund in refunds:
                refund.next_retry_at = lease_until
                refund.attempts += 1
            return [refund.refund_no for refund in refunds]

    async def get_refund_for_processing(
        self, refund_no: str
    ) -> tuple[OrderRefund, UserOrder] | None:
        async with self.session.begin():
            row = (
                await self.session.execute(
                    select(OrderRefund, UserOrder)
                    .join(UserOrder, UserOrder.id == OrderRefund.order_id)
                    .where(OrderRefund.refund_no == refund_no)
                )
            ).first()
            return row if row else None

    async def finalize_refund_success(
        self, refund_no: str, refund_fee: Decimal | None
    ) -> None:
        now = datetime.now()
        async with self.session.begin():
            refund = await self.session.scalar(
                select(OrderRefund)
                .where(OrderRefund.refund_no == refund_no)
                .with_for_update()
            )
            if not refund or refund.status == "succeeded":
                return
            order = await self.session.get(UserOrder, refund.order_id, with_for_update=True)
            if refund.origin == "user_request":
                credit = await self.session.scalar(
                    select(UserCredit)
                    .where(UserCredit.user_id == refund.user_id)
                    .with_for_update()
                )
                if not credit:
                    raise PaymentConflict("用户次数账户不存在")
                if refund.credit_type == "logo":
                    credit.logo_total_refund += refund.credit_count
                else:
                    credit.total_refund += refund.credit_count
            refund.status = "succeeded"
            refund.provider_refund_fee = refund_fee or refund.amount
            refund.completed_at = now
            refund.next_retry_at = None
            refund.last_error = None
            order.status = "refunded"

    async def finalize_refund_failure(self, refund_no: str, error: str) -> None:
        now = datetime.now()
        async with self.session.begin():
            refund = await self.session.scalar(
                select(OrderRefund)
                .where(OrderRefund.refund_no == refund_no)
                .with_for_update()
            )
            if not refund or refund.status != "processing":
                return
            order = await self.session.get(UserOrder, refund.order_id, with_for_update=True)
            if refund.origin == "late_payment":
                await self._credit_order_locked(
                    order, "late_payment_fallback", refund.refund_no
                )
                order.status = "paid"
            else:
                credit = await self.session.scalar(
                    select(UserCredit)
                    .where(UserCredit.user_id == refund.user_id)
                    .with_for_update()
                )
                if credit and refund.reserved_credit_count:
                    if refund.credit_type == "logo":
                        credit.logo_balance += refund.reserved_credit_count
                        balance_after = credit.logo_balance
                    else:
                        credit.balance += refund.reserved_credit_count
                        balance_after = credit.balance
                    self.session.add(
                        CreditLog(
                            user_id=refund.user_id,
                            change_count=refund.reserved_credit_count,
                            balance_after=balance_after,
                            credit_type=refund.credit_type,
                            type="refund_release",
                            remark="支付宝明确拒绝退款，退回暂扣次数",
                            source_type="refund_release",
                            source_id=refund.reservation_key or refund.refund_no,
                        )
                    )
                    refund.reserved_credit_count = 0
                order.status = "paid"
            refund.status = "failed"
            refund.last_error = error[:1000]
            refund.completed_at = now
            refund.next_retry_at = None

    async def schedule_refund_retry(self, refund_no: str, error: str) -> None:
        async with self.session.begin():
            refund = await self.session.scalar(
                select(OrderRefund)
                .where(OrderRefund.refund_no == refund_no)
                .with_for_update()
            )
            if refund and refund.status == "processing":
                refund.last_error = error[:1000]
                refund.next_retry_at = datetime.now() + retry_delay(refund.attempts)

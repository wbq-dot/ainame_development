from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

import settings
from core.platform_auth import issue_api_key
from models.platform_models import (
    ApiCallLog,
    ApiCreditLog,
    ApiOrder,
    ApiPackage,
    ApiRefund,
    ApiWallet,
    DeveloperAccount,
    DeveloperApiKey,
    PlatformAdminAudit,
    PlatformTask,
    PlatformTaskEvent,
    PlatformTaskItem,
    PromotionBalanceLog,
    ReferralCampaign,
    ReferralRelation,
    ReferralReward,
)


class PlatformConflict(ValueError):
    pass


class PlatformNotFound(ValueError):
    pass


def request_hash(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class PlatformRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_developer(self, email: str, name: str, password: str, referral_code: str | None) -> DeveloperAccount:
        now = datetime.now()
        async with self.session.begin():
            exists = await self.session.scalar(select(DeveloperAccount.id).where(DeveloperAccount.email == email.lower()))
            if exists:
                raise PlatformConflict("该邮箱已注册开发者账号")
            inviter = None
            campaign = None
            if referral_code:
                inviter = await self.session.scalar(
                    select(DeveloperAccount).where(
                        DeveloperAccount.referral_code == referral_code.upper(),
                        DeveloperAccount.status == "active",
                    )
                )
                if not inviter:
                    raise PlatformConflict("推广码无效")
                campaign = await self.session.scalar(
                    select(ReferralCampaign).where(
                        ReferralCampaign.is_active.is_(True),
                        ReferralCampaign.starts_at <= now,
                        ReferralCampaign.ends_at >= now,
                    )
                )
                if not campaign:
                    raise PlatformConflict("当前没有生效的邀请活动")
            developer = DeveloperAccount(
                email=email.lower(), name=name.strip(), password_hash="", status="active",
                referral_code=secrets.token_hex(5).upper(), rate_limit_per_minute=60,
            )
            developer.set_password(password)
            self.session.add(developer)
            await self.session.flush()
            self.session.add(ApiWallet(developer_id=developer.id))
            if inviter and campaign:
                self.session.add(
                    ReferralRelation(
                        inviter_id=inviter.id, invitee_id=developer.id, campaign_id=campaign.id,
                        commission_rate=campaign.commission_rate,
                        inviter_credit=campaign.inviter_credit, invitee_credit=campaign.invitee_credit,
                    )
                )
            await self.session.flush()
            return developer

    async def create_api_key(self, developer_id: int, name: str) -> tuple[DeveloperApiKey, str]:
        raw, prefix, digest = issue_api_key()
        async with self.session.begin():
            key = DeveloperApiKey(developer_id=developer_id, name=name.strip(), key_prefix=prefix, key_digest=digest)
            self.session.add(key)
            await self.session.flush()
        return key, raw

    async def list_api_keys(self, developer_id: int) -> list[DeveloperApiKey]:
        return list((await self.session.scalars(select(DeveloperApiKey).where(DeveloperApiKey.developer_id == developer_id).order_by(DeveloperApiKey.id.desc()))).all())

    async def update_api_key(self, developer_id: int, key_id: int, *, name: str | None = None, revoke: bool = False) -> DeveloperApiKey:
        async with self.session.begin():
            key = await self.session.scalar(select(DeveloperApiKey).where(DeveloperApiKey.id == key_id, DeveloperApiKey.developer_id == developer_id).with_for_update())
            if not key:
                raise PlatformNotFound("API Key 不存在")
            if name is not None:
                key.name = name.strip()
            if revoke:
                key.status = "revoked"
                key.revoked_at = datetime.now()
            await self.session.flush()
            return key

    async def regenerate_api_key(self, developer_id: int, key_id: int) -> tuple[DeveloperApiKey, str]:
        async with self.session.begin():
            old = await self.session.scalar(select(DeveloperApiKey).where(DeveloperApiKey.id == key_id, DeveloperApiKey.developer_id == developer_id).with_for_update())
            if not old:
                raise PlatformNotFound("API Key 不存在")
            old.status = "revoked"
            old.revoked_at = datetime.now()
            raw, prefix, digest = issue_api_key()
            new = DeveloperApiKey(developer_id=developer_id, name=old.name, key_prefix=prefix, key_digest=digest)
            self.session.add(new)
            await self.session.flush()
            return new, raw

    async def wallet(self, developer_id: int, lock: bool = False) -> ApiWallet:
        query = select(ApiWallet).where(ApiWallet.developer_id == developer_id)
        if lock:
            query = query.with_for_update()
        wallet = await self.session.scalar(query)
        if not wallet:
            raise PlatformNotFound("API 次数账户不存在")
        return wallet

    async def reserve_credits(self, developer_id: int, count: int, reference: str) -> int:
        async with self.session.begin():
            wallet = await self.wallet(developer_id, lock=True)
            if wallet.balance - wallet.reserved < count:
                raise PlatformConflict("API 调用次数不足")
            wallet.reserved += count
            return wallet.balance - wallet.reserved

    async def finalize_credits(self, developer_id: int, count: int, reference: str, log_type: str = "api_consume") -> int:
        async with self.session.begin():
            wallet = await self.wallet(developer_id, lock=True)
            count = min(count, wallet.reserved)
            wallet.reserved -= count
            wallet.balance -= count
            self.session.add(ApiCreditLog(developer_id=developer_id, change_count=-count, balance_after=wallet.balance, type=log_type, reference=reference))
            return wallet.balance

    async def release_credits(self, developer_id: int, count: int) -> int:
        async with self.session.begin():
            wallet = await self.wallet(developer_id, lock=True)
            wallet.reserved = max(0, wallet.reserved - count)
            return wallet.balance - wallet.reserved

    async def find_call(self, api_key_id: int, idem: str) -> ApiCallLog | None:
        return await self.session.scalar(select(ApiCallLog).where(ApiCallLog.api_key_id == api_key_id, ApiCallLog.idempotency_key == idem))

    async def create_call(self, developer_id: int, api_key_id: int, endpoint: str, idem: str, payload: dict) -> tuple[ApiCallLog, bool]:
        digest = request_hash(payload)
        try:
            async with self.session.begin():
                existing = await self.session.scalar(select(ApiCallLog).where(ApiCallLog.api_key_id == api_key_id, ApiCallLog.idempotency_key == idem).with_for_update())
                if existing:
                    if existing.request_hash != digest:
                        raise PlatformConflict("相同 Idempotency-Key 对应了不同请求")
                    return existing, False
                call = ApiCallLog(request_no=f"req_{uuid4().hex}", developer_id=developer_id, api_key_id=api_key_id, endpoint=endpoint, idempotency_key=idem, request_hash=digest, status="processing")
                self.session.add(call)
                await self.session.flush()
                return call, True
        except IntegrityError:
            await self.session.rollback()
            existing = await self.find_call(api_key_id, idem)
            if not existing or existing.request_hash != digest:
                raise PlatformConflict("相同 Idempotency-Key 对应了不同请求")
            return existing, False

    async def complete_call(self, call_id: int, *, status: str, response: dict | None, credits: int, duration_ms: int, error_type: str | None = None) -> ApiCallLog:
        async with self.session.begin():
            call = await self.session.get(ApiCallLog, call_id, with_for_update=True)
            call.status, call.response_data, call.credit_count = status, response, credits
            call.duration_ms, call.error_type, call.completed_at = duration_ms, error_type, datetime.now()
            await self.session.flush()
            return call

    async def create_task(self, *, task_type: str, owner_type: str, owner_id: int, total: int, payload: dict | None, api_key_id: int | None = None, reserved: int = 0, items: list[dict] | None = None) -> PlatformTask:
        async with self.session.begin():
            task = PlatformTask(task_no=f"task_{uuid4().hex}", task_type=task_type, owner_type=owner_type, owner_id=owner_id, api_key_id=api_key_id, total_count=total, payload=payload, reserved_credits=reserved)
            self.session.add(task)
            await self.session.flush()
            for index, item in enumerate(items or []):
                self.session.add(PlatformTaskItem(task_id=task.id, item_index=index, input_data=item))
            self.session.add(PlatformTaskEvent(task_id=task.id, status="queued", message="任务已创建"))
            await self.session.flush()
            return task

    async def task_detail(self, task_no: str, owner_type: str | None = None, owner_id: int | None = None) -> dict:
        filters = [PlatformTask.task_no == task_no]
        if owner_type is not None:
            filters += [PlatformTask.owner_type == owner_type, PlatformTask.owner_id == owner_id]
        task = await self.session.scalar(select(PlatformTask).where(*filters))
        if not task:
            raise PlatformNotFound("任务不存在")
        items = list((await self.session.scalars(select(PlatformTaskItem).where(PlatformTaskItem.task_id == task.id).order_by(PlatformTaskItem.item_index))).all())
        return {"task_no": task.task_no, "task_type": task.task_type, "status": task.status, "total_count": task.total_count, "success_count": task.success_count, "failure_count": task.failure_count, "attempts": task.attempts, "max_attempts": task.max_attempts, "last_error": task.last_error, "created_at": task.created_at, "started_at": task.started_at, "completed_at": task.completed_at, "items": items}

    async def list_tasks(self, *, owner_type: str | None = None, owner_id: int | None = None, task_type: str | None = None, status: str | None = None, page: int = 1, page_size: int = 20) -> tuple[list[PlatformTask], int]:
        filters = []
        if owner_type: filters.append(PlatformTask.owner_type == owner_type)
        if owner_id is not None: filters.append(PlatformTask.owner_id == owner_id)
        if task_type: filters.append(PlatformTask.task_type == task_type)
        if status: filters.append(PlatformTask.status == status)
        total = await self.session.scalar(select(func.count(PlatformTask.id)).where(*filters))
        items = list((await self.session.scalars(select(PlatformTask).where(*filters).order_by(PlatformTask.id.desc()).offset((page-1)*page_size).limit(page_size))).all())
        return items, int(total or 0)

    async def retry_task(self, task_no: str) -> PlatformTask:
        async with self.session.begin():
            task = await self.session.scalar(select(PlatformTask).where(PlatformTask.task_no == task_no).with_for_update())
            if not task:
                raise PlatformNotFound("任务不存在")
            if task.status in {"queued", "running"}:
                return task
            if task.status not in {"failed", "partial_failed", "publish_failed"}:
                raise PlatformConflict("当前任务状态不可重试")
            if task.task_type == "batch_naming" and task.status != "publish_failed" and task.reserved_credits == 0:
                retry_count = int(await self.session.scalar(select(func.count(PlatformTaskItem.id)).where(PlatformTaskItem.task_id == task.id, PlatformTaskItem.status == "failed")) or 0)
                wallet = await self.wallet(task.owner_id, lock=True)
                if wallet.balance - wallet.reserved < retry_count:
                    raise PlatformConflict("开发者可用次数不足，无法重试失败条目")
                wallet.reserved += retry_count
                task.reserved_credits = retry_count
            task.status, task.last_error, task.next_retry_at = "queued", None, None
            task.completed_at = None
            self.session.add(PlatformTaskEvent(task_id=task.id, status="queued", message="管理员重新入队"))
            return task

    async def list_packages(self, active_only: bool = True) -> list[ApiPackage]:
        query = select(ApiPackage)
        if active_only: query = query.where(ApiPackage.is_active.is_(True))
        return list((await self.session.scalars(query.order_by(ApiPackage.sort_order, ApiPackage.id))).all())

    async def save_package(self, data: dict, package_id: int | None = None) -> ApiPackage:
        async with self.session.begin():
            package = await self.session.get(ApiPackage, package_id, with_for_update=True) if package_id else ApiPackage()
            if package_id and not package: raise PlatformNotFound("API 套餐不存在")
            for key, value in data.items(): setattr(package, key, value)
            self.session.add(package)
            await self.session.flush()
            return package

    async def create_order(self, developer_id: int, package_id: int, use_promotion: bool) -> ApiOrder:
        now = datetime.now()
        async with self.session.begin():
            package = await self.session.scalar(select(ApiPackage).where(ApiPackage.id == package_id, ApiPackage.is_active.is_(True)).with_for_update())
            if not package: raise PlatformNotFound("API 套餐不存在或已下架")
            wallet = await self.wallet(developer_id, lock=True)
            promotion = min(Decimal(wallet.promotion_balance), Decimal(package.price)) if use_promotion else Decimal("0.00")
            cash = Decimal(package.price) - promotion
            if promotion:
                wallet.promotion_balance -= promotion
                self.session.add(PromotionBalanceLog(developer_id=developer_id, amount=-promotion, balance_after=wallet.promotion_balance, type="order_reserve", reference=None))
            order = ApiOrder(order_no=f"api_{uuid4().hex}", developer_id=developer_id, package_id=package.id, package_name=package.name, credit_count=package.credit_count, total_amount=package.price, promotion_amount=promotion, cash_amount=cash, status="pending")
            self.session.add(order)
            await self.session.flush()
            if promotion:
                log = await self.session.scalar(select(PromotionBalanceLog).where(PromotionBalanceLog.developer_id == developer_id).order_by(PromotionBalanceLog.id.desc()).limit(1))
                log.reference = order.order_no
            if cash == 0:
                await self._credit_paid_order(order, now, trade_no=None)
            return order

    async def _credit_paid_order(self, order: ApiOrder, now: datetime, trade_no: str | None) -> None:
        if order.status == "paid": return
        order.status, order.paid_at, order.alipay_trade_no = "paid", now, trade_no
        wallet = await self.wallet(order.developer_id, lock=True)
        wallet.balance += order.credit_count
        self.session.add(ApiCreditLog(developer_id=order.developer_id, change_count=order.credit_count, balance_after=wallet.balance, type="package_recharge", reference=order.order_no))
        relation = await self.session.scalar(select(ReferralRelation).where(ReferralRelation.invitee_id == order.developer_id))
        if relation and order.cash_amount > 0:
            prior = await self.session.scalar(select(ReferralReward.id).join(ApiOrder, ApiOrder.id == ReferralReward.order_id).where(ReferralReward.relation_id == relation.id))
            if not prior:
                amount = (Decimal(order.cash_amount) * Decimal(relation.commission_rate)).quantize(Decimal("0.01"))
                campaign = await self.session.get(ReferralCampaign, relation.campaign_id)
                if campaign and campaign.reward_cap is not None: amount = min(amount, Decimal(campaign.reward_cap))
                self.session.add(ReferralReward(relation_id=relation.id, order_id=order.id, commission_amount=amount, inviter_credit=relation.inviter_credit, invitee_credit=relation.invitee_credit, settle_after=now + timedelta(hours=settings.REFUND_WINDOW_HOURS)))

    async def record_order_paid(self, order_no: str, amount: Decimal, trade_no: str) -> None:
        async with self.session.begin():
            order = await self.session.scalar(select(ApiOrder).where(ApiOrder.order_no == order_no).with_for_update())
            if not order or Decimal(order.cash_amount) != Decimal(amount): raise PlatformConflict("开发者订单不存在或金额不一致")
            if order.status == "refunded": raise PlatformConflict("订单已经退款")
            if order.status == "closed":
                wallet = await self.wallet(order.developer_id, lock=True)
                if order.promotion_amount:
                    if wallet.promotion_balance < order.promotion_amount:
                        raise PlatformConflict("迟到支付订单的推广余额已被使用，需管理员人工处理")
                    wallet.promotion_balance -= order.promotion_amount
                    self.session.add(PromotionBalanceLog(developer_id=order.developer_id, amount=-order.promotion_amount, balance_after=wallet.promotion_balance, type="late_payment_reapply", reference=order.order_no))
            await self._credit_paid_order(order, datetime.now(), trade_no)

    async def list_orders(self, developer_id: int) -> list[ApiOrder]:
        return list((await self.session.scalars(select(ApiOrder).where(ApiOrder.developer_id == developer_id).order_by(ApiOrder.id.desc()))).all())

    async def request_refund(self, developer_id: int, order_no: str, reason: str) -> ApiRefund:
        async with self.session.begin():
            order = await self.session.scalar(select(ApiOrder).where(ApiOrder.order_no == order_no, ApiOrder.developer_id == developer_id).with_for_update())
            if not order or order.status != "paid" or not order.paid_at: raise PlatformConflict("只有已支付订单可以退款")
            if datetime.now() > order.paid_at + timedelta(hours=settings.REFUND_WINDOW_HOURS): raise PlatformConflict("已超过24小时退款申请期限")
            wallet = await self.wallet(developer_id, lock=True)
            if wallet.balance - wallet.reserved < order.credit_count: raise PlatformConflict("可用 API 次数不足，无法整单退款")
            active = await self.session.scalar(select(ApiRefund.id).where(ApiRefund.order_id == order.id, ApiRefund.status.in_(("requested", "processing", "succeeded"))))
            if active: raise PlatformConflict("该订单已有退款记录")
            refund = ApiRefund(refund_no=f"apirf_{uuid4().hex}", order_id=order.id, developer_id=developer_id, reason=reason)
            self.session.add(refund); await self.session.flush(); return refund

    async def finalize_refund(self, refund_no: str, admin_id: int, approve: bool, note: str | None) -> ApiRefund:
        async with self.session.begin():
            refund = await self.session.scalar(select(ApiRefund).where(ApiRefund.refund_no == refund_no).with_for_update())
            if not refund: raise PlatformNotFound("退款申请不存在")
            if refund.status != "requested": raise PlatformConflict("退款申请已处理")
            order = await self.session.get(ApiOrder, refund.order_id, with_for_update=True)
            refund.reviewed_by, refund.review_note, refund.reviewed_at = admin_id, note, datetime.now()
            if not approve:
                refund.status = "rejected"
                await self.audit(admin_id, "refund_reject", "api_refund", refund_no, note)
                return refund
            wallet = await self.wallet(order.developer_id, lock=True)
            if wallet.balance - wallet.reserved < order.credit_count: raise PlatformConflict("开发者可用次数不足，不能退款")
            wallet.balance -= order.credit_count
            wallet.promotion_balance += order.promotion_amount
            self.session.add(ApiCreditLog(developer_id=order.developer_id, change_count=-order.credit_count, balance_after=wallet.balance, type="order_refund", reference=order.order_no))
            if order.promotion_amount:
                self.session.add(PromotionBalanceLog(developer_id=order.developer_id, amount=order.promotion_amount, balance_after=wallet.promotion_balance, type="refund_restore", reference=order.order_no))
            reward = await self.session.scalar(select(ReferralReward).where(ReferralReward.order_id == order.id).with_for_update())
            if reward and reward.status == "pending": reward.status, reward.invalid_reason = "invalid", "首购订单已退款"
            order.status, order.refunded_at = "refunded", datetime.now()
            refund.status = "succeeded"
            await self.audit(admin_id, "refund_approve", "api_refund", refund_no, note)
            return refund

    async def list_refunds(self, status: str | None = None) -> list[ApiRefund]:
        query = select(ApiRefund)
        if status: query = query.where(ApiRefund.status == status)
        return list((await self.session.scalars(query.order_by(ApiRefund.id.desc()))).all())

    async def close_expired_orders(self, batch_size: int = 50) -> int:
        count = 0
        async with self.session.begin():
            orders = list((await self.session.scalars(select(ApiOrder).where(ApiOrder.status == "pending", ApiOrder.expires_at <= datetime.now()).with_for_update().limit(batch_size))).all())
            for order in orders:
                wallet = await self.wallet(order.developer_id, lock=True)
                if order.promotion_amount:
                    wallet.promotion_balance += order.promotion_amount
                    self.session.add(PromotionBalanceLog(developer_id=order.developer_id, amount=order.promotion_amount, balance_after=wallet.promotion_balance, type="expired_order_restore", reference=order.order_no))
                order.status, order.closed_at = "closed", datetime.now(); count += 1
        return count

    async def close_order(self, order_no: str, reason: str = "订单关闭") -> None:
        async with self.session.begin():
            order = await self.session.scalar(select(ApiOrder).where(ApiOrder.order_no == order_no).with_for_update())
            if not order or order.status != "pending": return
            wallet = await self.wallet(order.developer_id, lock=True)
            if order.promotion_amount:
                wallet.promotion_balance += order.promotion_amount
                self.session.add(PromotionBalanceLog(developer_id=order.developer_id, amount=order.promotion_amount, balance_after=wallet.promotion_balance, type="order_close_restore", reference=order.order_no))
            order.status, order.closed_at = "closed", datetime.now()

    async def growth_summary(self, developer_id: int) -> dict:
        invited = await self.session.scalar(select(func.count(ReferralRelation.id)).where(ReferralRelation.inviter_id == developer_id))
        settled = await self.session.scalar(select(func.count(ReferralReward.id)).join(ReferralRelation).where(ReferralRelation.inviter_id == developer_id, ReferralReward.status == "settled"))
        pending = await self.session.scalar(select(func.count(ReferralReward.id)).join(ReferralRelation).where(ReferralRelation.inviter_id == developer_id, ReferralReward.status == "pending"))
        wallet = await self.wallet(developer_id)
        developer = await self.session.get(DeveloperAccount, developer_id)
        logs = list((await self.session.scalars(select(PromotionBalanceLog).where(PromotionBalanceLog.developer_id == developer_id).order_by(PromotionBalanceLog.id.desc()).limit(50))).all())
        return {"referral_code": developer.referral_code, "invited_count": int(invited or 0), "settled_count": int(settled or 0), "pending_count": int(pending or 0), "promotion_balance": wallet.promotion_balance, "logs": logs}

    async def settle_rewards(self, batch_size: int = 50) -> int:
        count = 0
        async with self.session.begin():
            rewards = list((await self.session.scalars(select(ReferralReward).where(ReferralReward.status == "pending", ReferralReward.settle_after <= datetime.now()).with_for_update().limit(batch_size))).all())
            for reward in rewards:
                order = await self.session.get(ApiOrder, reward.order_id)
                relation = await self.session.get(ReferralRelation, reward.relation_id)
                if not order or order.status != "paid":
                    reward.status, reward.invalid_reason = "invalid", "订单已退款或失效"; continue
                inviter_wallet = await self.wallet(relation.inviter_id, lock=True)
                invitee_wallet = await self.wallet(relation.invitee_id, lock=True)
                inviter_wallet.balance += reward.inviter_credit
                invitee_wallet.balance += reward.invitee_credit
                inviter_wallet.promotion_balance += reward.commission_amount
                self.session.add(ApiCreditLog(developer_id=relation.inviter_id, change_count=reward.inviter_credit, balance_after=inviter_wallet.balance, type="referral_reward", reference=str(reward.id)))
                self.session.add(ApiCreditLog(developer_id=relation.invitee_id, change_count=reward.invitee_credit, balance_after=invitee_wallet.balance, type="referral_reward", reference=str(reward.id)))
                self.session.add(PromotionBalanceLog(developer_id=relation.inviter_id, amount=reward.commission_amount, balance_after=inviter_wallet.promotion_balance, type="referral_commission", reference=str(reward.id)))
                reward.status, reward.settled_at = "settled", datetime.now(); count += 1
        return count

    async def statistics(self, developer_id: int, start: datetime, end: datetime) -> dict:
        row = (await self.session.execute(select(func.count(ApiCallLog.id), func.sum(ApiCallLog.credit_count), func.avg(ApiCallLog.duration_ms)).where(ApiCallLog.developer_id == developer_id, ApiCallLog.created_at >= start, ApiCallLog.created_at <= end))).one()
        success = await self.session.scalar(select(func.count(ApiCallLog.id)).where(ApiCallLog.developer_id == developer_id, ApiCallLog.status == "succeeded", ApiCallLog.created_at >= start, ApiCallLog.created_at <= end))
        total = int(row[0] or 0); success = int(success or 0)
        return {"total": total, "success": success, "failed": total-success, "success_rate": round(success/total*100, 2) if total else 0, "credits": int(row[1] or 0), "average_duration_ms": round(float(row[2] or 0), 2), "start": start, "end": end}

    async def audit(self, admin_id: int, action: str, target_type: str, target_id: str | int, reason: str | None = None, detail: str | None = None) -> None:
        self.session.add(PlatformAdminAudit(admin_user_id=admin_id, action=action, target_type=target_type, target_id=str(target_id), reason=reason, detail=detail))

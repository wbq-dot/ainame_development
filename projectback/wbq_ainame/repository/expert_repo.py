from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.User import User
from models.expert_models import (
    ExpertIncome,
    ExpertOrder,
    ExpertOrderAttachment,
    ExpertProfile,
    ExpertReport,
    ExpertReview,
    ExpertServicePackage,
    ExpertSettlementRequest,
)
from core.expert_service import (
    COMMISSION_RATE,
    EXPERT_TIERS,
    calculate_commission,
    confirmation_deadline,
    create_expert_order_no,
    delivery_deadline,
)


class ExpertDomainError(Exception):
    def __init__(self, message: str, status_code: int = 409):
        super().__init__(message)
        self.status_code = status_code


class ExpertRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def profile_for_user(self, user_id: int) -> ExpertProfile | None:
        return await self.session.scalar(
            select(ExpertProfile).where(ExpertProfile.user_id == user_id)
        )

    async def require_expert_profile(self, user_id: int) -> ExpertProfile:
        profile = await self.profile_for_user(user_id)
        if not profile or profile.status != "approved":
            raise ExpertDomainError("专家资料未审核通过", 403)
        return profile

    async def submit_application(self, user_id: int, data: dict) -> ExpertProfile:
        async with self.session.begin():
            user = await self.session.scalar(
                select(User).where(User.id == user_id).with_for_update()
            )
            if not user or user.role == "admin":
                raise ExpertDomainError("管理员账号不能申请成为专家", 403)
            profile = await self.session.scalar(
                select(ExpertProfile).where(ExpertProfile.user_id == user_id).with_for_update()
            )
            if profile and profile.status in {"pending", "approved", "suspended"}:
                raise ExpertDomainError("当前专家申请状态不允许重复提交")
            if profile:
                for key, value in data.items():
                    setattr(profile, key, value)
                profile.status = "pending"
                profile.review_note = None
                profile.reviewed_at = None
                profile.updated_at = datetime.now()
            else:
                profile = ExpertProfile(user_id=user_id, status="pending", **data)
                self.session.add(profile)
            await self.session.flush()
            return profile

    async def attach_credential(
        self, user_id: int, attachment: tuple[str, str, int, str]
    ) -> ExpertProfile:
        async with self.session.begin():
            profile = await self.session.scalar(
                select(ExpertProfile)
                .where(ExpertProfile.user_id == user_id)
                .with_for_update()
            )
            if not profile:
                raise ExpertDomainError("请先提交专家申请", 400)
            if profile.status not in {"pending", "rejected"}:
                raise ExpertDomainError("当前申请状态不能修改资质附件")
            profile.credential_file_key = attachment[0]
            profile.credential_file_name = attachment[1]
            profile.updated_at = datetime.now()
            await self.session.flush()
            return profile

    async def list_public_experts(self) -> list[dict]:
        rating = (
            select(
                ExpertReview.expert_id.label("expert_id"),
                func.avg(ExpertReview.rating).label("average_rating"),
                func.count(ExpertReview.id).label("review_count"),
            )
            .group_by(ExpertReview.expert_id)
            .subquery()
        )
        result = await self.session.execute(
            select(
                ExpertProfile,
                func.coalesce(rating.c.average_rating, 0),
                func.coalesce(rating.c.review_count, 0),
            )
            .outerjoin(rating, rating.c.expert_id == ExpertProfile.id)
            .where(ExpertProfile.status == "approved")
            .order_by(ExpertProfile.id.desc())
        )
        return [self._profile_dict(profile, avg, count) for profile, avg, count in result.all()]

    async def list_public_packages(self, expert_id: int | None = None) -> list[dict]:
        rating = (
            select(
                ExpertReview.expert_id.label("expert_id"),
                func.avg(ExpertReview.rating).label("average_rating"),
                func.count(ExpertReview.id).label("review_count"),
            )
            .group_by(ExpertReview.expert_id)
            .subquery()
        )
        conditions = [
            ExpertServicePackage.status == "active",
            ExpertProfile.status == "approved",
        ]
        if expert_id is not None:
            conditions.append(ExpertServicePackage.expert_id == expert_id)
        result = await self.session.execute(
            select(
                ExpertServicePackage,
                ExpertProfile.display_name,
                ExpertProfile.title,
                func.coalesce(rating.c.average_rating, 0),
                func.coalesce(rating.c.review_count, 0),
            )
            .join(ExpertProfile, ExpertProfile.id == ExpertServicePackage.expert_id)
            .outerjoin(rating, rating.c.expert_id == ExpertProfile.id)
            .where(*conditions)
            .order_by(ExpertServicePackage.id.desc())
        )
        return [
            self._package_dict(package, name, title, avg, count)
            for package, name, title, avg, count in result.all()
        ]

    async def get_public_package(self, package_id: int) -> dict:
        rows = await self.list_public_packages()
        for item in rows:
            if item["id"] == package_id:
                return item
        raise ExpertDomainError("专家套餐不存在或已下架", 404)

    async def list_expert_packages(self, user_id: int) -> list[ExpertServicePackage]:
        profile = await self.require_expert_profile(user_id)
        result = await self.session.scalars(
            select(ExpertServicePackage)
            .where(ExpertServicePackage.expert_id == profile.id)
            .order_by(ExpertServicePackage.id.desc())
        )
        return list(result.all())

    async def save_package(
        self, user_id: int, data: dict, package_id: int | None = None
    ) -> ExpertServicePackage:
        async with self.session.begin():
            profile = await self.require_expert_profile(user_id)
            if package_id is None:
                package = ExpertServicePackage(
                    expert_id=profile.id,
                    revision_count=1,
                    status="draft",
                    **data,
                )
                self.session.add(package)
            else:
                package = await self.session.scalar(
                    select(ExpertServicePackage)
                    .where(
                        ExpertServicePackage.id == package_id,
                        ExpertServicePackage.expert_id == profile.id,
                    )
                    .with_for_update()
                )
                if not package:
                    raise ExpertDomainError("套餐不存在", 404)
                for key, value in data.items():
                    setattr(package, key, value)
                package.status = "draft"
                package.review_note = None
                package.reviewed_at = None
                package.updated_at = datetime.now()
            await self.session.flush()
            return package

    async def submit_package(self, user_id: int, package_id: int) -> ExpertServicePackage:
        async with self.session.begin():
            profile = await self.require_expert_profile(user_id)
            package = await self.session.scalar(
                select(ExpertServicePackage)
                .where(
                    ExpertServicePackage.id == package_id,
                    ExpertServicePackage.expert_id == profile.id,
                )
                .with_for_update()
            )
            if not package:
                raise ExpertDomainError("套餐不存在", 404)
            if package.status not in {"draft", "rejected", "offline"}:
                raise ExpertDomainError("当前套餐状态不能提交审核")
            package.status = "pending"
            package.review_note = None
            package.updated_at = datetime.now()
            await self.session.flush()
            return package

    async def create_order(self, user_id: int, data: dict) -> ExpertOrder:
        async with self.session.begin():
            package = None
            profile = None
            package_id = data.get("package_id")
            tier_code = data.get("expert_level", "ordinary")
            if package_id is not None:
                package = await self.session.scalar(
                    select(ExpertServicePackage)
                    .where(
                        ExpertServicePackage.id == package_id,
                        ExpertServicePackage.status == "active",
                    )
                    .with_for_update()
                )
                if not package:
                    raise ExpertDomainError("专家套餐不存在或已下架", 404)
                profile = await self.session.scalar(
                    select(ExpertProfile).where(
                        ExpertProfile.id == package.expert_id,
                        ExpertProfile.status == "approved",
                    )
                )
                if not profile:
                    raise ExpertDomainError("专家当前无法接单")
                if profile.user_id == user_id:
                    raise ExpertDomainError("不能购买自己的专家套餐", 400)
                tier_code = getattr(profile, "expert_level", "ordinary")
                package_name = package.name
                amount = Decimal(package.price)
                days = package.delivery_days
            else:
                tier = EXPERT_TIERS.get(tier_code)
                if not tier:
                    raise ExpertDomainError("不支持的专家套餐等级", 400)
                package_name = tier["name"]
                amount = Decimal(tier["price"])
                days = int(tier["delivery_days"])
            platform_fee, expert_income = calculate_commission(amount)
            order = ExpertOrder(
                order_no=create_expert_order_no(),
                user_id=user_id,
                expert_id=profile.id if profile else None,
                package_id=package.id if package else None,
                expert_level=tier_code,
                package_name=package_name,
                amount=amount,
                delivery_days=days,
                commission_rate=COMMISSION_RATE,
                platform_fee=platform_fee,
                expert_income=expert_income,
                service_mode=data.get("service_mode", "naming"),
                candidate_name=data.get("candidate_name"),
                naming_type=data["naming_type"],
                surname=data.get("surname"),
                gender=data.get("gender"),
                birth_datetime=data.get("birth_datetime"),
                birth_calendar=data.get("birth_calendar"),
                birthplace=data.get("birthplace"),
                five_elements=data.get("five_elements"),
                generation_character=data.get("generation_character"),
                avoid_characters=data.get("avoid_characters"),
                parent_expectations=data.get("parent_expectations"),
                submitted_content=data.get("submitted_content"),
                background=data["background"],
                focus=data["focus"],
                notes=data.get("notes"),
                payment_status="unpaid",
                service_status="pending_payment",
                settlement_status="none",
            )
            self.session.add(order)
            await self.session.flush()
            return order

    async def mark_paid(self, order_no: str, trade_no: str, amount: Decimal) -> tuple[ExpertOrder, bool]:
        async with self.session.begin():
            order = await self.session.scalar(
                select(ExpertOrder)
                .where(ExpertOrder.order_no == order_no)
                .with_for_update()
            )
            if not order:
                raise ExpertDomainError("订单不存在", 404)
            if Decimal(order.amount) != Decimal(amount):
                raise ExpertDomainError("支付金额不匹配", 400)
            if order.payment_status == "paid":
                return order, False
            if order.payment_status != "unpaid" or order.service_status != "pending_payment":
                raise ExpertDomainError("订单状态不允许确认支付")
            now = datetime.now()
            order.payment_status = "paid"
            order.service_status = "pending_acceptance"
            order.alipay_trade_no = trade_no
            order.paid_at = now
            order.accept_deadline = now + timedelta(hours=24)
            await self.session.flush()
            return order, True

    async def get_order_for_user(self, order_id: int, user_id: int) -> ExpertOrder:
        order = await self.session.get(ExpertOrder, order_id)
        if not order or order.user_id != user_id:
            raise ExpertDomainError("订单不存在", 404)
        return order

    async def get_order_for_expert(self, order_id: int, user_id: int) -> ExpertOrder:
        profile = await self.require_expert_profile(user_id)
        order = await self.session.get(ExpertOrder, order_id)
        if not order or order.expert_id != profile.id:
            raise ExpertDomainError("订单不存在", 404)
        return order

    async def list_orders(self, user_id: int, expert: bool = False) -> list[dict]:
        if expert:
            profile = await self.require_expert_profile(user_id)
            condition = or_(
                ExpertOrder.expert_id == profile.id,
                and_(
                    ExpertOrder.expert_id.is_(None),
                    ExpertOrder.expert_level == profile.expert_level,
                    ExpertOrder.payment_status == "paid",
                    ExpertOrder.service_status == "pending_acceptance",
                ),
            )
        else:
            condition = ExpertOrder.user_id == user_id
        result = await self.session.execute(
            select(ExpertOrder, ExpertProfile.display_name)
            .outerjoin(ExpertProfile, ExpertProfile.id == ExpertOrder.expert_id)
            .where(condition)
            .order_by(ExpertOrder.id.desc())
        )
        items = []
        for order, expert_name in result.all():
            report_version = await self.session.scalar(
                select(func.max(ExpertReport.version)).where(ExpertReport.order_id == order.id)
            )
            image_count = await self.session.scalar(
                select(func.count(ExpertOrderAttachment.id)).where(
                    ExpertOrderAttachment.order_id == order.id
                )
            )
            items.append(self._order_dict(order, expert_name, report_version, image_count))
        return items

    async def order_detail(self, order_id: int, user_id: int, expert: bool = False) -> dict:
        order = (
            await self.get_order_for_expert(order_id, user_id)
            if expert
            else await self.get_order_for_user(order_id, user_id)
        )
        name = await self.session.scalar(
            select(ExpertProfile.display_name).where(ExpertProfile.id == order.expert_id)
        )
        version = await self.session.scalar(
            select(func.max(ExpertReport.version)).where(ExpertReport.order_id == order.id)
        )
        image_count = await self.session.scalar(
            select(func.count(ExpertOrderAttachment.id)).where(
                ExpertOrderAttachment.order_id == order.id
            )
        )
        return self._order_dict(order, name, version, image_count)

    async def add_order_attachment(
        self,
        order_id: int,
        user_id: int,
        attachment: tuple[str, str, int, str],
        max_images: int,
    ) -> ExpertOrderAttachment:
        async with self.session.begin():
            order = await self.session.scalar(
                select(ExpertOrder)
                .where(ExpertOrder.id == order_id, ExpertOrder.user_id == user_id)
                .with_for_update()
            )
            if not order:
                raise ExpertDomainError("订单不存在", 404)
            if order.payment_status != "unpaid" or order.service_status != "pending_payment":
                raise ExpertDomainError("只能在订单付款前补充客户图片")
            count = await self.session.scalar(
                select(func.count(ExpertOrderAttachment.id)).where(
                    ExpertOrderAttachment.order_id == order.id
                )
            )
            if int(count or 0) >= max_images:
                raise ExpertDomainError(f"每个订单最多上传 {max_images} 张客户图片", 400)
            item = ExpertOrderAttachment(
                order_id=order.id,
                file_key=attachment[0],
                file_name=attachment[1],
                file_size=attachment[2],
                content_type=attachment[3],
            )
            self.session.add(item)
            await self.session.flush()
            return item

    async def list_order_attachments(self, order_id: int) -> list[ExpertOrderAttachment]:
        result = await self.session.scalars(
            select(ExpertOrderAttachment)
            .where(ExpertOrderAttachment.order_id == order_id)
            .order_by(ExpertOrderAttachment.id)
        )
        return list(result.all())

    async def cancel_unpaid(self, order_id: int, user_id: int) -> ExpertOrder:
        async with self.session.begin():
            order = await self.session.scalar(
                select(ExpertOrder)
                .where(ExpertOrder.id == order_id, ExpertOrder.user_id == user_id)
                .with_for_update()
            )
            if not order:
                raise ExpertDomainError("订单不存在", 404)
            if order.payment_status != "unpaid" or order.service_status != "pending_payment":
                raise ExpertDomainError("只有未付款订单可以取消")
            order.payment_status = "closed"
            order.service_status = "cancelled"
            return order

    async def expert_accept(self, order_id: int, user_id: int, accept: bool) -> ExpertOrder:
        async with self.session.begin():
            profile = await self.require_expert_profile(user_id)
            order = await self.session.scalar(
                select(ExpertOrder)
                .where(
                    ExpertOrder.id == order_id,
                    or_(
                        ExpertOrder.expert_id == profile.id,
                        ExpertOrder.expert_id.is_(None),
                    ),
                )
                .with_for_update()
            )
            if not order:
                raise ExpertDomainError("订单不存在", 404)
            if order.payment_status != "paid" or order.service_status != "pending_acceptance":
                raise ExpertDomainError("当前订单状态不能接单或拒单")
            if order.expert_id is None and order.expert_level != profile.expert_level:
                raise ExpertDomainError("该订单不属于你的专家等级", 403)
            if order.accept_deadline and order.accept_deadline < datetime.now():
                order.payment_status = "refund_pending"
                order.service_status = "cancelled"
                await self.session.flush()
                return order
            if accept:
                now = datetime.now()
                order.expert_id = profile.id
                order.service_status = "working"
                order.accepted_at = now
                order.delivery_deadline = delivery_deadline(now, order.delivery_days)
            else:
                if order.expert_id is None:
                    raise ExpertDomainError("订单池中的订单无需拒绝，可直接跳过")
                order.payment_status = "refund_pending"
                order.service_status = "cancelled"
            await self.session.flush()
            return order

    async def add_report(
        self,
        order_id: int,
        user_id: int,
        conclusion: str,
        analysis: str,
        suggestions: str,
        recommended_names: str | None,
        five_elements_analysis: str | None,
        final_reply: str | None,
        attachment: tuple[str, str, int, str] | None,
    ) -> ExpertReport:
        async with self.session.begin():
            profile = await self.require_expert_profile(user_id)
            order = await self.session.scalar(
                select(ExpertOrder)
                .where(ExpertOrder.id == order_id, ExpertOrder.expert_id == profile.id)
                .with_for_update()
            )
            if not order:
                raise ExpertDomainError("订单不存在", 404)
            allowed = {"working": 1, "revision_requested": 2}
            if order.service_status not in allowed:
                raise ExpertDomainError("当前订单状态不能提交报告")
            version = allowed[order.service_status]
            existing = await self.session.scalar(
                select(ExpertReport).where(
                    ExpertReport.order_id == order.id,
                    ExpertReport.version == version,
                )
            )
            if existing:
                raise ExpertDomainError("该版本报告已经提交")
            values = {}
            if attachment:
                values = {
                    "attachment_key": attachment[0],
                    "attachment_name": attachment[1],
                    "attachment_size": attachment[2],
                    "attachment_mime": attachment[3],
                }
            report = ExpertReport(
                order_id=order.id,
                version=version,
                conclusion=conclusion,
                analysis=analysis,
                suggestions=suggestions,
                recommended_names=recommended_names,
                five_elements_analysis=five_elements_analysis,
                final_reply=final_reply,
                **values,
            )
            self.session.add(report)
            now = datetime.now()
            order.service_status = "delivered"
            order.delivered_at = now
            order.confirm_deadline = confirmation_deadline(now)
            await self.session.flush()
            return report

    async def latest_report(self, order_id: int, user_id: int, expert: bool = False) -> ExpertReport:
        if expert:
            order = await self.get_order_for_expert(order_id, user_id)
        else:
            order = await self.get_order_for_user(order_id, user_id)
        report = await self.session.scalar(
            select(ExpertReport)
            .where(ExpertReport.order_id == order.id)
            .order_by(ExpertReport.version.desc())
        )
        if not report:
            raise ExpertDomainError("报告尚未交付", 404)
        return report

    async def request_revision(self, order_id: int, user_id: int, reason: str) -> ExpertOrder:
        async with self.session.begin():
            order = await self.session.scalar(
                select(ExpertOrder)
                .where(ExpertOrder.id == order_id, ExpertOrder.user_id == user_id)
                .with_for_update()
            )
            if not order:
                raise ExpertDomainError("订单不存在", 404)
            if order.service_status != "delivered":
                raise ExpertDomainError("当前订单状态不能申请修改")
            if order.revision_used:
                raise ExpertDomainError("本订单的一次免费修改已使用")
            if order.confirm_deadline and order.confirm_deadline < datetime.now():
                raise ExpertDomainError("确认期限已结束")
            order.revision_used = True
            order.revision_reason = reason
            order.service_status = "revision_requested"
            order.confirm_deadline = None
            return order

    async def complete_order(self, order: ExpertOrder, now: datetime | None = None) -> ExpertIncome:
        current = now or datetime.now()
        order.service_status = "completed"
        order.settlement_status = "available"
        order.completed_at = current
        income = await self.session.scalar(
            select(ExpertIncome).where(ExpertIncome.order_id == order.id)
        )
        if not income:
            income = ExpertIncome(
                order_id=order.id,
                expert_id=order.expert_id,
                gross_amount=order.amount,
                platform_fee=order.platform_fee,
                net_amount=order.expert_income,
                status="available",
            )
            self.session.add(income)
        return income

    async def user_confirm(self, order_id: int, user_id: int) -> ExpertOrder:
        async with self.session.begin():
            order = await self.session.scalar(
                select(ExpertOrder)
                .where(ExpertOrder.id == order_id, ExpertOrder.user_id == user_id)
                .with_for_update()
            )
            if not order:
                raise ExpertDomainError("订单不存在", 404)
            if order.service_status != "delivered":
                raise ExpertDomainError("只有待确认报告可以确认完成")
            await self.complete_order(order)
            await self.session.flush()
            return order

    async def dispute(self, order_id: int, user_id: int, reason: str) -> ExpertOrder:
        async with self.session.begin():
            order = await self.session.scalar(
                select(ExpertOrder)
                .where(ExpertOrder.id == order_id, ExpertOrder.user_id == user_id)
                .with_for_update()
            )
            if not order:
                raise ExpertDomainError("订单不存在", 404)
            if order.service_status not in {"working", "delivered", "revision_requested"}:
                raise ExpertDomainError("当前订单状态不能发起争议")
            order.service_status = "disputed"
            order.dispute_reason = reason
            order.confirm_deadline = None
            return order

    async def add_review(self, order_id: int, user_id: int, rating: int, content: str | None) -> ExpertReview:
        async with self.session.begin():
            order = await self.session.scalar(
                select(ExpertOrder).where(
                    ExpertOrder.id == order_id,
                    ExpertOrder.user_id == user_id,
                )
            )
            if not order:
                raise ExpertDomainError("订单不存在", 404)
            if order.service_status != "completed":
                raise ExpertDomainError("订单完成后才能评价")
            exists = await self.session.scalar(
                select(ExpertReview).where(ExpertReview.order_id == order.id)
            )
            if exists:
                raise ExpertDomainError("该订单已经评价")
            review = ExpertReview(
                order_id=order.id,
                user_id=user_id,
                expert_id=order.expert_id,
                rating=rating,
                content=content,
            )
            self.session.add(review)
            await self.session.flush()
            return review

    async def income_summary(self, user_id: int) -> dict:
        profile = await self.require_expert_profile(user_id)
        result = await self.session.execute(
            select(ExpertIncome.status, func.coalesce(func.sum(ExpertIncome.net_amount), 0))
            .where(ExpertIncome.expert_id == profile.id)
            .group_by(ExpertIncome.status)
        )
        values = {status: Decimal(amount) for status, amount in result.all()}
        return {
            "available": values.get("available", Decimal("0.00")),
            "pending": values.get("in_settlement", Decimal("0.00")),
            "paid": values.get("paid", Decimal("0.00")),
        }

    async def create_settlement(
        self, user_id: int, amount: Decimal, remark: str | None
    ) -> ExpertSettlementRequest:
        async with self.session.begin():
            profile = await self.require_expert_profile(user_id)
            incomes = list(
                (
                    await self.session.scalars(
                        select(ExpertIncome)
                        .where(
                            ExpertIncome.expert_id == profile.id,
                            ExpertIncome.status == "available",
                        )
                        .order_by(ExpertIncome.id)
                        .with_for_update()
                    )
                ).all()
            )
            selected = []
            total = Decimal("0.00")
            for income in incomes:
                selected.append(income)
                total += Decimal(income.net_amount)
                if total >= amount:
                    break
            if total != amount:
                raise ExpertDomainError("结算金额必须等于若干笔完整可结算订单收入")
            request = ExpertSettlementRequest(
                expert_id=profile.id,
                amount=amount,
                status="pending",
                remark=remark,
            )
            self.session.add(request)
            await self.session.flush()
            for income in selected:
                income.status = "in_settlement"
                income.settlement_request_id = request.id
            return request

    async def list_settlements(self, user_id: int) -> list[ExpertSettlementRequest]:
        profile = await self.require_expert_profile(user_id)
        result = await self.session.scalars(
            select(ExpertSettlementRequest)
            .where(ExpertSettlementRequest.expert_id == profile.id)
            .order_by(ExpertSettlementRequest.id.desc())
        )
        return list(result.all())

    async def admin_list_profiles(self) -> list[ExpertProfile]:
        return list(
            (
                await self.session.scalars(
                    select(ExpertProfile).order_by(ExpertProfile.id.desc())
                )
            ).all()
        )

    async def admin_profile_decision(
        self,
        profile_id: int,
        decision: str,
        note: str | None,
        expert_level: str | None = None,
    ) -> ExpertProfile:
        async with self.session.begin():
            profile = await self.session.scalar(
                select(ExpertProfile).where(ExpertProfile.id == profile_id).with_for_update()
            )
            if not profile:
                raise ExpertDomainError("专家申请不存在", 404)
            user = await self.session.scalar(
                select(User).where(User.id == profile.user_id).with_for_update()
            )
            if decision == "approve":
                if profile.status not in {"pending", "rejected"}:
                    raise ExpertDomainError("当前状态不能审核通过")
                profile.status = "approved"
                profile.expert_level = (
                    expert_level or getattr(profile, "expert_level", None) or "ordinary"
                )
                user.role = "expert"
            elif decision == "reject":
                if profile.status != "pending":
                    raise ExpertDomainError("只有待审核申请可以驳回")
                profile.status = "rejected"
                user.role = "user"
            elif decision == "suspend":
                if profile.status != "approved":
                    raise ExpertDomainError("只有正常专家可以停用")
                profile.status = "suspended"
                packages = await self.session.scalars(
                    select(ExpertServicePackage).where(
                        ExpertServicePackage.expert_id == profile.id,
                        ExpertServicePackage.status == "active",
                    )
                )
                for package in packages:
                    package.status = "offline"
            elif decision == "restore":
                if profile.status != "suspended":
                    raise ExpertDomainError("只有停用专家可以恢复")
                profile.status = "approved"
                user.role = "expert"
            else:
                raise ExpertDomainError("不支持的审核动作", 400)
            profile.review_note = note
            profile.reviewed_at = datetime.now()
            profile.updated_at = datetime.now()
            await self.session.flush()
            return profile

    async def admin_list_packages(self) -> list[dict]:
        result = await self.session.execute(
            select(ExpertServicePackage, ExpertProfile.display_name)
            .join(ExpertProfile, ExpertProfile.id == ExpertServicePackage.expert_id)
            .order_by(ExpertServicePackage.id.desc())
        )
        return [self._package_dict(package, name) for package, name in result.all()]

    async def admin_package_decision(
        self, package_id: int, decision: str, note: str | None
    ) -> ExpertServicePackage:
        async with self.session.begin():
            package = await self.session.scalar(
                select(ExpertServicePackage)
                .where(ExpertServicePackage.id == package_id)
                .with_for_update()
            )
            if not package:
                raise ExpertDomainError("套餐不存在", 404)
            if decision == "approve":
                if package.status != "pending":
                    raise ExpertDomainError("只有待审核套餐可以通过")
                package.status = "active"
            elif decision == "reject":
                if package.status != "pending":
                    raise ExpertDomainError("只有待审核套餐可以驳回")
                package.status = "rejected"
            elif decision == "offline":
                if package.status != "active":
                    raise ExpertDomainError("只有上架套餐可以下架")
                package.status = "offline"
            else:
                raise ExpertDomainError("不支持的套餐审核动作", 400)
            package.review_note = note
            package.reviewed_at = datetime.now()
            package.updated_at = datetime.now()
            await self.session.flush()
            return package

    async def admin_list_orders(self) -> list[dict]:
        result = await self.session.execute(
            select(ExpertOrder, ExpertProfile.display_name)
            .outerjoin(ExpertProfile, ExpertProfile.id == ExpertOrder.expert_id)
            .order_by(ExpertOrder.id.desc())
        )
        return [self._order_dict(order, name) for order, name in result.all()]

    async def admin_resolve_dispute(
        self,
        order_id: int,
        resolution: str,
        note: str,
        refund_reference: str | None,
    ) -> ExpertOrder:
        async with self.session.begin():
            order = await self.session.scalar(
                select(ExpertOrder).where(ExpertOrder.id == order_id).with_for_update()
            )
            if not order:
                raise ExpertDomainError("订单不存在", 404)
            if resolution == "refund":
                if order.payment_status not in {"paid", "refund_pending"}:
                    raise ExpertDomainError("当前支付状态不能登记退款")
                if not refund_reference:
                    raise ExpertDomainError("登记退款必须填写退款流水号", 400)
                order.payment_status = "refunded"
                order.service_status = "cancelled"
                order.settlement_status = "reversed"
                order.refund_reference = refund_reference
                order.refunded_at = datetime.now()
                income = await self.session.scalar(
                    select(ExpertIncome).where(ExpertIncome.order_id == order.id).with_for_update()
                )
                if income:
                    if income.status == "paid":
                        raise ExpertDomainError("该订单收入已打款，不能直接登记退款")
                    income.status = "reversed"
            elif resolution == "complete":
                if order.service_status != "disputed":
                    raise ExpertDomainError("只有争议订单可以处理完成")
                await self.complete_order(order)
            else:
                raise ExpertDomainError("不支持的争议处理方式", 400)
            order.admin_note = note
            await self.session.flush()
            return order

    async def admin_list_settlements(self) -> list[ExpertSettlementRequest]:
        return list(
            (
                await self.session.scalars(
                    select(ExpertSettlementRequest).order_by(
                        ExpertSettlementRequest.id.desc()
                    )
                )
            ).all()
        )

    async def admin_process_settlement(
        self,
        request_id: int,
        decision: str,
        note: str | None,
        payment_reference: str | None,
    ) -> ExpertSettlementRequest:
        async with self.session.begin():
            request = await self.session.scalar(
                select(ExpertSettlementRequest)
                .where(ExpertSettlementRequest.id == request_id)
                .with_for_update()
            )
            if not request:
                raise ExpertDomainError("结算申请不存在", 404)
            if request.status != "pending":
                raise ExpertDomainError("结算申请已经处理")
            incomes = list(
                (
                    await self.session.scalars(
                        select(ExpertIncome)
                        .where(ExpertIncome.settlement_request_id == request.id)
                        .with_for_update()
                    )
                ).all()
            )
            if decision == "paid":
                if not payment_reference:
                    raise ExpertDomainError("确认打款必须填写打款流水号", 400)
                request.status = "paid"
                request.payment_reference = payment_reference
                for income in incomes:
                    income.status = "paid"
                    income.paid_at = datetime.now()
                    order = await self.session.get(ExpertOrder, income.order_id)
                    if order:
                        order.settlement_status = "paid"
            elif decision == "reject":
                request.status = "rejected"
                for income in incomes:
                    income.status = "available"
                    income.settlement_request_id = None
            else:
                raise ExpertDomainError("不支持的结算处理方式", 400)
            request.remark = note or request.remark
            request.processed_at = datetime.now()
            await self.session.flush()
            return request

    async def run_maintenance(self, now: datetime | None = None) -> dict:
        current = now or datetime.now()
        counts = {"closed": 0, "accept_timeout": 0, "delivery_timeout": 0, "completed": 0}
        async with self.session.begin():
            orders = list(
                (
                    await self.session.scalars(
                        select(ExpertOrder)
                        .where(
                            ExpertOrder.service_status.in_(
                                ["pending_payment", "pending_acceptance", "working", "delivered"]
                            )
                        )
                        .with_for_update()
                    )
                ).all()
            )
            for order in orders:
                if (
                    order.service_status == "pending_payment"
                    and order.created_at <= current - timedelta(hours=1)
                ):
                    order.payment_status = "closed"
                    order.service_status = "cancelled"
                    counts["closed"] += 1
                elif (
                    order.service_status == "pending_acceptance"
                    and order.accept_deadline
                    and order.accept_deadline <= current
                ):
                    order.payment_status = "refund_pending"
                    order.service_status = "cancelled"
                    counts["accept_timeout"] += 1
                elif (
                    order.service_status == "working"
                    and order.delivery_deadline
                    and order.delivery_deadline <= current
                ):
                    order.service_status = "disputed"
                    order.dispute_reason = "专家交付超时，等待管理员处理"
                    counts["delivery_timeout"] += 1
                elif (
                    order.service_status == "delivered"
                    and order.confirm_deadline
                    and order.confirm_deadline <= current
                ):
                    await self.complete_order(order, current)
                    counts["completed"] += 1
        return counts

    @staticmethod
    def _profile_dict(profile: ExpertProfile, avg=0, count=0) -> dict:
        return {
            "id": profile.id,
            "user_id": profile.user_id,
            "display_name": profile.display_name,
            "title": profile.title,
            "bio": profile.bio,
            "specialties": profile.specialties,
            "expert_level": profile.expert_level,
            "experience_years": profile.experience_years,
            "status": profile.status,
            "review_note": profile.review_note,
            "created_at": profile.created_at,
            "reviewed_at": profile.reviewed_at,
            "average_rating": round(float(avg or 0), 1),
            "review_count": int(count or 0),
        }

    @staticmethod
    def _package_dict(package: ExpertServicePackage, name=None, title=None, avg=0, count=0) -> dict:
        return {
            "id": package.id,
            "expert_id": package.expert_id,
            "name": package.name,
            "description": package.description,
            "deliverables": package.deliverables,
            "price": package.price,
            "delivery_days": package.delivery_days,
            "revision_count": package.revision_count,
            "status": package.status,
            "review_note": package.review_note,
            "expert_name": name,
            "expert_title": title,
            "average_rating": round(float(avg or 0), 1),
            "review_count": int(count or 0),
            "created_at": package.created_at,
        }

    @staticmethod
    def _order_dict(
        order: ExpertOrder,
        expert_name=None,
        report_version=None,
        image_count=0,
    ) -> dict:
        values = {
            column.name: getattr(order, column.name)
            for column in ExpertOrder.__table__.columns
        }
        values["expert_name"] = expert_name
        values["report_version"] = report_version
        values["image_count"] = int(image_count or 0)
        return values

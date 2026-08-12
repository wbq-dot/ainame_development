import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.authtools import AuthHandler
from core.alipaytools import PaymentConfigurationError, create_alipay
from dependencies import get_session
from modules.platform.platform_models import (
    ApiCallLog, ApiOrder, ApiPackage, ApiRefund, DeveloperAccount, DeveloperApiKey, PlatformTask,
    ReferralCampaign, ReferralRelation, ReferralReward,
)
from modules.platform.platform_repo import PlatformConflict, PlatformNotFound, PlatformRepository
from modules.platform.platform_schemas import (
    AdminDeveloperActionIn, AdminRewardInvalidateIn, AdminTaskRetryIn, ApiPackageIn, ApiPackageStatusIn,
    ApiRefundReviewIn, CampaignIn,
)
from modules.platform.task_service import publish_or_mark_failed


router = APIRouter(prefix="/admin/platform", tags=["admin-platform"])
auth = AuthHandler()


@router.get("/developers")
async def developers(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), keyword: str = "", status: str = "", admin_id: int = Depends(auth.admin_dependency), session: AsyncSession = Depends(get_session)):
    filters = []
    if keyword: filters.append((DeveloperAccount.email.like(f"%{keyword}%")) | (DeveloperAccount.name.like(f"%{keyword}%")))
    if status: filters.append(DeveloperAccount.status == status)
    total = await session.scalar(select(func.count(DeveloperAccount.id)).where(*filters))
    rows = list((await session.scalars(select(DeveloperAccount).where(*filters).order_by(DeveloperAccount.id.desc()).offset((page-1)*page_size).limit(page_size))).all())
    items = []
    for row in rows:
        keys = await session.scalar(select(func.count(DeveloperApiKey.id)).where(DeveloperApiKey.developer_id == row.id, DeveloperApiKey.status == "active"))
        items.append({"id": row.id, "email": row.email, "name": row.name, "status": row.status, "referral_code": row.referral_code, "rate_limit_per_minute": row.rate_limit_per_minute, "active_keys": int(keys or 0), "created_at": row.created_at})
    return {"items": items, "total": int(total or 0), "page": page, "page_size": page_size}


async def _developer_status(developer_id: int, status: str, data: AdminDeveloperActionIn, admin_id: int, session: AsyncSession):
    async with session.begin():
        developer = await session.get(DeveloperAccount, developer_id, with_for_update=True)
        if not developer: raise HTTPException(404, "开发者不存在")
        developer.status, developer.auth_version = status, developer.auth_version + 1
        developer.frozen_at = datetime.now() if status == "frozen" else None
        if status == "frozen":
            keys = list((await session.scalars(select(DeveloperApiKey).where(DeveloperApiKey.developer_id == developer_id, DeveloperApiKey.status == "active").with_for_update())).all())
            for key in keys: key.status, key.revoked_at = "revoked", datetime.now()
        await PlatformRepository(session).audit(admin_id, f"developer_{status}", "developer", developer_id, data.reason)
    return {"message": "开发者已冻结" if status == "frozen" else "开发者已解冻"}


@router.post("/developers/{developer_id}/freeze")
async def freeze(developer_id: int, data: AdminDeveloperActionIn, admin_id: int = Depends(auth.admin_dependency), session: AsyncSession = Depends(get_session)): return await _developer_status(developer_id, "frozen", data, admin_id, session)


@router.post("/developers/{developer_id}/unfreeze")
async def unfreeze(developer_id: int, data: AdminDeveloperActionIn, admin_id: int = Depends(auth.admin_dependency), session: AsyncSession = Depends(get_session)): return await _developer_status(developer_id, "active", data, admin_id, session)


@router.get("/developers/{developer_id}/keys")
async def developer_keys(developer_id: int, admin_id: int = Depends(auth.admin_dependency), session: AsyncSession = Depends(get_session)):
    return await PlatformRepository(session).list_api_keys(developer_id)


@router.post("/keys/{key_id}/revoke")
async def admin_revoke_key(key_id: int, data: AdminDeveloperActionIn, admin_id: int = Depends(auth.admin_dependency), session: AsyncSession = Depends(get_session)):
    async with session.begin():
        key = await session.get(DeveloperApiKey, key_id, with_for_update=True)
        if not key: raise HTTPException(404, "API Key 不存在")
        if key.status != "revoked": key.status, key.revoked_at = "revoked", datetime.now()
        await PlatformRepository(session).audit(admin_id, "api_key_revoke", "developer_api_key", key_id, data.reason)
    return {"message": "API Key 已吊销"}


@router.get("/packages")
async def packages(admin_id: int = Depends(auth.admin_dependency), session: AsyncSession = Depends(get_session)): return await PlatformRepository(session).list_packages(False)


@router.post("/packages", status_code=201)
async def create_package(data: ApiPackageIn, admin_id: int = Depends(auth.admin_dependency), session: AsyncSession = Depends(get_session)):
    package = await PlatformRepository(session).save_package(data.model_dump())
    async with session.begin(): await PlatformRepository(session).audit(admin_id, "package_create", "api_package", package.id)
    return package


@router.put("/packages/{package_id}")
async def update_package(package_id: int, data: ApiPackageIn, admin_id: int = Depends(auth.admin_dependency), session: AsyncSession = Depends(get_session)):
    try: package = await PlatformRepository(session).save_package(data.model_dump(), package_id)
    except PlatformNotFound as exc: raise HTTPException(404, str(exc)) from exc
    async with session.begin(): await PlatformRepository(session).audit(admin_id, "package_update", "api_package", package.id)
    return package


@router.patch("/packages/{package_id}/status")
async def package_status(package_id: int, data: ApiPackageStatusIn, admin_id: int = Depends(auth.admin_dependency), session: AsyncSession = Depends(get_session)):
    async with session.begin():
        package = await session.get(ApiPackage, package_id, with_for_update=True)
        if not package: raise HTTPException(404, "API 套餐不存在")
        package.is_active = data.is_active
        await PlatformRepository(session).audit(admin_id, "package_activate" if data.is_active else "package_deactivate", "api_package", package_id, data.reason)
    return package


@router.get("/campaigns")
async def campaigns(admin_id: int = Depends(auth.admin_dependency), session: AsyncSession = Depends(get_session)): return list((await session.scalars(select(ReferralCampaign).order_by(ReferralCampaign.id.desc()))).all())


@router.post("/campaigns", status_code=201)
async def create_campaign(data: CampaignIn, admin_id: int = Depends(auth.admin_dependency), session: AsyncSession = Depends(get_session)):
    async with session.begin():
        if data.is_active and await session.scalar(select(ReferralCampaign.id).where(ReferralCampaign.is_active.is_(True), ReferralCampaign.starts_at < data.ends_at, ReferralCampaign.ends_at > data.starts_at)): raise HTTPException(409, "该时间段已有启用的邀请活动")
        campaign = ReferralCampaign(**data.model_dump()); session.add(campaign); await session.flush()
        await PlatformRepository(session).audit(admin_id, "campaign_create", "referral_campaign", campaign.id)
    return campaign


@router.put("/campaigns/{campaign_id}")
async def update_campaign(campaign_id: int, data: CampaignIn, admin_id: int = Depends(auth.admin_dependency), session: AsyncSession = Depends(get_session)):
    async with session.begin():
        campaign = await session.get(ReferralCampaign, campaign_id, with_for_update=True)
        if not campaign: raise HTTPException(404, "邀请活动不存在")
        if data.is_active and await session.scalar(select(ReferralCampaign.id).where(ReferralCampaign.is_active.is_(True), ReferralCampaign.id != campaign_id, ReferralCampaign.starts_at < data.ends_at, ReferralCampaign.ends_at > data.starts_at)): raise HTTPException(409, "该时间段已有其他启用的邀请活动")
        for key, value in data.model_dump().items(): setattr(campaign, key, value)
        await PlatformRepository(session).audit(admin_id, "campaign_update", "referral_campaign", campaign.id)
    return campaign


@router.get("/referrals")
async def referrals(status: str = "", admin_id: int = Depends(auth.admin_dependency), session: AsyncSession = Depends(get_session)):
    query = select(ReferralReward, ReferralRelation).join(ReferralRelation, ReferralRelation.id == ReferralReward.relation_id)
    if status: query = query.where(ReferralReward.status == status)
    rows = (await session.execute(query.order_by(ReferralReward.id.desc()))).all()
    return [{"id": reward.id, "inviter_id": relation.inviter_id, "invitee_id": relation.invitee_id, "campaign_id": relation.campaign_id, "status": reward.status, "commission_amount": reward.commission_amount, "settle_after": reward.settle_after, "settled_at": reward.settled_at} for reward, relation in rows]


@router.post("/referrals/{reward_id}/invalidate")
async def invalidate_reward(reward_id: int, data: AdminRewardInvalidateIn, admin_id: int = Depends(auth.admin_dependency), session: AsyncSession = Depends(get_session)):
    async with session.begin():
        reward = await session.get(ReferralReward, reward_id, with_for_update=True)
        if not reward: raise HTTPException(404, "奖励记录不存在")
        if reward.status != "pending": raise HTTPException(409, "只有待结算奖励可以作废")
        reward.status, reward.invalid_reason = "invalid", data.reason
        await PlatformRepository(session).audit(admin_id, "reward_invalidate", "referral_reward", reward_id, data.reason)
    return {"message": "异常奖励已作废"}


@router.get("/calls")
async def calls(developer_id: int | None = None, status: str = "", endpoint: str = "", page: int = 1, page_size: int = 20, admin_id: int = Depends(auth.admin_dependency), session: AsyncSession = Depends(get_session)):
    filters = []
    if developer_id is not None: filters.append(ApiCallLog.developer_id == developer_id)
    if status: filters.append(ApiCallLog.status == status)
    if endpoint: filters.append(ApiCallLog.endpoint == endpoint)
    total = await session.scalar(select(func.count(ApiCallLog.id)).where(*filters))
    items = list((await session.scalars(select(ApiCallLog).where(*filters).order_by(ApiCallLog.id.desc()).offset((page-1)*page_size).limit(page_size))).all())
    return {"items": items, "total": int(total or 0), "page": page, "page_size": page_size}


@router.get("/refunds")
async def refunds(status: str = "", admin_id: int = Depends(auth.admin_dependency), session: AsyncSession = Depends(get_session)):
    return await PlatformRepository(session).list_refunds(status or None)


@router.post("/refunds/{refund_no}/review")
async def review_refund(refund_no: str, data: ApiRefundReviewIn, admin_id: int = Depends(auth.admin_dependency), session: AsyncSession = Depends(get_session)):
    if data.approve:
        pair = (await session.execute(select(ApiRefund, ApiOrder).join(ApiOrder, ApiOrder.id == ApiRefund.order_id).where(ApiRefund.refund_no == refund_no))).first()
        if not pair: raise HTTPException(404, "退款申请不存在")
        refund_row, order = pair
        if refund_row.status != "requested": raise HTTPException(409, "退款申请已处理")
        cash_amount, order_no = order.cash_amount, order.order_no
        await session.rollback()
        if cash_amount > 0:
            try:
                result = await asyncio.to_thread(create_alipay().api_alipay_trade_refund, out_trade_no=order_no, refund_amount=str(cash_amount), out_request_no=refund_no)
            except PaymentConfigurationError as exc: raise HTTPException(503, str(exc)) from exc
            except Exception as exc: raise HTTPException(502, "支付宝退款请求失败，记录仍保持待审核") from exc
            if result.get("code") != "10000": raise HTTPException(502, result.get("sub_msg") or "支付宝未确认退款成功")
    try: return await PlatformRepository(session).finalize_refund(refund_no, admin_id, data.approve, data.note)
    except PlatformNotFound as exc: raise HTTPException(404, str(exc)) from exc
    except PlatformConflict as exc: raise HTTPException(409, str(exc)) from exc


@router.get("/tasks")
async def tasks(task_type: str = "", status: str = "", page: int = 1, page_size: int = 20, admin_id: int = Depends(auth.admin_dependency), session: AsyncSession = Depends(get_session)):
    items, total = await PlatformRepository(session).list_tasks(task_type=task_type or None, status=status or None, page=page, page_size=page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/tasks/{task_no}")
async def task_detail(task_no: str, admin_id: int = Depends(auth.admin_dependency), session: AsyncSession = Depends(get_session)):
    try: return await PlatformRepository(session).task_detail(task_no)
    except PlatformNotFound as exc: raise HTTPException(404, str(exc)) from exc


@router.post("/tasks/{task_no}/retry")
async def retry_task(task_no: str, data: AdminTaskRetryIn, admin_id: int = Depends(auth.admin_dependency), session: AsyncSession = Depends(get_session)):
    repo = PlatformRepository(session)
    try: task = await repo.retry_task(task_no)
    except PlatformNotFound as exc: raise HTTPException(404, str(exc)) from exc
    except PlatformConflict as exc: raise HTTPException(409, str(exc)) from exc
    async with session.begin(): await repo.audit(admin_id, "task_retry", "platform_task", task_no, data.reason)
    published = await publish_or_mark_failed(task_no)
    return {"message": "任务已重新入队" if published else "重新发布失败，任务仍可重试", "status": "queued" if published else "publish_failed"}


@router.get("/statistics")
async def platform_statistics(admin_id: int = Depends(auth.admin_dependency), session: AsyncSession = Depends(get_session)):
    developers = await session.scalar(select(func.count(DeveloperAccount.id)))
    calls = await session.scalar(select(func.count(ApiCallLog.id)))
    success = await session.scalar(select(func.count(ApiCallLog.id)).where(ApiCallLog.status == "succeeded"))
    tasks = await session.scalar(select(func.count(PlatformTask.id)))
    failed_tasks = await session.scalar(select(func.count(PlatformTask.id)).where(PlatformTask.status.in_(("failed", "partial_failed", "publish_failed"))))
    return {"developers": int(developers or 0), "calls": int(calls or 0), "successful_calls": int(success or 0), "tasks": int(tasks or 0), "failed_tasks": int(failed_tasks or 0)}

import secrets
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import settings
from core.authtools import AuthHandler
from dependencies import get_session
from repository.admin_repo import (
    AdminRepository,
    AdminEmailConflict,
    AdminPackageNameConflict,
    AdminPackageNotFound,
    AdminStateConflict,
    AdminTargetForbidden,
    AdminTargetNotFound,
)
from repository.expert_repo import ExpertDomainError, ExpertRepository
from schemas.admin_schemas import (
    AdminActionIn,
    AdminActionOut,
    AdminBootstrapIn,
    AdminBootstrapOut,
    AdminBootstrapStatusOut,
    AdminCreditAdjustmentIn,
    AdminCreditAdjustmentOut,
    AdminPackageMutationOut,
    AdminPackageOut,
    AdminPackageStatusIn,
    AdminPackageStatusOut,
    AdminPackageWriteIn,
    AdminUserListOut,
)
from schemas.expert_schemas import (
    AdminDecisionIn,
    AdminDisputeIn,
    ExpertApplicationOut,
    ExpertOrderOut,
    ExpertPackageOut,
    ExpertProfileOut,
    SettlementOut,
    SettlementProcessIn,
)
from repository.payment_repo import (
    PaymentConflict,
    PaymentNotFound,
    PaymentRepository,
    RefundNotEligible,
)
from schemas.pay_schemas import (
    RefundListOut,
    RefundOut,
    RefundRejectIn,
    RefundReviewIn,
)


router = APIRouter(prefix="/admin", tags=["admin"])
auth_handler = AuthHandler()
MIN_BOOTSTRAP_SECRET_LENGTH = 32


def _bootstrap_enabled() -> bool:
    return len(settings.ADMIN_BOOTSTRAP_SECRET) >= MIN_BOOTSTRAP_SECRET_LENGTH


@router.get("/bootstrap/status", response_model=AdminBootstrapStatusOut)
async def bootstrap_status(session: AsyncSession = Depends(get_session)):
    initialization_required = await AdminRepository(session).bootstrap_status()
    return {
        "initialization_required": initialization_required,
        "bootstrap_enabled": _bootstrap_enabled(),
    }


@router.post("/bootstrap", response_model=AdminBootstrapOut, status_code=201)
async def bootstrap_admin(
    data: AdminBootstrapIn,
    session: AsyncSession = Depends(get_session),
):
    configured_secret = settings.ADMIN_BOOTSTRAP_SECRET
    if not _bootstrap_enabled():
        raise HTTPException(status_code=503, detail="管理员网页初始化未启用")
    if not secrets.compare_digest(data.bootstrap_secret, configured_secret):
        raise HTTPException(status_code=403, detail="初始化凭据无效")

    try:
        user = await AdminRepository(session).bootstrap_admin(
            email=str(data.email),
            username=data.username,
            password=data.password,
        )
    except AdminEmailConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AdminStateConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="管理员账号与现有数据冲突") from exc
    return {
        "message": "首任管理员创建成功",
        "user_id": user.id,
        "email": user.email,
        "username": user.username,
    }


@router.get("/users", response_model=AdminUserListOut)
async def list_users(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    keyword: Annotated[str | None, Query(max_length=100)] = None,
    status: Literal["active", "frozen", "deleted"] | None = None,
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = AdminRepository(session)
    items, total = await repository.list_users(page, page_size, keyword, status)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/packages", response_model=list[AdminPackageOut])
async def list_packages(
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    return await AdminRepository(session).list_packages()


@router.get("/packages/{package_id}", response_model=AdminPackageOut)
async def get_package(
    package_id: int,
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await AdminRepository(session).get_package(package_id)
    except AdminPackageNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/packages",
    response_model=AdminPackageMutationOut,
    status_code=201,
)
async def create_package(
    data: AdminPackageWriteIn,
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        package = await AdminRepository(session).create_package(
            admin_user_id,
            data.name,
            data.price,
            data.credit_count,
            data.credit_type,
        )
    except AdminPackageNameConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="套餐名称已经存在") from exc
    return {"message": "套餐已创建，当前为下架状态", "package": package}


@router.put(
    "/packages/{package_id}",
    response_model=AdminPackageMutationOut,
)
async def update_package(
    package_id: int,
    data: AdminPackageWriteIn,
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        package, changed = await AdminRepository(session).update_package(
            admin_user_id,
            package_id,
            data.name,
            data.price,
            data.credit_count,
            data.credit_type,
        )
    except AdminPackageNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AdminPackageNameConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AdminStateConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="套餐名称已经存在") from exc
    message = "套餐已更新" if changed else "套餐信息未变化"
    return {"message": message, "package": package}


@router.patch(
    "/packages/{package_id}/status",
    response_model=AdminPackageStatusOut,
)
async def change_package_status(
    package_id: int,
    data: AdminPackageStatusIn,
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        package, changed = await AdminRepository(session).change_package_status(
            admin_user_id,
            package_id,
            data.is_active,
        )
    except AdminPackageNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not changed:
        state_label = "上架" if data.is_active else "下架"
        message = f"套餐已经处于{state_label}状态"
    else:
        message = "套餐已上架" if data.is_active else "套餐已下架"
    return {"message": message, "package": package}


@router.post(
    "/users/{user_id}/credit-adjustments",
    response_model=AdminCreditAdjustmentOut,
)
async def adjust_user_credit(
    user_id: int,
    data: AdminCreditAdjustmentIn,
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await AdminRepository(session).adjust_user_credit(
            admin_user_id,
            user_id,
            data.credit_type,
            data.change_count,
            data.reason,
        )
    except AdminTargetNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AdminTargetForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except AdminStateConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"message": "用户余额已调整", **result}


@router.post("/users/{user_id}/freeze", response_model=AdminActionOut)
async def freeze_user(
    user_id: int,
    data: AdminActionIn | None = None,
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    user = await _change_status(
        session,
        admin_user_id,
        user_id,
        "frozen",
        data.reason if data else None,
    )
    return {"message": "用户已冻结", "user": user}


@router.post("/users/{user_id}/unfreeze", response_model=AdminActionOut)
async def unfreeze_user(
    user_id: int,
    data: AdminActionIn | None = None,
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    user = await _change_status(
        session,
        admin_user_id,
        user_id,
        "active",
        data.reason if data else None,
    )
    return {"message": "用户已解冻", "user": user}


@router.delete("/users/{user_id}", response_model=AdminActionOut)
async def delete_user(
    user_id: int,
    data: AdminActionIn | None = None,
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = AdminRepository(session)
    try:
        user = await repository.soft_delete_user(
            admin_user_id,
            user_id,
            data.reason if data else None,
        )
    except AdminTargetNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AdminTargetForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except AdminStateConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"message": "用户已删除并匿名化", "user": user}


async def _change_status(
    session: AsyncSession,
    admin_user_id: int,
    user_id: int,
    target_status: str,
    reason: str | None,
) -> dict:
    repository = AdminRepository(session)
    try:
        return await repository.change_status(
            admin_user_id,
            user_id,
            target_status,
            reason,
        )
    except AdminTargetNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AdminTargetForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except AdminStateConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _raise_expert_domain(exc: ExpertDomainError):
    raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/expert-applications", response_model=list[ExpertApplicationOut])
async def list_expert_applications(
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    return await ExpertRepository(session).admin_list_profiles()


@router.post(
    "/expert-applications/{profile_id}/decision",
    response_model=ExpertProfileOut,
)
async def decide_expert_application(
    profile_id: int,
    data: AdminDecisionIn,
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).admin_profile_decision(
            profile_id, data.decision, data.note, data.expert_level
        )
    except ExpertDomainError as exc:
        _raise_expert_domain(exc)


@router.get("/expert-packages", response_model=list[ExpertPackageOut])
async def list_admin_expert_packages(
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    return await ExpertRepository(session).admin_list_packages()


@router.post(
    "/expert-packages/{package_id}/decision",
    response_model=ExpertPackageOut,
)
async def decide_expert_package(
    package_id: int,
    data: AdminDecisionIn,
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).admin_package_decision(
            package_id, data.decision, data.note
        )
    except ExpertDomainError as exc:
        _raise_expert_domain(exc)


@router.get("/expert-orders", response_model=list[ExpertOrderOut])
async def list_admin_expert_orders(
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    return await ExpertRepository(session).admin_list_orders()


@router.post("/expert-orders/{order_id}/resolve", response_model=ExpertOrderOut)
async def resolve_expert_order(
    order_id: int,
    data: AdminDisputeIn,
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).admin_resolve_dispute(
            order_id, data.resolution, data.note, data.refund_reference
        )
    except ExpertDomainError as exc:
        _raise_expert_domain(exc)


@router.get("/expert-settlements", response_model=list[SettlementOut])
async def list_admin_expert_settlements(
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    return await ExpertRepository(session).admin_list_settlements()


@router.post(
    "/expert-settlements/{request_id}/process",
    response_model=SettlementOut,
)
async def process_expert_settlement(
    request_id: int,
    data: SettlementProcessIn,
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).admin_process_settlement(
            request_id, data.decision, data.note, data.payment_reference
        )
    except ExpertDomainError as exc:
        _raise_expert_domain(exc)


@router.get("/refunds", response_model=RefundListOut)
async def list_refunds(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    keyword: Annotated[str | None, Query(max_length=100)] = None,
    status: Literal["requested", "rejected", "processing", "succeeded", "failed"] | None = None,
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    items, total = await PaymentRepository(session).list_admin_refunds(
        page, page_size, status, keyword
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post(
    "/refunds/{refund_no}/approve", response_model=RefundOut, status_code=202
)
async def approve_refund(
    refund_no: str,
    data: RefundReviewIn | None = None,
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        refund, approved = await PaymentRepository(session).approve_refund(
            refund_no,
            admin_user_id,
            data.reason if data else None,
        )
        if not approved:
            raise HTTPException(status_code=409, detail=refund["review_note"])
        return refund
    except PaymentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (PaymentConflict, RefundNotEligible) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/refunds/{refund_no}/reject", response_model=RefundOut)
async def reject_refund(
    refund_no: str,
    data: RefundRejectIn,
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await PaymentRepository(session).reject_refund(
            refund_no, admin_user_id, data.reason
        )
    except PaymentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PaymentConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/refunds/{refund_no}/retry", response_model=RefundOut, status_code=202)
async def retry_refund(
    refund_no: str,
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await PaymentRepository(session).retry_refund(
            refund_no, admin_user_id
        )
    except PaymentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (PaymentConflict, RefundNotEligible) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

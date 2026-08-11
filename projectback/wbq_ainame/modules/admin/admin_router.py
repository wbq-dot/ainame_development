import secrets
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import settings
from core.authtools import AuthHandler
from dependencies import get_session
from modules.admin.admin_repo import (
    AdminRepository,
    AdminEmailConflict,
    AdminStateConflict,
    AdminTargetForbidden,
    AdminTargetNotFound,
)
from modules.admin.admin_schemas import (
    AdminActionIn,
    AdminActionOut,
    AdminBootstrapIn,
    AdminBootstrapOut,
    AdminBootstrapStatusOut,
    AdminUserListOut,
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

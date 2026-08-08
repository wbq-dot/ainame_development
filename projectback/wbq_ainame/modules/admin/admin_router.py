from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.authtools import AuthHandler
from dependencies import get_session
from modules.admin.admin_repo import (
    AdminRepository,
    AdminStateConflict,
    AdminTargetForbidden,
    AdminTargetNotFound,
)
from modules.admin.admin_schemas import AdminActionIn, AdminActionOut, AdminUserListOut


router = APIRouter(prefix="/admin", tags=["admin"])
auth_handler = AuthHandler()


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

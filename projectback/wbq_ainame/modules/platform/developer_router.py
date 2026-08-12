from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_mail import FastMail, MessageSchema, MessageType
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.redistools import get_redis
from dependencies import get_email, get_session
from modules.platform.platform_auth import developer_auth
from modules.platform.platform_models import ApiCreditLog, DeveloperAccount
from modules.platform.platform_repo import PlatformConflict, PlatformNotFound, PlatformRepository
from modules.platform.platform_schemas import (
    ApiKeyCreateIn, ApiKeyCreatedOut, ApiKeyOut, ApiKeyRenameIn,
    DeveloperLoginIn, DeveloperLoginOut, DeveloperOut, DeveloperPasswordIn,
    DeveloperRefreshOut, DeveloperRegisterIn, WalletOut,
)


router = APIRouter(prefix="/developer", tags=["developer-platform"])


@router.get("/auth/code")
async def send_code(email: str = Query(..., min_length=3, max_length=100), mail: FastMail = Depends(get_email), redis: Redis = Depends(get_redis)):
    import random
    code = f"{random.SystemRandom().randrange(1000, 10000)}"
    await mail.send_message(MessageSchema(subject="【智能起名开放平台】注册验证码", recipients=[email], body=f"您的验证码是 {code}，5 分钟内有效。", subtype=MessageType.plain))
    await redis.set(f"developer:register:{email.lower()}", code, 300)
    return {"message": "验证码已发送"}


@router.post("/auth/register", response_model=DeveloperOut, status_code=201)
async def register(data: DeveloperRegisterIn, redis: Redis = Depends(get_redis), session: AsyncSession = Depends(get_session)):
    saved = await redis.get(f"developer:register:{str(data.email).lower()}")
    if not saved or saved != data.code: raise HTTPException(400, "验证码错误或已过期")
    try:
        developer = await PlatformRepository(session).register_developer(str(data.email), data.name, data.password, data.referral_code)
    except PlatformConflict as exc: raise HTTPException(409, str(exc)) from exc
    await redis.delete(f"developer:register:{str(data.email).lower()}")
    return developer


@router.post("/auth/login", response_model=DeveloperLoginOut)
async def login(data: DeveloperLoginIn, session: AsyncSession = Depends(get_session)):
    developer = await session.scalar(select(DeveloperAccount).where(DeveloperAccount.email == data.email.lower()))
    if not developer or not developer.check_password(data.password): raise HTTPException(400, "邮箱或密码错误")
    if developer.status != "active": raise HTTPException(423, "开发者账号已冻结")
    return {"developer": developer, **developer_auth.login_tokens(developer)}


@router.post("/auth/refresh", response_model=DeveloperRefreshOut)
async def refresh(developer: DeveloperAccount = Depends(developer_auth.refresh)):
    return {"access_token": developer_auth.login_tokens(developer)["access_token"]}


@router.get("/me", response_model=DeveloperOut)
async def me(developer: DeveloperAccount = Depends(developer_auth.access)): return developer


@router.patch("/password")
async def change_password(data: DeveloperPasswordIn, developer: DeveloperAccount = Depends(developer_auth.access), session: AsyncSession = Depends(get_session)):
    async with session.begin():
        row = await session.get(DeveloperAccount, developer.id, with_for_update=True)
        if not row.check_password(data.current_password): raise HTTPException(400, "当前密码错误")
        row.set_password(data.new_password); row.auth_version += 1
    return {"message": "密码已修改，请重新登录"}


@router.get("/keys", response_model=list[ApiKeyOut])
async def keys(developer: DeveloperAccount = Depends(developer_auth.access), session: AsyncSession = Depends(get_session)): return await PlatformRepository(session).list_api_keys(developer.id)


@router.post("/keys", response_model=ApiKeyCreatedOut, status_code=201)
async def create_key(data: ApiKeyCreateIn, developer: DeveloperAccount = Depends(developer_auth.access), session: AsyncSession = Depends(get_session)):
    key, raw = await PlatformRepository(session).create_api_key(developer.id, data.name)
    return {**ApiKeyOut.model_validate(key).model_dump(), "api_key": raw}


@router.patch("/keys/{key_id}", response_model=ApiKeyOut)
async def rename_key(key_id: int, data: ApiKeyRenameIn, developer: DeveloperAccount = Depends(developer_auth.access), session: AsyncSession = Depends(get_session)):
    try: return await PlatformRepository(session).update_api_key(developer.id, key_id, name=data.name)
    except PlatformNotFound as exc: raise HTTPException(404, str(exc)) from exc


@router.post("/keys/{key_id}/revoke", response_model=ApiKeyOut)
async def revoke_key(key_id: int, developer: DeveloperAccount = Depends(developer_auth.access), session: AsyncSession = Depends(get_session)):
    try: return await PlatformRepository(session).update_api_key(developer.id, key_id, revoke=True)
    except PlatformNotFound as exc: raise HTTPException(404, str(exc)) from exc


@router.post("/keys/{key_id}/regenerate", response_model=ApiKeyCreatedOut)
async def regenerate_key(key_id: int, developer: DeveloperAccount = Depends(developer_auth.access), session: AsyncSession = Depends(get_session)):
    try: key, raw = await PlatformRepository(session).regenerate_api_key(developer.id, key_id)
    except PlatformNotFound as exc: raise HTTPException(404, str(exc)) from exc
    return {**ApiKeyOut.model_validate(key).model_dump(), "api_key": raw}


@router.get("/wallet", response_model=WalletOut)
async def wallet(developer: DeveloperAccount = Depends(developer_auth.access), session: AsyncSession = Depends(get_session)):
    row = await PlatformRepository(session).wallet(developer.id)
    return {"balance": row.balance, "reserved": row.reserved, "available": row.balance-row.reserved, "promotion_balance": row.promotion_balance}


@router.get("/wallet/logs")
async def wallet_logs(page: int = 1, page_size: int = 20, developer: DeveloperAccount = Depends(developer_auth.access), session: AsyncSession = Depends(get_session)):
    total = await session.scalar(select(__import__('sqlalchemy').func.count(ApiCreditLog.id)).where(ApiCreditLog.developer_id == developer.id))
    items = list((await session.scalars(select(ApiCreditLog).where(ApiCreditLog.developer_id == developer.id).order_by(ApiCreditLog.id.desc()).offset((page-1)*page_size).limit(page_size))).all())
    return {"items": items, "total": int(total or 0), "page": page, "page_size": page_size}


@router.get("/statistics")
async def statistics(days: int = Query(7, ge=1, le=366), developer: DeveloperAccount = Depends(developer_auth.access), session: AsyncSession = Depends(get_session)):
    end = datetime.now(); return await PlatformRepository(session).statistics(developer.id, end-timedelta(days=days), end)


@router.get("/growth")
async def growth(developer: DeveloperAccount = Depends(developer_auth.access), session: AsyncSession = Depends(get_session)): return await PlatformRepository(session).growth_summary(developer.id)


@router.get("/tasks")
async def developer_tasks(page: int = 1, page_size: int = 20, developer: DeveloperAccount = Depends(developer_auth.access), session: AsyncSession = Depends(get_session)):
    items, total = await PlatformRepository(session).list_tasks(owner_type="developer", owner_id=developer.id, page=page, page_size=page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/tasks/{task_no}")
async def developer_task_detail(task_no: str, developer: DeveloperAccount = Depends(developer_auth.access), session: AsyncSession = Depends(get_session)):
    try: return await PlatformRepository(session).task_detail(task_no, "developer", developer.id)
    except PlatformNotFound as exc: raise HTTPException(404, str(exc)) from exc

import json
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_mail import FastMail, MessageSchema, MessageType
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from core.authtools import AuthHandler
from core.redistools import get_redis
from dependencies import get_email, get_session
from repository.account_repo import (
    AccountEmailConflict,
    AccountEmailUnchanged,
    AccountNotFound,
    AccountPasswordInvalid,
    AccountRepository,
    AdminSelfDeletionForbidden,
)
from schemas.account_schemas import (
    AccountMessageOut,
    ChangeEmailIn,
    ChangePasswordIn,
    SendEmailChangeCodeIn,
)


router = APIRouter(prefix="/account", tags=["account"])
auth_handler = AuthHandler()
logger = logging.getLogger(__name__)

EMAIL_CODE_TTL_SECONDS = 300
EMAIL_CODE_COOLDOWN_SECONDS = 60
EMAIL_CODE_MAX_ATTEMPTS = 5


def _code_key(user_id: int) -> str:
    return f"account:email-change:code:{user_id}"


def _cooldown_key(user_id: int) -> str:
    return f"account:email-change:cooldown:{user_id}"


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _raise_account_error(exc: Exception) -> None:
    if isinstance(exc, AccountNotFound):
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    if isinstance(exc, AdminSelfDeletionForbidden):
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if isinstance(exc, (AccountEmailConflict,)):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, (AccountEmailUnchanged, AccountPasswordInvalid)):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise exc


@router.patch("/password", response_model=AccountMessageOut)
async def change_password(
    data: ChangePasswordIn,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        await AccountRepository(session).change_password(
            user_id,
            data.current_password,
            data.new_password,
        )
    except Exception as exc:
        _raise_account_error(exc)
    return {"message": "密码修改成功，请重新登录"}


@router.post("/email-change/code", response_model=AccountMessageOut)
async def send_email_change_code(
    data: SendEmailChangeCodeIn,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
    mail: FastMail = Depends(get_email),
    redis: Redis = Depends(get_redis),
):
    new_email = _normalize_email(str(data.new_email))
    try:
        await AccountRepository(session).validate_email_target(user_id, new_email)
    except Exception as exc:
        _raise_account_error(exc)

    cooldown_set = await redis.set(
        _cooldown_key(user_id),
        "1",
        ex=EMAIL_CODE_COOLDOWN_SECONDS,
        nx=True,
    )
    if not cooldown_set:
        raise HTTPException(status_code=429, detail="验证码发送过于频繁，请稍后再试")

    code = f"{secrets.randbelow(1_000_000):06d}"
    message = MessageSchema(
        subject="【智能起名】绑定邮箱验证码",
        recipients=[new_email],
        body=f"您的绑定邮箱验证码是 {code}，五分钟内有效。",
        subtype=MessageType.plain,
    )
    try:
        await mail.send_message(message)
        await redis.set(
            _code_key(user_id),
            json.dumps({"email": new_email, "code": code, "attempts": 0}),
            ex=EMAIL_CODE_TTL_SECONDS,
        )
    except Exception as exc:
        await redis.delete(_cooldown_key(user_id))
        raise HTTPException(status_code=503, detail="验证码发送失败，请稍后重试") from exc

    return {"message": "验证码已发送至新邮箱"}


@router.patch("/email", response_model=AccountMessageOut)
async def change_email(
    data: ChangeEmailIn,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
):
    new_email = _normalize_email(str(data.new_email))
    key = _code_key(user_id)
    saved_value = await redis.get(key)
    if not saved_value:
        raise HTTPException(status_code=400, detail="验证码不存在或已经过期")

    try:
        saved = json.loads(saved_value)
    except (TypeError, ValueError):
        await redis.delete(key)
        raise HTTPException(status_code=400, detail="验证码已失效，请重新获取")

    if saved.get("email") != new_email or saved.get("code") != data.code:
        attempts = int(saved.get("attempts", 0)) + 1
        if attempts >= EMAIL_CODE_MAX_ATTEMPTS:
            await redis.delete(key)
            raise HTTPException(status_code=400, detail="验证码错误次数过多，请重新获取")
        saved["attempts"] = attempts
        ttl = await redis.ttl(key)
        if ttl <= 0:
            await redis.delete(key)
            raise HTTPException(status_code=400, detail="验证码不存在或已经过期")
        await redis.set(key, json.dumps(saved), ex=ttl)
        raise HTTPException(status_code=400, detail="验证码输入错误，请注意核对")

    try:
        await AccountRepository(session).change_email(user_id, new_email)
    except Exception as exc:
        _raise_account_error(exc)
    try:
        await redis.delete(key, _cooldown_key(user_id))
    except Exception:
        # 数据库修改已经提交，Redis 清理失败不能把成功响应变成误导性的失败。
        logger.exception("Failed to delete used email change code for user %s", user_id)
    return {"message": "绑定邮箱修改成功，请使用新邮箱重新登录"}


@router.delete("", response_model=AccountMessageOut, status_code=status.HTTP_202_ACCEPTED)
async def delete_account(
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        await AccountRepository(session).soft_delete_self(user_id)
    except Exception as exc:
        _raise_account_error(exc)
    return {"message": "账号已注销，个人内容正在清理"}

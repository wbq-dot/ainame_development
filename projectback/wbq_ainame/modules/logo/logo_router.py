from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from core.authtools import AuthHandler
from modules.logo.logo_tools import generate_company_logo
from dependencies import get_session
from repository.credit_repo import CreditRepository, LOGO_CREDIT_COST
from modules.logo.logo_schemas import LogoGenerateIn, LogoGenerateOut
from modules.logo.logo_tools import LOGO_DIR
from models.User import User


router = APIRouter(prefix="/logos", tags=["logos"])
auth_handler = AuthHandler()


async def account_is_active(session: AsyncSession, user_id: int) -> bool:
    status = await session.scalar(select(User.status).where(User.id == user_id))
    return status == "active"


@router.post("/generate", response_model=LogoGenerateOut)
async def generate_logo(
    data: LogoGenerateIn,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    company_name = data.company_name.strip()
    if not company_name:
        raise HTTPException(status_code=400, detail="请输入企业名称")

    credit_repository = CreditRepository(session)
    try:
        remaining_balance = await credit_repository.consume_logo_credit(user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Logo生成需要1次Logo次数，当前余额不足，请先购买Logo套餐",
        ) from exc

    try:
        logo = await run_in_threadpool(
            generate_company_logo,
            company_name=company_name,
            user_id=user_id,
            **data.model_dump(exclude={"company_name"}),
        )
    except Exception as exc:
        await _refund_logo_credit(credit_repository, user_id)
        raise HTTPException(
            status_code=502,
            detail="Logo生成失败，本次Logo次数已退回",
        ) from exc

    if not logo.get("logo_url"):
        await _refund_logo_credit(credit_repository, user_id)
        status = logo.get("logo_status") or "图片模型没有返回有效图片"
        raise HTTPException(
            status_code=502,
            detail=f"{status}；本次Logo次数已退回",
        )

    # 模型调用期间用户可能从其他设备注销；不要在注销清理后写回新文件。
    if not await account_is_active(session, user_id):
        file_name = logo.get("logo_file_name")
        if file_name:
            (LOGO_DIR / file_name).unlink(missing_ok=True)
        raise HTTPException(status_code=401, detail="账号已失效")

    return {
        "company_name": company_name,
        **logo,
        "credit_cost": LOGO_CREDIT_COST,
        "remaining_logo_balance": remaining_balance,
    }


async def _refund_logo_credit(
    credit_repository: CreditRepository,
    user_id: int,
) -> None:
    try:
        await credit_repository.refund_logo_credit(user_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Logo生成失败且次数退回异常，请联系管理员处理",
        ) from exc

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.authtools import AuthHandler
from dependencies import get_session
from repository.credit_repo import CreditRepository
from schemas.credit_schemas import CreditBalanceOut

# 登录之后操作其他页面免登录
auth_handler = AuthHandler()
router = APIRouter(prefix="/credit")


@router.get("/balance",response_model=CreditBalanceOut)
# 获取次数，必须已经登录了，只需要把JWT 解码的 id 传入到参数中就可以实现
async def get_credit_balance(user_id: int=Depends(auth_handler.auth_access_dependency),session:AsyncSession=Depends(get_session)):
    # 去账户表，查询自己有几次起名的余额
    creditRepository = CreditRepository(session)
    name_balance, logo_balance = await creditRepository.get_balances(user_id)
    return CreditBalanceOut(
        balance=name_balance,
        name_balance=name_balance,
        logo_balance=logo_balance,
    )

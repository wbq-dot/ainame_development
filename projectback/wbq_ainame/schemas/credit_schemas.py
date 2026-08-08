
from pydantic import BaseModel

# 用来得到次数余额查询的返回模版
class CreditBalanceOut(BaseModel):
    balance: int
    name_balance: int
    logo_balance: int

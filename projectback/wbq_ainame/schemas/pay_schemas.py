from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

# 客户传入的套餐信息
class CreateOrderIn(BaseModel):
    package_id:int

# 返回一个支付信息 订单号 金额 次数  支付地址
class CreateOrderOut(BaseModel):
    order_no: str
    amount: Decimal
    credit_count: int
    credit_type: Literal["name", "logo"]
    pay_url: str

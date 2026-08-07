
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PackageOut(BaseModel):
    id: int
    name: str
    price: Decimal
    credit_count: int
    # 当模型的结构和表的结构不完全一致时 ConfigDict(from_attributes=True) 返回数据库的部分 model 数据填到路由的 model 中
    model_config = ConfigDict(from_attributes=True)
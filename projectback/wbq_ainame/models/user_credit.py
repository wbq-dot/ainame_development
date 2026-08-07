from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, MappedColumn
from . import Base


class UserCredit(Base):
    # 这个数据库表主要记录的是起名的账户有几次
    __tablename__ = "user_credit"

    id:Mapped[int] = MappedColumn(Integer, primary_key=True,autoincrement=True)
    # unique=True  每个用户只能有一条账目记录， index=True 便于查询
    user_id:Mapped[int] = MappedColumn(Integer,ForeignKey("user.id"),unique=True,nullable=False,index=True)
    # default=0,nullable=False  不设定值时默认填入 0
    balance:Mapped[int] = MappedColumn(Integer,default=0,nullable=False)

    total_used:Mapped[int] = MappedColumn(Integer,default=0,nullable=False)

    total_recharge:Mapped[int] = MappedColumn(Integer,default=0,nullable=False)
    # default=datetime.now,nullable=False   创建时就设定为创建的当下时间
    created_at:Mapped[datetime] = MappedColumn(DateTime,default=datetime.now,nullable=False)
    # default=datetime.now  创建时 updated_at 也填充为创建的当下时间    onupdate=datetime.now  当进行数据的修改，填充修改的当下时间
    updated_at:Mapped[datetime] = MappedColumn(DateTime,default=datetime.now,onupdate=datetime.now,nullable=False)

class CreditLog(Base):
    __tablename__ = "credit_log"

    id:Mapped[int] = MappedColumn(Integer,primary_key=True,autoincrement=True)
    # unique=False 流水表将所有客户的所有流水计入一张流数表，一个用户有多个流水
    user_id:Mapped[int] = MappedColumn(Integer,ForeignKey("user.id"),unique=False,nullable=False,index=True)

    change_count:Mapped[int] = MappedColumn(Integer,default=0,nullable=False)
    #  balance_after == update balance
    balance_after:Mapped[int] = MappedColumn(Integer,nullable=False)

    type:Mapped[str]=MappedColumn(String(200),nullable=False)

    remark:Mapped[str]=MappedColumn(String(200),nullable=True)

    created_at:Mapped[datetime] = MappedColumn(DateTime,default=datetime.now,nullable=False)









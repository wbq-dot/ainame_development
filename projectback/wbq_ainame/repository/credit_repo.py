from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user_credit import UserCredit, CreditLog

class CreditRepository:
   def __init__(self,session:AsyncSession):
       self.session = session

   # 表 == 类  列名 == 属性名  一条数据 == 一个实例对象  实例化对象 == 插入数据  对象.属性 == 这一条数据在该列的值 (CURD)
   #注册账号，赠送3次
   async def create_register_credit(self,user_id:int,gift_count:int=3):
       async with self.session.begin():
           # 注册给我的账户充值3次，拿到用户、自定义给出赠送次数(默认)、没有使用 和 没有充值
          credit =  UserCredit(
               user_id = user_id,
               balance = gift_count,
               total_used=0,
               total_recharge=0
           )
          self.session.add(credit)
         # 注册后流水记录，拿到用户、改变的次数 +3、变换后剩余次数 3、类型注册赠送、说明
          log = CreditLog(
              user_id = user_id,
              change_count=gift_count,
              balance_after=gift_count,
              type="register_gift",
              remark=f"注册赠送{gift_count}次起名机会"
          )
          self.session.add(log)
          await self.session.flush()

          return credit

    # 查询剩余次数
   async def get_balance(self, user_id: int) -> int:

       async with self.session.begin():
           # 查到的是 id 一致的一条数据 == Python 的实例化对象
           credit = await self.session.scalar(
               select(UserCredit).where(UserCredit.user_id == user_id)
           )
        # 不是我的用户次数就是0
       if not credit:
           return 0
       # 对象.balance = 表中该条数据中balance对应的数据
       return credit.balance

    # 起名消费次数
   async def consume_name_credit(self, user_id: int) -> int:
       async with self.session.begin():
           credit = await self.session.scalar(select(UserCredit).
                where(UserCredit.user_id == user_id).with_for_update())  # .with_for_update() 锁表查询数据，不让用户直接提交数据时相互影响，先执行一个事务再执行另一个事务
           if not credit:
               raise ValueError("用户次数账户不存在")
           if credit.balance <= 0:
               raise ValueError("起名次数不足")
           # 1.修改 UserCredit  次数 -1 使用 +1
           credit.balance -= 1    # 对象.属性 = 新值    等价 credit.balance = credit.balance - 1
           credit.total_used += 1
           # CreditLog  每次操作重新写入新的流水
           log = CreditLog(
               user_id=user_id,
               change_count=-1,  # 改变增加 + 减小 -
               balance_after=credit.balance,  # 修改之后的 balance
               type="name_consume",
               remark="起名消耗1次",
           )
           self.session.add(log)
           await self.session.flush()   # 数据直接返回数据库不等待
       return credit.balance




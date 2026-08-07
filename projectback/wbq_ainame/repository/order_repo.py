from models.package import Package
from models.user_order import UserOrder
from datetime import datetime
import random
from sqlalchemy import select
from models.user_credit import UserCredit,CreditLog

class OrderRepo:

    def __init__(self,session):
        self.session = session

    # 生成订单号   字符串（时间 + 随机整数）
    def create_order_no(self):
        time_str = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = str(random.randint(100000, 999999))  # random.randint(a, b)  从 [a , b] 中随机选择一个整数
        return time_str+random_str

    async def create_order(self,user_id:int,package:Package):
        async with self.session.begin():
           order =  UserOrder(
                order_no=self.create_order_no(),
                user_id = user_id,
                package_id=package.id,
                amount=package.price,
                credit_count=package.credit_count,
                status="pending"
            )
           self.session.add(order)
           await self.session.flush()   # 立即存表，进行支付连接的生成
           return order

    async def get_by_order_no(self, order_no):
        async with self.session.begin():
            order = await  self.session.scalar(select(UserOrder).where(UserOrder.order_no == order_no))
            return order

    async def pay_success(self, order_no, alipay_trade_no):
        async with self.session.begin():
            order = await self.session.scalar(select(UserOrder).where(UserOrder.order_no == order_no).with_for_update())

            if not order:
                raise ValueError("订单不存在")

            # 订单可能被多次异步调用，所以，非常必要判断状态，如果已经做过处理，避免重复处理
            if order.status == "paid":
                return order, False

            # 未支付状态
            if order.status != "pending":
                raise ValueError("订单状态异常")

            # 把订单变成已付款 已付款、交易号和付款时间
            order.status = "paid"
            order.alipay_trade_no = alipay_trade_no
            order.paid_at = datetime.now()

            # 修改账户次数
            userCredit: UserCredit = await self.session.scalar(
                select(UserCredit).where(UserCredit.user_id == order.user_id).with_for_update())
            userCredit.balance = userCredit.balance + order.credit_count

            # 加流水
            log = CreditLog(
                user_id=order.user_id,
                change_count=order.credit_count,
                balance_after=userCredit.balance,
                type="recharge",
                remark=f"支付成功，充值次数为{order.credit_count}"
            )
            self.session.add(log)
            return order, True
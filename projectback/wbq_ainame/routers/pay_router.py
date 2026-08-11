from fastapi import APIRouter, Depends, HTTPException,Request
from sqlalchemy.ext.asyncio import AsyncSession
from core.alipaytools import (
    build_alipay_page_pay_url,
    create_alipay,
    get_notify_url,
    get_return_url,
)
from core.authtools import AuthHandler
from dependencies import get_session
from models.user_order import UserOrder
from repository.order_repo import OrderRepo
from repository.package_repo import PackageRepository
from schemas.pay_schemas import CreateOrderIn, CreateOrderOut
from fastapi.responses import HTMLResponse
from fastapi.responses import PlainTextResponse
from decimal import Decimal


router = APIRouter(prefix="/pay", tags=["pay"])
auth_handler = AuthHandler()

@router.post("/create_order", response_model=CreateOrderOut)
async def create_order(data: CreateOrderIn,
user_id: int = Depends(auth_handler.auth_access_dependency),  # 即进行校验也进行注入，填充user_id
session: AsyncSession = Depends(get_session)
):
    package_repo = PackageRepository(session=session)
    order_repo = OrderRepo(session=session)
    # 1. 查询套餐  -- 一条套餐的数据
    package = await package_repo.get_by_id(data.package_id)
    if not package:
        raise HTTPException(status_code=400, detail="套餐不存在或已下架")

    # 2.去生成订单 -- 用户信息 + 套餐信息 -> await 立马生成订单
    order: UserOrder = await order_repo.create_order(user_id, package)

    # 3.使用统一参数生成支付宝链接
    pay_url = build_alipay_page_pay_url(
        out_trade_no=order.order_no,
        subject=f"购买{package.name}",
        total_amount=str(order.amount),
        notify_url=get_notify_url(),
        return_url=get_return_url(),
    )

    # CreateOrderOut 本身就是类，可以实例化对象返回
    return CreateOrderOut(
        order_no=order.order_no,
        amount=order.amount,
        credit_count=order.credit_count,
        credit_type=order.credit_type,
        pay_url=pay_url)



# 支付的过程:  传入购买的套餐号 -> 生成订单 -> 支付宝链接 -> 输入密码 -> 支付宝流转 ->  return_url (给客户展示支付成功，使用get方式访问)
#                                                                      ->  notify_url (返回公网服务器，进行订单支付校验和完整订单生成，使用post 方式访问)

# notify_url
@router.post("/paySuccess")   # 填的路由 == ALIPAY_NOTIFY_URL
async def alipay_notify(request: Request, session: AsyncSession = Depends(get_session)):
    # 异步代码，此处需要公网服务器，不能运行。但是逻辑是必须理解的
    # 1.获取支付宝post过来的表单
    form_data = await request.form()
    notify_data = dict(form_data)  # 字典格式

    # 2.pop 取参数，之后扔掉，防止泄露或者干扰后续操作
    sign = notify_data.pop("sign", None)    # 取签名的值，通过这个对上是这个客户付的款

    notify_data.pop("sign_type", None)    # 把类型直接扔掉，防止后续干扰

    if not sign:
        raise HTTPException(400, "订单不存在")

    alipay = create_alipay()
    verify_result = alipay.verify(notify_data, sign)    # 校验，确保收到的支付回调确实来自支付宝官方，且数据在传输过程中未被篡改。

    if not verify_result:
        return PlainTextResponse("failure")       # 支付宝传递信息的过程中异常

    # 字典的方式来取值
    order_no = notify_data.get("out_trade_no")
    total_amount = notify_data.get("total_amount")
    alipay_trade_no = notify_data.get("trade_no")
    trade_status = notify_data.get("trade_status")

    if not order_no:
        return PlainTextResponse("failure")    # 订单号不存在也是失败

    if trade_status not in ["TRADE_SUCCESS", "TRADE_FINISHED"]:
        return PlainTextResponse("failure")    # 不是交易成功和交易完成的字样 失败


    order_repo = OrderRepo(session)

    # 验证订单是否存在
    order:UserOrder = await order_repo.get_by_order_no(order_no)

    if not order:
        return PlainTextResponse("failure")    # 后端没有前端订单也失败

    if Decimal(str(order.amount)) != Decimal(str(total_amount)):  # 转换成 Decimal 精确小数
        return PlainTextResponse("failure")   # 付的款不对

    # 修改订单状态，增加账户次数，写流水
    await  order_repo.pay_success(order_no,alipay_trade_no)

    return PlainTextResponse("success")



# 异步无法调用，只能使用浏览器端帮助跳转到 notify_url 测试
@router.get("/success", response_class=HTMLResponse)   # ALIPAY_RETURN_URL == 路由地址  使用html回复写在网页上
async def pay_success(
    request: Request,
    session: AsyncSession = Depends(get_session),
):

    # 真实情况下给浏览器的返回
    # return """
    # <html>
    #     <head>
    #         <meta charset="utf-8">
    #         <title>支付完成</title>
    #     </head>
    #     <body>
    #         <h2>支付完成</h2>
    #         <p>如果您已经完成付款，请返回系统查看订单状态。</p>
    #         <p>注意：次数到账以支付宝异步通知结果为准。</p>
    #     </body>
    # </html>
    # """


    # 1. 获取支付宝浏览器跳转回来时携带的参数
    params = dict(request.query_params)   # query_params  http://xxx:xx/xx?query_params   把传过来的参数变成键值对的字典

    # 2. 验签
    sign = params.pop("sign", None)
    params.pop("sign_type", None)

    # 没有签名，抛异常
    if not sign:
        return """
                <html>
                    <head><meta charset="utf-8"></head>
                    <body>
                        <h2>支付结果异常</h2>
                        <p>没有获取到支付宝签名。</p>
                    </body>
                </html>
                """
    alipay = create_alipay()
    verify_result = alipay.verify(params, sign)

    # 验签失败，检查配置
    if not verify_result:
        return """
               <html>
                   <head><meta charset="utf-8"></head>
                   <body>
                       <h2>支付结果异常</h2>
                       <p>支付宝验签失败，请检查支付宝公钥配置。</p>
                   </body>
               </html>
               """

    # 3. 获取交易信息，交易成功才能给客户端返回，不需要校验交易状态
    order_no = params.get("out_trade_no")
    alipay_trade_no = params.get("trade_no", "")
    total_amount = params.get("total_amount")

    if not order_no:
        return """
           <html>
               <head><meta charset="utf-8"></head>
               <body>
                   <h2>支付结果异常</h2>
                   <p>没有获取到订单号 out_trade_no。</p>
               </body>
           </html>
           """

    order_repo = OrderRepo(session=session)
    order = await order_repo.get_by_order_no(order_no)

    if not order:
        return """
           <html>
               <head><meta charset="utf-8"></head>
               <body>
                   <h2>支付结果异常</h2>
                   <p>订单不存在。</p>
               </body>
           </html>
           """
    # 4. 校验金额，防止有人伪造回跳地址
    if total_amount is not None:
        if Decimal(str(order.amount)) != Decimal(str(total_amount)):
            return """
               <html>
                   <head><meta charset="utf-8"></head>
                   <body>
                       <h2>支付结果异常</h2>
                       <p>订单金额校验失败。</p>
                   </body>
               </html>
               """

    # 5. 修改数据库：
    # 订单 pending -> paid
    # 增加用户次数
    # 写入次数流水
    try:

        order, is_first_success = await order_repo.pay_success(
            order_no=order_no,
            alipay_trade_no=alipay_trade_no,
        )     # 修改订单，增加次数，写入流水，返回完整订单 和 bool
    except Exception as e:
        return f"""
           <html>
               <head><meta charset="utf-8"></head>
               <body>
                   <h2>支付处理失败</h2>
                   <p>{str(e)}</p>
               </body>
           </html>
           """
        # 7. 返回支付成功页面 True 修改成功   False  多次提交，不该我的购买次数
    if is_first_success:
        credit_label = "Logo" if order.credit_type == "logo" else "起名"
        message = f"支付成功，已为您增加 {order.credit_count} 次{credit_label}次数。"
    else:
        message = "该订单之前已经处理过，请不要重复刷新页面。"

    return f"""
       <html>
           <head>
               <meta charset="utf-8">
               <title>支付完毕</title>
           </head>
           <body>
               <h2>支付完毕</h2>
               <p>{message}</p>
               <p>订单号：{order.order_no}</p>
               <p>订单状态：{order.status}</p>
           </body>
       </html>
       """




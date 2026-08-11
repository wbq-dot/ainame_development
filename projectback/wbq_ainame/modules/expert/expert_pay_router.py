from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.alipaytools import create_alipay
from core.authtools import AuthHandler
from dependencies import get_session
from modules.expert.expert_models import ExpertOrder
from modules.expert.expert_repo import ExpertDomainError, ExpertRepository


router = APIRouter(prefix="/expert-pay", tags=["expert-pay"])
auth_handler = AuthHandler()


@router.post("/notify")
async def expert_alipay_notify(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    notify_data = dict(await request.form())
    sign = notify_data.pop("sign", None)
    notify_data.pop("sign_type", None)
    if not sign or not create_alipay().verify(notify_data, sign):
        return PlainTextResponse("failure")
    if notify_data.get("trade_status") not in {"TRADE_SUCCESS", "TRADE_FINISHED"}:
        return PlainTextResponse("failure")
    order_no = notify_data.get("out_trade_no")
    trade_no = notify_data.get("trade_no")
    total_amount = notify_data.get("total_amount")
    if not order_no or not trade_no or total_amount is None:
        return PlainTextResponse("failure")
    try:
        await ExpertRepository(session).mark_paid(
            order_no, trade_no, Decimal(str(total_amount))
        )
    except ExpertDomainError:
        return PlainTextResponse("failure")
    return PlainTextResponse("success")


@router.get("/return", response_class=HTMLResponse)
async def expert_alipay_return(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    params = dict(request.query_params)
    sign = params.pop("sign", None)
    params.pop("sign_type", None)
    if not sign or not create_alipay().verify(params, sign):
        return "<meta charset='utf-8'><h2>支付结果验证失败</h2><p>请返回知名台查看订单状态。</p>"
    order_no = params.get("out_trade_no")
    total_amount = params.get("total_amount")
    trade_no = params.get("trade_no", "")
    if not order_no or total_amount is None:
        return "<meta charset='utf-8'><h2>支付结果缺少订单信息</h2>"
    try:
        order, first = await ExpertRepository(session).mark_paid(
            order_no, trade_no, Decimal(str(total_amount))
        )
    except ExpertDomainError as exc:
        return f"<meta charset='utf-8'><h2>支付处理失败</h2><p>{str(exc)}</p>"
    message = "支付成功，等待专家接单。" if first else "该订单已处理，请勿重复刷新。"
    return (
        "<meta charset='utf-8'><h2>专家精批订单</h2>"
        f"<p>{message}</p><p>订单号：{order.order_no}</p>"
    )


@router.get("/status/{order_no}")
async def expert_payment_status(
    order_no: str,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    order = await session.scalar(
        select(ExpertOrder).where(
            ExpertOrder.order_no == order_no,
            ExpertOrder.user_id == user_id,
        )
    )
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return {
        "order_no": order.order_no,
        "payment_status": order.payment_status,
        "service_status": order.service_status,
    }


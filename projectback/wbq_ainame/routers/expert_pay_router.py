import logging
from html import escape

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.alipaytools import (
    PaymentConfigurationError,
    parse_alipay_amount,
    verify_alipay_response,
)
from dependencies import get_session
from repository.expert_repo import ExpertDomainError, ExpertRepository


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/expert-pay", tags=["expert-pay"])
PAID_STATUSES = {"TRADE_SUCCESS", "TRADE_FINISHED"}


@router.post("/notify")
async def expert_alipay_notify(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    try:
        notify_data = verify_alipay_response(
            dict(await request.form()),
            require_seller_id=True,
        )
        if notify_data is None or notify_data.get("trade_status") not in PAID_STATUSES:
            return PlainTextResponse("failure")
        order_no = notify_data.get("out_trade_no")
        trade_no = notify_data.get("trade_no")
        total_amount = parse_alipay_amount(notify_data.get("total_amount"))
        if not order_no or not trade_no or total_amount is None:
            return PlainTextResponse("failure")
        await ExpertRepository(session).mark_paid(
            order_no,
            trade_no,
            total_amount,
        )
    except (PaymentConfigurationError, ExpertDomainError):
        return PlainTextResponse("failure")
    except Exception:
        logger.exception("专家订单支付宝异步通知处理失败")
        return PlainTextResponse("failure")
    return PlainTextResponse("success")


@router.get("/return", response_class=HTMLResponse)
async def expert_alipay_return(
    request: Request,
):
    try:
        params = verify_alipay_response(dict(request.query_params))
    except PaymentConfigurationError:
        params = None
    except Exception:
        logger.exception("专家订单支付宝同步回跳验签失败")
        params = None
    if params is None:
        return (
            "<meta charset='utf-8'><h2>支付结果验证失败</h2>"
            "<p>请勿依据当前页面判断是否到账，请返回知名台查看订单状态。</p>"
        )
    order_no = params.get("out_trade_no")
    if not order_no:
        return (
            "<meta charset='utf-8'><h2>支付结果缺少订单信息</h2>"
            "<p>请返回知名台查看订单状态。</p>"
        )
    return (
        "<meta charset='utf-8'><h2>专家精批订单</h2>"
        "<p>支付页面已返回，系统正在等待支付宝异步通知确认到账。</p>"
        f"<p>订单号：{escape(str(order_no))}</p>"
        "<p>请返回知名台的专家订单页面查看最新状态。</p>"
    )


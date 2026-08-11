import logging
from decimal import Decimal, InvalidOperation
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

import settings
from core.alipaytools import (
    PaymentConfigurationError,
    create_alipay,
    get_alipay_gateway,
    get_notify_url,
    get_return_url,
)
from core.authtools import AuthHandler
from dependencies import get_session
from repository.order_repo import OrderRepo
from repository.package_repo import PackageRepository
from repository.payment_repo import (
    PaymentConflict,
    PaymentNotFound,
    PaymentRepository,
    RefundNotEligible,
)
from schemas.pay_schemas import (
    CreateOrderIn,
    CreateOrderOut,
    OrderListOut,
    OrderOut,
    RefundOut,
    RefundRequestIn,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pay", tags=["pay"])
auth_handler = AuthHandler()
PAID_STATUSES = {"TRADE_SUCCESS", "TRADE_FINISHED"}


def _payment_unavailable(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


@router.post("/create_order", response_model=CreateOrderOut)
async def create_order(
    data: CreateOrderIn,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        alipay = create_alipay()
    except PaymentConfigurationError as exc:
        raise _payment_unavailable(exc) from exc

    package = await PackageRepository(session).get_by_id(data.package_id)
    if not package:
        raise HTTPException(status_code=400, detail="套餐不存在或已下架")
    order = await OrderRepo(session).create_order(user_id, package)
    order_string = alipay.api_alipay_trade_page_pay(
        out_trade_no=order.order_no,
        subject=f"购买{package.name}",
        total_amount=str(order.amount),
        timeout_express=f"{settings.PAYMENT_ORDER_TIMEOUT_MINUTES}m",
        notify_url=get_notify_url(),
        return_url=get_return_url(),
    )
    return {
        "order_no": order.order_no,
        "amount": order.amount,
        "credit_count": order.credit_count,
        "credit_type": order.credit_type,
        "pay_url": f"{get_alipay_gateway()}?{order_string}",
        "status": order.status,
        "expires_at": order.expires_at,
    }


@router.post("/paySuccess")
async def alipay_notify(
    request: Request, session: AsyncSession = Depends(get_session)
):
    try:
        form_data = dict(await request.form())
        sign = form_data.pop("sign", None)
        sign_type = form_data.pop("sign_type", None)
        if not sign or sign_type != "RSA2":
            return PlainTextResponse("failure")
        alipay = create_alipay()
        if not alipay.verify(form_data, sign):
            return PlainTextResponse("failure")
        if form_data.get("app_id") != settings.ALIPAY_APP_ID:
            return PlainTextResponse("failure")
        if form_data.get("seller_id") != settings.ALIPAY_SELLER_ID:
            return PlainTextResponse("failure")

        order_no = form_data.get("out_trade_no")
        trade_no = form_data.get("trade_no")
        trade_status = form_data.get("trade_status")
        total_amount = form_data.get("total_amount")
        if not order_no:
            return PlainTextResponse("failure")
        order = await OrderRepo(session).get_by_order_no(order_no)
        if not order:
            return PlainTextResponse("failure")
        try:
            amount_matches = Decimal(str(order.amount)) == Decimal(str(total_amount))
        except (InvalidOperation, ValueError):
            amount_matches = False
        if not amount_matches:
            return PlainTextResponse("failure")

        repository = PaymentRepository(session)
        if trade_status in PAID_STATUSES:
            if not trade_no:
                return PlainTextResponse("failure")
            await repository.record_payment_success(order_no, trade_no)
        elif trade_status == "TRADE_CLOSED":
            await repository.record_provider_closed(order_no)
        return PlainTextResponse("success")
    except (PaymentConfigurationError, PaymentNotFound, PaymentConflict):
        return PlainTextResponse("failure")
    except Exception:
        logger.exception("支付宝异步通知处理失败")
        return PlainTextResponse("failure")


def _result_redirect(order_no: str | None, verified: bool) -> RedirectResponse:
    target = settings.PAYMENT_FRONTEND_RESULT_URL
    separator = "&" if "?" in target.split("#", 1)[-1] else "?"
    query = f"verified={1 if verified else 0}"
    if order_no:
        query = f"order_no={quote(order_no)}&{query}"
    return RedirectResponse(f"{target}{separator}{query}", status_code=302)


@router.get("/success")
async def pay_success(request: Request):
    params = dict(request.query_params)
    sign = params.pop("sign", None)
    sign_type = params.pop("sign_type", None)
    order_no = params.get("out_trade_no")
    if not sign or sign_type != "RSA2":
        return _result_redirect(None, False)
    try:
        verified = create_alipay().verify(params, sign)
    except PaymentConfigurationError:
        verified = False
    if not verified or params.get("app_id") != settings.ALIPAY_APP_ID:
        return _result_redirect(None, False)
    return _result_redirect(order_no, True)


@router.get("/orders", response_model=OrderListOut)
async def list_orders(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    items, total = await PaymentRepository(session).list_user_orders(
        user_id, page, page_size
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/orders/{order_no}", response_model=OrderOut)
async def get_order(
    order_no: str,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await PaymentRepository(session).get_user_order(order_no, user_id)
    except PaymentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/orders/{order_no}/refunds", response_model=RefundOut, status_code=201
)
async def request_refund(
    order_no: str,
    data: RefundRequestIn,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await PaymentRepository(session).create_refund_request(
            order_no, user_id, data.reason
        )
    except PaymentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (PaymentConflict, RefundNotEligible) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

import logging
from decimal import Decimal
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
    parse_alipay_amount,
    verify_alipay_response,
)
from core.authtools import AuthHandler
from dependencies import get_session
from repository.order_repo import OrderRepo, PackageUnavailableError
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

    order_repo = OrderRepo(session=session)
    # 查询并锁定套餐、校验上架状态、创建订单必须原子完成。
    try:
        order, package = await order_repo.create_order(user_id, data.package_id)
    except PackageUnavailableError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
        form_data = verify_alipay_response(
            dict(await request.form()),
            require_seller_id=True,
        )
        if form_data is None:
            return PlainTextResponse("failure")

        order_no = form_data.get("out_trade_no")
        trade_no = form_data.get("trade_no")
        trade_status = form_data.get("trade_status")
        total_amount = parse_alipay_amount(form_data.get("total_amount"))
        if not order_no:
            return PlainTextResponse("failure")
        order = await OrderRepo(session).get_by_order_no(order_no)
        if not order:
            return PlainTextResponse("failure")
        if total_amount is None or Decimal(str(order.amount)) != total_amount:
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
    try:
        params = verify_alipay_response(dict(request.query_params))
    except PaymentConfigurationError:
        params = None
    except Exception:
        logger.exception("支付宝同步回跳验签失败")
        params = None
    if params is None:
        return _result_redirect(None, False)
    return _result_redirect(params.get("out_trade_no"), True)


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

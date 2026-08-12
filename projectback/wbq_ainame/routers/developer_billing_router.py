from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

import settings
from core.alipaytools import PaymentConfigurationError, build_alipay_page_pay_url, create_alipay, get_notify_url, get_return_url
from dependencies import get_session
from core.platform_auth import developer_auth
from models.platform_models import DeveloperAccount
from repository.platform_repo import PlatformConflict, PlatformNotFound, PlatformRepository
from schemas.platform_schemas import ApiOrderCreateIn, ApiRefundIn


router = APIRouter(prefix="/developer/billing", tags=["developer-billing"])


def _notify_url() -> str: return get_notify_url().replace("/pay/paySuccess", "/developer/billing/alipay/notify")
def _return_url() -> str: return get_return_url().replace("/pay/success", "/developer/billing/alipay/return")


@router.get("/packages")
async def packages(session: AsyncSession = Depends(get_session)): return await PlatformRepository(session).list_packages(True)


@router.post("/orders", status_code=201)
async def create_order(data: ApiOrderCreateIn, developer: DeveloperAccount = Depends(developer_auth.access), session: AsyncSession = Depends(get_session)):
    repo = PlatformRepository(session)
    try: order = await repo.create_order(developer.id, data.package_id, data.use_promotion_balance)
    except PlatformNotFound as exc: raise HTTPException(404, str(exc)) from exc
    pay_url = None
    if order.cash_amount > 0:
        try: pay_url = build_alipay_page_pay_url(out_trade_no=order.order_no, subject=f"开放平台-{order.package_name}", total_amount=str(order.cash_amount), return_url=_return_url(), notify_url=_notify_url())
        except PaymentConfigurationError as exc:
            await repo.close_order(order.order_no, "支付配置不可用")
            raise HTTPException(503, str(exc)) from exc
    return {"order_no": order.order_no, "package_name": order.package_name, "credit_count": order.credit_count, "total_amount": order.total_amount, "promotion_amount": order.promotion_amount, "cash_amount": order.cash_amount, "status": order.status, "pay_url": pay_url, "created_at": order.created_at, "expires_at": order.expires_at, "paid_at": order.paid_at}


@router.get("/orders")
async def orders(developer: DeveloperAccount = Depends(developer_auth.access), session: AsyncSession = Depends(get_session)): return await PlatformRepository(session).list_orders(developer.id)


@router.post("/orders/{order_no}/refresh")
async def refresh_order(order_no: str, developer: DeveloperAccount = Depends(developer_auth.access), session: AsyncSession = Depends(get_session)):
    orders = await PlatformRepository(session).list_orders(developer.id)
    order = next((item for item in orders if item.order_no == order_no), None)
    if not order: raise HTTPException(404, "订单不存在")
    if order.status != "pending" or order.cash_amount <= 0: return order
    try:
        result = await __import__("asyncio").to_thread(create_alipay().api_alipay_trade_query, out_trade_no=order_no)
    except PaymentConfigurationError as exc: raise HTTPException(503, str(exc)) from exc
    except Exception as exc: raise HTTPException(502, "支付宝查单暂不可用") from exc
    if result.get("code") == "10000" and result.get("trade_status") in {"TRADE_SUCCESS", "TRADE_FINISHED"}:
        await session.rollback()
        await PlatformRepository(session).record_order_paid(order_no, Decimal(result.get("total_amount", "")), result.get("trade_no", ""))
        orders = await PlatformRepository(session).list_orders(developer.id)
        order = next(item for item in orders if item.order_no == order_no)
    return order


@router.post("/orders/{order_no}/refunds", status_code=201)
async def refund(order_no: str, data: ApiRefundIn, developer: DeveloperAccount = Depends(developer_auth.access), session: AsyncSession = Depends(get_session)):
    try: return await PlatformRepository(session).request_refund(developer.id, order_no, data.reason)
    except PlatformConflict as exc: raise HTTPException(409, str(exc)) from exc


@router.post("/alipay/notify")
async def alipay_notify(request: Request, session: AsyncSession = Depends(get_session)):
    try:
        form = dict(await request.form()); sign = form.pop("sign", None); sign_type = form.pop("sign_type", None)
        alipay = create_alipay()
        if not sign or sign_type != "RSA2" or not alipay.verify(form, sign): return PlainTextResponse("failure")
        if form.get("app_id") != settings.ALIPAY_APP_ID or form.get("seller_id") != settings.ALIPAY_SELLER_ID: return PlainTextResponse("failure")
        if form.get("trade_status") in {"TRADE_SUCCESS", "TRADE_FINISHED"}:
            await PlatformRepository(session).record_order_paid(form.get("out_trade_no", ""), Decimal(form.get("total_amount", "")), form.get("trade_no", ""))
        return PlainTextResponse("success")
    except (PaymentConfigurationError, PlatformConflict, InvalidOperation, ValueError): return PlainTextResponse("failure")


@router.get("/alipay/return")
async def alipay_return(request: Request):
    form = dict(request.query_params); sign = form.pop("sign", None); sign_type = form.pop("sign_type", None)
    verified = False
    try:
        verified = bool(sign and sign_type == "RSA2" and create_alipay().verify(form, sign) and form.get("app_id") == settings.ALIPAY_APP_ID)
    except PaymentConfigurationError:
        pass
    separator = "&" if "?" in settings.DEVELOPER_PAYMENT_RESULT_URL.split("#", 1)[-1] else "?"
    return RedirectResponse(f"{settings.DEVELOPER_PAYMENT_RESULT_URL}{separator}verified={1 if verified else 0}", status_code=302)

import asyncio
import logging
from datetime import datetime
from decimal import Decimal

import settings
from core.alipaytools import create_alipay, parse_alipay_amount
from models import AsyncSessionFactory
from repository.payment_repo import PaymentRepository


logger = logging.getLogger(__name__)
PAID_STATUSES = {"TRADE_SUCCESS", "TRADE_FINISHED"}
DEFINITE_REFUND_FAILURES = {
    "ACQ.TRADE_NOT_EXIST",
    "ACQ.TRADE_STATUS_ERROR",
    "ACQ.REFUND_AMT_NOT_EQUAL_TOTAL",
    "ACQ.REASON_TRADE_REFUND_FEE_ERR",
    "ACQ.TRADE_HAS_FINISHED",
}


async def reconcile_order(order_no: str) -> None:
    async with AsyncSessionFactory() as session:
        repository = PaymentRepository(session)
        order = await repository.get_order_for_reconcile(order_no)
    if not order or order.status != "pending":
        return

    try:
        alipay = create_alipay()
        result = await asyncio.to_thread(
            alipay.api_alipay_trade_query, out_trade_no=order_no
        )
        code = str(result.get("code", ""))
        trade_status = result.get("trade_status")
        if code == "10000" and trade_status in PAID_STATUSES:
            if result.get("out_trade_no") != order_no:
                raise ValueError("支付宝查单返回了其他商户订单号")
            if parse_alipay_amount(result.get("total_amount")) != Decimal(str(order.amount)):
                raise ValueError("支付宝查单金额与本地订单不一致")
            trade_no = result.get("trade_no")
            if not trade_no:
                raise ValueError("支付宝查单未返回交易号")
            async with AsyncSessionFactory() as write_session:
                await PaymentRepository(write_session).record_payment_success(
                    order_no, trade_no
                )
            return
        if code == "10000" and trade_status == "TRADE_CLOSED":
            async with AsyncSessionFactory() as write_session:
                await PaymentRepository(write_session).record_provider_closed(order_no)
            return
        if code == "10000" and trade_status == "WAIT_BUYER_PAY":
            if datetime.now() >= order.expires_at:
                close_result = await asyncio.to_thread(
                    alipay.api_alipay_trade_close, out_trade_no=order_no
                )
                if str(close_result.get("code", "")) == "10000":
                    async with AsyncSessionFactory() as write_session:
                        await PaymentRepository(write_session).record_provider_closed(
                            order_no
                        )
                    return
            raise RuntimeError("支付宝订单仍待付款")
        if result.get("sub_code") == "ACQ.TRADE_NOT_EXIST" and datetime.now() >= order.expires_at:
            async with AsyncSessionFactory() as write_session:
                await PaymentRepository(write_session).record_provider_closed(order_no)
            return
        raise RuntimeError(
            result.get("sub_msg") or result.get("msg") or "支付宝查单结果不确定"
        )
    except Exception as exc:
        logger.warning("支付查单暂未完成：订单=%s，异常=%s", order_no, type(exc).__name__)
        async with AsyncSessionFactory() as retry_session:
            await PaymentRepository(retry_session).schedule_order_retry(
                order_no, str(exc)
            )


async def process_refund(refund_no: str) -> None:
    async with AsyncSessionFactory() as session:
        pair = await PaymentRepository(session).get_refund_for_processing(refund_no)
    if not pair:
        return
    refund, order = pair
    if refund.status != "processing":
        return

    try:
        alipay = create_alipay()
        query = await asyncio.to_thread(
            alipay.api_alipay_trade_fastpay_refund_query,
            refund.refund_no,
            out_trade_no=order.order_no,
        )
        query_code = str(query.get("code", ""))
        refund_status = query.get("refund_status")
        if query_code == "10000" and (
            refund_status == "REFUND_SUCCESS" or query.get("refund_amount") is not None
        ):
            async with AsyncSessionFactory() as write_session:
                await PaymentRepository(write_session).finalize_refund_success(
                    refund_no, parse_alipay_amount(query.get("refund_amount"))
                )
            return

        query_sub_code = query.get("sub_code")
        if query_code != "10000" and query_sub_code not in {
            "ACQ.TRADE_NOT_EXIST",
            "ACQ.REFUND_NOT_EXIST",
        }:
            raise RuntimeError(
                query.get("sub_msg") or query.get("msg") or "支付宝查退结果不确定"
            )

        result = await asyncio.to_thread(
            alipay.api_alipay_trade_refund,
            str(refund.amount),
            out_trade_no=order.order_no,
            out_request_no=refund.refund_no,
            refund_reason=refund.reason,
        )
        if str(result.get("code", "")) == "10000":
            async with AsyncSessionFactory() as write_session:
                await PaymentRepository(write_session).finalize_refund_success(
                    refund_no,
                    parse_alipay_amount(result.get("refund_fee"))
                    or Decimal(str(refund.amount)),
                )
            return
        error = result.get("sub_msg") or result.get("msg") or "支付宝拒绝退款"
        if result.get("sub_code") in DEFINITE_REFUND_FAILURES:
            async with AsyncSessionFactory() as write_session:
                await PaymentRepository(write_session).finalize_refund_failure(
                    refund_no, error
                )
            return
        raise RuntimeError(error)
    except Exception as exc:
        logger.warning("支付宝退款结果待确认：退款=%s，异常=%s", refund_no, type(exc).__name__)
        async with AsyncSessionFactory() as retry_session:
            await PaymentRepository(retry_session).schedule_refund_retry(
                refund_no, str(exc)
            )


async def run_reconciliation_batch() -> tuple[int, int]:
    if not settings.PAYMENT_ENABLED:
        return 0, 0
    async with AsyncSessionFactory() as session:
        repository = PaymentRepository(session)
        order_nos = await repository.claim_due_orders(
            settings.PAYMENT_RECONCILE_BATCH_SIZE
        )
    for order_no in order_nos:
        await reconcile_order(order_no)

    async with AsyncSessionFactory() as session:
        refund_nos = await PaymentRepository(session).claim_due_refunds(
            settings.PAYMENT_RECONCILE_BATCH_SIZE
        )
    for refund_no in refund_nos:
        await process_refund(refund_no)
    return len(order_nos), len(refund_nos)


async def payment_reconciliation_loop() -> None:
    while True:
        try:
            orders, refunds = await run_reconciliation_batch()
            if orders or refunds:
                logger.info("支付对账批次完成：订单=%s，退款=%s", orders, refunds)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("支付对账批次失败")
        await asyncio.sleep(settings.PAYMENT_RECONCILE_INTERVAL_SECONDS)

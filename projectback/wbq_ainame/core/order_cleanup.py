"""Compatibility tasks for standard payment orders and expert orders."""

import asyncio
import logging
import os

from core.payment_service import payment_reconciliation_loop
from models import AsyncSessionFactory
from modules.expert.expert_repo import ExpertRepository


logger = logging.getLogger(__name__)
ORDER_CLEANUP_INTERVAL_SECONDS = max(
    10,
    int(os.getenv("ORDER_CLEANUP_INTERVAL_SECONDS", "300")),
)


async def maintain_expert_orders() -> dict:
    async with AsyncSessionFactory() as session:
        return await ExpertRepository(session).run_maintenance()


async def expert_order_maintenance_loop() -> None:
    """Maintain expert orders immediately, then repeat periodically."""
    while True:
        try:
            result = await maintain_expert_orders()
            if any(result.values()):
                logger.info("Maintained expert orders: %s", result)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Missing expert migrations must not prevent the app from starting.
            logger.exception("Failed to maintain expert orders")

        await asyncio.sleep(ORDER_CLEANUP_INTERVAL_SECONDS)


# Legacy imports must continue to close standard payment orders through the
# reconciliation service; those orders must never be deleted.
cleanup_expired_orders_loop = payment_reconciliation_loop

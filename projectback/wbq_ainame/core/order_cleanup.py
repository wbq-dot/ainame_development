import asyncio
import logging
import os

from models import AsyncSessionFactory
from repository.order_repo import OrderRepo


logger = logging.getLogger(__name__)
ORDER_CLEANUP_INTERVAL_SECONDS = max(
    10,
    int(os.getenv("ORDER_CLEANUP_INTERVAL_SECONDS", "300")),
)


async def delete_expired_pending_orders() -> int:
    async with AsyncSessionFactory() as session:
        return await OrderRepo(session).delete_expired_pending_orders()


async def cleanup_expired_orders_loop() -> None:
    """Clean expired pending orders immediately, then repeat periodically."""
    while True:
        try:
            deleted_count = await delete_expired_pending_orders()
            if deleted_count:
                logger.info("Deleted %s expired pending orders", deleted_count)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Failed to delete expired pending orders")

        await asyncio.sleep(ORDER_CLEANUP_INTERVAL_SECONDS)

import asyncio
import logging
import os

from models import AsyncSessionFactory
from repository.order_repo import OrderRepo
from modules.expert.expert_repo import ExpertRepository


logger = logging.getLogger(__name__)
ORDER_CLEANUP_INTERVAL_SECONDS = max(
    10,
    int(os.getenv("ORDER_CLEANUP_INTERVAL_SECONDS", "300")),
)


async def delete_expired_pending_orders() -> int:
    async with AsyncSessionFactory() as session:
        return await OrderRepo(session).delete_expired_pending_orders()


async def maintain_expert_orders() -> dict:
    async with AsyncSessionFactory() as session:
        return await ExpertRepository(session).run_maintenance()


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

        try:
            result = await maintain_expert_orders()
            if any(result.values()):
                logger.info("Maintained expert orders: %s", result)
        except asyncio.CancelledError:
            raise
        except Exception:
            # 迁移尚未执行时只记录错误，不影响现有服务启动。
            logger.exception("Failed to maintain expert orders")

        await asyncio.sleep(ORDER_CLEANUP_INTERVAL_SECONDS)

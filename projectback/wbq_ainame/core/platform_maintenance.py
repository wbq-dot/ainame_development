import asyncio
import logging
from datetime import datetime

from sqlalchemy import select

from models import AsyncSessionFactory
from models.platform_models import PlatformTask
from repository.platform_repo import PlatformRepository
from core.platform_tasks import publish_or_mark_failed


logger = logging.getLogger(__name__)


async def run_platform_maintenance() -> dict:
    async with AsyncSessionFactory() as session:
        repo = PlatformRepository(session)
        rewards = await repo.settle_rewards()
        closed = await repo.close_expired_orders()
    async with AsyncSessionFactory() as session:
        due = list((await session.scalars(select(PlatformTask.task_no).where(PlatformTask.status.in_(("failed", "partial_failed")), PlatformTask.next_retry_at <= datetime.now()).limit(20))).all())
    retried = 0
    for task_no in due:
        async with AsyncSessionFactory() as session:
            try: await PlatformRepository(session).retry_task(task_no)
            except Exception: continue
        if await publish_or_mark_failed(task_no): retried += 1
    return {"rewards": rewards, "orders_closed": closed, "tasks_retried": retried}


async def platform_maintenance_loop() -> None:
    while True:
        try:
            result = await run_platform_maintenance()
            if any(result.values()): logger.info("开放平台维护完成：%s", result)
        except Exception: logger.exception("开放平台维护失败")
        await asyncio.sleep(60)

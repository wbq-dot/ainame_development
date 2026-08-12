import asyncio
import json
import os
import sys

import aio_pika

from core.platform_tasks import PLATFORM_QUEUE, consume_task


async def handle(message: aio_pika.IncomingMessage) -> None:
    async with message.process(requeue=False):
        payload = json.loads(message.body.decode("utf-8"))
        await consume_task(payload["task_no"])


async def main() -> None:
    connection = await aio_pika.connect_robust(os.getenv("RABBITMQ_URL"))
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await channel.declare_queue(PLATFORM_QUEUE, durable=True)
    await queue.consume(handle)
    await asyncio.Future()


if __name__ == "__main__":
    if sys.platform == "win32": asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

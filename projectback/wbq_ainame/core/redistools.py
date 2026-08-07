import redis.asyncio as aioredis
from typing import AsyncGenerator
from dotenv import load_dotenv
import os
load_dotenv()


redis_client = aioredis.from_url(
    url=os.getenv("REDIS_URL"),
    encoding="utf-8",
    decode_responses=True
)

async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:    # AsyncGenerator 异步的生成器返回一个异步的Redis连接
    # 直接返回 client，因为连接池会在后台自动管理连接
    yield redis_client
"""只读检查专家模块数据库结构与基础查询。"""

import asyncio

from models import AsyncSessionFactory, engine
from modules.expert.expert_repo import ExpertRepository


async def main() -> None:
    try:
        async with AsyncSessionFactory() as session:
            repository = ExpertRepository(session)
            experts = await repository.list_public_experts()
            packages = await repository.list_public_packages()
            print(f"expert database check passed: experts={len(experts)}, packages={len(packages)}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())


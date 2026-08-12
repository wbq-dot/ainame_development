"""创建或修正本地专家订单池演示账号。"""

import argparse
import asyncio

from sqlalchemy import select

from models import AsyncSessionFactory, engine
from models.User import User
from models.expert_models import ExpertProfile


DEMO_EXPERTS = (
    {
        "email": "ordinary.expert@example.local",
        "username": "ordinary_expert",
        "password": "DemoExpert29!",
        "display_name": "普通起名顾问",
        "title": "传统文化起名专家",
        "expert_level": "ordinary",
        "experience_years": 5,
    },
    {
        "email": "renowned.expert@example.local",
        "username": "renowned_expert",
        "password": "DemoExpert69!",
        "display_name": "知名起名顾问",
        "title": "姓名文化资深专家",
        "expert_level": "renowned",
        "experience_years": 12,
    },
    {
        "email": "top.expert@example.local",
        "username": "top_expert",
        "password": "DemoExpert159!",
        "display_name": "顶级起名顾问",
        "title": "高端命名首席顾问",
        "expert_level": "top",
        "experience_years": 20,
    },
)


async def sync_demo_experts() -> int:
    results = []
    async with AsyncSessionFactory() as session:
        async with session.begin():
            for item in DEMO_EXPERTS:
                user = await session.scalar(select(User).where(User.email == item["email"]))
                action = "已修正"
                if user is None:
                    user = User(
                        email=item["email"],
                        username=item["username"],
                        password=item["password"],
                        role="expert",
                        status="active",
                    )
                    session.add(user)
                    await session.flush()
                    action = "已创建"
                else:
                    user.username = item["username"]
                    user.password = item["password"]
                    user.role = "expert"
                    user.status = "active"
                    user.frozen_at = None
                    user.deleted_at = None

                profile = await session.scalar(
                    select(ExpertProfile).where(ExpertProfile.user_id == user.id)
                )
                values = {
                    "display_name": item["display_name"],
                    "title": item["title"],
                    "bio": "本地演示专家账号，用于测试专家订单池、接单和报告交付流程。",
                    "specialties": "人名起名、五行分析、寓意与读音建议",
                    "experience_years": item["experience_years"],
                    "expert_level": item["expert_level"],
                    "status": "approved",
                    "review_note": "本地开发演示账号",
                }
                if profile is None:
                    profile = ExpertProfile(user_id=user.id, **values)
                    session.add(profile)
                else:
                    for key, value in values.items():
                        setattr(profile, key, value)
                results.append((item["email"], item["expert_level"], action))

    for email, level, action in results:
        print(f"{action}: {email} ({level})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="初始化本地专家演示账号")
    parser.add_argument("--yes", action="store_true", help="确认执行已列明的本地账号写入")
    args = parser.parse_args()
    if not args.yes:
        print("未执行：请在确认账号信息后使用 --yes。")
        return 1
    async def run() -> int:
        try:
            return await sync_demo_experts()
        finally:
            await engine.dispose()

    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())

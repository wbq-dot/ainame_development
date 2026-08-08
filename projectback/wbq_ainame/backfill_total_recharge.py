"""按余额、已使用次数和注册赠送次数修复单个用户的累计充值次数。"""

import argparse
import asyncio

from sqlalchemy import select

from models import AsyncSessionFactory, engine
from models.user_credit import UserCredit


async def backfill(user_id: int, gift_count: int) -> None:
    async with AsyncSessionFactory() as session:
        async with session.begin():
            credit = await session.scalar(
                select(UserCredit)
                .where(UserCredit.user_id == user_id)
                .with_for_update()
            )
            if not credit:
                raise SystemExit(f"未找到 user_id={user_id} 的次数账户")

            before = credit.total_recharge
            calculated = credit.balance + credit.total_used - gift_count
            if calculated < 0:
                raise SystemExit(
                    "计算结果小于 0，请检查余额、已使用次数或赠送次数后再执行"
                )

            print(
                f"更新前 user_id={user_id}, balance={credit.balance}, "
                f"total_used={credit.total_used}, total_recharge={before}"
            )
            credit.total_recharge = calculated

        await session.refresh(credit)
        print(
            f"更新后 user_id={user_id}, total_recharge={credit.total_recharge}, "
            f"计算式={credit.balance}+{credit.total_used}-{gift_count}={calculated}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--gift-count", type=int, required=True)
    args = parser.parse_args()
    async def run() -> None:
        try:
            await backfill(args.user_id, args.gift_count)
        finally:
            await engine.dispose()

    asyncio.run(run())


if __name__ == "__main__":
    main()

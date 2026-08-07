import argparse
import asyncio
import sys

from sqlalchemy import select

from models import AsyncSessionFactory, engine
from models.User import User
from models.user_credit import UserCredit


TEST_ADMIN_EMAIL = "admin@ainame.com"
TEST_ADMIN_USERNAME = "admin"
TEST_ADMIN_PASSWORD = "Admin123456"


def confirm(message: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    answer = input(f"{message}\n请输入 yes 确认：").strip().lower()
    return answer == "yes"


async def create_test_admin(assume_yes: bool) -> int:
    action = (
        "即将创建本地测试管理员：\n"
        f"邮箱：{TEST_ADMIN_EMAIL}\n"
        f"用户名：{TEST_ADMIN_USERNAME}\n"
        "角色：admin\n"
        "同时创建余额为0的次数账户。"
    )
    if not confirm(action, assume_yes):
        print("操作已取消。")
        return 1

    async with AsyncSessionFactory() as session:
        async with session.begin():
            existing = await session.scalar(
                select(User).where(User.email == TEST_ADMIN_EMAIL)
            )
            if existing:
                print("创建失败：该邮箱已经存在，不会覆盖账号或密码。")
                return 2

            user = User(
                email=TEST_ADMIN_EMAIL,
                username=TEST_ADMIN_USERNAME,
                password=TEST_ADMIN_PASSWORD,
                role="admin",
                status="active",
            )
            session.add(user)
            await session.flush()
            session.add(
                UserCredit(
                    user_id=user.id,
                    balance=0,
                    total_used=0,
                    total_recharge=0,
                )
            )

    print(f"管理员创建成功，用户ID：{user.id}")
    return 0


async def promote_user(email: str, assume_yes: bool) -> int:
    if not confirm(f"即将把现有账号 {email} 提升为管理员。", assume_yes):
        print("操作已取消。")
        return 1

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = await session.scalar(select(User).where(User.email == email))
            if not user:
                print("提升失败：账号不存在。")
                return 2
            if user.status != "active":
                print("提升失败：只有正常状态账号可以成为管理员。")
                return 3
            user.role = "admin"
    print(f"账号 {email} 已提升为管理员。")
    return 0


async def show_user(email: str) -> int:
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(User, UserCredit)
            .outerjoin(UserCredit, UserCredit.user_id == User.id)
            .where(User.email == email)
        )
        row = result.first()
    if not row:
        print("账号不存在。")
        return 2
    user, credit = row
    print(f"ID: {user.id}")
    print(f"Email: {user.email}")
    print(f"Username: {user.username}")
    print(f"Role: {user.role}")
    print(f"Status: {user.status}")
    print(f"Balance: {credit.balance if credit else 0}")
    print("Password stored as hash: yes")
    return 0


async def change_email(from_email: str, to_email: str, assume_yes: bool) -> int:
    action = f"即将把账号邮箱从 {from_email} 修改为 {to_email}，其他账号信息保持不变。"
    if not confirm(action, assume_yes):
        print("操作已取消。")
        return 1

    async with AsyncSessionFactory() as session:
        async with session.begin():
            target_exists = await session.scalar(select(User).where(User.email == to_email))
            if target_exists:
                print("修改失败：目标邮箱已经存在。")
                return 2
            user = await session.scalar(select(User).where(User.email == from_email))
            if not user:
                print("修改失败：原账号不存在。")
                return 3
            user.email = to_email
    print(f"账号邮箱已修改为 {to_email}。")
    return 0


def parse_args():
    parser = argparse.ArgumentParser(description="管理员账号管理工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser(
        "create-test-admin",
        help="创建固定的本地测试管理员",
    )
    create_parser.add_argument("--yes", action="store_true", help="跳过交互确认")

    promote_parser = subparsers.add_parser("promote", help="提升现有账号为管理员")
    promote_parser.add_argument("--email", required=True)
    promote_parser.add_argument("--yes", action="store_true", help="跳过交互确认")

    show_parser = subparsers.add_parser("show", help="只读查看账号角色和状态")
    show_parser.add_argument("--email", required=True)

    email_parser = subparsers.add_parser("change-email", help="修改现有账号邮箱")
    email_parser.add_argument("--from-email", required=True)
    email_parser.add_argument("--to-email", required=True)
    email_parser.add_argument("--yes", action="store_true", help="跳过交互确认")
    return parser.parse_args()


async def async_main() -> int:
    args = parse_args()
    try:
        if args.command == "create-test-admin":
            return await create_test_admin(args.yes)
        if args.command == "promote":
            return await promote_user(args.email, args.yes)
        if args.command == "show":
            return await show_user(args.email)
        if args.command == "change-email":
            return await change_email(args.from_email, args.to_email, args.yes)
        return 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(async_main()))

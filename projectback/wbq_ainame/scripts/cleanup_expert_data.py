"""盘点并按显式确认清理专家模块与测试管理账号。"""

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from models import engine
from core.expert_service import private_storage_dir


EXPERT_TABLES = (
    "expert_income",
    "expert_settlement_request",
    "expert_review",
    "expert_report",
    "expert_order_attachment",
    "expert_order",
    "expert_service_package",
    "expert_profile",
)

CONFIRM_TOKEN = "CONFIRM_PERMANENT_CLEANUP"
EXPECTED_EXPERT_COUNTS = {
    "expert_income": 1,
    "expert_settlement_request": 1,
    "expert_review": 0,
    "expert_report": 1,
    "expert_order_attachment": 0,
    "expert_order": 4,
    "expert_service_package": 0,
    "expert_profile": 3,
}
EXPECTED_UNPAID_ORDER_IDS = [22, 23, 24, 25, 26]
EXPECTED_PAID_ORDER_IDS = [3, 4, 5, 11, 14, 20, 27]
EXPECTED_ACCOUNT_EMAILS = [
    "admin@ainame.com",
    "ordinary.expert@example.local",
    "renowned.expert@example.local",
    "top.expert@example.local",
]


async def audit() -> None:
    async with engine.connect() as connection:
        print("[专家模块表]")
        for table_name in EXPERT_TABLES:
            count = await connection.scalar(text(f"SELECT COUNT(*) FROM `{table_name}`"))
            print(f"{table_name}: {int(count or 0)}")

        print("\n[普通充值订单状态]")
        rows = (
            await connection.execute(
                text(
                    "SELECT status, COUNT(*) AS total, "
                    "GROUP_CONCAT(id ORDER BY id) AS ids "
                    "FROM user_order GROUP BY status"
                )
            )
        ).all()
        for status, total, ids in rows:
            print(f"{status}: {total}; IDs={ids}")
        unpaid = await connection.scalar(
            text("SELECT COUNT(*) FROM user_order WHERE status <> 'paid'")
        )
        print(f"待清理的所有未支付普通订单: {int(unpaid or 0)}")

        print("\n[待清理管理员与专家账号]")
        accounts = (
            await connection.execute(
                text(
                    "SELECT id, email, username, role, status "
                    "FROM user WHERE role IN ('admin', 'expert') ORDER BY id"
                )
            )
        ).all()
        if not accounts:
            print("无")
        for row in accounts:
            print(
                f"ID={row.id}; Email={row.email}; Username={row.username}; "
                f"Role={row.role}; Status={row.status}"
            )

        print("\n[上述账号关联数据]")
        account_ids = [int(row.id) for row in accounts]
        if account_ids:
            id_csv = ",".join(str(item) for item in account_ids)
            queries = {
                "user_credit": f"SELECT COUNT(*) FROM user_credit WHERE user_id IN ({id_csv})",
                "credit_log": f"SELECT COUNT(*) FROM credit_log WHERE user_id IN ({id_csv})",
                "user_order": f"SELECT COUNT(*) FROM user_order WHERE user_id IN ({id_csv})",
                "admin_action_log": (
                    "SELECT COUNT(*) FROM admin_action_log "
                    f"WHERE admin_user_id IN ({id_csv}) OR target_user_id IN ({id_csv})"
                ),
            }
            for label, statement in queries.items():
                count = await connection.scalar(text(statement))
                print(f"{label}: {int(count or 0)}")
        else:
            print("无")

        print("\n[清理后预计保留]")
        normal_users = await connection.scalar(
            text("SELECT COUNT(*) FROM user WHERE role NOT IN ('admin', 'expert')")
        )
        paid_orders = await connection.scalar(
            text("SELECT COUNT(*) FROM user_order WHERE status = 'paid' AND user_id NOT IN "
                 "(SELECT id FROM user WHERE role IN ('admin', 'expert'))")
        )
        print(f"普通用户: {int(normal_users or 0)}")
        print(f"普通用户已支付充值订单: {int(paid_orders or 0)}")
        remaining_users = (
            await connection.execute(
                text(
                    "SELECT id, email, username, status FROM user "
                    "WHERE role NOT IN ('admin', 'expert') ORDER BY id"
                )
            )
        ).all()
        for row in remaining_users:
            print(
                f"保留用户 ID={row.id}; Email={row.email}; "
                f"Username={row.username}; Status={row.status}"
            )

        print("\n[保留表当前 ID 范围]")
        for table_name in (
            "user",
            "user_credit",
            "credit_log",
            "user_order",
            "package",
            "admin_action_log",
        ):
            row = (
                await connection.execute(
                    text(
                        f"SELECT COUNT(*) AS total, MIN(id) AS min_id, "
                        f"MAX(id) AS max_id FROM `{table_name}`"
                    )
                )
            ).one()
            print(
                f"{table_name}: count={row.total}; min={row.min_id}; max={row.max_id}"
            )

        print("\n[下一条自增 ID]")
        tracked_tables = (
            "user",
            "user_credit",
            "credit_log",
            "user_order",
            "package",
            "admin_action_log",
            *EXPERT_TABLES,
        )
        table_names = ",".join(f"'{item}'" for item in tracked_tables)
        auto_rows = (
            await connection.execute(
                text(
                    "SELECT TABLE_NAME, AUTO_INCREMENT FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA = DATABASE() "
                    f"AND TABLE_NAME IN ({table_names}) ORDER BY TABLE_NAME"
                )
            )
        ).all()
        for table_name, auto_increment in auto_rows:
            print(f"{table_name}: {auto_increment}")

    storage = private_storage_dir()
    files = [item for item in storage.glob("*") if item.is_file() and item.name != ".gitkeep"]
    print("\n[专家私有附件]")
    print(f"目录: {storage}")
    print(f"待清理文件: {len(files)}")


async def _current_snapshot(connection) -> dict:
    expert_counts = {}
    for table_name in EXPERT_TABLES:
        expert_counts[table_name] = int(
            await connection.scalar(text(f"SELECT COUNT(*) FROM `{table_name}`")) or 0
        )
    unpaid_ids = list(
        (
            await connection.scalars(
                text("SELECT id FROM user_order WHERE status <> 'paid' ORDER BY id")
            )
        ).all()
    )
    paid_ids = list(
        (
            await connection.scalars(
                text("SELECT id FROM user_order WHERE status = 'paid' ORDER BY id")
            )
        ).all()
    )
    accounts = (
        await connection.execute(
            text(
                "SELECT id, email, username, role, status FROM user "
                "WHERE role IN ('admin', 'expert') ORDER BY id"
            )
        )
    ).mappings().all()
    return {
        "expert_counts": expert_counts,
        "unpaid_order_ids": [int(item) for item in unpaid_ids],
        "paid_order_ids": [int(item) for item in paid_ids],
        "accounts": [dict(row) for row in accounts],
    }


def _validate_snapshot(snapshot: dict) -> None:
    errors = []
    if snapshot["expert_counts"] != EXPECTED_EXPERT_COUNTS:
        errors.append("专家模块表行数已变化")
    if snapshot["unpaid_order_ids"] != EXPECTED_UNPAID_ORDER_IDS:
        errors.append("未支付订单 ID 已变化")
    if snapshot["paid_order_ids"] != EXPECTED_PAID_ORDER_IDS:
        errors.append("已支付订单 ID 已变化")
    emails = [item["email"] for item in snapshot["accounts"]]
    if emails != EXPECTED_ACCOUNT_EMAILS:
        errors.append("管理员或专家账号列表已变化")
    storage = private_storage_dir()
    files = [item for item in storage.glob("*") if item.is_file() and item.name != ".gitkeep"]
    if files:
        errors.append("专家私有附件目录出现了新文件")
    if errors:
        raise RuntimeError("；".join(errors) + "，已停止清理，请重新盘点确认。")


def _write_manifest(snapshot: dict) -> Path:
    backup_dir = Path(__file__).resolve().parents[1] / "backups" / "cleanup-manifests"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = backup_dir / f"expert_cleanup_{timestamp}.json"
    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "purpose": "永久清理前删除清单，不包含密码哈希或客户正文",
        "snapshot": snapshot,
        "id_plan": {
            "paid_user_order": "按原 ID 升序重排为 1-7",
            "credit_log": "按原 ID 升序重排为 1-53",
            "empty_expert_tables_next_id": 1,
        },
    }
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


async def execute_cleanup(confirm_token: str) -> None:
    if confirm_token != CONFIRM_TOKEN:
        raise RuntimeError("确认令牌不正确，拒绝执行永久清理。")

    async with engine.connect() as connection:
        snapshot = await _current_snapshot(connection)
    _validate_snapshot(snapshot)
    manifest_path = _write_manifest(snapshot)

    async with engine.begin() as connection:
        account_ids = [int(item["id"]) for item in snapshot["accounts"]]
        id_csv = ",".join(str(item) for item in account_ids)

        for table_name in (
            "expert_income",
            "expert_review",
            "expert_report",
            "expert_order_attachment",
            "expert_order",
            "expert_service_package",
            "expert_settlement_request",
            "expert_profile",
        ):
            await connection.execute(text(f"DELETE FROM `{table_name}`"))

        await connection.execute(
            text(
                "DELETE FROM admin_action_log "
                f"WHERE admin_user_id IN ({id_csv}) OR target_user_id IN ({id_csv})"
            )
        )
        await connection.execute(
            text(f"DELETE FROM credit_log WHERE user_id IN ({id_csv})")
        )
        await connection.execute(
            text("DELETE FROM user_order WHERE status <> 'paid'")
        )
        await connection.execute(
            text(f"DELETE FROM user_order WHERE user_id IN ({id_csv})")
        )
        await connection.execute(
            text(f"DELETE FROM user_credit WHERE user_id IN ({id_csv})")
        )
        await connection.execute(
            text(f"DELETE FROM user WHERE id IN ({id_csv})")
        )

        await connection.execute(text("SET @order_next_id := 0"))
        await connection.execute(
            text(
                "UPDATE user_order SET id = (@order_next_id := @order_next_id + 1) "
                "ORDER BY id"
            )
        )
        await connection.execute(text("SET @credit_log_next_id := 0"))
        await connection.execute(
            text(
                "UPDATE credit_log SET id = (@credit_log_next_id := @credit_log_next_id + 1) "
                "ORDER BY id"
            )
        )

    next_ids = {
        "user": 2,
        "user_credit": 2,
        "credit_log": 54,
        "user_order": 8,
        "package": 7,
        "admin_action_log": 1,
        **{table_name: 1 for table_name in EXPERT_TABLES},
    }
    async with engine.begin() as connection:
        for table_name, next_id in next_ids.items():
            await connection.execute(
                text(f"ALTER TABLE `{table_name}` AUTO_INCREMENT = {next_id}")
            )

    storage = private_storage_dir()
    expected_storage = (
        Path(__file__).resolve().parents[1] / "private_storage" / "expert"
    ).resolve()
    if storage != expected_storage:
        raise RuntimeError("私有附件目录不符合预期，数据库已清理但未执行文件清理。")
    for item in storage.iterdir():
        if item.is_file() and item.name != ".gitkeep":
            item.unlink()

    async with engine.connect() as connection:
        for table_name in EXPERT_TABLES:
            count = int(
                await connection.scalar(text(f"SELECT COUNT(*) FROM `{table_name}`")) or 0
            )
            if count != 0:
                raise RuntimeError(f"验收失败：{table_name} 仍有 {count} 条数据")
        remaining_accounts = int(
            await connection.scalar(
                text("SELECT COUNT(*) FROM user WHERE role IN ('admin', 'expert')")
            )
            or 0
        )
        unpaid_orders = int(
            await connection.scalar(
                text("SELECT COUNT(*) FROM user_order WHERE status <> 'paid'")
            )
            or 0
        )
        user_ids = list((await connection.scalars(text("SELECT id FROM user ORDER BY id"))).all())
        order_ids = list(
            (await connection.scalars(text("SELECT id FROM user_order ORDER BY id"))).all()
        )
        credit_log_ids = list(
            (await connection.scalars(text("SELECT id FROM credit_log ORDER BY id"))).all()
        )
        if remaining_accounts or unpaid_orders:
            raise RuntimeError("验收失败：仍有管理员、专家或未支付订单")
        if user_ids != [1] or order_ids != list(range(1, 8)):
            raise RuntimeError("验收失败：用户或已支付订单 ID 未按计划重排")
        if credit_log_ids != list(range(1, 54)):
            raise RuntimeError("验收失败：次数流水 ID 未按计划重排")

    print("永久清理执行成功。")
    print(f"删除清单：{manifest_path}")
    print("保留用户 ID: 1")
    print("保留已支付订单 ID: 1-7")
    print("保留次数流水 ID: 1-53")


async def repair_auto_increment(confirm_token: str) -> None:
    if confirm_token != CONFIRM_TOKEN:
        raise RuntimeError("确认令牌不正确，拒绝重置自增 ID。")

    async with engine.connect() as connection:
        for table_name in EXPERT_TABLES:
            count = int(
                await connection.scalar(text(f"SELECT COUNT(*) FROM `{table_name}`")) or 0
            )
            if count:
                raise RuntimeError(f"拒绝重置：{table_name} 不为空")
        roles = int(
            await connection.scalar(
                text("SELECT COUNT(*) FROM user WHERE role IN ('admin', 'expert')")
            )
            or 0
        )
        unpaid = int(
            await connection.scalar(
                text("SELECT COUNT(*) FROM user_order WHERE status <> 'paid'")
            )
            or 0
        )
        user_ids = list((await connection.scalars(text("SELECT id FROM user ORDER BY id"))).all())
        order_ids = list(
            (await connection.scalars(text("SELECT id FROM user_order ORDER BY id"))).all()
        )
        credit_ids = list(
            (await connection.scalars(text("SELECT id FROM credit_log ORDER BY id"))).all()
        )
        if roles or unpaid or user_ids != [1] or order_ids != list(range(1, 8)):
            raise RuntimeError("清理后数据状态已变化，拒绝重置自增 ID")
        if credit_ids != list(range(1, 54)):
            raise RuntimeError("次数流水 ID 状态已变化，拒绝重置自增 ID")

    targets = {
        "user": 2,
        "user_credit": 2,
        "credit_log": 54,
        "user_order": 8,
        "admin_action_log": 1,
        **{table_name: 1 for table_name in EXPERT_TABLES},
    }
    async with engine.connect() as raw_connection:
        connection = await raw_connection.execution_options(
            isolation_level="AUTOCOMMIT"
        )
        for table_name, next_id in targets.items():
            await connection.execute(text(f"OPTIMIZE TABLE `{table_name}`"))
            await connection.execute(
                text(f"ALTER TABLE `{table_name}` AUTO_INCREMENT = {next_id}")
            )

    async with engine.connect() as connection:
        for table_name, expected in targets.items():
            actual = await connection.scalar(
                text(
                    "SELECT AUTO_INCREMENT FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name"
                ),
                {"table_name": table_name},
            )
            if int(actual or 1) != expected:
                raise RuntimeError(
                    f"{table_name} 下一条 ID 仍为 {actual}，目标为 {expected}"
                )
    print("自增 ID 重置成功。")


def parse_args():
    parser = argparse.ArgumentParser(description="专家模块清理工具")
    parser.add_argument("--execute", action="store_true", help="执行已确认的永久清理")
    parser.add_argument(
        "--repair-auto-increment",
        action="store_true",
        help="重建表统计并完成已确认的自增 ID 重置",
    )
    parser.add_argument("--confirm-token", default="")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    try:
        if args.repair_auto_increment:
            await repair_auto_increment(args.confirm_token)
        elif args.execute:
            await execute_cleanup(args.confirm_token)
        else:
            await audit()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

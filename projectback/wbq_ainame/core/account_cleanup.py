import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, select, update

from core.rag_service import delete_user_knowledge
from core.workflow import delete_naming_thread
from models import AsyncSessionFactory
from models.account_security import AccountDeletionJob, NamingSession
from modules.logo.logo_tools import LOGO_DIR


logger = logging.getLogger(__name__)
ACCOUNT_CLEANUP_INTERVAL_SECONDS = max(
    10,
    int(os.getenv("ACCOUNT_CLEANUP_INTERVAL_SECONDS", "60")),
)
ACCOUNT_CLEANUP_BATCH_SIZE = max(
    1,
    min(50, int(os.getenv("ACCOUNT_CLEANUP_BATCH_SIZE", "10"))),
)
BACKEND_DIR = Path(__file__).resolve().parents[1]
UPLOAD_FOLDER = Path(
    os.getenv("UPLOAD_FOLDER", str(BACKEND_DIR / "uploader"))
).resolve()


def _delete_files(directory: Path, pattern: str) -> int:
    if not directory.exists():
        return 0
    deleted_count = 0
    for file_path in directory.glob(pattern):
        if file_path.is_file():
            file_path.unlink(missing_ok=True)
            deleted_count += 1
    return deleted_count


async def _claim_due_jobs() -> list[tuple[int, int, int]]:
    now = datetime.now()
    stale_before = now - timedelta(minutes=10)
    async with AsyncSessionFactory() as session:
        async with session.begin():
            # 进程异常退出后，处理中的任务可重新进入重试队列。
            await session.execute(
                update(AccountDeletionJob)
                .where(
                    AccountDeletionJob.status == "processing",
                    AccountDeletionJob.updated_at <= stale_before,
                )
                .values(status="failed", next_retry_at=now, updated_at=now)
            )
            jobs = list(
                (
                    await session.scalars(
                        select(AccountDeletionJob)
                        .where(
                            AccountDeletionJob.status.in_(["pending", "failed"]),
                            AccountDeletionJob.next_retry_at <= now,
                        )
                        .order_by(AccountDeletionJob.id)
                        .limit(ACCOUNT_CLEANUP_BATCH_SIZE)
                        .with_for_update(skip_locked=True)
                    )
                ).all()
            )
            claimed = []
            for job in jobs:
                job.status = "processing"
                job.attempts += 1
                job.updated_at = now
                claimed.append((job.id, job.user_id, job.attempts))
            return claimed


async def _delete_naming_sessions(user_id: int) -> int:
    async with AsyncSessionFactory() as session:
        thread_ids = list(
            (
                await session.scalars(
                    select(NamingSession.thread_id).where(
                        NamingSession.user_id == user_id
                    )
                )
            ).all()
        )

    for thread_id in thread_ids:
        await delete_naming_thread(thread_id)

    if thread_ids:
        async with AsyncSessionFactory() as session:
            async with session.begin():
                await session.execute(
                    delete(NamingSession).where(NamingSession.user_id == user_id)
                )
    return len(thread_ids)


async def purge_user_content(user_id: int) -> None:
    await asyncio.to_thread(delete_user_knowledge, user_id)
    await asyncio.to_thread(_delete_files, UPLOAD_FOLDER, f"{user_id}_*")
    await asyncio.to_thread(_delete_files, LOGO_DIR, f"user_{user_id}_*.png")
    await _delete_naming_sessions(user_id)


async def _mark_completed(job_id: int) -> None:
    now = datetime.now()
    async with AsyncSessionFactory() as session:
        async with session.begin():
            job = await session.get(AccountDeletionJob, job_id, with_for_update=True)
            if not job:
                return
            job.status = "completed"
            job.last_error = None
            job.completed_at = now
            job.updated_at = now


async def _mark_failed(job_id: int, attempts: int, exc: Exception) -> None:
    now = datetime.now()
    retry_seconds = min(3600, 60 * (2 ** max(0, attempts - 1)))
    async with AsyncSessionFactory() as session:
        async with session.begin():
            job = await session.get(AccountDeletionJob, job_id, with_for_update=True)
            if not job:
                return
            job.status = "failed"
            job.last_error = f"{type(exc).__name__}: {exc}"[:1000]
            job.next_retry_at = now + timedelta(seconds=retry_seconds)
            job.updated_at = now


async def process_account_deletion_jobs() -> int:
    claimed_jobs = await _claim_due_jobs()
    completed_count = 0
    for job_id, user_id, attempts in claimed_jobs:
        try:
            await purge_user_content(user_id)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Failed to purge content for deleted user %s", user_id)
            await _mark_failed(job_id, attempts, exc)
        else:
            await _mark_completed(job_id)
            completed_count += 1
            logger.info("Purged personal content for deleted user %s", user_id)
    return completed_count


async def account_cleanup_loop() -> None:
    while True:
        try:
            await process_account_deletion_jobs()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Failed to process account deletion jobs")
        await asyncio.sleep(ACCOUNT_CLEANUP_INTERVAL_SECONDS)

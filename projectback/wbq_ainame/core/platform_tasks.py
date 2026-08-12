import json
import os
from pathlib import Path
from datetime import datetime, timedelta

import aio_pika
from sqlalchemy import select

from core.rag_service import process_and_store_file
from core.workflow import generate_naming
from models import AsyncSessionFactory
from models.platform_models import PlatformTask, PlatformTaskEvent, PlatformTaskItem
from repository.platform_repo import PlatformRepository
from schemas.name_schemas import NameIn


PLATFORM_QUEUE = os.getenv("PLATFORM_TASK_QUEUE", "platform_task_queue")


async def publish_task(task_no: str) -> None:
    connection = await aio_pika.connect_robust(os.getenv("RABBITMQ_URL"))
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(PLATFORM_QUEUE, durable=True)
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps({"task_no": task_no}).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            ),
            routing_key=queue.name,
        )


async def publish_or_mark_failed(task_no: str) -> bool:
    try:
        await publish_task(task_no)
        return True
    except Exception as exc:
        async with AsyncSessionFactory() as session, session.begin():
            task = await session.scalar(select(PlatformTask).where(PlatformTask.task_no == task_no).with_for_update())
            if task:
                task.status = "publish_failed"
                task.last_error = str(exc)[:1000]
                session.add(PlatformTaskEvent(task_id=task.id, status="publish_failed", message="任务发布失败，可在后台重试"))
        return False


async def _run_batch(task: PlatformTask) -> None:
    async with AsyncSessionFactory() as session:
        items = list((await session.scalars(select(PlatformTaskItem).where(PlatformTaskItem.task_id == task.id).order_by(PlatformTaskItem.item_index))).all())
    success = failure = new_success = 0
    for item in items:
        if item.status == "succeeded":
            success += 1
            continue
        try:
            result = await generate_naming(NameIn.model_validate(item.input_data), task.owner_id, use_private_knowledge=False)
            output = result.get("final_output") or {}
            if not output.get("names"):
                raise ValueError("模型没有返回有效候选名字")
            async with AsyncSessionFactory() as session, session.begin():
                row = await session.get(PlatformTaskItem, item.id, with_for_update=True)
                row.status, row.output_data, row.error = "succeeded", output, None
                row.attempts += 1; row.completed_at = datetime.now()
            success += 1
            new_success += 1
        except Exception as exc:
            async with AsyncSessionFactory() as session, session.begin():
                row = await session.get(PlatformTaskItem, item.id, with_for_update=True)
                row.status, row.error = "failed", str(exc)[:1000]
                row.attempts += 1; row.completed_at = datetime.now()
            failure += 1
    async with AsyncSessionFactory() as session:
        repo = PlatformRepository(session)
        if new_success:
            await repo.finalize_credits(task.owner_id, new_success, task.task_no, "batch_naming")
        if failure:
            await repo.release_credits(task.owner_id, failure)
    async with AsyncSessionFactory() as session, session.begin():
        row = await session.get(PlatformTask, task.id, with_for_update=True)
        row.success_count, row.failure_count = success, failure
        row.reserved_credits = 0
        row.status = "succeeded" if not failure else ("partial_failed" if success else "failed")
        if failure and row.attempts < row.max_attempts:
            row.next_retry_at = datetime.now() + timedelta(minutes=(1, 5, 15)[min(row.attempts - 1, 2)])
        row.completed_at = datetime.now()
        session.add(PlatformTaskEvent(task_id=row.id, status=row.status, message=f"成功 {success} 条，失败 {failure} 条"))


async def _run_knowledge(task: PlatformTask) -> None:
    payload = task.payload or {}
    split_count = await __import__("asyncio").to_thread(process_and_store_file, payload["file_path"], task.owner_id, payload.get("knowledge_type", "general"))
    async with AsyncSessionFactory() as session, session.begin():
        row = await session.get(PlatformTask, task.id, with_for_update=True)
        row.status, row.success_count, row.completed_at = "succeeded", 1, datetime.now()
        row.payload = {**payload, "split_count": split_count}
        session.add(PlatformTaskEvent(task_id=row.id, status="succeeded", message=f"已建立 {split_count} 个文本块"))
    Path(payload["file_path"]).unlink(missing_ok=True)


async def consume_task(task_no: str) -> None:
    async with AsyncSessionFactory() as session, session.begin():
        task = await session.scalar(select(PlatformTask).where(PlatformTask.task_no == task_no).with_for_update())
        if not task or task.status in {"succeeded", "running"}:
            return
        task.status, task.started_at, task.attempts = "running", datetime.now(), task.attempts + 1
        session.add(PlatformTaskEvent(task_id=task.id, status="running", message="任务开始执行"))
        task_id = task.id
    async with AsyncSessionFactory() as session:
        task = await session.get(PlatformTask, task_id)
        try:
            if task.task_type == "batch_naming": await _run_batch(task)
            elif task.task_type == "knowledge_index": await _run_knowledge(task)
            else: raise ValueError("不支持的任务类型")
        except Exception as exc:
            release_count = 0
            async with AsyncSessionFactory() as write, write.begin():
                row = await write.get(PlatformTask, task_id, with_for_update=True)
                row.last_error = str(exc)[:1000]
                row.status = "failed"
                if row.attempts < row.max_attempts:
                    row.next_retry_at = datetime.now() + timedelta(minutes=(1, 5, 15)[min(row.attempts - 1, 2)])
                elif row.task_type == "batch_naming":
                    release_count = row.reserved_credits
                    row.reserved_credits = 0
                if row.attempts >= row.max_attempts and row.task_type == "knowledge_index":
                    payload = row.payload or {}
                    if payload.get("file_path"):
                        Path(payload["file_path"]).unlink(missing_ok=True)
                row.completed_at = datetime.now()
                write.add(PlatformTaskEvent(task_id=row.id, status="failed", message=row.last_error))
            if release_count:
                async with AsyncSessionFactory() as release_session:
                    await PlatformRepository(release_session).release_credits(task.owner_id, release_count)
            raise

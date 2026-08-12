import os
import re
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from core.authtools import AuthHandler
from dependencies import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from repository.platform_repo import PlatformNotFound, PlatformRepository
from core.platform_tasks import publish_or_mark_failed
from core.rag_service import KNOWLEDGE_TYPES
import aio_pika
import json
import settings


auth_handler = AuthHandler()
router = APIRouter(prefix="/knowledge", tags=["知识库"])
# 创建临时上传文件保存的文件夹
BACKEND_DIR = Path(__file__).resolve().parents[1]
UPLOAD_FOLDER = Path(os.getenv("UPLOAD_FOLDER", str(BACKEND_DIR / "uploader"))).resolve()
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".pdf", ".txt"}


async def send_to_queue(message_dict: dict):

    # 连接 rabbitMQ
    RABBITMQ_URL = os.getenv("RABBITMQ_URL")
    connection = await aio_pika.connect_robust(RABBITMQ_URL)    # aio_pika 异步的访问 rabbitMQ

    async with connection:
        channel = await connection.channel()    # 建立通道

        queue = await channel.declare_queue(settings.QUEUE_NAME, durable=True)  # declare_queue(name, durable=True)  声明列队名字并 durable=True 进行持久化的存储

        message_body = json.dumps(message_dict).encode("utf-8")   # 将字典转换成 json

        # 上传 json 到 rabbitMQ
        await channel.default_exchange.publish(
            # 将 json 信息传递到 rabbitMQ
            aio_pika.Message(
                body=message_body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            ),
            # 传入声明的队列名，将 json 放到那个队列中
            routing_key=queue.name
        )



@router.post("/upload", status_code=202)
async def upload_file(file: UploadFile = File(...),
                      knowledge_type: str = Form("general"),
                      user_id:int=Depends(auth_handler.auth_access_dependency),
                      session: AsyncSession = Depends(get_session)):
    knowledge_type = knowledge_type.strip().lower()
    if knowledge_type not in KNOWLEDGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="知识类型必须是通用、人名、企业名或宠物名",
        )
    original_name = file.filename or "unnamed"
    safe_name = re.split(r"[/\\]", original_name)[-1]
    safe_name = re.sub(r"[^\w.\-\u4e00-\u9fff]", "_", safe_name)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="只允许上传 PDF 或 TXT 文件")

    file_path = (UPLOAD_FOLDER / f"{user_id}_{uuid4().hex}_{safe_name}").resolve()
    if file_path.parent != UPLOAD_FOLDER:
        raise HTTPException(status_code=400, detail="文件名不安全")

    total_size = 0
    try:
        with file_path.open("wb") as target:
            while chunk := await file.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > settings.MAX_UPLOAD_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"文件不能超过 {settings.MAX_UPLOAD_SIZE // (1024 * 1024)} MB",
                    )
                target.write(chunk)
    except Exception:
        file_path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    task = await PlatformRepository(session).create_task(
        task_type="knowledge_index",
        owner_type="user",
        owner_id=user_id,
        total=1,
        payload={"file_path": str(file_path), "knowledge_type": knowledge_type, "original_name": safe_name},
    )
    published = await publish_or_mark_failed(task.task_no)

    type_labels = {
        "general": "通用",
        "human": "人名",
        "company": "企业名",
        "pet": "宠物名",
    }
    return {
        "result": "success" if published else "publish_failed",
        "task_id": task.task_no,
        "status": "queued" if published else "publish_failed",
        "message": (
            f"文件 {safe_name} 已作为{type_labels[knowledge_type]}资料上传，后台任务已排队。"
            if published else "文件已安全保存，但任务队列暂不可用，可由管理员重新入队。"
        ),
    }


@router.get("/tasks/{task_no}")
async def knowledge_task(
    task_no: str,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await PlatformRepository(session).task_detail(task_no, "user", user_id)
    except PlatformNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

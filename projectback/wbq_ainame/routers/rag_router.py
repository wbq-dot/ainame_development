import os
import re
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from core.authtools import AuthHandler
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
            aio_pika.Message(body=message_body),
            # 传入声明的队列名，将 json 放到那个队列中
            routing_key=queue.name
        )



@router.post("/upload")
async def upload_file(file: UploadFile = File(...),
                      user_id:int=Depends(auth_handler.auth_access_dependency)):
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

    task_message = {
        "user_id": user_id,
        "file_path": str(file_path),
    }
    try:
        await send_to_queue(task_message)
    except Exception as exc:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=503, detail="知识库任务队列暂时不可用") from exc

    return {"result": "success",
        "message": f"文件 {safe_name} 上传成功！后台正在为您构建专属知识库，请稍候测试起名功能。"}

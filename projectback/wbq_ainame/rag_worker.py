'''
rabbitMQ 基于 Erlang 语言开发的消息中间件，主要用于实现服务解耦、异步通信和流量缓冲（削峰填谷）。防止传输数据时内容的丢失，和访卡顿的瓶颈
1. 安装  Erlang 解释器   https://www.erlang.org/patches/OTP-29.0.2
2. 一路 Next 默认安装即可
3. 用户的环境变量配置 -> 新建 ->  变量名 ERLANG_HOME   变量值 C:\\Program Files\\Erlang OTP -> 点击 path  输入 %ERLANG_HOME%\bin
4. C:\\Windows\\System32>erl -version 查看版本和解释器是否安装
5. 安装 rabbitmq-server-x.y.z.exe -> 一路 Next 完成安装  -> 以管理员身份运行 RabbitMQ Command Prompt
6. 在黑框中输入  rabbitmq-plugins enable rabbitmq_management -> net stop RabbitMQ  -> net start RabbitMQ
7. 访问 http://127.0.0.1:15672 地址查看文件的处理进程  -> 第一次登录的密码账号均为 guest
8. 修改自己的密码账号  Admin -> Add a User  -> 输入账号密码 和 Tags 输入 administrator -> 点击上面框中新出现的账号 -> 点击 Set permission
'''

# 单独执行的文件，使用命令执行

import asyncio
import json
import logging
import sys
import os
import settings
import aio_pika
from pathlib import Path
from sqlalchemy import select

from core.rag_service import delete_user_knowledge, process_and_store_file
from dotenv import load_dotenv
from models import AsyncSessionFactory
from models.User import User
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("rag_worker")

# rabbitMQ 就像一个智能的“任务排队缓冲区”。当系统需要执行大量函数节点时，它不会让所有任务一拥而上直接压垮系统，而是先把这些函数执行所需的关键参数数据暂存在队列里。
# 然后，下游服务按照自己能够承受的节奏，按序列、依次地从队列中取出数据并执行。

RABBITMQ_URL = os.getenv("RABBITMQ_URL")


async def user_is_active(user_id: int) -> bool:
    async with AsyncSessionFactory() as session:
        status = await session.scalar(select(User.status).where(User.id == user_id))
    return status == "active"

async def process_message(message: aio_pika.IncomingMessage):  # message 存在 rabbitMQ 的消息
    file_path = None
    try:
        task_data = json.loads(message.body.decode("utf-8"))  # 将存入的 json 数据加载为 dict 拿出来
        user_id = int(task_data["user_id"])   # 取 user_id 值
        file_path = task_data.get("file_path") # 取 file_path 值
        knowledge_type = task_data.get("knowledge_type", "general")
        if not file_path:
            raise ValueError("知识库任务缺少文件路径")

        if not await user_is_active(user_id):
            await message.ack()
            return

        # Chroma 和 Ollama 客户端是同步调用，放到工作线程避免阻塞 RabbitMQ 事件循环。
        split_count = await asyncio.to_thread(
            process_and_store_file,
            file_path,
            user_id,
            knowledge_type,
        )

        # 注销可能发生在向量化过程中；完成后再次检查，防止内容被重新写回。
        if not await user_is_active(user_id):
            await asyncio.to_thread(delete_user_knowledge, user_id)
    except Exception:
        logger.exception("知识库任务处理失败，消息将被拒绝且不重新入队")
        if not message.processed:
            await message.reject(requeue=False)
    else:
        await message.ack()
        logger.info(
            "知识库任务处理完成：用户=%s，分类=%s，文本块=%s",
            user_id,
            knowledge_type,
            split_count,
        )
    finally:
        if file_path:
            Path(file_path).unlink(missing_ok=True)


async def main():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()

        await channel.set_qos(prefetch_count=1)  # 设置数据取值的频次，每次拿取一条数据

        queue = await channel.declare_queue(settings.QUEUE_NAME, durable=True)  # 根据序列名连接到 rabbitMQ 序列

        # 通过执行函数来消费序列
        await queue.consume(process_message)
        logger.info("知识库任务消费者已启动，队列=%s", settings.QUEUE_NAME)

        # 控制消费者一直监听等待
        await asyncio.Future()


if __name__ == "__main__":   # 入口
    # 兼容 Windows 系统的底层异步事件循环机制
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())   # 异步的运行这个 main() 函数
    except KeyboardInterrupt:
        print("知识库任务消费者已停止。")

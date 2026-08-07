# FastAPI 项目的依赖项（如公共依赖函数）

from core.mailtools  import create_mail_instance
from fastapi_mail import FastMail

async def get_email() -> FastMail:
    return create_mail_instance()


# 建立数据库连接池工厂，返回连接
from models import AsyncSessionFactory

async def get_session() :
    session = AsyncSessionFactory()
    try:
        yield session   # 连接后只有关闭连接后，才能再次连接
    finally:
        await session.close()
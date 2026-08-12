import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
import models   # 导入 models 模块
from core.alipaytools import validate_payment_settings
from core.account_cleanup import account_cleanup_loop
from core.order_cleanup import cleanup_expired_orders_loop
from core.order_cleanup import expert_order_maintenance_loop
from core.platform_maintenance import platform_maintenance_loop
from core.workflow import init_workflow_graph, close_workflow_graph
from fastapi.middleware.cors import CORSMiddleware
import settings

# @asynccontextmanager 把下面的 lifespan 函数变成一个“上下文管理器”,在 FastAPI 中，它专门用来界定“启动前”和“关闭后”两个不同的阶段。
@asynccontextmanager   # 异步的环境管理
async def lifespan(app: FastAPI):
    if settings.PAYMENT_ENABLED:
        validate_payment_settings()
    # 服务启动时，安全地初始化带记忆的工作流
    await init_workflow_graph()
    order_cleanup_task = asyncio.create_task(cleanup_expired_orders_loop())
    account_cleanup_task = asyncio.create_task(account_cleanup_loop())
    expert_order_maintenance_task = asyncio.create_task(expert_order_maintenance_loop())
    platform_maintenance_task = asyncio.create_task(platform_maintenance_loop())
    # 在这个 yield 关键字之上的所有代码，都会在 FastAPI 应用启动、但还没有开始接收任何外部网络请求的时候执行
    # 在这个 yield 关键字之下的所有代码，只有在你停止服务器，或者服务器被关闭时才会执行。
    try:
        yield
    finally:
        background_tasks = (
            order_cleanup_task,
            account_cleanup_task,
            expert_order_maintenance_task,
            platform_maintenance_task,
        )
        for task in background_tasks:
            task.cancel()
        for task in background_tasks:
            with suppress(asyncio.CancelledError):
                await task
        # 服务停止时，清理数据库连接
        await close_workflow_graph()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


from routers.auth_router import router as auth_router
from routers.credit_router import router as credit_router
from routers.package_router import router as package_router
from routers.pay_router import router as pay_router
from routers.rag_router import router as rag_router
from routers.account_router import router as account_router

from pathlib import Path
from fastapi.staticfiles import StaticFiles
from routers.logo_router import router as logo_router
from routers.admin_router import router as admin_router
from routers.expert_router import (
    payment_status_router as expert_payment_status_router,
    router as expert_router,
)
from routers.expert_pay_router import router as expert_pay_router
from routers.community_router import router as community_router
from routers.community_router import admin_router as community_admin_router
from routers.developer_router import router as developer_router
from routers.openapi_router import router as openapi_router
from routers.developer_billing_router import router as developer_billing_router
from routers.platform_admin_router import router as platform_admin_router


BACKEND_DIR = Path(__file__).resolve().parent   # Path(__file__) 当前的文件路径 resolve() 解析 parent 上层的文件夹   D:\data\wbq_ainame
STATIC_DIR = BACKEND_DIR / "static"     # 路径拼接
(STATIC_DIR / "logos").mkdir(parents=True, exist_ok=True)  # 创建父子文件夹，存在不创建
# 把服务器上的 STATIC_DIR 文件夹，开放到网址的 /static 路径下。以后用户访问 /static/.env.png，服务器就会去那个文件夹里找 .env.png 并返回给他。
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(logo_router)


app.include_router(auth_router)

from routers.name_router import router as name_router
app.include_router(name_router)

app.include_router(credit_router)

app.include_router(package_router)

app.include_router(pay_router)

app.include_router(rag_router)
app.include_router(account_router)
app.include_router(admin_router)
app.include_router(expert_router)
app.include_router(expert_pay_router)
app.include_router(expert_payment_status_router)
app.include_router(community_router)
app.include_router(community_admin_router)
app.include_router(developer_router)
app.include_router(openapi_router)
app.include_router(developer_billing_router)
app.include_router(platform_admin_router)

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


if __name__ == "__main__":
    import uvicorn

    # 监听所有网卡，使同一局域网内的手机和其他设备可以访问。
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

from fastapi import FastAPI, Depends
import models   # 导入 models 模块
from contextlib import asynccontextmanager
from core.workflow import init_workflow_graph, close_workflow_graph
from fastapi.middleware.cors import CORSMiddleware
import settings

# @asynccontextmanager 把下面的 lifespan 函数变成一个“上下文管理器”,在 FastAPI 中，它专门用来界定“启动前”和“关闭后”两个不同的阶段。
@asynccontextmanager   # 异步的环境管理
async def lifespan(app: FastAPI):
    # 服务启动时，安全地初始化带记忆的工作流
    await init_workflow_graph()
    # 在这个 yield 关键字之上的所有代码，都会在 FastAPI 应用启动、但还没有开始接收任何外部网络请求的时候执行
    # 在这个 yield 关键字之下的所有代码，只有在你停止服务器，或者服务器被关闭时才会执行。
    yield
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


from fastapi_mail import FastMail, MessageSchema, MessageType
from dependencies import get_email
from routers.auth_router import router as auth_router
from routers.credit_router import router as credit_router
from routers.package_router import router as package_router
from routers.pay_router import router as pay_router
from routers.rag_router import router as rag_router

from pathlib import Path
from fastapi.staticfiles import StaticFiles
from routers.logo_router import router as logo_router
from routers.admin_router import router as admin_router


BACKEND_DIR = Path(__file__).resolve().parent   # Path(__file__) 当前的文件路径 resolve() 解析 parent 上层的文件夹   D:\data\wbq_ainame
STATIC_DIR = BACKEND_DIR / "static"     # 路径拼接
(STATIC_DIR / "logos").mkdir(parents=True, exist_ok=True)  # 创建父子文件夹，存在不创建
# 把服务器上的 STATIC_DIR 文件夹，开放到网址的 /static 路径下。以后用户访问 /static/xxx.png，服务器就会去那个文件夹里找 xxx.png 并返回给他。
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(logo_router)


app.include_router(auth_router)

from routers.name_router import router as name_router
app.include_router(name_router)

app.include_router(credit_router)

app.include_router(package_router)

app.include_router(pay_router)

app.include_router(rag_router)
app.include_router(admin_router)


@app.post("/email")   # 定义子路由
async def simple_send(mail:FastMail=Depends(get_email)):  # 通过依赖注入将工具绑定到参数中
    try:
        html = """<p>this is verify code 123456</p> """
        # 准备消息
        message = MessageSchema(    # MessageSchema 定义发送的邮件内容和格式
            # 消息的主题
            subject="ainame_app code",
            # 发给谁 list
            recipients=["3588951615@qq.com"],
            # 消息体
            body=html,
            # 消息的格式类型 MessageType设置类型  html、plain。
            subtype=MessageType.html)
        # 工具来发生邮件 FastMail(config).send_message(MessageSchema(邮件内容和格式))
        await mail.send_message(message)    # await  异步函数当该操作没有完成就可以执行后面的代码操作，通过加入 await 就可以等待前面的完成在执行后面的操作。
        return {"message":"邮件发送成功，请到你的邮箱查看"}
    except  Exception as e:
        print(e)




@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}

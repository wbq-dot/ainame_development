import random
import string
from typing import Annotated
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import EmailStr
from fastapi_mail import FastMail, MessageSchema, MessageType
from redis.asyncio import Redis

# 导入自定义函数模块
from dependencies import get_email
from core.redistools import get_redis
router = APIRouter(prefix="/auth", tags=["auth_email"])


# 开发验证码发送和储存
@router.get("/code")
async def get_code(email:Annotated[EmailStr, Query(...)],   # email 接受外来的参数  Query 定义 ? 后的参数，类型 EmailStr
                  mail:FastMail=Depends(get_email),       # 通过依赖注入传入发邮件的工具
                  redisclient:Redis=Depends(get_redis)):  # 通过依赖注入传入操作 Redis 数据库的工具
    #1.生成校验码
    source = string.digits*4         # string.digits="0,1,2,...,9" 所有的数字  "0123456789012345678901234567890123456789"
    code = "".join(random.sample(source,4))  # random.sample(iterable,n) 从可迭代类型的数据中随机抽取 n 个数字，且不能重复取，并得到一个列表 ['5', '3', '1', '9']
    #2.发送邮件给用户
    message = MessageSchema(
        subject="【智能起名】注册验证码",
        recipients=[email],   # 发生邮箱号的 list
        body=f"您的验证码是{code}，五分钟有效",
        subtype=MessageType.plain   # plain 是 str 的消息类型
    )
    await  mail.send_message(message)

    #3.存入redis
    await redisclient.set(f"regist:code:{email}", code,300)   # 定义一个指定的键，后续按照这个方式来查验证码进行校验通过，存储 5 min
    return {"result": "success", "message": "验证码已发送至您的邮箱"}


# 用户注册功能
from schemas.user_schemas import RegisterIn,UserCreateSchema
from sqlalchemy.ext.asyncio.session import AsyncSession
from dependencies import get_session
from repository.user_repo import UserRepository
from repository.credit_repo import CreditRepository

# 1.接收用户传过来的参数：用户名(邮箱/电话)，密码，验证码
@router.post("/register")
async def register(data:RegisterIn,  # basemodel 定义传入数据的格式并进行后端校验， post 方法规定的
                   session:AsyncSession=Depends(get_session),  # 依赖注入进行 mysql 数据库的连接操作，注入后的类型 AsyncSession
                   redis:Redis = Depends(get_redis)):   # Redis 数据库工具校验验证码

    user_repo = UserRepository(session=session)  # 定义好的连接传入到数据库操作(CRUD)的类当中，变成实例化对象，处理 user 表

    # 2.核验邮箱是否已被注册
    email_exist = await user_repo.email_is_exist(email=data.email)   # 校验数据库开始时是否存在这个邮箱，True False
    if email_exist:
        raise HTTPException(400, detail="该邮箱已经存在！")

    # 3. 校验验证码是否正确
    redis_key = f"regist:code:{data.email}"   #  regist:code:{data.email} == regist:code:{email}  这两个 key 必须相同
    saved_code = await redis.get(redis_key)
    if not saved_code:
        raise HTTPException(400, "验证码不存在，或者已经过期!")

    if saved_code != data.code:
        raise HTTPException(400, detail="验证码输入错误，请注意核对!")

    # 4. 存入数据到数据库，进行后端和数据库的交互必须使用 schemas 模型，不能直接使用数据库的类
    user_create = UserCreateSchema(email=data.email,password=data.password, username=data.username)
    user:User = await user_repo.create(user_create)   # 直接返回 实例化的对象

    #5. 创建起名次数的账户，并赠送3次
    credit_repository = CreditRepository(session)
    credit = await credit_repository.create_register_credit(user_id=user.id, gift_count=3)

    #6. 直接删除验证码数据
    await redis.delete(redis_key)

    return {"messages":f"恭喜您注册成功！！ \n 同时获得{credit.balance}次起名机会 ！！"}


from core.authtools import AuthHandler
from schemas.user_schemas import LoginIn, LoginOutSchema, RefreshOutSchema
from models.User import User
auth_handler=AuthHandler()
# 登录时一般接收用户名和密码
@router.post("/login",response_model=LoginOutSchema)  # 定义输出的 json 格式
async def login(loginInfo:LoginIn,session:AsyncSession=Depends(get_session)):
    # 1.验证这个邮箱是否在我这里注册过。从数据库验证
    user_repo = UserRepository(session)   # 数据库操作工具
    user:User = await  user_repo.get_by_email(email=loginInfo.email)   # 从邮箱中查数据
    if not user:
        raise  HTTPException(status_code=400,detail="该用户不存在")
    if user.status == "frozen":
        raise HTTPException(status_code=423, detail="账号已被冻结，请联系管理员")
    if user.status == "deleted":
        raise HTTPException(status_code=400, detail="该用户不存在")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="账号状态异常")
    # 2.密码验证，如果密码错了，不让登陆
    if not user.check_password(loginInfo.password):
        raise  HTTPException(status_code=400,detail="密码错误，请重新输入")


    # 3.生成jwt token，返回 token 和 用户名、邮箱
    tokens = auth_handler.encode_login_token(user_id=user.id)
    return {
        "user":user,
        "access_token":tokens["access_token"],
        "refresh_token":tokens["refresh_token"],
    }


@router.post("/refresh", response_model=RefreshOutSchema)
async def refresh_access_token(
    user_id: int = Depends(auth_handler.auth_refresh_dependency),
):
    """使用有效的 refresh token 换取新的 access token。"""
    return auth_handler.encode_update_token(user_id=user_id)





from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession
from models.User import User
from  schemas.user_schemas import UserCreateSchema

# 使用类定义数据库的增删改查
class UserRepository:

    def __init__(self,session:AsyncSession):   # AsyncSession 类型声明 异步的连接
        self.session = session

    # 根据邮箱，查询一条数据
    async def get_by_email(self,email:str):
        async with self.session.begin():
            stmt = select(User).where(User.email == email)
            return await self.session.scalar(stmt)

    # 根据邮箱，查询是否邮箱存在
    async def email_is_exist(self,email:str):
        async with self.session.begin():
            stmt = select(exists().where(User.email == email))  # 当 User.email == email 是否存在，不存在返回 True  存在返回 False
            return await self.session.scalar(stmt)   # 对于 select 操作使用 scalar

    # 注册用户，插入一条信息
    async def create(self,user_schema:UserCreateSchema):    # UserCreateSchema 通过这个模型来定义外界要传入数据库数据的模型
        async with self.session.begin():
            user = User(**user_schema.model_dump())    # user_schema.model_dump() 将模型的类型转换为字典类型，解包变成 key = value，就可以定义一个对象
            self.session.add(user)   # 存入一条数据到数据库
            await self.session.flush()    # 刷新就可以数据加载完直接存入数据库，不是等 session 结束后再存。
            return user


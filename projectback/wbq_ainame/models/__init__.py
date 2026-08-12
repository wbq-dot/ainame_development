#  数据库表映射的文件都放到 models 中
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from dotenv import load_dotenv
import os
load_dotenv()


# 做数据的 CRUD 所使用的
DB_URI = os.getenv("DB_URI")


engine = create_async_engine(
url=DB_URI,
# 将输出所有执行SQL的日志（默认是关闭的）
echo=os.getenv("SQL_ECHO", "false").strip().lower() in {"1", "true", "yes", "on"},
# 连接池大小（默认是5个）
pool_size=10,
# 允许连接池最大的连接数（默认是10个）
max_overflow=20,
# 获得连接超时时间（默认是30s）
pool_timeout=10,
# 连接回收时间（默认是-1，代表永不回收）
pool_recycle=3600,
# 连接前是否预检查（默认是False）
pool_pre_ping=True,
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    autoflush=True,   # flush，SQLAlchemy 会自动把内存里的修改同步到数据库事务中
    expire_on_commit=False  # commit() 后仍然可以访问对象属性
)


# DeclarativeBase 类就可以实现一边创建类的实例化属性，一边连接数据库生成表的列名

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

# 定义命名约定的Base类
class Base(DeclarativeBase):
    # MetaData(naming_convention={...}): 这是 SQLAlchemy Core 的元数据容器，自定义表关联属性（即各种约束和索引）的自动生成命名规则
    metadata = MetaData(naming_convention={
        # ix: index，索引
        "ix": "ix_%(column_0_label)s",
        # un: unique，唯一约束
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        # ck: Check，检查约束
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        # fk: Foreign Key，外键约束
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        # pk: Primary Key，主键约束
        "pk": "pk_%(table_name)s"
    })

from . import User    # 当使用 FastAPI 运行main接口时，直接读取导入的软件包，直接执行里面的 __init__.py 文件，放在此处是因为 User 继承了 Base 类，必须先定义 Base 类

# alembic init alembictable --template async   初始化 alembic 表  -> 生成 .idea\alembictable\alembic.init 文件  ->  alembic.ini  注释掉 url 信息
# -> 修改 env.py 文件 context.config.set_main_option("sqlalchemy.url", database_url) 将这个数据库的连接地址给配置文件  ->  将 target_metadata = None (Base.metadata 替换) 将元数据修改成我们 Base 自主定义的
# -> alembic revision --autogenerate -m "自己给定日志" 将我们对 models 的操作转换成对应的 sql 语句，并校验 ->  alembic upgrade head  更新数据库，传入执行的操作

from . import user_credit
from . import package
from . import user_order
from . import account_security
from . import payment_refund
from modules.admin import admin_action_log
from modules.expert import expert_models
from modules.community import community_models
from modules.platform import platform_models


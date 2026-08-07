# 项目根目录新建：init_pg_memory.py
import asyncio
import sys
import os
from dotenv import load_dotenv
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
load_dotenv()

DB_URI = os.getenv("POST_GRESQL_DB")

# 建立记忆储存的四个表
async def setup_memory_db():
    print("正在连接 PostgreSQL...")
    async with AsyncPostgresSaver.from_conn_string(DB_URI) as saver:  # from_conn_string 通过字符串 uri 进行连接
        await saver.setup()        # This method creates the necessary tables in the Postgres database
        print("✅ PostgreSQL 记忆持久化数据表创建成功！")


if __name__ == "__main__":   # 只有该文件的运行才会执行如下代码
    # ⚠️ 专治 Windows 下的异步兼容性报错
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(setup_memory_db())   # 异步的运行函数


# postgresql 储存持久化记忆力
'''
1. 安装依赖
pip install langgraph-checkpoint-postgres "psycopg[binary]"
2. 创建ainame数据库  
3. 编写创建数据表脚本 -- 创建 4 个表 
'''




'''
redis 的基础操作：  key - value (存储的内容  String(字符串)、List(链表)、set(集合)、zset(有序集合))
1. 增加和修改数据 :  set key value   set old_key new_value
2. 查看数据 : get key
3. 储存带有时间限制的数据: setex key seconde value
4. 查看数据存储还有多少时间 : ttl key
5. 删除数据： del key
6. 不修改的增加： setnx key value  存在不修改和添加，不存在添加

python 中使用 Redis
安装: pip install redis

'''

import redis
import time

uri = "redis://127.0.0.1:6379/0"  # 6379 端口号   0 数据库的编号  0-15

# 创建客户端
redis_client = redis.from_url(
    uri, # 地址
    decode_responses=True,   # 二进制解码
    encoding="utf-8"     # 编码的方式
)

# 增
redis_client.set("python","123456")  # 永久存储
redis_client.set("code2","123456",50)  # 按照秒数储存

# 查询
# 查询值
print(redis_client.get("python"))

# 查询是否存在
time.sleep(20)
print(redis_client.exists("code2"))   # 1

time.sleep(31)
print(redis_client.exists("code2"))  # 0

# 删除
redis_client.delete("code2")

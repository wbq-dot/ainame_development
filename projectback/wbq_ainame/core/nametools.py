'''
安装依赖包:
1. 安装 langchain
pip install langchain==1.1.0
2. 安装 langchain-deepseek
pip install langchain-deepseek==1.0.1
'''


import asyncio
from langchain_deepseek import ChatDeepSeek
from langchain_core.prompts import ChatPromptTemplate
from schemas.name_schemas import NameResultSchema
from dotenv import load_dotenv
import os

# 读取项目根目录下的 .env 文件
load_dotenv()

# 使用 ChatDeepSeek 来连接大模型 API
llm = ChatDeepSeek(
    model="deepseek-v4-pro",   # 连接的模型 deepseek-chat 即将过期
    api_key=os.getenv("DEEP_SEEKER_API_KEY"),  # API-key
    temperature=0.5,   # 模型的温度，0.3 ~ 0.5 内容比较真实，有一些发散
    timeout=120,      # 请求延时
    extra_body={
        "thinking": {
            "type": "disabled"
        }
    }        # 额外的一些配置，关闭思考模式，按照给定的模版输出
)

# 系统提示词
system_prompt = """你是一位精通汉语言文学与传统文化的命名专家。请为用户创作富有文化底蕴的人名。
原则：平仄协调，寓意深远，优先从《诗经》《楚辞》或唐诗宋词中汲取灵感。
请给出 5 个候选方案。"""

# 系统提示词和应用工具的提示词模版
prompt_template = ChatPromptTemplate.from_messages([
    ("system", system_prompt),   # 无论大模型调用哪个工具或输入什么内容，都要遵守系统提示词的要求
    ("user", "【姓氏】:{surname} 【性别】:{gender} 【字数限制】:{length} 【其它要求】:{other} 【避讳字】:{exclude}"),
])     # 接受用户提交的提示词，提交是通过函数来实现的

# with_structured_output 使用自定义的输出结构化模版
structured_llm = llm.with_structured_output(NameResultSchema)
# 通道的传递链，依次执行
chain = prompt_template | structured_llm

from schemas.name_schemas import NameIn

# 定义异步函数接受客户传入的参数
async def generate_name(name_info:NameIn):   # 客户传入的值进行模版校验，name_info:NameIn 外部传入的参数必须满足这个类的定义

    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = await chain.ainvoke({      # 异步的传值，模型输出
                "surname": name_info.surname,
                "gender": name_info.gender,
                "length": name_info.length,
                "other": name_info.other,
                "exclude": name_info.exclude
            })

            if result is not None:
                return result
        except Exception as e:
            print(f"❌ 第 {attempt + 1} 次请求遭遇网络异常: {e}，正在重试...")
    return {"names":["三次机会已用完，没有返回姓名结果！！"]}


# 测试代码，看看是否可用
# async def main():
#     name_info = NameIn(
#         surname="张",
#         gender="女",
#         length="三字",
#         other="希望名字里带点水的意象",
#         exclude=["李", "王"]
#     )
#     result = await generate_name(name_info)
#     print(result)
#
# if __name__ == "__main__":
#     asyncio.run(main())
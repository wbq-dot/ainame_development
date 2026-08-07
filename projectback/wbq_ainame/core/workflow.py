from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_deepseek import ChatDeepSeek
from schemas.name_schemas import NameIn
from schemas.name_schemas import NameResultSchema
from core.rag_service import retrieve_user_knowledge
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from schemas.name_schemas import FeedbackIn
from core.domaintools import check_domain
import asyncio
from dotenv import load_dotenv
import os
import uuid

# 读取项目根目录下的 .env 文件
load_dotenv()


# 1. 定义图的状态（State）传递结构，在流程里既作为输出结果也作为输入参数
class WorkflowState(TypedDict):
    user_id: int    # 让节点知道调用那个用户的 rag 知识库
    category: str
    surname: str
    gender: str
    length: str
    other: str
    exclude: List[str]
    final_output: Dict[str, Any] # 存放下游 Agent 生成的结构化数据，就是存放模型输出的起名结果
    history_names: str    # 之前的记忆历史
    feedback: str

# 2. 初始化 DeepSeek 大模型
llm = ChatDeepSeek(
    model="deepseek-v4-pro",
    api_key=os.getenv("DEEP_SEEKER_API_KEY"),
    temperature=0.5,
    timeout=120,
    extra_body={
        "thinking": {
            "type": "disabled"   # 关闭推理能力才能结构化输出
        }
    }
)


# 3. 强制大模型输出我们定义的 Pydantic 结构  .with_retry 重试调用大模型多少次
structured_llm = llm.with_structured_output(NameResultSchema).with_retry(stop_after_attempt=3)


# 4. 定义节点

# 开始节点/主管节点，将任务分发到其他分节点
async def supervisor_node(state: WorkflowState) -> Dict[str, Any]:
    """主管节点：后续可在这里扩展意图清洗或记录日志"""
    return {}

# 人名节点
async def human_naming_node(state: WorkflowState) -> Dict[str, Any]:
    """人名专家节点"""    # 给大模型看节点的提示词
    prompt = f"""你是一位精通汉语言文学与传统文化的命名专家。请为用户创作富有文化底蕴的人名。
    【姓氏】: {state['surname']}
    【性别倾向】: {state['gender']}
    【字数限制】: {state['length']}
    【其它具体要求】: {state['other']}
    【避讳排除字】: {'、'.join(state['exclude'])}
    原则：平仄协调，优先从《诗经》《楚辞》或唐诗宋词中汲取灵感。请给出 5 个候选方案。"""  # 输入到大模型 ainvoke 中的信息
    response = await structured_llm.ainvoke(prompt)
    return {"final_output": response.model_dump()}

# 企业起名的节点
async def company_naming_node(state: WorkflowState) -> Dict[str, Any]:

    """企业品牌节点"""

    # 通过id 和 检索信息查找相似度高的数据
    user_id = state['user_id']   # 得到用户的 id 号
    search_query = "品牌命名规范"   # 检索的问题
    rag_context = retrieve_user_knowledge(query=search_query,user_id=user_id)  # 返回通过知识库 (向量数据库) 中检索到的数据
    # 将检索出的数据拼接成提示词
    if rag_context:
        rag_prompt = f"""
    【用户的专属私有知识库参考】
    {rag_context}
    原则：请优先参考上面的规则和词汇。
    """                        # 给大模型另外补充的提示词
    else:
        rag_prompt = """
    本次没有检索到足够相关的专属资料。
    原则：不要编造用户知识库内容，直接根据用户需求生成。
    """

    # 将 rag 提示词和用户信息提示词组合
    prompt = f"""你是一位精通商业品牌传播的资深顾问。请创作符合商业规范的公司名。
    【用户需求】
    行业或核心诉求: {state['other']}
    字数限制: {state['length']}
    避讳排除字: {'、'.join(state['exclude'])}
    
    {rag_prompt}。 最后，请给出 5 个候选方案。"""


    # prompt = f"""你是一位精通商业品牌传播与工商命名的资深顾问。请创作符合商业规范的公司名。
    # 【行业或核心诉求】: {state['other']}
    # 【字数限制】: {state['length']}
    # 【避讳排除字】: {'、'.join(state['exclude'])}
    # 原则：易于传播、符合行业调性，具备良好的商业愿景。请给出 5 个候选方案。"""

    # 需要微调走的位置
    feedback = state.get("feedback")  # 用户的调整意见
    history_names = state.get("history_names") # 上一次大模型生成的历史结果
    if feedback and history_names:    # 两个都不为空才可以判断为是微调
        # 将意见和历史起名结果一起拼成提示词
        feedback_instruction = f"""
                🟣 警告：这是一次微调请求！
                【上一轮你生成的名字是】：{history_names}
                【用户的最新修改意见】：{feedback}

                请严格保留上一轮中用户满意的部分，仅针对【修改意见】对历史名字进行迭代优化！绝不能抛弃历史记录重新随机生成！
                """
        # 再将反馈的提示词信息和之前的初始需求一起拼接成新的提示词
        prompt = f"""你是一位资深的起名顾问。
               【用户初始需求】：{prompt}

               {feedback_instruction}

               🔴 核心纪律：如果有用户的修改意见，必须完全服从！给出 5 个候选方案。"""


    # 这个是将输出的结果拼成字符串作为历史起名
    response = await structured_llm.ainvoke(prompt)   # 里面包含域名和域名状态  {tread_id:..., names:[{name:,domain:,domain_state:}...]}
    # tasks = ["未注册"，“已注册”，"未注册"，“已注册”，“已注册”]
    tasks = [check_domain(n.domain) for n in response.names]  # for n in [{name:,domain:,domain_state:},...]
    statuses = await asyncio.gather(*tasks)   # 用于并发执行多个异步任务并聚合结果的核心高阶 API，最后返回结果的排序和传入服务器参数的原始序列一致

    for n, status in zip(response.names, statuses):   # [({name:,domain:,domain_state:},status),...] 拼接一个名字字典和对应的域名状态的元组
        n.domain_status = status

    # 使用新的起名结果替换历史的起名结果
    memory_list = [f"【{n.name}】寓意：{n.moral}" for n in response.names]
    names_str = "\n".join(memory_list)

    return {"final_output": response.model_dump(), "history_names": names_str}   # model_dump() 就是将 WorkflowState 类的输出格式 -> dict


# 宠物起名的节点
async def pet_naming_node(state: WorkflowState) -> Dict[str, Any]:
    """宠物起名节点"""
    prompt = f"""你是一位充满创意的宠物达人。请为用户的宠物起一些富有灵性的名字。
    【宠物特征/性格】: {state['other']}
    【字数限制】: {state['length']}
    【避讳排除字】: {'、'.join(state['exclude'])}
    原则：亲切好记、富有画面感或软萌感。请给出 5 个候选方案。"""
    response = await structured_llm.ainvoke(prompt)
    return {"final_output": response.model_dump()}

# 5. 构建流程图
workflow = StateGraph(WorkflowState)  # StateGraph(定义图的状态)
# 加节点
workflow.add_node("supervisor_node", supervisor_node)  # workflow.add_node(node, 节点函数)
workflow.add_node("human_naming_node", human_naming_node)
workflow.add_node("company_naming_node", company_naming_node)
workflow.add_node("pet_naming_node", pet_naming_node)

workflow.set_entry_point("supervisor_node")   # .set_entry_point()  Specifies the first node to be called in the graph  定义起始节点

# 定义节点流转的条件函数
def route_by_category(state: WorkflowState) :
    """条件路由：根据前端传来的 category 决定走哪个节点"""
    category_map = {"人名": "human_node", "企业名": "company_node", "宠物名": "pet_node"}
    return category_map.get(state.get("category"))  # state.get("category") == 起名的分类  category_map.get(state.get("category")) 对应的节点名字

# 定义条件边，起始节点 -> 条件函数通过客户传入的分类信息 -> 分类节点的名字 -> 分类节点
workflow.add_conditional_edges("supervisor_node",route_by_category,
{"human_node": "human_naming_node", "company_node": "company_naming_node", "pet_node": "pet_naming_node"}
)

# 最后的边  任意分类的节点 -> END
workflow.add_edge("human_naming_node", END)
workflow.add_edge("company_naming_node", END)
workflow.add_edge("pet_naming_node", END)

# naming_graph = workflow.compile()   # 编译流程图


# 给 lang_graph 加记忆，当服务启动就连接记忆
POSTGRESQL_DB = os.getenv("POST_GRESQL_DB")
connection_pool = None
naming_graph = None

# 定义开启记忆函数，一旦运行带记忆的 lang_graph 就被部署
async def init_workflow_graph():
    """在 FastAPI 启动时调用此函数来初始化图和连接池"""
    global connection_pool, naming_graph
    connection_pool = AsyncConnectionPool(POSTGRESQL_DB, max_size=10)   #  定义连接池类，连接postgresql 数据库
    memory = AsyncPostgresSaver(connection_pool)    # 开启这个连接池的记忆功能
    # 编译带记忆的智能体
    naming_graph = workflow.compile(checkpointer=memory)

# 定义关闭记忆函数
async def close_workflow_graph():
    """在 FastAPI 关闭时清理连接"""
    global connection_pool
    if connection_pool:
        await connection_pool.close()   # 关闭连接池


async def generate_naming(name_info: NameIn,user_id:int):
    """提供给 Router 调用的统一异步接口"""
    thread_id = str(uuid.uuid4())   # 自动的生成一个随机的id，每次生成的都不一样 uuid1 uuid3 uuid4 uuid5

    # 初始化状态参数
    workflow_state = {
    "user_id":user_id,
    "category": name_info.category,
    "surname": name_info.surname,
    "gender": name_info.gender,
    "length": name_info.length,
    "other": name_info.other,
    "exclude": name_info.exclude,
    "final_output": {}
    }

    config = {"configurable": {"thread_id": thread_id}}      # 得到 thread_id 的配置
    final_output = await naming_graph.ainvoke(workflow_state, config)   # 带记忆的 naming_graph

    # final_state = await naming_graph.ainvoke(workflow_state)  # 将初始化的参数传入流程图的状态结构里
    return {"thread_id":thread_id,"final_output":final_output.get("final_output",None)}    # final_output.get("final_output",None)  得到 "final_output" 的值


# 历史起名微调的函数
async def feedback_naming(fedback_in: FeedbackIn,user_id:int):
    # 其他的 other length ...  可以由之前的历史起名状态获得，但是 user_id 和 category 的传入是为了让后端再次确认好用户的标识和分类，防止流程无法触发。
    workflow_state = {
        "user_id": user_id,
        "category": fedback_in.category,
        "feedback": fedback_in.feedback
    }

    config = {"configurable": {"thread_id": fedback_in.thread_id}}    # 配置 thread_id 拿到所有起名的历史结果
    # 将记忆和微调信息传入流转图的状态中
    final_output = await naming_graph.ainvoke(workflow_state, config)
    return {"thread_id": fedback_in.thread_id, "final_output": final_output.get("final_output", None)}


from typing import TypedDict, List, Dict, Any
import logging
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
logger = logging.getLogger(__name__)


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
    use_private_knowledge: bool


class WorkflowSessionNotFoundError(ValueError):
    pass


class WorkflowSessionAccessError(PermissionError):
    pass


class WorkflowSessionCategoryError(ValueError):
    pass


def _feedback_instruction(state: WorkflowState) -> str:
    feedback = (state.get("feedback") or "").strip()
    history_names = (state.get("history_names") or "").strip()
    if not feedback or not history_names:
        return ""
    return f"""
    【上一轮候选名字】
    {history_names}
    【用户本轮调整意见】
    {feedback}
    这是同一轮会话的继续调整。请结合上一轮候选，严格执行用户意见；明确要求保留的名字必须保留，其余候选再针对性优化。
    """


def _history_names(response: NameResultSchema) -> str:
    return "\n".join(f"【{item.name}】寓意：{item.moral}" for item in response.names)


def _knowledge_prompt(
    user_id: int,
    query: str,
    focus: str,
    knowledge_type: str,
    fallback_query: str | None = None,
    use_private_knowledge: bool = True,
) -> str:
    """按当前起名类型检索用户私有知识库，并生成可安全拼入提示词的上下文。"""
    if not use_private_knowledge:
        return "【专属知识库】开放平台调用不读取普通用户私人资料。"
    rag_context = retrieve_user_knowledge(
        query=query,
        user_id=user_id,
        knowledge_type=knowledge_type,
        fallback_query=fallback_query,
    )
    if not rag_context:
        return f"""
    【专属知识库】本次没有检索到与{focus}足够相关的资料。
    请直接根据用户要求创作，不要编造或声称引用了用户知识库。
    """
    return f"""
    【用户专属知识库参考：{focus}】
    {rag_context}
    请优先遵守其中的命名规则、偏好、禁忌和背景信息；若与用户本次明确要求冲突，以本次要求为准。
    """

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
    exclude_text = "、".join(state["exclude"])
    core_requirement = (state.get("other") or "").strip()
    rag_prompt = await asyncio.to_thread(
        _knowledge_prompt,
        user_id=state["user_id"],
        query=" ".join(
            part
            for part in [
                "孩子起名",
                core_requirement,
                f"姓氏{state['surname']}" if state.get("surname") else "",
                f"避讳{exclude_text}" if exclude_text else "",
            ]
            if part
        ),
        fallback_query=" ".join(
            part
            for part in [
                core_requirement,
                f"避讳{exclude_text}" if exclude_text else "",
            ]
            if part
        ),
        focus="人名命名",
        knowledge_type="human",
        use_private_knowledge=state.get("use_private_knowledge", True),
    )
    prompt = f"""你是一位精通汉语言文学与传统文化的命名专家。请为用户创作富有文化底蕴的人名。
    【姓氏】: {state['surname']}
    【性别倾向】: {state['gender']}
    【字数限制】: {state['length']}
    【其它具体要求】: {state['other']}
    【避讳排除字】: {'、'.join(state['exclude'])}
    {rag_prompt}
    {_feedback_instruction(state)}
    原则：平仄协调，优先从《诗经》《楚辞》或唐诗宋词中汲取灵感。请给出 5 个候选方案。"""  # 输入到大模型 ainvoke 中的信息
    response = await structured_llm.ainvoke(prompt)
    return {
        "final_output": response.model_dump(),
        "history_names": _history_names(response),
    }

# 企业起名的节点
async def company_naming_node(state: WorkflowState) -> Dict[str, Any]:

    """企业品牌节点"""

    exclude_text = "、".join(state["exclude"])
    core_requirement = (state.get("other") or "").strip()
    rag_prompt = await asyncio.to_thread(
        _knowledge_prompt,
        user_id=state["user_id"],
        query=" ".join(
            part
            for part in [
                "企业品牌起名",
                core_requirement,
                f"避讳{exclude_text}" if exclude_text else "",
            ]
            if part
        ),
        fallback_query=core_requirement,
        focus="企业品牌命名",
        knowledge_type="company",
        use_private_knowledge=state.get("use_private_knowledge", True),
    )

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

    feedback_instruction = _feedback_instruction(state)
    if feedback_instruction:
        prompt = f"""{prompt}
        {feedback_instruction}
        请输出调整后的 5 个候选方案。"""


    # 这个是将输出的结果拼成字符串作为历史起名
    response = await structured_llm.ainvoke(prompt)   # 里面包含域名和域名状态  {tread_id:..., names:[{name:,domain:,domain_state:}...]}
    # tasks = ["未注册"，“已注册”，"未注册"，“已注册”，“已注册”]
    tasks = [check_domain(n.domain) for n in response.names]  # for n in [{name:,domain:,domain_state:},...]
    statuses = await asyncio.gather(*tasks, return_exceptions=True)   # 域名服务不可用不能导致整次公司起名失败

    for n, status in zip(response.names, statuses):   # [({name:,domain:,domain_state:},status),...] 拼接一个名字字典和对应的域名状态的元组
        if isinstance(status, Exception):
            logger.warning("域名查询失败：域名=%s，异常=%s", n.domain, status)
            n.domain_status = "⚠️ 域名查询暂时不可用"
        else:
            n.domain_status = status

    # 使用新的起名结果替换历史的起名结果
    return {"final_output": response.model_dump(), "history_names": _history_names(response)}   # model_dump() 就是将 WorkflowState 类的输出格式 -> dict


# 宠物起名的节点
async def pet_naming_node(state: WorkflowState) -> Dict[str, Any]:
    """宠物起名节点"""
    exclude_text = "、".join(state["exclude"])
    core_requirement = (state.get("other") or "").strip()
    rag_prompt = await asyncio.to_thread(
        _knowledge_prompt,
        user_id=state["user_id"],
        query=" ".join(
            part
            for part in [
                "宠物起名",
                core_requirement,
                f"避讳{exclude_text}" if exclude_text else "",
            ]
            if part
        ),
        fallback_query=core_requirement,
        focus="宠物命名",
        knowledge_type="pet",
        use_private_knowledge=state.get("use_private_knowledge", True),
    )
    prompt = f"""你是一位充满创意的宠物达人。请为用户的宠物起一些富有灵性的名字。
    【宠物特征/性格】: {state['other']}
    【字数限制】: {state['length']}
    【避讳排除字】: {'、'.join(state['exclude'])}
    {rag_prompt}
    {_feedback_instruction(state)}
    原则：亲切好记、富有画面感或软萌感。请给出 5 个候选方案。"""
    response = await structured_llm.ainvoke(prompt)
    return {
        "final_output": response.model_dump(),
        "history_names": _history_names(response),
    }

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


async def delete_naming_thread(thread_id: str) -> None:
    """删除指定用户会话的全部 LangGraph 检查点。"""
    if naming_graph is None or naming_graph.checkpointer is None:
        raise RuntimeError("起名工作流尚未初始化")
    await naming_graph.checkpointer.adelete_thread(thread_id)


async def generate_naming(name_info: NameIn, user_id: int, use_private_knowledge: bool = True):
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
    ,"use_private_knowledge": use_private_knowledge
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
    snapshot = await naming_graph.aget_state(config)
    previous_state = snapshot.values or {}
    if not previous_state:
        raise WorkflowSessionNotFoundError("起名会话不存在或已失效，请重新生成一组名字")
    if previous_state.get("user_id") != user_id:
        raise WorkflowSessionAccessError("无权访问该起名会话")
    if previous_state.get("category") != fedback_in.category:
        raise WorkflowSessionCategoryError("起名类型与原会话不一致")

    # 兼容修复前已经生成的人名/宠物名会话：旧记录没有 history_names，
    # 但 final_output 中仍保留了候选名字，可在反馈时恢复为历史上下文。
    if not previous_state.get("history_names"):
        previous_names = (previous_state.get("final_output") or {}).get("names") or []
        if previous_names:
            workflow_state["history_names"] = "\n".join(
                f"【{item.get('name', '')}】寓意：{item.get('moral', '')}"
                for item in previous_names
            )

    # 将记忆和微调信息传入流转图的状态中
    final_output = await naming_graph.ainvoke(workflow_state, config)
    return {"thread_id": fedback_in.thread_id, "final_output": final_output.get("final_output", None)}


import os
import re
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

# 读取项目根目录下的 .env 文件
load_dotenv()

# 使用本地 Ollama 的 Qwen3 向量模型。
OLLAMA_EMBEDDING_MODEL = os.getenv(
    "OLLAMA_EMBEDDING_MODEL",
    "qwen3-embedding:4b",
).strip()
OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://127.0.0.1:11434",
).strip().rstrip("/")

ollamaEmbeddin = OllamaEmbeddings(
    model=OLLAMA_EMBEDDING_MODEL,
    base_url=OLLAMA_BASE_URL,
)


def get_collection_name(user_id: int) -> str:
    """不同向量模型使用独立集合，防止向量维度不一致。"""
    model_suffix = re.sub(r"[^a-zA-Z0-9_-]", "_", OLLAMA_EMBEDDING_MODEL)
    return f"user_{user_id}_docs_{model_suffix}"
# 向量化数据库位置
CHROMDB_PATH = os.getenv("CHROMDB_PATH")


# 向量化用户文件
def process_and_store_file(file_path:str,user_id:int):
    # 判断文件类型，选择自己加载方式
    if file_path.endswith(".pdf"):   # .endswith()  通过后缀判断文件类型
        loader = PyPDFLoader(file_path)
    elif file_path.endswith(".txt"):
        loader = TextLoader(file_path,encoding="utf-8")
    else:
        print("Invalid file type")
        return    # 直接 return 跳出函数

    docs = loader.load()

    # 切分文件的工具
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
        add_start_index=True
    )

    # 切割
    all_splits = text_splitter.split_documents(docs)

    # 切割的碎片向量化
    vector_store = Chroma(
        collection_name=get_collection_name(user_id),
        embedding_function=ollamaEmbeddin,   # 向量化的工具
        persist_directory=CHROMDB_PATH     # 存储的路径位置
    )

    vector_store.add_documents(all_splits)
    print(f"[后台任务完成] 用户 {user_id} 的知识库更新完毕！存入 {len(all_splits)} 个文本块。")



def retrieve_user_knowledge(
    query: str,
    user_id: int,   # 指明找那个客户的数据库
    top_k: int = 5,  # 从数据库找5条信息
    min_score: float = 0.65  # 向量库检索数据的评分
) -> str | None:


    # 连接到该用户的专属库
    vector_store = Chroma(
    collection_name=get_collection_name(user_id),
    embedding_function=ollamaEmbeddin,   # 向量化的工具和我们做向量库时必须一致
    persist_directory=CHROMDB_PATH       # 持久化向量数据库的路径
    )

    #  try except  如果客户没传rag 知识库防止报错
    try:
        results = vector_store.similarity_search_with_relevance_scores(query,k=top_k)  # similarity_search_with_relevance_scores 将相似度归一化后的结果，真实的得分
        qualified_docs = [doc for doc, score in results if score >= min_score]  # 筛选得分高于 0.65 的数据，低于的都舍弃
        if not qualified_docs:
            return None
        return "\n".join([doc.page_content for doc in qualified_docs])  # 将输出的结果换行拼接成字符串
    except Exception:
        return None

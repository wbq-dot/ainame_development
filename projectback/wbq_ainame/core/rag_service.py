import hashlib
import logging
import os
import re
import time
from pathlib import Path

import chromadb
import httpx
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from ollama import Client, ResponseError
from dotenv import load_dotenv

# 读取项目根目录下的 .env 文件
load_dotenv()
logger = logging.getLogger(__name__)

# 使用本地 Ollama 的 Qwen3 向量模型。
OLLAMA_EMBEDDING_MODEL = os.getenv(
    "OLLAMA_EMBEDDING_MODEL",
    "qwen3-embedding:4b",
).strip()
OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://127.0.0.1:11434",
).strip().rstrip("/")
OLLAMA_REQUEST_TIMEOUT = float(os.getenv("OLLAMA_REQUEST_TIMEOUT", "180"))
RAG_EMBED_BATCH_SIZE = max(1, int(os.getenv("RAG_EMBED_BATCH_SIZE", "8")))
RAG_EMBED_MAX_ATTEMPTS = max(1, int(os.getenv("RAG_EMBED_MAX_ATTEMPTS", "4")))
RAG_EMBED_RETRY_DELAY = max(0.1, float(os.getenv("RAG_EMBED_RETRY_DELAY", "3")))
RAG_TOP_K = max(1, int(os.getenv("RAG_TOP_K", "3")))
KNOWLEDGE_TYPES = {"general", "human", "company", "pet"}
BACKEND_DIR = Path(__file__).resolve().parents[1]


def _optional_score(name: str) -> float | None:
    value = os.getenv(name, "").strip()
    return float(value) if value else None


# 默认不使用固定分数门槛。Chroma 默认使用 L2 距离，不同向量模型的归一化
# 分数范围并不一致；固定写死 0.65 会把已经按分类命中的资料再次错误过滤掉。
RAG_PRIMARY_MIN_SCORE = _optional_score("RAG_PRIMARY_MIN_SCORE")
RAG_FALLBACK_MIN_SCORE = _optional_score("RAG_FALLBACK_MIN_SCORE")


class KnowledgeRetrievalUnavailableError(RuntimeError):
    """知识库向量服务不可用，不能把该故障伪装成普通的未命中。"""


def normalize_knowledge_type(knowledge_type: str) -> str:
    value = (knowledge_type or "general").strip().lower()
    if value not in KNOWLEDGE_TYPES:
        raise ValueError("知识类型必须是 general、human、company 或 pet")
    return value

class LocalOllamaEmbeddings(Embeddings):
    """Use a minimal local Ollama request without proxy or generation options."""

    def __init__(self, model: str, base_url: str, timeout: float) -> None:
        self.model = model
        self.client = Client(
            host=base_url,
            timeout=timeout,
            trust_env=False,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embed(model=self.model, input=texts)
        return response["embeddings"]

    def embed_query(self, text: str) -> list[float]:
        response = self.client.embed(model=self.model, input=text)
        return response["embeddings"][0]


ollamaEmbeddin = LocalOllamaEmbeddings(
    model=OLLAMA_EMBEDDING_MODEL,
    base_url=OLLAMA_BASE_URL,
    timeout=OLLAMA_REQUEST_TIMEOUT,
)


def get_collection_name(user_id: int) -> str:
    """不同向量模型使用独立集合，防止向量维度不一致。"""
    model_suffix = re.sub(r"[^a-zA-Z0-9_-]", "_", OLLAMA_EMBEDDING_MODEL)
    return f"user_{user_id}_docs_{model_suffix}"


# 向量化数据库位置
def _resolve_chromadb_path(raw_path: str | None) -> str:
    normalized_path = (raw_path or "").strip() or "chroma_rag_db"
    path = Path(normalized_path).expanduser()
    if not path.is_absolute():
        path = BACKEND_DIR / path
    return str(path.resolve())


CHROMDB_PATH = _resolve_chromadb_path(os.getenv("CHROMDB_PATH"))


def delete_user_knowledge(user_id: int) -> int:
    """删除用户在所有向量模型版本下的知识库集合。"""
    chroma_path = Path(CHROMDB_PATH)
    if not chroma_path.exists():
        return 0

    client = chromadb.PersistentClient(path=CHROMDB_PATH)
    prefix = f"user_{user_id}_docs_"
    deleted_count = 0
    for collection in client.list_collections():
        collection_name = (
            collection.name if hasattr(collection, "name") else str(collection)
        )
        if collection_name.startswith(prefix):
            client.delete_collection(collection_name)
            deleted_count += 1
    return deleted_count


def _document_ids(file_path: str, user_id: int, count: int) -> list[str]:
    """为同一次上传生成稳定ID，任务重试时覆盖而不是重复插入。"""
    source = str(Path(file_path).resolve())
    return [
        hashlib.sha256(f"{user_id}:{source}:{index}".encode("utf-8")).hexdigest()
        for index in range(count)
    ]


def _is_retryable_embedding_error(exc: Exception) -> bool:
    if isinstance(exc, ResponseError):
        return exc.status_code in {500, 502, 503, 504}
    return isinstance(exc, (httpx.TimeoutException, httpx.TransportError))


def _add_batch_with_retry(vector_store: Chroma, documents: list, ids: list[str]) -> None:
    for attempt in range(1, RAG_EMBED_MAX_ATTEMPTS + 1):
        try:
            vector_store.add_documents(documents, ids=ids)
            return
        except Exception as exc:
            if not _is_retryable_embedding_error(exc) or attempt >= RAG_EMBED_MAX_ATTEMPTS:
                raise
            delay = RAG_EMBED_RETRY_DELAY * (2 ** (attempt - 1))
            logger.warning(
                "Ollama向量化暂时失败，第 %s/%s 次，%.1f秒后重试：%s",
                attempt,
                RAG_EMBED_MAX_ATTEMPTS,
                delay,
                exc,
            )
            time.sleep(delay)


# 向量化用户文件
def process_and_store_file(
    file_path: str,
    user_id: int,
    knowledge_type: str = "general",
) -> int:
    knowledge_type = normalize_knowledge_type(knowledge_type)
    # 判断文件类型，选择自己加载方式
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":   # .endswith()  通过后缀判断文件类型
        loader = PyPDFLoader(file_path)
    elif suffix == ".txt":
        loader = TextLoader(file_path,encoding="utf-8")
    else:
        raise ValueError("只支持 PDF 或 TXT 文件")

    docs = loader.load()

    # 切分文件的工具
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
        add_start_index=True
    )

    # 切割
    all_splits = text_splitter.split_documents(docs)
    if not all_splits:
        raise ValueError("文件中没有可用于构建知识库的文本")

    for document in all_splits:
        document.metadata["knowledge_type"] = knowledge_type

    # 切割的碎片向量化
    vector_store = Chroma(
        collection_name=get_collection_name(user_id),
        embedding_function=ollamaEmbeddin,   # 向量化的工具
        persist_directory=CHROMDB_PATH     # 存储的路径位置
    )

    all_ids = _document_ids(file_path, user_id, len(all_splits))
    try:
        for start in range(0, len(all_splits), RAG_EMBED_BATCH_SIZE):
            end = min(start + RAG_EMBED_BATCH_SIZE, len(all_splits))
            _add_batch_with_retry(
                vector_store,
                all_splits[start:end],
                all_ids[start:end],
            )
            logger.info(
                "用户 %s 知识库向量化进度：%s/%s",
                user_id,
                end,
                len(all_splits),
            )
    except Exception:
        try:
            vector_store.delete(ids=all_ids)
        except Exception:
            logger.exception("清理失败知识库任务的临时向量时出错")
        raise

    logger.info(
        "后台任务完成：用户 %s 的知识库已存入 %s 个文本块",
        user_id,
        len(all_splits),
    )
    return len(all_splits)



def _qualified_documents(results: list, min_score: float | None) -> list:
    if min_score is None:
        return [document for document, _ in results]
    return [document for document, score in results if score >= min_score]


def _log_scores(
    user_id: int,
    knowledge_type: str,
    stage: str,
    results: list,
) -> None:
    logger.info(
        "知识库检索：用户=%s，分类=%s，阶段=%s，分数=%s",
        user_id,
        knowledge_type,
        stage,
        [round(score, 4) for _, score in results],
    )


def retrieve_user_knowledge(
    query: str,
    user_id: int,
    knowledge_type: str = "general",
    fallback_query: str | None = None,
    top_k: int | None = None,
    primary_min_score: float | None = None,
    fallback_min_score: float | None = None,
) -> str | None:
    """先按分类精确检索，再用精简词降级；兼容没有分类元数据的旧知识块。"""
    knowledge_type = normalize_knowledge_type(knowledge_type)
    top_k = top_k or RAG_TOP_K
    primary_min_score = (
        RAG_PRIMARY_MIN_SCORE
        if primary_min_score is None
        else primary_min_score
    )
    fallback_min_score = (
        RAG_FALLBACK_MIN_SCORE
        if fallback_min_score is None
        else fallback_min_score
    )
    allowed_types = list(dict.fromkeys([knowledge_type, "general"]))
    metadata_filter = {"knowledge_type": {"$in": allowed_types}}

    try:
        vector_store = Chroma(
            collection_name=get_collection_name(user_id),
            embedding_function=ollamaEmbeddin,
            persist_directory=CHROMDB_PATH,
        )
        collection_probe = vector_store.get(
            limit=1,
            include=["metadatas"],
        )
        if not collection_probe.get("ids"):
            return None

        category_probe = vector_store.get(
            where=metadata_filter,
            limit=1,
            include=["metadatas"],
        )
        has_categorized_documents = bool(category_probe.get("ids"))

        if not has_categorized_documents:
            first_metadata = (collection_probe.get("metadatas") or [{}])[0] or {}
            if first_metadata.get("knowledge_type"):
                # 集合中有分类数据，但当前分类没有资料。不能退化为无过滤检索，
                # 否则公司起名可能错误读到人名或宠物资料。
                return None

            # 兼容修复前没有 knowledge_type 元数据的旧知识块。
            legacy_query = fallback_query or query
            legacy_results = vector_store.similarity_search_with_relevance_scores(
                legacy_query,
                k=top_k,
            )
            _log_scores(user_id, knowledge_type, "旧数据兼容检索", legacy_results)
            documents = _qualified_documents(legacy_results, fallback_min_score)
            if not documents:
                return None
            return "\n".join(document.page_content for document in documents)

        categorized_primary = vector_store.similarity_search_with_relevance_scores(
            query,
            k=top_k,
            filter=metadata_filter,
        )
        _log_scores(user_id, knowledge_type, "分类主检索", categorized_primary)
        documents = _qualified_documents(categorized_primary, primary_min_score)
        if documents:
            return "\n".join(document.page_content for document in documents)

        categorized_fallback = []
        if fallback_query and fallback_query.strip() != query.strip():
            categorized_fallback = vector_store.similarity_search_with_relevance_scores(
                fallback_query,
                k=top_k,
                filter=metadata_filter,
            )
            _log_scores(user_id, knowledge_type, "分类降级检索", categorized_fallback)
            documents = _qualified_documents(
                categorized_fallback,
                fallback_min_score,
            )
            if documents:
                return "\n".join(document.page_content for document in documents)

        return None
    except Exception as exc:
        logger.exception(
            "知识库检索失败：用户=%s，分类=%s，数据库=%s，异常类型=%s",
            user_id,
            knowledge_type,
            CHROMDB_PATH,
            type(exc).__name__,
        )
        raise KnowledgeRetrievalUnavailableError(
            _retrieval_error_message(exc)
        ) from exc


def _exception_chain(exc: Exception):
    current = exc
    seen = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def _retrieval_error_message(exc: Exception) -> str:
    errors = list(_exception_chain(exc))
    if any(isinstance(error, httpx.TimeoutException) for error in errors):
        return "知识库向量模型请求超时，请稍后重试"
    if any(isinstance(error, httpx.ConnectError) for error in errors):
        return "无法连接知识库向量模型服务，请检查向量服务地址和进程状态"
    if any(isinstance(error, ResponseError) for error in errors):
        return "知识库向量模型返回错误，请检查模型名称和服务端日志"
    if any(
        isinstance(error, ConnectionError) and "ollama" in str(error).lower()
        for error in errors
    ):
        return "无法连接知识库向量模型服务，请检查向量服务地址和进程状态"
    return "知识库检索执行失败，请检查向量数据库路径、集合和服务端错误日志"

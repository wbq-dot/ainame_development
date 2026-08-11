import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from ollama import ResponseError

import rag_worker
from core import rag_service


class FakeVectorStore:
    def __init__(self, failures: int = 0):
        self.failures = failures
        self.calls = 0
        self.received_ids = []

    def add_documents(self, documents, ids):
        self.calls += 1
        self.received_ids.append(ids)
        if self.calls <= self.failures:
            raise ResponseError("temporary failure", 502)


class FakeSearchStore:
    def __init__(self, result_batches=None, error=None, has_categorized=True):
        self.result_batches = list(result_batches or [])
        self.error = error
        self.has_categorized = has_categorized
        self.calls = []

    def get(self, **kwargs):
        if "where" not in kwargs:
            return {"ids": ["existing-doc"], "metadatas": [{}]}
        return {"ids": ["categorized-doc"] if self.has_categorized else []}

    def similarity_search_with_relevance_scores(self, query, **kwargs):
        self.calls.append({"query": query, **kwargs})
        if self.error:
            raise self.error
        return self.result_batches.pop(0)


def fake_document(content="知识库内容"):
    return SimpleNamespace(page_content=content, metadata={})


class FakeOllamaClient:
    def __init__(self):
        self.calls = []

    def embed(self, **kwargs):
        self.calls.append(kwargs)
        values = kwargs["input"]
        if isinstance(values, str):
            values = [values]
        return {"embeddings": [[float(index)] for index, _ in enumerate(values)]}


class FakeMessage:
    def __init__(self, body: dict):
        self.body = json.dumps(body).encode("utf-8")
        self.processed = False
        self.acked = False
        self.rejected = False
        self.requeue = None

    async def ack(self):
        self.processed = True
        self.acked = True

    async def reject(self, requeue=False):
        self.processed = True
        self.rejected = True
        self.requeue = requeue


class RagServiceTests(unittest.TestCase):
    def test_document_ids_are_stable(self):
        first = rag_service._document_ids("example.txt", 7, 3)
        second = rag_service._document_ids("example.txt", 7, 3)
        self.assertEqual(first, second)
        self.assertEqual(3, len(set(first)))

    def test_502_is_retried(self):
        store = FakeVectorStore(failures=2)
        with (
            patch.object(rag_service, "RAG_EMBED_MAX_ATTEMPTS", 4),
            patch.object(rag_service.time, "sleep", return_value=None),
        ):
            rag_service._add_batch_with_retry(store, [object()], ["doc-id"])
        self.assertEqual(3, store.calls)

    def test_local_ollama_request_has_only_model_and_input(self):
        embeddings = rag_service.LocalOllamaEmbeddings(
            model="qwen3-embedding:4b",
            base_url="http://127.0.0.1:11434",
            timeout=180,
        )
        fake_client = FakeOllamaClient()
        embeddings.client = fake_client

        result = embeddings.embed_documents(["first", "second"])

        self.assertEqual([[0.0], [1.0]], result)
        self.assertEqual(
            {"model": "qwen3-embedding:4b", "input": ["first", "second"]},
            fake_client.calls[0],
        )

    def test_primary_search_filters_by_category_and_general(self):
        store = FakeSearchStore([[(fake_document("人名规则"), 0.72)]])
        with patch.object(rag_service, "Chroma", return_value=store):
            result = rag_service.retrieve_user_knowledge(
                query="孩子起名 属火",
                user_id=7,
                knowledge_type="human",
                fallback_query="属火",
            )

        self.assertEqual("人名规则", result)
        self.assertEqual(
            {"knowledge_type": {"$in": ["human", "general"]}},
            store.calls[0]["filter"],
        )

    def test_fallback_query_uses_lower_score_threshold(self):
        document = fake_document("忌水，偏好火属性名字")
        store = FakeSearchStore([
            [(document, 0.59)],
            [(document, 0.60)],
        ])
        with patch.object(rag_service, "Chroma", return_value=store):
            result = rag_service.retrieve_user_knowledge(
                query="孩子起名 姓氏王 属火",
                user_id=7,
                knowledge_type="human",
                fallback_query="属火 忌水",
                primary_min_score=0.65,
                fallback_min_score=0.55,
            )

        self.assertEqual("忌水，偏好火属性名字", result)
        self.assertEqual("属火 忌水", store.calls[1]["query"])

    def test_legacy_documents_without_category_are_still_retrieved(self):
        document = fake_document("旧的人名知识")
        store = FakeSearchStore(
            [[(document, 0.61)]],
            has_categorized=False,
        )
        with patch.object(rag_service, "Chroma", return_value=store):
            result = rag_service.retrieve_user_knowledge(
                query="孩子起名",
                user_id=7,
                knowledge_type="human",
                fallback_query="属火 忌水",
            )

        self.assertEqual("旧的人名知识", result)
        self.assertNotIn("filter", store.calls[0])

    def test_vector_service_failure_is_not_silently_ignored(self):
        store = FakeSearchStore(error=ConnectionError("Ollama unavailable"))
        with (
            patch.object(rag_service, "Chroma", return_value=store),
            self.assertRaises(rag_service.KnowledgeRetrievalUnavailableError),
        ):
            rag_service.retrieve_user_knowledge(
                query="孩子起名",
                user_id=7,
                knowledge_type="human",
            )

    def test_non_ollama_error_is_not_reported_as_ollama_failure(self):
        store = FakeSearchStore(error=ValueError("invalid vector filter"))
        with patch.object(rag_service, "Chroma", return_value=store):
            with self.assertRaises(
                rag_service.KnowledgeRetrievalUnavailableError
            ) as context:
                rag_service.retrieve_user_knowledge(
                    query="企业起名",
                    user_id=7,
                    knowledge_type="company",
                )

        self.assertNotIn("Ollama", str(context.exception))
        self.assertIn("向量数据库路径", str(context.exception))


class RagWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_successful_task_is_acknowledged(self):
        message = FakeMessage({
            "user_id": 7,
            "file_path": "example.txt",
            "knowledge_type": "human",
        })
        with patch.object(
            rag_worker,
            "process_and_store_file",
            return_value=2,
        ) as process, patch.object(
            rag_worker,
            "user_is_active",
            return_value=True,
        ):
            await rag_worker.process_message(message)
        self.assertTrue(message.acked)
        self.assertFalse(message.rejected)
        process.assert_called_once_with("example.txt", 7, "human")

    async def test_failed_task_is_rejected_without_requeue(self):
        message = FakeMessage({"user_id": 7, "file_path": "example.txt"})
        with patch.object(
            rag_worker,
            "process_and_store_file",
            side_effect=RuntimeError("test failure"),
        ), patch.object(
            rag_worker,
            "user_is_active",
            return_value=True,
        ):
            await rag_worker.process_message(message)
        self.assertFalse(message.acked)
        self.assertTrue(message.rejected)
        self.assertFalse(message.requeue)

    async def test_deleted_user_task_is_acknowledged_without_processing(self):
        message = FakeMessage({"user_id": 7, "file_path": "example.txt"})
        with patch.object(
            rag_worker,
            "process_and_store_file",
        ) as process, patch.object(
            rag_worker,
            "user_is_active",
            return_value=False,
        ):
            await rag_worker.process_message(message)
        self.assertTrue(message.acked)
        self.assertFalse(message.rejected)
        process.assert_not_called()


if __name__ == "__main__":
    unittest.main()

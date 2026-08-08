import unittest
from unittest.mock import AsyncMock, patch

from core import workflow
from schemas.name_schemas import FeedbackIn, NameResultSchema


class FakeStructuredLlm:
    def __init__(self):
        self.prompts = []

    async def ainvoke(self, prompt):
        self.prompts.append(prompt)
        return NameResultSchema(
            thread_id="test-thread",
            names=[
                {
                    "name": "新名字",
                    "reference": "测试出处",
                    "moral": "测试寓意",
                    "domain": "example.com",
                    "domain_status": "未查询",
                }
            ],
        )


class FakeSnapshot:
    def __init__(self, values):
        self.values = values


class FakeGraph:
    def __init__(self, values):
        self.values = values
        self.invoked = False
        self.invoked_state = None

    async def aget_state(self, config):
        return FakeSnapshot(self.values)

    async def ainvoke(self, state, config):
        self.invoked = True
        self.invoked_state = state
        return {"final_output": {"names": []}}


def complete_state(category):
    return {
        "user_id": 7,
        "category": category,
        "surname": "林",
        "gender": "不限",
        "length": "两字",
        "other": "简洁现代",
        "exclude": [],
        "final_output": {},
        "history_names": "【旧名字】寓意：上一轮内容",
        "feedback": "保留旧名字，其余更现代",
    }


class WorkflowMemoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_human_feedback_uses_previous_names(self):
        fake_llm = FakeStructuredLlm()
        with (
            patch.object(workflow, "structured_llm", fake_llm),
            patch.object(workflow, "retrieve_user_knowledge", return_value=None),
        ):
            result = await workflow.human_naming_node(complete_state("人名"))

        self.assertIn("旧名字", fake_llm.prompts[0])
        self.assertIn("保留旧名字", fake_llm.prompts[0])
        self.assertIn("新名字", result["history_names"])

    async def test_pet_feedback_uses_previous_names(self):
        fake_llm = FakeStructuredLlm()
        with (
            patch.object(workflow, "structured_llm", fake_llm),
            patch.object(workflow, "retrieve_user_knowledge", return_value=None),
        ):
            result = await workflow.pet_naming_node(complete_state("宠物名"))

        self.assertIn("旧名字", fake_llm.prompts[0])
        self.assertIn("保留旧名字", fake_llm.prompts[0])
        self.assertIn("新名字", result["history_names"])

    async def test_human_naming_uses_private_knowledge(self):
        fake_llm = FakeStructuredLlm()
        with (
            patch.object(workflow, "structured_llm", fake_llm),
            patch.object(
                workflow,
                "retrieve_user_knowledge",
                return_value="家族辈分字为清，避免使用浩字。",
            ) as retrieve,
        ):
            await workflow.human_naming_node(complete_state("人名"))

        retrieve.assert_called_once()
        self.assertEqual(7, retrieve.call_args.kwargs["user_id"])
        self.assertEqual("human", retrieve.call_args.kwargs["knowledge_type"])
        self.assertEqual(
            "孩子起名 简洁现代 姓氏林",
            retrieve.call_args.kwargs["query"],
        )
        self.assertEqual(
            "简洁现代",
            retrieve.call_args.kwargs["fallback_query"],
        )
        self.assertIn("家族辈分字为清", fake_llm.prompts[0])

    async def test_pet_naming_uses_private_knowledge(self):
        fake_llm = FakeStructuredLlm()
        with (
            patch.object(workflow, "structured_llm", fake_llm),
            patch.object(
                workflow,
                "retrieve_user_knowledge",
                return_value="这只猫出生在春天，喜欢铃铛。",
            ) as retrieve,
        ):
            await workflow.pet_naming_node(complete_state("宠物名"))

        retrieve.assert_called_once()
        self.assertEqual(7, retrieve.call_args.kwargs["user_id"])
        self.assertEqual("pet", retrieve.call_args.kwargs["knowledge_type"])
        self.assertEqual(
            "宠物起名 简洁现代",
            retrieve.call_args.kwargs["query"],
        )
        self.assertIn("出生在春天", fake_llm.prompts[0])

    async def test_company_feedback_uses_previous_names(self):
        fake_llm = FakeStructuredLlm()
        with (
            patch.object(workflow, "structured_llm", fake_llm),
            patch.object(workflow, "retrieve_user_knowledge", return_value=None),
            patch.object(workflow, "check_domain", AsyncMock(return_value="未注册")),
        ):
            result = await workflow.company_naming_node(complete_state("企业名"))

        self.assertIn("旧名字", fake_llm.prompts[0])
        self.assertIn("保留旧名字", fake_llm.prompts[0])
        self.assertIn("新名字", result["history_names"])

    async def test_company_uses_private_knowledge_when_domain_lookup_fails(self):
        fake_llm = FakeStructuredLlm()
        with (
            patch.object(workflow, "structured_llm", fake_llm),
            patch.object(
                workflow,
                "retrieve_user_knowledge",
                return_value="品牌名必须包含与星光相关的字。",
            ),
            patch.object(
                workflow,
                "check_domain",
                AsyncMock(side_effect=TimeoutError("whois timeout")),
            ),
        ):
            result = await workflow.company_naming_node(complete_state("企业名"))

        self.assertIn("品牌名必须包含与星光相关的字", fake_llm.prompts[0])
        self.assertEqual(
            "⚠️ 域名查询暂时不可用",
            result["final_output"]["names"][0]["domain_status"],
        )

    async def test_feedback_rejects_another_users_thread(self):
        fake_graph = FakeGraph({"user_id": 8, "category": "人名"})
        feedback = FeedbackIn(
            thread_id="thread-owned-by-user-8",
            category="人名",
            feedback="保留第一个名字",
        )

        with (
            patch.object(workflow, "naming_graph", fake_graph),
            self.assertRaises(workflow.WorkflowSessionAccessError),
        ):
            await workflow.feedback_naming(feedback, user_id=7)

        self.assertFalse(fake_graph.invoked)

    async def test_old_session_recovers_history_from_final_output(self):
        fake_graph = FakeGraph(
            {
                "user_id": 7,
                "category": "宠物名",
                "final_output": {
                    "names": [{"name": "团团", "moral": "圆满可爱"}]
                },
            }
        )
        feedback = FeedbackIn(
            thread_id="old-pet-thread",
            category="宠物名",
            feedback="保留团团",
        )

        with patch.object(workflow, "naming_graph", fake_graph):
            await workflow.feedback_naming(feedback, user_id=7)

        self.assertIn("团团", fake_graph.invoked_state["history_names"])


if __name__ == "__main__":
    unittest.main()

import unittest
from types import SimpleNamespace

from pydantic import ValidationError

from modules.community.community_models import (
    CommunityCandidate,
    CommunityComment,
    CommunityReport,
    CommunityTopic,
    CommunityVote,
)
from modules.community.community_repo import CommunityRepository
from modules.community.community_schemas import ModerationIn, ReportCreateIn, TopicCreateIn


class CommunityModuleTests(unittest.TestCase):
    def test_topic_requires_at_least_two_candidates(self):
        with self.assertRaises(ValidationError):
            TopicCreateIn(
                title="新品牌名字投票",
                description="请为我们的新品牌选择一个更容易记住的名字",
                candidates=[{"name": "知禾", "meaning": "表达生长感"}],
            )

    def test_topic_rejects_duplicate_candidate_names(self):
        with self.assertRaisesRegex(ValidationError, "候选名不能重复"):
            TopicCreateIn(
                title="新品牌名字投票",
                description="请为我们的新品牌选择一个更容易记住的名字",
                candidates=[
                    {"name": "知禾", "meaning": "表达生长感"},
                    {"name": "知禾", "meaning": "表达亲和感"},
                ],
            )

    def test_valid_topic_and_report_payloads(self):
        topic = TopicCreateIn(
            title="新品牌名字投票",
            description="请为我们的新品牌选择一个更容易记住的名字",
            candidates=[
                {"name": "知禾", "meaning": "自然生长，温和亲切"},
                {"name": "云章", "meaning": "兼具文化感和传播力"},
            ],
        )
        report = ReportCreateIn(target_type="comment", target_id=3, reason="spam")
        self.assertEqual(2, len(topic.candidates))
        self.assertEqual("comment", report.target_type)

    def test_vote_has_one_choice_per_user_and_topic(self):
        constraints = {constraint.name for constraint in CommunityVote.__table__.constraints}
        self.assertIn("uq_community_vote_topic_user", constraints)

    def test_all_five_community_tables_are_registered(self):
        tables = {
            CommunityTopic.__tablename__,
            CommunityCandidate.__tablename__,
            CommunityVote.__tablename__,
            CommunityComment.__tablename__,
            CommunityReport.__tablename__,
        }
        self.assertEqual(5, len(tables))

    def test_moderation_only_accepts_hide_or_restore(self):
        self.assertEqual(
            "hide",
            ModerationIn(target_type="comment", target_id=8, action="hide").action,
        )
        with self.assertRaises(ValidationError):
            ModerationIn(target_type="comment", target_id=8, action="delete")


class FakeModerationSession:
    def __init__(self, target):
        self.target = target
        self.committed = False

    async def get(self, model, target_id):
        return self.target

    async def commit(self):
        self.committed = True


class CommunityModerationTests(unittest.IsolatedAsyncioTestCase):
    async def test_hiding_topic_keeps_data_and_clears_featured(self):
        topic = SimpleNamespace(status="open", is_featured=True, featured_at=object())
        session = FakeModerationSession(topic)
        result = await CommunityRepository(session).moderate_content("topic", 3, "hide")
        self.assertEqual("hidden", topic.status)
        self.assertFalse(topic.is_featured)
        self.assertIsNone(topic.featured_at)
        self.assertTrue(session.committed)
        self.assertEqual("投票主题已隐藏", result["message"])

    async def test_restoring_comment_makes_it_visible(self):
        comment = SimpleNamespace(status="hidden")
        session = FakeModerationSession(comment)
        await CommunityRepository(session).moderate_content("comment", 9, "restore")
        self.assertEqual("visible", comment.status)


if __name__ == "__main__":
    unittest.main()

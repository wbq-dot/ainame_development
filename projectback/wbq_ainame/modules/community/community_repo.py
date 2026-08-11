from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.User import User
from modules.community.community_models import (
    CommunityCandidate,
    CommunityComment,
    CommunityReport,
    CommunityTopic,
    CommunityVote,
)
from modules.community.community_schemas import (
    CandidateCreateIn,
    CommentCreateIn,
    ReportCreateIn,
    TopicCreateIn,
)


class CommunityDomainError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class CommunityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_topic(self, user_id: int, data: TopicCreateIn):
        topic = CommunityTopic(user_id=user_id, title=data.title, description=data.description)
        try:
            async with self.session.begin():
                self.session.add(topic)
                await self.session.flush()
                self.session.add_all(
                    CommunityCandidate(
                        topic_id=topic.id,
                        user_id=user_id,
                        name=item.name,
                        meaning=item.meaning,
                    )
                    for item in data.candidates
                )
        except IntegrityError as exc:
            raise CommunityDomainError("候选名不能重复", 409) from exc
        return await self.get_topic(topic.id, user_id)

    async def list_topics(
        self, sort: str, page: int, page_size: int, user_id: int | None = None
    ):
        conditions = [CommunityTopic.status != "hidden"]
        if sort == "featured":
            conditions.append(CommunityTopic.is_featured.is_(True))

        vote_count = (
            select(func.count(CommunityVote.id))
            .join(
                CommunityCandidate,
                CommunityCandidate.id == CommunityVote.candidate_id,
            )
            .where(CommunityVote.topic_id == CommunityTopic.id)
            .where(CommunityCandidate.status == "visible")
            .correlate(CommunityTopic)
            .scalar_subquery()
        )
        comment_count = (
            select(func.count(CommunityComment.id))
            .where(
                CommunityComment.topic_id == CommunityTopic.id,
                CommunityComment.status == "visible",
            )
            .correlate(CommunityTopic)
            .scalar_subquery()
        )
        total = await self.session.scalar(select(func.count(CommunityTopic.id)).where(*conditions))
        statement = (
            select(
                CommunityTopic,
                User.username.label("author_name"),
                vote_count.label("vote_count"),
                comment_count.label("comment_count"),
            )
            .join(User, User.id == CommunityTopic.user_id)
            .where(*conditions)
        )
        if sort == "popular":
            statement = statement.order_by(vote_count.desc(), CommunityTopic.created_at.desc())
        elif sort == "featured":
            statement = statement.order_by(
                CommunityTopic.featured_at.desc(), CommunityTopic.created_at.desc()
            )
        else:
            statement = statement.order_by(CommunityTopic.created_at.desc())
        rows = (
            await self.session.execute(statement.offset((page - 1) * page_size).limit(page_size))
        ).all()
        return await self._serialize_topics(rows, user_id), int(total or 0)

    async def get_topic(self, topic_id: int, user_id: int | None = None):
        vote_count = (
            select(func.count(CommunityVote.id))
            .join(
                CommunityCandidate,
                CommunityCandidate.id == CommunityVote.candidate_id,
            )
            .where(CommunityVote.topic_id == CommunityTopic.id)
            .where(CommunityCandidate.status == "visible")
            .correlate(CommunityTopic)
            .scalar_subquery()
        )
        comment_count = (
            select(func.count(CommunityComment.id))
            .where(
                CommunityComment.topic_id == CommunityTopic.id,
                CommunityComment.status == "visible",
            )
            .correlate(CommunityTopic)
            .scalar_subquery()
        )
        row = (
            await self.session.execute(
                select(
                    CommunityTopic,
                    User.username.label("author_name"),
                    vote_count.label("vote_count"),
                    comment_count.label("comment_count"),
                )
                .join(User, User.id == CommunityTopic.user_id)
                .where(CommunityTopic.id == topic_id, CommunityTopic.status != "hidden")
            )
        ).first()
        if not row:
            raise CommunityDomainError("投票主题不存在", 404)
        return (await self._serialize_topics([row], user_id))[0]

    async def _serialize_topics(self, rows, user_id: int | None):
        if not rows:
            return []
        topic_ids = [row[0].id for row in rows]
        candidate_vote_count = (
            select(func.count(CommunityVote.id))
            .where(CommunityVote.candidate_id == CommunityCandidate.id)
            .correlate(CommunityCandidate)
            .scalar_subquery()
        )
        candidate_rows = (
            await self.session.execute(
                select(
                    CommunityCandidate,
                    User.username.label("author_name"),
                    candidate_vote_count.label("vote_count"),
                )
                .join(User, User.id == CommunityCandidate.user_id)
                .where(
                    CommunityCandidate.topic_id.in_(topic_ids),
                    CommunityCandidate.status == "visible",
                )
                .order_by(candidate_vote_count.desc(), CommunityCandidate.created_at.asc())
            )
        ).all()
        voted_ids: set[int] = set()
        if user_id:
            voted_ids = set(
                (
                    await self.session.scalars(
                        select(CommunityVote.candidate_id).where(
                            CommunityVote.user_id == user_id,
                            CommunityVote.topic_id.in_(topic_ids),
                        )
                    )
                ).all()
            )
        candidates: dict[int, list[dict]] = {topic_id: [] for topic_id in topic_ids}
        for candidate, author_name, vote_total in candidate_rows:
            candidates[candidate.topic_id].append(
                {
                    "id": candidate.id,
                    "name": candidate.name,
                    "meaning": candidate.meaning,
                    "author_name": author_name,
                    "vote_count": int(vote_total or 0),
                    "voted": candidate.id in voted_ids,
                    "created_at": candidate.created_at,
                }
            )
        return [
            {
                "id": topic.id,
                "title": topic.title,
                "description": topic.description,
                "author_name": author_name,
                "status": topic.status,
                "is_featured": topic.is_featured,
                "vote_count": int(vote_total or 0),
                "comment_count": int(comment_total or 0),
                "candidates": candidates[topic.id],
                "created_at": topic.created_at,
            }
            for topic, author_name, vote_total, comment_total in rows
        ]

    async def add_candidate(self, topic_id: int, user_id: int, data: CandidateCreateIn):
        topic = await self.session.get(CommunityTopic, topic_id)
        if not topic or topic.status == "hidden":
            raise CommunityDomainError("投票主题不存在", 404)
        if topic.status != "open":
            raise CommunityDomainError("该投票已结束", 409)
        candidate = CommunityCandidate(
            topic_id=topic_id, user_id=user_id, name=data.name, meaning=data.meaning
        )
        try:
            self.session.add(candidate)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise CommunityDomainError("这个候选名已经存在", 409) from exc
        return await self.get_topic(topic_id, user_id)

    async def vote(self, topic_id: int, candidate_id: int, user_id: int):
        candidate = await self.session.scalar(
            select(CommunityCandidate)
            .join(CommunityTopic, CommunityTopic.id == CommunityCandidate.topic_id)
            .where(
                CommunityCandidate.id == candidate_id,
                CommunityCandidate.topic_id == topic_id,
                CommunityCandidate.status == "visible",
                CommunityTopic.status == "open",
            )
        )
        if not candidate:
            raise CommunityDomainError("候选名不存在或投票已结束", 404)
        existing = await self.session.scalar(
            select(CommunityVote).where(
                CommunityVote.topic_id == topic_id, CommunityVote.user_id == user_id
            )
        )
        if existing:
            existing.candidate_id = candidate_id
            existing.created_at = datetime.now()
        else:
            self.session.add(
                CommunityVote(
                    topic_id=topic_id, candidate_id=candidate_id, user_id=user_id
                )
            )
        await self.session.commit()
        return await self.get_topic(topic_id, user_id)

    async def list_comments(self, topic_id: int):
        exists = await self.session.scalar(
            select(CommunityTopic.id).where(
                CommunityTopic.id == topic_id, CommunityTopic.status != "hidden"
            )
        )
        if not exists:
            raise CommunityDomainError("投票主题不存在", 404)
        rows = (
            await self.session.execute(
                select(CommunityComment, User.username)
                .join(User, User.id == CommunityComment.user_id)
                .where(
                    CommunityComment.topic_id == topic_id,
                    CommunityComment.status == "visible",
                )
                .order_by(CommunityComment.created_at.asc())
            )
        ).all()
        return [
            {
                "id": comment.id,
                "content": comment.content,
                "author_name": username,
                "created_at": comment.created_at,
            }
            for comment, username in rows
        ]

    async def add_comment(self, topic_id: int, user_id: int, data: CommentCreateIn):
        exists = await self.session.scalar(
            select(CommunityTopic.id).where(
                CommunityTopic.id == topic_id, CommunityTopic.status != "hidden"
            )
        )
        if not exists:
            raise CommunityDomainError("投票主题不存在", 404)
        comment = CommunityComment(topic_id=topic_id, user_id=user_id, content=data.content)
        self.session.add(comment)
        await self.session.commit()
        return {
            "id": comment.id,
            "content": comment.content,
            "author_name": (
                await self.session.scalar(select(User.username).where(User.id == user_id))
            ),
            "created_at": comment.created_at,
        }

    async def create_report(self, user_id: int, data: ReportCreateIn):
        models = {
            "topic": CommunityTopic,
            "candidate": CommunityCandidate,
            "comment": CommunityComment,
        }
        if not await self.session.get(models[data.target_type], data.target_id):
            raise CommunityDomainError("举报内容不存在", 404)
        report = CommunityReport(
            reporter_user_id=user_id,
            target_type=data.target_type,
            target_id=data.target_id,
            reason=data.reason,
            detail=data.detail,
        )
        try:
            self.session.add(report)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise CommunityDomainError("你已经举报过该内容", 409) from exc
        return {"message": "举报已提交，我们会尽快处理", "report_id": report.id}

    async def set_featured(self, topic_id: int, is_featured: bool):
        topic = await self.session.get(CommunityTopic, topic_id)
        if not topic or topic.status == "hidden":
            raise CommunityDomainError("投票主题不存在", 404)
        topic.is_featured = is_featured
        topic.featured_at = datetime.now() if is_featured else None
        await self.session.commit()
        return {"message": "已加入社区精选" if is_featured else "已取消社区精选"}

    async def list_admin_topics(self, status: str, page: int, page_size: int):
        conditions = [] if status == "all" else [CommunityTopic.status == status]
        vote_count = (
            select(func.count(CommunityVote.id))
            .where(CommunityVote.topic_id == CommunityTopic.id)
            .correlate(CommunityTopic)
            .scalar_subquery()
        )
        report_count = (
            select(func.count(CommunityReport.id))
            .where(
                CommunityReport.target_type == "topic",
                CommunityReport.target_id == CommunityTopic.id,
            )
            .correlate(CommunityTopic)
            .scalar_subquery()
        )
        total = await self.session.scalar(
            select(func.count(CommunityTopic.id)).where(*conditions)
        )
        topic_rows = (
            await self.session.execute(
                select(
                    CommunityTopic,
                    User.username.label("author_name"),
                    vote_count.label("vote_count"),
                    report_count.label("report_count"),
                )
                .join(User, User.id == CommunityTopic.user_id)
                .where(*conditions)
                .order_by(CommunityTopic.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        if not topic_rows:
            return [], int(total or 0)

        topic_ids = [row[0].id for row in topic_rows]
        candidate_vote_count = (
            select(func.count(CommunityVote.id))
            .where(CommunityVote.candidate_id == CommunityCandidate.id)
            .correlate(CommunityCandidate)
            .scalar_subquery()
        )
        candidate_rows = (
            await self.session.execute(
                select(
                    CommunityCandidate,
                    User.username.label("author_name"),
                    candidate_vote_count.label("vote_count"),
                )
                .join(User, User.id == CommunityCandidate.user_id)
                .where(CommunityCandidate.topic_id.in_(topic_ids))
                .order_by(CommunityCandidate.created_at.asc())
            )
        ).all()
        comment_rows = (
            await self.session.execute(
                select(CommunityComment, User.username.label("author_name"))
                .join(User, User.id == CommunityComment.user_id)
                .where(CommunityComment.topic_id.in_(topic_ids))
                .order_by(CommunityComment.created_at.asc())
            )
        ).all()
        candidates: dict[int, list[dict]] = {topic_id: [] for topic_id in topic_ids}
        comments: dict[int, list[dict]] = {topic_id: [] for topic_id in topic_ids}
        for candidate, author_name, votes in candidate_rows:
            candidates[candidate.topic_id].append(
                {
                    "id": candidate.id,
                    "name": candidate.name,
                    "meaning": candidate.meaning,
                    "author_name": author_name,
                    "status": candidate.status,
                    "vote_count": int(votes or 0),
                    "created_at": candidate.created_at,
                }
            )
        for comment, author_name in comment_rows:
            comments[comment.topic_id].append(
                {
                    "id": comment.id,
                    "content": comment.content,
                    "author_name": author_name,
                    "status": comment.status,
                    "created_at": comment.created_at,
                }
            )
        return [
            {
                "id": topic.id,
                "title": topic.title,
                "description": topic.description,
                "author_name": author_name,
                "status": topic.status,
                "is_featured": topic.is_featured,
                "vote_count": int(votes or 0),
                "report_count": int(reports or 0),
                "candidates": candidates[topic.id],
                "comments": comments[topic.id],
                "created_at": topic.created_at,
            }
            for topic, author_name, votes, reports in topic_rows
        ], int(total or 0)

    async def moderate_content(self, target_type: str, target_id: int, action: str):
        model = {
            "topic": CommunityTopic,
            "candidate": CommunityCandidate,
            "comment": CommunityComment,
        }[target_type]
        target = await self.session.get(model, target_id)
        if not target:
            raise CommunityDomainError("管理目标不存在", 404)
        target.status = "hidden" if action == "hide" else (
            "open" if target_type == "topic" else "visible"
        )
        if target_type == "topic" and action == "hide":
            target.is_featured = False
            target.featured_at = None
        await self.session.commit()
        target_name = {"topic": "投票主题", "candidate": "候选名", "comment": "评论"}[
            target_type
        ]
        action_name = "隐藏" if action == "hide" else "恢复"
        return {"message": f"{target_name}已{action_name}"}

    async def list_reports(self, status: str):
        rows = (
            await self.session.execute(
                select(CommunityReport, User.username)
                .join(User, User.id == CommunityReport.reporter_user_id)
                .where(CommunityReport.status == status)
                .order_by(CommunityReport.created_at.desc())
            )
        ).all()
        target_ids = {
            target_type: [
                report.target_id
                for report, _ in rows
                if report.target_type == target_type
            ]
            for target_type in ("topic", "candidate", "comment")
        }
        target_maps: dict[str, dict[int, object]] = {}
        for target_type, model in (
            ("topic", CommunityTopic),
            ("candidate", CommunityCandidate),
            ("comment", CommunityComment),
        ):
            ids = target_ids[target_type]
            targets = (
                (await self.session.scalars(select(model).where(model.id.in_(ids)))).all()
                if ids
                else []
            )
            target_maps[target_type] = {target.id: target for target in targets}

        def target_info(report):
            target = target_maps[report.target_type].get(report.target_id)
            if not target:
                return "内容已不存在", "missing"
            if report.target_type == "topic":
                return target.title, target.status
            if report.target_type == "candidate":
                return f"候选名：{target.name}", target.status
            return target.content[:100], target.status

        result = []
        for report, username in rows:
            summary, target_status = target_info(report)
            result.append(
                {
                    "id": report.id,
                    "target_type": report.target_type,
                    "target_id": report.target_id,
                    "reason": report.reason,
                    "detail": report.detail,
                    "status": report.status,
                    "resolution": report.resolution,
                    "reporter_name": username,
                    "target_summary": summary,
                    "target_status": target_status,
                    "created_at": report.created_at,
                }
            )
        return result

    async def resolve_report(
        self, report_id: int, admin_user_id: int, action: str, resolution: str | None
    ):
        report = await self.session.get(CommunityReport, report_id)
        if not report:
            raise CommunityDomainError("举报记录不存在", 404)
        if report.status != "pending":
            raise CommunityDomainError("该举报已经处理", 409)
        if action == "hide":
            model = {
                "topic": CommunityTopic,
                "comment": CommunityComment,
            }.get(report.target_type)
            if model:
                target = await self.session.get(model, report.target_id)
                if target:
                    target.status = "hidden"
                    if report.target_type == "topic":
                        target.is_featured = False
                        target.featured_at = None
            else:
                candidate = await self.session.get(CommunityCandidate, report.target_id)
                if candidate:
                    candidate.status = "hidden"
        report.status = "resolved"
        report.resolution = resolution or ("已隐藏相关内容" if action == "hide" else "无需处理")
        report.resolved_by = admin_user_id
        report.resolved_at = datetime.now()
        await self.session.commit()
        return {"message": "举报已处理"}

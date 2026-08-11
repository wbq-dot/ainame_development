from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.authtools import AuthHandler
from dependencies import get_session
from modules.community.community_repo import CommunityDomainError, CommunityRepository
from modules.community.community_schemas import (
    AdminTopicListOut,
    CandidateCreateIn,
    CommentCreateIn,
    CommentOut,
    FeaturedIn,
    ModerationIn,
    ReportCreateIn,
    ReportOut,
    ReportResolveIn,
    TopicCreateIn,
    TopicListOut,
    TopicOut,
    VoteIn,
)


router = APIRouter(prefix="/community", tags=["community"])
admin_router = APIRouter(prefix="/admin/community", tags=["admin-community"])
auth_handler = AuthHandler()
optional_security = HTTPBearer(auto_error=False)


async def optional_user_id(
    credentials: HTTPAuthorizationCredentials | None = Security(optional_security),
) -> int | None:
    if not credentials:
        return None
    user_id = auth_handler.decode_access_token(credentials.credentials)
    user = await auth_handler._get_available_user(user_id)
    return user.id


def handle_domain_error(exc: CommunityDomainError):
    raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/topics", response_model=TopicListOut)
async def list_topics(
    sort: Literal["latest", "popular", "featured"] = "latest",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
    user_id: int | None = Depends(optional_user_id),
    session: AsyncSession = Depends(get_session),
):
    items, total = await CommunityRepository(session).list_topics(
        sort, page, page_size, user_id
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/topics", response_model=TopicOut, status_code=201)
async def create_topic(
    data: TopicCreateIn,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await CommunityRepository(session).create_topic(user_id, data)
    except CommunityDomainError as exc:
        handle_domain_error(exc)


@router.get("/topics/{topic_id}", response_model=TopicOut)
async def get_topic(
    topic_id: int,
    user_id: int | None = Depends(optional_user_id),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await CommunityRepository(session).get_topic(topic_id, user_id)
    except CommunityDomainError as exc:
        handle_domain_error(exc)


@router.post("/topics/{topic_id}/candidates", response_model=TopicOut, status_code=201)
async def add_candidate(
    topic_id: int,
    data: CandidateCreateIn,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await CommunityRepository(session).add_candidate(topic_id, user_id, data)
    except CommunityDomainError as exc:
        handle_domain_error(exc)


@router.put("/topics/{topic_id}/vote", response_model=TopicOut)
async def vote(
    topic_id: int,
    data: VoteIn,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await CommunityRepository(session).vote(topic_id, data.candidate_id, user_id)
    except CommunityDomainError as exc:
        handle_domain_error(exc)


@router.get("/topics/{topic_id}/comments", response_model=list[CommentOut])
async def list_comments(topic_id: int, session: AsyncSession = Depends(get_session)):
    try:
        return await CommunityRepository(session).list_comments(topic_id)
    except CommunityDomainError as exc:
        handle_domain_error(exc)


@router.post("/topics/{topic_id}/comments", response_model=CommentOut, status_code=201)
async def add_comment(
    topic_id: int,
    data: CommentCreateIn,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await CommunityRepository(session).add_comment(topic_id, user_id, data)
    except CommunityDomainError as exc:
        handle_domain_error(exc)


@router.post("/reports", status_code=201)
async def create_report(
    data: ReportCreateIn,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await CommunityRepository(session).create_report(user_id, data)
    except CommunityDomainError as exc:
        handle_domain_error(exc)


@admin_router.put("/topics/{topic_id}/featured")
async def set_featured(
    topic_id: int,
    data: FeaturedIn,
    _: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await CommunityRepository(session).set_featured(topic_id, data.is_featured)
    except CommunityDomainError as exc:
        handle_domain_error(exc)


@admin_router.get("/topics", response_model=AdminTopicListOut)
async def list_admin_topics(
    status: Literal["all", "open", "closed", "hidden"] = "all",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
    _: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    items, total = await CommunityRepository(session).list_admin_topics(
        status, page, page_size
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@admin_router.post("/moderate")
async def moderate_content(
    data: ModerationIn,
    _: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await CommunityRepository(session).moderate_content(
            data.target_type, data.target_id, data.action
        )
    except CommunityDomainError as exc:
        handle_domain_error(exc)


@admin_router.get("/reports", response_model=list[ReportOut])
async def list_reports(
    status: Literal["pending", "resolved"] = "pending",
    _: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    return await CommunityRepository(session).list_reports(status)


@admin_router.post("/reports/{report_id}/resolve")
async def resolve_report(
    report_id: int,
    data: ReportResolveIn,
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await CommunityRepository(session).resolve_report(
            report_id, admin_user_id, data.action, data.resolution
        )
    except CommunityDomainError as exc:
        handle_domain_error(exc)

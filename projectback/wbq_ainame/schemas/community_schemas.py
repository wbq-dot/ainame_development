from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CommunitySchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class CandidateCreateIn(CommunitySchema):
    name: str = Field(min_length=1, max_length=50)
    meaning: str = Field(min_length=2, max_length=500)


class TopicCreateIn(CommunitySchema):
    title: str = Field(min_length=4, max_length=80)
    description: str = Field(min_length=10, max_length=2000)
    candidates: list[CandidateCreateIn] = Field(min_length=2, max_length=10)

    @model_validator(mode="after")
    def candidate_names_must_be_unique(self):
        normalized = [item.name.casefold() for item in self.candidates]
        if len(normalized) != len(set(normalized)):
            raise ValueError("候选名不能重复")
        return self


class VoteIn(BaseModel):
    candidate_id: int = Field(gt=0)


class CommentCreateIn(CommunitySchema):
    content: str = Field(min_length=1, max_length=500)


class ReportCreateIn(CommunitySchema):
    target_type: Literal["topic", "candidate", "comment"]
    target_id: int = Field(gt=0)
    reason: Literal["spam", "abuse", "privacy", "illegal", "other"]
    detail: str | None = Field(default=None, max_length=500)


class FeaturedIn(BaseModel):
    is_featured: bool


class ReportResolveIn(CommunitySchema):
    action: Literal["dismiss", "hide"]
    resolution: str | None = Field(default=None, max_length=500)


class ModerationIn(BaseModel):
    target_type: Literal["topic", "candidate", "comment"]
    target_id: int = Field(gt=0)
    action: Literal["hide", "restore"]


class CandidateOut(BaseModel):
    id: int
    name: str
    meaning: str
    author_name: str
    vote_count: int
    voted: bool = False
    created_at: datetime


class TopicOut(BaseModel):
    id: int
    title: str
    description: str
    author_name: str
    status: str
    is_featured: bool
    vote_count: int
    comment_count: int
    candidates: list[CandidateOut]
    created_at: datetime


class TopicListOut(BaseModel):
    items: list[TopicOut]
    total: int
    page: int
    page_size: int


class CommentOut(BaseModel):
    id: int
    content: str
    author_name: str
    created_at: datetime


class ReportOut(BaseModel):
    id: int
    target_type: str
    target_id: int
    reason: str
    detail: str | None
    status: str
    resolution: str | None
    reporter_name: str
    target_summary: str
    target_status: str
    created_at: datetime


class AdminCandidateOut(BaseModel):
    id: int
    name: str
    meaning: str
    author_name: str
    status: str
    vote_count: int
    created_at: datetime


class AdminCommentOut(BaseModel):
    id: int
    content: str
    author_name: str
    status: str
    created_at: datetime


class AdminTopicOut(BaseModel):
    id: int
    title: str
    description: str
    author_name: str
    status: str
    is_featured: bool
    vote_count: int
    report_count: int
    candidates: list[AdminCandidateOut]
    comments: list[AdminCommentOut]
    created_at: datetime


class AdminTopicListOut(BaseModel):
    items: list[AdminTopicOut]
    total: int
    page: int
    page_size: int

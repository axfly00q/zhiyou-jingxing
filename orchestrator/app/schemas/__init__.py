"""Pydantic schemas（请求/响应模型）。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class QuizItem(BaseModel):
    """KG 内置知识问题。"""
    q: str
    options: List[str]
    answer: int
    fact: str = ""


class TouristPreference(BaseModel):
    """游客偏好——5 维偏好分数（0~1），来源于偏好引导页滑块。"""
    history: float = Field(0.5, ge=0, le=1, description="历史人文偏好")
    nature: float = Field(0.5, ge=0, le=1, description="自然风光偏好")
    architecture: float = Field(0.5, ge=0, le=1, description="建筑艺术偏好")
    family: float = Field(0.5, ge=0, le=1, description="亲子友好")
    photo: float = Field(0.5, ge=0, le=1, description="摄影打卡")
    duration_min: int = Field(120, ge=30, le=480, description="期望游览时长（分钟）")
    start_spot: Optional[str] = Field(None, description="起始景点 code，留空则自动选大门")
    wheelchair: bool = Field(False, description="需要无障碍/轮椅通道")
    children: bool = Field(False, description="携带儿童")
    rush: bool = Field(False, description="时间紧张，跳过次要景点")


class RouteSpot(BaseModel):
    code: str
    name: str
    themes: List[str]
    highlight: str
    suggested_minutes: int
    tags: List[str] = []
    map_x: Optional[float] = None
    map_y: Optional[float] = None
    quiz: List[QuizItem] = []


class RouteResponse(BaseModel):
    park: str
    total_minutes: int
    score: float
    spots: List[RouteSpot]
    narrative: str = Field(..., description="一段贴合偏好的开场白，由数字人播报")


class RouteContext(BaseModel):
    """前端每次发消息时携带的精简路线状态，用于注入 Dify 上下文。"""
    current_spot_code: Optional[str] = None
    current_spot_name: Optional[str] = None
    visited_names: List[str] = Field(default_factory=list, description="已游览景点名称列表")
    remaining_names: List[str] = Field(default_factory=list, description="剩余路线景点名称列表")
    total_minutes: int = 0
    elapsed_minutes: int = 0
    preferences_summary: Optional[str] = None


class CheckinRequest(BaseModel):
    """用户到达景点打卡请求。"""
    session_id: str
    spot_code: str
    park_code: str
    avatar_code: Optional[str] = None
    route_context: Optional[RouteContext] = None


class CheckinResponse(BaseModel):
    """打卡响应：景点介绍 + TTS + VRM 动作 + 下一站提示。"""
    narrative: str
    audio_url: Optional[str] = None
    emotion: str = "joy"
    motion: str = "wave"
    next_spot_name: Optional[str] = None
    next_walk_minutes: Optional[int] = None
    checked_in_spot_code: str
    badge: Optional["BadgeOut"] = None


class ChatTextRequest(BaseModel):
    session_id: str
    message: str
    avatar_code: Optional[str] = None
    park_code: Optional[str] = None
    route_context: Optional[RouteContext] = None


class ChatTextResponse(BaseModel):
    answer: str
    citations: List[dict] = []
    audio_url: Optional[str] = None
    intent: Optional[str] = None
    emotion: str = Field("neutral",
                         description="情绪标签：neutral/joy/sorrow/angry/surprised")
    motion: str = Field("idle",
                        description="动作语义：idle/wave/explain/think")
    latency_ms: int = 0
    new_route: Optional["RouteResponse"] = Field(None, description="重规划后的新路线，非None时前端更新路线状态")


class ReviewCreate(BaseModel):
    session_id: str
    park_code: Optional[str] = None
    rating: int = Field(..., ge=1, le=5)
    tags: List[str] = []
    comment: Optional[str] = None


class ReviewOut(BaseModel):
    id: int
    session_id: str
    park_code: Optional[str] = None
    rating: int
    tags: List[str] = []
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BadgeOut(BaseModel):
    id: int
    session_id: str
    park_code: Optional[str] = None
    badge_type: str
    badge_name: str
    unlocked_at: datetime

    class Config:
        from_attributes = True


class SummaryRequest(BaseModel):
    session_id: str
    park_code: Optional[str] = None
    spots: List[str] = []
    elapsed_minutes: int = 0


class AvatarIn(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    preview_url: Optional[str] = None
    voice_id: str
    is_default: bool = False
    model_type: str = "vrm"
    model_url: Optional[str] = None
    default_motion: Optional[str] = "idle"


class AvatarOut(AvatarIn):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class OverviewMetrics(BaseModel):
    today_sessions: int
    today_messages: int
    week_sessions: int
    avg_latency_ms: float
    satisfaction: float = Field(..., description="正向比例 0~1")
    today_neg_rate: float = Field(0.0, description="今日负面对话比例 0~1")


class HotQuestion(BaseModel):
    question: str
    count: int


class SentimentPoint(BaseModel):
    date: str
    pos: int
    neu: int
    neg: int


class SuggestionOut(BaseModel):
    id: int
    title: str
    summary: str
    priority: str
    status: str
    evidence: Optional[List[Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SuggestionStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(open|resolved|ignored)$",
                        description="open / resolved / ignored")

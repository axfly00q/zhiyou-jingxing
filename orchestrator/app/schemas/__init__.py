"""Pydantic schemas（请求/响应模型）。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class TouristPreference(BaseModel):
    """游客偏好——5 维偏好分数（0~1），来源于偏好引导页滑块。"""
    history: float = Field(0.5, ge=0, le=1, description="历史人文偏好")
    nature: float = Field(0.5, ge=0, le=1, description="自然风光偏好")
    architecture: float = Field(0.5, ge=0, le=1, description="建筑艺术偏好")
    family: float = Field(0.5, ge=0, le=1, description="亲子友好")
    photo: float = Field(0.5, ge=0, le=1, description="摄影打卡")
    duration_min: int = Field(120, ge=30, le=480, description="期望游览时长（分钟）")
    start_spot: Optional[str] = Field(None, description="起始景点 code，留空则自动选大门")


class RouteSpot(BaseModel):
    code: str
    name: str
    themes: List[str]
    highlight: str
    suggested_minutes: int


class RouteResponse(BaseModel):
    park: str
    total_minutes: int
    score: float
    spots: List[RouteSpot]
    narrative: str = Field(..., description="一段贴合偏好的开场白，由数字人播报")


class ChatTextRequest(BaseModel):
    session_id: str
    message: str
    avatar_code: Optional[str] = None


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

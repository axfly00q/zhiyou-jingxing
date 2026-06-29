"""SQLAlchemy ORM models."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Conversation(Base):
    __tablename__ = "conversation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    tourist_profile: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    avatar_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    dify_conversation_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    park_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    preferences_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation",
                                                    cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "message"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversation.id", ondelete="CASCADE"),
                                                 index=True)
    role: Mapped[str] = mapped_column(String(16))  # user / assistant
    content: Mapped[str] = mapped_column(Text)
    intent: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    sentiment: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # pos/neu/neg
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    keywords: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    citations: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class Avatar(Base):
    """数字人形象 + 默认音色绑定。"""
    __tablename__ = "avatar"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preview_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    voice_id: Mapped[str] = mapped_column(String(64))
    is_default: Mapped[bool] = mapped_column(default=False)
    # ---- VRM 数字人 ----
    model_type: Mapped[str] = mapped_column(String(16), default="vrm")
    model_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    default_motion: Mapped[Optional[str]] = mapped_column(String(32), nullable=True,
                                                          default="idle")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Suggestion(Base):
    """LLM 生成的服务优化建议。"""
    __tablename__ = "suggestion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text)
    evidence: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # message ids
    priority: Mapped[str] = mapped_column(String(16), default="medium")
    status: Mapped[str] = mapped_column(String(16), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class Review(Base):
    """游客游后主动评分。"""
    __tablename__ = "review"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    park_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    rating: Mapped[int] = mapped_column(Integer)  # 1-5
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class Badge(Base):
    """成就徽章：全部景点打卡 / 知识问答达人。"""
    __tablename__ = "badge"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    park_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    badge_type: Mapped[str] = mapped_column(String(64))  # route_complete / quiz_master
    badge_name: Mapped[str] = mapped_column(String(128))
    unlocked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# 让 init_db 能 import 到全部模型
all_models = [Conversation, Message, Avatar, Suggestion, Review, Badge]

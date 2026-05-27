"""数据大屏 + 报告 API（公开只读）。"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import Integer, case, cast, extract, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Avatar, Conversation, Message, Review, Suggestion
from app.schemas import HotQuestion, OverviewMetrics, SentimentPoint, SuggestionOut

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview", response_model=OverviewMetrics)
async def overview(days: int = 7, db: AsyncSession = Depends(get_db)):
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    week_start = today_start - timedelta(days=days)

    today_sessions = (await db.execute(
        select(func.count(Conversation.id)).where(Conversation.started_at >= today_start)
    )).scalar_one()
    today_msgs = (await db.execute(
        select(func.count(Message.id)).where(Message.created_at >= today_start)
    )).scalar_one()
    week_sessions = (await db.execute(
        select(func.count(Conversation.id)).where(Conversation.started_at >= week_start)
    )).scalar_one()
    avg_latency = (await db.execute(
        select(func.avg(Message.latency_ms))
        .where(Message.role == "assistant", Message.created_at >= week_start)
    )).scalar() or 0.0
    # 满意度：优先从游客主动评分（Review 表）计算，无评分时回退到情感推断
    avg_rating = (await db.execute(
        select(func.avg(Review.rating))
        .where(Review.created_at >= week_start)
    )).scalar()
    if avg_rating:
        satisfaction = round(float(avg_rating) / 5.0, 3)
    else:
        pos = (await db.execute(
            select(func.count(Message.id))
            .where(Message.role == "user", Message.sentiment == "pos",
                   Message.created_at >= week_start)
        )).scalar_one()
        total = (await db.execute(
            select(func.count(Message.id))
            .where(Message.role == "user", Message.sentiment.is_not(None),
                   Message.created_at >= week_start)
        )).scalar_one()
        satisfaction = round((pos / total), 3) if total else 0.0
    today_neg = (await db.execute(
        select(func.count(Message.id))
        .where(Message.role == "user", Message.sentiment == "neg",
               Message.created_at >= today_start)
    )).scalar_one()
    today_total_sent = (await db.execute(
        select(func.count(Message.id))
        .where(Message.role == "user", Message.sentiment.is_not(None),
               Message.created_at >= today_start)
    )).scalar_one()
    today_neg_rate = (today_neg / today_total_sent) if today_total_sent else 0.0
    return OverviewMetrics(
        today_sessions=today_sessions,
        today_messages=today_msgs,
        week_sessions=week_sessions,
        avg_latency_ms=round(float(avg_latency), 1),
        satisfaction=round(satisfaction, 3),
        today_neg_rate=round(today_neg_rate, 3),
    )


@router.get("/hot-questions", response_model=List[HotQuestion])
async def hot_questions(limit: int = 10, db: AsyncSession = Depends(get_db)):
    week_start = datetime.utcnow() - timedelta(days=7)
    q = (select(Message.content, func.count(Message.id).label("c"))
         .where(Message.role == "user", Message.created_at >= week_start)
         .group_by(Message.content).order_by(func.count(Message.id).desc()).limit(limit))
    rows = (await db.execute(q)).all()
    return [HotQuestion(question=r[0][:80], count=r[1]) for r in rows]


@router.get("/sentiment-trend", response_model=List[SentimentPoint])
async def sentiment_trend(days: int = 7, db: AsyncSession = Depends(get_db)):
    start = datetime.utcnow() - timedelta(days=days)
    q = (select(func.date(Message.created_at).label("d"),
                Message.sentiment, func.count(Message.id))
         .where(Message.role == "user", Message.created_at >= start,
                Message.sentiment.is_not(None))
         .group_by("d", Message.sentiment).order_by("d"))
    rows = (await db.execute(q)).all()
    bucket: dict[str, dict[str, int]] = {}
    for d, s, c in rows:
        key = str(d)
        bucket.setdefault(key, {"pos": 0, "neu": 0, "neg": 0})
        if s in bucket[key]:
            bucket[key][s] += c
    return [SentimentPoint(date=k, **v) for k, v in sorted(bucket.items())]


@router.get("/spot-heatmap")
async def spot_heatmap(db: AsyncSession = Depends(get_db)):
    """从用户消息里粗匹配景点名 → 提及次数；供大屏热力图。

    实现：每个 park 一次聚合 SQL（``SUM(CASE WHEN content LIKE '%name%' THEN 1 ELSE 0 END)``），
    避免对每个景点单独 COUNT 造成 N+1。
    """
    from app.services.kg_repo import load_park
    counts: dict[str, dict] = {}
    for park_code in ("zhuozhengyuan", "liuyuan"):
        graph = load_park(park_code)
        if not graph:
            continue
        spots = list(graph.all())
        if not spots:
            continue
        cols = [
            func.sum(case((Message.content.like(f"%{s.name}%"), 1), else_=0)).label(s.code)
            for s in spots
        ]
        row = (await db.execute(
            select(*cols).where(Message.role == "user")
        )).one()
        for s, n in zip(spots, row):
            n = int(n or 0)
            if n:
                counts[s.code] = {"name": s.name, "park": park_code, "count": n}
    return sorted(counts.values(), key=lambda x: x["count"], reverse=True)


@router.get("/suggestions", response_model=List[SuggestionOut])
async def list_suggestions(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Suggestion).order_by(Suggestion.created_at.desc()).limit(50)
    )).scalars().all()
    return rows


@router.get("/hourly-traffic")
async def hourly_traffic(days: int = 7, db: AsyncSession = Depends(get_db)):
    """按小时（UTC+8）统计用户消息量，展示全天客流峰谷分布。"""
    start = datetime.utcnow() - timedelta(days=days)
    hour_expr = cast(
        extract("hour", Message.created_at + text("INTERVAL '8 hours'")), Integer
    ).label("hour")
    q = (
        select(hour_expr, func.count(Message.id).label("count"))
        .where(Message.role == "user", Message.created_at >= start)
        .group_by(hour_expr)
        .order_by(hour_expr)
    )
    rows = (await db.execute(q)).all()
    bucket = {h: 0 for h in range(24)}
    for hour, count in rows:
        bucket[int(hour)] = count
    return [{"hour": f"{h:02d}", "count": v} for h, v in sorted(bucket.items())]


@router.get("/question-categories")
async def question_categories(days: int = 30, db: AsyncSession = Depends(get_db)):
    """按 intent 分类统计游客提问分布。"""
    start = datetime.utcnow() - timedelta(days=days)
    INTENT_LABELS = {
        "explain": "景点讲解",
        "recommend": "景点推荐",
        "complaint": "投诉反馈",
        "navigation": "导航路线",
        "chitchat": "闲聊",
    }
    q = (
        select(Message.intent, func.count(Message.id).label("count"))
        .where(Message.role == "user", Message.intent.is_not(None),
               Message.created_at >= start)
        .group_by(Message.intent)
        .order_by(func.count(Message.id).desc())
    )
    rows = (await db.execute(q)).all()
    return [
        {"intent": r[0], "label": INTENT_LABELS.get(r[0], r[0]), "count": r[1]}
        for r in rows
    ]


@router.get("/avatar-preference")
async def avatar_preference(days: int = 30, db: AsyncSession = Depends(get_db)):
    """统计各数字人被选择的会话次数。"""
    start = datetime.utcnow() - timedelta(days=days)
    q = (
        select(
            Conversation.avatar_id,
            Avatar.name,
            func.count(Conversation.id).label("count"),
        )
        .outerjoin(Avatar, Conversation.avatar_id == Avatar.code)
        .where(Conversation.avatar_id.is_not(None), Conversation.started_at >= start)
        .group_by(Conversation.avatar_id, Avatar.name)
        .order_by(func.count(Conversation.id).desc())
        .limit(8)
    )
    rows = (await db.execute(q)).all()
    return [
        {"avatar_id": r[0], "name": r[1] or r[0], "count": r[2]}
        for r in rows
    ]

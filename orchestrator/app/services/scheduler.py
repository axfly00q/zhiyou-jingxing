"""APScheduler 定时任务：每 30 分钟聚合负面消息 → 生成建议入库。"""
from __future__ import annotations

from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.logger import logger
from app.models import Message, Suggestion
from app.services.sentiment import generate_suggestions
from app.services.tts_storage import cleanup_tts_cache

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


async def aggregate_suggestions_job() -> None:
    """近 24 小时 sentiment_score < -0.3 的消息 → LLM → Suggestion 表。"""
    since = datetime.utcnow() - timedelta(hours=24)
    async with AsyncSessionLocal() as session:
        q = (select(Message)
             .where(Message.created_at >= since,
                    Message.sentiment == "neg")
             .order_by(Message.sentiment_score.asc())
             .limit(30))
        rows = (await session.execute(q)).scalars().all()
        if not rows:
            logger.info("无负面消息，跳过建议生成")
            return
        payload = [{"id": r.id, "content": r.content,
                    "sentiment_score": r.sentiment_score or 0.0} for r in rows]
        suggestions = await generate_suggestions(payload)
        for s in suggestions:
            session.add(Suggestion(
                title=s["title"], summary=s["summary"],
                priority=s["priority"], evidence=s.get("evidence"),
            ))
        await session.commit()
        logger.info("建议引擎落库 {} 条", len(suggestions))


async def cleanup_tts_job() -> None:
    """定期清理 TTS 音频缓存（>1h）避免磁盘堆积。"""
    n = cleanup_tts_cache()
    if n:
        logger.info("清理 TTS 缓存 {} 个文件", n)


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(aggregate_suggestions_job, "interval", minutes=30,
                      id="aggregate_suggestions", replace_existing=True)
    scheduler.add_job(cleanup_tts_job, "interval", minutes=30,
                      id="cleanup_tts", replace_existing=True)
    scheduler.start()
    logger.info("APScheduler 已启动")

"""对话主链路：
- POST /api/chat/text   文本输入 → 完整回复 + TTS + VRM 表情/动作标签
- POST /api/chat/voice  音频输入（multipart wav）→ ASR → 同上
- WS   /api/chat/ws     实时双向：客户端送 JSON {type, payload}

自研编排：ASR → 情感/意图分析（异步）→ Dify RAG → TTS → dialogue_tagger（VRM 驱动表情/动作）。
"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.logger import logger
from app.models import Conversation, Message
from app.schemas import ChatTextRequest, ChatTextResponse
from app.services.asr_funasr import asr_client
from app.services.audio_transcode import to_wav_16k_mono
from app.services.dialogue_tagger import tag as tag_dialogue
from app.services.dify_client import dify_client
from app.services.sentiment import analyze
from app.services.tts_cosyvoice import tts_client
from app.services.tts_storage import save_tts_mp3
from app.core.security import verify_session_sig

router = APIRouter(prefix="/api/chat", tags=["chat"])


async def _ensure_conversation(db: AsyncSession, session_id: str,
                               avatar_code: Optional[str],
                               park_code: Optional[str] = None) -> Conversation:
    q = select(Conversation).where(Conversation.session_id == session_id)
    conv = (await db.execute(q)).scalar_one_or_none()
    if conv is None:
        conv = Conversation(session_id=session_id, avatar_id=avatar_code,
                            park_code=park_code)
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
    elif park_code and not conv.park_code:
        conv.park_code = park_code
        await db.commit()
    return conv


async def _save_user_message(db: AsyncSession, conv: Conversation, text: str) -> Message:
    """落库 + 后台分析（不阻塞主链路）。"""
    msg = Message(conversation_id=conv.id, role="user", content=text)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    asyncio.create_task(_analyze_and_update(msg.id, text))
    return msg


async def _analyze_and_update(message_id: int, text: str) -> None:
    from app.core.database import AsyncSessionLocal  # 避免循环
    result = await analyze(text)
    async with AsyncSessionLocal() as session:
        m = await session.get(Message, message_id)
        if m is None:
            return
        m.intent = result.intent
        m.sentiment = result.sentiment
        m.sentiment_score = result.sentiment_score
        m.keywords = result.keywords
        await session.commit()


async def _save_assistant_message(db: AsyncSession, conv: Conversation,
                                  text: str, citations: list,
                                  latency_ms: int) -> Message:
    msg = Message(conversation_id=conv.id, role="assistant",
                  content=text, citations=citations, latency_ms=latency_ms)
    db.add(msg)
    await db.commit()
    return msg


def _get_secondary_tts():
    """根据配置懒加载二级 TTS 客户端；无配置时返回 None。"""
    provider = settings.tts_secondary_provider.lower()
    if provider == "edge":
        from app.services.tts_edge import EdgeTTSClient
        return EdgeTTSClient()
    if provider == "fish":
        from app.services.tts_fish import FishTTSClient
        return FishTTSClient()
    return None


async def _orchestrate(session_id: str, user_text: str,
                       avatar_code: Optional[str],
                       db: AsyncSession,
                       park_code: Optional[str] = None) -> ChatTextResponse:
    t0 = time.perf_counter()
    conv = await _ensure_conversation(db, session_id, avatar_code, park_code)
    await _save_user_message(db, conv, user_text)

    # 1) Dify RAG 问答（携带已有 conversation_id 保持多轮上下文）
    dify_resp = await dify_client.chat(query=user_text, user=session_id,
                                        conversation_id=conv.dify_conversation_id)
    answer = dify_resp["answer"]
    citations = dify_resp["citations"]
    # 回写 Dify 返回的 conversation_id，供下一轮使用
    if dify_resp.get("conversation_id") and dify_resp["conversation_id"] != "stub":
        conv.dify_conversation_id = dify_resp["conversation_id"]
        await db.commit()

    # 2) TTS——三级降级链：CosyVoice2 → 二级（edge/fish）→ 前端 Web Speech API
    audio = await tts_client.synthesize(answer)
    if not audio:
        secondary = _get_secondary_tts()
        if secondary:
            audio = await secondary.synthesize(answer)
            if audio:
                logger.info("TTS Tier2 ({}) 生效", settings.tts_secondary_provider)
    audio_url: Optional[str] = None
    if audio:
        audio_url = await save_tts_mp3(audio, session_id)

    # 3) 数字人语义标签（前端 VRM 渲染时驱动表情/动作）
    tags = tag_dialogue(answer)

    latency = int((time.perf_counter() - t0) * 1000)
    await _save_assistant_message(db, conv, answer, citations, latency)
    return ChatTextResponse(answer=answer, citations=citations,
                            audio_url=audio_url, latency_ms=latency,
                            emotion=tags.emotion, motion=tags.motion)


@router.post("/text", response_model=ChatTextResponse)
async def chat_text(req: ChatTextRequest, db: AsyncSession = Depends(get_db)):
    return await _orchestrate(req.session_id, req.message, req.avatar_code, db,
                               park_code=req.park_code)


@router.post("/voice", response_model=ChatTextResponse)
async def chat_voice(
    session_id: str = Form(...),
    avatar_code: Optional[str] = Form(None),
    audio: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    audio_bytes = await audio.read()
    # 前端 MediaRecorder 默认输出 webm/opus，FunASR 仅吃 wav → 先转码
    audio_bytes = await to_wav_16k_mono(audio_bytes, src_hint=audio.filename)
    text = await asr_client.transcribe(audio_bytes)
    if not text:
        return ChatTextResponse(answer="抱歉，没听清，请再说一次。", citations=[], latency_ms=0)
    return await _orchestrate(session_id, text, avatar_code, db)


@router.post("/interrupt")
async def interrupt(session_id: str):
    """VRM 方案下打断由前端 audio.pause() 完成；服务端无状态可清。"""
    return {"ok": True}


_FALLBACK_SUGGESTIONS = [
    "这里最佳拍照点在哪？",
    "能介绍一下这里的历史吗？",
    "下一个景点是哪里？",
    "门票怎么购买？",
]


@router.get("/suggestions")
async def chat_suggestions(park: Optional[str] = None,
                           limit: int = 5,
                           db: AsyncSession = Depends(get_db)):
    """返回指定园区近 7 天 Top N 热门用户问题，无数据时兜底返回静态列表。"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    week_start = datetime.utcnow() - timedelta(days=7)
    q = (select(Message.content, func.count(Message.id).label("c"))
         .join(Conversation, Conversation.id == Message.conversation_id)
         .where(Message.role == "user", Message.created_at >= week_start))
    if park:
        q = q.where(Conversation.park_code == park)
    q = q.group_by(Message.content).order_by(func.count(Message.id).desc()).limit(limit)
    rows = (await db.execute(q)).all()
    if rows:
        return [{"question": r[0][:80], "count": r[1]} for r in rows]
    return [{"question": q, "count": 0} for q in _FALLBACK_SUGGESTIONS]


@router.get("/avatar-stream")
async def avatar_stream_url(session_id: Optional[str] = None,
                            avatar_code: Optional[str] = None,
                            db: AsyncSession = Depends(get_db)):
    """返回当前数字人的 VRM 模型与配置，前端用 three-vrm 加载。

    - 优先按 ``avatar_code`` 查；未指定则取 ``is_default=True`` 的第一条；都没有则返回占位。
    """
    from app.models import Avatar
    sid = session_id or uuid.uuid4().hex[:16]
    q = select(Avatar)
    if avatar_code:
        q = q.where(Avatar.code == avatar_code)
    else:
        q = q.where(Avatar.is_default == True)  # noqa: E712
    avatar = (await db.execute(q.limit(1))).scalar_one_or_none()

    if avatar is None:
        return {
            "session_id": sid,
            "avatar_code": avatar_code or "",
            "model_type": "vrm",
            "model_url": "",
            "default_motion": "idle",
            "voice_id": "",
            "name": "",
        }
    return {
        "session_id": sid,
        "avatar_code": avatar.code,
        "model_type": avatar.model_type or "vrm",
        "model_url": avatar.model_url or "",
        "default_motion": avatar.default_motion or "idle",
        "voice_id": avatar.voice_id,
        "name": avatar.name,
    }


@router.websocket("/ws")
async def chat_ws(ws: WebSocket):
    """轻量 WS：客户端发 {type:'text', session_id, message} 等。

    鉴权：握手需携带 ``?session_id=xxx&sig=hmac16``；sig 为 HMAC-SHA256(session_id, secret_key)[:16]。
    未携带 sig 以保持向后兼容（仅警告）；sig 错误则关闭 4001。
    """
    qp = ws.query_params
    qs_sid = qp.get("session_id")
    sig = qp.get("sig")
    if qs_sid and sig is not None and not verify_session_sig(qs_sid, sig):
        await ws.close(code=4001)
        return
    if qs_sid and sig is None:
        logger.warning("WS 未携带 sig（向后兼容放行） sid={}", qs_sid)
    await ws.accept()
    from app.core.database import AsyncSessionLocal
    try:
        while True:
            data = await ws.receive_json()
            kind = data.get("type")
            sid = data.get("session_id") or qs_sid or uuid.uuid4().hex[:16]
            avatar = data.get("avatar_code")
            if kind == "text":
                async with AsyncSessionLocal() as db:
                    resp = await _orchestrate(sid, data.get("message", ""), avatar, db)
                await ws.send_json({"type": "answer", **resp.model_dump()})
            elif kind == "interrupt":
                # VRM 方案下打断由前端处理
                await ws.send_json({"type": "interrupted"})
            elif kind == "ping":
                await ws.send_json({"type": "pong"})
            else:
                await ws.send_json({"type": "error", "msg": f"unknown type: {kind}"})
    except WebSocketDisconnect:
        logger.info("WS 断开")

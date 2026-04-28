"""对话主链路：
- POST /api/chat/text   文本输入 → 完整回复 + TTS + 数字人推流
- POST /api/chat/voice  音频输入（multipart wav）→ ASR → 同上
- WS   /api/chat/ws     实时双向：客户端送 JSON {type, payload}

自研编排：ASR → 情感/意图分析（异步）→ Dify RAG → TTS → LiveTalking。
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

from app.core.database import get_db
from app.core.logger import logger
from app.models import Conversation, Message
from app.schemas import ChatTextRequest, ChatTextResponse
from app.services.asr_funasr import asr_client
from app.services.dify_client import dify_client
from app.services.livetalking_client import livetalking_client
from app.services.sentiment import analyze
from app.services.tts_cosyvoice import tts_client

router = APIRouter(prefix="/api/chat", tags=["chat"])


async def _ensure_conversation(db: AsyncSession, session_id: str,
                               avatar_code: Optional[str]) -> Conversation:
    q = select(Conversation).where(Conversation.session_id == session_id)
    conv = (await db.execute(q)).scalar_one_or_none()
    if conv is None:
        conv = Conversation(session_id=session_id, avatar_id=avatar_code)
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
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


async def _orchestrate(session_id: str, user_text: str,
                       avatar_code: Optional[str],
                       db: AsyncSession) -> ChatTextResponse:
    t0 = time.perf_counter()
    conv = await _ensure_conversation(db, session_id, avatar_code)
    await _save_user_message(db, conv, user_text)

    # 1) Dify RAG 问答
    dify_resp = await dify_client.chat(query=user_text, user=session_id,
                                        conversation_id=None)
    answer = dify_resp["answer"]
    citations = dify_resp["citations"]

    # 2) TTS
    audio = await tts_client.synthesize(answer)
    audio_url: Optional[str] = None
    if audio:
        # 简化：把 base64 dataURL 直接给前端，避免引入对象存储
        import base64
        audio_url = "data:audio/mpeg;base64," + base64.b64encode(audio).decode("ascii")

    # 3) LiveTalking 推流（异步，不等待返回）
    asyncio.create_task(livetalking_client.speak_text(answer, session_id, avatar_code))

    latency = int((time.perf_counter() - t0) * 1000)
    await _save_assistant_message(db, conv, answer, citations, latency)
    return ChatTextResponse(answer=answer, citations=citations,
                            audio_url=audio_url, latency_ms=latency)


@router.post("/text", response_model=ChatTextResponse)
async def chat_text(req: ChatTextRequest, db: AsyncSession = Depends(get_db)):
    return await _orchestrate(req.session_id, req.message, req.avatar_code, db)


@router.post("/voice", response_model=ChatTextResponse)
async def chat_voice(
    session_id: str = Form(...),
    avatar_code: Optional[str] = Form(None),
    audio: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    audio_bytes = await audio.read()
    text = await asr_client.transcribe(audio_bytes)
    if not text:
        return ChatTextResponse(answer="抱歉，没听清，请再说一次。", citations=[], latency_ms=0)
    return await _orchestrate(session_id, text, avatar_code, db)


@router.post("/interrupt")
async def interrupt(session_id: str):
    await livetalking_client.interrupt(session_id)
    return {"ok": True}


@router.get("/avatar-stream")
async def avatar_stream_url(session_id: Optional[str] = None,
                            avatar_code: Optional[str] = None):
    """返回数字人 WebRTC 页面 URL，前端 iframe 嵌入。"""
    sid = session_id or uuid.uuid4().hex[:16]
    return {"session_id": sid,
            "url": livetalking_client.webrtc_page_url(sid, avatar_code)}


@router.websocket("/ws")
async def chat_ws(ws: WebSocket):
    """轻量 WS：客户端发 {type:'text', session_id, message} 等。"""
    await ws.accept()
    from app.core.database import AsyncSessionLocal
    try:
        while True:
            data = await ws.receive_json()
            kind = data.get("type")
            sid = data.get("session_id") or uuid.uuid4().hex[:16]
            avatar = data.get("avatar_code")
            if kind == "text":
                async with AsyncSessionLocal() as db:
                    resp = await _orchestrate(sid, data.get("message", ""), avatar, db)
                await ws.send_json({"type": "answer", **resp.model_dump()})
            elif kind == "interrupt":
                await livetalking_client.interrupt(sid)
                await ws.send_json({"type": "interrupted"})
            elif kind == "ping":
                await ws.send_json({"type": "pong"})
            else:
                await ws.send_json({"type": "error", "msg": f"unknown type: {kind}"})
    except WebSocketDisconnect:
        logger.info("WS 断开")

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
from app.schemas import (ChatTextRequest, ChatTextResponse,
                         CheckinRequest, CheckinResponse, RouteContext)
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
    asyncio.create_task(_update_pref(conv.session_id, text))
    return msg


async def _update_pref(session_id: str, text: str) -> None:
    from app.services.pref_analyzer import analyze_and_update_pref
    await analyze_and_update_pref(session_id, text)


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
    if provider == "doubao":
        from app.services.tts_doubao import DoubaoTTSClient
        return DoubaoTTSClient()
    return None


def _build_dify_inputs(rc: Optional[RouteContext]) -> dict:
    """把路线上下文转为 Dify inputs 字典；无路线时返回全部 key 的空字符串（满足 Dify 必填校验）。"""
    if not rc:
        return {
            "current_spot": "",
            "visited_spots": "",
            "remaining_spots": "",
            "elapsed_minutes": "",
            "remaining_minutes": "",
            "preferences_summary": "",
        }
    remaining_min = max(rc.total_minutes - rc.elapsed_minutes, 0)
    return {
        "current_spot": rc.current_spot_name or "",
        "visited_spots": "、".join(rc.visited_names) if rc.visited_names else "无",
        "remaining_spots": "、".join(rc.remaining_names) if rc.remaining_names else "无",
        "elapsed_minutes": str(rc.elapsed_minutes),
        "remaining_minutes": str(remaining_min),
        "preferences_summary": rc.preferences_summary or "",
    }


_CHECKIN_KW = {"到了", "在这", "到达", "走到", "来到", "已经到", "抵达", "来了"}


def _detect_checkin(text: str, remaining_names: list[str]) -> Optional[str]:
    """若用户消息包含「到了/来到/… + 景点名」则返回景点名，否则 None。"""
    if not any(kw in text for kw in _CHECKIN_KW):
        return None
    for name in remaining_names:
        if name and name in text:
            return name
    return None


_SKIP_KW = {"跳过", "不想看", "不去", "过这个", "跳", "不看", "略过"}
_ADD_KW = {"我想看", "加一个", "能去", "想去", "加上", "还想看"}


def _detect_replan_intent(text: str) -> tuple[Optional[str], str]:
    """检测路线调整意图。返回 (action, hint)，action ∈ {None, 'skip', 'add'}。"""
    for kw in _SKIP_KW:
        if kw in text:
            return "skip", ""
    for kw in _ADD_KW:
        if kw in text:
            # 提取 hint：去掉触发词，剩余部分作为景点名关键字
            hint = text
            for k in _ADD_KW:
                hint = hint.replace(k, "")
            hint = hint.strip("，。！？、 ")
            return "add", hint
    return None, ""


async def _tts_synthesize(text: str, session_id: str) -> Optional[str]:
    """TTS 三级降级，返回 audio_url 或 None。"""
    audio = await tts_client.synthesize(text)
    if not audio:
        secondary = _get_secondary_tts()
        if secondary:
            audio = await secondary.synthesize(text)
            if audio:
                logger.info("TTS Tier2 ({}) 生效", settings.tts_secondary_provider)
    if audio:
        return await save_tts_mp3(audio, session_id)
    return None


async def _orchestrate(session_id: str, user_text: str,
                       avatar_code: Optional[str],
                       db: AsyncSession,
                       park_code: Optional[str] = None,
                       route_context: Optional[RouteContext] = None) -> ChatTextResponse:
    t0 = time.perf_counter()
    conv = await _ensure_conversation(db, session_id, avatar_code, park_code)

    # B2：对话关键词打卡检测（优先于普通问答）
    if route_context and route_context.remaining_names:
        matched_name = _detect_checkin(user_text, route_context.remaining_names)
        if matched_name:
            logger.info("对话检测到打卡意图：{}", matched_name)
            # 找到 remaining 里匹配名称对应的 code（前端只传了 name，需要从 remaining 反查）
            # 这里直接拿名字匹配；checkin 接口用 spot_code，前端 UI 打卡会传正确 code
            # 对话打卡：构造 CheckinRequest 并走打卡链路
            await _save_user_message(db, conv, user_text)
            result = await _do_checkin(
                session_id=session_id,
                spot_code=None,  # 对话打卡时只有名字，kg 通过名字查
                spot_name=matched_name,
                park_code=park_code or (conv.park_code or ""),
                avatar_code=avatar_code,
                route_context=route_context,
                conv=conv,
                db=db,
            )
            latency = int((time.perf_counter() - t0) * 1000)
            await _save_assistant_message(db, conv, result.narrative, [], latency)
            return ChatTextResponse(
                answer=result.narrative,
                audio_url=result.audio_url,
                emotion=result.emotion,
                motion=result.motion,
                latency_ms=latency,
            )

    await _save_user_message(db, conv, user_text)

    # A3/B3：路线重规划意图检测（在 Dify 调用前，有路线且有当前景点时才检测）
    if route_context and route_context.current_spot_code and route_context.remaining_names:
        replan_action, replan_hint = _detect_replan_intent(user_text)
        if replan_action:
            from app.services.kg_planner import plan_remaining
            from app.schemas import TouristPreference
            # 从 conv 恢复偏好（尽力而为，无则用默认值）
            tourist_pref = TouristPreference()
            remaining_codes = []
            # 尝试将 remaining_names 反查为 code
            _park = park_code or (conv.park_code or "")
            if _park:
                from app.services.kg_repo import load_park as _load_park
                _graph = _load_park(_park)
                if _graph:
                    remaining_codes = [
                        next((s.code for s in _graph.all() if s.name == n), "")
                        for n in route_context.remaining_names
                    ]
                    remaining_codes = [c for c in remaining_codes if c]
            new_route = plan_remaining(
                park=_park,
                current_code=route_context.current_spot_code,
                remaining_codes=remaining_codes,
                pref=tourist_pref,
                action=replan_action,
                hint=replan_hint,
            )
            if new_route:
                if replan_action == "skip":
                    next_name = route_context.remaining_names[0] if route_context.remaining_names else ""
                    answer = f"好的，跳过{next_name}{'，' if next_name else ''}直接前往下一站！"
                    if new_route.spots:
                        answer += f"接下来我们去{new_route.spots[0].name}。"
                else:
                    answer = f"没问题！已为您把{replan_hint or '该景点'}加入行程。"
                    if new_route.spots:
                        answer += f"下一站先去{new_route.spots[0].name}。"
                audio_url = await _tts_synthesize(answer, session_id)
                tags = tag_dialogue(answer)
                latency = int((time.perf_counter() - t0) * 1000)
                await _save_assistant_message(db, conv, answer, [], latency)
                return ChatTextResponse(
                    answer=answer, audio_url=audio_url,
                    emotion=tags.emotion, motion=tags.motion,
                    latency_ms=latency, new_route=new_route,
                )

    # 1) Dify RAG 问答（携带已有 conversation_id 保持多轮上下文）
    inputs = _build_dify_inputs(route_context)
    dify_resp = await dify_client.chat(query=user_text, user=session_id,
                                        conversation_id=conv.dify_conversation_id,
                                        inputs=inputs)
    answer = dify_resp["answer"]
    citations = dify_resp["citations"]
    # 回写 Dify 返回的 conversation_id，供下一轮使用
    if dify_resp.get("conversation_id") and dify_resp["conversation_id"] != "stub":
        conv.dify_conversation_id = dify_resp["conversation_id"]
        await db.commit()

    # 2) TTS——三级降级链：CosyVoice2 → 二级（edge/fish）→ 前端 Web Speech API
    audio_url = await _tts_synthesize(answer, session_id)

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
                               park_code=req.park_code,
                               route_context=req.route_context)


async def _do_checkin(
    session_id: str,
    spot_code: Optional[str],
    spot_name: Optional[str],
    park_code: str,
    avatar_code: Optional[str],
    route_context: Optional[RouteContext],
    conv,
    db: AsyncSession,
) -> CheckinResponse:
    """打卡核心逻辑：查 highlight → TTS → Dify 补充 → 拼接。"""
    from app.services.kg_repo import load_park

    highlight = ""
    resolved_code = spot_code or ""
    resolved_name = spot_name or ""

    graph = load_park(park_code) if park_code else None
    if graph:
        # 先按 code 找，再按名字找
        spot_obj = (graph.get(spot_code) if spot_code else None)
        if spot_obj is None and spot_name:
            spot_obj = next((s for s in graph.all() if s.name == spot_name), None)
        if spot_obj:
            highlight = spot_obj.highlight
            resolved_code = spot_obj.code
            resolved_name = spot_obj.name

    # Dify 补充一句（带路线上下文）
    inputs = _build_dify_inputs(route_context)
    dify_query = f"我已到达{resolved_name}，请用一句话补充一个有趣的小知识或观赏建议。"
    dify_resp = await dify_client.chat(
        query=dify_query,
        user=session_id,
        conversation_id=conv.dify_conversation_id,
        inputs=inputs,
    )
    dify_supplement = dify_resp.get("answer", "") if isinstance(dify_resp, dict) else ""
    if dify_resp.get("conversation_id") and dify_resp["conversation_id"] != "stub":
        conv.dify_conversation_id = dify_resp["conversation_id"]
        await db.commit()

    narrative = highlight
    if dify_supplement and dify_supplement != highlight:
        narrative = (highlight + "\n\n" + dify_supplement).strip()
    if not narrative:
        narrative = f"欢迎来到{resolved_name}！"

    audio_url = await _tts_synthesize(narrative, session_id)

    # 确定下一站
    next_spot_name: Optional[str] = None
    next_walk_minutes: Optional[int] = None
    if route_context and route_context.remaining_names:
        remaining = route_context.remaining_names
        # 当前打卡景点在 remaining 中的位置
        try:
            idx = remaining.index(resolved_name)
            if idx + 1 < len(remaining):
                next_spot_name = remaining[idx + 1]
        except ValueError:
            # 打卡的不在 remaining 里（已经是第一站场景）
            if remaining:
                next_spot_name = remaining[0]
        # 从 KG 找步行时间
        if graph and next_spot_name and resolved_code:
            spot_obj = graph.get(resolved_code)
            if spot_obj:
                next_spot_obj = next((s for s in graph.all() if s.name == next_spot_name), None)
                if next_spot_obj:
                    next_walk_minutes = spot_obj.neighbor_minutes(next_spot_obj.code)

    return CheckinResponse(
        narrative=narrative,
        audio_url=audio_url,
        emotion="joy",
        motion="wave",
        next_spot_name=next_spot_name,
        next_walk_minutes=next_walk_minutes,
        checked_in_spot_code=resolved_code,
    )


@router.post("/checkin", response_model=CheckinResponse)
async def checkin(req: CheckinRequest, db: AsyncSession = Depends(get_db)):
    """用户到达景点打卡：返回景点介绍 + TTS + VRM wave 动作 + 下一站提示。"""
    conv = await _ensure_conversation(db, req.session_id, req.avatar_code, req.park_code)
    return await _do_checkin(
        session_id=req.session_id,
        spot_code=req.spot_code,
        spot_name=None,
        park_code=req.park_code,
        avatar_code=req.avatar_code,
        route_context=req.route_context,
        conv=conv,
        db=db,
    )


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


@router.get("/pref/{session_id}")
async def get_pref(session_id: str, db: AsyncSession = Depends(get_db)):
    """返回当前会话的偏好摘要，前端轮询用于感知偏好变化。"""
    q = select(Conversation).where(Conversation.session_id == session_id)
    conv = (await db.execute(q)).scalar_one_or_none()
    if conv is None:
        return {"preferences_summary": ""}
    return {"preferences_summary": conv.preferences_summary or ""}


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

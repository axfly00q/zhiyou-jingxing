"""LiveTalking 客户端：把 TTS 音频送给数字人，让其口型同步播放。

LiveTalking 官方提供 /human 接口接受文本/音频，并通过 WebRTC 推流。
此处仅封装"给数字人喂音频/文本"与"获取播放页"两个动作。
"""
from __future__ import annotations

from typing import Optional

import httpx

from app.core.config import settings
from app.core.logger import logger


class LiveTalkingClient:
    def __init__(self) -> None:
        self.base_url = settings.livetalking_base_url.rstrip("/")
        self.default_avatar = settings.livetalking_default_avatar

    async def speak_text(self, text: str, session_id: str,
                         avatar: Optional[str] = None) -> bool:
        """触发数字人朗读一段文本。"""
        if not self.base_url:
            logger.warning("LIVETALKING_BASE_URL 未配置，跳过推流")
            return False
        payload = {
            "text": text,
            "type": "echo",
            "interrupt": True,
            "sessionid": session_id,
            "avatar": avatar or self.default_avatar,
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(f"{self.base_url}/human", json=payload)
                resp.raise_for_status()
            return True
        except Exception as exc:
            logger.exception("LiveTalking 推送失败：{}", exc)
            return False

    async def interrupt(self, session_id: str) -> None:
        if not self.base_url:
            return
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(f"{self.base_url}/interrupt",
                                  json={"sessionid": session_id})
        except Exception as exc:
            logger.warning("LiveTalking interrupt 失败：{}", exc)

    def webrtc_page_url(self, session_id: str,
                        avatar: Optional[str] = None) -> str:
        """前端 iframe 嵌入这个 URL 即可显示数字人画面。"""
        return (f"{self.base_url}/webrtc.html?sessionid={session_id}"
                f"&avatar={avatar or self.default_avatar}")


livetalking_client = LiveTalkingClient()

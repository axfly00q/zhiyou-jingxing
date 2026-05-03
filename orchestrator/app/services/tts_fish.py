"""Fish Audio TTS 客户端（Tier-2 降级）：调用 Fish Audio REST API 合成中文语音。

API 文档：https://docs.fish.audio/api-reference/text-to-speech
鉴权：Bearer token（FISH_API_KEY）
音色：FISH_VOICE_ID 指定克隆音色 ID，留空则使用 Fish 默认中文女声
"""
from __future__ import annotations

from typing import Optional

import httpx

from app.core.config import settings
from app.core.logger import logger

_FISH_TTS_URL = "https://api.fish.audio/v1/tts"


class FishTTSClient:
    def __init__(self) -> None:
        self.api_key = settings.fish_api_key
        self.voice_id = settings.fish_voice_id

    async def synthesize(self, text: str) -> bytes:
        """文本 → MP3 字节；未配置 API Key 或请求失败时返回 b''。"""
        if not text:
            return b""
        if not self.api_key:
            logger.warning("FISH_API_KEY 未配置，跳过 Fish Audio TTS")
            return b""

        payload: dict = {
            "text": text,
            "format": "mp3",
            "latency": "normal",
        }
        if self.voice_id:
            payload["reference_id"] = self.voice_id

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(_FISH_TTS_URL, json=payload, headers=headers)
                resp.raise_for_status()
                return resp.content
        except Exception as exc:
            logger.exception("Fish Audio TTS 失败：{}", exc)
            return b""

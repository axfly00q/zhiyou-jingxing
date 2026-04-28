"""CosyVoice2 HTTP 客户端：文本 + 音色 → MP3 字节。

预期接口：POST {TTS_BASE_URL}/api/v1/tts  json={"text", "voice"} → audio/mpeg
"""
from __future__ import annotations

from typing import Optional

import httpx

from app.core.config import settings
from app.core.logger import logger


class TTSClient:
    def __init__(self) -> None:
        self.base_url = settings.tts_base_url.rstrip("/")
        self.default_voice = settings.tts_default_voice

    async def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
        if not self.base_url:
            logger.warning("TTS_BASE_URL 未配置，返回空音频")
            return b""
        payload = {"text": text, "voice": voice or self.default_voice, "format": "mp3"}
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(f"{self.base_url}/api/v1/tts", json=payload)
                resp.raise_for_status()
                return resp.content
        except Exception as exc:
            logger.exception("TTS 失败：{}", exc)
            return b""


tts_client = TTSClient()

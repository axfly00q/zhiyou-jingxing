"""FunASR HTTP 客户端：上传 16k WAV → 文本。

FunASR 官方 runtime 提供 WebSocket / HTTP 两种接口；此处用 HTTP 简化集成。
预期接口：POST {ASR_BASE_URL}/api/v1/asr  multipart audio_file → {"text": "..."}
"""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.logger import logger


class ASRClient:
    def __init__(self) -> None:
        self.base_url = settings.asr_base_url.rstrip("/")

    async def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000,
                         lang: str = "zh") -> str:
        if not self.base_url:
            logger.warning("ASR_BASE_URL 未配置，返回空文本")
            return ""
        files = {"audio_file": ("audio.wav", audio_bytes, "audio/wav")}
        params = {"lang": lang, "sample_rate": sample_rate}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(f"{self.base_url}/api/v1/asr",
                                         files=files, params=params)
                resp.raise_for_status()
                return (resp.json() or {}).get("text", "").strip()
        except Exception as exc:
            logger.exception("ASR 失败：{}", exc)
            return ""


asr_client = ASRClient()

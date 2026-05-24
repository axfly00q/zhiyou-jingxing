"""火山引擎 BigTTS 客户端（Tier-2 降级 TTS）。

控制台：https://console.volcengine.com/speech/service/8
鉴权：APP ID + Access Token（控制台「服务接口认证信息」→「编辑」查看）
端点：https://openspeech.bytedance.com/api/v1/tts
集群：volcano_bigtts
"""
from __future__ import annotations

import base64
import uuid
from typing import Optional

import httpx

from app.core.config import settings
from app.core.logger import logger

_TTS_URL = "https://openspeech.bytedance.com/api/v1/tts"
_CLUSTER = "volcano_bigtts"
_DEFAULT_VOICE = "zh_female_wanwanxiaohe_moon_bigtts"


class DoubaoTTSClient:
    def __init__(self, voice: Optional[str] = None) -> None:
        self.app_id = settings.doubao_app_id
        self.access_token = settings.doubao_access_token
        self.voice = voice or settings.doubao_tts_voice or _DEFAULT_VOICE

    async def synthesize(self, text: str) -> bytes:
        """文本 -> MP3 字节；未配置凭证或请求失败时返回 b''。"""
        if not text:
            return b""
        if not self.app_id or not self.access_token:
            logger.warning("DOUBAO_APP_ID / DOUBAO_ACCESS_TOKEN 未配置，跳过火山 BigTTS")
            return b""
        payload = {
            "app": {
                "appid": self.app_id,
                "token": self.access_token,
                "cluster": _CLUSTER,
            },
            "user": {"uid": "orchestrator"},
            "audio": {
                "voice_type": self.voice,
                "encoding": "mp3",
                "speed_ratio": 1.0,
                "volume_ratio": 1.0,
                "pitch_ratio": 1.0,
            },
            "request": {
                "reqid": uuid.uuid4().hex,
                "text": text,
                "text_type": "plain",
                "operation": "query",
            },
        }
        headers = {
            "Authorization": f"Bearer;{self.access_token}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(_TTS_URL, json=payload, headers=headers)
                if resp.status_code != 200:
                    logger.error("火山 BigTTS 返回 {} body={}", resp.status_code, resp.text[:200])
                    return b""
                data = resp.json()
                code = data.get("code")
                if code != 3000:
                    logger.error("火山 BigTTS 业务错误 code={} msg={}", code, data.get("message"))
                    return b""
                audio_b64: str = data.get("data", {}).get("audio", "")
                if not audio_b64:
                    logger.warning("火山 BigTTS 返回空音频")
                    return b""
                return base64.b64decode(audio_b64)
        except Exception as exc:
            logger.exception("火山 BigTTS 失败：{}", exc)
            return b""

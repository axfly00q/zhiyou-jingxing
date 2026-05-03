"""Edge TTS 客户端（Tier-2 降级）：调用微软 edge-tts 库合成中文语音。

依赖：edge-tts>=6.1（已在 pyproject.toml 中声明）
默认音色：zh-CN-XiaoxiaoNeural（微软晓晓，自然女声，适合导游场景）
"""
from __future__ import annotations

import io
from typing import Optional

from app.core.config import settings
from app.core.logger import logger

_DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"


class EdgeTTSClient:
    def __init__(self, voice: Optional[str] = None) -> None:
        self.voice = voice or _DEFAULT_VOICE

    async def synthesize(self, text: str) -> bytes:
        """文本 → MP3 字节；失败返回 b''。"""
        if not text:
            return b""
        try:
            import edge_tts  # 懒导入，仅在实际使用时触发
            buf = io.BytesIO()
            communicate = edge_tts.Communicate(text, self.voice)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buf.write(chunk["data"])
            data = buf.getvalue()
            if not data:
                logger.warning("Edge TTS 返回空音频 voice={}", self.voice)
            return data
        except ImportError:
            logger.error("edge-tts 未安装，无法使用 Edge TTS；请运行 pip install edge-tts")
            return b""
        except Exception as exc:
            logger.exception("Edge TTS 失败：{}", exc)
            return b""

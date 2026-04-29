"""TTS 音频缓存：把 MP3 字节落盘为 ``data/tts_cache/{sid}_{ts}.mp3``，
返回相对 URL（``/static/tts/...``），由 ``main.py`` 的 StaticFiles 路由对外提供。

避免把音频 base64 内嵌在 JSON 响应里（B13）：单分钟语音可达 ~1.4 MB，
多并发会迅速堆叠在内存与 nginx ``client_max_body_size`` 之上。
"""
from __future__ import annotations

import asyncio
import re
import time
from pathlib import Path

from app.core.logger import logger

# 与 main.py 中 StaticFiles 挂载点对应
TTS_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "tts_cache"
TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

_SAFE = re.compile(r"[^A-Za-z0-9_-]")
_MAX_AGE_SEC = 3600  # 1 小时


def _safe(name: str) -> str:
    return _SAFE.sub("", name or "")[:32] or "anon"


async def save_tts_mp3(data: bytes, session_id: str) -> str:
    """把 MP3 字节写到缓存目录，返回 ``/static/tts/<filename>`` 公开 URL。"""
    fn = f"{_safe(session_id)}_{int(time.time() * 1000)}.mp3"
    fp = TTS_CACHE_DIR / fn
    await asyncio.to_thread(fp.write_bytes, data)
    return f"/static/tts/{fn}"


def cleanup_tts_cache(max_age_sec: int = _MAX_AGE_SEC) -> int:
    """删除超过 ``max_age_sec`` 的缓存文件，返回清理数量。"""
    now = time.time()
    n = 0
    for f in TTS_CACHE_DIR.glob("*.mp3"):
        try:
            if now - f.stat().st_mtime > max_age_sec:
                f.unlink(missing_ok=True)
                n += 1
        except OSError as exc:  # noqa: PERF203
            logger.warning("清理 TTS 缓存失败 {}: {}", f, exc)
    return n

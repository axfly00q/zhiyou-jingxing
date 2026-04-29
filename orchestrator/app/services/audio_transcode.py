"""音频格式转换：把任意上传音频（webm/opus、mp4、ogg…）转为 16k mono PCM WAV。

FunASR HTTP 接口仅稳定支持 wav/pcm。前端 ``MediaRecorder`` 默认输出 ``audio/webm;codecs=opus``，
若直接以 ``audio/wav`` 文件名透传，FunASR 会解析失败返回空。

使用 ffmpeg 子进程做转码；若运行环境没有 ffmpeg，则记录 warning 并原样返回，由上层决定是否继续。
"""
from __future__ import annotations

import asyncio
import shutil

from app.core.logger import logger

_TARGET_SR = 16000
_HAS_FFMPEG: bool | None = None


def _ffmpeg_available() -> bool:
    global _HAS_FFMPEG
    if _HAS_FFMPEG is None:
        _HAS_FFMPEG = shutil.which("ffmpeg") is not None
        if not _HAS_FFMPEG:
            logger.warning("ffmpeg 不在 PATH 中，无法做音频转码；ASR 可能失败")
    return _HAS_FFMPEG


async def to_wav_16k_mono(data: bytes, src_hint: str | None = None) -> bytes:
    """把任意编码的音频字节转成 16k mono WAV。失败或无 ffmpeg 时返回原始字节。"""
    if not data:
        return data
    # 已经是 wav 头就不处理
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return data
    if not _ffmpeg_available():
        return data
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-i", "pipe:0",
            "-ac", "1", "-ar", str(_TARGET_SR), "-f", "wav",
            "pipe:1",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, err = await proc.communicate(input=data)
        if proc.returncode != 0:
            logger.error("ffmpeg 转码失败 hint={} rc={} stderr={}",
                         src_hint, proc.returncode, err.decode("utf-8", "ignore")[:200])
            return data
        return out
    except Exception as exc:
        logger.exception("ffmpeg 调用异常：{}", exc)
        return data

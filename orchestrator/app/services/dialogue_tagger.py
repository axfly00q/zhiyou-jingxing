"""把 LLM 文本回复转成数字人前端需要的 (emotion, motion) 标签。

MVP 阶段使用关键词规则；后续可替换为让 LLM 在生成时直接输出
JSON 包含 emotion/motion 字段。
"""
from __future__ import annotations

from dataclasses import dataclass

# VRM 标准情绪：neutral / joy / sorrow / angry / surprised
EMOTIONS = ("neutral", "joy", "sorrow", "angry", "surprised")
# 前端预制动作：idle / wave / explain / think
MOTIONS = ("idle", "wave", "explain", "think")

_JOY_KW = ("欢迎", "你好", "您好", "高兴", "开心", "棒", "太好了", "请", "谢谢", "感谢")
_SORROW_KW = ("抱歉", "对不起", "遗憾", "不好意思", "可惜")
_SURPRISED_KW = ("哇", "竟然", "居然", "想不到", "没想到")
_ANGRY_KW = ()  # 留空，导游场景几乎不出现

_WAVE_KW = ("欢迎", "你好", "您好", "再见", "下次")
_EXPLAIN_KW = ("看", "请看", "这里", "这个", "那是", "那个", "这就是", "首先",
               "其次", "另外", "比如", "例如", "也就是说", "其实", "建造", "始建")
_THINK_KW = ("嗯", "让我想想", "可能", "也许", "应该", "或许", "我觉得")


@dataclass(frozen=True)
class DialogueTags:
    emotion: str = "neutral"
    motion: str = "idle"


def _hit_any(text: str, words: tuple[str, ...]) -> bool:
    return any(w in text for w in words)


def tag(text: str) -> DialogueTags:
    """根据回答文本推断情绪与动作。空文本返回默认 (neutral, idle)。"""
    if not text:
        return DialogueTags()

    # 情绪
    emotion = "neutral"
    if _hit_any(text, _SORROW_KW):
        emotion = "sorrow"
    elif _hit_any(text, _SURPRISED_KW):
        emotion = "surprised"
    elif _hit_any(text, _JOY_KW):
        emotion = "joy"
    elif _hit_any(text, _ANGRY_KW):
        emotion = "angry"

    # 动作（优先级：think > wave > explain > idle）
    motion = "idle"
    if _hit_any(text, _THINK_KW):
        motion = "think"
    elif _hit_any(text, _WAVE_KW):
        motion = "wave"
    elif _hit_any(text, _EXPLAIN_KW):
        motion = "explain"

    return DialogueTags(emotion=emotion, motion=motion)

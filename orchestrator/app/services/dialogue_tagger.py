"""把 LLM 文本回复转成数字人前端需要的 (emotion, motion) 标签。

MVP 阶段使用关键词规则；后续可替换为让 LLM 在生成时直接输出
JSON 包含 emotion/motion 字段。
"""
from __future__ import annotations

from dataclasses import dataclass

# VRM 标准情绪：neutral / joy / sorrow / angry / surprised
EMOTIONS = ("neutral", "joy", "sorrow", "angry", "surprised")
# 前端预制动作：idle / wave / explain / think + 7 个新增动作
MOTIONS = ("idle", "wave", "explain", "think",
           "beckon", "bow", "clap", "goodbye", "listen", "point", "shrug")

_JOY_KW = ("欢迎", "你好", "您好", "高兴", "开心", "棒", "太好了", "请", "谢谢", "感谢")
_SORROW_KW = ("抱歉", "对不起", "遗憾", "不好意思", "可惜")
_SURPRISED_KW = ("哇", "竟然", "居然", "想不到", "没想到")
_ANGRY_KW = ()  # 留空，导游场景几乎不出现

# ---- 动作关键词 ----
# 原有动作（wave 去掉"再见"交给 goodbye；explain 去掉"请看"交给 point）
_WAVE_KW = ("欢迎", "你好", "您好", "下次")
_EXPLAIN_KW = ("看", "这里", "这个", "那是", "那个", "这就是", "首先",
               "其次", "另外", "比如", "例如", "也就是说", "其实", "建造", "始建")
_THINK_KW = ("嗯", "让我想想", "可能", "也许", "应该", "或许", "我觉得")

# 新增 7 个动作关键词
_GOODBYE_KW = ("再见", "拜拜", "下次见", "再会", "结束游览", "告辞", "回见")
_BOW_KW = ("感谢", "谢谢", "致敬", "敬意", "辛苦了", "多谢", "鞠躬")
_CLAP_KW = ("答对了", "恭喜", "太棒了", "厉害", "真不错", "正确", "完全正确", "真棒")
_BECKON_KW = ("过来看", "跟我来", "这边走", "来这里", "过来吧", "随我来", "走这边")
_POINT_KW = ("请看", "那边", "那里", "往那看", "方向", "指向", "看那", "前方就是")
_SHRUG_KW = ("不确定", "不太清楚", "不知道", "这个嘛", "说不准", "难说", "不好说")
# listen：不由文本触发，由前端语音检测自动触发


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

    # 动作（优先级：goodbye > bow > clap > beckon > point > shrug > think > wave > explain > idle）
    motion = "idle"
    if _hit_any(text, _GOODBYE_KW):
        motion = "goodbye"
    elif _hit_any(text, _BOW_KW):
        motion = "bow"
    elif _hit_any(text, _CLAP_KW):
        motion = "clap"
    elif _hit_any(text, _BECKON_KW):
        motion = "beckon"
    elif _hit_any(text, _POINT_KW):
        motion = "point"
    elif _hit_any(text, _SHRUG_KW):
        motion = "shrug"
    elif _hit_any(text, _THINK_KW):
        motion = "think"
    elif _hit_any(text, _WAVE_KW):
        motion = "wave"
    elif _hit_any(text, _EXPLAIN_KW):
        motion = "explain"

    return DialogueTags(emotion=emotion, motion=motion)

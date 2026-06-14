"""创新点 2：游客情感分析 + 服务优化建议引擎。

两个能力：
1) `analyze(text)` —— 单条游客发言的实时打标：意图 / 情感 / 关键词；
   走 LLM JSON 模式，prompt 内置类目 schema，失败兜底用关键词规则。
2) `generate_suggestions(messages)` —— 聚合一段时间内的负向消息，
   让 LLM 提炼"问题摘要 + 改进建议"，落库 `Suggestion`，对应"服务优化建议"。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import List, Optional

from app.core.logger import logger
from app.services.llm_client import llm_client

INTENTS = ["explain", "recommend", "complaint", "navigation", "chitchat"]
SENTIMENTS = ["pos", "neu", "neg"]

_NEG_KW = (
    # 直接投诉词
    "不满", "投诉", "差评", "失望", "排队", "脏", "贵", "无聊", "找不到", "误导", "等太久",
    # 补充：常见投诉场景
    "人太多", "看不到", "设施差", "不推荐", "没想象中",
    "没有想象", "不值得", "太差", "走弯路", "指示牌太少",
    "很差", "不如意", "差得",
)
_POS_KW = (
    # 直接赞誉词
    "好看", "漂亮", "喜欢", "棒", "舒服", "好玩", "厉害", "感谢", "很推荐", "强推",
    # 补充：景区高频赞誉词
    "开阔", "太美", "值得", "很美", "很好", "很棒",
    "真美", "真好", "超美", "非常漂亮", "景色很好",
    "赞", "不错", "满意", "很开心", "非常好",
)


@dataclass
class AnalysisResult:
    intent: str
    sentiment: str
    sentiment_score: float  # -1 ~ 1
    keywords: List[str]


def _rule_fallback(text: str) -> AnalysisResult:
    # ── 1. 情感判断 ──────────────────────────────────────────────────────────
    if any(k in text for k in _NEG_KW):
        s, sc = "neg", -0.6
    elif any(k in text for k in _POS_KW):
        s, sc = "pos", 0.6
    else:
        s, sc = "neu", 0.0

    # ── 2. 意图判断（优先级：complaint > recommend > navigation > explain > chitchat）
    # neg 情感直接归 complaint，不被其他关键词覆盖
    if s == "neg":
        intent = "complaint"
    else:
        intent = "chitchat"
        # recommend：含推荐/建议关键词（最高级，因为"带孩子去哪"包含哪，但是recommend）
        if any(k in text for k in ("推荐", "建议", "哪个好", "值得去", "适合")):
            intent = "recommend"
        # navigation：含方位/位置关键词
        elif any(k in text for k in ("怎么走", "在哪", "在哪里", "出口", "厕所", "停车", "哪里", "哪边", "方向", "餐厅", "附近")):
            intent = "navigation"
        # explain：含 what/why/how 问词，但排除「怎么走」「怎么了」「怎么样」等
        elif any(k in text for k in ("为什么", "什么意思", "什么朝代", "什么时候",
                                     "什么是", "讲讲", "介绍", "来历", "历史",
                                     "怎么理解", "怎么来的")):
            intent = "explain"
        elif "怎么" in text and "走" not in text and "了" not in text and "样" not in text:
            intent = "explain"

    kws = re.findall(r"[\u4e00-\u9fa5A-Za-z]{2,6}", text)[:5]
    return AnalysisResult(intent, s, sc, kws)




PROMPT = """你是文旅服务的对话标注引擎。请对游客发言做三项标注，严格输出 JSON：
{{
  "intent": one of {intents},
  "sentiment": one of {sentiments},
  "sentiment_score": float in [-1, 1],
  "keywords": [up to 5 short Chinese keywords]
}}
游客发言：「{text}」
只输出 JSON，不要任何解释。"""


async def analyze(text: str) -> AnalysisResult:
    if not text.strip():
        return AnalysisResult("chitchat", "neu", 0.0, [])
    try:
        raw = await llm_client.chat(
            [{"role": "user", "content": PROMPT.format(
                intents=INTENTS, sentiments=SENTIMENTS, text=text)}],
            temperature=0.0, max_tokens=200, json_mode=True,
        )
        data = json.loads(raw)
        intent = data.get("intent") if data.get("intent") in INTENTS else "chitchat"
        sentiment = data.get("sentiment") if data.get("sentiment") in SENTIMENTS else "neu"
        score = float(data.get("sentiment_score", 0.0))
        score = max(-1.0, min(1.0, score))
        kws = [str(k) for k in (data.get("keywords") or [])][:5]
        return AnalysisResult(intent, sentiment, score, kws)
    except Exception as exc:
        logger.warning("情感分析降级到规则：{}", exc)
        return _rule_fallback(text)


SUGGEST_PROMPT = """以下是过去一段时间游客的负面/投诉发言（已标注情感强度）。
请从服务质量、讲解内容、动线设计、设施体验四个角度，提炼出最多 5 条
"问题摘要 + 可执行改进建议"，每条 priority ∈ ["high","medium","low"]。
严格输出 JSON 数组：
[{{"title": "...", "summary": "...", "priority": "..."}}]

输入样本：
{samples}
"""


async def generate_suggestions(neg_messages: List[dict]) -> list[dict]:
    """neg_messages: [{id, content, sentiment_score}, ...]，按情感强度 Top N 提供。"""
    if not neg_messages:
        return []
    samples = "\n".join(
        f"- (msg#{m['id']}, score={m['sentiment_score']:.2f}) {m['content']}"
        for m in neg_messages[:30]
    )
    try:
        raw = await llm_client.chat(
            [{"role": "user", "content": SUGGEST_PROMPT.format(samples=samples)}],
            temperature=0.3, max_tokens=800, json_mode=True,
        )
        # 兼容 LLM 直接返回数组或包了一层 {"suggestions": [...]} 的情况
        data = json.loads(raw)
        if isinstance(data, dict):
            data = data.get("suggestions") or data.get("data") or []
        out: list[dict] = []
        evidence_ids = [m["id"] for m in neg_messages[:30]]
        for item in (data or [])[:5]:
            out.append({
                "title": str(item.get("title", ""))[:120] or "未命名建议",
                "summary": str(item.get("summary", ""))[:1000],
                "priority": item.get("priority") if item.get("priority") in
                            ("high", "medium", "low") else "medium",
                "evidence": evidence_ids,
            })
        return out
    except Exception as exc:
        logger.warning("建议生成失败：{}", exc)
        return []

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

_NEG_KW = ("不满", "投诉", "差评", "失望", "排队", "脏", "贵", "无聊", "找不到", "误导", "等太久")
_POS_KW = ("好看", "漂亮", "喜欢", "棒", "推荐", "舒服", "好玩", "厉害", "感谢")


@dataclass
class AnalysisResult:
    intent: str
    sentiment: str
    sentiment_score: float  # -1 ~ 1
    keywords: List[str]


def _rule_fallback(text: str) -> AnalysisResult:
    if any(k in text for k in _NEG_KW):
        s, sc = "neg", -0.6
    elif any(k in text for k in _POS_KW):
        s, sc = "pos", 0.6
    else:
        s, sc = "neu", 0.0
    intent = "complaint" if s == "neg" else "chitchat"
    if any(k in text for k in ("怎么", "为什么", "讲讲", "介绍")):
        intent = "explain"
    if any(k in text for k in ("推荐", "去哪", "建议")):
        intent = "recommend"
    if any(k in text for k in ("怎么走", "在哪", "出口", "厕所")):
        intent = "navigation"
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

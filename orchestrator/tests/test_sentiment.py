"""sentiment 规则兜底单测（无 LLM 也可跑）。"""
from __future__ import annotations

from app.services.sentiment import _rule_fallback


def test_negative_keywords():
    r = _rule_fallback("排队太久了，太失望")
    assert r.sentiment == "neg"
    assert r.intent == "complaint"
    assert r.sentiment_score < 0


def test_positive_keywords():
    r = _rule_fallback("远香堂真漂亮，喜欢")
    assert r.sentiment == "pos"
    assert r.sentiment_score > 0


def test_intent_explain():
    r = _rule_fallback("讲讲香洲的来历")
    assert r.intent == "explain"


def test_intent_navigation():
    r = _rule_fallback("远香堂怎么走")
    assert r.intent == "navigation"

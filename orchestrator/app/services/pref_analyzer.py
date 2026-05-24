"""游客偏好分析器：从对话内容自动推断游客偏好标签。

在每轮对话后台异步运行，不阻塞主链路。
分析结果合并写入 Conversation.preferences_summary，供下一轮 Dify 调用使用。

偏好标签集合：
- 历史人文：关注典故、历史、名人、文化
- 摄影打卡：关注拍照、角度、光线、构图
- 亲子：带孩子游览，关注趣味、互动
- 建筑艺术：关注工艺、设计、榫卯、构造
"""
from __future__ import annotations

import re
from typing import Optional

from app.core.logger import logger

# 关键词规则（快速匹配，无需 LLM）
_PREF_RULES: list[tuple[str, list[str]]] = [
    ("历史人文", ["历史", "典故", "古代", "文化", "名人", "朝代", "渊源", "由来", "故事", "传说", "诗词"]),
    ("摄影打卡", ["拍照", "拍摄", "摄影", "角度", "构图", "光线", "打卡", "照片", "拍", "镜头", "好看"]),
    ("亲子",     ["孩子", "小孩", "儿童", "宝宝", "小朋友", "带娃", "亲子", "孩子们"]),
    ("建筑艺术", ["建筑", "工艺", "榫卯", "构造", "设计", "结构", "雕刻", "石雕", "木雕", "砖雕"]),
]


def _detect_prefs_from_text(text: str) -> set[str]:
    """从单条文本中检测偏好标签集合（规则匹配，O(n) 快速）。"""
    detected: set[str] = set()
    for label, keywords in _PREF_RULES:
        if any(kw in text for kw in keywords):
            detected.add(label)
    return detected


def _merge_prefs(existing: Optional[str], new_prefs: set[str]) -> str:
    """将新检测到的偏好合并到现有偏好字符串中，去重保序。"""
    existing_set: set[str] = set()
    if existing:
        existing_set = {p.strip() for p in re.split(r"[,，、\s]+", existing) if p.strip()}
    merged = existing_set | new_prefs
    # 按固定顺序排列（保持一致性）
    order = [label for label, _ in _PREF_RULES]
    return "、".join(p for p in order if p in merged)


async def analyze_and_update_pref(
    session_id: str,
    user_text: str,
) -> Optional[str]:
    """
    分析 user_text，将新偏好合并写入数据库 Conversation.preferences_summary。
    返回更新后的 preferences_summary（或 None 若无变化/无会话）。
    """
    new_prefs = _detect_prefs_from_text(user_text)
    if not new_prefs:
        return None

    try:
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import select
        from app.models import Conversation

        async with AsyncSessionLocal() as db:
            q = select(Conversation).where(Conversation.session_id == session_id)
            conv = (await db.execute(q)).scalar_one_or_none()
            if conv is None:
                return None

            updated = _merge_prefs(conv.preferences_summary, new_prefs)
            if updated == (conv.preferences_summary or ""):
                return updated  # 无变化

            conv.preferences_summary = updated
            await db.commit()
            logger.info("session={} 偏好更新: {}", session_id, updated)
            return updated

    except Exception as e:
        logger.warning("pref_analyzer 写库失败: {}", e)
        return None

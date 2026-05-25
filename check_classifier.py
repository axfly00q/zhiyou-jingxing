#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试 orchestrator /api/chat/text 对新分类的响应"""
import json, urllib.request, uuid

CASES = [
    ("A2_导航设施", "洗手间在哪里"),
    ("A3_拍照建议", "这里哪里最适合拍照"),
    ("A4_情绪安抚", "走了好久好累人也太多了"),
    ("B0_知识问答", "远香堂有什么历史"),
    ("D1_英文", "Where is the restroom please"),
]

def call(message: str) -> dict:
    body = json.dumps({
        "session_id": uuid.uuid4().hex[:14],
        "message": message,
        "park": "zhuozhengyuan",
    }).encode("utf-8")
    req = urllib.request.Request(
        "http://localhost:8000/api/chat/text",
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))

if __name__ == "__main__":
    for label, q in CASES:
        print(f"\n===== {label}: {q} =====")
        try:
            r = call(q)
            ans = r.get("answer", "")
            print(f"answer({len(ans)}字): {ans[:500]}")
            print(f"intent={r.get('intent')} emotion={r.get('emotion')} latency={r.get('latency_ms')}ms")
        except Exception as e:
            print(f"ERROR: {e}")

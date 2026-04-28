"""Dify 知识库问答客户端。

Dify 应用（chat-app）以 HTTP API 暴露：
    POST /v1/chat-messages
携带 `query`、`conversation_id`，返回 `answer` + `metadata.retriever_resources`。
"""
from __future__ import annotations

from typing import AsyncIterator, Optional

import httpx

from app.core.config import settings
from app.core.logger import logger


class DifyClient:
    def __init__(self) -> None:
        self.base_url = settings.dify_base_url.rstrip("/")
        self.api_key = settings.dify_api_key

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def chat(self, query: str, user: str,
                   conversation_id: Optional[str] = None,
                   inputs: Optional[dict] = None) -> dict:
        """阻塞式调用，返回 {answer, citations, conversation_id}。"""
        if not self.api_key:
            logger.warning("Dify api_key 未配置，返回桩答案")
            return {
                "answer": f"（Dify 未配置）你问的是：{query}",
                "citations": [],
                "conversation_id": conversation_id or "stub",
            }
        payload = {
            "query": query,
            "user": user,
            "response_mode": "blocking",
            "inputs": inputs or {},
        }
        if conversation_id:
            payload["conversation_id"] = conversation_id
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{self.base_url}/chat-messages",
                                     json=payload, headers=self._headers)
            resp.raise_for_status()
            data = resp.json()
        citations = []
        for r in (data.get("metadata", {}).get("retriever_resources") or []):
            citations.append({
                "title": r.get("document_name"),
                "snippet": (r.get("content") or "")[:200],
                "score": r.get("score"),
            })
        return {
            "answer": data.get("answer", ""),
            "citations": citations,
            "conversation_id": data.get("conversation_id"),
        }

    async def stream(self, query: str, user: str,
                     conversation_id: Optional[str] = None) -> AsyncIterator[str]:
        """流式调用（SSE），按 token 产出 answer 片段。"""
        if not self.api_key:
            yield f"（Dify 未配置）你问的是：{query}"
            return
        payload = {
            "query": query,
            "user": user,
            "response_mode": "streaming",
            "inputs": {},
        }
        if conversation_id:
            payload["conversation_id"] = conversation_id
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", f"{self.base_url}/chat-messages",
                                     json=payload, headers=self._headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    chunk = line[5:].strip()
                    if not chunk or chunk == "[DONE]":
                        continue
                    import json
                    try:
                        evt = json.loads(chunk)
                    except json.JSONDecodeError:
                        continue
                    if evt.get("event") in ("message", "agent_message"):
                        yield evt.get("answer", "")


dify_client = DifyClient()

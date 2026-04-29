"""Dify 知识库问答客户端。

Dify 应用（chat-app）以 HTTP API 暴露：
    POST /v1/chat-messages
携带 `query`、`conversation_id`，返回 `answer` + `metadata.retriever_resources`。
"""
from __future__ import annotations

import json
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
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(f"{self.base_url}/chat-messages",
                                         json=payload, headers=self._headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            body = (exc.response.text or "")[:200]
            logger.error("Dify {} body={}", exc.response.status_code, body)
            return {"answer": "（知识库服务暂不可用，请稍后再试）", "citations": [],
                    "conversation_id": conversation_id}
        except httpx.HTTPError as exc:
            logger.exception("Dify 网络错误：{}", exc)
            return {"answer": "（网络不稳定，请稍后再试）", "citations": [],
                    "conversation_id": conversation_id}
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
        """流式调用（SSE），按 token 产出 answer 片段。

        任何 HTTP / 网络 / JSON 错误都会被捕获并以一段提示文本产出，避免向
        WebSocket handler 抛出未处理异常导致连接被静默关闭。
        """
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
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream("POST", f"{self.base_url}/chat-messages",
                                         json=payload, headers=self._headers) as resp:
                    if resp.status_code >= 400:
                        body = (await resp.aread()).decode("utf-8", "ignore")[:200]
                        logger.error("Dify 流式返回 {} body={}", resp.status_code, body)
                        yield "（知识库服务暂不可用，请稍后重试）"
                        return
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        chunk = line[5:].strip()
                        if not chunk or chunk == "[DONE]":
                            continue
                        try:
                            evt = json.loads(chunk)
                        except json.JSONDecodeError:
                            continue
                        if evt.get("event") in ("message", "agent_message"):
                            yield evt.get("answer", "")
        except httpx.HTTPError as exc:
            logger.exception("Dify 流式网络错误：{}", exc)
            yield "（网络不稳定，请稍后重试）"

    async def upload_dataset_document(self, filename: str, content: bytes,
                                       content_type: str = "application/octet-stream") -> dict:
        """调用 Dify Datasets API 把文件入库（``create_by_file``）。

        要求 ``settings.dify_dataset_id`` 与 ``settings.dify_dataset_api_key`` 都已配置；
        否则抛 ``RuntimeError``。返回 Dify 响应原文（含 ``document.id`` 等）。
        """
        dataset_id = settings.dify_dataset_id
        api_key = settings.dify_dataset_api_key or self.api_key
        if not dataset_id or not api_key:
            raise RuntimeError("dify dataset 未配置")
        url = f"{self.base_url}/datasets/{dataset_id}/document/create_by_file"
        # 按 Dify 规范：data 字段是 JSON 字符串；file 是 multipart 文件
        data_json = json.dumps({
            "indexing_technique": "high_quality",
            "process_rule": {"mode": "automatic"},
        })
        files = {
            "data": (None, data_json, "application/json"),
            "file": (filename, content, content_type),
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, files=files,
                                     headers={"Authorization": f"Bearer {api_key}"})
            resp.raise_for_status()
            return resp.json()


dify_client = DifyClient()

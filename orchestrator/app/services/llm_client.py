"""LLM 客户端：用于自研模块（情感分析、建议生成、KG 抽取）。

注意：游客对话主链路的 LLM 调用走 Dify（含 RAG），此处的 LLM 仅服务于
"非对话"场景。多供应商通过 `LLM_PROVIDER` 环境变量切换。
"""
from __future__ import annotations

from typing import List

import httpx

from app.core.config import settings
from app.core.logger import logger


class LLMError(RuntimeError):
    pass


class LLMClient:
    """OpenAI 兼容协议（DeepSeek / 通义 DashScope OpenAI 兼容端点）。"""

    def __init__(self) -> None:
        if settings.llm_provider == "deepseek":
            self.api_key = settings.deepseek_api_key
            self.base_url = settings.deepseek_base_url
            self.model = settings.deepseek_model
        elif settings.llm_provider == "dashscope":
            self.api_key = settings.dashscope_api_key
            self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
            self.model = settings.dashscope_model
        else:
            raise LLMError(f"unknown LLM provider: {settings.llm_provider}")

    async def chat(self, messages: List[dict], temperature: float = 0.3,
                   max_tokens: int = 1024, json_mode: bool = False) -> str:
        if not self.api_key:
            logger.warning("LLM api_key 未配置，返回桩文本（仅用于本地无 Key 调试）")
            return "{}" if json_mode else "（LLM 未配置）"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]


llm_client = LLMClient()

# 智游景行 · 景区导览 AI 数字人

面向苏州园林（拙政园 / 留园）的智能、互动、个性化数字人导览 MVP。

## 架构总览

```
                       ┌─────────────────────┐
游客浏览器 ──WebRTC──▶ │ LiveTalking (数字人)│ ◀─音频──┐
        │              └─────────────────────┘         │
        │                                              │
        ▼  WebSocket                                   │
 ┌──────────────────┐  HTTP   ┌──────────────────┐   │
 │ Orchestrator     │────────▶│ Dify (RAG + LLM)│   │
 │ (FastAPI 自研)   │         └──────────────────┘   │
 │                  │  HTTP   ┌──────────────────┐   │
 │ - 对话编排       │────────▶│ FunASR (ASR)    │   │
 │ - 知识图谱路线规划│         └──────────────────┘   │
 │ - 情感分析+建议  │  HTTP   ┌──────────────────┐   │
 │                  │────────▶│ CosyVoice2 (TTS)│───┘
 └──────────────────┘         └──────────────────┘
        │
        ├─PostgreSQL（业务数据 / 对话 / 建议）
        ├─Redis（会话缓存）
        └─Neo4j（景区知识图谱）

 三个前端：
 - frontend-tourist     游客对话端
 - frontend-admin       运营后台
 - frontend-dashboard   数据大屏
```

## 复用 vs 自研

| 模块 | 方案 |
|---|---|
| 数字人驱动 | LiveTalking + MuseTalk（复用） |
| LLM/RAG | Dify（复用） |
| ASR / TTS | FunASR / CosyVoice2（复用） |
| **对话编排 / 路线规划 / 情感分析 / 大屏** | **自研** |

## 快速开始

```bash
cp deploy/.env.example deploy/.env
cd deploy && docker compose up -d
# 等待 Dify 初始化完成，按 docs/部署手册.md 配置应用与 API Key
```

详见 [部署手册](docs/部署手册.md) 与 [总体设计](docs/总体设计.md)。

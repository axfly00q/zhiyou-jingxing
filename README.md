# 智游景行 · 景区导览 AI 数字人

面向苏州园林（拙政园 / 留园）的智能、互动、个性化数字人导览 MVP。

## 架构总览

```
                        ┌──────────────────────────┐
游客浏览器 ──three-vrm──▶│ VRM 数字人（浏览器渲染） │ ◀── MP3 音频 ──┐
        │               └──────────────────────────┘                │
        │                                                           │
        ▼  HTTP / WebSocket                                         │
 ┌──────────────────┐  HTTP   ┌──────────────────┐                 │
 │ Orchestrator     │────────▶│ Dify (RAG + LLM) │                 │
 │ (FastAPI 自研)   │         └──────────────────┘                 │
 │                  │  HTTP   ┌──────────────────┐                 │
 │ - 对话编排       │────────▶│ FunASR (ASR)     │                 │
 │ - 知识图谱路线规划│         └──────────────────┘                 │
 │ - 情感分析+建议  │  HTTP   ┌──────────────────┐                 │
 │ - 表情/动作标签  │────────▶│ CosyVoice2 (TTS) │─────────────────┘
 └──────────────────┘         └──────────────────┘
        │
        ├─PostgreSQL（业务数据 / 对话 / 建议）
        ├─Redis（会话缓存）
        └─Neo4j（景区知识图谱）

 三个前端：
 - frontend-tourist     游客对话端（内置 three-vrm 数字人 + lipSync 嘴型）
 - frontend-admin       运营后台（VRM 模型/动作上传、形象管理、服务建议、知识库）
 - frontend-dashboard   数据大屏
```

## 复用 vs 自研

| 模块 | 方案 |
|---|---|
| 数字人渲染 | three-vrm + VRM 1.0 模型（浏览器本地渲染，无 GPU 服务依赖） |
| 嘴型同步 | Web Audio API + 频谱→5 元音权重（自研轻量算法） |
| LLM/RAG | Dify（复用） |
| ASR / TTS | FunASR / CosyVoice2（复用） |
| **对话编排 / 路线规划 / 情感分析 / 表情动作标签 / 大屏** | **自研** |

## 快速开始

```bash
cp deploy/.env.example deploy/.env
cd deploy && docker compose up -d
# 等待 Dify 初始化完成，按 docs/部署手册.md 配置应用与 API Key
# 在管理后台上传 VRM 模型与 .vrma 动作文件
```

详见 [部署手册](docs/部署手册.md) 与 [总体设计](docs/总体设计.md)。

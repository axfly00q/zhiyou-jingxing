# 智游景行 - 项目启动指南

## 当前启动状态

✅ **已启动的服务：**
- **后端 API**：http://127.0.0.1:8000
  - Swagger 文档：http://127.0.0.1:8000/docs
  - ReDoc 文档：http://127.0.0.1:8000/redoc

## 启动方式对比

### 方式 A: Docker 完整启动（推荐生产部署）

**前置要求：**
- Docker Desktop 或 Docker Engine
- docker-compose v2+

**启动命令：**
```bash
cd deploy
docker compose up -d --build
```

**启动后访问地址：**
- 游客端：http://localhost:5173
- 管理后台：http://localhost:5174（admin / admin123）
- 数据大屏：http://localhost:5175
- 后端 API：http://localhost:8000/docs
- Neo4j：http://localhost:7474

**配置说明：**
- PostgreSQL、Redis、Neo4j 自动启动
- 修改 `deploy/.env` 配置各项 API Key 后重启

---

### 方式 B: 本地开发模式（当前使用）

**前置要求：**
- Python 3.11+
- Node.js 20+
- 外部服务（需手动启动）：
  - PostgreSQL 16+
  - Redis 7+
  - Neo4j 5+
  - Dify（可选，无则降级）
  - FunASR（可选，无则降级）
  - CosyVoice2（可选，无则降级）

#### 后端启动

✅ **已完成：**
```bash
cd orchestrator
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -e .[dev]
python -m uvicorn app.main:app --reload --port 8000
```

**后端 API 已在：** http://127.0.0.1:8000

#### 前端启动

**游客端（待启动）：**
```bash
cd frontend-tourist
npm install
npm run dev
# 访问：http://localhost:5173
```

**管理后台（待启动）：**
```bash
cd frontend-admin
npm install
npm run dev
# 访问：http://localhost:5174
```

**数据大屏（待启动）：**
```bash
cd frontend-dashboard
npm install
npm run dev
# 访问：http://localhost:5175
```

---

## 当前系统检查

| 组件 | 状态 | 说明 |
|---|---|---|
| Python 3.11+ | ✅ 已安装 | 后端运行中 |
| Node.js | ❌ 未找到 | 需安装以启动前端 |
| Docker | ❌ 未配置 | 若需 Docker 启动需安装配置 |
| PostgreSQL | ❓ 未检查 | 本地开发模式需要 |
| Redis | ❓ 未检查 | 本地开发模式需要 |
| Neo4j | ❓ 未检查 | 本地开发模式需要 |

---

## 建议启动方案

### 快速方案（推荐）
**安装 Docker Desktop，使用方式 A：**
1. 下载安装 [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. 在 Windows 上启用 WSL2 后端
3. 运行 `cd deploy && docker compose up -d --build`
4. 等待 5-10 分钟所有服务启动完成
5. 访问各个前端 URL

### 本地开发方案
**如果坚持本地开发模式：**
1. 安装 [Node.js 20+](https://nodejs.org/)
2. 在系统上启动数据库服务：
   - PostgreSQL (port 5432)
   - Redis (port 6379)
   - Neo4j (port 7687)
3. 修改 `deploy/.env` 中的数据库连接参数
4. 按上面的"前端启动"步骤启动各前端

---

## 外部服务配置

**可选服务**（缺失时会自动降级）：

| 服务 | 功能 | 默认端口 | 配置变量 |
|---|---|---|---|
| Dify | LLM/RAG 知识库 | 5001 | `DIFY_API_KEY` |
| FunASR | 语音识别 (ASR) | 10095 | `ASR_BASE_URL` |
| CosyVoice2 | 语音合成 (TTS) | 8001 | `TTS_BASE_URL` |

详见 [部署手册](docs/部署手册.md) 配置说明。

---

## 常见问题

**Q: 后端启动失败（数据库连接错误）**
A: PostgreSQL/Redis/Neo4j 未运行。要么：
- 使用 Docker 方式 A（自动启动）
- 或在本地手动启动这些数据库

**Q: 前端显示"无法连接到后端"**
A: 检查后端是否运行在 http://127.0.0.1:8000，查看浏览器控制台网络错误

**Q: 数字人不显示 / 没有声音**
A: 需要上传 VRM 模型和配置 TTS/ASR，见 [部署手册第七节](docs/部署手册.md#七数字人形象与音色配置)

---

## 项目架构

```
智游景行（完整架构）
├── 后端（已启动 ✅）
│   └── FastAPI Orchestrator @ http://127.0.0.1:8000
├── 前端
│   ├── 游客端 @ http://localhost:5173  [待启动]
│   ├── 管理后台 @ http://localhost:5174 [待启动]
│   └── 数据大屏 @ http://localhost:5175 [待启动]
└── 基础设施（未启动）
    ├── PostgreSQL (port 5432)
    ├── Redis (port 6379)
    ├── Neo4j (port 7474/7687)
    └── Nginx (反向代理)
```

---

## 下一步

1. **安装 Node.js** 并启动前端（或改用 Docker）
2. **配置数据库** 连接（本地模式）或等待 Docker 启动（Docker 模式）
3. **访问后端 API** 文档验证：http://127.0.0.1:8000/docs
4. **上传 VRM 模型** 至管理后台配置数字人

---

*此指南在项目启动时自动生成*

# 智游景行启动手册

本文用于本机演示、开发联调、微信小程序调试和问题排查。当前项目统一约定：**Orchestrator 后端固定使用 8010 端口**。

## 1. 启动前先确认

### 1.1 必备环境

| 环境 | 用途 | 建议版本 | 检查命令 |
|---|---|---|---|
| Docker Desktop | PostgreSQL、Redis、Neo4j、Dify 等容器服务 | 最新稳定版 | `docker version` |
| Docker Compose v2 | 启动 `deploy/docker-compose.yml` | 随 Docker Desktop 安装 | `docker compose version` |
| Python | 本地启动 Orchestrator | 3.11+ | `python --version` |
| Node.js / npm | 启动前端 Vite 服务 | Node.js 20+ | `node -v` / `npm -v` |
| 微信开发者工具 | 调试 `miniprogram-tourist` | 稳定版 | 手动打开 |

### 1.2 关键端口

| 端口 | 服务 | 注意事项 |
|---|---|---|
| 8010 | Orchestrator 后端 API | 全项目统一后端端口，不能被 LiveTalking 或旧进程占用 |
| 5173 | 整合游客端 `frontend-web` / 游客端 | 本机主要演示入口 |
| 5174 | 管理后台 | Docker 生产模式或单独开发启动时使用 |
| 5175 | 数据大屏 | Docker 生产模式或单独开发启动时使用 |
| 5432 | PostgreSQL | Docker 模式由容器提供 |
| 6379 | Redis | Docker 模式由容器提供 |
| 7474 / 7687 | Neo4j | 图数据库浏览器 / Bolt 连接 |
| 80 | Dify Nginx | `deploy/.env` 中 Docker 模式使用 `http://nginx/v1` |

端口被占用时，在 PowerShell 中查看：

```powershell
netstat -ano | findstr :8010
netstat -ano | findstr :5173
```

需要结束占用进程时：

```powershell
taskkill /F /PID <PID>
```

## 2. 推荐启动方式：Hybrid 本地演示模式

这是当前最适合本机演示的方式：基础设施走 Docker，后端和整合前端在本机开发模式运行。

### 2.1 一键脚本启动

在仓库根目录执行：

```powershell
.\start.bat
```

脚本会依次完成：

1. 检查 Python、npm、Docker 是否存在。
2. 清理 `8010` 和 `5173` 的残留监听进程。
3. 启动 Docker 基础服务。
4. 重启一次 `dify-nginx-1`，规避 Dify 容器 IP 缓存导致的 502。
5. 启动本地 Orchestrator：`http://localhost:8010`。
6. 启动整合前端 `frontend-web`：`http://localhost:5173`。
7. 自动打开浏览器。

### 2.2 手动启动步骤

如果脚本失败，按下面顺序手动启动，更容易定位问题。

1. 启动 Docker Desktop，等待 Docker 图标稳定。

2. 启动基础服务：

```powershell
cd d:\zhiyou-jingxing\deploy
docker compose up -d postgres redis neo4j
```

3. 如需 Dify，确认 Dify 栈也已启动：

```powershell
cd d:\zhiyou-jingxing\dify
docker compose up -d
docker restart dify-nginx-1
```

4. 启动后端：

```powershell
cd d:\zhiyou-jingxing\orchestrator
if (!(Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
python -m uvicorn app.main:app --host 0.0.0.0 --port 8010
```

5. 新开一个 PowerShell，启动整合前端：

```powershell
cd d:\zhiyou-jingxing\frontend-web
npm install
npm run dev
```

6. 访问：

```text
整合游客端：http://localhost:5173
后端 API：http://localhost:8010/docs
```

## 3. Docker 完整模式

完整模式会构建并启动 `orchestrator`、`frontend-tourist`、`frontend-admin`、`frontend-dashboard` 和基础设施。

```powershell
cd d:\zhiyou-jingxing\deploy
docker compose up -d --build
```

访问地址：

| 页面 | 地址 |
|---|---|
| 游客端 | http://localhost:5173 |
| 管理后台 | http://localhost:5174 |
| 数据大屏 | http://localhost:5175 |
| API 文档 | http://localhost:8010/docs |
| Neo4j | http://localhost:7474 |

注意：如果你正在用本地 Vite 启动 `frontend-web`，不要同时让 Docker 前端容器占用 5173。必要时停止 Docker 前端：

```powershell
docker stop zhiyou-jingxing-frontend-tourist-1 zhiyou-jingxing-frontend-admin-1 zhiyou-jingxing-frontend-dashboard-1
```

## 4. 微信小程序启动

小程序不能独立完成业务闭环，必须能访问 Orchestrator 后端。

### 4.1 编译小程序

```powershell
cd d:\zhiyou-jingxing\miniprogram-tourist
npm install
npm run build:mp-weixin
```

微信开发者工具导入目录：

```text
d:\zhiyou-jingxing\miniprogram-tourist\dist\build\mp-weixin
```

开发热更新模式：

```powershell
npm run dev:mp-weixin
```

开发模式产物在：

```text
d:\zhiyou-jingxing\miniprogram-tourist\dist\dev\mp-weixin
```

### 4.2 小程序网络注意事项

当前小程序 API 地址在 `miniprogram-tourist/src/api.js`：

```js
export const BASE_URL = 'http://127.0.0.1:8010/api'
```

在微信开发者工具里本机调试时可用 `127.0.0.1`。真机预览时，手机无法访问电脑自己的 `127.0.0.1`，需要改为电脑局域网 IP，例如：

```js
export const BASE_URL = 'http://192.168.x.x:8010/api'
```

同时要保证电脑和手机在同一网络，并在微信开发者工具里勾选“不校验合法域名、web-view、TLS 版本以及 HTTPS 证书”。

## 5. 配置文件说明

### 5.1 端口必须统一为 8010

这些位置都应保持 8010：

| 文件 | 应有配置 |
|---|---|
| `deploy/.env` | `APP_PORT=8010` |
| `deploy/.env.example` | `APP_PORT=8010` |
| `deploy/docker-compose.yml` | `8010:8010` |
| `orchestrator/Dockerfile` | `EXPOSE 8010`，`--port 8010` |
| `orchestrator/app/core/config.py` | `app_port: int = 8010` |
| `frontend-web/vite.config.js` | `target: 'http://127.0.0.1:8010'` |
| `frontend-tourist/vite.config.js` | `target: 'http://127.0.0.1:8010'` |
| `frontend-admin/vite.config.js` | `target: 'http://127.0.0.1:8010'` |
| `frontend-dashboard/vite.config.js` | `target: 'http://127.0.0.1:8010'` |
| `miniprogram-tourist/src/api.js` | `http://127.0.0.1:8010/api` |

如果页面出现 `ECONNREFUSED 127.0.0.1:8010`，优先检查后端是否真的在 8010 启动。

### 5.2 Docker 环境变量

Docker 模式主要读：

```text
deploy/.env
```

本地开发时，如果后端从 `orchestrator` 目录启动，代码默认会尝试读取：

```text
orchestrator/.env
```

如果没有 `orchestrator/.env`，会使用代码默认值或系统环境变量。为了少踩坑，建议本地开发也准备一份 `orchestrator/.env`，并确保端口和关键服务地址正确。

## 6. 启动后验证清单

按这个顺序检查，能最快定位问题：

### 6.1 容器状态

```powershell
docker ps
```

至少应看到：

```text
zhiyou-jingxing-postgres-1
zhiyou-jingxing-redis-1
zhiyou-jingxing-neo4j-1
```

如果用 Docker 完整模式，还应看到：

```text
zhiyou-jingxing-orchestrator-1
zhiyou-jingxing-frontend-tourist-1
zhiyou-jingxing-frontend-admin-1
zhiyou-jingxing-frontend-dashboard-1
```

### 6.2 后端是否可访问

浏览器打开：

```text
http://localhost:8010/docs
```

也可用 PowerShell：

```powershell
Invoke-WebRequest http://127.0.0.1:8010/docs -UseBasicParsing
```

### 6.3 前端是否可访问

浏览器打开：

```text
http://localhost:5173
```

如果页面能打开但提示 `API 异常（已用本地数据）`，说明前端活着，后端接口或后端依赖有问题。

### 6.4 路线规划接口

```powershell
Invoke-RestMethod http://127.0.0.1:8010/api/route/parks
```

正常应返回灵山胜境和留园。

## 7. 常见问题与排查路径

### 7.1 前端显示 `Request failed with status code 500`

先判断是“后端没起来”还是“后端内部报错”。

1. 打开 `http://localhost:8010/docs`。
2. 如果打不开，查端口和后端进程。
3. 如果能打开，查看后端日志。

本地后端日志就在启动后端的 PowerShell 窗口里。

Docker 后端日志：

```powershell
docker logs zhiyou-jingxing-orchestrator-1 --tail 100
```

重点看：数据库连接失败、Neo4j 连接失败、Dify 请求失败、Python Traceback。

### 7.2 前端控制台报 `ECONNREFUSED 127.0.0.1:8010`

含义：前端代理连不上后端。

排查顺序：

1. `netstat -ano | findstr :8010` 看 8010 是否有人监听。
2. `http://localhost:8010/docs` 是否能打开。
3. 确认后端启动命令带了 `--port 8010`。
4. 确认没有旧容器或旧进程占用 8010。

### 7.3 Docker 构建卡住或中途终端退出

`docker compose up -d --build` 会构建多个前端镜像，首次构建可能比较久。看到 `Building 92.2s` 不一定是失败。

建议：

```powershell
cd d:\zhiyou-jingxing\deploy
docker compose ps
docker compose logs orchestrator --tail 100
```

如果只是为了演示，不需要每次都 `--build`：

```powershell
docker compose up -d
```

只有修改了 Dockerfile、依赖或生产构建内容时才需要：

```powershell
docker compose up -d --build
```

### 7.4 PowerShell 中 `grep` / `head` 不存在

这是正常的，Windows PowerShell 没有这些 Linux 命令。替代写法：

```powershell
docker ps | Select-String orchestrator
docker logs zhiyou-jingxing-orchestrator-1 | Select-Object -Last 100
```

### 7.5 PowerShell 中 `curl` 弹出安全警告

PowerShell 的 `curl` 是 `Invoke-WebRequest` 别名。建议直接用：

```powershell
Invoke-WebRequest http://127.0.0.1:8010/docs -UseBasicParsing
Invoke-RestMethod http://127.0.0.1:8010/api/route/parks
```

### 7.6 Dify 页面 502 或后端调用 Dify 失败

先检查 Dify 容器：

```powershell
docker ps | Select-String dify
```

如果 `dify-api-1` 不健康，或页面 502：

```powershell
docker restart dify-api-1
docker restart dify-nginx-1
```

等待 `dify-api-1` 健康后再刷新。Docker 模式下 Orchestrator 通过 `http://nginx/v1` 访问 Dify，这要求 `orchestrator` 容器加入 `dify_default` 网络。

### 7.7 Neo4j 连接失败

路线规划有 JSON 降级逻辑，Neo4j 不可用时通常不影响基础路线规划演示。

仍需检查时：

```powershell
docker logs zhiyou-jingxing-neo4j-1 --tail 100
```

Neo4j 页面：

```text
http://localhost:7474
```

### 7.8 TTS 没声音

TTS 有降级链。`CosyVoice2` 不可用时，如果 `TTS_SECONDARY_PROVIDER=edge`，会尝试 Edge TTS。

排查：

1. 看后端日志是否有 TTS 请求失败。
2. 检查 `deploy/.env` 里的 `TTS_BASE_URL` 和 `TTS_SECONDARY_PROVIDER`。
3. 确认浏览器没有静音，页面允许播放音频。

### 7.9 小程序规划失败

常见原因：

1. Orchestrator 没启动，导致 `CONNECTION_REFUSED`。
2. 真机访问时仍使用 `127.0.0.1`。
3. 微信开发者工具未勾选“不校验合法域名”。
4. 修改源码后没有重新 `npm run build:mp-weixin`。

### 7.10 LiveTalking 和 Orchestrator 端口冲突

`livetalking/docker-compose.yml` 当前也映射了：

```yaml
ports:
  - "8010:8010"
```

这会和 Orchestrator 的 8010 冲突。演示主系统时不要同时启动 LiveTalking；如果必须启动，需要把 LiveTalking 改到其他端口，例如 `8020:8010`，并同步调整调用方配置。

## 8. 日志速查

### 8.1 Docker 服务日志

```powershell
docker logs zhiyou-jingxing-orchestrator-1 --tail 100
docker logs zhiyou-jingxing-postgres-1 --tail 100
docker logs zhiyou-jingxing-redis-1 --tail 100
docker logs zhiyou-jingxing-neo4j-1 --tail 100
docker logs dify-api-1 --tail 100
docker logs dify-nginx-1 --tail 100
```

### 8.2 Compose 状态

```powershell
cd d:\zhiyou-jingxing\deploy
docker compose ps
```

### 8.3 前端日志

Vite 前端日志在运行 `npm run dev` 的 PowerShell 窗口里。常见信息：

| 日志 | 含义 |
|---|---|
| `VITE ready` | 前端启动成功 |
| `http proxy error` | 前端可用，但代理后端失败 |
| `ECONNREFUSED 127.0.0.1:8010` | 后端未启动或端口错误 |

## 9. 停止与重启

### 9.1 停止本地后端和前端

直接关闭对应 PowerShell 窗口，或按 `Ctrl+C`。

### 9.2 停止 Docker 基础服务

```powershell
cd d:\zhiyou-jingxing\deploy
docker compose down
```

### 9.3 保留数据重启

```powershell
cd d:\zhiyou-jingxing\deploy
docker compose restart
```

### 9.4 清空数据重启

谨慎使用，会删除 PostgreSQL 和 Neo4j volume 数据：

```powershell
cd d:\zhiyou-jingxing\deploy
docker compose down -v
docker compose up -d --build
```

## 10. 演示前检查清单

演示前按下面顺序过一遍：

1. Docker Desktop 已启动。
2. `docker ps` 中基础容器正常运行。
3. `http://localhost:8010/docs` 可打开。
4. `http://localhost:5173` 可打开。
5. 首页没有 `API 异常` 红字。
6. 路线规划按钮可返回路线。
7. 对话接口能返回文本。
8. 数字人模型已在后台上传并设为默认。
9. 如果要演示语音，确认浏览器麦克风权限和 TTS 降级链可用。
10. 如果要演示小程序，提前确认使用的是正确编译产物，并且网络地址不是错误的 `127.0.0.1`。

## 11. 最快恢复流程

当系统状态乱了，按这个流程恢复：

```powershell
# 1. 停掉可能抢端口的前端容器
docker stop zhiyou-jingxing-frontend-tourist-1 zhiyou-jingxing-frontend-admin-1 zhiyou-jingxing-frontend-dashboard-1

# 2. 确认 8010/5173 无旧进程占用，必要时 taskkill
netstat -ano | findstr :8010
netstat -ano | findstr :5173

# 3. 启动基础设施
cd d:\zhiyou-jingxing\deploy
docker compose up -d postgres redis neo4j

# 4. 启动后端
cd d:\zhiyou-jingxing\orchestrator
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8010

# 5. 新开窗口启动前端
cd d:\zhiyou-jingxing\frontend-web
npm run dev
```

恢复后访问：

```text
http://localhost:5173
```

## 12. 不要踩的坑

1. 不要让 Orchestrator 和 LiveTalking 同时抢 `8010`。
2. 不要看到 Docker `Building` 时间长就立刻判断失败，先看 `docker compose ps`。
3. 不要在 Windows PowerShell 里直接照抄 `grep`、`head`，用 `Select-String` 和 `Select-Object -Last`。
4. 不要让小程序真机继续访问 `127.0.0.1`。
5. 不要改完小程序源码后忘记重新编译。
6. 不要把 Dify 的宿主机地址和 Docker 内网地址混用：容器内访问 Dify 用 `http://nginx/v1`，本机访问通常用 `http://localhost/v1`。
7. 不要在演示前临时清 volume，除非确定可以重新初始化数据。

更多部署细节见 [docs/部署手册.md](docs/部署手册.md)。

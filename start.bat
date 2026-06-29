@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================================
echo        智游景行 - 一键守护与启动脚本 (Hybrid 模式)
echo ========================================================
echo.

:: 1. 环境预检
echo [*] 检查运行环境...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请安装 Python 3.11+ 并添加到环境变量！
    pause
    exit /b 1
)

where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到 Node.js，请安装 Node.js 20+ 并添加到环境变量！
    pause
    exit /b 1
)
echo [OK] 基础环境就绪。
echo.

:: 2. 检测 Docker Desktop 是否已运行，否则自动启动
echo [*] 检测 Docker Desktop 状态...
docker info >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] Docker Desktop 未运行，正在自动启动...
    set "DOCKER_PATH="
    for %%p in (
        "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
        "%LocalAppData%\Programs\Docker\Docker\Docker Desktop.exe"
    ) do (
        if exist "%%~p" set "DOCKER_PATH=%%~p"
    )
    if defined DOCKER_PATH (
        start "" !DOCKER_PATH!
        echo [*] 等待 Docker 引擎就绪（最多 90 秒）...
        set DOCKER_WAIT=0
        :wait_docker
        timeout /t 3 /nobreak >nul
        docker info >nul 2>nul
        if %errorlevel% equ 0 goto docker_ready
        set /a DOCKER_WAIT+=3
        if !DOCKER_WAIT! geq 90 (
            echo [错误] Docker 引擎 90 秒内未就绪，请手动启动 Docker Desktop 后重试！
            pause
            exit /b 1
        )
        echo [*] 仍在等待... (!DOCKER_WAIT!s)
        goto wait_docker
        :docker_ready
        echo [OK] Docker 引擎已就绪！
    ) else (
        echo [错误] 未找到 Docker Desktop，请先安装！
        pause
        exit /b 1
    )
) else (
    echo [OK] Docker Desktop 已在运行。
)
echo.

:: 3. 同时设置 Docker Desktop 开机自启（写注册表，只执行一次也无妨）
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "DockerDesktop" >nul 2>nul
if %errorlevel% neq 0 (
    set "DOCKER_EXE="
    for %%p in (
        "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
        "%LocalAppData%\Programs\Docker\Docker\Docker Desktop.exe"
    ) do (
        if exist "%%~p" set "DOCKER_EXE=%%~p"
    )
    if defined DOCKER_EXE (
        reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "DockerDesktop" /t REG_SZ /d "!DOCKER_EXE!" /f >nul
        echo [OK] 已将 Docker Desktop 设为开机自启。
    )
)

:: 4. 清理可能残留的僵尸端口
echo [*] 清理残留端口 (8010, 5173)...
powershell -NoProfile -Command "$p = (Get-NetTCPConnection -LocalPort 8010 -State Listen -EA SilentlyContinue).OwningProcess; if ($p) { Stop-Process -Id $p -Force }" >nul 2>nul
echo [OK] 端口清理完毕。
echo.

:: 5. 启动底层依赖 (Docker Compose)
echo [*] 启动底层依赖 (Postgres, Redis, Neo4j)...
cd deploy
docker compose up -d
if %errorlevel% neq 0 (
    echo [错误] Docker Compose 启动失败！请检查 deploy/docker-compose.yml
    pause
    exit /b 1
)
cd ..
echo [OK] Docker 容器已启动。
echo.

:: 6. 等待 Postgres 就绪（最多 30 秒）
echo [*] 等待 Postgres 数据库就绪...
set PG_WAIT=0
:wait_pg
timeout /t 2 /nobreak >nul
docker compose -f deploy/docker-compose.yml exec -T postgres pg_isready -U zhiyou >nul 2>nul
if %errorlevel% equ 0 goto pg_ready
set /a PG_WAIT+=2
if !PG_WAIT! geq 30 (
    echo [!] Postgres 30秒内未就绪，继续启动（可能有延迟）
    goto pg_ready
)
echo [*] 等待数据库... (!PG_WAIT!s)
goto wait_pg
:pg_ready
echo [OK] 数据库已就绪！
echo.

:: 7. 拉起 Orchestrator (后端)
echo [*] 准备启动 Orchestrator 后端...
cd orchestrator
if not exist ".venv" (
    echo [!] 未发现 .venv 虚拟环境，正在创建并安装依赖...
    python -m venv .venv
    .venv\Scripts\python -m pip install -e .[dev]
)
echo [*] 正在后台启动 FastAPI 服务...
start "Orchestrator Backend" cmd /c ".venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8010"
cd ..

:: 等待后端就绪
echo [*] 等待后端 8010 端口就绪...
set BACK_WAIT=0
:wait_backend
timeout /t 1 /nobreak >nul
powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 8010 -State Listen -EA SilentlyContinue) { exit 0 } else { exit 1 }" >nul 2>nul
if %errorlevel% equ 0 goto backend_ready
set /a BACK_WAIT+=1
if !BACK_WAIT! geq 30 (
    echo [!] 后端启动超时，请检查日志
    goto backend_ready
)
goto wait_backend
:backend_ready
echo [OK] 后端已就绪！
echo.

:: 8. 拉起 Frontend-Web (前端游客端)
echo [*] 准备启动游客端前端...
cd frontend-web
if not exist "node_modules" (
    echo [!] 未发现 node_modules，正在安装前端依赖...
    call npm install
)
echo [*] 正在后台启动 Vite 开发服务器...
start "Frontend Web" cmd /c "npm run dev"
cd ..

:: 9. 完成
echo.
echo ========================================================
echo   全部服务启动成功！
echo   游客端页面即将自动在浏览器打开...
echo   (如果未能自动打开，请手动访问 http://localhost:5173)
echo ========================================================
echo.
timeout /t 3 /nobreak >nul
start http://localhost:5173

pause

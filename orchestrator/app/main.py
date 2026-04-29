"""FastAPI 入口。"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import admin, analytics, chat, route
from app.core.config import settings
from app.core.database import init_db
from app.core.logger import logger
from app.services.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("启动 orchestrator (env={})", settings.app_env)
    await init_db()
    start_scheduler()
    yield
    logger.info("orchestrator 退出")


app = FastAPI(title="智游景行 · 编排层", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(route.router)
app.include_router(analytics.router)
app.include_router(admin.router)

# 静态资产托管：VRM 模型 / 动作 / 上传等
_DATA_ROOT = Path(__file__).resolve().parents[1] / "data"
_AVATARS_VRM_DIR = _DATA_ROOT / "avatars_vrm"
_AVATARS_VRM_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static/avatars", StaticFiles(directory=str(_AVATARS_VRM_DIR)), name="avatars")

# TTS 音频缓存（B13）：避免 base64 dataURL 内存膨胀
_TTS_CACHE_DIR = _DATA_ROOT / "tts_cache"
_TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static/tts", StaticFiles(directory=str(_TTS_CACHE_DIR)), name="tts")


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}

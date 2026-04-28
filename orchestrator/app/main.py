"""FastAPI 入口。"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}

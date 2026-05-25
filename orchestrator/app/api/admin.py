"""管理后台 API：登录 + 形象管理 + 知识库透传 Dify。"""
from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.logger import logger
from app.core.security import create_access_token, verify_admin
from app.models import Avatar, Suggestion
from app.schemas import AvatarIn, AvatarOut, LoginRequest, SuggestionOut, SuggestionStatusUpdate, TokenResponse
from app.services.dify_client import dify_client

router = APIRouter(prefix="/api/admin", tags=["admin"])

# 数字人 VRM 资产根目录（与 main.py StaticFiles 挂载点对应）
_AVATARS_VRM_DIR = Path(__file__).resolve().parents[2] / "data" / "avatars_vrm"
_AVATARS_VRM_DIR.mkdir(parents=True, exist_ok=True)
# 单个 .vrm 上限：50 MB
_MAX_VRM_BYTES = 50 * 1024 * 1024


def _avatar_dir(code: str) -> Path:
    """安全解析 avatar 子目录，防止路径穿越。"""
    if not code or "/" in code or "\\" in code or code.startswith(".") or len(code) > 64:
        raise HTTPException(400, "invalid avatar code")
    base = _AVATARS_VRM_DIR.resolve()
    target = (base / code).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise HTTPException(400, "invalid avatar code")
    if target == base:
        raise HTTPException(400, "invalid avatar code")
    return target


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    if req.username != settings.admin_username or req.password != settings.admin_password:
        raise HTTPException(401, "invalid credentials")
    return TokenResponse(access_token=create_access_token(req.username))


# ---- 数字人形象 ----

@router.get("/avatars", response_model=List[AvatarOut])
async def list_avatars(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Avatar).order_by(Avatar.id))).scalars().all()
    return rows


@router.post("/avatars", response_model=AvatarOut, dependencies=[Depends(verify_admin)])
async def create_avatar(payload: AvatarIn, db: AsyncSession = Depends(get_db)):
    if payload.is_default:
        for a in (await db.execute(select(Avatar))).scalars():
            a.is_default = False
    obj = Avatar(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/avatars/{avatar_id}", dependencies=[Depends(verify_admin)])
async def delete_avatar(avatar_id: int, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Avatar, avatar_id)
    if not obj:
        raise HTTPException(404, "not found")
    await db.delete(obj)
    await db.commit()
    return {"ok": True}


@router.post("/avatars/{code}/upload-vrm", dependencies=[Depends(verify_admin)])
async def upload_vrm(code: str, file: UploadFile = File(...),
                     db: AsyncSession = Depends(get_db)):
    """上传 VRM 模型文件，保存到 ``data/avatars_vrm/{code}/model.vrm``，
    并把 ``model_url`` 回写到对应 Avatar 记录。"""
    if not file.filename or not file.filename.lower().endswith(".vrm"):
        raise HTTPException(400, "only .vrm files are accepted")
    target_dir = _avatar_dir(code)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "model.vrm"

    size = 0
    # 同步文件 IO 放到线程池，避免阻塞事件循环
    f = await asyncio.to_thread(target.open, "wb")
    try:
        while True:
            chunk = await file.read(1 << 20)  # 1 MiB
            if not chunk:
                break
            size += len(chunk)
            if size > _MAX_VRM_BYTES:
                await asyncio.to_thread(f.close)
                target.unlink(missing_ok=True)
                raise HTTPException(413, "vrm file too large (>50MB)")
            await asyncio.to_thread(f.write, chunk)
    finally:
        await asyncio.to_thread(f.close)
    logger.info("VRM 上传成功 code={} bytes={}", code, size)

    model_url = f"/static/avatars/{code}/model.vrm"
    avatar = (await db.execute(select(Avatar).where(Avatar.code == code))).scalar_one_or_none()
    if avatar is not None:
        avatar.model_type = "vrm"
        avatar.model_url = model_url
        await db.commit()
    return {"ok": True, "model_url": model_url, "size": size}


@router.post("/avatars/{code}/upload-motion", dependencies=[Depends(verify_admin)])
async def upload_motion(code: str, name: str, file: UploadFile = File(...)):
    """上传 ``.vrma`` 动作文件到 ``motions/{name}.vrma``。"""
    safe_name = name.strip().lower()
    if not safe_name or not safe_name.replace("_", "").isalnum() or len(safe_name) > 32:
        raise HTTPException(400, "invalid motion name (a-z0-9_, max 32)")
    if not file.filename or not file.filename.lower().endswith(".vrma"):
        raise HTTPException(400, "only .vrma files are accepted")
    motion_dir = _avatar_dir(code) / "motions"
    motion_dir.mkdir(parents=True, exist_ok=True)
    target = motion_dir / f"{safe_name}.vrma"
    data = await file.read()
    if len(data) > _MAX_VRM_BYTES:
        raise HTTPException(413, "motion file too large (>50MB)")
    await asyncio.to_thread(target.write_bytes, data)
    return {"ok": True, "motion_url": f"/static/avatars/{code}/motions/{safe_name}.vrma"}


# ---- 知识库（透传 Dify Datasets API）----

@router.post("/knowledge/upload", dependencies=[Depends(verify_admin)])
async def upload_knowledge(file: UploadFile = File(...)):
    """落盘到 ``data/uploads`` 留底，并尽力调用 Dify Datasets API 入库。

    - 若未配置 ``DIFY_DATASET_ID`` / ``DIFY_DATASET_API_KEY``，仅落盘并返回 ``synced=false``。
    - 调用失败不影响落盘成功，返回 ``synced=false`` 与 ``error``。
    """
    if not file.filename:
        raise HTTPException(400, "missing filename")
    target = Path(__file__).resolve().parents[2] / "data" / "uploads"
    target.mkdir(parents=True, exist_ok=True)
    fp = target / file.filename
    content = await file.read()
    await asyncio.to_thread(fp.write_bytes, content)

    synced = False
    error: str | None = None
    document_id: str | None = None
    try:
        resp = await dify_client.upload_dataset_document(
            filename=file.filename,
            content=content,
            content_type=file.content_type or "application/octet-stream",
        )
        synced = True
        document_id = (resp.get("document") or {}).get("id")
        logger.info("Dify 知识库同步成功 file={} doc_id={}", file.filename, document_id)
    except RuntimeError as exc:
        error = str(exc)
        logger.warning("Dify 知识库未配置，仅落盘：{}", exc)
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
        logger.exception("Dify 知识库同步失败：{}", exc)

    return {"ok": True, "saved_as": fp.name, "synced": synced,
            "document_id": document_id, "error": error}


@router.get("/knowledge/list", dependencies=[Depends(verify_admin)])
async def list_knowledge():
    """返回已上传知识库文件列表（按修改时间倒序）。"""
    target = Path(__file__).resolve().parents[2] / "data" / "uploads"
    if not target.exists():
        return []
    files = []
    for fp in sorted(target.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True):
        if fp.is_file():
            stat = fp.stat()
            files.append({
                "name": fp.name,
                "size": stat.st_size,
                "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
    return files


# ---- 服务建议状态管理 ----

@router.patch("/suggestions/{suggestion_id}/status",
              response_model=SuggestionOut,
              dependencies=[Depends(verify_admin)])
async def update_suggestion_status(suggestion_id: int,
                                   payload: SuggestionStatusUpdate,
                                   db: AsyncSession = Depends(get_db)):
    """更新建议状态：open / resolved / ignored。"""
    obj = await db.get(Suggestion, suggestion_id)
    if not obj:
        raise HTTPException(404, "suggestion not found")
    obj.status = payload.status
    await db.commit()
    await db.refresh(obj)
    return obj

"""管理后台 API：登录 + 形象管理 + 知识库透传 Dify。"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, verify_admin
from app.models import Avatar
from app.schemas import AvatarIn, AvatarOut, LoginRequest, TokenResponse

router = APIRouter(prefix="/api/admin", tags=["admin"])


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


# ---- 知识库（透传 Dify Datasets API）----

@router.post("/knowledge/upload", dependencies=[Depends(verify_admin)])
async def upload_knowledge(file: UploadFile = File(...)):
    """简化：把文件保存到 data/uploads；真正入 Dify 由 docs/部署手册.md 中说明的 CLI 完成。
    生产可调用 Dify Datasets API：POST /datasets/{id}/document/create_by_file。
    """
    from pathlib import Path
    target = Path(__file__).resolve().parents[2] / "data" / "uploads"
    target.mkdir(parents=True, exist_ok=True)
    fp = target / file.filename
    fp.write_bytes(await file.read())
    return {"ok": True, "saved_as": str(fp.name)}

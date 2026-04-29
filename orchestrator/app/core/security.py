"""极简 JWT 鉴权，仅供 MVP 单一管理员使用。"""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/login", auto_error=False)


def create_access_token(subject: str, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def verify_admin(token: Optional[str] = Depends(oauth2_scheme)) -> str:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing token")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        if sub != settings.admin_username:
            raise HTTPException(status_code=403, detail="forbidden")
        return sub
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc


# ---- 轻量 HMAC 签名：为游客端 WebSocket 防滥用用 ----

def sign_session(session_id: str) -> str:
    """为 session_id 产出 16 位 hex 签名。"""
    if not session_id:
        return ""
    mac = hmac.new(settings.secret_key.encode("utf-8"),
                   session_id.encode("utf-8"), hashlib.sha256)
    return mac.hexdigest()[:16]


def verify_session_sig(session_id: str, sig: Optional[str]) -> bool:
    if not session_id or not sig:
        return False
    expected = sign_session(session_id)
    return hmac.compare_digest(expected, sig)

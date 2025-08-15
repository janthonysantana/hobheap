from __future__ import annotations

import datetime as dt
import secrets
from typing import Optional

import jwt
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.db import get_db
from ..models.entities import User

ALGORITHM = "HS256"
JWT_SECRET = "dev-secret-change-me"  # deterministic for tests; replace with env secret

security = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = creds.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError as e:
        logging.error("JWT decode error: %s", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    sub = payload.get("sub")
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token payload")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def create_access_token(user_id: int) -> str:
    now = dt.datetime.now(dt.UTC)
    expire = now + dt.timedelta(days=settings.access_token_expire_days)
    to_encode = {"sub": str(user_id), "exp": int(expire.timestamp()), "iat": int(now.timestamp())}
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)

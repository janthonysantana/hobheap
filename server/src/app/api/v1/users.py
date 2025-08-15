from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db import get_db
from ...models.entities import User
from ...services.auth import create_access_token, get_current_user
from ...repositories.otps import otp_repository
from ...schemas.base import OTPIssueOut
from ...services.rate_limit import check_and_increment, RateLimitExceeded, reset as reset_rl
from ...schemas.base import UserCreate, UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=payload.email, phone=payload.phone)
    db.add(user)
    await db.flush()  # assign id
    return user


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/login", summary="Issue access token (mock OTP flow)")
async def login(email: str, db: AsyncSession = Depends(get_db)):
    key = f"login:{email.lower()}"
    try:
        check_and_increment(key)
    except RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    user = await db.scalar(select(User).where(User.email == email))
    if not user:
        raise HTTPException(status_code=400, detail="User not registered")
    token = create_access_token(user.id)
    reset_rl(key)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/otp/request", response_model=OTPIssueOut)
async def request_otp(email: str, db: AsyncSession = Depends(get_db)):
    key = f"otp_req:{email.lower()}"
    try:
        check_and_increment(key)
    except RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    user = await db.scalar(select(User).where(User.email == email))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    otp = await otp_repository.issue(db, user.id)
    # In real system: send email/SMS. Mask destination for response.
    masked = email[:2] + "***" + email.split("@")[-1]
    return OTPIssueOut(user_id=user.id, masked_destination=masked, sent=True)


@router.post("/otp/verify")
async def verify_otp(email: str, code: str, db: AsyncSession = Depends(get_db)):
    key = f"otp_verify:{email.lower()}"
    try:
        check_and_increment(key)
    except RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    user = await db.scalar(select(User).where(User.email == email))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    ok = await otp_repository.validate(db, user.id, code)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    token = create_access_token(user.id)
    reset_rl(key)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/", response_model=list[UserOut])
async def list_users(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.scalars(select(User).limit(limit).offset(offset))
    return result.all()

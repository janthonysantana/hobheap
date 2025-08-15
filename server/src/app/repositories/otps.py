from __future__ import annotations
import datetime as dt
import secrets
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from ..models.entities import OTP

class OTPRepository:
    CODE_LENGTH = 6

    def _generate_code(self) -> str:
        return ''.join(secrets.choice('0123456789') for _ in range(self.CODE_LENGTH))

    async def issue(self, db: AsyncSession, user_id: int, ttl_minutes: int = 10) -> OTP:
        code = self._generate_code()
        expires_at = dt.datetime.now(dt.UTC) + dt.timedelta(minutes=ttl_minutes)
        otp = OTP(user_id=user_id, code=code, expires_at=expires_at)
        db.add(otp)
        await db.flush()
        return otp

    async def validate(self, db: AsyncSession, user_id: int, code: str) -> bool:
        otp = await db.scalar(
            select(OTP).where(
                OTP.user_id == user_id,
                OTP.code == code,
                OTP.consumed == False,  # noqa: E712
                OTP.expires_at > dt.datetime.now(dt.UTC),
            )
        )
        if not otp:
            return False
        otp.consumed = True
        return True

    async def cleanup(self, db: AsyncSession):
        await db.execute(delete(OTP).where(OTP.expires_at < dt.datetime.now(dt.UTC)))


otp_repository = OTPRepository()

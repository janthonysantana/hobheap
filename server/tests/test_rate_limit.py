import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.anyio
async def test_rate_limit_login_invalid_email():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Attempt login with unknown email to trigger failures
        for _ in range(3):
            r = await client.post("/api/v1/users/login", params={"email": "no_user@example.com"})
            assert r.status_code == 400
        r_block = await client.post("/api/v1/users/login", params={"email": "no_user@example.com"})
        assert r_block.status_code == 429


@pytest.mark.anyio
async def test_rate_limit_otp_request():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # create user
        await client.post("/api/v1/users/", json={"email": "otp@example.com"})
        for _ in range(3):
            r = await client.post("/api/v1/users/otp/request", params={"email": "otp@example.com"})
            assert r.status_code == 200
        r_block = await client.post("/api/v1/users/otp/request", params={"email": "otp@example.com"})
        assert r_block.status_code == 429

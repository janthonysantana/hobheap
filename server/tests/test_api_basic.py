import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app as fastapi_app
from app.core.db import Base, engine  # noqa: F401  (import kept if needed later)


@pytest.mark.anyio
async def test_user_card_document_flow():
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # create user
        resp = await client.post("/api/v1/users/", json={"email": "a@example.com"})
        assert resp.status_code == 201
        user = resp.json()
        # login
        token_resp = await client.post("/api/v1/users/login", params={"email": user["email"]})
        assert token_resp.status_code == 200
        token = token_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        # create card
        card_resp = await client.post("/api/v1/cards/", json={"content_md": "# Hello"}, headers=headers)
        assert card_resp.status_code == 201, card_resp.text
        card_id = card_resp.json()["id"]
        # create document
        doc_resp = await client.post("/api/v1/documents/", json={"title": "Doc1"}, headers=headers)
        assert doc_resp.status_code == 201
        doc_id = doc_resp.json()["id"]
        # add card to document
        add_resp = await client.post(
            f"/api/v1/documents/{doc_id}/cards", json={"card_id": card_id, "row": 0, "col": 0}, headers=headers
        )
        assert add_resp.status_code == 201, add_resp.text
        # list docs
        list_docs = await client.get("/api/v1/documents/", headers=headers)
        assert list_docs.status_code == 200
        assert len(list_docs.json()) == 1
        # soft delete card
        del_resp = await client.delete(f"/api/v1/cards/{card_id}", headers=headers)
        assert del_resp.status_code == 204
        # get deleted card should 404
        get_deleted = await client.get(f"/api/v1/cards/{card_id}", headers=headers)
        assert get_deleted.status_code == 404

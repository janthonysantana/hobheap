import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.anyio
async def test_tag_assignment_and_filtering():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # create user
        resp = await client.post('/api/v1/users/', json={'email': 't1@example.com'})
        assert resp.status_code == 201
        user = resp.json()
        # login to obtain token
        login = await client.post('/api/v1/users/login', params={'email': user['email']})
        assert login.status_code == 200, login.text
        token = login.json()['access_token']
        headers={'Authorization': f'Bearer {token}'}

        # create card
        resp = await client.post('/api/v1/cards/', json={'content_md': '# Card1'}, headers=headers)
        assert resp.status_code == 201, resp.text
        card = resp.json()

        # assign tags
        resp = await client.post('/api/v1/tags/assign', json={'card_id': card['id'], 'tags': ['alpha','beta']}, headers=headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert len(data['tags']) == 2
        names = sorted([t['name'] for t in data['tags']])
        assert names == ['alpha','beta']

        # filter cards by tag
        resp = await client.get('/api/v1/cards/?tag=alpha', headers=headers)
        assert resp.status_code == 200
        cards = resp.json()
        assert len(cards) == 1
        assert cards[0]['id'] == card['id']

        # add second card with overlapping tag
        resp = await client.post('/api/v1/cards/', json={'content_md': '# Card2'}, headers=headers)
        assert resp.status_code == 201
        card2 = resp.json()
        await client.post('/api/v1/tags/assign', json={'card_id': card2['id'], 'tags': ['beta','gamma']}, headers=headers)

        # filter by beta (should return both)
        resp = await client.get('/api/v1/cards/?tag=beta', headers=headers)
        cards = resp.json()
        ids = sorted([c['id'] for c in cards])
        assert ids == sorted([card['id'], card2['id']])

        # filter by gamma (single)
        resp = await client.get('/api/v1/cards/?tag=gamma', headers=headers)
        cards = resp.json()
        assert len(cards) == 1 and cards[0]['id'] == card2['id']

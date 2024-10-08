import pytest

pytestmark = pytest.mark.asyncio


async def test_index(client):
    response = await client.get("/")
    assert response.status_code == 307

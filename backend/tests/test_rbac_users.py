import pytest
from httpx import AsyncClient

from .conftest import login, auth_headers

pytestmark = pytest.mark.anyio


async def test_manager_can_only_create_agents(client: AsyncClient):
    manager_token = await login(client, "manager1", "Passw0rd!")

    r = await client.post(
        "/users",
        headers=auth_headers(manager_token),
        json={"username": "newadmin", "password": "Passw0rd!", "role": "admin", "email": None},
    )
    assert r.status_code in (401, 403), r.text

    r2 = await client.post(
        "/users",
        headers=auth_headers(manager_token),
        json={"username": "newagent1", "password": "Passw0rd!", "role": "agent", "email": None},
    )
    assert r2.status_code in (200, 201), r2.text

    body = r2.json()
    assert body.get("ok") is True
    assert body["data"]["role"] == "agent"
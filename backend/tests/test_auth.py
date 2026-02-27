import pytest
from httpx import AsyncClient

from .conftest import login, auth_headers

pytestmark = pytest.mark.anyio


async def test_login_wrong_password_returns_401_or_400(client: AsyncClient):
    resp = await client.post(
        "/auth/login",
        json={"username": "admin1", "password": "WRONG_PASSWORD"},
    )
    assert resp.status_code in (400, 401), resp.text


async def test_login_success_with_seeded_admin(client: AsyncClient):
    token = await login(client, "admin1", "Passw0rd!")
    assert isinstance(token, str) and len(token) > 20

    # Sanity-check: token works on a protected endpoint
    resp = await client.get("/users", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text


async def test_token_endpoint_is_optional(client: AsyncClient):
    """
    Your project may use /auth/login instead of /token (OAuth2PasswordRequestForm).
    So /token might not exist. This test ensures either behavior is acceptable.
    """
    resp = await client.post("/token", data={"username": "admin1", "password": "Passw0rd!"})
    assert resp.status_code in (200, 404), resp.text
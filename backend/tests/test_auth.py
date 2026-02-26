import os
import pytest

from .conftest import login, auth_headers


@pytest.mark.anyio
async def test_login_wrong_password_returns_401_or_400(client):
    # We don't assume a user exists for this test; it should fail cleanly.
    resp = await client.post(
    "/auth/login",
    json={"username": "not-a-real-user@example.com", "password": "wrong"},
)
    # Some apps use 401, some use 400; accept both.
    assert resp.status_code in (400, 401), resp.text


@pytest.mark.anyio
async def test_login_success_if_seeded_user_exists(client):
    """
    This test is optional until you have seed users in your test DB.
    Set env vars to enable it:
      TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD
    """
    email = os.getenv("TEST_ADMIN_EMAIL")
    password = os.getenv("TEST_ADMIN_PASSWORD")

    if not email or not password:
        pytest.skip("Set TEST_ADMIN_EMAIL and TEST_ADMIN_PASSWORD to run this test.")

    token = await login(client, email, password)
    assert isinstance(token, str) and len(token) > 20

    headers = auth_headers(token)

    # Smoke check: call something protected (adjust if your route differs)
    # Use a route that requires auth but not special role if possible.
    resp = await client.get("/users", headers=headers)
    assert resp.status_code in (200, 403), resp.text  # 200 if admin/manager, 403 if not enough role


@pytest.mark.anyio
async def test_token_endpoint_works_if_exposed(client):
    """
    If you use OAuth2 compatible /token, this verifies it responds correctly
    when given bad creds (should be 400/401, not 500).
    """
    resp = await client.post(
        "/token",
        data={"username": "nope@example.com", "password": "nope"},
    )
    # If /token doesn't exist, 404 is acceptable; otherwise must fail cleanly.
    assert resp.status_code in (404, 400, 401), resp.text
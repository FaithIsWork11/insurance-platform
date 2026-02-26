import sys
from pathlib import Path

# Ensure backend/ is importable so `import app` works
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import pytest
import httpx

from app.main import app
from app.db import SessionLocal
from app.models.user import User

# ⚠️ Adjust this import if your hash function lives elsewhere
from app.core.passwords import hash_password
# If your project instead uses:
# from app.core.security import get_password_hash
# then replace hash_password(...) below with get_password_hash(...)


# -------------------------------------------------------------------
# Async test client
# -------------------------------------------------------------------
@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# -------------------------------------------------------------------
# Deterministic seeding
# -------------------------------------------------------------------
def seed_test_data(db):
    """
    Deterministic seed for RBAC tests.

    - Always ensure admin1/manager1/agent1/agent2 exist with Passw0rd!
    - Delete any leftover users created by tests (newagent1/newadmin) so reruns don't fail.
    """

    # Delete only known test usernames (safe + deterministic)
    usernames_to_reset = ["admin1", "manager1", "agent1", "agent2", "newagent1", "newadmin"]
    db.query(User).filter(User.username.in_(usernames_to_reset)).delete(synchronize_session=False)
    db.commit()

    # Recreate required fixed users
    db.add_all(
        [
            User(
                username="admin1",
                role="admin",
                email=None,
                is_active=True,
                password_hash=hash_password("Passw0rd!"),
            ),
            User(
                username="manager1",
                role="manager",
                email=None,
                is_active=True,
                password_hash=hash_password("Passw0rd!"),
            ),
            User(
                username="agent1",
                role="agent",
                email=None,
                is_active=True,
                password_hash=hash_password("Passw0rd!"),
            ),
            User(
                username="agent2",
                role="agent",
                email=None,
                is_active=True,
                password_hash=hash_password("Passw0rd!"),
            ),
        ]
    )
    db.commit()


@pytest.fixture(autouse=True)
def seed_users():
    """
    Runs before EVERY test automatically.
    Guarantees admin1/manager1/agent1/agent2 exist with known password.
    """
    db = SessionLocal()
    try:
        seed_test_data(db)
        yield
    finally:
        db.close()


# -------------------------------------------------------------------
# Auth helpers
# -------------------------------------------------------------------
async def login(client: httpx.AsyncClient, username: str, password: str) -> str:
    resp = await client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )

    if resp.status_code == 404:
        # Fallback if using OAuth2PasswordRequestForm
        resp = await client.post(
            "/token",
            data={"username": username, "password": password},
        )

    assert resp.status_code == 200, resp.text

    # If your API wraps data like: {"ok": true, "data": {...}}
    body = resp.json()
    if "access_token" in body:
        return body["access_token"]
    if "data" in body and "access_token" in body["data"]:
        return body["data"]["access_token"]

    raise AssertionError(f"Login response missing access_token: {body}")


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
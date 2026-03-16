import sys
from pathlib import Path

import httpx
import pytest
import pytest_asyncio

# Ensure backend/ is importable so `import app` works
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.core.passwords import hash_password  # noqa: E402


@pytest_asyncio.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def seed_test_data(db):
    """
    Deterministic seed for RBAC tests.
    - Ensure admin1/manager1/agent1/agent2 exist with Passw0rd!
    - Delete known test users so reruns don't fail.
    """
    usernames_to_reset = ["admin1", "manager1", "agent1", "agent2", "newagent1", "newadmin"]
    db.query(User).filter(User.username.in_(usernames_to_reset)).delete(synchronize_session=False)
    db.commit()

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
    db = SessionLocal()
    try:
        seed_test_data(db)
        yield
    finally:
        db.close()


async def login(client: httpx.AsyncClient, username: str, password: str) -> str:
    resp = await client.post("/auth/login", json={"username": username, "password": password})

    if resp.status_code == 404:
        resp = await client.post("/token", data={"username": username, "password": password})

    assert resp.status_code == 200, resp.text

    body = resp.json()
    if "access_token" in body:
        return body["access_token"]
    if "data" in body and "access_token" in body["data"]:
        return body["data"]["access_token"]

    raise AssertionError(f"Login response missing access_token: {body}")


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
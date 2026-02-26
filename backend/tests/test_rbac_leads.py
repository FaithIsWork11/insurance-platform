import pytest
from httpx import AsyncClient

from .conftest import login, auth_headers

pytestmark = pytest.mark.anyio


async def test_agent_sees_only_assigned_leads(client: AsyncClient):
    agent_token = await login(client, "agent1", "Passw0rd!")
    admin_token = await login(client, "admin1", "Passw0rd!")

    lead = {
        "first_name": "Test",
        "last_name": "Lead",
        "phone": "5551112222",
        "email": None,
        "zip_code": "33311",
        "state": "FL",
        "coverage_type": "AUTO",
        "source": "TEST",
    }

    r_create = await client.post("/leads", headers=auth_headers(agent_token), json=lead)
    assert r_create.status_code in (200, 201), r_create.text
    lead_id = r_create.json()["data"]["id"]

    r_get = await client.get(f"/leads/{lead_id}", headers=auth_headers(agent_token))
    assert r_get.status_code == 200, r_get.text

    r_admin_get = await client.get(f"/leads/{lead_id}", headers=auth_headers(admin_token))
    assert r_admin_get.status_code == 200, r_admin_get.text


async def test_agent_cannot_view_unassigned_lead(client: AsyncClient):
    agent1_token = await login(client, "agent1", "Passw0rd!")
    agent2_token = await login(client, "agent2", "Passw0rd!")

    lead = {
        "first_name": "Hidden",
        "last_name": "Lead",
        "phone": "5553334444",
        "email": None,
        "zip_code": "33311",
        "state": "FL",
        "coverage_type": "AUTO",
        "source": "TEST",
    }
    r_create = await client.post("/leads", headers=auth_headers(agent1_token), json=lead)
    assert r_create.status_code in (200, 201), r_create.text
    lead_id = r_create.json()["data"]["id"]

    r_get = await client.get(f"/leads/{lead_id}", headers=auth_headers(agent2_token))
    assert r_get.status_code in (401, 403), r_get.text  # depending on your auth/forbidden handling
import pytest

from app.db import SessionLocal
from app.models.user import User


@pytest.mark.asyncio
async def test_admin_user_and_lead_flow(client):
    # login as admin
    admin_login = await client.post(
        "/auth/login",
        json={"username": "admin1", "password": "Passw0rd!"},
    )
    assert admin_login.status_code == 200, admin_login.text
    admin_body = admin_login.json()
    admin_token = admin_body.get("access_token") or admin_body["data"]["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # create agent user
    create_agent = await client.post(
        "/users",
        json={
            "username": "newagent1",
            "email": "newagent1@example.com",
            "password": "Passw0rd!",
            "role": "agent",
        },
        headers=admin_headers,
    )
    assert create_agent.status_code in (200, 201), create_agent.text
    agent_body = create_agent.json()
    agent_data = agent_body.get("data", agent_body)
    agent_id = agent_data["id"]

    # login as new agent
    agent_login = await client.post(
        "/auth/login",
        json={"username": "newagent1", "password": "Passw0rd!"},
    )
    assert agent_login.status_code == 200, agent_login.text
    agent_login_body = agent_login.json()
    agent_token = agent_login_body.get("access_token") or agent_login_body["data"]["access_token"]
    agent_headers = {"Authorization": f"Bearer {agent_token}"}

    # create lead as agent
    create_lead = await client.post(
    "/leads",
    json={
        "first_name": "John",
        "last_name": "Customer",
        "phone": "9545551212",
        "email": "johncustomer@example.com",
        "zip_code": "33309",
        "source": "website",
    },
    headers=agent_headers,
)
    assert create_lead.status_code in (200, 201), create_lead.text
    lead_body = create_lead.json()
    lead_data = lead_body.get("data", lead_body)
    lead_id = lead_data["id"]

    # get lead as same agent
    get_lead = await client.get(f"/leads/{lead_id}", headers=agent_headers)
    assert get_lead.status_code == 200, get_lead.text

    # update lead status
    update_lead = await client.patch(
        f"/leads/{lead_id}",
        json={"status": "CONTACTED"},
        headers=agent_headers,
    )
    assert update_lead.status_code == 200, update_lead.text

    # disable user as admin
    disable_user = await client.patch(
        f"/users/{agent_id}/disable",
        headers=admin_headers,
    )
    assert disable_user.status_code == 200, disable_user.text

    # enable user as admin
    enable_user = await client.patch(
        f"/users/{agent_id}/enable",
        headers=admin_headers,
    )
    assert enable_user.status_code == 200, enable_user.text

    # soft delete lead as admin
    delete_lead = await client.delete(
        f"/leads/{lead_id}",
        headers=admin_headers,
    )
    assert delete_lead.status_code == 200, delete_lead.text

    # restore lead as admin
    restore_lead = await client.post(
        f"/leads/{lead_id}/restore",
        headers=admin_headers,
    )
    assert restore_lead.status_code == 200, restore_lead.text
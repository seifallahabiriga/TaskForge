"""
Task lifecycle tests.

Covers: task creation → DB row exists, status endpoint, ownership enforcement,
and the end-to-end inference flow (submit → poll → SUCCESS → result).

The E2E test is marked with a custom marker so it can be skipped in fast
feedback loops (it's slow — it waits for Celery to process the job):

    pytest -m "not e2e"   # skip slow tests
    pytest -m e2e          # run only E2E tests
"""
import asyncio
import pytest
from uuid import UUID


@pytest.mark.asyncio
async def test_create_task_returns_201(client, auth_headers):
    response = await client.post(
        "/tasks/",
        json={
            "task_type": "INFERENCE",
            "name": "Explain async/await",
            "input_payload": {"prompt": "Explain async/await in Python in one sentence."},
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    UUID(data["id"])
    assert data["status"] == "PENDING"
    assert data["task_type"] == "INFERENCE"


@pytest.mark.asyncio
async def test_create_task_requires_auth(client):
    response = await client.post(
        "/tasks/",
        json={"task_type": "INFERENCE", "name": "Hello", "input_payload": {"prompt": "hello"}},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_task_status(client, auth_headers):
    create = await client.post(
        "/tasks/",
        json={"task_type": "INFERENCE", "name": "Math", "input_payload": {"prompt": "What is 2+2?"}},
        headers=auth_headers,
    )
    task_id = create.json()["id"]
    response = await client.get(f"/tasks/{task_id}/status", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] in {"PENDING", "QUEUED", "RUNNING", "SUCCESS", "FAILED", "RETRYING"}


@pytest.mark.asyncio
async def test_get_task_ownership_enforced(client, auth_headers):
    create = await client.post(
        "/tasks/",
        json={"task_type": "INFERENCE", "name": "Secret", "input_payload": {"prompt": "Secret task."}},
        headers=auth_headers,
    )
    task_id = create.json()["id"]

    await client.post(
        "/auth/register",
        json={"email": "userb@example.com", "password": "OtherPass99!", "username": "userb"},
    )
    login_b = await client.post(
        "/auth/login",
        json={"email": "userb@example.com", "password": "OtherPass99!"},
    )
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

    response = await client.get(f"/tasks/{task_id}", headers=headers_b)
    assert response.status_code in {403, 404}


@pytest.mark.asyncio
async def test_list_user_tasks(client, auth_headers):
    for name, prompt in [("First task", "First task"), ("Second task", "Second task")]:
        await client.post(
            "/tasks/",
            json={"task_type": "INFERENCE", "name": name, "input_payload": {"prompt": prompt}},
            headers=auth_headers,
        )

    response = await client.get("/tasks/user/me", headers=auth_headers)
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) >= 2
    for t in tasks:
        UUID(t["id"])


@pytest.mark.asyncio
async def test_delete_task(client, auth_headers):
    create = await client.post(
        "/tasks/",
        json={"task_type": "INFERENCE", "name": "To be deleted", "input_payload": {"prompt": "Delete me"}},
        headers=auth_headers,
    )
    task_id = create.json()["id"]

    delete = await client.delete(f"/tasks/{task_id}", headers=auth_headers)
    assert delete.status_code in {200, 204}

    get = await client.get(f"/tasks/{task_id}", headers=auth_headers)
    assert get.status_code == 404


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_inference_task_end_to_end(client, auth_headers):
    create = await client.post(
        "/tasks/",
        json={
            "task_type": "INFERENCE",
            "name": "Three words",
            "input_payload": {"prompt": "Reply with exactly three words: hello world test."},
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    task_id = create.json()["id"]

    terminal_statuses = {"SUCCESS", "FAILED"}
    status = "PENDING"
    for _ in range(60):
        await asyncio.sleep(1)
        resp = await client.get(f"/tasks/{task_id}/status", headers=auth_headers)
        status = resp.json()["status"]
        if status in terminal_statuses:
            break

    assert status == "SUCCESS", f"Task ended in status: {status}"

    result_resp = await client.get(f"/results/{task_id}", headers=auth_headers)
    assert result_resp.status_code == 200
    result = result_resp.json()
    assert result["output"]
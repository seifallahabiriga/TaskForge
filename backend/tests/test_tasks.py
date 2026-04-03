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


# ---------------------------------------------------------------------------
# Task creation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_task_returns_201(client, auth_headers):
    """POST /tasks/ creates a task and returns 201 with a valid UUID."""
    response = await client.post(
        "/tasks/",
        json={
            "task_type": "INFERENCE",
            "prompt": "Explain async/await in Python in one sentence.",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()

    # ID must be a valid UUID — Pydantic will have serialized it as a string.
    UUID(data["id"])  # raises ValueError if invalid
    assert data["status"] == "PENDING"
    assert data["task_type"] == "INFERENCE"


@pytest.mark.asyncio
async def test_create_task_requires_auth(client):
    """Creating a task without a token returns 401."""
    response = await client.post(
        "/tasks/",
        json={"task_type": "INFERENCE", "prompt": "hello"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_task_status(client, auth_headers):
    """GET /tasks/{task_id}/status returns the current status string."""
    create = await client.post(
        "/tasks/",
        json={"task_type": "INFERENCE", "prompt": "What is 2+2?"},
        headers=auth_headers,
    )
    task_id = create.json()["id"]

    response = await client.get(f"/tasks/{task_id}/status", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] in {
        "PENDING", "QUEUED", "RUNNING", "SUCCESS", "FAILED", "RETRYING"
    }


@pytest.mark.asyncio
async def test_get_task_ownership_enforced(client, auth_headers):
    """
    A second user cannot read another user's task — should return 403 or 404.

    We don't assert which one (the route may hide existence entirely) but
    it must not be 200.
    """
    # Create a task as user A.
    create = await client.post(
        "/tasks/",
        json={"task_type": "INFERENCE", "prompt": "Secret task."},
        headers=auth_headers,
    )
    task_id = create.json()["id"]

    # Register and log in as user B.
    await client.post(
        "/auth/register",
        json={
            "email": "userb@example.com",
            "password": "OtherPass99!",
            "username": "User B",
        },
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
    """GET /tasks/user/me returns only the authenticated user's tasks."""
    # Create two tasks.
    for prompt in ["First task", "Second task"]:
        await client.post(
            "/tasks/",
            json={"task_type": "INFERENCE", "prompt": prompt},
            headers=auth_headers,
        )

    response = await client.get("/tasks/user/me", headers=auth_headers)
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) >= 2
    # All tasks must belong to this user (no cross-user leakage).
    # The schema exposes user_id — verify they're all the same.
    user_ids = {t["user_id"] for t in tasks}
    assert len(user_ids) == 1


@pytest.mark.asyncio
async def test_delete_task(client, auth_headers):
    """Owner can delete their task; subsequent GET returns 404."""
    create = await client.post(
        "/tasks/",
        json={"task_type": "INFERENCE", "prompt": "To be deleted."},
        headers=auth_headers,
    )
    task_id = create.json()["id"]

    delete = await client.delete(f"/tasks/{task_id}", headers=auth_headers)
    assert delete.status_code in {200, 204}

    get = await client.get(f"/tasks/{task_id}", headers=auth_headers)
    assert get.status_code == 404


# ---------------------------------------------------------------------------
# End-to-end inference (slow — requires a live Celery worker and ML provider)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_inference_task_end_to_end(client, auth_headers):
    """
    Submit an INFERENCE task and poll until it reaches SUCCESS.

    This test requires:
      - A running Celery worker connected to the same Redis
      - A valid ML provider API key (Groq is the primary)

    In CI this runs against real services (see the workflow's `services:` block).
    Skip locally if you don't have Celery running:

        pytest -m "not e2e"
    """
    create = await client.post(
        "/tasks/",
        json={
            "task_type": "INFERENCE",
            "prompt": "Reply with exactly three words: hello world test.",
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    task_id = create.json()["id"]

    # Poll up to 60 seconds — Celery picks up jobs quickly in CI.
    terminal_statuses = {"SUCCESS", "FAILED"}
    status = "PENDING"
    for _ in range(60):
        await asyncio.sleep(1)
        resp = await client.get(f"/tasks/{task_id}/status", headers=auth_headers)
        status = resp.json()["status"]
        if status in terminal_statuses:
            break

    assert status == "SUCCESS", f"Task ended in status: {status}"

    # Result must exist and contain non-empty output.
    result_resp = await client.get(f"/results/{task_id}", headers=auth_headers)
    assert result_resp.status_code == 200
    result = result_resp.json()
    assert result["output"]  # non-empty string
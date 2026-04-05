"""
Auth flow tests.

Covers: register → login → get token (the happy path required by the brief),
plus negative cases that matter for security.
"""
import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    response = await client.post(
        "/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "StrongPass99!",
            "username": "newuser",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {
        "email": "dup@example.com",
        "password": "StrongPass99!",
        "username": "firstuser",
    }

    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 200

    second = await client.post("/auth/register", json=payload)
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_login_success(client, registered_user):
    response = await client.post(
        "/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client, registered_user):
    response = await client.post(
        "/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client):
    response = await client.post(
        "/auth/login",
        json={
            "email": "ghost@example.com",
            "password": "whatever",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_token_refresh(client, registered_user):
    login = await client.post(
        "/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "TestPassword123!",
        },
    )

    refresh_token = login.json()["refresh_token"]

    response = await client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_protected_route_without_token(client):
    response = await client.get("/tasks/user/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_with_token(client, auth_headers):
    response = await client.get("/tasks/user/me", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
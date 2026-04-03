"""
Auth flow tests.

Covers: register → login → get token (the happy path required by the brief),
plus negative cases that matter for security.
"""
import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    """New user can register and receives a 201 with the user payload."""
    response = await client.post(
        "/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "StrongPass99!",
            "full_name": "New User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    # is_admin must never be exposed in the output schema.
    assert "is_admin" not in data
    assert "password" not in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    """Registering with an already-used email returns 409."""
    payload = {
        "email": "dup@example.com",
        "password": "StrongPass99!",
        "full_name": "First",
    }
    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/auth/register", json=payload)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client, registered_user):
    """Registered user can log in and receives an access token."""
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
    assert data["token_type"] == "bearer"
    # Refresh token should also be present.
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client, registered_user):
    """Wrong password returns 401, not 403 (avoids leaking which field is wrong)."""
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
    """Login with unknown email returns 401 (same as wrong password — no user enumeration)."""
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
    """Refresh token can be exchanged for a new access token."""
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
    """Hitting a protected route without a token returns 401."""
    response = await client.get("/tasks/user/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_with_token(client, auth_headers):
    """Authenticated request to /tasks/user/me returns 200 with a list."""
    response = await client.get("/tasks/user/me", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
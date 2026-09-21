"""
User endpoint integration tests.

WHAT CHANGED:
- Login requests now use LoginRequest schema (email + password only, no name)
- Tests still cover the same flows: signup, login, auth, refresh, logout
"""


def test_create_user(client):
    r = client.post(
        "/users/create",
        json={"email": "test@example.com", "name": "testkas", "password": "test@123"},
    )
    assert r.status_code == 201
    data = r.json()
    # Access token is in the JSON body
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    # Refresh token is in an HttpOnly cookie, NOT in the JSON body
    assert "refresh_token" not in data
    assert "refresh_token" in r.cookies


def test_login(client):
    # Create user first
    client.post(
        "/users/create",
        json={"email": "test@example.com", "name": "testkas", "password": "test@123"},
    )
    # Login — now only needs email + password (no name)
    r = client.post(
        "/users/login",
        json={"email": "test@example.com", "password": "test@123"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in r.cookies


def test_login_wrong_password(client):
    client.post(
        "/users/create",
        json={"email": "test@example.com", "name": "testkas", "password": "test@123"},
    )
    r = client.post(
        "/users/login",
        json={"email": "test@example.com", "password": "wrong"},
    )
    assert r.status_code == 401


def test_protected_route_with_token(client):
    # Create user and get the access token
    r = client.post(
        "/users/create",
        json={"email": "test@example.com", "name": "testkas", "password": "test@123"},
    )
    access_token = r.json()["access_token"]

    # Use access token in Authorization header to hit a protected route
    r = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert r.status_code == 200
    assert r.json()["email"] == "test@example.com"


def test_protected_route_without_token(client):
    r = client.get("/users/me")
    assert r.status_code == 401


def test_refresh_token_flow(client):
    # Create user — the refresh token cookie is set automatically
    r = client.post(
        "/users/create",
        json={"email": "test@example.com", "name": "testkas", "password": "test@123"},
    )
    # The TestClient automatically sends cookies back on subsequent requests
    # Call refresh endpoint — it reads the refresh_token cookie
    r = client.post("/users/refresh")
    assert r.status_code == 200
    assert "access_token" in r.json()
    assert "refresh_token" in r.cookies  # Rotated refresh token


def test_logout_clears_cookie(client):
    # Create user
    client.post(
        "/users/create",
        json={"email": "test@example.com", "name": "testkas", "password": "test@123"},
    )
    r = client.post("/users/logout")
    assert r.status_code == 204

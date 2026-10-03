def test_register_and_me(client, auth_headers):
    res = client.get("/api/v1/users/me", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["email"] == "test@example.com"


def test_register_duplicate_email(client, auth_headers):
    res = client.post("/api/v1/auth/register", json={"email": "TEST@example.com", "password": "password123"})
    assert res.status_code == 409


def test_login_wrong_password(client, auth_headers):
    res = client.post("/api/v1/auth/login", data={"username": "test@example.com", "password": "wrong-password"})
    assert res.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/v1/users/me").status_code == 401
    bad = client.get("/api/v1/users/me", headers={"Authorization": "Bearer nope"})
    assert bad.status_code == 401

def test_training_chat_saves_history_and_memory(client, auth_headers):
    res = client.post("/api/v1/agents/training/chat", json={"message": "Mam kontuzję kolana"}, headers=auth_headers)
    assert res.status_code == 200
    assert "kontuzję kolana" in res.json()["reply"]

    res = client.post("/api/v1/agents/training/chat", json={"message": "Jaki trening na nogi?"}, headers=auth_headers)
    assert "Mam kontuzję kolana" in res.json()["memories_used"]

    history = client.get("/api/v1/agents/training/history", headers=auth_headers).json()
    assert [m["role"] for m in history] == ["user", "assistant", "user", "assistant"]


def test_memory_is_isolated_per_user(client, auth_headers):
    client.post("/api/v1/agents/training/chat", json={"message": "Sekret użytkownika A"}, headers=auth_headers)

    client.post("/api/v1/auth/register", json={"email": "b@example.com", "password": "password123"})
    token = client.post("/api/v1/auth/login", data={"username": "b@example.com", "password": "password123"})
    headers_b = {"Authorization": f"Bearer {token.json()['access_token']}"}

    res = client.post("/api/v1/agents/training/chat", json={"message": "Sekret"}, headers=headers_b)
    assert "Sekret użytkownika A" not in res.json()["memories_used"]


def test_photo_upload(client, auth_headers):
    files = {"file": ("x.png", b"\x89PNG fake", "image/png")}
    res = client.post("/api/v1/agents/photo", files=files, data={"message": "Co tu jest?"}, headers=auth_headers)
    assert res.status_code == 200
    assert "zdjęcie" in res.json()["reply"]


def test_photo_rejects_non_image(client, auth_headers):
    files = {"file": ("x.txt", b"hello", "text/plain")}
    assert client.post("/api/v1/agents/photo", files=files, headers=auth_headers).status_code == 415

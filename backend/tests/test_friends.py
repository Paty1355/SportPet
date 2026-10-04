import pytest

def test_friends_and_pet_privacy(client):
    client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "password123"})
    client.post("/api/v1/auth/register", json={"email": "b@example.com", "password": "password123"})
    
    token_a = client.post("/api/v1/auth/login", data={"username": "a@example.com", "password": "password123"}).json()["access_token"]
    token_b = client.post("/api/v1/auth/login", data={"username": "b@example.com", "password": "password123"}).json()["access_token"]
    
    auth_a = {"Authorization": f"Bearer {token_a}"}
    auth_b = {"Authorization": f"Bearer {token_b}"}

    user_b = client.get("/api/v1/users/me", headers=auth_b).json()
    b_id = user_b["id"]

    client.put("/api/v1/me/pet", json={"name": "Puszek", "level": 5, "hat": "red_cap"}, headers=auth_b)

    res_forbidden = client.get(f"/api/v1/friends/{b_id}/pet", headers=auth_a)
    assert res_forbidden.status_code == 403

    req = client.post("/api/v1/friends/requests", json={"user_id": b_id}, headers=auth_a)
    assert req.status_code == 201
    req_id = req.json()["id"]
 
    req_duplicate = client.post("/api/v1/friends/requests", json={"user_id": b_id}, headers=auth_a)
    assert req_duplicate.status_code == 409

    acc = client.post(f"/api/v1/friends/requests/{req_id}/accept", headers=auth_b)
    assert acc.status_code == 200

    friends_list = client.get("/api/v1/friends/", headers=auth_a).json()
    assert len(friends_list) == 1
    assert friends_list[0]["id"] == b_id

    pet_res = client.get(f"/api/v1/friends/{b_id}/pet", headers=auth_a)
    assert pet_res.status_code == 200
    assert pet_res.json()["name"] == "Puszek"
    assert pet_res.json()["hat"] == "red_cap"

    client.patch("/api/v1/me/privacy", json={"share_pet": False}, headers=auth_b)
    
    pet_hidden = client.get(f"/api/v1/friends/{b_id}/pet", headers=auth_a)
    assert pet_hidden.status_code == 200
    assert pet_hidden.json() == {}

    user_a = client.get("/api/v1/users/me", headers=auth_a).json()
    del_res = client.delete(f"/api/v1/friends/{user_a['id']}", headers=auth_b)
    assert del_res.status_code == 200
    
    assert client.get(f"/api/v1/friends/{b_id}/pet", headers=auth_a).status_code == 403
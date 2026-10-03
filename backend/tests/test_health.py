import pytest

URL = "/api/v1/health/ingest"

BP = {"ts": "2026-10-03T08:00:00Z", "systolic": 120, "diastolic": 80}
HR = {"metric": "heart_rate", "ts": "2026-10-03T08:00:00Z", "value": 70.5}
CYCLE = {"date": "2026-10-03", "cycle_day": 12, "phase": "follicular", "cycle_length": 28}
ECG = {
    "started_at": "2026-10-03T08:00:00Z",
    "sample_rate_hz": 512,
    "avg_heart_rate": 68,
    "classification": "sinus_rhythm",
    "samples": [0.0, 0.1],
}


def set_sex(client, headers, sex):
    assert client.patch("/api/v1/users/me", json={"sex": sex}, headers=headers).status_code == 200


def test_ingest_counts_each_section(client, auth_headers):
    set_sex(client, auth_headers, "F")
    body = {
        "samples": [HR, {**HR, "metric": "spo2", "value": 97}],
        "daily": [{"date": "2026-10-03", "steps": 8000, "sleep_minutes": 430}],
        "blood_pressure": [BP],
        "ecg": [ECG],
        "cycle": [CYCLE],
    }
    res = client.post(URL, json=body, headers=auth_headers)
    assert res.status_code == 201
    assert res.json() == {"samples": 2, "daily": 1, "blood_pressure": 1, "ecg": 1, "cycle": 1}


def test_ingest_is_idempotent(client, auth_headers):
    body = {"samples": [HR], "daily": [{"date": "2026-10-03", "steps": 1}], "blood_pressure": [BP], "ecg": [ECG]}
    assert client.post(URL, json=body, headers=auth_headers).json()["samples"] == 1
    again = client.post(URL, json=body, headers=auth_headers).json()
    assert again == {"samples": 0, "daily": 0, "blood_pressure": 0, "ecg": 0, "cycle": 0}


def test_cycle_requires_female_user(client, auth_headers):
    assert client.post(URL, json={"cycle": [CYCLE]}, headers=auth_headers).status_code == 422  # sex nieustawiona
    set_sex(client, auth_headers, "M")
    assert client.post(URL, json={"cycle": [CYCLE]}, headers=auth_headers).status_code == 422
    set_sex(client, auth_headers, "F")
    assert client.post(URL, json={"cycle": [CYCLE]}, headers=auth_headers).json()["cycle"] == 1


@pytest.mark.parametrize(
    "body",
    [
        {"blood_pressure": [{**BP, "systolic": 70, "diastolic": 90}]},
        {"samples": [{**HR, "value": 400}]},
        {"samples": [{**HR, "ts": "2026-10-03T08:00:00"}]},  # brak strefy czasowej
        {"samples": [{**HR, "metric": "bogus"}]},
        {"cycle": [{**CYCLE, "cycle_day": 30}]},
    ],
)
def test_invalid_payloads_rejected(client, auth_headers, body):
    assert client.post(URL, json=body, headers=auth_headers).status_code == 422


def test_requires_auth(client):
    assert client.post(URL, json={}).status_code == 401


def test_users_do_not_collide(client, auth_headers):
    client.post("/api/v1/auth/register", json={"email": "b@example.com", "password": "password123"})
    login = client.post("/api/v1/auth/login", data={"username": "b@example.com", "password": "password123"})
    token = login.json()["access_token"]
    other = {"Authorization": f"Bearer {token}"}
    # ten sam klucz (ts, metric) u innego użytkownika to osobny wiersz
    assert client.post(URL, json={"samples": [HR]}, headers=auth_headers).json()["samples"] == 1
    assert client.post(URL, json={"samples": [HR]}, headers=other).json()["samples"] == 1


def test_profile_fields_validated_and_returned(client, auth_headers):
    ok = {"sex": "F", "birth_date": "1990-01-01", "weight_kg": 62.5, "height_cm": 168}
    assert client.patch("/api/v1/users/me", json=ok, headers=auth_headers).status_code == 200
    me = client.get("/api/v1/users/me", headers=auth_headers).json()
    assert {k: me[k] for k in ok} == ok
    assert client.patch("/api/v1/users/me", json={"weight_kg": 5}, headers=auth_headers).status_code == 422


@pytest.fixture
def service(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "service_key", "svc-key")
    return {"X-Service-Key": "svc-key"}


def test_service_endpoints_require_key(client, auth_headers, service):
    assert client.get("/api/v1/health/service/users").status_code == 401
    assert client.get("/api/v1/health/service/users", headers={"X-Service-Key": "nope"}).status_code == 401
    assert client.get("/api/v1/health/service/users", headers=auth_headers).status_code == 401  # JWT to nie klucz
    assert client.get("/api/v1/health/service/users", headers=service).status_code == 200


def test_service_endpoints_disabled_without_key(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "service_key", None)
    res = client.get("/api/v1/health/service/users", headers={"X-Service-Key": ""})
    assert res.status_code == 503


def test_service_sets_profile_and_ingests_for_any_user(client, auth_headers, service):
    users = client.get("/api/v1/health/service/users", headers=service).json()
    uid = users[0]["id"]
    assert users[0]["sex"] is None
    patched = client.patch(f"/api/v1/health/service/users/{uid}/profile", json={"sex": "F"}, headers=service)
    assert patched.json()["sex"] == "F"
    res = client.post(f"/api/v1/health/service/ingest/{uid}", json={"samples": [HR], "cycle": [CYCLE]}, headers=service)
    assert res.status_code == 201 and res.json()["samples"] == 1 and res.json()["cycle"] == 1
    assert client.post("/api/v1/health/service/ingest/9999", json={}, headers=service).status_code == 404

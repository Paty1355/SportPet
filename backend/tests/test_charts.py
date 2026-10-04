from datetime import UTC, datetime

INGEST = "/api/v1/health/ingest"
H = "/api/v1/health"


def hr(ts, value):
    return {"metric": "heart_rate", "ts": ts, "value": value}


def seed(client, headers):
    body = {
        "samples": [
            hr("2026-10-03T08:00:00Z", 60),
            hr("2026-10-03T08:04:00Z", 80),
            hr("2026-10-03T08:05:00Z", 100),
            {"metric": "spo2", "ts": "2026-10-03T08:00:00Z", "value": 97},
        ],
        "daily": [
            {"date": "2026-10-02", "steps": 5000, "sleep_minutes": 400},
            {"date": "2026-10-03", "steps": 9000, "sleep_minutes": 450},
        ],
        "blood_pressure": [{"ts": "2026-10-03T08:00:00Z", "systolic": 120, "diastolic": 80}],
        "ecg": [
            {
                "started_at": "2026-10-03T09:00:00Z",
                "sample_rate_hz": 512,
                "avg_heart_rate": 66,
                "classification": "sinus_rhythm",
                "samples": [float(i) for i in range(1000)],
            }
        ],
    }
    assert client.post(INGEST, json=body, headers=headers).status_code == 201


WINDOW = {"start": "2026-10-03T00:00:00Z", "end": "2026-10-04T00:00:00Z"}


def test_series_raw_is_sorted_and_scoped_to_metric(client, auth_headers):
    seed(client, auth_headers)
    res = client.get(f"{H}/series", params={"metric": "heart_rate", **WINDOW}, headers=auth_headers).json()
    assert res["unit"] == "bpm" and [p["value"] for p in res["points"]] == [60, 80, 100]


def test_series_bucket_aggregates(client, auth_headers):
    seed(client, auth_headers)
    params = {"metric": "heart_rate", "bucket": "5m", **WINDOW}
    res = client.get(f"{H}/series", params=params, headers=auth_headers).json()
    first, second = res["points"]
    assert (first["value"], first["min"], first["max"]) == (70, 60, 80)
    assert second["value"] == 100
    assert datetime.fromisoformat(first["ts"]) == datetime(2026, 10, 3, 8, 0, tzinfo=UTC)


def test_series_range_limits(client, auth_headers):
    p = {"metric": "heart_rate", "start": "2026-07-01T00:00:00Z", "end": "2026-10-04T00:00:00Z"}
    assert client.get(f"{H}/series", params=p, headers=auth_headers).status_code == 422
    assert client.get(f"{H}/series", params={**p, "bucket": "1d"}, headers=auth_headers).status_code == 422
    inverted = {"metric": "heart_rate", "start": WINDOW["end"], "end": WINDOW["start"]}
    assert client.get(f"{H}/series", params=inverted, headers=auth_headers).status_code == 422
    assert client.get(f"{H}/series", params={"metric": "bogus"}, headers=auth_headers).status_code == 422


DASH = {"end": "2026-10-03", "days": 7}


def test_dashboard_collects_window_and_latest_values(client, auth_headers):
    seed(client, auth_headers)
    profile = {"sex": "M", "birth_date": "1990-01-01", "weight_kg": 80, "height_cm": 200}
    client.patch("/api/v1/users/me", json=profile, headers=auth_headers)
    res = client.get(f"{H}/dashboard", params=DASH, headers=auth_headers).json()
    assert res["latest"]["heart_rate"]["value"] == 100 and res["latest"]["stress"] is None
    assert res["bmi"] == 20.0 and res["age"] >= 35 and res["cycle"] == []
    assert [(d["date"], d["steps"]) for d in res["daily"]] == [("2026-10-02", 5000), ("2026-10-03", 9000)]
    assert res["blood_pressure"][0]["systolic"] == 120
    assert len(res["ecg"]) == 1 and "samples" not in res["ecg"][0]
    assert "metrics" in res["stats"]


def test_dashboard_window_is_inclusive_and_bounded(client, auth_headers):
    seed(client, auth_headers)
    one_day = client.get(f"{H}/dashboard", params={"end": "2026-10-02", "days": 7}, headers=auth_headers).json()
    assert [d["date"] for d in one_day["daily"]] == ["2026-10-02"] and one_day["ecg"] == []
    assert client.get(f"{H}/dashboard", params={"days": 61}, headers=auth_headers).status_code == 422


def test_users_cannot_read_each_others_data(client, auth_headers):
    seed(client, auth_headers)
    client.post("/api/v1/auth/register", json={"email": "b@example.com", "password": "password123"})
    login = client.post("/api/v1/auth/login", data={"username": "b@example.com", "password": "password123"})
    other = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get(f"{H}/series", params={"metric": "heart_rate", **WINDOW}, headers=other).json()["points"] == []
    res = client.get(f"{H}/dashboard", params=DASH, headers=other).json()
    assert res["daily"] == [] and res["ecg"] == [] and res["blood_pressure"] == []


def test_charts_require_auth(client):
    for path in ("series?metric=spo2", "dashboard"):
        assert client.get(f"{H}/{path}").status_code == 401

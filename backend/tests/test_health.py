def test_report_returns_pdf(client, auth_headers):
    res = client.get("/api/v1/health/report", headers=auth_headers)

    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/pdf")
    assert res.headers["content-disposition"] == 'attachment; filename="raport.pdf"'
    assert res.content.startswith(b"%PDF-")


def test_report_requires_token(client):
    res = client.get("/api/v1/health/report")
    assert res.status_code == 401


def test_report_validates_limit(client, auth_headers):
    res = client.get("/api/v1/health/report?limit=0", headers=auth_headers)
    assert res.status_code == 422

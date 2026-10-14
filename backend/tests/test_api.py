import uuid

import pytest


def test_health_and_settings_hide_secrets(client):
    assert client.get("/api/v1/health").json() == {"status": "ok", "database": "ok"}
    s = client.get("/api/v1/settings/status").json()
    assert s["demo_mode"] is True and s["wcag"]["version"] == "2.2"
    assert "key" not in str(s).lower().replace("api_key", "")  # no secret material


def test_create_audit_validation_errors_are_consistent(client):
    r = client.post("/api/v1/audits", json={"url": "x"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    r = client.post("/api/v1/audits", json={"url": "https://example.com", "mode": "nope"})
    assert r.status_code == 422 and r.json()["error"]["details"][0]["field"] == "mode"


@pytest.mark.parametrize("url", ["http://127.0.0.1/", "http://localhost:8080/", "http://169.254.169.254/latest/meta-data/",
                                 "file:///etc/passwd", "http://10.0.0.1/", "http://127.0.0.1:8000/api/v1/health"])
def test_ssrf_urls_rejected_with_400(client, url):
    r = client.post("/api/v1/audits", json={"url": url})
    assert r.status_code == 400 and r.json()["error"]["code"] == "url_not_allowed"
    assert client.get("/api/v1/audits").json()["total"] == 0  # nothing was queued


def test_not_found_and_bad_ids(client):
    for path in (f"/api/v1/audits/{uuid.uuid4()}", "/api/v1/audits/not-a-uuid", f"/api/v1/reports/{uuid.uuid4()}",
                 f"/api/v1/audits/{uuid.uuid4()}/findings", f"/api/v1/evaluations/{uuid.uuid4()}"):
        r = client.get(path)
        assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
    assert client.delete(f"/api/v1/audits/{uuid.uuid4()}").status_code == 404


def test_pagination_bounds(client):
    assert client.get("/api/v1/audits?page=0").status_code == 422
    assert client.get("/api/v1/audits?page_size=1000").status_code == 422
    body = client.get("/api/v1/audits").json()
    assert body == {"items": [], "total": 0, "page": 1, "page_size": 10}


def test_dashboard_empty_state_is_real_zeros(client):
    d = client.get("/api/v1/dashboard/summary").json()
    assert d["total_audits"] == 0 and d["total_findings"] == 0 and d["recent_audits"] == []


def test_evaluation_summary_is_pending_without_runs(client):
    s = client.get("/api/v1/evaluations/summary").json()
    assert s["state"] == "pending" and s["latest_run"] is None and "pending" in s["note"].lower()
    assert s["dataset"]["n_pages"] == 16 and s["dataset"]["n_annotations"] == 18


def test_report_format_validated(client):
    assert client.get(f"/api/v1/reports/{uuid.uuid4()}?format=exe").status_code == 422


def test_security_headers_and_cors(client):
    r = client.options("/api/v1/audits", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in r.headers
    r = client.options("/api/v1/audits", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"

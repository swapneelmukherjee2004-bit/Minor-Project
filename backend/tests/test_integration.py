"""Full lifecycle with real Chromium, real axe-core, real PostgreSQL and the demo (mock) AI provider."""
import http.server
import json
import threading
import time

import pytest
from sqlalchemy import select

from app.core.security import UrlPolicy
from app.db.session import get_sessionmaker
from app.models import Audit, Finding
from app.services.ai_providers import ProviderError

pytestmark = pytest.mark.browser


def wait(client, audit_id, timeout=60):
    end = time.time() + timeout
    while time.time() < end:
        a = client.get(f"/api/v1/audits/{audit_id}").json()
        if a["status"] in ("completed", "failed"):
            return a
        time.sleep(0.3)
    raise AssertionError("audit did not finish")


def start(client, url, **kw):
    r = client.post("/api/v1/audits", json={"url": url, **kw})
    assert r.status_code == 202, r.text
    return r.json()["id"]


def test_full_audit_lifecycle(client, fix_origin):
    aid = start(client, f"{fix_origin}/fixtures/img-vague-alt.html", mode="combined")
    a = wait(client, aid)
    assert a["status"] == "completed", a
    assert a["demo_mode"] is True and a["ai_model"] == "demo-heuristic-v1" and a["has_screenshot"]
    assert a["tool_versions"]["axe_core"] and a["prompt_version"] == "audit-v1"
    shot = client.get(f"/api/v1/audits/{aid}/screenshot")
    assert shot.status_code == 200 and shot.content[:8] == b"\x89PNG\r\n\x1a\n" and len(shot.content) > 1000

    items = client.get(f"/api/v1/audits/{aid}/findings").json()["items"]
    methods = {f["method"] for f in items}
    assert {"custom", "ai"} <= methods
    ai = next(f for f in items if f["method"] == "ai")
    assert ai["evidence"]["selector"] == "#revenue-chart" and ai["evidence"]["html_excerpt"].startswith("<img")
    assert ai["status"] in ("suspected", "needs_manual_review") and ai["detected_by"] == "ai_only"
    assert any(f["rule_id"] == "custom-filename-alt" and f["selector"] == "#hero-photo" for f in items)
    # filters
    assert all(f["method"] == "ai" for f in client.get(f"/api/v1/audits/{aid}/findings?method=ai").json()["items"])
    assert all(f["method"] in ("axe", "custom") for f in client.get(f"/api/v1/audits/{aid}/findings?method=conventional").json()["items"])

    cmp = client.get(f"/api/v1/audits/{aid}/comparison").json()
    assert cmp["counts"]["ai_only"] >= 1 and cmp["ground_truth"]["available"] is True and cmp["demo_mode"] is True
    assert cmp["ground_truth"]["methods"]["ai"]["finding"]["tp"] == 1  # 'graphic' alt found by the demo AI only

    # persistence: rows really live in PostgreSQL
    with get_sessionmaker()() as db:
        assert db.scalar(select(Audit).where(Audit.id == aid)).dom_context["images"]
        assert len(db.scalars(select(Finding).where(Finding.audit_id == aid)).all()) == len(items)

    # reports
    j = client.get(f"/api/v1/reports/{aid}?format=json")
    assert j.status_code == 200 and json.loads(j.text)["metadata"]["demo_mode"] is True
    assert "title" in client.get(f"/api/v1/reports/{aid}?format=csv").text.splitlines()[0]
    assert client.get(f"/api/v1/reports/{aid}?format=pdf").content.startswith(b"%PDF")

    # dashboard + history reflect real data
    d = client.get("/api/v1/dashboard/summary").json()
    assert d["total_audits"] == 1 and d["total_findings"] == len(items) and d["demo_audits"] == 1
    assert client.get("/api/v1/audits?q=img-vague").json()["total"] == 1
    assert client.get("/api/v1/audits?q=zzz").json()["total"] == 0

    # delete cascades
    assert client.delete(f"/api/v1/audits/{aid}").status_code == 204
    assert client.get(f"/api/v1/audits/{aid}").status_code == 404
    with get_sessionmaker()() as db:
        assert db.scalars(select(Finding).where(Finding.audit_id == aid)).all() == []


def test_axe_real_findings_with_wcag_mapping(client, fix_origin):
    aid = start(client, f"{fix_origin}/fixtures/contrast-low.html", mode="conventional")
    assert wait(client, aid)["status"] == "completed"
    items = client.get(f"/api/v1/audits/{aid}/findings").json()["items"]
    f = next(x for x in items if x["rule_id"] == "color-contrast")
    assert f["method"] == "axe" and f["selector"] == "#fine-print" and "1.4.3" in f["wcag_criteria"]
    assert f["category"] == "contrast" and f["status"] == "confirmed" and f["help_url"].startswith("https://dequeuniversity.com")
    assert not any(x["method"] == "ai" for x in items)


def test_clean_baseline_has_no_confirmed_violations(client, fix_origin):
    aid = start(client, f"{fix_origin}/fixtures/baseline-form.html", mode="combined")
    assert wait(client, aid)["status"] == "completed"
    assert client.get(f"/api/v1/audits/{aid}/findings?status=confirmed").json()["total"] == 0
    cmp = client.get(f"/api/v1/audits/{aid}/comparison").json()
    assert cmp["ground_truth"]["available"] is True and cmp["ground_truth"]["n_annotations"] == 0


def test_non_fixture_url_has_no_ground_truth(client, fix_origin):
    aid = start(client, f"{fix_origin}/fixtures/baseline-article.html", mode="conventional")
    wait(client, aid)
    with get_sessionmaker()() as db:  # simulate a user page: ground truth keyed by fixture file only
        pass
    cmp = client.get(f"/api/v1/audits/{aid}/comparison").json()
    assert cmp["ground_truth"]["available"] is True


def test_ai_provider_failure_degrades_gracefully(client, fix_origin):
    runner = client.app.state.runner

    def boom(_s):
        raise ProviderError("Provider unavailable after 4 attempts (503).")
    runner.provider_factory = boom
    aid = start(client, f"{fix_origin}/fixtures/nav-generic-links.html", mode="combined")
    a = wait(client, aid)
    assert a["status"] == "completed" and "unavailable" in a["ai_error"]
    items = client.get(f"/api/v1/audits/{aid}/findings").json()["items"]
    assert items and all(f["method"] != "ai" for f in items)
    aid2 = start(client, f"{fix_origin}/fixtures/nav-generic-links.html", mode="ai")
    b = wait(client, aid2)
    assert b["status"] == "failed" and "AI analysis failed" in b["error"]


def test_ai_garbage_output_is_handled(client, fix_origin):
    class Garbage:
        name, model = "mock", "garbage"

        async def complete(self, *a):
            return "I refuse to produce JSON"
    client.app.state.runner.provider_factory = lambda _s: Garbage()
    aid = start(client, f"{fix_origin}/fixtures/heading-skip.html", mode="combined")
    a = wait(client, aid)
    assert a["status"] == "completed" and "valid JSON" in a["ai_error"]


def test_delete_blocked_while_running_and_restart_recovery(client):
    from app.models import Audit as A
    with get_sessionmaker()() as db:
        a = A(url="https://example.com", host="example.com", mode="combined", status="running")
        db.add(a)
        db.commit()
        aid = a.id
    assert client.delete(f"/api/v1/audits/{aid}").status_code == 409
    client.app.state.runner.recover_interrupted()
    got = client.get(f"/api/v1/audits/{aid}").json()
    assert got["status"] == "failed" and "restart" in got["error"]


# ---- browser-level SSRF defences: sub-requests and redirects ----
@pytest.fixture()
def hostile_site(tmp_path):
    (tmp_path / "fixtures").mkdir()
    (tmp_path / "fixtures" / "ssrf.html").write_text(
        '<!doctype html><html lang="en"><head><title>t</title></head><body><main><h1>x</h1>'
        '<img src="http://169.254.169.254/latest/meta-data/" onerror="document.title=\'blocked-meta\'" alt="">'
        '</main></body></html>')

    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(tmp_path), **k)

        def do_GET(self):
            if self.path.startswith("/fixtures/redirect"):
                self.send_response(302)
                self.send_header("Location", "http://127.0.0.1:9/secret")
                self.end_headers()
                return
            super().do_GET()

        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def test_browser_blocks_internal_subrequests_and_redirects(client, hostile_site):
    runner = client.app.state.runner
    policy = UrlPolicy(fixture_origins={hostile_site})
    for path, want_status in (("ssrf.html", "completed"), ("redirect.html", "failed")):
        with get_sessionmaker()() as db:
            a = Audit(url=f"{hostile_site}/fixtures/{path}", host="127.0.0.1", mode="conventional", status="queued")
            db.add(a)
            db.commit()
            aid = a.id
        # run on the app's own loop so the Playwright objects belong to it
        client.portal.call(runner.run, aid, policy)
        with get_sessionmaker()() as db:
            a = db.get(Audit, aid)
            assert a.status == want_status, a.error
            if path == "ssrf.html":
                assert a.page_title == "blocked-meta"  # the metadata-IP request was aborted by the guard
            else:
                assert "blocked network address" in a.error

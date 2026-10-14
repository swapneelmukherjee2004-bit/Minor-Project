import json
from types import SimpleNamespace

from app.services import report_service as rep


def audit():
    return SimpleNamespace(id="a" * 36, url="https://e.com", final_url=None, mode="combined", status="completed", page_title="T",
                           created_at=None, completed_at=None, tool_versions={"axe_core": "4.10.2"}, ai_provider="mock", ai_model="demo",
                           prompt_version="audit-v1", demo_mode=True, ai_error=None, ai_rejected_count=0)


def fnd(title="=HYPERLINK(\"http://evil\")", desc="<script>alert(1)</script> & <b>bold"):
    return SimpleNamespace(id="f1", method="ai", rule_id="r", title=title, description=desc, severity="high", category="images",
                           status="suspected", confidence=0.5, wcag_criteria=["1.1.1"], selector="#a",
                           evidence={"html_excerpt": "<img src=x onerror=1>", "dom_observation": "+cmd", "screenshot_observation": ""},
                           user_impact="", recommendation="fix")


CMP = {"counts": {"conventional_only": 0, "ai_only": 1, "both": 0}, "groups": [{"group_id": 1, "detected_by": "ai_only", "conventional_ids": [], "ai_ids": ["f1"]}]}


def test_json_report_structure_and_no_secrets_or_paths():
    r = rep.build_report(audit(), [fnd()], CMP, None)
    text = rep.to_json(r)
    assert json.loads(text)["ground_truth_metrics"] == {"available": False}
    assert "screenshot_key" not in text and "/home/" not in text and r["limitations"]
    assert r["findings"][0]["detected_by"] == "ai_only" and r["metadata"]["demo_mode"] is True


def test_csv_neutralises_formula_injection():
    out = rep.to_csv(rep.build_report(audit(), [fnd()], CMP, None))
    assert "'=HYPERLINK" in out and "'+cmd" in out


def test_pdf_generates_and_escapes_markup():
    pdf = rep.to_pdf(rep.build_report(audit(), [fnd()], CMP, None))
    assert pdf.startswith(b"%PDF") and len(pdf) > 1000

"""Report export (JSON / CSV / PDF). Untrusted text is escaped; internal paths and secrets are never included."""
import csv
import io
import json
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

LIMITATIONS = [
    "Automated tools, including axe-core, cannot detect every accessibility problem.",
    "AI findings are inferences from a screenshot and extracted DOM context; they require human verification.",
    "Screenshot and DOM analysis cannot verify keyboard behaviour or screen-reader announcements.",
    "A clean automated report does not demonstrate WCAG conformance. This is an audit aid, not a certification.",
    "Model confidence is an uncalibrated self-assessment, not the probability that an issue exists.",
]
_CSV_FIELDS = ["method", "rule_id", "title", "severity", "category", "status", "confidence", "wcag_criteria", "selector",
               "detected_by", "description", "user_impact", "recommendation", "html_excerpt", "dom_observation", "screenshot_observation"]


def _dt(v: datetime | None) -> str | None:
    return v.isoformat() if v else None


def build_report(audit, findings: list, comparison: dict, ground_truth: dict | None) -> dict:
    detected = {}
    for g in comparison["groups"]:
        for i in g["conventional_ids"] + g["ai_ids"]:
            detected[i] = g["detected_by"]
    return {
        "metadata": {"audit_id": audit.id, "url": audit.url, "final_url": audit.final_url, "mode": audit.mode,
                     "status": audit.status, "page_title": audit.page_title, "created_at": _dt(audit.created_at),
                     "completed_at": _dt(audit.completed_at), "tool_versions": audit.tool_versions or {},
                     "ai_provider": audit.ai_provider, "ai_model": audit.ai_model, "prompt_version": audit.prompt_version,
                     "demo_mode": audit.demo_mode, "ai_error": audit.ai_error, "wcag_scope": "WCAG 2.2 Level A and AA",
                     "ai_findings_rejected_by_validation": audit.ai_rejected_count},
        "comparison": comparison["counts"],
        "ground_truth_metrics": ground_truth if ground_truth else {"available": False},
        "findings": [{
            "id": f.id, "method": f.method, "rule_id": f.rule_id, "title": f.title, "description": f.description,
            "severity": f.severity, "category": f.category, "status": f.status, "confidence": f.confidence,
            "wcag_criteria": f.wcag_criteria, "selector": f.selector, "evidence": f.evidence,
            "user_impact": f.user_impact, "recommendation": f.recommendation, "detected_by": detected.get(f.id)}
            for f in findings],
        "limitations": LIMITATIONS,
    }


def _csv_safe(v) -> str:
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s  # neutralise spreadsheet formula injection


def to_csv(report: dict) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=_CSV_FIELDS)
    w.writeheader()
    for f in report["findings"]:
        ev = f.get("evidence") or {}
        row = {**f, "wcag_criteria": ";".join(f["wcag_criteria"]), "html_excerpt": ev.get("html_excerpt"),
               "dom_observation": ev.get("dom_observation"), "screenshot_observation": ev.get("screenshot_observation")}
        w.writerow({k: _csv_safe(row.get(k)) for k in _CSV_FIELDS})
    return buf.getvalue()


def to_json(report: dict) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False)


def to_pdf(report: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title="Accessibility audit report", leftMargin=36, rightMargin=36)
    st = getSampleStyleSheet()
    p = lambda text, style="BodyText": Paragraph(escape(str(text)), st[style])  # noqa: E731 - everything escaped
    m = report["metadata"]
    els = [p("Accessibility Audit Report", "Title"), p(f"URL: {m['url']}"), p(f"Mode: {m['mode']}   Status: {m['status']}"),
           p(f"Created: {m['created_at']}   Scope: {m['wcag_scope']}")]
    if m["demo_mode"]:
        els.append(p("DEMO MODE: AI findings in this report were produced by a mock provider, not a real model.", "Heading3"))
    els += [p(f"Tools: {json.dumps(m['tool_versions'])}"), Spacer(1, 8), p("Comparison summary", "Heading2"),
            p(f"Conventional only: {report['comparison']['conventional_only']}; AI only: {report['comparison']['ai_only']}; "
              f"both: {report['comparison']['both']}"), Spacer(1, 8), p("Findings", "Heading2")]
    for f in report["findings"]:
        els.append(p(f"[{f['severity'].upper()}] {f['title']}", "Heading4"))
        els.append(p(f"Method: {f['method']} | Category: {f['category']} | Status: {f['status']} | "
                     f"WCAG: {', '.join(f['wcag_criteria']) or 'n/a'} | Confidence: {f['confidence'] if f['confidence'] is not None else 'n/a'}"))
        ev = f.get("evidence") or {}
        for label, val in (("Selector", f.get("selector")), ("DOM", ev.get("dom_observation")), ("Screenshot", ev.get("screenshot_observation")),
                           ("HTML", ev.get("html_excerpt")), ("Why it matters", f.get("user_impact")), ("Fix", f.get("recommendation"))):
            if val:
                els.append(p(f"{label}: {val}"))
        els.append(Spacer(1, 4))
    els += [Spacer(1, 8), p("Limitations", "Heading2")] + [p("- " + x) for x in report["limitations"]]
    doc.build(els)
    return buf.getvalue()

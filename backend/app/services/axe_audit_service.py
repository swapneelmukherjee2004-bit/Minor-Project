"""Conventional audit: axe-core (run in-page) plus a few documented deterministic heuristics."""
import re
from pathlib import Path

from playwright.async_api import Page

from app.utils.wcag import AXE_RUN_TAGS, axe_tag_to_criterion

AXE_JS = (Path(__file__).resolve().parents[1] / "assets" / "axe.min.js").read_text()
MAX_NODES_PER_RULE = 10

_IMPACT = {"critical": "critical", "serious": "high", "moderate": "medium", "minor": "low"}
_CATEGORY_BY_RULE = {
    "image-alt": "images", "input-image-alt": "images", "role-img-alt": "images", "svg-img-alt": "images",
    "object-alt": "images", "area-alt": "images", "image-redundant-alt": "images",
    "color-contrast": "contrast", "color-contrast-enhanced": "contrast", "link-in-text-block": "contrast",
    "label": "forms", "select-name": "forms", "autocomplete-valid": "forms", "form-field-multiple-labels": "forms",
    "label-title-only": "forms", "aria-input-field-name": "forms",
    "link-name": "navigation", "bypass": "navigation", "skip-link": "navigation", "tabindex": "navigation",
    "identical-links-same-purpose": "navigation", "frame-title": "navigation",
    "button-name": "semantics", "document-title": "semantics", "html-has-lang": "semantics",
    "html-lang-valid": "semantics", "valid-lang": "semantics", "heading-order": "semantics",
    "empty-heading": "semantics", "landmark-one-main": "semantics", "list": "semantics", "listitem": "semantics",
    "definition-list": "semantics", "dlitem": "semantics", "meta-viewport": "readability",
}


def category_for_axe(rule_id: str) -> str:
    if rule_id in _CATEGORY_BY_RULE:
        return _CATEGORY_BY_RULE[rule_id]
    if rule_id.startswith("aria-"):
        return "semantics"
    if rule_id.startswith("color-"):
        return "contrast"
    return "other"


async def run_axe(page: Page) -> tuple[list[dict], str]:
    """Returns (raw_findings, axe_version). Nodes are capped per rule; selectors still need canonicalisation."""
    await page.evaluate(AXE_JS)
    result = await page.evaluate(
        """async (tags) => { const r = await axe.run(document, {runOnly: {type: 'tag', values: tags},
           resultTypes: ['violations', 'incomplete']}); return {version: axe.version,
           violations: r.violations, incomplete: r.incomplete}; }""", AXE_RUN_TAGS)
    out: list[dict] = []
    for bucket, status in (("violations", "confirmed"), ("incomplete", "needs_manual_review")):
        for rule in result[bucket]:
            criteria = sorted({c for t in rule.get("tags", []) if (c := axe_tag_to_criterion(t))})
            for node in rule.get("nodes", [])[:MAX_NODES_PER_RULE]:
                target = node.get("target") or []
                sel = target[0] if target and isinstance(target[0], str) and len(target) == 1 else None
                impact = node.get("impact") or rule.get("impact") or "medium"
                out.append({
                    "method": "axe", "rule_id": rule["id"], "title": rule.get("help", rule["id"]),
                    "description": rule.get("description", ""), "category": category_for_axe(rule["id"]),
                    "severity": _IMPACT.get(impact, "medium") if status == "confirmed" else "low",
                    "confidence": None, "status": status, "verification_method": "automated" if status == "confirmed" else "manual_review",
                    "wcag_criteria": criteria, "raw_selector": sel,
                    "evidence": {"dom_observation": (node.get("failureSummary") or "").strip()[:1500],
                                 "html_excerpt": (node.get("html") or "")[:400], "selector": sel or "",
                                 "screenshot_observation": ""},
                    "user_impact": "", "recommendation": (node.get("failureSummary") or rule.get("help", "")).strip()[:1500],
                    "help_url": rule.get("helpUrl"),
                })
    return out, result["version"]


# ---------- documented custom heuristics (labelled method="custom", never presented as axe) ----------
_GENERIC_LINK = re.compile(r"^(click here|here|read more|more|learn more|link|this link|details|continue|go)$", re.I)
_FILENAME_ALT = re.compile(r"^[\w\-. ]+\.(png|jpe?g|gif|svg|webp|avif)$|^(img|image|dsc|photo|screenshot)[-_ ]?\d*$", re.I)


def custom_checks(ctx: dict) -> list[dict]:
    """Deterministic checks axe-core (WCAG tag set) does not perform. Intentionally conservative."""
    found: list[dict] = []

    def add(rule_id, title, desc, category, el, criteria, rec, severity="low"):
        found.append({
            "method": "custom", "rule_id": rule_id, "title": title, "description": desc, "category": category,
            "severity": severity, "confidence": None, "status": "suspected", "verification_method": "automated",
            "wcag_criteria": criteria, "raw_selector": el["selector"], "help_url": None,
            "evidence": {"dom_observation": desc, "html_excerpt": el["html"], "selector": el["selector"], "screenshot_observation": ""},
            "user_impact": "", "recommendation": rec,
        })

    prev = None
    for h in ctx.get("headings", []):
        if h.get("level") and prev and h["level"] > prev + 1 and h["visible"]:
            add("custom-heading-skip", f"Heading level skipped (h{prev} to h{h['level']})",
                f"Heading '{h['text']}' jumps from level {prev} to {h['level']}, which can disorient screen-reader users navigating by headings.",
                "semantics", h, ["1.3.1"], "Use heading levels that follow the document outline without skipping levels.")
        if h.get("level"):
            prev = h["level"]
    for img in ctx.get("images", []):
        alt = (img.get("alt") or "").strip()
        if img["tag"] == "img" and alt and _FILENAME_ALT.match(alt):
            add("custom-filename-alt", "Alternative text looks like a file name or placeholder",
                f"alt=\"{alt}\" appears to be a file name or generic placeholder rather than a description.",
                "images", img, ["1.1.1"], "Describe the image's purpose in context, or use alt=\"\" if it is decorative.", "medium")
    for a in ctx.get("links", []):
        name = (a.get("accessibleName") or "").strip()
        if name and _GENERIC_LINK.match(name):
            add("custom-generic-link-text", f"Generic link text \"{name}\"",
                f"The link's accessible name \"{name}\" does not describe its destination or purpose on its own.",
                "navigation", a, ["2.4.4"], "Use link text that describes the destination, or add context via aria-label/aria-describedby.")
    return found

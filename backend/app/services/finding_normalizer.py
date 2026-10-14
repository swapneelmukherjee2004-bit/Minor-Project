"""Normalisation + matching of conventional and AI findings.

Matching strategy (documented in docs/ARCHITECTURE.md):
  Two findings from DIFFERENT methods (conventional = axe|custom, ai) are placed in the same group iff
    (1) both carry a canonical selector and the selectors are equal or one is an ancestor of the other, AND
    (2) they share a category OR share at least one WCAG success criterion.
  A shared category alone never merges findings. Findings without a selector are never merged.
  Originals are preserved; group_id only links them.
"""
from collections import defaultdict


def conventional(method: str) -> bool:
    return method in ("axe", "custom")


def selectors_related(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    if a == b:
        return True
    return b.startswith(a + " > ") or a.startswith(b + " > ")


def normalize(raw: dict, canonical_selector: str | None) -> dict:
    """Fill defaults and canonical selector on a raw finding dict (axe, custom or ai)."""
    f = dict(raw)
    sel = canonical_selector or f.pop("raw_selector", None) or None
    f.pop("raw_selector", None)
    f["selector"] = sel
    ev = dict(f.get("evidence") or {})
    ev["selector"] = sel or ""
    f["evidence"] = ev
    f["wcag_criteria"] = sorted(set(f.get("wcag_criteria", [])), key=lambda x: [int(p) for p in x.split(".")])
    return f


def _compatible(a: dict, b: dict) -> bool:
    if not selectors_related(a.get("selector"), b.get("selector")):
        return False
    return a["category"] == b["category"] or bool(set(a["wcag_criteria"]) & set(b["wcag_criteria"]))


def assign_groups(findings: list[dict]) -> list[dict]:
    """Assign group_id so that findings found by both method families share one id. Mutates and returns."""
    conv = [f for f in findings if conventional(f["method"])]
    ai = [f for f in findings if not conventional(f["method"])]
    nxt = 1
    for f in findings:
        f["group_id"] = None
    for c in conv:  # conventional findings on the same element+category collapse into one group
        for prev in conv:
            if prev is c:
                break
            if prev["group_id"] and prev["selector"] and prev["selector"] == c["selector"] and prev["category"] == c["category"]:
                c["group_id"] = prev["group_id"]
                break
        if c["group_id"] is None:
            c["group_id"], nxt = nxt, nxt + 1
    for a in ai:
        match = next((c for c in conv if _compatible(c, a)), None)
        if match:
            a["group_id"] = match["group_id"]
        else:
            a["group_id"], nxt = nxt, nxt + 1
    return findings


def comparison(findings: list) -> dict:
    """Summarise detection provenance per group. `findings` may be ORM rows or dicts."""
    g = defaultdict(lambda: {"conventional": [], "ai": []})
    for f in findings:
        get = (lambda k: f[k]) if isinstance(f, dict) else (lambda k: getattr(f, k))
        gid = get("group_id")
        g[gid]["conventional" if conventional(get("method")) else "ai"].append(get("id") if not isinstance(f, dict) else f.get("id"))
    groups = []
    for gid, d in sorted(g.items(), key=lambda kv: (kv[0] is None, kv[0])):
        kind = "both" if d["conventional"] and d["ai"] else ("conventional_only" if d["conventional"] else "ai_only")
        groups.append({"group_id": gid, "detected_by": kind, "conventional_ids": d["conventional"], "ai_ids": d["ai"]})
    counts = {k: sum(1 for x in groups if x["detected_by"] == k) for k in ("conventional_only", "ai_only", "both")}
    return {"counts": counts, "groups": groups, "total_groups": len(groups)}
